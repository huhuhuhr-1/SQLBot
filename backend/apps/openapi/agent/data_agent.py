"""
Data Agent：基于 DeepAgents 框架的数据探查 Agent。

完全依赖 DeepAgents 内置能力 + data-explorer 技能：
- LocalShellBackend: execute(bash), read_file, write_file, edit_file, ls, grep, glob
- SkillsMiddleware: 渐进加载 data-explorer SKILL.md
- TodoListMiddleware: write_todos 任务管理
- SubAgentMiddleware: task 子任务委派
- MemorySaver: 会话记忆

Agent 通过 bash 调用 scripts/run.sh 操作 SQLBot API（发现数据源、拉元数据、执行 SQL 导出 CSV），
通过 read_file 读 CSV 数据，通过 bash python3 分析数据，最后生成报告。
不需要任何自定义工具。
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

DATA_AGENT_SYSTEM_PROMPT = """\
你是 SQLBot Data Agent — 一个顶尖的数据探查专家。

## 身份与环境

你运行在 SQLBot 平台中，工作目录是 data-explorer 技能根目录。
你的全部能力来自 DeepAgents 内置工具和 data-explorer 技能脚本。

## 工具清单

**内置工具（直接可用）:**
- `execute`: 执行 bash 命令（包括 python3）
- `read_file` / `write_file` / `edit_file`: 读写编辑文件
- `ls` / `grep` / `glob`: 浏览搜索文件
- `write_todos`: 规划和跟踪任务进度
- `task`: 委派子任务给子 Agent

**技能脚本（通过 execute 调用）:**
- `bash scripts/run.sh list-ds {user_id}` — 列出可用数据源
- `bash scripts/run.sh describe {user_id} <db_id>` — 查看数据源 schema
- `bash scripts/run.sh exec {user_id} <db_id> "<SQL>" [file.csv]` — 执行 SQL 导出 CSV
- `bash scripts/run.sh pull-table {user_id} <db_id> <table>` — 同步单表详情
- 更多命令: `bash scripts/run.sh -h`

## 当前用户上下文

- 用户 ID: {user_id}
- API 地址: {api_url}
- Token 已通过 init 预配置
- 数据源元数据缓存在 `~/.sqlbot/{user_id}/`

## 你的工作流程

1. **先了解工具**: 执行 `bash scripts/run.sh -h` 了解所有可用命令
2. **发现数据源**: `bash scripts/run.sh list-ds {user_id}`
3. **了解结构**: `bash scripts/run.sh describe {user_id} <db_id>` 或读取本地缓存
4. **参考方言**: 读取 `references/engines/` 下的 YAML 确保 SQL 语法正确
5. **迭代探查**: `bash scripts/run.sh exec {user_id} <db_id> "<SQL>" result.csv` 导出 CSV
6. **分析数据**: 读取 CSV 或用 `python3` 脚本做统计分析
7. **产出报告**: 汇总所有证据，生成结构化中文报告

## 输出要求

- 所有面向用户的内容使用**中文**
- **严禁杜撰**：报告中的数值必须有 CSV 证据支撑
- 最终报告包含：发现、证据、风险、建议
- SQL 必须符合数据源的方言规范（参考 references/engines/）
"""


class DataAgentRunner:
    """基于 DeepAgents 框架的 Data Agent — 零自定义工具，完全依赖内置能力 + 技能。"""

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

    # ===== 预初始化：通过 run.sh 初始化用户空间和元数据 =====

    async def _pre_init_user_space(self) -> None:
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
            _log.error(f"init failed (rc={rc}): {err[:200]}")
            return

        await _run(["bash", script, "pull-permissions", uid])

        from apps.datasource.crud.datasource import get_datasource_list_for_openapi

        ds_list = get_datasource_list_for_openapi(
            session=self.session, user=self.current_user
        )
        _log.info(f"  pre_init: {len(ds_list)} 个数据源, 拉取元数据...")
        for ds in ds_list:
            ds_id = str(ds.id)
            await _run(["bash", script, "pull-index", uid, ds_id])
            await _run(["bash", script, "pull-semantic", uid, ds_id])
        _log.info("  pre_init: 完成")

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

        skills_dir = str(SKILL_DIR.parent)
        skills_arg = [skills_dir + "/"] if os.path.isdir(skills_dir) else None

        agent = create_deep_agent(
            model=llm,
            system_prompt=system_prompt,
            backend=backend,
            skills=skills_arg,
            checkpointer=MemorySaver(),
            name="sqlbot-data-agent",
        )

        return agent

    # ===== SSE 事件标签 =====

    @staticmethod
    def _build_stage_label(tool_name: str, tool_input: Any) -> str:
        type_labels = {
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
        base_label = type_labels.get(tool_name, tool_name)

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
                pattern = tool_input.get("pattern", "")
                if pattern:
                    detail = str(pattern)[:80]
        elif isinstance(tool_input, str) and tool_input:
            detail = tool_input.strip().split("\n")[0][:120]

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

            uid = str(self.current_user.id)
            thread_id = str(self.chat_question.chat_id or f"da-{uid}")

            _log.info("[1/3] 预初始化...")
            await self._pre_init_user_space()

            await self.queue.put(
                {
                    "type": "plan",
                    "content": (
                        "**Data Agent 模式**\n\n"
                        "使用 DeepAgents 框架，具备 bash 执行、文件读写、"
                        "技能加载和任务管理能力。\n\n"
                        f"- 用户 ID: `{uid}`\n"
                        "- 数据源: 自动发现所有可用数据源\n"
                        "- 技能: `data-explorer`\n"
                        "- 工具: `execute`(bash), `read_file`, `write_file`, "
                        "`edit_file`, `ls`, `grep`, `glob`, `write_todos`, `task`"
                    ),
                    "plan": {
                        "mode": "data-agent",
                        "skills": ["data-explorer"],
                        "tools": [
                            "execute",
                            "read_file",
                            "write_file",
                            "edit_file",
                            "ls",
                            "grep",
                            "glob",
                            "write_todos",
                            "task",
                        ],
                    },
                }
            )
            await self.queue.put(
                {"type": "stage", "content": "Data Agent 启动", "stage": "agent"}
            )

            _log.info("[2/3] 构建 DeepAgent...")
            agent = await self._build_agent()
            _log.info("[2/3] 完成")

            user_input = self.chat_question.question
            report_content = ""
            event_count = 0
            tool_call_count = 0

            _log.info(f"[3/3] astream_events: {user_input[:80]}...")
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
                f"结束: {event_count} 事件, {tool_call_count} 工具调用, "
                f"report={len(report_content)}"
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
                _log.warning("report_content 为空")

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
            _log.error(f"Data Agent 出错: {e}")
            import traceback

            traceback.print_exc()
            await self.queue.put(
                {
                    "reasoning_content": "",
                    "content": f"Data Agent 执行出错：{e}",
                    "type": "error",
                }
            )
