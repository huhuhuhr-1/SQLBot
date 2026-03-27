"""
Data Agent：基于 LangChain DeepAgents 的数据探查 Agent。

核心理念 — Local First + Bash 驱动：
- 使用 LocalShellBackend，Agent 通过 bash 执行 scripts/run.sh 与 SQLBot API 交互
- 加载磁盘上的 data-explorer SKILL.md（progressive disclosure）
- Agent 自主同步元数据、编写 SQL、导出 CSV、读取分析、生成报告
- 不依赖旧的 NL2SQL 工具链，而是让模型直接根据元数据写 SQL
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from langchain_core.messages import AIMessageChunk
from sqlmodel import Session

from apps.ai_model.model_factory import create_llm
from apps.openapi.models.openapiModels import OpenChatQuestion
from common.core.deps import CurrentAssistant, CurrentUser
from common.utils.utils import SQLBotLogUtil

SKILL_DIR = Path(__file__).parent / "skills" / "data-explorer"

DATA_AGENT_SYSTEM_PROMPT = """\
你是 SQLBot Data Agent — 一个顶尖的数据探查专家。

## 身份与环境

你运行在 SQLBot 平台中，当前工作目录已设置为 data-explorer 技能根目录。
你可以通过 `execute` 工具执行 bash 命令，通过文件系统工具读写文件。

## 快速启动

1. 先执行 `bash scripts/run.sh -h` 了解所有可用命令
2. 用户的登录信息已自动注入（见下方），你可以直接开始同步元数据
3. 参阅 `references/IMPLEMENTATION.md` 了解 .sqlbot 缓存结构

## 当前用户上下文

- 用户 ID: {user_id}
- API 地址: {api_url}
- Token 已通过 `scripts/run.sh init` 预配置
- 所有可用数据源的 schema 和术语已自动同步到本地 `~/.sqlbot/{user_id}/`

## 你的工作流程

1. **发现数据源**: 执行 `bash scripts/run.sh list-ds {user_id}` 查看可用数据源
2. **检查缓存**: `bash scripts/run.sh check {user_id} <db_id>` 查看某数据源的元数据状态
3. **阅读 schema**: `bash scripts/run.sh describe {user_id} <db_id>` 或直接读 `~/.sqlbot/{user_id}/schema/<db_id>/summary.json`
4. **参考方言**: 读取 `references/engines/` 下的 YAML 确保 SQL 语法正确
5. **迭代探查**: 少量多次执行 SQL，每次导出 CSV 到 exports/，读取分析
6. **产出报告**: 汇总所有 CSV 证据，生成结构化中文报告

**重要**: 你无需知道具体的数据源 ID，先 list-ds 看有哪些，再根据用户问题选择合适的数据源。

## 输出要求

- 所有面向用户的内容使用**中文**
- **严禁杜撰**：报告中的数值必须有 CSV 证据支撑
- 最终报告包含：发现、证据、风险、建议
- SQL 必须符合数据源方言规范
"""


class DataAgentRunner:
    """
    基于 DeepAgents 的 Data Agent — data-explorer 技能驱动。

    关键特性：
    - LocalShellBackend：Agent 可执行 bash（run.sh）和读写文件
    - data-explorer Skill：SKILL.md + scripts/run.sh + references/
    - 无旧工具依赖：Agent 通过 bash 脚本调用 SQLBot API，自己写 SQL
    - 流式输出：astream_events → SSE 推送到前端
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

        port = 8000
        return f"http://localhost:{port}{settings.API_V1_STR}"

    def _get_user_token(self) -> str:
        """为当前用户生成合法的 JWT token，供 run.sh 调用 API 使用。"""
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

    def _get_datasource_id(self) -> str:
        ds_id = getattr(self.chat_question, "datasource_id", None)
        if ds_id:
            return str(ds_id)
        chat_id = self.chat_question.chat_id
        if chat_id:
            from apps.chat.curd.chat import get_chat

            chat = get_chat(self.session, chat_id)
            if chat and getattr(chat, "datasource", None):
                return str(chat.datasource)
        return ""

    async def _pre_init_user_space(self) -> None:
        """在启动 Agent 前，初始化 .sqlbot 缓存并自动拉取所有可用数据源的元数据。"""
        uid = str(self.current_user.id)
        api_url = self._get_api_url()
        token = self._get_user_token()
        script = str(SKILL_DIR / "scripts" / "run.sh")

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
            SQLBotLogUtil.error(f"init user space failed: {err}")
            return

        # 拉取权限（可用数据源列表）
        await _run(["bash", script, "pull-permissions", uid])

        # 自动拉取所有数据源的 schema 索引和术语
        from apps.datasource.crud.datasource import get_datasource_list_for_openapi

        ds_list = get_datasource_list_for_openapi(session=self.session, user=self.current_user)
        for ds in ds_list:
            ds_id = str(ds.id)
            # 拉取 L1/L2 schema 索引
            await _run(["bash", script, "pull-index", uid, ds_id])
            # 拉取术语口径
            await _run(["bash", script, "pull-semantic", uid, ds_id])

    async def _build_agent(self):
        from deepagents import create_deep_agent
        from deepagents.backends import LocalShellBackend

        llm = await create_llm(use_tool=True)

        uid = str(self.current_user.id)
        api_url = self._get_api_url()

        system_prompt = DATA_AGENT_SYSTEM_PROMPT.format(
            user_id=uid,
            api_url=api_url,
        )

        skill_dir_str = str(SKILL_DIR)

        backend = LocalShellBackend(
            root_dir=skill_dir_str,
            timeout=120,
            env={
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "HOME": os.environ.get("HOME", "/root"),
                "SQLBOT_URL": api_url,
            },
            inherit_env=False,
        )

        # skills 路径要相对于 backend 的 root_dir（即 SKILL_DIR 本身）
        # 因为 SKILL_DIR 就是 data-explorer/，SKILL.md 在其根目录
        # 但 DeepAgents 的 skills 参数需要指向包含 skill 子目录的父目录
        parent_skills_dir = str(SKILL_DIR.parent)
        skills_arg = (
            [parent_skills_dir + "/"] if os.path.isdir(parent_skills_dir) else None
        )

        agent = create_deep_agent(
            model=llm,
            system_prompt=system_prompt,
            backend=backend,
            skills=skills_arg,
            name="sqlbot-data-agent",
        )

        return agent

    async def run(self) -> None:
        try:
            await self._pre_init_user_space()

            uid = str(self.current_user.id)

            await self.queue.put(
                {
                    "type": "plan",
                    "content": (
                        "**Data Agent 模式**\n\n"
                        "使用 DeepAgents 框架，具备 bash 执行、本地文件读写、"
                        "data-explorer 技能加载等完整 agentic 数据探查能力。\n\n"
                        f"- 用户 ID: `{uid}`\n"
                        "- 数据源: 自动发现所有可用数据源\n"
                        "- 技能: `data-explorer` (Local First + 渐进式加载 + 证据链)\n"
                        "- 工具: `execute` (bash), `read_file`, `write_file`, `ls`, `grep`"
                    ),
                    "plan": {
                        "mode": "data-agent",
                        "skills": ["data-explorer"],
                        "tools": [
                            "execute",
                            "read_file",
                            "write_file",
                            "ls",
                            "grep",
                            "write_todos",
                        ],
                    },
                }
            )
            await self.queue.put(
                {
                    "type": "stage",
                    "content": "当前阶段：Data Agent 启动",
                    "stage": "agent",
                }
            )

            agent = await self._build_agent()

            user_input = self.chat_question.question

            report_content = ""

            async for event in agent.astream_events(
                {"messages": [{"role": "user", "content": user_input}]},
                version="v2",
                config={"recursion_limit": 15000},
            ):
                kind = event.get("event", "")
                data = event.get("data", {})

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
                    input_preview = ""
                    if isinstance(tool_input, dict):
                        input_preview = json.dumps(tool_input, ensure_ascii=False)[:300]
                    elif isinstance(tool_input, str):
                        input_preview = tool_input[:300]

                    stage_map = {
                        "execute": ("执行命令", "execute"),
                        "read_file": ("读取文件", "read"),
                        "write_file": ("写入文件", "write"),
                        "ls": ("浏览目录", "browse"),
                        "grep": ("搜索内容", "search"),
                        "write_todos": ("任务规划", "plan"),
                        "glob": ("文件匹配", "browse"),
                    }

                    if tool_name in stage_map:
                        label, stage = stage_map[tool_name]
                        await self.queue.put(
                            {
                                "type": "stage",
                                "content": f"当前阶段：{label}",
                                "stage": stage,
                            }
                        )

                    await self.queue.put(
                        {
                            "reasoning_content": "",
                            "content": f"\n### 调用工具: `{tool_name}`\n```\n{input_preview}\n```\n",
                            "type": "process",
                        }
                    )

                elif kind == "on_tool_end":
                    tool_name = event.get("name", "")
                    output = data.get("output", "")
                    output_preview = str(output)[:500] if output else ""
                    if output_preview:
                        await self.queue.put(
                            {
                                "reasoning_content": "",
                                "content": f"\n**`{tool_name}` 结果**:\n```\n{output_preview}\n```\n",
                                "type": "process",
                            }
                        )

            # Agent 完成后，发送报告（从 agent 的最终输出中提取）
            if report_content:
                await self.queue.put(
                    {
                        "type": "stage",
                        "content": "当前阶段：汇总报告",
                        "stage": "report",
                    }
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
            SQLBotLogUtil.error(e)
            SQLBotLogUtil.error("Data Agent 执行出错")
            import traceback

            traceback.print_exc()
            await self.queue.put(
                {
                    "reasoning_content": "",
                    "content": f"Data Agent 执行出错：{e}",
                    "type": "error",
                }
            )
