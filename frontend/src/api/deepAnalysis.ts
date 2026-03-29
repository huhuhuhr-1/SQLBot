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

  /** 批量删除深度分析会话（仅当前用户、origin=1） */
  batchDeleteSessions: (
    chatIds: number[]
  ): Promise<{ deleted: number; skipped_ids: number[] }> => {
    return request
      .post('/openapi/deep-analysis/sessions/batch-delete', { chat_ids: chatIds })
      .then((res: any) => ({
        deleted: Number(res?.deleted) || 0,
        skipped_ids: Array.isArray(res?.skipped_ids) ? res.skipped_ids.map(Number) : [],
      }))
  },

  /**
   * 按范围清理深度分析会话（仅 origin=1），语义同智能问数 cleanChats。
   */
  cleanSessions: (params?: {
    chat_ids?: number[]
    start_time?: string
    end_time?: string
  }): Promise<{
    success_count: number
    failed_count: number
    total_count: number
    message: string
  }> => {
    return request.post('/openapi/deep-analysis/sessions/clean', {
      chat_ids: params?.chat_ids ?? undefined,
      start_time: params?.start_time,
      end_time: params?.end_time,
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
