"""Data Agent 语义工具：供 create_deep_agent(tools=...) 注册。"""

from __future__ import annotations

import json

from langchain_core.tools import StructuredTool
from sqlmodel import Session

from apps.openapi.dao.openapiDao import get_datasource_by_name_or_id
from apps.openapi.models.openapiModels import DataSourceRequest
from apps.template.template import get_sql_template
from common.core.deps import CurrentUser


def build_data_agent_tools(
    session: Session, user: CurrentUser, workspace_uid: str
) -> list:
    from apps.openapi.agent import sqlbot_workspace as sw

    uid = workspace_uid

    def sqlbot_list_datasources(step_description: str = "") -> str:
        """列出当前用户可见的数据源（id、名称、类型、描述）。step_description：给界面看的简短中文说明。"""
        rows = sw.write_permissions(session, user, uid)
        lines = [
            f"- [{r['id']}] {r['name']} ({r['type']}) {r.get('description', '')}"
            for r in rows
        ]
        head = (step_description.strip() + "\n\n") if step_description.strip() else ""
        return head + (
            "可见数据源：\n" + "\n".join(lines) if lines else "（无可见数据源）"
        )

    def sqlbot_sync_datasource(datasource_id: int, step_description: str = "") -> str:
        """同步指定数据源的元数据到本地缓存（schema、术语、表关系）。datasource_id：数据源数字 ID。"""
        res = sw.sync_datasource_to_disk(session, user, uid, int(datasource_id))
        head = (step_description.strip() + "\n\n") if step_description.strip() else ""
        if not res.get("ok"):
            return head + f"同步失败：{res.get('error', 'unknown')}"
        return head + json.dumps(res, ensure_ascii=False, indent=2)

    def sqlbot_execute_sql_csv(
        datasource_id: int,
        sql: str,
        output_filename: str,
        step_description: str = "",
    ) -> str:
        """执行只读 SQL，将结果导出为 CSV 到本地 exports 目录。sql 使用英文别名；output_filename 仅文件名如 out.csv。"""
        res = sw.execute_sql_to_csv(
            session, user, uid, int(datasource_id), sql, output_filename
        )
        head = (step_description.strip() + "\n\n") if step_description.strip() else ""
        if not res.get("ok"):
            err = res.get("error", "unknown")
            fail_obj = {
                "ok": False,
                "error": err,
                "sql": sql.strip(),
                "datasource_id": int(datasource_id),
            }
            out = head + json.dumps(fail_obj, ensure_ascii=False, indent=2)
            out += f"\n\n```sql\n{sql.strip()}\n```\n"
            return out
        body = {
            "ok": True,
            "sql": sql.strip(),
            "datasource_id": int(datasource_id),
            "path": res["path"],
            "row_count": res["row_count"],
            "columns": res["columns"],
            "preview_rows": res["preview_rows"],
        }
        out = head + json.dumps(body, ensure_ascii=False, indent=2)
        out += f"\n\n```sql\n{sql.strip()}\n```\n"
        return out

    def sqlbot_sql_dialect(datasource_id: int, step_description: str = "") -> str:
        """根据数据源引擎类型返回系统内置 SQL 方言模板（规则与示例），用于生成可解析的 SQL。"""
        ds = get_datasource_by_name_or_id(
            session=session, user=user, query=DataSourceRequest(id=int(datasource_id))
        )
        if ds is None:
            return f"数据源 {datasource_id} 未找到或无权访问"
        try:
            tpl = get_sql_template(ds.type)
        except Exception as e:
            return (
                step_description.strip() + "\n\n" if step_description.strip() else ""
            ) + f"无法加载方言模板: {e}"
        raw = json.dumps(tpl, ensure_ascii=False, indent=2)
        max_len = 14000
        if len(raw) > max_len:
            raw = raw[:max_len] + "\n\n...（已截断，完整内容见 templates/sql_examples）"
        head = (step_description.strip() + "\n\n") if step_description.strip() else ""
        return head + raw

    return [
        StructuredTool.from_function(
            name="sqlbot_list_datasources",
            description="列出当前用户可见的数据源。可选 step_description 用中文简述本步目的（供日志展示）。",
            func=sqlbot_list_datasources,
        ),
        StructuredTool.from_function(
            name="sqlbot_sync_datasource",
            description="将指定数据源的表结构、业务术语、表关系同步到本地 .sqlbot 缓存，便于 read_file/grep。",
            func=sqlbot_sync_datasource,
        ),
        StructuredTool.from_function(
            name="sqlbot_execute_sql_csv",
            description=(
                "执行只读 SQL 并导出 CSV 到工作区 exports。返回 JSON 含 sql、datasource_id、"
                "path、row_count、columns、preview_rows，并附 Markdown SQL 代码块便于界面展示。"
                "SQL 列别名请用英文。"
            ),
            func=sqlbot_execute_sql_csv,
        ),
        StructuredTool.from_function(
            name="sqlbot_sql_dialect",
            description="获取该数据源对应引擎的 SQL 方言模板（引号、LIMIT 等），生成 SQL 前先调用。",
            func=sqlbot_sql_dialect,
        ),
    ]
