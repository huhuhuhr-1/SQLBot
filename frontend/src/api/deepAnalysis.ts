import { request } from '@/utils/request'
import { chatApi, type ChatInfo } from '@/api/chat'

/**
 * 深度分析会话列表（仅 origin=1）
 */
export const deepAnalysisApi = {
  /**
   * 绑定数据源并创建一条深度分析 session（origin=1），用于「新建分析」弹层确认后立即插表
   */
  startSession: (datasourceId: number): Promise<ChatInfo> => {
    return request
      .post('/chat/start', { datasource: datasourceId, origin: 1, question: '' })
      .then((res: any) => {
        const chat = chatApi.toChatInfo(res)
        if (!chat) throw new Error('Create session failed')
        return chat
      })
  },

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
