"""Data Agent：基于 DeepAgents + data-explorer 技能 + 语义工具。"""

from __future__ import annotations

import asyncio
import csv as csv_module
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.messages import AIMessageChunk, HumanMessage, SystemMessage
from sqlmodel import Session

from apps.ai_model.model_factory import create_llm
from apps.datasource.crud.datasource import (
    get_datasource_list_for_openapi,
    get_table_schema,
)
from apps.openapi.agent import sqlbot_workspace as sw
from apps.openapi.agent.data_agent_report_html import (
    build_report_html,
    sanitize_evidence_for_json,
)
from apps.openapi.agent.data_agent_tool_format import (
    _extract_first_json_object,
    extract_write_todos_list,
    format_deepagent_tool_output,
    parse_execute_tool_raw,
    tool_result_summary_line,
)
from apps.openapi.agent.data_agent_tools import build_data_agent_tools
from apps.openapi.dao.openapiDao import get_datasource_by_name_or_id
from apps.openapi.models.openapiModels import DataSourceRequest, OpenChatQuestion
from apps.openapi.service.openapi_service import create_access_token_with_expiry
from common.core.config import settings
from common.core.deps import CurrentUser
from common.utils.utils import SQLBotLogUtil

# 预规划用的 schema 总长度上限，避免撑爆上下文
_DATA_AGENT_SCHEMA_BUDGET = 22000


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

    def _aggregate_schema_digest(self) -> str:
        """多数据源表结构摘要，供预规划 LLM 使用（与智能问数 schema 同源）。"""
        parts: list[str] = []
        used = 0
        q = (self.chat_question.question or "").strip()
        for row in get_datasource_list_for_openapi(
            session=self.session, user=self.current_user
        ):
            ds = get_datasource_by_name_or_id(
                session=self.session,
                user=self.current_user,
                query=DataSourceRequest(id=int(row.id)),
            )
            if ds is None:
                continue
            block = get_table_schema(
                session=self.session,
                current_user=self.current_user,
                ds=ds,
                question=q,
                embedding=False,
            )
            header = f"### 数据源 id={row.id} name={row.name} type={row.type}\n\n"
            chunk = header + (block or "（无表结构）")
            if used + len(chunk) > _DATA_AGENT_SCHEMA_BUDGET:
                parts.append(
                    f"### 数据源 id={row.id} name={row.name}\n\n"
                    "（表结构过长，其余数据源请用 sqlbot_sync_datasource + read_file 读本地 .sqlbot 元数据）\n"
                )
                break
            parts.append(chunk)
            used += len(chunk)
        if not parts:
            return "（当前无可见数据源或未配置表；请先配置数据源与选表。）"
        return "\n\n".join(parts)

    async def _generate_data_agent_execution_plan(self, schema_digest: str) -> str:
        """
        对标智能问数「先思考再动手」：在 Agent 循环前生成可展示的执行规划（Markdown）。
        """
        system = (
            "你是企业级 Data Agent 的任务规划助手。根据用户分析意图与数据库 schema 摘要，"
            "输出一份**可执行、可分步**的 Markdown 执行规划（使用中文）。\n\n"
            "结构要求：\n"
            "1. 用 `## 目标理解` 简要重述业务问题、时间口径、关键实体（不确定则写「待澄清」）。\n"
            "2. 用 `## 涉及数据源与表` 列出可能用到的数据源 id、表/主题（可写待同步后从 .sqlbot 确认）。\n"
            "3. 用 `## 执行步骤` 给出有序步骤列表；每步包含：**要做什么**、**建议使用的工具类型**"
            "（如：sqlbot_list_datasources / sqlbot_sync_datasource / read_file+grep 读 schema / "
            "sqlbot_sql_dialect / sqlbot_execute_sql_csv / execute 跑 Python 读 exports 下 CSV）、"
            "**本步产出**（如：CSV 路径、中间结论）。\n"
            "4. 用 `## 预期交付` 说明最终需要表格、图表还是文字结论（可多种）。\n"
            "5. 不要编造不存在的表名或字段；信息不足时明确写需要同步元数据后再查。\n"
            "6. 禁止输出敷衍套话；步骤应具体到能指导后续工具调用。\n"
        )
        human = (
            f"【Schema 摘要】\n\n{schema_digest}\n\n"
            f"【用户问题】\n\n{self.chat_question.question or ''}\n"
        )
        try:
            llm = await create_llm(use_tool=False)
            resp = await llm.ainvoke(
                [SystemMessage(content=system), HumanMessage(content=human)]
            )
            text = getattr(resp, "content", None) or ""
            if isinstance(text, list):
                text = "".join(
                    getattr(b, "text", str(b)) for b in text if b is not None
                )
            plan = (text or "").strip()
            if len(plan) < 80:
                return (
                    "## 执行步骤\n\n"
                    "1. 使用 `sqlbot_list_datasources` 确认可见数据源。\n"
                    "2. 对涉及库执行 `sqlbot_sync_datasource`，必要时 `read_file`/`grep` 阅读 `.sqlbot` 下 schema。\n"
                    "3. `sqlbot_sql_dialect` 确认方言后，用 `sqlbot_execute_sql_csv` 导出结果 CSV。\n"
                    "4. 复杂统计或制图用 `execute` 运行 Python 读取 `exports` 下 CSV。\n"
                    "5. 汇总结论与建议。\n"
                )
            return plan
        except Exception as e:
            SQLBotLogUtil.error(f"Data Agent 预规划失败: {e}")
            return (
                "## 执行步骤（预规划失败，采用默认步骤）\n\n"
                "请按工具顺序：列出数据源 → 同步元数据 → 读本地 schema → 方言模板 → "
                "执行 SQL 导出 CSV → 必要时 Python 分析。\n"
            )

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
            "用户消息开头包含「系统自动生成的执行规划」：必须按步骤推进，避免跳步；每步说明正在完成规划中的哪一条。",
            "阶段建议：① 确认数据源与 .sqlbot 元数据（list/sync/read_file/grep）② sqlbot_sql_dialect ③ sqlbot_execute_sql_csv 导出证据 ④ execute+Python 做复杂统计或制图。",
            "优先使用语义工具：sqlbot_list_datasources、sqlbot_sync_datasource、sqlbot_sql_dialect、sqlbot_execute_sql_csv；",
            "sqlbot_execute_sql_csv 的结果含 JSON（含 sql、preview）与 SQL 代码块，便于界面展示；复杂分析用 execute 读 exports 下 CSV。",
            "最终给用户的总结须采用报告体：先摘要，再分点发现与证据（CSV/SQL），最后建议；系统可能在结束后再次整理格式，但草稿也应条理清晰。",
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
            "sqlbot_execute_sql_csv": "执行 SQL（导出 CSV）",
            "sqlbot_sql_dialect": "查阅 SQL 方言模板",
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
            "write_todos": "更新任务列表",
            "task": "委派子任务",
        }
        base = labels.get(tool_name, tool_name)
        detail = ""
        if isinstance(tool_input, dict):
            if tool_name == "write_todos":
                tl = tool_input.get("todos")
                if isinstance(tl, list) and tl:
                    detail = f"{len(tl)} 项"
            elif tool_name == "execute":
                cmd = tool_input.get("command", tool_input.get("cmd", ""))
                if isinstance(cmd, str) and cmd:
                    line = cmd.strip().split("\n")[0]
                    sm = re.search(r"([\w./-]+\.(?:sh|py))\b", line)
                    if sm:
                        tail = line[:100] + ("…" if len(line) > 100 else "")
                        detail = f"`{sm.group(1)}` · {tail}"
                    else:
                        detail = line[:120] + ("…" if len(line) > 120 else "")
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
    def _tool_result_for_stream(
        tool_name: str, out: str, *, execute_command: str | None = None
    ) -> str:
        if tool_name.startswith("sqlbot_"):
            limit = 12000
            if len(out) > limit:
                return out[:limit] + "\n\n...（输出已截断）"
            return out
        return format_deepagent_tool_output(
            tool_name, out, execute_command=execute_command
        )

    def _evidence_from_sql_csv_tool(
        self, raw: str, tool_input, workspace_uid: str
    ) -> dict | None:
        """从 sqlbot_execute_sql_csv 工具输出中解析一条证据记录。"""
        s0 = (raw or "").strip()
        obj = _extract_first_json_object(s0)
        if obj is None:
            # 工具输出可能是 ToolMessage repr 或 Python dict repr；尽可能恢复为 dict
            try:
                import ast

                s1 = s0
                # ToolMessage repr 里 content='...'
                m = re.search(r"\bcontent=(['\"])", s1)
                if m:
                    # 复用 data_agent_tool_format 中对 ToolMessage content 的解析逻辑
                    from apps.openapi.agent.data_agent_tool_format import (
                        _extract_toolmessage_content_str as _tm_content,
                    )

                    inner = _tm_content(s1)
                    if inner:
                        s1 = inner.strip()
                if s1.startswith("{") and s1.endswith("}"):
                    try:
                        obj = json.loads(s1)
                    except json.JSONDecodeError:
                        # 可能是 Python dict 单引号
                        obj = ast.literal_eval(s1)
            except Exception:
                obj = None
        if not isinstance(obj, dict):
            return None
        step_desc = ""
        if isinstance(tool_input, dict):
            step_desc = str(tool_input.get("step_description", "") or "")[:240]
        sql = str(obj.get("sql") or "")[:2000]
        path = str(obj.get("path") or "")[:500]
        err = str(obj.get("error") or "")[:500]
        rel_path = ""
        if path:
            try:
                rel_path = str(
                    Path(path).resolve().relative_to(sw.user_dir(workspace_uid).resolve())
                )
            except ValueError:
                rel_path = ""
        cols = obj.get("columns")
        columns_out = (
            [str(x)[:200] for x in cols[:64]] if isinstance(cols, list) else None
        )
        pr = obj.get("preview_rows")
        preview_out = None
        if isinstance(pr, list):

            def _norm_cell(v):
                if v is None:
                    return None
                if isinstance(v, (int, float, str, bool)):
                    return v
                return str(v)

            def _norm_row(r):
                if isinstance(r, dict):
                    return {k: _norm_cell(v) for k, v in r.items()}
                if isinstance(r, (list, tuple)):
                    return [_norm_cell(x) for x in r]
                return _norm_cell(r)

            preview_out = [_norm_row(r) for r in pr[:20]]
        rec: dict = {
            "datasource_id": obj.get("datasource_id"),
            "row_count": obj.get("row_count"),
            "path": path,
            "rel_path": rel_path,
            "ok": obj.get("ok", True),
            "error": err,
            "sql": sql,
            "step_description": step_desc,
        }
        if columns_out is not None:
            rec["columns"] = columns_out
        if preview_out is not None:
            rec["preview_rows"] = preview_out
        return rec

    @staticmethod
    def _event_tool_name(name: str) -> str:
        """LangGraph 事件里工具名可能是 `tools/sqlbot_execute_sql_csv` 等形式。"""
        n = (name or "").strip()
        if "/" in n:
            return n.rsplit("/", 1)[-1]
        return n

    @staticmethod
    def _csv_paths_from_text(text: str) -> list[str]:
        """从 execute / 技能脚本输出里抽取 exports 下 CSV 路径（skill 常不调 sqlbot_execute_sql_csv）。"""
        if not text:
            return []
        out: list[str] = []
        seen: set[str] = set()
        for m in re.finditer(
            r"(?:CSV:\s*)?[`\"']?([^\s`\"'<>]+\.csv)[`\"']?",
            text,
            re.IGNORECASE,
        ):
            p = (m.group(1) or "").strip()
            if p and p not in seen:
                seen.add(p)
                out.append(p)
        for m in re.finditer(
            r"([^\s`\"'<>]+/exports/[a-zA-Z0-9._-]+\.csv)", text, re.IGNORECASE
        ):
            p = (m.group(1) or "").strip()
            if p and p not in seen:
                seen.add(p)
                out.append(p)
        return out

    def _evidence_from_exports_csv_file(
        self,
        raw_path: str,
        workspace_uid: str,
        *,
        step_description: str = "",
    ) -> dict | None:
        """根据工作区内已存在的 CSV 文件构造一条证据（无 SQL，用于 execute/脚本路径）。"""
        p = (raw_path or "").strip()
        if not p.lower().endswith(".csv"):
            return None
        try:
            path = Path(p).expanduser()
            if not path.is_absolute():
                path = (sw.user_dir(workspace_uid) / p).resolve()
            else:
                path = path.resolve()
        except OSError:
            return None
        base = sw.user_dir(workspace_uid).resolve()
        try:
            path.relative_to(base)
        except ValueError:
            return None
        if not path.is_file():
            return None
        rel_path = str(path.relative_to(base))
        try:
            with path.open(encoding="utf-8-sig", errors="replace", newline="") as f:
                reader = csv_module.DictReader(f)
                cols = list(reader.fieldnames or [])
                preview: list[dict] = []
                for i, row in enumerate(reader):
                    if i >= 20:
                        break
                    preview.append(
                        {k: ("" if v is None else str(v)[:500]) for k, v in row.items()}
                    )
        except Exception:
            return None
        try:
            with path.open(encoding="utf-8-sig", errors="replace", newline="") as f:
                n_lines = sum(1 for _ in f)
            row_count = max(0, n_lines - 1)
        except Exception:
            row_count = len(preview)
        rec: dict = {
            "datasource_id": None,
            "row_count": row_count,
            "path": str(path),
            "rel_path": rel_path,
            "ok": True,
            "error": "",
            "sql": "",
            "step_description": (step_description or "")[:240],
        }
        if cols:
            rec["columns"] = [str(c)[:200] for c in cols[:64]]
        if preview:
            rec["preview_rows"] = preview
        return rec

    def _merge_evidence_from_execute(
        self,
        *,
        raw_tool_output: str,
        tool_input,
        workspace_uid: str,
        evidence_log: list[dict],
    ) -> None:
        pe = parse_execute_tool_raw(raw_tool_output)
        scan_txt = pe.output or ""
        desc = ""
        if isinstance(tool_input, dict):
            c = tool_input.get("command", tool_input.get("cmd", ""))
            if isinstance(c, str) and c.strip():
                desc = c.strip().split("\n")[0][:200]
        existing: set[str] = set()
        for e in evidence_log:
            pp = e.get("path")
            if not pp:
                continue
            try:
                existing.add(str(Path(str(pp)).resolve()))
            except Exception:
                pass
        for raw_p in self._csv_paths_from_text(scan_txt):
            ev = self._evidence_from_exports_csv_file(
                raw_p, workspace_uid, step_description=desc
            )
            if not ev:
                continue
            try:
                key = str(Path(str(ev["path"])).resolve())
            except Exception:
                continue
            if key in existing:
                continue
            existing.add(key)
            ev["index"] = len(evidence_log) + 1
            evidence_log.append(ev)

    def _build_report_bundle(
        self,
        *,
        chat_id: int,
        question: str,
        report_md: str,
        evidence_json: list[dict],
    ) -> dict:
        """生成离线 HTML 的结构化数据包（可落盘复现渲染）。"""
        now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        return {
            "version": 1,
            "generated_at": now,
            "chat_id": chat_id,
            "question": (question or "").strip(),
            "report_markdown": report_md or "",
            "evidence": evidence_json or [],
        }

    async def _finalize_structured_report(
        self,
        *,
        question: str,
        plan_excerpt: str,
        evidence_log: list[dict],
        draft: str,
    ) -> str:
        """将模型草稿整理为固定章节 Markdown（对标正式分析报告）。"""
        if not getattr(settings, "DATA_AGENT_STRUCTURED_REPORT", True):
            return draft
        text = (draft or "").strip()
        if not text:
            return draft
        try:
            ev_text = json.dumps(evidence_log, ensure_ascii=False)
            if len(ev_text) > 8000:
                ev_text = ev_text[:8000] + "\n…（证据列表已截断）"
            plan_x = (plan_excerpt or "")[:6000]
            draft_x = text[:14000]
            if len(text) > 14000:
                draft_x += "\n\n…（草稿已截断，整理时请保留核心结论）"

            system = (
                "你是数据分析报告编辑。请将「分析草稿」改写为正式 Markdown 分析报告，"
                "必须使用以下章节标题（按顺序，使用 # / ##）：\n"
                "# 分析摘要\n"
                "## 数据与证据\n"
                "## 主要发现\n"
                "## 建议与后续\n"
                "## 附录（SQL 与导出索引）\n\n"
                "写作要求：\n"
                "- 「分析摘要」用 3～6 句话概括业务问题、数据范围与核心结论。\n"
                "- 「数据与证据」用 Markdown 表格或有序列表，为每条证据编号（E1,E2…），"
                "列出数据源 id、行数、CSV 路径、SQL 摘要；内容须与「证据 JSON」一致，禁止编造路径或行数。\n"
                "- 「主要发现」分条列出，每条尽量对应证据编号或 CSV 路径。\n"
                "- 「建议与后续」写可执行建议或数据/口径待办。\n"
                "- 「附录」汇总关键 SQL（可截断）与导出文件路径。\n"
                "- 禁止空洞套话；若证据不足须在摘要或发现中明确说明限制。\n"
                "- 全文使用中文。\n"
            )
            human = (
                f"用户问题：\n{question}\n\n"
                f"执行规划（摘录）：\n{plan_x}\n\n"
                f"证据 JSON：\n{ev_text}\n\n"
                f"---\n分析草稿：\n{draft_x}"
            )
            llm = await create_llm(use_tool=False)
            resp = await llm.ainvoke(
                [SystemMessage(content=system), HumanMessage(content=human)]
            )
            out = getattr(resp, "content", None) or ""
            if isinstance(out, list):
                out = "".join(getattr(b, "text", str(b)) for b in out if b is not None)
            polished = (out or "").strip()
            if len(polished) < 120:
                return draft
            return polished
        except Exception as e:
            SQLBotLogUtil.error(f"Data Agent 结构化报告失败，使用草稿: {e}")
            return draft

    async def _emit_report_stage(
        self, stage: str, status: str, message: str = ""
    ) -> None:
        await self.queue.put(
            {
                "type": "report_stage",
                "stage": stage,
                "status": status,
                "message": message,
            }
        )

    def _evidence_summary_text(self, evidence_log: list[dict]) -> str:
        lines: list[str] = []
        for ev in evidence_log:
            if not isinstance(ev, dict):
                continue
            idx = ev.get("index", "")
            lines.append(
                f"E{idx}: ds={ev.get('datasource_id')} rows={ev.get('row_count')} "
                f"path={ev.get('rel_path') or ev.get('path')} "
                f"cols={ev.get('columns')}"
            )
            sql = str(ev.get("sql") or "")
            if sql:
                lines.append("  sql: " + sql[:400].replace("\n", " "))
        return "\n".join(lines)[:12000]

    async def _report_correct(
        self, *, question: str, body: str, evidence_summary: str
    ) -> str:
        system = (
            "你是数据分析报告审校员。对照「证据摘要」检查下面 Markdown 报告中的事实、数字与结论，"
            "修正明显错误、矛盾或夸大表述；不得编造证据中不存在的路径或行数。"
            "保持原有章节结构（# 分析摘要、## 数据与证据 等）；如证据不足，将相关句改为谨慎表述。"
            "全文使用中文，直接输出修正后的完整 Markdown。"
        )
        human = (
            f"用户问题：\n{question[:4000]}\n\n"
            f"证据摘要：\n{evidence_summary}\n\n"
            f"---\n待审校报告：\n{body[:20000]}"
        )
        if len(body) > 20000:
            human += "\n\n…（报告已截断，请仅就可见部分审校并保持结构）"
        try:
            llm = await create_llm(use_tool=False)
            resp = await llm.ainvoke(
                [SystemMessage(content=system), HumanMessage(content=human)]
            )
            out = getattr(resp, "content", None) or ""
            if isinstance(out, list):
                out = "".join(
                    getattr(b, "text", str(b)) for b in out if b is not None
                )
            corrected = (out or "").strip()
            if len(corrected) < 80:
                return body
            return corrected
        except Exception as e:
            SQLBotLogUtil.error(f"Data Agent 报告纠错失败，沿用上一版: {e}")
            return body

    async def _report_polish(self, body: str) -> str:
        system = (
            "你是专业中文技术编辑。在不改变事实、数字、路径与 SQL 的前提下，润色下面 Markdown："
            "段落衔接、用词统一、标题层级清晰。禁止新增数据或结论。直接输出润色后的完整 Markdown。"
        )
        human = f"待润色报告：\n{body[:22000]}"
        try:
            llm = await create_llm(use_tool=False)
            resp = await llm.ainvoke(
                [SystemMessage(content=system), HumanMessage(content=human)]
            )
            out = getattr(resp, "content", None) or ""
            if isinstance(out, list):
                out = "".join(
                    getattr(b, "text", str(b)) for b in out if b is not None
                )
            polished = (out or "").strip()
            if len(polished) < 80:
                return body
            return polished
        except Exception as e:
            SQLBotLogUtil.error(f"Data Agent 报告润色失败，沿用上一版: {e}")
            return body

    async def _emit_buffered_llm_text(
        self, buffer_parts: list[str], *, title: str, stage_key: str
    ) -> None:
        """将工具调用间隙的 LLM 文本单独成步，避免与上一工具混在同一步里。"""
        text = "".join(buffer_parts)
        buffer_parts.clear()
        if not text.strip():
            return
        await self.queue.put(
            {
                "type": "stage",
                "content": title,
                "stage": stage_key,
                "tool": "llm",
            }
        )
        await self.queue.put(
            {
                "reasoning_content": "",
                "content": text,
                "type": "process",
            }
        )

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
            schema_digest = self._aggregate_schema_digest()
            execution_plan_md = await self._generate_data_agent_execution_plan(
                schema_digest
            )

            methodology = (
                "### 工作方法提示（data-explorer）\n\n"
                "1. **元数据** — `.sqlbot` 本地缓存与 schema 文件是生成 SQL 的依据。\n"
                "2. **证据链** — 用 `sqlbot_execute_sql_csv` 导出 CSV，再决定是否用 Python 深入分析。\n"
                "3. **界面** — 左侧为步骤时间线，右侧详情含 SQL、JSON 与命令输出；请保持步骤描述与规划一致。\n"
            )
            await self.queue.put(
                {
                    "type": "plan",
                    "content": (
                        f"**Data Agent(技能)**\n\n"
                        f"## 执行规划（系统自动生成）\n\n{execution_plan_md}\n\n"
                        f"---\n\n{methodology}\n"
                        f"**环境**\n\n"
                        f"- 工作区: `{uid}`\n"
                        f"- SQLBOT_HOME: `{sqlbot_home}`\n"
                        f"- 技能目录: `{skill_path}`\n"
                        f"- 技能: `data-explorer`\n"
                    ),
                    "plan": {
                        "mode": "data-agent",
                        "skills": ["data-explorer"],
                        "sqlbot_home": str(sqlbot_home),
                        "workspace_uid": uid,
                        "plan_source": "llm",
                        "schema_digest_chars": len(schema_digest),
                    },
                }
            )
            await self.queue.put(
                {"type": "stage", "content": "Data Agent(技能) 启动", "stage": "agent"}
            )

            agent = await self._build_agent()
            # 不再让 LLM 自由写作产出最终报告；最终交付由 evidence + bundle 渲染离线 HTML。
            # report_text 仅用于过程展示（不写入最终 report 字段）。
            report_text = ""
            evidence_log: list[dict] = []
            tc = 0
            tool_time_stack: list[float] = []
            post_tool_llm_buffer: list[str] = []
            accumulate_post_tool_llm = False
            last_execute_command: str | None = None

            user_q = (self.chat_question.question or "").strip()
            agent_user_content = (
                "系统已在界面「任务规划」中展示执行规划。请严格按该规划顺序推进；"
                "每完成规划中的关键一步，用一两句中文说明对应了规划中哪一条。\n\n"
                "---\n\n"
                "## 执行规划（与任务规划卡片一致）\n\n"
                f"{execution_plan_md}\n\n"
                "---\n\n"
                "## 用户原始问题\n\n"
                f"{user_q}\n"
            )

            async for event in agent.astream_events(
                {
                    "messages": [
                        {"role": "user", "content": agent_user_content},
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
                            report_text += text
                            if accumulate_post_tool_llm:
                                post_tool_llm_buffer.append(text)
                            else:
                                await self.queue.put(
                                    {
                                        "reasoning_content": "",
                                        "content": text,
                                        "type": "process",
                                    }
                                )

                elif kind == "on_tool_start":
                    await self._emit_buffered_llm_text(
                        post_tool_llm_buffer,
                        title="推理与生成 SQL",
                        stage_key="llm_reasoning_sql",
                    )
                    accumulate_post_tool_llm = False

                    name = event.get("name", "")
                    ename = self._event_tool_name(name)
                    inp = data.get("input", {})
                    if ename == "execute" and isinstance(inp, dict):
                        c = inp.get("command", inp.get("cmd", ""))
                        last_execute_command = c if isinstance(c, str) else None
                    elif ename == "execute":
                        last_execute_command = None
                    tool_time_stack.append(time.monotonic())
                    tc += 1
                    label = self._stage_label(ename, inp)
                    _log.info(f"  🔧 #{tc}: {ename}")
                    await self.queue.put(
                        {"type": "stage", "content": label, "stage": ename, "tool": ename}
                    )
                    await self.queue.put(
                        {
                            "reasoning_content": "",
                            "content": f"开始执行：{label}\n\n",
                            "type": "process",
                        }
                    )

                elif kind == "on_tool_end":
                    accumulate_post_tool_llm = True

                    name = event.get("name", "")
                    ename = self._event_tool_name(name)
                    out = str(data.get("output", ""))
                    tool_inp = data.get("input")
                    if ename == "sqlbot_execute_sql_csv":
                        ev = self._evidence_from_sql_csv_tool(out, tool_inp, uid)
                        if ev:
                            ev["index"] = len(evidence_log) + 1
                            evidence_log.append(ev)
                    if ename == "execute":
                        self._merge_evidence_from_execute(
                            raw_tool_output=out,
                            tool_input=tool_inp,
                            workspace_uid=uid,
                            evidence_log=evidence_log,
                        )
                    t0 = tool_time_stack.pop() if tool_time_stack else None
                    duration_ms = (
                        int((time.monotonic() - t0) * 1000) if t0 is not None else None
                    )
                    _log.info(f"  ✅ {ename} | {len(out)}c | {duration_ms}ms")
                    cmd_for_exec = last_execute_command if ename == "execute" else None
                    body = self._tool_result_for_stream(
                        ename, out, execute_command=cmd_for_exec
                    )
                    summ = tool_result_summary_line(ename, out, command=cmd_for_exec)
                    if ename == "execute":
                        last_execute_command = None
                    payload: dict = {
                        "reasoning_content": "",
                        "content": body,
                        "type": "process",
                        "tool": ename,
                    }
                    if duration_ms is not None:
                        payload["duration_ms"] = duration_ms
                    if summ:
                        payload["result_summary"] = summ
                    if ename == "write_todos":
                        todos_snap = extract_write_todos_list(out)
                        if todos_snap:
                            payload["todos"] = todos_snap
                    await self.queue.put(payload)

            # 收尾阶段：仅汇总证据并生成离线 HTML（不再展示“撰写报告/纠错/润色”等步骤）
            await self._emit_buffered_llm_text(
                post_tool_llm_buffer,
                title="汇总",
                stage_key="llm_summary",
            )
            accumulate_post_tool_llm = False

            # 最终报告：只输出 HTML（离线文件），并将证据写入 report_bundle.json
            await self.queue.put({"type": "stage", "content": "汇总证据", "stage": "report_bundle"})
            ev_json = sanitize_evidence_for_json(evidence_log)
            html_relpath: str | None = None
            html_doc = build_report_html("", ev_json, chat_id=int(self.chat_question.chat_id or 0))
            if getattr(settings, "DATA_AGENT_REPORT_WRITE_HTML_FILE", False) and (
                self.chat_question.chat_id
            ):
                da_dir = sw.user_dir(uid) / "deep_analysis" / str(self.chat_question.chat_id)
                da_dir.mkdir(parents=True, exist_ok=True)
                (da_dir / "report.html").write_text(html_doc, encoding="utf-8")
                try:
                    bundle = self._build_report_bundle(
                        chat_id=int(self.chat_question.chat_id),
                        question=user_q,
                        report_md="",
                        evidence_json=ev_json,
                    )
                    (da_dir / "report_bundle.json").write_text(
                        json.dumps(bundle, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                except Exception as e:
                    SQLBotLogUtil.error(f"写 report_bundle.json 失败: {e}")
                html_relpath = f"deep_analysis/{self.chat_question.chat_id}/report.html"

            await self.queue.put(
                {
                    "type": "stage",
                    "content": "生成 HTML 报告",
                    "stage": "report_html",
                }
            )
            await self.queue.put(
                {
                    "type": "process",
                    "content": (
                        "离线 HTML 报告已生成。\n"
                        f"- 证据条数：{len(ev_json)}\n"
                        f"- HTML 字符数：{len(html_doc)}\n"
                    ),
                }
            )
            payload = {
                "reasoning_content": "",
                "content": "",
                "type": "report",
                "evidence": ev_json,
            }
            if html_relpath:
                payload["report_html_relpath"] = html_relpath
            await self.queue.put(payload)

            await self.queue.put(
                {
                    "reasoning_content": "",
                    "content": "",
                    "type": "finish",
                    "chat_id": self.chat_question.chat_id,
                }
            )
            _log.info(f"Data Agent done: {tc} tools, report_text={len(report_text)}c")

        except Exception as e:
            _log.error(f"Data Agent error: {e}")
            import traceback

            traceback.print_exc()
            await self.queue.put(
                {
                    "reasoning_content": "",
                    "content": f"Data Agent(技能) 执行出错：{e}",
                    "type": "error",
                }
            )
