import asyncio
import json
import re
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


# =========================
# 工具：PG 类型判断
# =========================
def _is_timestamp_pgtype(pg_type: str) -> bool:
    t = (pg_type or "").lower().strip()
    return ("timestamp" in t) or (t == "date")


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
        # 常见分隔符/中文
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
    # 百分比不应该进整数；若出现，按不可解析处理
    if s.endswith("%"):
        return None
    # 浮点整数化（如 "12.0"）
    try:
        f = float(s)
        if abs(f - round(f)) < 1e-9:
            return int(round(f))
    except Exception:
        pass
    # 直接 int
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
        return float(s)
    except Exception:
        return None


# =========================
# Pydantic：LLM 输出结构
# =========================
class FieldInfo(BaseModel):
    column: str = Field(..., description="英文字段名（小写下划线）")
    name_cn: str = Field(..., description="原始中文列名")
    type: str = Field(..., description="PG 类型，如 varchar(512)/integer/numeric(10,2)/timestamp")
    comment: str = Field(..., description="简洁注释")


class TableSchema(BaseModel):
    fields: List[FieldInfo]
    table_comment: Optional[str] = Field(default="", description="表级注释")


# =========================
# Schema 校验与自保策略
# =========================
def _ensure_unique_columns(cols: List[str]) -> List[str]:
    seen = {}
    out = []
    for c in cols:
        base = (c or "col").strip().lower() or "col"
        name = base
        k = 1
        while name in seen:
            k += 1
            name = f"{base}_{k}"
        seen[name] = True
        out.append(name)
    return out


def _adjust_text_type_by_length(series: pd.Series, base_type: str = "varchar(512)", max_varchar: int = 1024) -> str:
    """
    基于实际数据长度，动态决定 varchar(N) 或 text。
    """
    try:
        lengths = series.fillna("").astype(str).map(len)
        max_len = int(lengths.max()) if not lengths.empty else 0
        if max_len == 0:
            return base_type
        n = min(max(max_len, 50), max_varchar)  # 最小 50，最大 1024
        if n >= max_varchar:
            return "text"
        return f"varchar({n})"
    except Exception:
        return base_type


def _coerce_series_by_type(series: pd.Series, pg_type: str) -> Tuple[pd.Series, bool]:
    """
    按 pg_type 尝试整体列清洗。
    返回：(清洗后的列, 是否完全成功)
    """
    t = (pg_type or "").lower().strip()

    if _is_timestamp_pgtype(t):
        cleaned = series.apply(_normalize_to_str_ts)
        # 判定是否全为可解析的时间字符串（简单判断：匹配格式或为 None）
        ok_mask = cleaned.dropna().map(lambda s: bool(re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", str(s))))
        all_ok = ok_mask.all() if not ok_mask.empty else True
        return cleaned, all_ok

    if _is_boolean_pgtype(t):
        cleaned = series.apply(_coerce_boolean)
        all_ok = cleaned.isna().sum() == series.isna().sum()  # 仅原本为空才为空
        return cleaned, all_ok

    if _is_integer_pgtype(t):
        cleaned = series.apply(_coerce_integer)
        # 如果出现 None 多于原始空值，说明有解析失败
        all_ok = cleaned.isna().sum() == series.isna().sum()
        return cleaned, all_ok

    if _is_numeric_pgtype(t):
        cleaned = series.apply(_coerce_numeric)
        all_ok = cleaned.isna().sum() == series.isna().sum()
        return cleaned, all_ok

    # 文本：统一转字符串；后面会根据长度调整类型
    cleaned = series.where(series.isna(), series.astype(str).str.strip())
    return cleaned, True


def _finalize_types(df: pd.DataFrame, headers: List[str], fields: List[FieldInfo]) -> Tuple[
    pd.DataFrame, List[FieldInfo], Dict[str, str]]:
    """
    根据 LLM 建议类型逐列清洗；若失败则自动降级：
    - timestamp/date 解析失败 → text
    - integer/numeric 出现不可解析 → text
    - varchar 动态扩容（或转 text）
    返回：清洗后的 df、最终字段定义、每列最终 PG 类型映射
    """
    final_df = df.copy()
    final_fields: List[FieldInfo] = []
    final_types: Dict[str, str] = {}

    # 位置一一对应
    for orig_col, f in zip(headers, fields):
        series = final_df[orig_col] if orig_col in final_df.columns else pd.Series([], dtype=object)
        col_name = f.column
        pg_type = f.type

        cleaned, ok = _coerce_series_by_type(series, pg_type)

        # 若清洗失败，直接降级为 text（保证可插入）
        eff_type = pg_type
        if not ok:
            eff_type = "text"
            cleaned = series.astype(str).where(series.isna(), series.astype(str).str.strip())

        # 对文本类型动态调整 varchar(N) 长度
        if (not _is_timestamp_pgtype(eff_type)) and (not _is_boolean_pgtype(eff_type)) \
                and (not _is_integer_pgtype(eff_type)) and (not _is_numeric_pgtype(eff_type)):
            eff_type = _adjust_text_type_by_length(cleaned, base_type="varchar(512)", max_varchar=1024)

        # 写回
        final_df[orig_col] = cleaned
        final_types[col_name] = eff_type
        final_fields.append(FieldInfo(column=col_name, name_cn=f.name_cn, type=eff_type, comment=f.comment))

    return final_df, final_fields, final_types


# =========================
# 主流程
# =========================
def insert_pg_by_ai(df: pd.DataFrame, table_name: str, engine, sample_size: int = 10):
    """
    智能建表 & 导入（LLM schema + 强制类型清洗 + 失败自动降级）
    目标：在不牺牲数据可落库性的前提下最大化语义结构化程度。
    """
    try:
        # 1) 采样给 LLM
        headers = list(df.columns)
        sample_df = df.head(sample_size)
        samples = sample_df.to_dict(orient="records")
        sample_preview = json.dumps(samples, ensure_ascii=False)

        # 2) LLM 推断
        loop = asyncio.get_event_loop()
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
            3) type：常用 PG 类型（varchar(N)/text/integer/bigint/numeric(10,2)/timestamp/boolean）。
            4) comment：简洁的语义描述（避免单位/范围/格式）。
            5) 生成 table_comment（如“设备采集记录表”）。
            """)

        chain = prompt | llm | parser

        result: TableSchema = loop.run_until_complete(chain.ainvoke({
            "headers": headers,
            "sample_preview": sample_preview,
            "sample_size": sample_size,
            "format_instructions": parser.get_format_instructions()
        }))

        fields = result.fields
        if len(fields) != len(headers):
            raise HTTPException(status_code=500, detail=f"LLM 返回字段数({len(fields)})与表头数({len(headers)})不一致。")

        # 3) 确保列名唯一
        unique_cols = _ensure_unique_columns([f.column for f in fields])
        for i, f in enumerate(fields):
            fields[i] = FieldInfo(column=unique_cols[i], name_cn=f.name_cn, type=f.type, comment=f.comment)

        # 4) 基于 LLM 类型做强制清洗与自动降级
        df_clean, fields_final, type_map = _finalize_types(df, headers, fields)

        # 5) 生成 SQL（表注释 + 字段注释）
        table_comment = (result.table_comment or f"{table_name} 数据表").replace("'", "''")
        col_defs = []
        col_comments = []
        for f in fields_final:
            cname = f.column
            ctype = type_map[cname]
            cmt = (f.comment or "").replace("'", "''")
            col_defs.append(f'"{cname}" {ctype}')
            col_comments.append(f'COMMENT ON COLUMN "{table_name}"."{cname}" IS \'{cmt}\';')

        nl = "\n"
        comma_newline = ",\n    "

        create_sql = (
                f'DROP TABLE IF EXISTS "{table_name}";\n'
                f'CREATE TABLE "{table_name}" (\n'
                f'    {comma_newline.join(col_defs)}\n'
                f');\n'
                f'COMMENT ON TABLE "{table_name}" IS \'{table_comment}\';\n'
                + nl.join(col_comments)
        )

        # 6) 执行建表
        with engine.connect() as conn:
            conn.execute(text(create_sql))
            conn.commit()

        # 7) 重命名列并写入
        rename_map = {old: f.column for old, f in zip(headers, fields_final)}
        to_write = df_clean.rename(columns=rename_map)

        to_write.to_sql(
            table_name,
            engine,
            if_exists="append",
            index=False,
            chunksize=1000,
            method="multi"
        )

        return {
            "table": table_name,
            "columns": [f.model_dump() for f in fields_final],
            "rows_inserted": len(to_write),
            "sample_size": sample_size,
            "status": "success"
        }

    except HTTPException:
        raise
    except Exception as e:
        # 环境类问题（连接/权限/磁盘）仍可能抛错
        raise HTTPException(status_code=500, detail=f"建表/导入失败: {e}")
