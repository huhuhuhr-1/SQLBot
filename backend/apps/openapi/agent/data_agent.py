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
        _log = SQLBotLogUtil
        uid = str(self.current_user.id)
        api_url = self._get_api_url()
        token = self._get_user_token()
        script = str(SKILL_DIR / "scripts" / "run.sh")
        _log.info(f"  pre_init: uid={uid}, api_url={api_url}, script={script}")
        _log.info(f"  pre_init: SKILL_DIR={SKILL_DIR}, exists={SKILL_DIR.exists()}")

        async def _run(cmd: list[str]) -> tuple[int, str, str]:
            _log.info(f"  pre_init _run: {' '.join(cmd[:4])}...")
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(SKILL_DIR),
            )
            out, err = await proc.communicate()
            rc = proc.returncode
            if rc != 0:
                _log.warning(f"  pre_init _run rc={rc}, stderr={err.decode()[:200]}")
            return rc, out.decode(), err.decode()

        rc, out, err = await _run(["bash", script, "init", uid, api_url, token])
        if rc != 0:
            _log.error(f"init user space failed (rc={rc}): {err[:300]}")
            return
        _log.info(f"  pre_init: init OK, stdout={out[:100]}")

        rc, out, err = await _run(["bash", script, "pull-permissions", uid])
        _log.info(f"  pre_init: pull-permissions rc={rc}")

        from apps.datasource.crud.datasource import get_datasource_list_for_openapi

        ds_list = get_datasource_list_for_openapi(session=self.session, user=self.current_user)
        _log.info(f"  pre_init: 发现 {len(ds_list)} 个数据源，开始拉取 schema/semantic...")
        for ds in ds_list:
            ds_id = str(ds.id)
            await _run(["bash", script, "pull-index", uid, ds_id])
            await _run(["bash", script, "pull-semantic", uid, ds_id])
        _log.info("  pre_init: 所有数据源元数据拉取完成")

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

    @staticmethod
    def _tool_to_stage_code(tool_name: str) -> str:
        mapping = {
            "execute": "execute",
            "read_file": "read",
            "write_file": "write",
            "ls": "browse",
            "grep": "search",
            "write_todos": "plan",
            "glob": "browse",
        }
        return mapping.get(tool_name, "tool")

    @staticmethod
    def _build_stage_label(tool_name: str, tool_input) -> str:
        """从工具名和输入参数生成可读的步骤描述（类似参考产品的"查询数据：..."格式）。"""
        type_labels = {
            "execute": "执行命令",
            "read_file": "读取文件",
            "write_file": "写入文件",
            "ls": "浏览目录",
            "grep": "搜索内容",
            "write_todos": "任务规划",
            "glob": "文件匹配",
        }
        base_label = type_labels.get(tool_name, tool_name)

        detail = ""
        if isinstance(tool_input, dict):
            if tool_name == "execute":
                cmd = tool_input.get("command", tool_input.get("cmd", ""))
                if isinstance(cmd, str) and cmd:
                    short_cmd = cmd.strip().split("\n")[0][:120]
                    detail = short_cmd
            elif tool_name == "read_file":
                path = tool_input.get("path", tool_input.get("file_path", ""))
                if path:
                    detail = str(path)
            elif tool_name == "write_file":
                path = tool_input.get("path", tool_input.get("file_path", ""))
                if path:
                    detail = str(path)
            elif tool_name == "ls":
                path = tool_input.get("path", tool_input.get("dir", "."))
                detail = str(path)
            elif tool_name == "grep":
                pattern = tool_input.get("pattern", tool_input.get("query", ""))
                detail = str(pattern)[:80] if pattern else ""
        elif isinstance(tool_input, str) and tool_input:
            detail = tool_input.strip().split("\n")[0][:120]

        if detail:
            return f"{base_label}：{detail}"
        return base_label

    async def run(self) -> None:
        _log = SQLBotLogUtil
        try:
            _log.info("========== Data Agent 开始运行 ==========")
            _log.info(f"用户: {self.current_user.id}, 问题: {self.chat_question.question[:100]}")
            _log.info(f"chat_id: {self.chat_question.chat_id}, max_steps: {self.max_steps}")

            _log.info("[1/4] 初始化用户空间 (pre_init_user_space)...")
            await self._pre_init_user_space()
            _log.info("[1/4] 用户空间初始化完成")

            uid = str(self.current_user.id)

            _log.info("[2/4] 发送 plan 事件到前端...")
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
            _log.info("[2/4] plan/stage 事件已入队")

            _log.info("[3/4] 构建 DeepAgent...")
            agent = await self._build_agent()
            _log.info("[3/4] DeepAgent 构建完成")

            user_input = self.chat_question.question

            report_content = ""
            event_count = 0
            tool_call_count = 0

            _log.info(f"[4/4] 开始 astream_events, 输入: {user_input[:80]}...")
            async for event in agent.astream_events(
                {"messages": [{"role": "user", "content": user_input}]},
                version="v2",
                config={"recursion_limit": 15000},
            ):
                kind = event.get("event", "")
                data = event.get("data", {})
                event_count += 1

                if event_count <= 5 or event_count % 20 == 0:
                    _log.info(f"  event#{event_count}: kind={kind}, keys={list(data.keys())}")

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

                    _log.info(f"  🔧 tool_start #{tool_call_count}: {tool_name} | input: {input_preview[:120]}")

                    stage_label = self._build_stage_label(tool_name, tool_input)
                    stage_code = self._tool_to_stage_code(tool_name)

                    await self.queue.put(
                        {
                            "type": "stage",
                            "content": stage_label,
                            "stage": stage_code,
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
                    await self.queue.put(
                        {
                            "reasoning_content": "",
                            "content": f"### 调用工具: `{tool_name}`\n```\n{input_preview}\n```\n",
                            "type": "process",
                        }
                    )

                elif kind == "on_tool_end":
                    tool_name = event.get("name", "")
                    output = data.get("output", "")
                    output_str = str(output) if output else ""
                    output_preview = output_str[:800]
                    _log.info(f"  ✅ tool_end: {tool_name} | output_len={len(output_str)}, preview: {output_str[:80]}")

                    await self.queue.put(
                        {
                            "reasoning_content": "",
                            "content": f"\n**`{tool_name}` 执行结果** (共 {len(output_str)} 字符):\n```\n{output_preview}\n```\n",
                            "type": "process",
                        }
                    )
                    await self.queue.put(
                        {
                            "reasoning_content": "",
                            "content": "\n执行结束\n",
                            "type": "process",
                        }
                    )

            _log.info(f"astream_events 结束: 共 {event_count} 个事件, {tool_call_count} 次工具调用, report_len={len(report_content)}")

            if report_content:
                _log.info("发送 report 事件...")
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
            else:
                _log.warning("Data Agent 未产出 report_content（report 为空）")

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
