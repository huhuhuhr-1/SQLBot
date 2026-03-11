import { request } from '@/utils/request'

export const datasourceApi = {
  check: (data: any) => request.post('/datasource/check', data),
  check_by_id: (id: any) => request.get(`/datasource/check/${id}`),
  relationGet: (id: any) => request.post(`/table_relation/get/${id}`),
  relationSave: (dsId: any, data: any) => request.post(`/table_relation/save/${dsId}`, data),
  relationInfer: (dsId: number, tableIds?: number[]) =>
    request.post<unknown[]>(`/table_relation/infer/${dsId}`, { table_ids: tableIds ?? null }),
  add: (data: any) => request.post('/datasource/add', data),
  list: () => request.get('/datasource/list'),
  update: (data: any) => request.post('/datasource/update', data),
  delete: (id: number, name: string) => request.post(`/datasource/delete/${id}/${name}`),
  getTables: (id: number) => request.post(`/datasource/getTables/${id}`),
  getTablesByConf: (data: any) => request.post('/datasource/getTablesByConf', data),
  getFields: (id: number, table_name: string) =>
    request.post(`/datasource/getFields/${id}/${table_name}`),
  execSql: (id: number | string, sql: string) =>
    request.post(`/datasource/execSql/${id}`, { sql: sql }),
  chooseTables: (id: number, data: any) => request.post(`/datasource/chooseTables/${id}`, data),
  tableList: (id: number) => request.post(`/datasource/tableList/${id}`),
  fieldList: (id: number, data = { fieldName: '' }) =>
    request.post(`/datasource/fieldList/${id}`, data),
  edit: (data: any) => request.post('/datasource/editLocalComment', data),
  previewData: (id: number, data: any) => request.post(`/datasource/previewData/${id}`, data),
  saveTable: (data: any) => request.post('/datasource/editTable', data),
  saveField: (data: any) => request.post('/datasource/editField', data),
  getDs: (id: number) => request.post(`/datasource/get/${id}`),
  copy: (id: number, data?: { name?: string }) =>
    request.post(`/datasource/copy/${id}`, data ?? {}),
  cancelRequests: () => request.cancelRequests(),
  getSchema: (data: any) => request.post('/datasource/getSchemaByConf', data),
  syncFields: (id: number) => request.post(`/datasource/syncFields/${id}`),
  inferFieldComments: (tableId: number, fields: { id: number; field_name: string; field_comment?: string }[]) =>
    request.post<{ suggestions: { field_id: number; suggested_comment: string }[] }>(
      '/datasource/inferFieldComments',
      { table_id: tableId, fields }
    ),
  exportDsSchema: (id: any) =>
    request.get(`/datasource/exportDsSchema/${id}`, {
      responseType: 'blob',
      requestOptions: { customError: true },
    }),
  /** 批量导出数据源（基础信息、选中表、表映射、元数据） */
  exportBatch: (ids: number[]) =>
    request.post<{ datasources: any[] }>('/datasource/export', { ids }),
  /** 批量导入数据源 */
  importBatch: (payload: { datasources: any[] }) =>
    request.post<any[]>('/datasource/import', payload),
}
