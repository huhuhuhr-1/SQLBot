import { request } from '@/utils/request'

export interface DefaultPromptItem {
  defaultContent: string
  variables: { name: string; description: string }[]
}

export interface DefaultPromptsResponse {
  GENERATE_SQL: DefaultPromptItem
  ANALYSIS: DefaultPromptItem
  PREDICT_DATA: DefaultPromptItem
}

export const promptApi = {
  getList: (pageNum: any, pageSize: any, type: any, params: any) =>
    request.get(`/system/custom_prompt/${type}/page/${pageNum}/${pageSize}${params}`),
  updateEmbedded: (data: any) => request.put(`/system/custom_prompt`, data),
  deleteEmbedded: (params: any) => request.delete('/system/custom_prompt', { data: params }),
  getOne: (id: any) => request.get(`/system/custom_prompt/${id}`),
  export2Excel: (type: any, params: any) =>
    request.get(`/system/custom_prompt/${type}/export`, {
      params,
      responseType: 'blob',
      requestOptions: { customError: true },
    }),
  getDefaultPrompts: () => request.get<DefaultPromptsResponse>('/system/default-prompts'),
  optimizePrompt: (type: string, prompt: string) =>
    request.post<{ optimized: string }>('/system/prompt/optimize', { type, prompt }),
}
