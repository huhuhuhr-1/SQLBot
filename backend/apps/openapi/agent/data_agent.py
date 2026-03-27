"""
Data Agent：基于 DeepAgents 框架 + data-explorer 技能的数据探查 Agent。

架构设计：
- DeepAgents 提供全部能力：execute(bash), read_file, write_file, edit_file, ls, grep, glob, write_todos, task
- data-explorer 技能提供完整工作流：SKILL.md + scripts/run.sh + references/
- DataAgentRunner 仅负责：预注入 token → 创建 Agent → 流式推送 SSE 事件
- 零自定义工具：所有数据操作通过 bash scripts/run.sh 完成
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessageChunk
from sqlmodel import Session

from apps.ai_model.model_factory import create_llm
from apps.openapi.models.openapiModels import OpenChatQuestion
from common.core.deps import CurrentAssistant, CurrentUser
from common.utils.utils import SQLBotLogUtil

SKILL_DIR = Path(__file__).parent / "skills" / "data-explorer"


class DataAgentRunner:
    """基于 DeepAgents + data-explorer 技能的 Data Agent。

    设计原则：
    - 技能即全部：SKILL.md 定义工作流，run.sh 提供 API 客户端
    - Agent 用内置工具（bash/文件）驱动技能脚本
    - Runner 只做胶水：token 注入 + Agent 创建 + SSE 推送
    """

    def __init__(
        self,
        session: Session,
        current_user: CurrentUser,
        chat_question: OpenChatQuestion,
        current_assistant: CurrentAssistant,
        queue: asyncio.Queue,
        max_steps: int | None = None,
    ) -> None:
        self.session = session
        self.current_user = current_user
        self.chat_question = chat_question
        self.current_assistant = current_assistant
        self.queue = queue
        self.max_steps = max_steps or 30

    def _get_api_url(self) -> str:
        from common.core.config import settings

        return f"http://localhost:8000{settings.API_V1_STR}"

    def _get_user_token(self) -> str:
        from apps.openapi.service.openapi_service import (
            create_access_token_with_expiry,
        )

        user_dict = {
            "id": self.current_user.id,
            "account": getattr(self.current_user, "account", ""),
            "oid": getattr(self.current_user, "oid", 1),
        }
        token, _ = create_access_token_with_expiry(user_dict)
        return token

    async def _pre_init_user_space(self) -> None:
        """通过 run.sh init 注入 token，拉取元数据到本地缓存。

        Agent 启动后可直接读取 ~/.sqlbot/<uid>/ 下的缓存文件。
        """
        _log = SQLBotLogUtil
        uid = str(self.current_user.id)
        api_url = self._get_api_url()
        token = self._get_user_token()
        script = str(SKILL_DIR / "scripts" / "run.sh")

        if not Path(script).exists():
            _log.warning(f"run.sh not found: {script}")
            return

        async def _run(cmd: list[str]) -> tuple[int, str, str]:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(SKILL_DIR),
            )
            out, err = await proc.communicate()
            return proc.returncode, out.decode(), err.decode()

        rc, _, err = await _run(["bash", script, "init", uid, api_url, token])
        if rc != 0:
            _log.error(f"init failed: {err[:200]}")
            return

        await _run(["bash", script, "pull-permissions", uid])

        from apps.datasource.crud.datasource import (
            get_datasource_list_for_openapi,
        )

        ds_list = get_datasource_list_for_openapi(
            session=self.session, user=self.current_user
        )
        _log.info(f"  pre_init: {len(ds_list)} datasources")
        for ds in ds_list:
            await _run(["bash", script, "pull-index", uid, str(ds.id)])
            await _run(["bash", script, "pull-semantic", uid, str(ds.id)])

    async def _build_agent(self):
        from deepagents import create_deep_agent
        from deepagents.backends import LocalShellBackend
        from langgraph.checkpoint.memory import MemorySaver

        llm = await create_llm(use_tool=True)
        uid = str(self.current_user.id)
        api_url = self._get_api_url()

        backend = LocalShellBackend(
            root_dir=str(SKILL_DIR),
            timeout=120,
            env={
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "HOME": os.environ.get("HOME", "/root"),
                "SQLBOT_URL": api_url,
            },
            inherit_env=False,
        )

        skills_dir = str(SKILL_DIR.parent)
        skills_arg = [skills_dir + "/"] if os.path.isdir(skills_dir) else None

        system_prompt = (
            f"当前用户 ID: {uid}\n"
            f"API 地址: {api_url}\n"
            f"Token 已通过 init 预配置，可直接使用 scripts/run.sh 操作。\n"
            f"数据源元数据缓存在 ~/.sqlbot/{uid}/\n"
            f"所有面向用户的内容使用中文。"
        )

        return create_deep_agent(
            model=llm,
            system_prompt=system_prompt,
            backend=backend,
            skills=skills_arg,
            checkpointer=MemorySaver(),
            name="sqlbot-data-agent",
        )

    @staticmethod
    def _build_stage_label(tool_name: str, tool_input: Any) -> str:
        labels = {
            "execute": "执行命令",
            "read_file": "读取文件",
            "write_file": "写入文件",
            "edit_file": "编辑文件",
            "ls": "浏览目录",
            "grep": "搜索内容",
            "glob": "文件匹配",
            "write_todos": "任务规划",
            "task": "委派子任务",
        }
        base = labels.get(tool_name, tool_name)

        detail = ""
        if isinstance(tool_input, dict):
            if tool_name == "execute":
                cmd = tool_input.get("command", tool_input.get("cmd", ""))
                if isinstance(cmd, str) and cmd:
                    detail = cmd.strip().split("\n")[0][:120]
            elif tool_name in ("read_file", "write_file", "edit_file"):
                path = tool_input.get("path", tool_input.get("file_path", ""))
                if path:
                    detail = str(path)
            elif tool_name == "ls":
                detail = str(tool_input.get("path", "."))
            elif tool_name == "grep":
                detail = str(tool_input.get("pattern", ""))[:80]
        elif isinstance(tool_input, str) and tool_input:
            detail = tool_input.strip().split("\n")[0][:120]

        return f"{base}：{detail}" if detail else base

    async def run(self) -> None:
        _log = SQLBotLogUtil
        try:
            _log.info("========== Data Agent ==========")
            _log.info(
                f"user={self.current_user.id} q={self.chat_question.question[:80]}"
            )

            uid = str(self.current_user.id)
            thread_id = str(self.chat_question.chat_id or f"da-{uid}")

            await self._pre_init_user_space()

            await self.queue.put(
                {
                    "type": "plan",
                    "content": (
                        "**Data Agent 模式**\n\n"
                        "基于 DeepAgents + data-explorer 技能，"
                        "通过 bash 脚本与 SQLBot API 交互。\n\n"
                        f"- 用户 ID: `{uid}`\n"
                        "- 技能: `data-explorer`\n"
                        "- 能力: bash, 文件读写, SQL 导出 CSV, Python 分析"
                    ),
                    "plan": {"mode": "data-agent", "skills": ["data-explorer"]},
                }
            )
            await self.queue.put(
                {"type": "stage", "content": "Data Agent 启动", "stage": "agent"}
            )

            agent = await self._build_agent()

            report_content = ""
            event_count = 0
            tool_count = 0

            async for event in agent.astream_events(
                {
                    "messages": [
                        {"role": "user", "content": self.chat_question.question}
                    ]
                },
                version="v2",
                config={
                    "configurable": {"thread_id": thread_id},
                    "recursion_limit": self.max_steps * 50,
                },
            ):
                kind = event.get("event", "")
                data = event.get("data", {})
                event_count += 1

                if event_count <= 5 or event_count % 50 == 0:
                    _log.info(f"  #{event_count}: {kind}")

                if kind == "on_chat_model_stream":
                    chunk = data.get("chunk")
                    if chunk and isinstance(chunk, AIMessageChunk):
                        text = chunk.content
                        if isinstance(text, str) and text.strip():
                            report_content += text
                            await self.queue.put(
                                {
                                    "reasoning_content": "",
                                    "content": text,
                                    "type": "process",
                                }
                            )

                elif kind == "on_tool_start":
                    tool_name = event.get("name", "unknown")
                    tool_input = data.get("input", {})
                    tool_count += 1

                    preview = ""
                    if isinstance(tool_input, dict):
                        preview = json.dumps(tool_input, ensure_ascii=False)[:300]
                    elif isinstance(tool_input, str):
                        preview = tool_input[:300]
                    _log.info(f"  🔧 #{tool_count}: {tool_name} | {preview[:120]}")

                    label = self._build_stage_label(tool_name, tool_input)
                    await self.queue.put(
                        {
                            "type": "stage",
                            "content": label,
                            "stage": tool_name,
                            "tool": tool_name,
                        }
                    )
                    await self.queue.put(
                        {
                            "reasoning_content": "",
                            "content": f"开始执行：{label}\n\n",
                            "type": "process",
                        }
                    )

                elif kind == "on_tool_end":
                    tool_name = event.get("name", "")
                    output = data.get("output", "")
                    out_str = str(output) if output else ""
                    _log.info(f"  ✅ {tool_name} | {len(out_str)} chars")

                    await self.queue.put(
                        {
                            "reasoning_content": "",
                            "content": (
                                f"\n**{tool_name} 结果** ({len(out_str)} 字符):\n"
                                f"```\n{out_str[:1000]}\n```\n\n执行结束\n"
                            ),
                            "type": "process",
                        }
                    )

            _log.info(
                f"完成: {event_count} events, {tool_count} tools, report={len(report_content)}"
            )

            if report_content:
                await self.queue.put(
                    {"type": "stage", "content": "生成报告", "stage": "report"}
                )
                await self.queue.put(
                    {
                        "reasoning_content": "",
                        "content": report_content,
                        "type": "report",
                    }
                )

            await self.queue.put(
                {
                    "reasoning_content": "",
                    "content": "",
                    "type": "finish",
                    "chat_id": self.chat_question.chat_id,
                }
            )

        except Exception as e:
            _log.error(f"Data Agent error: {e}")
            import traceback

            traceback.print_exc()
            await self.queue.put(
                {
                    "reasoning_content": "",
                    "content": f"Data Agent 执行出错：{e}",
                    "type": "error",
                }
            )
