import { request } from '@/utils/request'

export const workspaceUserList = (params: any, pageNum: number, pageSize: number) =>
  request.get(`/system/workspace/uws/pager/${pageNum}/${pageSize}`, { params })

export const workspaceOptionUserList = (params: any, pageNum: number, pageSize: number) =>
  request.get(`/system/workspace/uws/option/pager/${pageNum}/${pageSize}`, { params })

export const workspaceUwsCreate = (data: any) => request.post('/system/workspace/uws', data)
export const workspaceUwsUpdate = (data: any) => request.put('/system/workspace/uws', data)
export const workspaceCreate = (data: any) => request.post('/system/workspace', data)
export const workspaceUpdate = (data: any) => request.put('/system/workspace', data)
export const workspaceUwsDelete = (data: any) => request.delete('/system/workspace/uws', { data })
export const workspaceDelete = (id: any) => request.delete(`/system/workspace/${id}`)
export const workspaceList = () => request.get('/system/workspace')
export const workspaceDetail = (id: any) => request.get(`/system/workspace/${id}`)
export const uwsOption = (params: any) => request.get('system/workspace/uws/option', { params })

/** 全部导出当前工作空间成员 */
export const workspaceUwsExport = (params?: { oid?: number }) =>
  request.post<{ version: number; oid: number; members: { uid: number; account: string; name: string; weight: number }[] }>(
    '/system/workspace/uws/export',
    {},
    { params }
  )
/** 批量导入成员（合并：按账号更新或新增） */
export const workspaceUwsImport = (payload: { members: { account: string; weight?: number }[] }, params?: { oid?: number }) =>
  request.post<any[]>('/system/workspace/uws/import', payload, { params })
