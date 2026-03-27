"""Data Agent：基于 DeepAgents + data-explorer 技能。"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from langchain_core.messages import AIMessageChunk
from sqlmodel import Session

from apps.ai_model.model_factory import create_llm
from apps.openapi.models.openapiModels import OpenChatQuestion
from common.core.deps import CurrentUser
from common.utils.utils import SQLBotLogUtil

SKILL_DIR = Path(__file__).parent / "skills" / "data-explorer"


class DataAgentRunner:

    def __init__(
            self,
            session: Session,
            current_user: CurrentUser,
            chat_question: OpenChatQuestion,
            queue: asyncio.Queue,
            max_steps: int | None = None,
    ) -> None:
        self.session = session
        self.current_user = current_user
        self.chat_question = chat_question
        self.queue = queue
        self.max_steps = max_steps or 30

    def _get_api_url(self) -> str:
        from common.core.config import settings
        return f"http://localhost:8000{settings.API_V1_STR}"

    def _get_user_token(self) -> str:
        from apps.openapi.service.openapi_service import create_access_token_with_expiry
        token, _ = create_access_token_with_expiry({
            "id": self.current_user.id,
            "account": getattr(self.current_user, "account", ""),
            "oid": getattr(self.current_user, "oid", 1),
        })
        return token

    async def _pre_init_user_space(self) -> None:
        uid = str(self.current_user.id)
        script = str(SKILL_DIR / "scripts" / "run.sh")
        if not Path(script).exists():
            return

        async def _run(cmd: list[str]) -> int:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=str(SKILL_DIR),
            )
            await proc.communicate()
            return proc.returncode

        if await _run(["bash", script, "init", uid, self._get_api_url(), self._get_user_token()]) != 0:
            return
        await _run(["bash", script, "pull-permissions", uid])

        from apps.datasource.crud.datasource import get_datasource_list_for_openapi
        for ds in get_datasource_list_for_openapi(session=self.session, user=self.current_user):
            await _run(["bash", script, "pull-index", uid, str(ds.id)])
            await _run(["bash", script, "pull-semantic", uid, str(ds.id)])

    async def _build_agent(self):
        from deepagents import create_deep_agent
        from deepagents.backends import LocalShellBackend
        from langgraph.checkpoint.memory import MemorySaver

        uid = str(self.current_user.id)
        api_url = self._get_api_url()

        return create_deep_agent(
            model=await create_llm(use_tool=True),
            system_prompt=(
                f"当前用户 ID: {uid}\nAPI 地址: {api_url}\n"
                f"Token 已预配置，可直接使用 scripts/run.sh。\n"
                f"元数据缓存在 ~/.sqlbot/{uid}/\n所有输出使用中文。"
            ),
            backend=LocalShellBackend(
                root_dir=str(SKILL_DIR), timeout=120,
                env={"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": os.environ.get("HOME", "/root"),
                     "SQLBOT_URL": api_url},
                inherit_env=False,
            ),
            skills=[str(SKILL_DIR.parent) + "/"] if os.path.isdir(SKILL_DIR.parent) else None,
            checkpointer=MemorySaver(),
            name="sqlbot-data-agent",
        )

    @staticmethod
    def _stage_label(tool_name: str, tool_input) -> str:
        labels = {
            "execute": "执行命令", "read_file": "读取文件", "write_file": "写入文件",
            "edit_file": "编辑文件", "ls": "浏览目录", "grep": "搜索内容",
            "glob": "文件匹配", "write_todos": "任务规划", "task": "委派子任务",
        }
        base = labels.get(tool_name, tool_name)
        detail = ""
        if isinstance(tool_input, dict):
            if tool_name == "execute":
                cmd = tool_input.get("command", tool_input.get("cmd", ""))
                if isinstance(cmd, str) and cmd:
                    detail = cmd.strip().split("\n")[0][:120]
            elif tool_name in ("read_file", "write_file", "edit_file"):
                detail = str(tool_input.get("path", tool_input.get("file_path", "")))
            elif tool_name == "ls":
                detail = str(tool_input.get("path", "."))
            elif tool_name == "grep":
                detail = str(tool_input.get("pattern", ""))[:80]
        elif isinstance(tool_input, str):
            detail = tool_input.strip().split("\n")[0][:120]
        return f"{base}：{detail}" if detail else base

    async def run(self) -> None:
        _log = SQLBotLogUtil
        try:
            uid = str(self.current_user.id)
            _log.info(f"Data Agent start: user={uid} q={self.chat_question.question[:80]}")

            await self._pre_init_user_space()

            await self.queue.put({
                "type": "plan",
                "content": f"**Data Agent**\n\n- 用户: `{uid}`\n- 技能: `data-explorer`",
                "plan": {"mode": "data-agent", "skills": ["data-explorer"]},
            })
            await self.queue.put({"type": "stage", "content": "Data Agent 启动", "stage": "agent"})

            agent = await self._build_agent()
            report = ""
            tc = 0

            async for event in agent.astream_events(
                    {"messages": [{"role": "user", "content": self.chat_question.question}]},
                    version="v2",
                    config={"configurable": {"thread_id": str(self.chat_question.chat_id or f"da-{uid}")},
                            "recursion_limit": self.max_steps * 50},
            ):
                kind = event.get("event", "")
                data = event.get("data", {})

                if kind == "on_chat_model_stream":
                    chunk = data.get("chunk")
                    if chunk and isinstance(chunk, AIMessageChunk):
                        text = chunk.content
                        if isinstance(text, str) and text.strip():
                            report += text
                            await self.queue.put({"reasoning_content": "", "content": text, "type": "process"})

                elif kind == "on_tool_start":
                    name = event.get("name", "")
                    inp = data.get("input", {})
                    tc += 1
                    label = self._stage_label(name, inp)
                    _log.info(f"  🔧 #{tc}: {name}")
                    await self.queue.put({"type": "stage", "content": label, "stage": name, "tool": name})
                    await self.queue.put(
                        {"reasoning_content": "", "content": f"开始执行：{label}\n\n", "type": "process"})

                elif kind == "on_tool_end":
                    name = event.get("name", "")
                    out = str(data.get("output", ""))
                    _log.info(f"  ✅ {name} | {len(out)}c")
                    await self.queue.put({"reasoning_content": "",
                                          "content": f"\n**{name} 结果** ({len(out)}字符):\n```\n{out[:1000]}\n```\n\n执行结束\n",
                                          "type": "process"})

            if report:
                await self.queue.put({"type": "stage", "content": "生成报告", "stage": "report"})
                await self.queue.put({"reasoning_content": "", "content": report, "type": "report"})

            await self.queue.put(
                {"reasoning_content": "", "content": "", "type": "finish", "chat_id": self.chat_question.chat_id})
            _log.info(f"Data Agent done: {tc} tools, report={len(report)}c")

        except Exception as e:
            _log.error(f"Data Agent error: {e}")
            import traceback
            traceback.print_exc()
            await self.queue.put({"reasoning_content": "", "content": f"Data Agent 执行出错：{e}", "type": "error"})
