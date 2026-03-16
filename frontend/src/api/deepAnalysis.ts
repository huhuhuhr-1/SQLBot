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

  /**
   * 根据数据源库表 + LLM 推荐深度分析目标（用于「试试这些分析目标」）
   */
  recommendQuestions: (datasourceId: number): Promise<{ questions: string[] }> => {
    return request.get('/openapi/deep-analysis/recommend-questions', {
      params: { datasource_id: datasourceId },
    }).then((res: any) => ({
      questions: Array.isArray(res?.questions) ? res.questions : [],
    }))
  },
}
