# SQLBot Datasource API
from apps.datasource.api.datasource import router
from apps.datasource.api.table_relation import router as table_relation_router
from apps.datasource.api.recommended_problem import router as recommended_problem_router

__all__ = ["router", "table_relation_router", "recommended_problem_router"]
