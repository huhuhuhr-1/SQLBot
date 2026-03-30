"""Data Agent 报告 HTML：离线单文件（无 CDN）+ 证据表 + 内联 SVG 预览图。"""

from __future__ import annotations

import html
import json
import math
import re
from typing import Any


def _try_parse_number(s: str) -> float | None:
    t = (s or "").strip().replace(",", "")
    if not t:
        return None
    t = t.rstrip("%")
    try:
        v = float(t)
        if v != v or abs(v) == float("inf"):
            return None
        return v
    except ValueError:
        return None


def _normalize_preview_row(row: Any, columns: list[str]) -> list[str]:
    if isinstance(row, dict):
        return [str(row.get(c, ""))[:500] for c in columns]
    if isinstance(row, (list, tuple)):
        lst = list(row)
        while len(lst) < len(columns):
            lst.append("")
        return [str(x)[:500] for x in lst[: len(columns)]]
    return [str(row)[:500]] + [""] * max(0, len(columns) - 1)


def _pick_numeric_series_from_preview(
    ev: dict[str, Any],
) -> tuple[str, list[str], list[float]] | None:
    """从 preview_rows 中挑一个数值列作为 Y，并挑一个列作为 X（类别/时间）。"""
    cols = ev.get("columns")
    rows_raw = ev.get("preview_rows")
    if not isinstance(cols, list) or not cols:
        return None
    if not isinstance(rows_raw, list) or len(rows_raw) < 2:
        return None
    columns = [str(c) for c in cols[:48]]
    data_rows = [_normalize_preview_row(r, columns) for r in rows_raw[:30]]
    if len(data_rows) < 2:
        return None

    val_i: int | None = None
    best_ok = 0
    for j in range(len(columns)):
        parsed = [_try_parse_number(r[j] if j < len(r) else "") for r in data_rows]
        ok = sum(1 for x in parsed if x is not None)
        if ok > best_ok and ok >= max(2, len(parsed) // 2):
            best_ok = ok
            val_i = j
    if val_i is None:
        return None

    cat_i = 0 if val_i != 0 else (1 if len(columns) > 1 else 0)
    x: list[str] = []
    y: list[float] = []
    for i, r in enumerate(data_rows):
        cat = str(r[cat_i])[:80] if cat_i < len(r) else ""
        x.append(cat or f"#{i + 1}")
        v = _try_parse_number(r[val_i] if val_i < len(r) else "")
        if v is None:
            continue
        y.append(float(v))
    if len(y) < 2:
        return None
    return str(columns[val_i])[:64], x[: len(y)], y


def _svg_bar_chart(
    *,
    title: str,
    x: list[str],
    y: list[float],
    width: int = 920,
    height: int = 240,
) -> str:
    if not x or not y:
        return ""
    n = min(len(x), len(y), 18)
    x = x[:n]
    y = y[:n]
    y_max = max(y) if y else 1.0
    if not math.isfinite(y_max) or y_max == 0:
        y_max = 1.0
    pad = 28
    w = width
    h = height
    inner_w = w - pad * 2
    inner_h = h - pad * 2
    bar_gap = 6
    bar_w = max(6, int((inner_w - bar_gap * (n - 1)) / max(1, n)))
    parts = [
        f'<svg viewBox="0 0 {w} {h}" width="100%" height="{h}" role="img" aria-label="{html.escape(title)}">',
        f'<text x="{pad}" y="{pad - 10}" class="svg-title">{html.escape(title)}</text>',
        f'<line x1="{pad}" y1="{h - pad}" x2="{w - pad}" y2="{h - pad}" class="svg-axis" />',
    ]
    for i in range(n):
        v = y[i]
        bh = 0 if y_max <= 0 else int(inner_h * (max(0.0, v) / y_max))
        x0 = pad + i * (bar_w + bar_gap)
        y0 = h - pad - bh
        parts.append(
            f'<rect x="{x0}" y="{y0}" width="{bar_w}" height="{bh}" rx="3" class="svg-bar"></rect>'
        )
        label = x[i]
        parts.append(
            f'<text x="{x0 + bar_w / 2}" y="{h - pad + 14}" class="svg-x" text-anchor="middle">{html.escape(label[:10])}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _basic_markdown_to_html(md: str) -> str:
    """
    轻量 Markdown 渲染：仅覆盖 DataAgent 报告常见结构（标题/列表/代码块/表格/段落）。
    目的：离线无 JS 依赖，同时避免全文变成 <pre> 影响观感。
    """
    text = (md or "").strip()
    if not text:
        return ""

    lines = text.splitlines()
    out: list[str] = []
    in_code = False
    code_lang = ""
    code_buf: list[str] = []
    table_buf: list[str] = []
    in_ul = False
    in_ol = False

    def _flush_code():
        nonlocal in_code, code_lang, code_buf
        if not in_code:
            return
        code = "\n".join(code_buf)
        out.append(
            '<pre class="code"><code>'
            + html.escape(code)
            + "</code></pre>"
        )
        in_code = False
        code_lang = ""
        code_buf = []

    def _flush_table():
        nonlocal table_buf
        if not table_buf:
            return
        rows = [r for r in table_buf if r.strip().startswith("|")]
        table_buf = []
        if len(rows) < 2:
            return
        # 跳过分隔行（第二行通常是 | --- |）
        def _split_row(r: str) -> list[str]:
            core = r.strip().strip("|")
            return [c.strip() for c in core.split("|")]

        head = _split_row(rows[0])
        body_rows = []
        for r in rows[1:]:
            cells = _split_row(r)
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                continue
            body_rows.append(cells)
        if not head:
            return
        th = "".join(f"<th>{html.escape(c)}</th>" for c in head[:24])
        trs = []
        for r in body_rows[:40]:
            tds = "".join(f"<td>{html.escape(c)}</td>" for c in r[:24])
            trs.append(f"<tr>{tds}</tr>")
        out.append(
            '<div class="table-wrap"><table class="md-table"><thead><tr>'
            + th
            + "</tr></thead><tbody>"
            + "".join(trs)
            + "</tbody></table></div>"
        )

    def _close_lists():
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    for line in lines:
        if line.strip().startswith("```"):
            if in_code:
                _flush_code()
            else:
                _flush_table()
                _close_lists()
                in_code = True
                code_lang = line.strip().lstrip("`").strip()
                code_buf = []
            continue
        if in_code:
            code_buf.append(line)
            continue

        if line.strip().startswith("|") and "|" in line.strip()[1:]:
            table_buf.append(line)
            continue
        if table_buf and not line.strip():
            _flush_table()
            continue

        m = re.match(r"^(#{1,3})\s+(.*)$", line.strip())
        if m:
            _flush_table()
            _close_lists()
            lvl = len(m.group(1))
            title = m.group(2).strip()
            lvl = min(3, max(1, lvl))
            out.append(f"<h{lvl}>{html.escape(title)}</h{lvl}>")
            continue

        m = re.match(r"^\s*[-*]\s+(.*)$", line)
        if m:
            _flush_table()
            if in_ol:
                out.append("</ol>")
                in_ol = False
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{html.escape(m.group(1).strip())}</li>")
            continue

        m = re.match(r"^\s*\d+\.\s+(.*)$", line)
        if m:
            _flush_table()
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{html.escape(m.group(1).strip())}</li>")
            continue

        if not line.strip():
            _flush_table()
            _close_lists()
            continue

        _flush_table()
        _close_lists()
        out.append(f"<p>{html.escape(line.strip())}</p>")

    _flush_table()
    _flush_code()
    _close_lists()
    return "\n".join(out)


def build_report_html(
    markdown_body: str,
    evidence: list[dict[str, Any]],
    *,
    chat_id: int,
) -> str:
    """生成离线单文件 HTML（无 CDN），包含证据表与 SVG 图表预览。"""
    safe_chat = int(chat_id)

    evidence_blocks: list[str] = []

    for i, ev in enumerate(evidence or []):
        if not isinstance(ev, dict):
            continue
        idx = ev.get("index", i + 1)
        head = f"<h3 id=\"ev-{i}\">证据 E{html.escape(str(idx))}</h3>"
        meta_parts = [
            f"<p><strong>数据源</strong>：{html.escape(str(ev.get('datasource_id', '—')))} &nbsp; "
            f"<strong>行数</strong>：{html.escape(str(ev.get('row_count', '—')))}</p>"
        ]
        rp = ev.get("rel_path") or ev.get("path") or ""
        if rp:
            meta_parts.append(
                f"<p><strong>导出文件（相对工作区）</strong>：<code>{html.escape(str(rp))}</code></p>"
            )
        sql = str(ev.get("sql") or "")
        if sql:
            meta_parts.append(
                "<details><summary>SQL（可折叠）</summary><pre>"
                + html.escape(sql[:8000])
                + ("…" if len(sql) > 8000 else "")
                + "</pre></details>"
            )

        cols = ev.get("columns")
        prev = ev.get("preview_rows")
        table_html = ""
        if isinstance(cols, list) and cols and isinstance(prev, list) and prev:
            col_names = [str(c) for c in cols[:24]]
            th = "".join(f"<th>{html.escape(str(c))}</th>" for c in col_names)
            trs = []
            for row in prev[:25]:
                cells = _normalize_preview_row(row, col_names)
                tds = "".join(f"<td>{html.escape(str(c))}</td>" for c in cells)
                trs.append(f"<tr>{tds}</tr>")
            table_html = (
                '<div class="table-wrap"><table><thead><tr>'
                + th
                + "</tr></thead><tbody>"
                + "".join(trs)
                + "</tbody></table></div>"
            )

        chart_block = ""
        picked = _pick_numeric_series_from_preview(ev)
        if picked:
            y_name, x_vals, y_vals = picked
            title = f"证据 E{idx} · {y_name}（预览）"
            chart_block = '<div class="chart">' + _svg_bar_chart(
                title=title, x=x_vals, y=y_vals
            ) + "</div>"

        evidence_blocks.append(
            '<section class="evidence-card">'
            + head
            + "".join(meta_parts)
            + table_html
            + chart_block
            + "</section>"
        )

    evidence_html = "\n".join(evidence_blocks)
    md_html = _basic_markdown_to_html(markdown_body or "")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>深度分析报告 #{safe_chat}</title>
  <style>
    :root {{
      --bg: #0b0f14;
      --paper: rgba(255,255,255,0.06);
      --paper2: rgba(255,255,255,0.08);
      --text: rgba(255,255,255,0.92);
      --muted: rgba(255,255,255,0.65);
      --line: rgba(255,255,255,0.12);
      --accent: #7cf7c5;
      --danger: #ff6b6b;
    }}
    body {{
      margin: 0;
      padding: 28px 18px 56px;
      background: radial-gradient(1200px 800px at 15% 10%, rgba(124,247,197,0.14), transparent 55%),
                  radial-gradient(1000px 600px at 80% 30%, rgba(255,107,107,0.10), transparent 55%),
                  var(--bg);
      color: var(--text);
      font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      line-height: 1.55;
    }}
    .container {{
      max-width: 1120px;
      margin: 0 auto;
    }}
    h1 {{
      font-size: 1.55rem;
      margin: 0 0 6px;
      letter-spacing: 0.5px;
    }}
    .muted {{ color: var(--muted); font-size: 0.92rem; margin: 0 0 18px; }}
    .grid {{
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      gap: 16px;
    }}
    @media (max-width: 980px) {{
      .grid {{ grid-template-columns: 1fr; }}
    }}
    .card {{
      background: linear-gradient(180deg, var(--paper2), var(--paper));
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 18px 18px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.25);
    }}
    .card h2 {{
      margin: 0 0 12px;
      font-size: 1.06rem;
      color: var(--accent);
      letter-spacing: 0.4px;
    }}
    .md h1, .md h2, .md h3 {{
      margin: 14px 0 10px;
      border-bottom: 1px solid var(--line);
      padding-bottom: 8px;
    }}
    .md p {{ margin: 10px 0; color: var(--text); }}
    .md ul, .md ol {{ margin: 8px 0 12px 18px; color: var(--text); }}
    .code {{
      background: rgba(0,0,0,0.35);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px 14px;
      overflow-x: auto;
      font-size: 0.86rem;
      color: rgba(255,255,255,0.88);
    }}
    .table-wrap {{ overflow-x: auto; margin: 12px 0; }}
    table {{
      border-collapse: collapse;
      width: 100%;
      min-width: 680px;
      font-size: 0.88rem;
    }}
    th, td {{
      border: 1px solid var(--line);
      padding: 7px 8px;
      vertical-align: top;
      color: rgba(255,255,255,0.86);
    }}
    th {{
      background: rgba(124,247,197,0.10);
      color: rgba(255,255,255,0.92);
      font-weight: 600;
    }}
    .evidence-card {{
      background: linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.05));
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px 16px;
      margin: 14px 0;
    }}
    .evidence-card h3 {{
      margin: 0 0 10px;
      font-size: 1.02rem;
      color: rgba(255,255,255,0.92);
    }}
    details > summary {{
      cursor: pointer;
      color: var(--accent);
      margin: 6px 0;
    }}
    code {{ color: rgba(255,255,255,0.9); }}
    .chart {{
      margin-top: 10px;
      padding: 10px 12px;
      border-radius: 12px;
      border: 1px solid var(--line);
      background: rgba(0,0,0,0.20);
    }}
    .svg-title {{ fill: rgba(255,255,255,0.85); font-size: 13px; font-weight: 600; }}
    .svg-axis {{ stroke: rgba(255,255,255,0.22); stroke-width: 1; }}
    .svg-bar {{ fill: rgba(124,247,197,0.75); }}
    .svg-x {{ fill: rgba(255,255,255,0.70); font-size: 11px; }}
    .footer {{
      margin-top: 18px;
      color: var(--muted);
      font-size: 0.9rem;
    }}
  </style>
</head>
<body>
  <div class="container">
    <h1>深度分析报告</h1>
    <p class="muted">会话 ID：{safe_chat} · 本文件为离线单页 HTML（无需外网/CDN/服务端）。</p>

    <div class="grid">
      <section class="card md">
        <h2>报告正文</h2>
        {md_html or '<p class="muted">（无报告正文）</p>'}
      </section>

      <aside class="card">
        <h2>证据概览</h2>
        <p class="muted">证据条数：{len(evidence or [])}（每条仅展示预览行，用于离线快速阅读）</p>
        <div class="footer">建议：正文结论尽量引用证据编号（E1/E2…）以便追溯。</div>
      </aside>
    </div>

    <section class="card" style="margin-top:16px;">
      <h2>数据证据与预览</h2>
      {evidence_html or '<p class="muted">（无结构化证据记录：请检查是否使用了 sqlbot_execute_sql_csv 导出 CSV）</p>'}
      <div class="footer">附录说明：导出 CSV 路径相对于 SQLBOT_HOME 下账号工作区根目录。</div>
    </section>
  </div>
</body>
</html>
"""


def sanitize_evidence_for_json(log: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """缩小 evidence 体积，便于写入 ChatRecord.analysis。"""
    out: list[dict[str, Any]] = []
    for e in log:
        if not isinstance(e, dict):
            continue
        row = dict(e)
        pr = row.get("preview_rows")
        cols = row.get("columns")
        if isinstance(pr, list) and isinstance(cols, list):
            col_list = [str(c) for c in cols]
            slim: list[Any] = []
            for r in pr[:20]:
                slim.append(_normalize_preview_row(r, col_list) if col_list else r)
            row["preview_rows"] = slim
        elif isinstance(pr, list):
            row["preview_rows"] = pr[:20]
        cols2 = row.get("columns")
        if isinstance(cols2, list):
            row["columns"] = [str(c)[:160] for c in cols2[:64]]
        for k in ("sql", "step_description", "error"):
            if k in row and isinstance(row[k], str) and len(row[k]) > 4000:
                row[k] = row[k][:4000] + "…"
        out.append(row)
    return out
