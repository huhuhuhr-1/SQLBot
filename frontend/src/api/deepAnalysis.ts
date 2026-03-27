import { request } from '@/utils/request'
import { chatApi, type ChatInfo } from '@/api/chat'

/**
 * 深度分析会话列表（仅 origin=1）
 */
export const deepAnalysisApi = {
  /**
   * 创建一条 Data Agent session（origin=1）
   * datasourceId 可选，不传则 Agent 自动发现所有数据源
   */
  startSession: (datasourceId?: number): Promise<ChatInfo> => {
    const body: Record<string, any> = { origin: 1, question: '' }
    if (datasourceId != null) body.datasource = datasourceId
    return request.post('/chat/start', body).then((res: any) => {
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
    return request
      .get('/openapi/deep-analysis/recommend-questions', {
        params: { datasource_id: datasourceId },
      })
      .then((res: any) => ({
        questions: Array.isArray(res?.questions) ? res.questions : [],
      }))
  },
}
