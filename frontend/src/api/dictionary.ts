import { request } from '@/utils/request'

export const dictionaryApi = {
  page: (pageNum: number, pageSize: number, params?: Record<string, string>) =>
    request.get(`/system/dict/page/${pageNum}/${pageSize}`, { params }),
  options: () => request.get('/system/dict/options'),
  detail: (id: number) => request.get(`/system/dict/${id}/detail`),
  save: (data: any) => request.put('/system/dict', data),
  delete: (idList: number[]) => request.delete('/system/dict', { data: idList }),
  enable: (id: number, enabled: boolean) => request.get(`/system/dict/${id}/enable/${enabled}`),
  bindingPage: (pageNum: number, pageSize: number, params?: Record<string, unknown>) =>
    request.get(`/system/dict/binding/page/${pageNum}/${pageSize}`, { params }),
  saveBinding: (data: any) => request.put('/system/dict/binding', data),
  deleteBinding: (idList: number[]) => request.delete('/system/dict/binding', { data: idList }),
}
