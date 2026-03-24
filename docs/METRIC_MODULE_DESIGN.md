# SQLBot 指标管理模块设计分析文档

> 版本：1.0  
> 日期：2026-03-23  
> 状态：设计评审

---

## 一、背景与目标

### 1.1 业务背景

SQLBot 目前通过库表名和字段名（元数据）进行 RAG 检索。当用户询问"利润"、"转化率"等业务概念时，AI 往往因为找不到对应字段而产生"幻觉"或计算逻辑错误。

### 1.2 模块目标

通过建立"业务名词"与"SQL 计算片段"的映射字典，为 AI 提供一份"计算说明书"，强制统一计算口径，显著提升 Text-to-SQL 的准确率。

### 1.3 核心价值

> **一句话总结**：这个模块就是给 SQLBot 增加一个"标准答案库"，让 AI 从"开卷考试"变成"填空题"，彻底解决算错数的问题。

---

## 二、设计文档整体评价

### 2.1 优点

| 评价维度 | 具体表现 |
|---------|---------|
| 问题定位 | 准确识别了"AI根据字段名盲目推断计算逻辑"的核心痛点 |
| 价值主张 | "标准答案库"概念直观，让AI从"开卷考试"变"填空题"的比喻恰当 |
| 流程对比 | Before/After对比清晰展示了预期效果 |
| 验收标准 | 配置生效、语义覆盖、计算准确三个维度明确 |

### 2.2 待完善之处

| 问题点 | 说明 |
|-------|------|
| 数据模型设计 | 过于简化，缺少关键字段 |
| 与术语库关系 | 未明确与现有 Terminology 模块的边界 |
| 语义注入细节 | Prompt 注入的具体格式和优先级未详细说明 |
| 依赖管理 | 未涉及公式依赖字段的校验机制 |

---

## 三、与现有架构的契合度分析

### 3.1 现有模块对比

| 模块 | 功能定位 | 核心能力 | 指标模块可借鉴点 |
|------|---------|---------|-----------------|
| **Terminology（术语库）** | 名词解释 | 同义词映射、向量检索、模糊匹配 | 指标语义检索逻辑 |
| **DataTraining（SQL示例）** | 示例校准 | 数据源绑定、embedding、问答对 | 指标与数据源关联 |
| **Dictionary（字典管理）** | 枚举值映射 | 字典项管理、字段绑定 | 维度约束管理 |

### 3.2 功能边界划分

```
┌─────────────────────────────────────────────────────────────┐
│                      用户提问："上个月利润多少？"              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Terminology（术语库）                                        │
│  ────────────────────                                        │
│  作用：解决"名词理解"问题                                      │
│  示例："利润" = "净利润" = "净收益"（同义词映射）               │
│  输出：业务概念的同义词扩展                                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Metric（指标库）【新增】                                      │
│  ────────────────────                                        │
│  作用：解决"计算口径"问题                                      │
│  示例：利润 = SUM(revenue - cost)（标准公式）                  │
│  输出：强制使用的SQL计算片段                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  DataTraining（SQL示例）                                      │
│  ────────────────────                                        │
│  作用：解决"查询模式"问题                                      │
│  示例：类似问题的SQL写法参考                                   │
│  输出：可参考的SQL示例                                         │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Prompt 注入顺序

建议按以下顺序组装 Prompt Context：

```
<Info>
  <db-engine>PostgreSQL 15</db-engine>
  <m-schema>表结构信息...</m-schema>
  <terminologies>术语定义...</terminologies>      <!-- 第1步：名词理解 -->
  <metrics>指标公式...</metrics>                   <!-- 第2步：计算口径 -->
  <sql-examples>SQL示例...</sql-examples>          <!-- 第3步：查询模式 -->
</Info>
```

---

## 四、数据模型设计

### 4.1 扩展版数据模型

设计文档中的模型过于简化，建议扩展为以下结构：

```python
# backend/apps/metric/models/metric_model.py

from datetime import datetime
from typing import List, Optional

from pgvector.sqlalchemy import VECTOR
from pydantic import BaseModel
from sqlalchemy import Column, Text, BigInteger, DateTime, Identity, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import SQLModel, Field


class CoreMetric(SQLModel, table=True):
    """指标主表"""
    __tablename__ = "core_metric"
    
    # 基础字段
    id: Optional[int] = Field(sa_column=Column(BigInteger, Identity(always=True), primary_key=True))
    oid: Optional[int] = Field(sa_column=Column(BigInteger, nullable=True, default=1))
    create_time: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=False), nullable=True))
    
    # 指标基本信息
    name: Optional[str] = Field(max_length=128)           # 指标名称（如：毛利、净利润）
    description: Optional[str] = Field(sa_column=Column(Text, nullable=True))  # 业务描述
    synonyms: Optional[List[str]] = Field(sa_column=Column(JSONB), default=[])  # 同义词列表
    
    # 数据源绑定
    ds_id: Optional[int] = Field(sa_column=Column(BigInteger, nullable=True))  # 关联数据源ID
    specific_ds: Optional[bool] = Field(sa_column=Column(Boolean, default=False))  # 是否限定数据源
    
    # 核心计算逻辑
    formula: Optional[str] = Field(sa_column=Column(Text, nullable=True))  # SQL公式片段
    dependencies: Optional[List[str]] = Field(sa_column=Column(JSONB), default=[])  # 依赖字段列表
    
    # 维度约束
    dimensions: Optional[List[str]] = Field(sa_column=Column(JSONB), default=[])  # 允许的维度字段
    
    # 向量检索
    embedding: Optional[List[float]] = Field(sa_column=Column(VECTOR(), nullable=True))
    
    # 状态
    enabled: Optional[bool] = Field(sa_column=Column(Boolean, default=True))


class MetricInfo(BaseModel):
    """指标信息传输对象"""
    id: Optional[int] = None
    create_time: Optional[datetime] = None
    
    name: Optional[str] = None
    description: Optional[str] = None
    synonyms: Optional[List[str]] = []
    
    ds_id: Optional[int] = None
    ds_name: Optional[str] = None
    specific_ds: Optional[bool] = False
    
    formula: Optional[str] = None
    dependencies: Optional[List[str]] = []
    dimensions: Optional[List[str]] = []
    
    enabled: Optional[bool] = True
```

### 4.2 字段说明

| 字段名 | 类型 | 必填 | 说明 |
|-------|------|-----|------|
| `id` | BigInteger | 是 | 主键 |
| `oid` | BigInteger | 是 | 组织ID（多租户隔离） |
| `name` | String(128) | 是 | 指标名称，如"毛利"、"净利润" |
| `description` | Text | 是 | 业务描述，供AI理解场景 |
| `synonyms` | JSONB | 否 | 同义词列表，如["利润", "净收益"] |
| `ds_id` | BigInteger | 否 | 关联数据源ID，为空表示全局有效 |
| `specific_ds` | Boolean | 否 | 是否限定数据源 |
| `formula` | Text | 是 | SQL聚合表达式，如 `SUM(revenue - cost)` |
| `dependencies` | JSONB | 否 | 依赖字段列表，如 `["revenue", "cost"]` |
| `dimensions` | JSONB | 否 | 允许的维度字段，如 `["region", "time"]` |
| `embedding` | VECTOR | 否 | 向量嵌入，用于语义检索 |
| `enabled` | Boolean | 是 | 启用状态 |

### 4.3 数据库迁移脚本

```python
# backend/alembic/versions/068_create_metric.py

"""068_create_metric

Revision ID: xxx
Revises: yyy
Create Date: 2026-03-23

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
import pgvector
from sqlalchemy.dialects import postgresql

revision = 'xxx'
down_revision = 'yyy'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('core_metric',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('oid', sa.BigInteger(), nullable=True, default=1),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=128), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('synonyms', postgresql.JSONB(), nullable=True),
        sa.Column('ds_id', sa.BigInteger(), nullable=True),
        sa.Column('specific_ds', sa.Boolean(), nullable=True, default=False),
        sa.Column('formula', sa.Text(), nullable=True),
        sa.Column('dependencies', postgresql.JSONB(), nullable=True),
        sa.Column('dimensions', postgresql.JSONB(), nullable=True),
        sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=True, default=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建索引
    op.create_index('ix_core_metric_oid', 'core_metric', ['oid'])
    op.create_index('ix_core_metric_ds_id', 'core_metric', ['ds_id'])
    op.create_index('ix_core_metric_name', 'core_metric', ['name'])


def downgrade():
    op.drop_index('ix_core_metric_name')
    op.drop_index('ix_core_metric_ds_id')
    op.drop_index('ix_core_metric_oid')
    op.drop_table('core_metric')
```

---

## 五、Prompt 注入策略

### 5.1 注入格式设计

建议采用结构化的 XML 格式注入：

```xml
<metrics>
  <metric>
    <name>利润</name>
    <synonyms>净利润, 净收益</synonyms>
    <description>净利润 = 总收入 - 总成本，反映企业最终盈利水平</description>
    <formula>SUM(revenue - cost)</formula>
    <dependencies>revenue, cost</dependencies>
    <dimensions>region, time_period, product_category</dimensions>
    <instruction>
      【强制规则】当用户询问"利润"、"净利润"、"净收益"时，必须使用此公式进行计算。
      严禁自行推导公式或使用其他计算方式。
      如需按维度分组，仅允许使用 dimensions 中列出的字段。
    </instruction>
  </metric>
  
  <metric>
    <name>转化率</name>
    <synonyms>转化率, 转化比率</synonyms>
    <description>转化率 = 成交用户数 / 访问用户数 × 100%</description>
    <formula>CAST(COUNT(DISTINCT buyer_id) AS DECIMAL) / NULLIF(COUNT(DISTINCT visitor_id), 0) * 100</formula>
    <dependencies>buyer_id, visitor_id</dependencies>
    <dimensions>channel, date, campaign</dimensions>
    <instruction>
      【强制规则】当用户询问"转化率"时，必须使用此公式。
      注意处理除零异常，使用 NULLIF 函数。
    </instruction>
  </metric>
</metrics>
```

### 5.2 模板生成器

```python
# backend/apps/template/generate_metric/generator.py

from xml.dom.minidom import parseString
import dicttoxml
import logging

logger = logging.getLogger(__name__)


def get_base_metric_template() -> str:
    """获取指标模板基础格式"""
    return """
<metrics>
{metrics}
</metrics>
"""


def get_metric_example():
    """获取指标示例"""
    _obj = {
        'metrics': [
            {
                'name': '利润',
                'synonyms': ['净利润', '净收益'],
                'description': '净利润 = 总收入 - 总成本',
                'formula': 'SUM(revenue - cost)',
                'dependencies': ['revenue', 'cost'],
                'dimensions': ['region', 'time_period'],
            }
        ]
    }
    return to_metric_xml_string(_obj, 'example')


def to_metric_xml_string(_dict: list[dict] | dict, root: str = 'metrics') -> str:
    """将字典转换为XML字符串"""
    item_name_func = lambda x: 'metric' if x == 'metrics' else 'item'
    dicttoxml.LOG.setLevel(logging.ERROR)
    
    xml = dicttoxml.dicttoxml(
        _dict,
        cdata=['name', 'description', 'formula', 'instruction'],
        custom_root=root,
        item_func=item_name_func,
        xml_declaration=False,
        encoding='utf-8',
        attr_type=False
    ).decode('utf-8')
    
    pretty_xml = parseString(xml).toprettyxml()
    
    if pretty_xml.startswith('<?xml'):
        end_index = pretty_xml.find('>') + 1
        pretty_xml = pretty_xml[end_index:].lstrip()
    
    # 替换 XML 转义字符
    escape_map = {
        '&lt;': '<',
        '&gt;': '>',
        '&amp;': '&',
        '&quot;': '"',
        '&apos;': "'"
    }
    for escaped, original in escape_map.items():
        pretty_xml = pretty_xml.replace(escaped, original)
    
    return pretty_xml
```

### 5.3 Prompt 模板更新

在 `backend/templates/template.yaml` 中新增指标占位符：

```yaml
# 在 system 模板中添加
system: |
  <Instruction>
    ...
    <metrics>：提供一组业务指标定义，块内每一个<metric>就是一个指标，
    其中<name>是指标名称，<formula>是必须使用的SQL计算片段，
    <instruction>内是强制规则，必须严格遵守。
    ...
  </Instruction>
  
  <Info>
    ...
    {metrics}
    ...
  </Info>
```

---

## 六、语义检索流程集成

### 6.1 检索逻辑实现

```python
# backend/apps/metric/curd/metric.py

from typing import List, Optional, Tuple
from sqlalchemy import and_, or_, select, text
from sqlalchemy.orm import Session

from apps.ai_model.embedding import EmbeddingModelCache
from apps.metric.models.metric_model import CoreMetric, MetricInfo
from apps.template.generate_metric.generator import to_metric_xml_string, get_base_metric_template
from common.core.config import settings


# 模糊匹配 SQL
fuzzy_match_sql = """
SELECT id, name, formula, similarity
FROM (
    SELECT id, name, formula, oid, ds_id, specific_ds, enabled,
           (1 - (embedding <=> :embedding_array)) AS similarity
    FROM core_metric
) TEMP
WHERE similarity > :similarity_threshold
  AND oid = :oid
  AND enabled = true
  AND (specific_ds = false OR ds_id = :ds_id OR ds_id IS NULL)
ORDER BY similarity DESC
LIMIT :limit_count
"""


def select_metric_by_word(
    session: Session,
    word: str,
    oid: int,
    ds_id: Optional[int] = None
) -> List[CoreMetric]:
    """通过关键词检索指标"""
    if not word or word.strip() == "":
        return []
    
    results: List[CoreMetric] = []
    
    # 1. 模糊匹配
    stmt = (
        select(CoreMetric)
        .where(
            and_(
                text(":sentence ILIKE '%' || name || '%'"),
                CoreMetric.oid == oid,
                CoreMetric.enabled == True
            )
        )
    )
    
    if ds_id is not None:
        stmt = stmt.where(
            or_(
                CoreMetric.specific_ds == False,
                CoreMetric.ds_id == ds_id,
                CoreMetric.ds_id.is_(None)
            )
        )
    
    params = {'sentence': word}
    if ds_id is not None:
        params['ds_id'] = ds_id
    
    fuzzy_results = session.execute(stmt, params).scalars().all()
    results.extend(fuzzy_results)
    
    # 2. 向量检索（如果启用）
    if settings.EMBEDDING_ENABLED:
        try:
            model = EmbeddingModelCache.get_model()
            embedding = model.embed_query(word)
            
            vector_results = session.execute(
                text(fuzzy_match_sql),
                {
                    'embedding_array': str(embedding),
                    'similarity_threshold': settings.EMBEDDING_METRIC_SIMILARITY or 0.7,
                    'oid': oid,
                    'ds_id': ds_id,
                    'limit_count': settings.EMBEDDING_METRIC_TOP_COUNT or 5
                }
            ).fetchall()
            
            for row in vector_results:
                # 避免重复
                if not any(r.id == row.id for r in results):
                    metric = session.get(CoreMetric, row.id)
                    if metric:
                        results.append(metric)
        except Exception as e:
            logger.error(f"Metric vector search failed: {e}")
    
    return results


def get_metric_template(
    session: Session,
    question: str,
    oid: Optional[int] = 1,
    ds_id: Optional[int] = None
) -> Tuple[str, List[dict]]:
    """获取指标模板"""
    if not oid:
        oid = 1
    
    results = select_metric_by_word(session, question, oid, ds_id)
    
    if not results:
        return '', []
    
    # 转换为字典列表
    metric_list = []
    for metric in results:
        metric_list.append({
            'name': metric.name,
            'synonyms': metric.synonyms or [],
            'description': metric.description,
            'formula': metric.formula,
            'dependencies': metric.dependencies or [],
            'dimensions': metric.dimensions or [],
            'instruction': f'【强制规则】当用户询问"{metric.name}"时，必须使用公式 {metric.formula} 进行计算，严禁自行推导。'
        })
    
    # 生成 XML
    metric_xml = to_metric_xml_string(metric_list)
    template = get_base_metric_template().format(metrics=metric_xml)
    
    return template, metric_list
```

### 6.2 LLM 流程集成

在 `backend/apps/chat/task/llm.py` 中新增指标检索步骤：

```python
# 在 LLMService 类中添加方法

def filter_metric_template(self, _session: Session, oid: int = None, ds_id: int = None):
    """检索并注入指标模板"""
    calculate_oid = oid
    calculate_ds_id = ds_id
    
    if self.current_assistant:
        calculate_oid = self.current_assistant.oid if self.current_assistant.type != 4 else self.current_user.oid
        if self.current_assistant.type == 1:
            calculate_ds_id = None
    
    self.current_logs[OperationEnum.FILTER_METRIC] = start_log(
        session=_session,
        operate=OperationEnum.FILTER_METRIC,
        record_id=self.record.id,
        local_operation=True
    )
    
    self.chat_question.metrics, metric_list = get_metric_template(
        _session, self.chat_question.question, calculate_oid, calculate_ds_id
    )
    
    self.current_logs[OperationEnum.FILTER_METRIC] = end_log(
        session=_session,
        log=self.current_logs[OperationEnum.FILTER_METRIC],
        full_message=metric_list
    )
```

### 6.3 ChatQuestion 模型扩展

在 `backend/apps/chat/models/chat_model.py` 中扩展：

```python
class AiModelQuestion(BaseModel):
    # ... 现有字段 ...
    
    # 新增指标字段
    metrics: str = ""
    
    def sql_sys_question(self, db_type: Union[str, DB], enable_query_limit: bool = True):
        # ... 现有逻辑 ...
        return _base_template['system'].format(
            engine=self.engine,
            schema=self.db_schema,
            question=self.question,
            lang=self.lang,
            terminologies=self.terminologies,
            metrics=self.metrics,  # 新增
            data_training=self.data_training,
            custom_prompt=self.custom_prompt or "",
            # ...
        )
```

---

## 七、API 接口设计

### 7.1 接口定义

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/api/v1/metrics/page/{page}/{size}` | 分页获取指标列表 |
| POST | `/api/v1/metrics` | 创建新指标 |
| PUT | `/api/v1/metrics/{id}` | 更新指标 |
| DELETE | `/api/v1/metrics` | 批量删除指标 |
| GET | `/api/v1/metrics/{id}/enable/{enabled}` | 启用/禁用指标 |
| GET | `/api/v1/metrics/export` | 导出指标 |
| POST | `/api/v1/metrics/uploadExcel` | 批量导入指标 |

### 7.2 API 实现

```python
# backend/apps/metric/api/metric.py

from fastapi import APIRouter, Query, UploadFile, File
from typing import Optional

from apps.metric.curd.metric import (
    page_metric,
    create_metric,
    update_metric,
    delete_metric,
    enable_metric
)
from apps.metric.models.metric_model import MetricInfo
from apps.system.schemas.permission import SqlbotPermission, require_permissions
from common.core.deps import SessionDep, CurrentUser, Trans

router = APIRouter(tags=["Metric"], prefix="/system/metric")


@router.get("/page/{current_page}/{page_size}")
@require_permissions(permission=SqlbotPermission(role=['ws_admin']))
async def get_page(
    session: SessionDep,
    current_user: CurrentUser,
    current_page: int,
    page_size: int,
    name: Optional[str] = Query(None, description="指标名称搜索"),
    ds_id: Optional[int] = Query(None, description="数据源ID筛选")
):
    """分页获取指标列表"""
    return page_metric(
        session, current_page, page_size, name, current_user.oid, ds_id
    )


@router.put("")
@require_permissions(permission=SqlbotPermission(role=['ws_admin']))
async def save_or_update(
    session: SessionDep,
    current_user: CurrentUser,
    trans: Trans,
    info: MetricInfo
):
    """创建或更新指标"""
    if info.id:
        return update_metric(session, info, current_user.oid, trans)
    else:
        return create_metric(session, info, current_user.oid, trans)


@router.delete("")
@require_permissions(permission=SqlbotPermission(role=['ws_admin']))
async def delete(session: SessionDep, id_list: list[int]):
    """批量删除指标"""
    delete_metric(session, id_list)


@router.get("/{id}/enable/{enabled}")
@require_permissions(permission=SqlbotPermission(role=['ws_admin']))
async def toggle_enable(
    session: SessionDep,
    id: int,
    enabled: bool,
    trans: Trans
):
    """启用/禁用指标"""
    enable_metric(session, id, enabled, trans)
```

---

## 八、前端实现

### 8.1 API 封装

```typescript
// frontend/src/api/metric.ts

import { request } from '@/utils/request'

export const metricApi = {
  page: (pageNum: number, pageSize: number, params?: Record<string, unknown>) =>
    request.get(`/system/metric/page/${pageNum}/${pageSize}`, { params }),
  
  save: (data: MetricInfo) => request.put('/system/metric', data),
  
  delete: (idList: number[]) => request.delete('/system/metric', { data: idList }),
  
  enable: (id: number, enabled: boolean) => 
    request.get(`/system/metric/${id}/enable/${enabled}`),
  
  export: () => request.get('/system/metric/export', { responseType: 'blob' }),
  
  uploadExcel: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/system/metric/uploadExcel', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  }
}

interface MetricInfo {
  id?: number
  name: string
  description: string
  synonyms?: string[]
  ds_id?: number
  specific_ds?: boolean
  formula: string
  dependencies?: string[]
  dimensions?: string[]
  enabled?: boolean
}
```

### 8.2 管理页面结构

```
frontend/src/views/system/metric/
├── index.vue           # 主页面（列表 + 搜索 + 操作）
├── MetricForm.vue      # 新增/编辑表单弹窗
└── MetricImport.vue    # Excel 导入组件
```

### 8.3 关键 UI 组件

```vue
<!-- MetricForm.vue 核心表单 -->
<template>
  <el-form :model="form" label-position="top">
    <!-- 基本信息 -->
    <el-form-item :label="t('metric.name')" required>
      <el-input v-model="form.name" maxlength="128" />
    </el-form-item>
    
    <el-form-item :label="t('metric.synonyms')">
      <el-select v-model="form.synonyms" multiple filterable allow-create>
      </el-select>
    </el-form-item>
    
    <el-form-item :label="t('metric.description')" required>
      <el-input v-model="form.description" type="textarea" :rows="3" />
    </el-form-item>
    
    <!-- 数据源绑定 -->
    <el-form-item :label="t('metric.datasource')">
      <el-switch v-model="form.specific_ds" />
      <el-select v-if="form.specific_ds" v-model="form.ds_id">
        <!-- 数据源选项 -->
      </el-select>
    </el-form-item>
    
    <!-- SQL 公式（语法高亮） -->
    <el-form-item :label="t('metric.formula')" required>
      <code-editor 
        v-model="form.formula" 
        language="sql"
        :height="120"
      />
    </el-form-item>
    
    <!-- 依赖字段 -->
    <el-form-item :label="t('metric.dependencies')">
      <el-select v-model="form.dependencies" multiple filterable allow-create>
      </el-select>
    </el-form-item>
    
    <!-- 维度约束 -->
    <el-form-item :label="t('metric.dimensions')">
      <el-select v-model="form.dimensions" multiple filterable allow-create>
      </el-select>
    </el-form-item>
  </el-form>
</template>
```

---

## 九、风险与建议

### 9.1 风险矩阵

| 风险点 | 影响程度 | 发生概率 | 建议措施 |
|-------|---------|---------|---------|
| 公式语法错误 | 高 | 中 | 添加 SQL 语法校验，支持"测试运行"功能 |
| 字段依赖失效 | 高 | 中 | 数据源表结构变更时，提供依赖检查告警 |
| 与术语库混淆 | 中 | 高 | 在 UI 上明确区分两者用途，提供使用场景说明 |
| 公式复杂度过高 | 中 | 低 | 支持公式分步定义，或引入变量占位符机制 |
| 向量检索不准 | 中 | 中 | 调优相似度阈值，支持人工调整权重 |

### 9.2 建议的实施优先级

```
Phase 1（MVP）：
├── 基础数据模型与 CRUD
├── 简单的 Prompt 注入
└── 基础管理界面

Phase 2（增强）：
├── 向量语义检索
├── SQL 语法校验
└── Excel 批量导入导出

Phase 3（高级）：
├── 依赖字段自动检测
├── 公式测试运行
└── 变更影响分析
```

---

## 十、总结

### 10.1 核心要点

1. **明确边界**：指标库解决"计算口径"问题，术语库解决"名词理解"问题，两者互补
2. **扩展模型**：增加依赖字段、维度约束、同义词等关键字段
3. **结构化注入**：采用 XML 格式的 Prompt 注入，提升 AI 理解准确度
4. **复用架构**：借鉴 Terminology 和 DataTraining 的成熟模式

### 10.2 下一步行动

- [ ] 确认数据模型最终设计
- [ ] 创建数据库迁移脚本
- [ ] 实现后端 CRUD 接口
- [ ] 集成到 LLM 流程
- [ ] 开发前端管理界面
- [ ] 编写单元测试
- [ ] 更新用户文档

---

## 附录

### A. 相关文件清单

| 类型 | 文件路径 | 说明 |
|-----|---------|------|
| 数据模型 | `backend/apps/metric/models/metric_model.py` | 指标模型定义 |
| CRUD | `backend/apps/metric/curd/metric.py` | 数据操作 |
| API | `backend/apps/metric/api/metric.py` | 接口定义 |
| 迁移 | `backend/alembic/versions/068_create_metric.py` | 数据库迁移 |
| 模板 | `backend/apps/template/generate_metric/generator.py` | Prompt 模板 |
| 前端API | `frontend/src/api/metric.ts` | API 封装 |
| 前端页面 | `frontend/src/views/system/metric/index.vue` | 管理页面 |

### B. 参考文档

- [SQLBot 项目指南](./GUIDE.md)
- [术语库实现](../backend/apps/terminology/)
- [SQL示例训练](../backend/apps/data_training/)
- [模板系统](../backend/templates/)