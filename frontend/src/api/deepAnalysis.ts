import { request } from '@/utils/request'
import { chatApi, type ChatInfo } from '@/api/chat'

/**
 * 深度分析会话列表（仅 origin=1）
 */
export const deepAnalysisApi = {
  sessions: (): Promise<ChatInfo[]> => {
    return request.get('/openapi/deep-analysis/sessions').then((res: any) => {
      return chatApi.toChatInfoList(Array.isArray(res) ? res : [])
    })
  },
}
