"""Data Agent：基于 DeepAgents + data-explorer 技能 + 语义工具。"""

from __future__ import annotations

import asyncio
import os

from langchain_core.messages import AIMessageChunk
from sqlmodel import Session

from apps.ai_model.model_factory import create_llm
from apps.datasource.crud.datasource import get_datasource_list_for_openapi
from apps.openapi.agent import sqlbot_workspace as sw
from apps.openapi.agent.data_agent_tools import build_data_agent_tools
from apps.openapi.models.openapiModels import OpenChatQuestion
from apps.openapi.service.openapi_service import create_access_token_with_expiry
from common.core.config import settings
from common.core.deps import CurrentUser
from common.utils.utils import SQLBotLogUtil


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

    def _public_api_base(self) -> str:
        b = (getattr(settings, "DATA_AGENT_PUBLIC_API_BASE", None) or "").strip()
        if b:
            return b.rstrip("/")
        env = (
            os.environ.get("SQLBOT_PUBLIC_API_BASE")
            or os.environ.get("DATA_AGENT_PUBLIC_API_BASE")
            or ""
        ).strip()
        if env:
            return env.rstrip("/")
        return "http://127.0.0.1:8000"

    def _api_v1_prefix(self) -> str:
        return f"{self._public_api_base()}{settings.API_V1_STR}"

    def _get_user_token(self) -> str:
        token, _ = create_access_token_with_expiry(
            {
                "id": self.current_user.id,
                "account": getattr(self.current_user, "account", ""),
                "oid": getattr(self.current_user, "oid", 1),
            }
        )
        return token

    def _workspace_uid(self) -> str:
        return sw.workspace_uid(self.current_user)

    async def _pre_init_user_space(self) -> None:
        uid = self._workspace_uid()
        api_base = self._public_api_base()
        token = self._get_user_token()
        sw.ensure_user_workspace(uid)
        sw.write_agent_config(uid, api_base, token)
        sw.write_permissions(self.session, self.current_user, uid)
        for ds in get_datasource_list_for_openapi(
            session=self.session, user=self.current_user
        ):
            sw.sync_datasource_to_disk(self.session, self.current_user, uid, int(ds.id))

    async def _build_agent(self):
        from deepagents import create_deep_agent
        from deepagents.backends import LocalShellBackend
        from langgraph.checkpoint.memory import MemorySaver

        uid = self._workspace_uid()
        skill_dir = sw.data_explorer_skill_dir()
        sqlbot_home = sw.sqlbot_root_path()
        api_base = self._public_api_base()
        tools = build_data_agent_tools(self.session, self.current_user, uid)

        if not skill_dir.is_dir():
            raise FileNotFoundError(
                f"Data Agent 技能目录不存在: {skill_dir}。"
                f"请设置环境变量 DATA_AGENT_SKILL_ROOT 或确保存在 {sw.repo_root_path() / '.claude' / 'skills' / 'data-explorer'}"
            )

        skills_arg = None
        mid = sw.skills_middleware_dir()
        if mid.is_dir():
            skills_arg = [str(mid) + "/"]

        sys_lines = [
            f"工作区账号目录名: {uid}（与 CLI 使用相同 account 时共用缓存）",
            f"本地根目录 SQLBOT_HOME: {sqlbot_home}",
            f"元数据与 CSV: {sqlbot_home / uid}",
            f"技能包目录（Shell cwd）: {skill_dir}",
            f"API 根 URL（供子进程/脚本）: {api_base}",
            "优先使用语义工具：sqlbot_list_datasources、sqlbot_sync_datasource、sqlbot_sql_dialect、sqlbot_execute_sql_csv；",
            "需要复杂统计或绘图时用 execute 运行 Python，或用 read_file 读取 exports 下 CSV。",
            "生成 SQL 时列别名请使用英文，避免解析错误。",
            "所有输出使用中文。",
        ]

        return create_deep_agent(
            model=await create_llm(use_tool=True),
            system_prompt="\n".join(sys_lines),
            tools=tools,
            backend=LocalShellBackend(
                root_dir=str(skill_dir),
                timeout=120,
                env={
                    "PATH": "/usr/local/bin:/usr/bin:/bin",
                    "HOME": os.environ.get("HOME", "/root"),
                    "SQLBOT_URL": self._api_v1_prefix(),
                    "SQLBOT_HOME": str(sqlbot_home),
                    "SQLBOT_WORKSPACE_UID": uid,
                },
                inherit_env=False,
            ),
            skills=skills_arg,
            checkpointer=MemorySaver(),
            name="sqlbot-data-agent",
        )

    @staticmethod
    def _stage_label(tool_name: str, tool_input) -> str:
        sqlbot_labels = {
            "sqlbot_list_datasources": "列出数据源",
            "sqlbot_sync_datasource": "同步元数据",
            "sqlbot_execute_sql_csv": "导出查询 CSV",
            "sqlbot_sql_dialect": "SQL 方言模板",
        }
        if tool_name.startswith("sqlbot_"):
            desc = ""
            if isinstance(tool_input, dict):
                desc = str(tool_input.get("step_description", "")).strip()
            base = sqlbot_labels.get(tool_name, tool_name)
            return f"{base}：{desc}" if desc else base

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
                detail = str(tool_input.get("path", tool_input.get("file_path", "")))
            elif tool_name == "ls":
                detail = str(tool_input.get("path", "."))
            elif tool_name == "grep":
                detail = str(tool_input.get("pattern", ""))[:80]
        elif isinstance(tool_input, str):
            detail = tool_input.strip().split("\n")[0][:120]
        return f"{base}：{detail}" if detail else base

    @staticmethod
    def _tool_result_for_stream(tool_name: str, out: str) -> str:
        if tool_name.startswith("sqlbot_"):
            limit = 12000
            if len(out) > limit:
                return out[:limit] + "\n\n...（输出已截断）"
            return out
        return f"\n**{tool_name} 结果** ({len(out)}字符):\n```\n{out[:1000]}\n```\n\n执行结束\n"

    async def run(self) -> None:
        _log = SQLBotLogUtil
        uid = self._workspace_uid()
        try:
            _log.info(
                f"Data Agent start: workspace={uid} q={self.chat_question.question[:80]}"
            )

            await self._pre_init_user_space()

            sqlbot_home = sw.sqlbot_root_path()
            skill_path = sw.data_explorer_skill_dir()
            await self.queue.put(
                {
                    "type": "plan",
                    "content": (
                        f"**Data Agent**\n\n- 工作区: `{uid}`\n- SQLBOT_HOME: `{sqlbot_home}`\n"
                        f"- 技能目录: `{skill_path}`\n- 技能: `data-explorer`"
                    ),
                    "plan": {
                        "mode": "data-agent",
                        "skills": ["data-explorer"],
                        "sqlbot_home": str(sqlbot_home),
                        "workspace_uid": uid,
                    },
                }
            )
            await self.queue.put(
                {"type": "stage", "content": "Data Agent 启动", "stage": "agent"}
            )

            agent = await self._build_agent()
            report = ""
            tc = 0

            async for event in agent.astream_events(
                {
                    "messages": [
                        {"role": "user", "content": self.chat_question.question}
                    ]
                },
                version="v2",
                config={
                    "configurable": {
                        "thread_id": str(self.chat_question.chat_id or f"da-{uid}")
                    },
                    "recursion_limit": self.max_steps * 50,
                },
            ):
                kind = event.get("event", "")
                data = event.get("data", {})

                if kind == "on_chat_model_stream":
                    chunk = data.get("chunk")
                    if chunk and isinstance(chunk, AIMessageChunk):
                        text = chunk.content
                        if isinstance(text, str) and text.strip():
                            report += text
                            await self.queue.put(
                                {
                                    "reasoning_content": "",
                                    "content": text,
                                    "type": "process",
                                }
                            )

                elif kind == "on_tool_start":
                    name = event.get("name", "")
                    inp = data.get("input", {})
                    tc += 1
                    label = self._stage_label(name, inp)
                    _log.info(f"  🔧 #{tc}: {name}")
                    await self.queue.put(
                        {"type": "stage", "content": label, "stage": name, "tool": name}
                    )
                    await self.queue.put(
                        {
                            "reasoning_content": "",
                            "content": f"开始执行：{label}\n\n",
                            "type": "process",
                        }
                    )

                elif kind == "on_tool_end":
                    name = event.get("name", "")
                    out = str(data.get("output", ""))
                    _log.info(f"  ✅ {name} | {len(out)}c")
                    body = self._tool_result_for_stream(name, out)
                    await self.queue.put(
                        {"reasoning_content": "", "content": body, "type": "process"}
                    )

            if report:
                await self.queue.put(
                    {"type": "stage", "content": "生成报告", "stage": "report"}
                )
                await self.queue.put(
                    {"reasoning_content": "", "content": report, "type": "report"}
                )

            await self.queue.put(
                {
                    "reasoning_content": "",
                    "content": "",
                    "type": "finish",
                    "chat_id": self.chat_question.chat_id,
                }
            )
            _log.info(f"Data Agent done: {tc} tools, report={len(report)}c")

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
