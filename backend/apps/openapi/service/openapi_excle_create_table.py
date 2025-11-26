import asyncio
import json
import re
import traceback
from typing import List, Optional, Tuple, Dict, Any

import pandas as pd
from sqlalchemy import text
from fastapi import HTTPException
from pydantic import BaseModel, Field
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser

from dateutil import parser as dtparser
import datetime as _dt

from apps.openapi.llm.my_llm import LLMManager
from common.utils.utils import SQLBotLogUtil  # 确保存在


# =========================
# 工具：PG 类型判断
# =========================
def _is_timestamp_pgtype(pg_type: str) -> bool:
    t = (pg_type or "").lower().strip()
    return "timestamp" in t


def _is_date_pgtype(pg_type: str) -> bool:
    t = (pg_type or "").lower().strip()
    return t == "date"


def _is_time_pgtype(pg_type: str) -> bool:
    t = (pg_type or "").lower().strip()
    return t == "time"


def _is_integer_pgtype(pg_type: str) -> bool:
    t = (pg_type or "").lower().strip()
    return t in {"smallint", "integer", "bigint", "int2", "int4", "int8"}


def _is_numeric_pgtype(pg_type: str) -> bool:
    t = (pg_type or "").lower().strip()
    return ("numeric" in t) or (t in {"decimal", "real", "double precision", "float", "float4", "float8"})


def _is_boolean_pgtype(pg_type: str) -> bool:
    t = (pg_type or "").lower().strip()
    return t == "boolean"


# =========================
# 工具：值级别清洗与规范化
# =========================
def _normalize_to_str_ts(value) -> Optional[str]:
    """规范为 'YYYY-MM-DD HH:MM:SS' 字符串；尽力解析各种格式"""
    if value is None:
        return None
    s = str(value).strip()
    if s == "" or s.lower() in {"nan", "nat", "none", "null"}:
        return None

    # pandas/datetime 直接格式化
    try:
        if hasattr(value, "to_pydatetime"):
            dt = value.to_pydatetime()
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(value, _dt.datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(value, _dt.date):
            return _dt.datetime(value.year, value.month, value.day).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass

    # Excel 序列号（按天）
    try:
        if isinstance(value, (int, float)) or s.replace(".", "", 1).isdigit():
            num = float(value)
            if 59 <= num <= 100000:
                dt = pd.to_datetime(num, unit="D", origin="1899-12-30", errors="raise")
                return dt.to_pydatetime().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass

    # 只有“年-月/年.月/年/月”的情况默认补 01 日
    try:
        ym_like = False
        if re.fullmatch(r"\d{4}[-/.]\d{1,2}", s) or ("年" in s and "日" not in s and "号" not in s):
            ym_like = True
        if ym_like:
            dt = dtparser.parse(s, default=_dt.datetime(1970, 1, 1))
            return dt.strftime("%Y-%m-%d %H:%M:%S")

        dt = dtparser.parse(s, default=_dt.datetime(1970, 1, 1))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        # 返回原值字符串，让后续降级策略接管
        return s


def _normalize_to_str_date(value) -> Optional[str]:
    """规范为 'YYYY-MM-DD' 字符串；尽力解析各种格式"""
    if value is None:
        return None
    s = str(value).strip()
    if s == "" or s.lower() in {"nan", "nat", "none", "null"}:
        return None
    try:
        if hasattr(value, "to_pydatetime"):
            d = value.to_pydatetime().date()
            return d.strftime("%Y-%m-%d")
        if isinstance(value, _dt.datetime):
            return value.date().strftime("%Y-%m-%d")
        if isinstance(value, _dt.date):
            return value.strftime("%Y-%m-%d")
    except Exception:
        pass
    try:
        # Excel 序列号
        if isinstance(value, (int, float)) or s.replace(".", "", 1).isdigit():
            num = float(value)
            if 59 <= num <= 100000:
                dt = pd.to_datetime(num, unit="D", origin="1899-12-30", errors="raise")
                return dt.date().strftime("%Y-%m-%d")
    except Exception:
        pass
    try:
        d = dtparser.parse(s, default=_dt.datetime(1970, 1, 1)).date()
        return d.strftime("%Y-%m-%d")
    except Exception:
        return s


def _coerce_boolean(v) -> Optional[bool]:
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in {"true", "t", "1", "y", "yes", "是", "对", "真"}:
        return True
    if s in {"false", "f", "0", "n", "no", "否", "错", "假"}:
        return False
    return None  # 交由降级策略


def _coerce_integer(v) -> Optional[int]:
    if v is None or str(v).strip() == "":
        return None
    s = str(v).strip().replace(",", "")  # 去千分位
    if s.endswith("%"):
        return None
    # 先尝试浮转整，兼容 "12.0"
    try:
        f = float(s)
        if abs(f - round(f)) < 1e-9:
            return int(round(f))
    except Exception:
        pass
    try:
        return int(s)
    except Exception:
        return None


def _coerce_numeric(v) -> Optional[float]:
    if v is None or str(v).strip() == "":
        return None
    s = str(v).strip().replace(",", "")  # 去千分位
    try:
        if s.endswith("%"):
            s = s[:-1].strip()
            return float(s) / 100.0
        # 会计负号 (123) → -123
        if re.fullmatch(r"\(\s*\d+(\.\d+)?\s*\)", s):
            s = "-" + s.strip("()").strip()
        return float(s)
    except Exception:
        return None


# =========================
# Pydantic：LLM 输出结构
# =========================
class FieldInfo(BaseModel):
    column: str = Field(..., description="英文字段名（小写下划线）")
    name_cn: str = Field(..., description="原始中文列名")
    type: str = Field(..., description="PG 类型，如 varchar(2048)/integer/numeric(10,2)/timestamp/date")
    comment: str = Field(..., description="简洁注释")


class TableSchema(BaseModel):
    fields: List[FieldInfo]
    table_comment: Optional[str] = Field(default="", description="表级注释")


# =========================
# 标识符 & 类型 安全消毒
# =========================
_PG_IDENT_MAX = 63
_IDENT_RE = re.compile(r"^[a-z_][a-z0-9_]*$")


def _sanitize_identifier(raw: str) -> str:
    """把任意字符串转为安全的 PG 标识符（小写下划线，仅 ASCII），限制 63 字节。"""
    if raw is None:
        raw = "col"
    name = re.sub(r"[^a-zA-Z0-9_]+", "_", raw.strip().lower())
    if not name or name[0].isdigit():
        name = f"col_{name}"
    if len(name) > _PG_IDENT_MAX:
        name = name[:_PG_IDENT_MAX]
    if not _IDENT_RE.match(name):
        name = "col_" + re.sub(r"[^a-z0-9_]", "", name)
        name = name[:_PG_IDENT_MAX]
    return name


def _ensure_unique_columns(cols: List[str]) -> List[str]:
    """sanitize + 去重 + 63字节冲突规避"""
    seen = {}
    out = []
    for c in cols:
        base = _sanitize_identifier(c or "col")
        name = base
        k = 1
        while name in seen:
            suffix = f"_{k}"
            name = (base[: max(1, _PG_IDENT_MAX - len(suffix))]) + suffix
            k += 1
        seen[name] = True
        out.append(name)
    return out


_TYPE_VARCHAR_RE = re.compile(r"^varchar\((\d+)\)$", re.I)
_TYPE_NUMERIC_RE = re.compile(r"^numeric\((\d+)\s*,\s*(\d+)\)$", re.I)


def _sanitize_pg_type(pg_type: str, series: Optional[pd.Series] = None) -> str:
    """
    类型白名单与限幅：
    - numeric(p,s)：p<=38, s<=10，超出限幅
    - integer/bigint/smallint/boolean/timestamp/date/time/text 保留
    - 其它/未知类型 → text
    """
    if not pg_type:
        return "text"
    t = pg_type.strip().lower().replace(" ", "")

    if t in {
        "text", "boolean", "smallint", "integer", "bigint", "timestamp", "date", "time",
        "int2", "int4", "int8", "real", "doubleprecision", "float4", "float8"
    }:
        return "timestamp" if t == "timestamp" else ("date" if t == "date" else ("time" if t == "time" else t))

    m = _TYPE_NUMERIC_RE.match(t)
    if m:
        p = min(int(m.group(1)), 38)
        s = min(int(m.group(2)), 10)
        if s > p:
            s = max(0, min(4, p))  # 简单修正
        return f"numeric({p},{s})"

    if t.startswith("numeric") or t.startswith("decimal"):
        return "numeric(18,4)"

    return "text"


# =========================
# SQL 字符串字面量转义（避免在 f-string 表达式里写带引号的字面量）
# =========================
def _sql_literal(val: Optional[str]) -> str:
    """把 Python 字符串转为 SQL 单引号字面量内容（只做 ' → '' 转义，不包裹引号）"""
    return (val or "").replace("'", "''")


# =========================
# Schema 校验与自保策略
# =========================
def _adjust_text_type_by_length(series: pd.Series, base_type: str = "varchar(2048)", max_varchar: int = 1024) -> str:
    """基于实际数据长度，动态决定 varchar(N) 或 text。"""
    try:
        lengths = series.fillna("").astype(str).map(len)
        max_len = int(lengths.max()) if not lengths.empty else 0
        if max_len == 0:
            return base_type
        n = min(max(max_len, 50), max_varchar)
        if n >= max_varchar:
            return "text"
        return f"varchar({n})"
    except Exception:
        return base_type


def _coerce_series_by_type(series: pd.Series, pg_type: str) -> Tuple[pd.Series, bool]:
    """按 pg_type 尝试整体列清洗。返回：(清洗后的列, 是否完全成功)"""
    t = (pg_type or "").lower().strip()

    if _is_date_pgtype(t):
        cleaned = series.apply(_normalize_to_str_date)
        ok_mask = cleaned.dropna().map(lambda s: bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(s))))
        all_ok = ok_mask.all() if not ok_mask.empty else True
        return cleaned, all_ok

    if _is_timestamp_pgtype(t):
        cleaned = series.apply(_normalize_to_str_ts)
        ok_mask = cleaned.dropna().map(lambda s: bool(re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", str(s))))
        all_ok = ok_mask.all() if not ok_mask.empty else True
        return cleaned, all_ok

    if _is_time_pgtype(t):
        def _norm_time(v):
            if v is None:
                return None
            s = str(v).strip()
            if s == "" or s.lower() in {"nan", "nat", "none", "null"}:
                return None
            try:
                return dtparser.parse(s).time().strftime("%H:%M:%S")
            except Exception:
                return s

        cleaned = series.apply(_norm_time)
        ok_mask = cleaned.dropna().map(lambda s: bool(re.fullmatch(r"\d{2}:\d{2}:\d{2}", str(s))))
        all_ok = ok_mask.all() if not ok_mask.empty else True
        return cleaned, all_ok

    if _is_boolean_pgtype(t):
        cleaned = series.apply(_coerce_boolean)
        all_ok = cleaned.isna().sum() == series.isna().sum()
        return cleaned, all_ok

    if _is_integer_pgtype(t):
        cleaned = series.apply(_coerce_integer)
        all_ok = cleaned.isna().sum() == series.isna().sum()
        return cleaned, all_ok

    if _is_numeric_pgtype(t):
        cleaned = series.apply(_coerce_numeric)
        all_ok = cleaned.isna().sum() == series.isna().sum()
        return cleaned, all_ok

    cleaned = series.where(series.isna(), series.astype(str).str.strip())
    return cleaned, True


def _finalize_types(
        df: pd.DataFrame,
        headers: List[str],
        fields: List[FieldInfo]
) -> Tuple[pd.DataFrame, List[FieldInfo], Dict[str, str]]:
    """
    根据 LLM 建议类型逐列清洗；若失败则自动降级：
    - timestamp/date/time 解析失败 → text
    - integer/numeric 出现不可解析 → text
    - varchar 动态扩容（或转 text）
    并对类型做白名单限幅。
    返回：清洗后的 df、最终字段定义、每列最终 PG 类型映射
    """
    final_df = df.copy()
    final_fields: List[FieldInfo] = []
    final_types: Dict[str, str] = {}

    # ✅ 关键修复：按“列位置”处理，规避重复表头带来的定位与 rename 问题
    for idx, f in enumerate(fields):
        series = final_df.iloc[:, idx] if idx < final_df.shape[1] else pd.Series([], dtype=object)
        col_name = _sanitize_identifier(f.column)  # 再保险
        suggested_pg_type = _sanitize_pg_type(f.type, series)

        cleaned, ok = _coerce_series_by_type(series, suggested_pg_type)
        eff_type = suggested_pg_type if ok else "text"
        if not ok:
            cleaned = series.astype(str).where(series.isna(), series.astype(str).str.strip())

        # 文本类型动态调整
        if (not _is_date_pgtype(eff_type)) and (not _is_timestamp_pgtype(eff_type)) and (not _is_time_pgtype(eff_type)) \
                and (not _is_boolean_pgtype(eff_type)) and (not _is_integer_pgtype(eff_type)) and (
                not _is_numeric_pgtype(eff_type)):
            eff_type = _adjust_text_type_by_length(cleaned)

        # 写回同一位置的列
        if idx < final_df.shape[1]:
            final_df.iloc[:, idx] = cleaned

        final_types[col_name] = eff_type
        final_fields.append(
            FieldInfo(column=col_name, name_cn=f.name_cn, type=eff_type, comment=f.comment)
        )

    return final_df, final_fields, final_types


# =========================
# 失败回退：纯文本建表 & 全量导入
# =========================
def _fallback_text_import(df: pd.DataFrame, table_name: str, engine, headers: List[str]) -> Dict[str, Any]:
    """
    任意数据必达策略：把所有列作为 text 存储，列名按 header 清洗去重，列注释保留原始 header。
    """
    SQLBotLogUtil.warning(f"🛟 [AI建表] 进入降级：按 TEXT 全量导入 → 表 {table_name}")
    safe_cols = _ensure_unique_columns(headers)
    col_defs = [f'"{c}" text' for c in safe_cols]

    # 先构造列注释 SQL（避免在 f-string 表达式放带引号文字）
    col_comments_lines = []
    for c, h in zip(safe_cols, headers):
        cmt = _sql_literal(str(h))
        col_comments_lines.append(f"COMMENT ON COLUMN \"{table_name}\".\"{c}\" IS '{cmt}';")

    _joiner = ",\n    "
    _cols_sql = _joiner.join(col_defs)
    _col_comments_sql = "\n".join(col_comments_lines)

    create_sql = (
        f'DROP TABLE IF EXISTS "{table_name}";\n'
        f'CREATE TABLE "{table_name}" (\n    {_cols_sql}\n);\n'
        f"{_col_comments_sql}"
    )
    SQLBotLogUtil.info(f"🧱 [降级建表] SQL:\n{create_sql}")
    with engine.connect() as conn:
        conn.execute(text(create_sql))
        conn.commit()

    # ✅ 同样用整体替换列名，规避重复表头
    to_write = df.copy()
    to_write.columns = safe_cols
    to_write.astype(str).to_sql(
        table_name, engine,
        if_exists="append",
        index=False,
        chunksize=1000,
        method="multi"
    )
    SQLBotLogUtil.info(f"✅ [降级建表] 已以 TEXT 模式导入 {len(df)} 行 → {table_name}")
    return {
        "table": table_name,
        "columns": [{"column": c, "name_cn": h, "type": "text", "comment": str(h)} for c, h in zip(safe_cols, headers)],
        "rows_inserted": len(df),
        "status": "fallback_text_success"
    }


# =========================
# 主流程（增强日志+降级，全面兼容 3.11）
# =========================
def insert_pg_by_ai(df: pd.DataFrame, table_name: str, engine, sample_size: int = 10):
    """
    智能建表 & 导入（LLM schema + 强制类型清洗 + 失败自动降级）
    目标：在不牺牲数据可落库性的前提下最大化语义结构化程度；若失败，必达降级。
    """
    headers = list(df.columns)
    try:
        # 1) 样本
        try:
            sample_df = df.head(sample_size).convert_dtypes().copy()
            for col in sample_df.columns:
                if pd.api.types.is_datetime64_any_dtype(sample_df[col]):
                    sample_df[col] = sample_df[col].astype(str)
            sample_preview = json.dumps(sample_df.to_dict(orient="records"), ensure_ascii=False)
            SQLBotLogUtil.info(f"🧩 [AI建表] 表 {table_name} 样本数据预览: {sample_preview[:1200]}...")
        except:
            SQLBotLogUtil.warning(f"🧩 [AI建表] 表 {table_name} 样本数据预览失败")
            sample_preview = []
        # 2) 调用 LLM
        loop = ensure_event_loop()
        llm = loop.run_until_complete(LLMManager.get_default_llm())
        parser = PydanticOutputParser(pydantic_object=TableSchema)

        prompt = ChatPromptTemplate.from_template("""
            你是一名资深数据库建模专家，专长 PostgreSQL。
            请基于以下 Excel 信息，为其生成 PG 表结构定义。

            输入：
            - 表头（按顺序）：{headers}
            - 样本数据（前 {sample_size} 条）：{sample_preview}

            输出（严格 JSON，仅此内容）：
            {format_instructions}

            规则：
            1) fields 数组长度与 headers 完全一致、顺序一致。
            2) column：英文小写，下划线；语义清晰。
            3) type：常用 PG 类型text/integer/bigint/numeric(10,2)/timestamp/date/boolean）。
            4) comment：使用headers提供的是中文则使用原文。如果不是中文则自定义（简洁的语义描述）。
            5) 生成 table_comment（如“设备采集记录表”）。
        """)

        chain = prompt | llm | parser
        llm_input = {
            "headers": headers,
            "sample_preview": sample_preview,
            "sample_size": sample_size,
            "format_instructions": parser.get_format_instructions()
        }

        SQLBotLogUtil.info("🧠 [AI建表] Prompt 输入内容:")
        SQLBotLogUtil.info(json.dumps(llm_input, ensure_ascii=False, indent=2)[:1500] + "...")

        result: TableSchema = loop.run_until_complete(
            asyncio.wait_for(chain.ainvoke(llm_input), timeout=60)
        )

        SQLBotLogUtil.info("🤖 [AI建表] LLM 输出结果:")
        SQLBotLogUtil.info(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))

        # 3) 校验与列名唯一化
        fields = result.fields
        if len(fields) != len(headers):
            raise HTTPException(status_code=500, detail=f"LLM 返回字段数({len(fields)})与表头数({len(headers)})不一致。")

        unique_cols = _ensure_unique_columns([f.column for f in fields])
        for i, f in enumerate(fields):
            fields[i] = FieldInfo(
                column=unique_cols[i],
                name_cn=f.name_cn,
                type=_sanitize_pg_type(f.type),  # 先做一轮类型限幅
                comment=f.comment
            )

        # 4) 类型清洗与降级（按列位置处理，兼容重复表头）
        df_clean, fields_final, type_map = _finalize_types(df, headers, fields)

        # 5) 生成 SQL —— 先拼块再放入 f-string（避免表达式里包含反斜杠/引号字面量）
        table_comment_esc = _sql_literal(result.table_comment or f"{table_name} 数据表")
        col_defs = [f'"{f.column}" {type_map[f.column]}' for f in fields_final]

        col_comments_lines = []
        for f in fields_final:
            cmt = _sql_literal(f.comment or "")
            col_comments_lines.append(f"COMMENT ON COLUMN \"{table_name}\".\"{f.column}\" IS '{cmt}';")

        _joiner = ",\n    "
        _cols_sql = _joiner.join(col_defs)
        _col_comments_sql = "\n".join(col_comments_lines)

        create_sql = (
            f'DROP TABLE IF EXISTS "{table_name}";\n'
            f'CREATE TABLE "{table_name}" (\n    {_cols_sql}\n);\n'
            f"COMMENT ON TABLE \"{table_name}\" IS '{table_comment_esc}';\n"
            f"{_col_comments_sql}"
        )
        SQLBotLogUtil.info(f"🧱 [AI建表] 生成 SQL:\n{create_sql}")

        # 6) 执行建表 + 写入数据（失败即降级）
        try:
            with engine.connect() as conn:
                conn.execute(text(create_sql))
                conn.commit()

            # ✅ 用最终列名整体覆盖，避免重复表头 rename 丢列
            to_write = df_clean.copy()
            to_write.columns = [f.column for f in fields_final]

            to_write.to_sql(
                table_name, engine,
                if_exists="append",
                index=False,
                chunksize=1000,
                method="multi"
            )
            SQLBotLogUtil.info(f"✅ [AI建表] 成功导入 {len(to_write)} 行数据 → {table_name}")

            return {
                "table": table_name,
                "columns": [f.model_dump() for f in fields_final],
                "rows_inserted": len(to_write),
                "sample_size": sample_size,
                "status": "success"
            }

        except Exception as write_err:
            SQLBotLogUtil.error(f"❌ [AI建表] 建表或写入失败，将转入 TEXT 降级。\n{write_err}\n{traceback.format_exc()}")
            # 降级：删表后转 TEXT
            with engine.connect() as conn:
                conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
                conn.commit()
            return _fallback_text_import(df, table_name, engine, headers)

    except asyncio.TimeoutError:
        # LLM 超时 → 直接降级
        return _fallback_text_import(df, table_name, engine, headers)
    except HTTPException:
        # 语义类异常（例如字段数不匹配） → 直接降级
        return _fallback_text_import(df, table_name, engine, headers)
    except Exception as e:
        SQLBotLogUtil.error(f"❌ [AI建表] 异常，将转入 TEXT 降级。\n{e}\n{traceback.format_exc()}")
        return _fallback_text_import(df, table_name, engine, headers)


# =========================
# Event Loop 工具
# =========================
def ensure_event_loop() -> asyncio.AbstractEventLoop:
    """
    通用事件循环获取器，兼容 Python 3.11+
    - 主线程：复用已有 loop；
    - 子线程：自动创建并绑定新 loop；
    """
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop
