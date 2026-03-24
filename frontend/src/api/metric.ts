import { request } from '@/utils/request'

export interface MetricSuggestResult {
  code: string
  name: string
  measure_sql: string
  aliases: string[]
  description?: string | null
  /** 与元数据对齐后主表名，用于前端选中「选表」 */
  used_table?: string | null
  /** 主度量列，用于前端选中「选字段」 */
  used_field?: string | null
  /** 时间粒度/分组口径，写入库并注入 Prompt，不进入 measure_sql */
  expansion_hint?: string | null
}

export interface MetricAdvancedSuggestResult {
  code: string
  name: string
  aliases?: string[]
  description?: string | null
  // derived
  base_metric_code?: string
  modifiers?: Record<string, unknown> | null
  expansion_hint?: string | null
  // composite
  expression?: string
  components?: { slot_code: string; child_metric_code: string }[]
  // atomic passthrough
  measure_sql?: string
  used_table?: string | null
  used_field?: string | null
}

export const metricApi = {
  page: (pageNum: number, pageSize: number, params?: Record<string, unknown>) =>
    request.get(`/system/metric/page/${pageNum}/${pageSize}`, { params }),
  save: (data: unknown) => request.put('/system/metric', data),
  delete: (idList: number[]) => request.delete('/system/metric', { data: idList }),
  enable: (id: number, enabled: boolean) => request.get(`/system/metric/${id}/enable/${enabled}`),
  options: (datasourceIds?: number[]) =>
    request.get('/system/metric/options/list', {
      params:
        datasourceIds && datasourceIds.length > 0
          ? { datasource_ids: datasourceIds.join(',') }
          : {},
    }),
  /** 使用工作区默认大模型，根据自然语言生成原子指标草稿 */
  suggest: (description: string, datasourceId?: number | null) =>
    request.post<MetricSuggestResult>(
      '/system/metric/suggest',
      { description, datasource_id: datasourceId ?? null },
      { requestOptions: { customError: true } },
    ),
  suggestAdvanced: (description: string, metricKind: string, datasourceId?: number | null) =>
    request.post<MetricAdvancedSuggestResult>(
      '/system/metric/suggest/advanced',
      {
        description,
        metric_kind: metricKind,
        datasource_id: datasourceId ?? null,
      },
      { requestOptions: { customError: true } },
    ),
}
