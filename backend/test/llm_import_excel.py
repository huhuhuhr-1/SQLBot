import asyncio
import json
import pandas as pd
from sqlalchemy import create_engine, text
from fastapi import HTTPException
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List


# === ✅ 模拟 LLM 管理器（可替换为真实实现） ===
# 你的项目应存在 core/llm/llm_manager.py
# 这里提供兼容示例
class DummyLLM:
    """模拟 LLM，返回伪造 JSON"""

    async def ainvoke(self, prompt):
        print("⚠️ [DummyLLM] 模拟 LLM 调用，返回固定字段结构")
        return {
            "fields": [
                {"column": "device_id", "name_cn": "设备编号", "type": "varchar(50)", "comment": "设备唯一编号"},
                {"column": "collected_at", "name_cn": "采集时间", "type": "timestamp", "comment": "采集数据时间"},
                {"column": "temperature_c", "name_cn": "温度(℃)", "type": "numeric(5,2)", "comment": "采集温度，单位℃"},
                {"column": "current_a", "name_cn": "电流(A)", "type": "numeric(6,3)", "comment": "采集电流，单位A"},
                {"column": "voltage_v", "name_cn": "电压(V)", "type": "numeric(6,2)", "comment": "采集电压，单位V"}
            ]
        }


class LLMManager:
    @staticmethod
    async def get_default_llm():
        # ⚠️ 如果项目内有真实 LLMManager，则删除此类
        return DummyLLM()


# === ✅ 定义字段结构模型 ===
class FieldInfo(BaseModel):
    column: str = Field(..., description="英文字段名，如 device_id")
    name_cn: str = Field(..., description="原始中文字段名")
    type: str = Field(..., description="PostgreSQL 数据类型")
    comment: str = Field(..., description="字段注释，包含含义、单位、取值范围等")


class TableSchema(BaseModel):
    fields: List[FieldInfo]


# === ✅ 主逻辑函数 ===
async def insert_pg(df: pd.DataFrame, table_name: str, engine, sample_size: int = 10):
    """
    智能建表：将 DataFrame 写入 PostgreSQL（LLM 辅助语义注释）
    可在 IDEA 中直接运行。
    """
    try:
        headers = list(df.columns)
        sample_df = df.head(sample_size)
        samples = sample_df.to_dict(orient="records")
        sample_preview = json.dumps(samples, ensure_ascii=False)

        # === 获取 LLM ===
        llm = await LLMManager.get_default_llm()

        # === 定义解析器 ===
        parser = PydanticOutputParser(pydantic_object=TableSchema)

        # === 定义提示词 ===
        prompt = ChatPromptTemplate.from_template("""
            你是资深数据库建模专家，负责将 Excel 数据转化为 PostgreSQL 表结构。
            请分析以下内容：
            - 表头：{headers}
            - 样本数据（前 {sample_size} 条）：{sample_preview}
            
            请生成字段定义信息，输出 JSON 格式（严格遵循下列结构）：
            {format_instructions}
            
            要求：
            1. 每个字段包含 column, name_cn, type, comment；
            2. 字段名语义化（英文小写下划线命名）；
            3. 字段类型符合样本数据推断（数字→numeric，时间→timestamp）；
            4. 字段注释应详细说明含义、单位、取值范围；
            5. 输出仅为 JSON，不包含其他说明。
            """)

        # === 构建并执行 LLM 链 ===
        # 如果 DummyLLM，直接模拟结果；否则使用 LangChain chain.ainvoke()
        if isinstance(llm, DummyLLM):
            result_dict = await llm.ainvoke(prompt)
            result = TableSchema(**result_dict)
        else:
            chain = prompt | llm | parser
            result: TableSchema = await chain.ainvoke({
                "headers": headers,
                "sample_preview": sample_preview,
                "sample_size": sample_size,
                "format_instructions": parser.get_format_instructions()
            })

        columns_info = result.fields

        # === 构造建表 SQL ===
        create_sql_parts, comment_sql_parts = [], []
        for col in columns_info:
            cname = col.column
            ctype = col.type
            comment = col.comment.replace("'", "''")
            create_sql_parts.append(f'"{cname}" {ctype}')
            comment_sql_parts.append(
                f"COMMENT ON COLUMN \"{table_name}\".\"{cname}\" IS '{comment}';"
            )

        comma_newline = ",\n    "
        newline = "\n"
        create_sql = f"""
        DROP TABLE IF EXISTS "{table_name}";
        CREATE TABLE "{table_name}" (
            {comma_newline.join(create_sql_parts)}
        );
        {newline.join(comment_sql_parts)}
        """

        # === 执行建表 ===
        with engine.connect() as conn:
            conn.execute(text(create_sql))
            conn.commit()

        # === 插入数据 ===
        rename_map = {old: new.column for old, new in zip(headers, columns_info)}
        df = df.rename(columns=rename_map)
        df.to_sql(
            table_name,
            engine,
            if_exists="append",
            index=False,
            chunksize=1000,
            method="multi"
        )

        print(f"✅ 表 {table_name} 创建并插入成功，共 {len(df)} 条记录。")
        return {
            "table": table_name,
            "columns": [c.model_dump() for c in columns_info],
            "rows_inserted": len(df),
            "sample_size": sample_size,
            "status": "success"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建表失败: {e}")


# === ✅ 可直接运行示例 ===
if __name__ == "__main__":
    import asyncio


    async def main():
        # 模拟 Excel 数据
        data = {
            "设备编号": ["DEV001", "DEV002", "DEV003"],
            "采集时间": ["2025-10-17 12:00:00", "2025-10-17 12:05:00", "2025-10-17 12:10:00"],
            "温度(℃)": [36.5, 37.0, 35.9],
            "电流(A)": [0.12, 0.14, 0.13],
            "电压(V)": [220, 219, 221]
        }
        df = pd.DataFrame(data)

        # 创建 PostgreSQL 引擎
        engine = create_engine("postgresql+psycopg2://user:password@localhost:5432/testdb")

        # 执行
        result = await insert_pg(df, "iot_data", engine, sample_size=10)
        print(json.dumps(result, ensure_ascii=False, indent=2))


    asyncio.run(main())
