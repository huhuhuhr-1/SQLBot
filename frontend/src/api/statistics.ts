import { request } from '@/utils/request'

export interface OverviewMetrics {
  total_queries: number
  success_queries: number
  failed_queries: number
  success_rate: number
  active_users: number
  active_datasources: number
  active_chats: number
  avg_duration_seconds: number | null
}

export interface DatasourceStats {
  datasource_id: number | null
  datasource_name: string | null
  total_queries: number
  success_queries: number
  failed_queries: number
  success_rate: number
  active_users: number
}

export interface UserStats {
  user_id: number | null
  user_name: string | null
  total_queries: number
  success_queries: number
  failed_queries: number
  success_rate: number
  active_datasources: number
}

export interface DailyTrendPoint {
  date: string
  total_queries: number
  success_queries: number
  failed_queries: number
}

export interface StatisticsOverviewResponse {
  overview: OverviewMetrics
  by_datasource: DatasourceStats[]
  by_user: UserStats[]
  daily_trend: DailyTrendPoint[]
}

export interface RecordItem {
  id: number | null
  chat_id: number | null
  create_time: string | null
  create_by: number | null
  user_name: string | null
  datasource_id: number | null
  datasource_name: string | null
  question: string | null
  finish: boolean
  error: string | null
}

export interface StatisticsRecordsResponse {
  items: RecordItem[]
  total: number
  page: number
  size: number
  total_pages: number
}

export const statisticsApi = {
  getOverview: (params?: { start_time?: string; end_time?: string }) =>
    request.get<StatisticsOverviewResponse>('/system/statistics/overview', { params }),

  getRecords: (params: {
    page?: number
    size?: number
    start_time?: string
    end_time?: string
    user_id?: number
    datasource_id?: number
    failed_only?: boolean
  }) => request.get<StatisticsRecordsResponse>('/system/statistics/records', { params }),
}

