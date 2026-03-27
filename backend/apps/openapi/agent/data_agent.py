"""
Data Agent：基于 DeepAgents 框架的数据探查 Agent。

正确使用 DeepAgents API：
- StateBackend（虚拟文件系统）替代 LocalShellBackend
- create_file_data 注入技能/元数据到 files 参数
- MemorySaver 支持会话记忆
- 自定义 execute_sql 工具（内存调用）替代 bash curl subprocess
"""

from __future__ import annotations

import asyncio
import base64
import json
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

## 身份

你运行在 SQLBot 平台中，具备直接查询数据库的能力。你的工作目录下有 data-explorer 技能文件，
里面包含 SQL 方言规范和分析方法论。

## 当前用户上下文

- 用户 ID: {user_id}
- 可用数据源: 已注入到 /datasources/ 目录下

## 你拥有的工具

- `execute_sql`: 直接执行 SQL 查询（传入 datasource_id 和 SQL 语句）
- `list_datasources`: 列出所有可用数据源
- `describe_datasource`: 查看数据源的表结构详情
- 标准文件工具: `read_file`, `write_file`, `ls`, `grep` 等（用于读取技能文件和方言规范）

## 你的工作流程

1. 先用 `list_datasources` 了解可用数据源
2. 用 `describe_datasource` 查看目标数据源的表结构和字段
3. 参考 /skills/data-explorer/references/engines/ 下的方言规范编写 SQL
4. 用 `execute_sql` 少量多次查询，逐步分析
5. 汇总证据，生成结构化中文报告

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
    """基于 DeepAgents 框架的 Data Agent — 正确使用虚拟文件系统和自定义工具。"""

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

    # ===== 自定义工具：直接内存调用 =====

    def _create_tools(self) -> list[StructuredTool]:
        """创建自定义工具，替代 bash curl subprocess。"""
        session = self.session
        user = self.current_user

        def execute_sql(datasource_id: int, sql: str) -> str:
            """执行 SQL 查询并返回结果。只允许 SELECT 类语句。"""
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
                    for row in data[:100]:
                        writer.writerow({str(k): str(v) for k, v in row.items()})
                    lines.append(buf.getvalue())
                return "\n".join(lines)
            except Exception as e:
                return f"SQL 执行错误: {e}"

        def list_datasources() -> str:
            """列出当前用户可用的所有数据源。"""
            from apps.datasource.crud.datasource import get_datasource_list_for_openapi

            try:
                ds_list = get_datasource_list_for_openapi(session=session, user=user)
                if not ds_list:
                    return "当前用户没有可用的数据源"
                lines = ["可用数据源列表:", ""]
                for ds in ds_list:
                    lines.append(
                        f"- ID: {ds.id} | 名称: {ds.name} | 类型: {ds.type_name or ds.type} | 描述: {ds.description or '无'}"
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
                    return (
                        f"数据源 ID {datasource_id} 没有数据表（可能需要先同步表结构）"
                    )

                lines = [f"数据源 ID: {datasource_id}, 共 {len(tables)} 张表", ""]
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
                            fname = f.field_name
                            ftype = f.field_type or ""
                            fcomment = f.custom_comment or f.field_comment or ""
                            lines.append(f"| {fname} | {ftype} | {fcomment} |")
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

    # ===== 构建虚拟文件系统 =====

    def _build_skill_files(self) -> dict[str, Any]:
        """将 data-explorer 技能文件和引擎方言注入虚拟文件系统。"""
        from deepagents.backends.utils import create_file_data

        files: dict[str, Any] = {}

        skill_md = SKILL_DIR / "SKILL.md"
        if skill_md.exists():
            files["/skills/data-explorer/SKILL.md"] = create_file_data(
                skill_md.read_text(encoding="utf-8")
            )

        impl_md = SKILL_DIR / "references" / "IMPLEMENTATION.md"
        if impl_md.exists():
            files["/skills/data-explorer/references/IMPLEMENTATION.md"] = (
                create_file_data(impl_md.read_text(encoding="utf-8"))
            )

        engines_dir = SKILL_DIR / "references" / "engines"
        if engines_dir.exists():
            for yaml_file in engines_dir.glob("*.yaml"):
                vpath = f"/skills/data-explorer/references/engines/{yaml_file.name}"
                files[vpath] = create_file_data(yaml_file.read_text(encoding="utf-8"))

        return files

    def _build_datasource_files(self) -> dict[str, Any]:
        """将数据源元数据注入虚拟文件系统，供 Agent 通过 read_file 查看。"""
        from deepagents.backends.utils import create_file_data

        from apps.datasource.crud.datasource import get_datasource_list_for_openapi

        files: dict[str, Any] = {}
        try:
            ds_list = get_datasource_list_for_openapi(
                session=self.session, user=self.current_user
            )
            index_lines = ["# 可用数据源\n"]
            for ds in ds_list:
                index_lines.append(
                    f"- **ID {ds.id}**: {ds.name} (类型: {ds.type_name or ds.type})"
                    + (f" — {ds.description}" if ds.description else "")
                )
            files["/datasources/index.md"] = create_file_data("\n".join(index_lines))
        except Exception as e:
            SQLBotLogUtil.error(f"构建数据源文件失败: {e}")

        return files

    # ===== 构建 Agent =====

    async def _build_agent(self):
        from deepagents import create_deep_agent
        from langgraph.checkpoint.memory import MemorySaver

        llm = await create_llm(use_tool=True)
        uid = str(self.current_user.id)

        system_prompt = DATA_AGENT_SYSTEM_PROMPT.format(user_id=uid)
        custom_tools = self._create_tools()
        checkpointer = MemorySaver()

        agent = create_deep_agent(
            model=llm,
            tools=custom_tools,
            system_prompt=system_prompt,
            skills=["/skills/"],
            checkpointer=checkpointer,
            name="sqlbot-data-agent",
        )

        return agent

    # ===== SSE 事件推送辅助 =====

    @staticmethod
    def _build_stage_label(tool_name: str, tool_input: Any) -> str:
        """从工具名和输入参数生成可读的步骤描述。"""
        type_labels = {
            "execute_sql": "查询数据",
            "list_datasources": "获取数据源列表",
            "describe_datasource": "获取数据集信息",
            "read_file": "读取文件",
            "write_file": "写入文件",
            "ls": "浏览目录",
            "grep": "搜索内容",
            "write_todos": "任务规划",
            "glob": "文件匹配",
            "edit_file": "编辑文件",
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
            elif tool_name == "read_file":
                path = tool_input.get("path", tool_input.get("file_path", ""))
                if path:
                    detail = str(path)
            elif tool_name == "execute":
                cmd = tool_input.get("command", tool_input.get("cmd", ""))
                if isinstance(cmd, str) and cmd:
                    detail = cmd.strip().split("\n")[0][:100]
            elif tool_name == "ls":
                detail = str(tool_input.get("path", "."))
        elif isinstance(tool_input, str) and tool_input:
            detail = tool_input.strip().split("\n")[0][:100]

        if detail:
            return f"{base_label}：{detail}"
        return base_label

    # ===== 主运行逻辑 =====

    async def run(self) -> None:
        _log = SQLBotLogUtil
        try:
            _log.info("========== Data Agent 开始运行 ==========")
            _log.info(
                f"用户: {self.current_user.id}, 问题: {self.chat_question.question[:100]}"
            )
            _log.info(
                f"chat_id: {self.chat_question.chat_id}, max_steps: {self.max_steps}"
            )

            uid = str(self.current_user.id)
            thread_id = str(self.chat_question.chat_id or f"da-{uid}")

            # 构建虚拟文件系统
            _log.info("[1/3] 构建虚拟文件系统...")
            skill_files = self._build_skill_files()
            ds_files = self._build_datasource_files()
            all_files = {**skill_files, **ds_files}
            _log.info(f"[1/3] 虚拟文件系统就绪: {len(all_files)} 个文件")

            # 发送 plan 事件
            await self.queue.put(
                {
                    "type": "plan",
                    "content": (
                        "**Data Agent 模式**\n\n"
                        "使用 DeepAgents 框架，具备 SQL 直接执行、元数据查询、"
                        "文件读写和技能加载能力。\n\n"
                        f"- 用户 ID: `{uid}`\n"
                        "- 数据源: 自动发现所有可用数据源\n"
                        "- 工具: `execute_sql`, `list_datasources`, `describe_datasource`, "
                        "`read_file`, `write_file`, `ls`, `grep`"
                    ),
                    "plan": {
                        "mode": "data-agent",
                        "tools": [
                            "execute_sql",
                            "list_datasources",
                            "describe_datasource",
                            "read_file",
                            "write_file",
                            "ls",
                            "grep",
                        ],
                    },
                }
            )
            await self.queue.put(
                {
                    "type": "stage",
                    "content": "Data Agent 启动",
                    "stage": "agent",
                }
            )

            # 构建 Agent
            _log.info("[2/3] 构建 DeepAgent...")
            agent = await self._build_agent()
            _log.info("[2/3] DeepAgent 构建完成")

            user_input = self.chat_question.question
            report_content = ""
            event_count = 0
            tool_call_count = 0

            _log.info(f"[3/3] 开始 astream_events, 输入: {user_input[:80]}...")
            async for event in agent.astream_events(
                {
                    "messages": [{"role": "user", "content": user_input}],
                    "files": all_files,
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
                    _log.info(f"  event#{event_count}: kind={kind}")

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
                        f"  🔧 tool_start #{tool_call_count}: {tool_name} | {input_preview[:120]}"
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
                    _log.info(f"  ✅ tool_end: {tool_name} | len={len(output_str)}")

                    await self.queue.put(
                        {
                            "reasoning_content": "",
                            "content": (
                                f"\n**{tool_name} 执行结果** ({len(output_str)} 字符):\n"
                                f"```\n{output_preview}\n```\n\n执行结束\n"
                            ),
                            "type": "process",
                        }
                    )

            _log.info(
                f"astream_events 结束: {event_count} 事件, "
                f"{tool_call_count} 工具调用, report_len={len(report_content)}"
            )

            if report_content:
                _log.info("发送 report 事件...")
                await self.queue.put(
                    {
                        "type": "stage",
                        "content": "生成报告",
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
            else:
                _log.warning("Data Agent 未产出 report_content")

            _log.info("发送 finish 事件...")
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
