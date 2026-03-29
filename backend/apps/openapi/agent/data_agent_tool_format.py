"""将 DeepAgents / LangChain 工具原始输出格式化为 Markdown，避免整段 repr 塞进代码块。"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from typing import Any

_NAME_TAIL = re.compile(r"\s*name\s*=")


def _scan_quoted_until_name_field(raw: str, start: int, q: str) -> str | None:
    """
    扫描 LangChain ToolMessage 风格：content='...' name='read_file'
    结束引号必须是「后跟 name=」的那一个，避免正文里未转义的单引号提前截断。
    """
    i = start
    parts: list[str] = []
    esc = False
    n = len(raw)
    while i < n:
        c = raw[i]
        if esc:
            if c == "n":
                parts.append("\n")
            elif c == "t":
                parts.append("\t")
            elif c == "r":
                parts.append("\r")
            elif c in (q, "\\"):
                parts.append(c)
            else:
                parts.append("\\")
                parts.append(c)
            esc = False
            i += 1
            continue
        if c == "\\":
            esc = True
            i += 1
            continue
        if c == q:
            tail = raw[i + 1 : min(n, i + 64)]
            if _NAME_TAIL.match(tail):
                return "".join(parts)
        parts.append(c)
        i += 1
    return None


def _extract_toolmessage_content_str(raw: str) -> str | None:
    m = re.search(r"\bcontent=(['\"])", raw)
    if not m:
        return None
    q = m.group(1)
    body = _scan_quoted_until_name_field(raw, m.end(), q)
    return body


def _parse_content_body_literal_or_str(raw: str) -> Any:
    """content 正文：若是 Python list/dict 字面量则解析，否则视为纯文本（如 read_file）。"""
    body = _extract_toolmessage_content_str(raw)
    if body is None:
        raise ValueError("no content=")
    try:
        return ast.literal_eval(body.strip())
    except (SyntaxError, ValueError, TypeError):
        return body


def _normalize_todo_items_for_api(items: list[Any]) -> list[dict[str, str]] | None:
    out: list[dict[str, str]] = []
    for item in items:
        if isinstance(item, dict):
            c = item.get("content")
            st = item.get("status", "")
            if c is not None:
                out.append(
                    {
                        "content": str(c),
                        "status": str(st) if st is not None else "",
                    }
                )
    return out if out else None


def _slice_balanced_square(s: str, open_idx: int) -> str | None:
    """从 open_idx 处的 '[' 起截取平衡的 [...] 子串（忽略字符串内的括号）。"""
    if open_idx < 0 or open_idx >= len(s) or s[open_idx] != "[":
        return None
    depth = 0
    in_str: str | None = None
    esc = False
    i = open_idx
    while i < len(s):
        c = s[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == in_str:
                in_str = None
            i += 1
            continue
        if c in ('"', "'"):
            in_str = c
            i += 1
            continue
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return s[open_idx : i + 1]
        i += 1
    return None


def extract_write_todos_list(raw: str | None) -> list[dict[str, str]] | None:
    """从 write_todos 工具原始输出中解析 [{content, status}, ...]。"""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None

    def _try_list(obj: Any) -> list[dict[str, str]] | None:
        if isinstance(obj, list):
            return _normalize_todo_items_for_api(obj)
        if isinstance(obj, dict):
            t = obj.get("todos")
            if isinstance(t, list):
                return _normalize_todo_items_for_api(t)
        return None

    try:
        parsed = _parse_content_body_literal_or_str(s)
        got = _try_list(parsed)
        if got:
            return got
        if isinstance(parsed, str):
            st = parsed.strip()
            if st.startswith("[") and st.endswith("]"):
                try:
                    inner = ast.literal_eval(st)
                    got = _try_list(inner)
                    if got:
                        return got
                except (SyntaxError, ValueError, TypeError):
                    pass
    except ValueError:
        pass

    body = _extract_toolmessage_content_str(s)
    if body is not None:
        try:
            inner = ast.literal_eval(body.strip())
            got = _try_list(inner)
            if got:
                return got
        except (SyntaxError, ValueError, TypeError):
            pass
        b = body.strip()
        if b.startswith("[") and b.endswith("]"):
            try:
                inner = ast.literal_eval(b)
                got = _try_list(inner)
                if got:
                    return got
            except (SyntaxError, ValueError, TypeError):
                pass

    marker = "Updated todo list to "
    mi = s.find(marker)
    if mi >= 0:
        br = s.find("[", mi + len(marker))
        if br >= 0:
            chunk = _slice_balanced_square(s, br)
            if chunk:
                try:
                    inner = ast.literal_eval(chunk)
                    got = _try_list(inner)
                    if got:
                        return got
                except (SyntaxError, ValueError, TypeError):
                    pass

    for needle in ("'todos':", '"todos":', "'todos' :", '"todos" :'):
        ti = s.find(needle)
        if ti >= 0:
            br = s.find("[", ti + len(needle))
            if br >= 0:
                chunk = _slice_balanced_square(s, br)
                if chunk:
                    try:
                        inner = ast.literal_eval(chunk)
                        got = _try_list(inner)
                        if got:
                            return got
                    except (SyntaxError, ValueError, TypeError):
                        pass

    return None


_LINE_NUM_PREFIX = re.compile(r"^\s*\d+\t")


def _beautify_schema_dump(text: str) -> str:
    """将 full_table_schema 类文本改成更易读的 Markdown（去掉行号列如 `     3\\t`）。"""
    lines = text.splitlines()
    out: list[str] = []
    for line in lines:
        core = _LINE_NUM_PREFIX.sub("", line)
        ls = core.lstrip()
        if ls.startswith("# Table:"):
            out.append("")
            out.append("### " + ls[2:].strip())
        elif ls.startswith("【") and "】" in ls:
            out.append(f"**{ls}**")
        elif ls in ("[", "]"):
            out.append(f"- `{ls}`")
        elif ls.startswith("(") and ")" in ls:
            out.append(f"- `{ls}`")
        else:
            out.append(core if core.strip() else line)
    return "\n".join(out)


@dataclass
class ParsedExecute:
    output: str
    exit_code: int | None
    truncated: bool


def _scan_quoted_value_with_escapes(
    source: str, start: int, q: str
) -> tuple[str, int] | None:
    """扫描 source[start:] 处开始的引号串，返回 (解码后内容, 闭合引号后的下标)。"""
    i = start
    parts: list[str] = []
    esc = False
    n = len(source)
    while i < n:
        c = source[i]
        if esc:
            if c == "n":
                parts.append("\n")
            elif c == "t":
                parts.append("\t")
            elif c == "r":
                parts.append("\r")
            elif c in (q, "\\"):
                parts.append(c)
            else:
                parts.append("\\")
                parts.append(c)
            esc = False
        elif c == "\\":
            esc = True
            i += 1
            continue
        elif c == q:
            return "".join(parts), i + 1
        else:
            parts.append(c)
        i += 1
    return None


def _parse_execute_response_repr(inner: str) -> tuple[str, int | None, bool] | None:
    """解析 `ExecuteResponse(output='...', exit_code=0, truncated=False)` 字面量。"""
    s = inner.strip()
    if not s.startswith("ExecuteResponse(") or not s.endswith(")"):
        return None
    rest = s[len("ExecuteResponse(") : -1].strip()
    if not rest.startswith("output="):
        return None
    idx = len("output=")
    q = rest[idx]
    if q not in "\"'":
        return None
    scanned = _scan_quoted_value_with_escapes(rest, idx + 1, q)
    if scanned is None:
        return None
    out_str, pos = scanned
    tail = rest[pos:].lstrip()
    if not tail.startswith(","):
        return None
    tail = tail[1:].lstrip()
    if not tail.startswith("exit_code="):
        return None
    tail = tail[len("exit_code=") :].strip()
    ec_m = re.match(r"(-?\d+|None)", tail)
    if not ec_m:
        return None
    exit_code: int | None
    if ec_m.group(1) == "None":
        exit_code = None
    else:
        exit_code = int(ec_m.group(1))
    tail = tail[ec_m.end() :].lstrip()
    if not tail.startswith(","):
        return None
    tail = tail[1:].lstrip()
    if not tail.startswith("truncated="):
        return None
    tail = tail[len("truncated=") :].strip()
    tr_m = re.match(r"(True|False)\s*$", tail)
    if not tr_m:
        return None
    truncated = tr_m.group(1) == "True"
    return out_str, exit_code, truncated


def parse_execute_tool_raw(raw: str) -> ParsedExecute:
    """统一解析 execute 工具原始字符串（含 ToolMessage / ExecuteResponse / 纯文本）。"""
    inner = _extract_toolmessage_content_str(raw)
    body = (inner if inner is not None else raw).strip()

    parsed = _parse_execute_response_repr(body)
    if parsed:
        out, code, trunc = parsed
        return ParsedExecute(out, code, trunc)

    out = body
    code: int | None = None
    m = re.search(r"\n\nExit code:\s*(-?\d+)\s*$", out)
    if m:
        code = int(m.group(1))
        out = out[: m.start()].rstrip()
    return ParsedExecute(out, code, False)


def format_execute_markdown(raw: str, command: str | None) -> str:
    pe = parse_execute_tool_raw(raw)
    parts: list[str] = []
    if command and str(command).strip():
        cmd = str(command).strip()
        if len(cmd) > 8000:
            cmd = cmd[:8000] + "\n\n…（命令已截断）"
        parts.append(f"**命令**\n\n```bash\n{cmd}\n```\n")
    if pe.exit_code is not None:
        ok = pe.exit_code == 0
        parts.append(
            f"**执行状态**：{'成功' if ok else '失败'} · 退出码 `{pe.exit_code}`"
        )
    else:
        parts.append("**执行状态**：已完成（无退出码信息）")
    if pe.truncated:
        parts.append("\n> 输出已被后端截断（体积上限）。")
    out_show = (
        pe.output if len(pe.output) <= 12000 else pe.output[:12000] + "\n\n…（截断）"
    )
    parts.append(f"\n**控制台输出**\n\n```text\n{out_show}\n```\n")
    return "\n".join(parts)


def execute_result_summary_line(raw: str, command: str | None = None) -> str:
    pe = parse_execute_tool_raw(raw)
    if pe.exit_code == 0:
        hint = "成功"
    elif pe.exit_code is not None:
        hint = f"退出码 {pe.exit_code}"
    else:
        hint = "已完成"
    n = len(pe.output or "")
    bits = [hint]
    if pe.truncated:
        bits.append("输出已截断")
    if n > 0:
        bits.append(f"约 {n} 字符")
    if command:
        c0 = str(command).strip().split("\n")[0]
        script_m = re.search(r"([\w./-]+\.(?:sh|py))\b", c0)
        if script_m:
            bits.insert(0, f"`{script_m.group(1)}`")
    return " · ".join(bits)


def _extract_first_json_object(s: str) -> Any | None:
    """从「前文 + JSON + 后文」中取出第一个顶层 JSON 对象（如 step_description 前缀 + JSON + sql 代码块）。"""
    i = s.find("{")
    if i < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    str_q = ""
    for j in range(i, len(s)):
        c = s[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == str_q:
                in_str = False
            continue
        if c in "\"'":
            in_str = True
            str_q = c
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(s[i : j + 1])
                except json.JSONDecodeError:
                    return None
    return None


def _sqlbot_result_summary_line(tool_name: str, raw: str) -> str | None:
    s = raw.strip()
    if len(s) > 50000:
        s = s[:50000]
    obj: Any | None = None
    try:
        obj = json.loads(s)
    except json.JSONDecodeError:
        inner = _extract_toolmessage_content_str(s)
        if inner is not None:
            try:
                obj = json.loads(inner.strip())
            except (json.JSONDecodeError, TypeError):
                obj = None
        if obj is None:
            obj = _extract_first_json_object(s)
    if obj is None:
        return None
    if isinstance(obj, list) and tool_name == "sqlbot_list_datasources":
        return f"{len(obj)} 个数据源"
    if not isinstance(obj, dict):
        return None
    if tool_name == "sqlbot_sync_datasource":
        if obj.get("ok"):
            t = obj.get("tables")
            name = obj.get("name") or ""
            if isinstance(t, int):
                return f"已同步 · {t} 张表" + (f" · {name}" if name else "")
            return "已同步"
        return "同步未成功"
    if tool_name == "sqlbot_list_datasources":
        arr = obj.get("datasources") or obj.get("items") or obj.get("data")
        if isinstance(arr, list):
            return f"{len(arr)} 个数据源"
    if tool_name == "sqlbot_execute_sql_csv":
        path = obj.get("path") or obj.get("csv_path") or obj.get("file")
        row_count = obj.get("row_count")
        if row_count is None:
            row_count = obj.get("rows")
        bits = []
        if obj.get("ok") is False:
            bits.append("执行失败")
        else:
            bits.append("已导出 CSV")
        if path:
            bits.append(str(path).split("/")[-1][:40])
        if isinstance(row_count, int):
            bits.append(f"{row_count} 行")
        return " · ".join(bits)
    if tool_name == "sqlbot_sql_dialect":
        return "已获取方言模板"
    return None


def tool_result_summary_line(
    tool_name: str, raw: str, *, command: str | None = None
) -> str | None:
    if tool_name == "execute":
        return execute_result_summary_line(raw, command)
    if tool_name.startswith("sqlbot_"):
        return _sqlbot_result_summary_line(tool_name, raw)
    return None


def format_deepagent_tool_output(
    tool_name: str,
    raw: str,
    *,
    max_chars: int = 24000,
    execute_command: str | None = None,
) -> str:
    s = (raw or "").strip()
    if tool_name != "execute" and len(s) > max_chars:
        s = s[:max_chars] + "\n\n…（输出已截断）"

    if tool_name == "ls":
        try:
            parsed = _parse_content_body_literal_or_str(s)
        except ValueError:
            parsed = None
        if isinstance(parsed, list):
            lines = "\n".join(f"- `{x}`" for x in parsed)
            return f"**目录内容**（共 {len(parsed)} 项）\n\n{lines}\n"

    if tool_name in ("read_file", "grep", "glob"):
        try:
            parsed = _parse_content_body_literal_or_str(s)
        except ValueError:
            parsed = None
        if isinstance(parsed, str) and parsed:
            if len(parsed) > 16000:
                parsed = parsed[:16000] + "\n\n…（截断）"
            if tool_name == "read_file" and (
                "# Table:" in parsed or "【DB_ID】" in parsed or "【Schema】" in parsed
            ):
                pretty = _beautify_schema_dump(parsed)
                return f"**read_file · 表结构摘要**\n\n{pretty}\n"
            return f"**{tool_name} 内容**\n\n```text\n{parsed}\n```\n"

    if tool_name == "write_todos":
        try:
            parsed = _parse_content_body_literal_or_str(s)
        except ValueError:
            parsed = None
        if isinstance(parsed, list):
            items = []
            for i, item in enumerate(parsed, 1):
                if isinstance(item, dict):
                    st = item.get("status", "")
                    cnt = item.get("content", str(item))
                    items.append(f"{i}. [{st}] {cnt}")
                else:
                    items.append(f"{i}. {item}")
            return "**任务列表**\n\n" + "\n".join(items) + "\n"

    if tool_name == "execute":
        if s.startswith("{") and s.endswith("}"):
            try:
                obj = json.loads(s)
                extra = ""
                if execute_command and str(execute_command).strip():
                    extra = f"**命令**\n\n```bash\n{str(execute_command).strip()[:8000]}\n```\n\n"
                return extra + (
                    "**命令输出**\n\n```json\n"
                    + json.dumps(obj, ensure_ascii=False, indent=2)
                    + "\n```\n"
                )
            except json.JSONDecodeError:
                pass
        return format_execute_markdown(s, execute_command)

    stripped = s.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            obj = json.loads(stripped)
            return (
                f"**{tool_name} 输出**\n\n```json\n"
                + json.dumps(obj, ensure_ascii=False, indent=2)
                + "\n```\n"
            )
        except json.JSONDecodeError:
            pass

    # 兜底：整块作为文本，不用「1000 字符」硬切
    show = s if len(s) <= 12000 else s[:12000] + "\n\n…（截断）"
    return f"**{tool_name} 输出**\n\n```text\n{show}\n```\n"
