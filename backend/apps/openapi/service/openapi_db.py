import asyncio
import hashlib
import os
import uuid

import pandas as pd
import json
from fastapi import HTTPException
from sqlalchemy import text
from sqlmodel import select

from apps.datasource.utils.utils import aes_decrypt
from apps.db.engine import get_engine_conn
from common.core.config import settings
from common.core.deps import SessionDep
from ...datasource.api.datasource import insert_pg
from ...datasource.crud.field import delete_field_by_ds_id
from ...datasource.crud.table import delete_table_by_ds_id
from ...datasource.models.datasource import CoreDatasource, DatasourceConf
import hashlib
import json
import os
import traceback
import uuid
import pandas as pd
from sqlalchemy import text
from fastapi import HTTPException
from common.utils.utils import SQLBotLogUtil
from apps.db.engine import get_engine_conn
from apps.datasource.crud.datasource import create_ds, getTables, update_table_and_fields
from apps.datasource.models.datasource import CreateDatasource, CoreTable, TableObj
from apps.datasource.utils.utils import aes_encrypt

path = settings.EXCEL_PATH


def delete_ds(session: SessionDep, id: int):
    """
    删除数据源（含表清理逻辑）
    - 对 Excel 类型：会删除所有实际创建的表。
    - 对其他类型：仅清理元数据。
    """
    from common.utils.utils import SQLBotLogUtil

    try:
        # === Step 1: 获取数据源记录 ===
        term = session.exec(select(CoreDatasource).where(CoreDatasource.id == id)).first()
        if not term:
            raise HTTPException(status_code=404, detail=f"Datasource with ID {id} not found")

        SQLBotLogUtil.info(f"🧩 准备删除数据源 ID={id}, 名称={term.name}, 类型={term.type}")

        # === Step 2: 删除 Excel 类型的物理表 ===
        if term.type == "excel":
            try:
                conf_raw = term.configuration or ""
                if not conf_raw.strip():
                    SQLBotLogUtil.warn(f"⚠️ 数据源 ID={id} 无配置项 configuration，跳过表删除。")
                else:
                    conf = DatasourceConf(**json.loads(aes_decrypt(conf_raw)))
                    engine = get_engine_conn()
                    with engine.begin() as conn:
                        for sheet in conf.sheets:
                            table_name = sheet.get("tableName")
                            if not table_name:
                                SQLBotLogUtil.warn(f"⚠️ 跳过无效 Sheet 项: {sheet}")
                                continue
                            SQLBotLogUtil.info(f"🗑️ 删除 Excel 表：{table_name}")
                            conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
                    SQLBotLogUtil.info(f"✅ 已删除 Excel 类型数据源的全部表。")
            except Exception as e:
                SQLBotLogUtil.error(f"❌ 删除 Excel 表失败: {traceback.format_exc()}")
                raise HTTPException(status_code=500, detail=f"Failed to drop Excel tables: {e}")

        # === Step 3: 删除元数据 ===
        delete_table_by_ds_id(session, id)
        delete_field_by_ds_id(session, id)

        # === Step 4: 删除数据源本身 ===
        session.delete(term)
        session.commit()
        SQLBotLogUtil.info(f"✅ 数据源删除成功 ID={id}, 名称={term.name}")

        return {"message": f"Datasource '{term.name}' (ID={id}) deleted successfully."}

    except HTTPException:
        # 已知错误直接抛出
        raise
    except Exception as e:
        session.rollback()
        SQLBotLogUtil.error(f"❌ 删除数据源异常: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Delete datasource failed: {e}")
    finally:
        # 清理事务状态
        if session.is_active:
            session.commit()


def insert_pg(df, table_name, engine):
    """将 DataFrame 写入 PostgreSQL（replace 模式）"""
    try:
        df.to_sql(table_name, engine, if_exists="replace", index=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to insert table {table_name}: {e}")


def upload_excel_and_create_datasource_service(session, trans, user, save_path: str, original_filename: str):
    """
    上传 Excel 并自动创建数据源（Excel类型）
    用于 openapi 层的复用。
    - 自动跳过空 sheet
    - 自动处理重名文件
    - 自动加密 configuration
    - 异常时清理孤表
    """
    created_tables = []  # 成功导入的表名
    try:
        SQLBotLogUtil.info(f"📂 开始上传并创建数据源：{original_filename}")
        engine = get_engine_conn()

        # === Step 1: 解析 Excel/CSV ===
        if original_filename.endswith(".csv"):
            df = pd.read_csv(save_path, engine="c")
            if df.empty or len(df.columns) == 0 or df.dropna(how="all").empty:
                SQLBotLogUtil.info(f"⚠️ 跳过 CSV：无有效数据")
            else:
                table_name = f"sheet1_{hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:10]}"
                insert_pg(df, table_name, engine)
                created_tables.append(table_name)
                SQLBotLogUtil.info(f"✅ 导入 CSV 完成：{table_name}")
        else:
            # 逐 sheet 读取
            sheet_names = pd.ExcelFile(save_path).sheet_names
            for sheet_name in sheet_names:
                df = pd.read_excel(save_path, sheet_name=sheet_name, engine="calamine")

                # ⚠️ 跳过空 sheet（行全空 或 无列）
                if df.empty or len(df.columns) == 0 or df.dropna(how="all").empty:
                    SQLBotLogUtil.info(f"⚠️ 跳过空 Sheet：{sheet_name}")
                    continue

                table_name = f"{sheet_name}_{hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:10]}"
                insert_pg(df, table_name, engine)
                created_tables.append(table_name)
                SQLBotLogUtil.info(f"✅ 导入 Sheet 完成：{table_name}")

        if not created_tables:
            SQLBotLogUtil.error(f"❌ Excel 内无有效数据表，终止创建。")
            raise HTTPException(status_code=400, detail="Excel has no valid data sheets")

        # === Step 2: 构建配置并加密 ===
        conf_dict = {
            "file_path": save_path,
            "sheets": [{"tableName": tname, "tableComment": ""} for tname in created_tables]
        }
        configuration_encrypted = aes_encrypt(json.dumps(conf_dict, ensure_ascii=False))

        # === Step 3: 检查并生成唯一名称 ===
        # base_name = original_filename
        # existing_names = [
        #     row[0]
        #     for row in session.exec(
        #         select(CoreDatasource.name).where(CoreDatasource.oid == user.oid)
        #     ).all()
        # ]
        #
        # if base_name in existing_names:
        #     suffix = uuid.uuid4().hex[:6]
        #     ds_name = f"{base_name.split('.')[0]}_{suffix}.{base_name.split('.')[-1]}"
        #     SQLBotLogUtil.info(f"⚠️ 检测到同名数据源，自动重命名为：{ds_name}")
        # else:
        #     ds_name = base_name
        suffix = uuid.uuid4().hex[:6]
        ds_name = f"{original_filename.split('.')[0]}_{suffix}.{original_filename.split('.')[-1]}"
        # === Step 4: 创建数据源对象 ===
        tables_payload = [CoreTable(table_name=tname, table_comment="") for tname in created_tables]
        ds = CreateDatasource(
            name=ds_name,
            type="excel",
            configuration=configuration_encrypted,
            tables=tables_payload,
        )

        datasource = create_ds(session, trans, user, ds)
        session.flush()
        SQLBotLogUtil.info(f"✅ 数据源创建成功 ID={datasource.id}")

        # === Step 5: 更新表字段信息 ===
        try:
            for tname in created_tables:
                tables = getTables(session, datasource.id)
                for t in tables:
                    if t.table_name == tname:
                        update_table_and_fields(session, TableObj.from_orm(t))
            SQLBotLogUtil.info(f"🧾 已登记 {len(created_tables)} 个表结构")
        except Exception as e:
            SQLBotLogUtil.error(f"⚠️ 更新表字段失败: {e}")

        SQLBotLogUtil.info(f"🎉 上传并创建数据源流程完成：{ds_name}")
        return datasource

    except Exception as e:
        SQLBotLogUtil.error(f"❌ 上传并创建数据源失败: {traceback.format_exc()}")
        # === Step 6: 清理孤表 ===
        if created_tables:
            SQLBotLogUtil.info(f"🧹 开始清理孤表，共 {len(created_tables)} 个")
            try:
                engine = get_engine_conn()
                with engine.connect() as conn:
                    for tname in created_tables:
                        conn.execute(text(f'DROP TABLE IF EXISTS "{tname}"'))
                        SQLBotLogUtil.info(f"🧹 已清理孤表：{tname}")
                    conn.commit()
            except Exception as drop_err:
                SQLBotLogUtil.error(f"⚠️ 清理孤表失败: {drop_err}")

        raise HTTPException(status_code=500, detail=f"Upload and create datasource failed: {e}")
