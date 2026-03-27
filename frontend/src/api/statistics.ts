import { request } from '@/utils/request'

// ----- Overview -----
export interface OverviewMetrics {
  total_queries: number
  success_queries: number
  failed_queries: number
  success_rate: number
  active_users: number
  active_datasources: number
  active_chats: number
  avg_duration_seconds: number | null
  total_users?: number
  total_datasources?: number
  total_tokens?: number
  duration_p50_seconds?: number | null
  duration_p90_seconds?: number | null
  duration_p99_seconds?: number | null
}

export interface DatasourceStats {
  datasource_id: number | null
  datasource_name: string | null
  total_queries: number
  success_queries: number
  failed_queries: number
  success_rate: number
  active_users: number
  avg_duration_seconds?: number | null
  total_tokens?: number
}

export interface UserStats {
  user_id: number | null
  user_name: string | null
  total_queries: number
  success_queries: number
  failed_queries: number
  success_rate: number
  active_datasources: number
  avg_duration_seconds?: number | null
  total_tokens?: number
}

export interface DailyTrendPoint {
  date: string
  total_queries: number
  success_queries: number
  failed_queries: number
  avg_duration_seconds?: number | null
  total_tokens?: number
  success_rate?: number
}

export interface StatisticsOverviewResponse {
  overview: OverviewMetrics
  by_datasource: DatasourceStats[]
  by_user: UserStats[]
  daily_trend: DailyTrendPoint[]
}

// ----- Trend -----
export interface TrendPoint {
  date: string
  total_queries: number
  success_queries: number
  failed_queries: number
  avg_duration_seconds: number | null
  total_tokens: number
  success_rate: number
}

export interface StatisticsTrendResponse {
  trend: TrendPoint[]
}

// ----- Datasource TOP -----
export interface DatasourceTopItem {
  datasource_id: number | null
  datasource_name: string | null
  value: number
  sort_key: string
}

export interface StatisticsDatasourceTopResponse {
  items: DatasourceTopItem[]
}

// ----- Datasource detailed -----
export interface DatasourceDetailedItem {
  datasource_id: number | null
  datasource_name: string | null
  total_queries: number
  success_queries: number
  failed_queries: number
  success_rate: number
  active_users: number
  avg_duration_seconds: number | null
  total_tokens: number
}

export interface StatisticsDatasourceDetailedResponse {
  items: DatasourceDetailedItem[]
  total: number
  page: number
  size: number
  total_pages: number
}

// ----- Failure analysis -----
export interface FailureReasonItem {
  error_type: string
  count: number
  sample_message?: string | null
}

export interface FailureByDatasourceItem {
  datasource_id: number | null
  datasource_name: string | null
  failed_count: number
}

export interface FailureByHourItem {
  hour: number
  failed_count: number
}

export interface StatisticsFailureAnalysisResponse {
  by_reason: FailureReasonItem[]
  by_datasource: FailureByDatasourceItem[]
  by_hour: FailureByHourItem[]
}

// ----- User detailed -----
export interface UserDetailedItem {
  user_id: number | null
  user_name: string | null
  total_queries: number
  success_queries: number
  failed_queries: number
  success_rate: number
  active_datasources: number
  avg_duration_seconds: number | null
  total_tokens: number
}

export interface StatisticsUserDetailedResponse {
  items: UserDetailedItem[]
  total: number
  page: number
  size: number
  total_pages: number
}

// ----- Records -----
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
  error_type?: string | null
  duration_seconds?: number | null
  total_tokens?: number | null
}

export interface StatisticsRecordsResponse {
  items: RecordItem[]
  total: number
  page: number
  size: number
  total_pages: number
}

const timeParams = (params?: { start_time?: string; end_time?: string }) =>
  params && params.start_time && params.end_time ? { params } : { params: params || {} }

export const statisticsApi = {
  getOverview: (params?: { start_time?: string; end_time?: string }) =>
    request.get<StatisticsOverviewResponse>('/system/statistics/overview', timeParams(params)),

  getTrend: (params?: { start_time?: string; end_time?: string }) =>
    request.get<StatisticsTrendResponse>('/system/statistics/trend', timeParams(params)),

  getDatasourceTop: (params: {
    start_time?: string
    end_time?: string
    sort_by?: 'total_queries' | 'failed_queries' | 'avg_duration_seconds' | 'total_tokens'
    limit?: number
  }) => request.get<StatisticsDatasourceTopResponse>('/system/statistics/datasource/top', { params }),

  getDatasourceDetailed: (params: {
    start_time?: string
    end_time?: string
    page?: number
    size?: number
    keyword?: string
    order_by?: string
    desc?: boolean
  }) => request.get<StatisticsDatasourceDetailedResponse>('/system/statistics/datasource/detailed', { params }),

  getFailureAnalysis: (params?: { start_time?: string; end_time?: string }) =>
    request.get<StatisticsFailureAnalysisResponse>('/system/statistics/failure/analysis', timeParams(params)),

  getUserDetailed: (params: {
    start_time?: string
    end_time?: string
    page?: number
    size?: number
    keyword?: string
    order_by?: string
    desc?: boolean
  }) => request.get<StatisticsUserDetailedResponse>('/system/statistics/user/detailed', { params }),

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
