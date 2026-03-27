"""
Data Agent：基于 DeepAgents 框架的数据探查 Agent。

正确使用 DeepAgents：
- LocalShellBackend 保留完整 bash/文件能力（execute, read, write, edit, ls, grep）
- 自定义 execute_sql / list_datasources / describe_datasource 作为额外工具
- MemorySaver 支持会话记忆
- skills 指向磁盘目录，由 SkillsMiddleware 渐进加载
- _pre_init_user_space 将元数据预写入 SKILL_DIR，Agent 通过内置工具读取
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessageChunk
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlmodel import Session

from apps.ai_model.model_factory import create_llm
from apps.openapi.models.openapiModels import OpenChatQuestion
from common.core.deps import CurrentAssistant, CurrentUser
from common.utils.utils import SQLBotLogUtil

SKILL_DIR = Path(__file__).parent / "skills" / "data-explorer"

DATA_AGENT_SYSTEM_PROMPT = """\
你是 SQLBot Data Agent — 一个顶尖的数据探查专家。

## 身份与环境

你运行在 SQLBot 平台中，工作目录是 data-explorer 技能根目录。
你可以通过 `execute` 工具执行 bash 命令，通过 `read_file` / `write_file` / `edit_file` 读写文件，
通过 `ls` / `grep` / `glob` 浏览和搜索文件。

## 额外的数据工具

除了标准的文件和 bash 工具，你还有三个专用数据工具：

- `execute_sql(datasource_id, sql)`: 直接执行 SQL 查询，返回 CSV 格式结果。比 bash curl 更快更稳定。
- `list_datasources()`: 列出所有可用数据源（ID、名称、类型）。
- `describe_datasource(datasource_id)`: 查看数据源的完整表结构（表名、字段名、字段类型、备注）。

优先使用这三个工具查数据，不要再通过 bash scripts/run.sh exec 方式。

## 当前用户上下文

- 用户 ID: {user_id}
- API 地址: {api_url}
- 数据源元数据已预写到 `~/.sqlbot/{user_id}/`（如有需要可通过 bash scripts/run.sh 补充拉取）

## 你的工作流程

1. **发现数据源**: 用 `list_datasources` 查看可用数据源
2. **了解结构**: 用 `describe_datasource` 查看目标数据源的表结构
3. **参考方言**: 读取 `references/engines/` 下的 YAML 确保 SQL 语法正确
4. **迭代探查**: 用 `execute_sql` 少量多次查询，逐步分析
5. **产出报告**: 汇总所有查询证据，生成结构化中文报告

## 输出要求

- 所有面向用户的内容使用**中文**
- **严禁杜撰**：报告中的数值必须有查询证据支撑
- 最终报告包含：发现、证据、风险、建议
- SQL 必须符合数据源的方言规范
"""


class ExecuteSqlInput(BaseModel):
    datasource_id: int = Field(description="数据源 ID")
    sql: str = Field(description="要执行的 SQL 查询语句（只允许 SELECT/SHOW/DESCRIBE）")


class DatasourceIdInput(BaseModel):
    datasource_id: int = Field(description="数据源 ID")


class DataAgentRunner:
    """基于 DeepAgents 框架的 Data Agent。

    架构：
    - LocalShellBackend: 保留 execute/read/write/edit/ls/grep/glob 全部内置能力
    - 自定义工具: execute_sql, list_datasources, describe_datasource（内存调用，零 subprocess）
    - SkillsMiddleware: 渐进式加载 data-explorer 技能
    - MemorySaver: 会话记忆
    - TodoListMiddleware: 内置 todos 任务管理
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
        from apps.openapi.service.openapi_service import create_access_token_with_expiry

        user_dict = {
            "id": self.current_user.id,
            "account": getattr(self.current_user, "account", ""),
            "oid": getattr(self.current_user, "oid", 1),
        }
        token, _ = create_access_token_with_expiry(user_dict)
        return token

    # ===== 自定义工具：内存调用，作为额外能力 =====

    def _create_custom_tools(self) -> list[StructuredTool]:
        session = self.session
        user = self.current_user

        def execute_sql(datasource_id: int, sql: str) -> str:
            """执行 SQL 查询并返回 CSV 格式结果。只允许 SELECT 类语句。"""
            from apps.datasource.crud.datasource import get_datasource_by_name_or_id
            from apps.datasource.models.datasource import DataSourceRequest
            from apps.db.db import exec_sql

            try:
                req = DataSourceRequest(id=datasource_id)
                ds = get_datasource_by_name_or_id(session, user, req)
                if ds is None:
                    return f"错误：数据源 ID {datasource_id} 不存在或无权限访问"

                result = exec_sql(ds=ds, sql=sql, origin_column=False)
                fields = result.get("fields", [])
                data = result.get("data", [])
                raw_sql = (
                    base64.b64decode(result.get("sql", "")).decode("utf-8")
                    if result.get("sql")
                    else sql
                )

                lines = [
                    f"执行 SQL: {raw_sql}",
                    f"返回 {len(data)} 行, {len(fields)} 列",
                ]
                if fields:
                    lines.append(f"字段: {', '.join(str(f) for f in fields)}")
                if data:
                    import csv
                    import io

                    buf = io.StringIO()
                    writer = csv.DictWriter(buf, fieldnames=[str(f) for f in fields])
                    writer.writeheader()
                    for row in data[:200]:
                        writer.writerow({str(k): str(v) for k, v in row.items()})
                    lines.append(buf.getvalue())
                return "\n".join(lines)
            except Exception as e:
                return f"SQL 执行错误: {e}"

        def list_datasources() -> str:
            """列出当前用户可用的所有数据源。"""
            from apps.datasource.crud.datasource import (
                get_datasource_list_for_openapi,
            )

            try:
                ds_list = get_datasource_list_for_openapi(session=session, user=user)
                if not ds_list:
                    return "当前用户没有可用的数据源"
                lines = ["可用数据源列表:", ""]
                for ds in ds_list:
                    lines.append(
                        f"- ID: {ds.id} | 名称: {ds.name} | "
                        f"类型: {ds.type_name or ds.type} | "
                        f"描述: {ds.description or '无'}"
                    )
                return "\n".join(lines)
            except Exception as e:
                return f"获取数据源列表失败: {e}"

        def describe_datasource(datasource_id: int) -> str:
            """查看数据源的表结构详情（表名、字段名、字段类型、备注）。"""
            from apps.datasource.crud.field import get_fields_by_table_id
            from apps.datasource.crud.table import get_tables_by_ds_id
            from apps.datasource.models.field import FieldObj

            try:
                tables = get_tables_by_ds_id(session, datasource_id)
                if not tables:
                    return f"数据源 ID {datasource_id} 没有数据表"

                lines = [
                    f"数据源 ID: {datasource_id}, 共 {len(tables)} 张表",
                    "",
                ]
                for t in tables:
                    comment = t.custom_comment or t.table_comment or ""
                    lines.append(
                        f"### 表: {t.table_name}" + (f" ({comment})" if comment else "")
                    )
                    fields = get_fields_by_table_id(session, t.id, FieldObj())
                    if fields:
                        lines.append("| 字段名 | 类型 | 备注 |")
                        lines.append("|--------|------|------|")
                        for f in fields:
                            lines.append(
                                f"| {f.field_name} | {f.field_type or ''} "
                                f"| {f.custom_comment or f.field_comment or ''} |"
                            )
                    lines.append("")
                return "\n".join(lines)
            except Exception as e:
                return f"获取数据源结构失败: {e}"

        return [
            StructuredTool.from_function(
                func=execute_sql,
                name="execute_sql",
                description="执行 SQL 查询并返回 CSV 格式结果。只允许 SELECT/SHOW/DESCRIBE 语句。",
                args_schema=ExecuteSqlInput,
            ),
            StructuredTool.from_function(
                func=list_datasources,
                name="list_datasources",
                description="列出当前用户可用的所有数据源（ID、名称、类型、描述）。",
            ),
            StructuredTool.from_function(
                func=describe_datasource,
                name="describe_datasource",
                description="查看数据源的完整表结构（表名、字段名、字段类型、备注）。",
                args_schema=DatasourceIdInput,
            ),
        ]

    # ===== 预初始化：将元数据写到磁盘供 Agent 的内置工具读取 =====

    async def _pre_init_user_space(self) -> None:
        """初始化 .sqlbot 缓存。Agent 可通过内置 read_file/ls 读取这些文件。"""
        _log = SQLBotLogUtil
        uid = str(self.current_user.id)
        api_url = self._get_api_url()
        token = self._get_user_token()
        script = str(SKILL_DIR / "scripts" / "run.sh")

        if not Path(script).exists():
            _log.warning(f"run.sh not found: {script}, skipping pre-init")
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

        _log.info(f"  pre_init: uid={uid}, api_url={api_url}")

        rc, _, err = await _run(["bash", script, "init", uid, api_url, token])
        if rc != 0:
            _log.error(f"init user space failed (rc={rc}): {err[:200]}")
            return

        await _run(["bash", script, "pull-permissions", uid])

        from apps.datasource.crud.datasource import get_datasource_list_for_openapi

        ds_list = get_datasource_list_for_openapi(
            session=self.session, user=self.current_user
        )
        _log.info(f"  pre_init: {len(ds_list)} 个数据源")
        for ds in ds_list:
            ds_id = str(ds.id)
            await _run(["bash", script, "pull-index", uid, ds_id])
            await _run(["bash", script, "pull-semantic", uid, ds_id])
        _log.info("  pre_init: 元数据拉取完成")

    # ===== 构建 Agent =====

    async def _build_agent(self):
        from deepagents import create_deep_agent
        from deepagents.backends import LocalShellBackend
        from langgraph.checkpoint.memory import MemorySaver

        llm = await create_llm(use_tool=True)
        uid = str(self.current_user.id)
        api_url = self._get_api_url()

        system_prompt = DATA_AGENT_SYSTEM_PROMPT.format(user_id=uid, api_url=api_url)

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

        custom_tools = self._create_custom_tools()
        checkpointer = MemorySaver()

        skills_dir = str(SKILL_DIR.parent)
        skills_arg = [skills_dir + "/"] if os.path.isdir(skills_dir) else None

        agent = create_deep_agent(
            model=llm,
            tools=custom_tools,
            system_prompt=system_prompt,
            backend=backend,
            skills=skills_arg,
            checkpointer=checkpointer,
            name="sqlbot-data-agent",
        )

        return agent

    # ===== SSE 事件推送 =====

    @staticmethod
    def _build_stage_label(tool_name: str, tool_input: Any) -> str:
        type_labels = {
            "execute_sql": "查询数据",
            "list_datasources": "获取数据源列表",
            "describe_datasource": "获取数据集信息",
            "read_file": "读取文件",
            "write_file": "写入文件",
            "edit_file": "编辑文件",
            "ls": "浏览目录",
            "grep": "搜索内容",
            "glob": "文件匹配",
            "write_todos": "任务规划",
            "execute": "执行命令",
            "task": "委派子任务",
        }
        base_label = type_labels.get(tool_name, tool_name)

        detail = ""
        if isinstance(tool_input, dict):
            if tool_name == "execute_sql":
                sql = tool_input.get("sql", "")
                ds_id = tool_input.get("datasource_id", "")
                if sql:
                    short_sql = sql.strip().split("\n")[0][:80]
                    detail = f"数据源 {ds_id}, {short_sql}"
            elif tool_name == "describe_datasource":
                ds_id = tool_input.get("datasource_id", "")
                if ds_id:
                    detail = f"数据源 {ds_id}"
            elif tool_name in ("read_file", "write_file", "edit_file"):
                path = tool_input.get("path", tool_input.get("file_path", ""))
                if path:
                    detail = str(path)
            elif tool_name == "execute":
                cmd = tool_input.get("command", tool_input.get("cmd", ""))
                if isinstance(cmd, str) and cmd:
                    detail = cmd.strip().split("\n")[0][:100]
            elif tool_name == "ls":
                detail = str(tool_input.get("path", "."))
            elif tool_name == "grep":
                pattern = tool_input.get("pattern", tool_input.get("query", ""))
                if pattern:
                    detail = str(pattern)[:80]
        elif isinstance(tool_input, str) and tool_input:
            detail = tool_input.strip().split("\n")[0][:100]

        return f"{base_label}：{detail}" if detail else base_label

    # ===== 主运行逻辑 =====

    async def run(self) -> None:
        _log = SQLBotLogUtil
        try:
            _log.info("========== Data Agent 开始运行 ==========")
            _log.info(
                f"用户: {self.current_user.id}, "
                f"问题: {self.chat_question.question[:100]}"
            )
            _log.info(
                f"chat_id: {self.chat_question.chat_id}, max_steps: {self.max_steps}"
            )

            uid = str(self.current_user.id)
            thread_id = str(self.chat_question.chat_id or f"da-{uid}")

            _log.info("[1/3] 预初始化用户空间...")
            await self._pre_init_user_space()
            _log.info("[1/3] 预初始化完成")

            await self.queue.put(
                {
                    "type": "plan",
                    "content": (
                        "**Data Agent 模式**\n\n"
                        "使用 DeepAgents 框架，具备 bash 执行、文件读写、"
                        "SQL 直接查询和技能加载能力。\n\n"
                        f"- 用户 ID: `{uid}`\n"
                        "- 数据源: 自动发现所有可用数据源\n"
                        "- 工具: `execute_sql`, `list_datasources`, `describe_datasource`, "
                        "`execute` (bash), `read_file`, `write_file`, `edit_file`, "
                        "`ls`, `grep`, `glob`, `write_todos`"
                    ),
                    "plan": {
                        "mode": "data-agent",
                        "tools": [
                            "execute_sql",
                            "list_datasources",
                            "describe_datasource",
                            "execute",
                            "read_file",
                            "write_file",
                            "edit_file",
                            "ls",
                            "grep",
                            "glob",
                            "write_todos",
                        ],
                    },
                }
            )
            await self.queue.put(
                {"type": "stage", "content": "Data Agent 启动", "stage": "agent"}
            )

            _log.info("[2/3] 构建 DeepAgent...")
            agent = await self._build_agent()
            _log.info("[2/3] DeepAgent 构建完成")

            user_input = self.chat_question.question
            report_content = ""
            event_count = 0
            tool_call_count = 0

            _log.info(f"[3/3] 开始 astream_events: {user_input[:80]}...")
            async for event in agent.astream_events(
                {"messages": [{"role": "user", "content": user_input}]},
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
                    _log.info(f"  event#{event_count}: {kind}")

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
                    tool_call_count += 1

                    input_preview = ""
                    if isinstance(tool_input, dict):
                        input_preview = json.dumps(tool_input, ensure_ascii=False)[:300]
                    elif isinstance(tool_input, str):
                        input_preview = tool_input[:300]

                    _log.info(
                        f"  🔧 #{tool_call_count}: {tool_name} | {input_preview[:120]}"
                    )

                    stage_label = self._build_stage_label(tool_name, tool_input)
                    await self.queue.put(
                        {
                            "type": "stage",
                            "content": stage_label,
                            "stage": tool_name,
                            "tool": tool_name,
                        }
                    )
                    await self.queue.put(
                        {
                            "reasoning_content": "",
                            "content": f"开始执行：{stage_label}\n\n",
                            "type": "process",
                        }
                    )

                elif kind == "on_tool_end":
                    tool_name = event.get("name", "")
                    output = data.get("output", "")
                    output_str = str(output) if output else ""
                    output_preview = output_str[:1000]
                    _log.info(f"  ✅ {tool_name} | len={len(output_str)}")

                    await self.queue.put(
                        {
                            "reasoning_content": "",
                            "content": (
                                f"\n**{tool_name} 执行结果** "
                                f"({len(output_str)} 字符):\n"
                                f"```\n{output_preview}\n```\n\n"
                                "执行结束\n"
                            ),
                            "type": "process",
                        }
                    )

            _log.info(
                f"astream_events 结束: {event_count} 事件, "
                f"{tool_call_count} 工具调用, "
                f"report_len={len(report_content)}"
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
            else:
                _log.warning("Data Agent 未产出 report_content")

            await self.queue.put(
                {
                    "reasoning_content": "",
                    "content": "",
                    "type": "finish",
                    "chat_id": self.chat_question.chat_id,
                }
            )
            _log.info("========== Data Agent 运行结束 ==========")

        except Exception as e:
            _log.error(f"Data Agent 执行出错: {e}")
            import traceback

            traceback.print_exc()
            await self.queue.put(
                {
                    "reasoning_content": "",
                    "content": f"Data Agent 执行出错：{e}",
                    "type": "error",
                }
            )
