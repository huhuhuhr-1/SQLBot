# Author: Junjun
# Date: 2025/5/22
from typing import Dict


def db_type_relation() -> Dict:
    return {
        "mysql": "MySQL",
        "sqlServer": "Microsoft SQL Server",
        "pg": "PostgreSQL",
        "excel": "Excel/CSV",
        "oracle": "Oracle",
        "ck": "ClickHouse",
        "dm": "达梦",
        "doris": "Apache Doris",
        "redshift": "AWS Redshift",
        "es": "Elasticsearch"
    }
