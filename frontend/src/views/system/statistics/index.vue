<script lang="ts" setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus-secondary'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { Chart } from '@antv/g2'
import {
  statisticsApi,
  type DatasourceDetailedItem,
  type RecordItem,
  type StatisticsOverviewResponse,
  type UserDetailedItem,
} from '@/api/statistics'

type TrendMetric = 'total' | 'success' | 'failed' | 'duration' | 'tokens'
type DatasourceOrderBy = 'total_queries' | 'failed_queries' | 'success_rate' | 'avg_duration_seconds' | 'total_tokens'
type UserOrderBy = 'total_queries' | 'success_rate' | 'avg_duration_seconds' | 'total_tokens'

const router = useRouter()

const loading = ref(false)
const data = ref<StatisticsOverviewResponse | null>(null)

const dateRange = ref<[string, string]>([
  dayjs().startOf('day').format('YYYY-MM-DD HH:mm:ss'),
  dayjs().endOf('day').format('YYYY-MM-DD HH:mm:ss'),
])

const overviewParams = computed(() => {
  if (!dateRange.value || dateRange.value.length !== 2) return {}
  return {
    start_time: dayjs(dateRange.value[0]).format('YYYY-MM-DD HH:mm:ss'),
    end_time: dayjs(dateRange.value[1]).format('YYYY-MM-DD HH:mm:ss'),
  }
})

const trendMetric = ref<TrendMetric>('total')
const topSortBy = ref<'total_queries' | 'failed_queries' | 'avg_duration_seconds' | 'total_tokens'>('total_queries')

const topDatasourceItems = ref<{ name: string; value: number }[]>([])
const failureData = ref<{ error_type: string; count: number }[]>([])

const datasourceRows = ref<DatasourceDetailedItem[]>([])
const datasourceTotal = ref(0)
const datasourcePage = ref(1)
const datasourcePageSize = ref(10)
const datasourceKeyword = ref('')
const datasourceKeywordInput = ref('')
const datasourceOrderBy = ref<DatasourceOrderBy>('total_queries')
const datasourceOrderDesc = ref(true)
const datasourceTableLoading = ref(false)

const userRows = ref<UserDetailedItem[]>([])
const userTotal = ref(0)
const userPage = ref(1)
const userPageSize = ref(10)
const userKeyword = ref('')
const userKeywordInput = ref('')
const userOrderBy = ref<UserOrderBy>('total_queries')
const userOrderDesc = ref(true)
const userTableLoading = ref(false)

const chartContainer = ref<HTMLDivElement | null>(null)
const topChartContainer = ref<HTMLDivElement | null>(null)
const failureChartContainer = ref<HTMLDivElement | null>(null)
let chartInstance: Chart | null = null
let topChartInstance: Chart | null = null
let failureChartInstance: Chart | null = null

const drawerVisible = ref(false)
const drawerTitle = ref('问数明细')
const recordFilter = ref<{ user_id?: number; datasource_id?: number }>({})
const records = ref<RecordItem[]>([])
const recordsTotal = ref(0)
const recordsPage = ref(1)
const recordsPageSize = ref(20)
const recordsLoading = ref(false)

const formatPercent = (val: number | null | undefined) => {
  if (val == null || val === undefined) return '0%'
  return `${(val * 100).toFixed(1)}%`
}

const formatDuration = (val: number | null | undefined) => {
  if (val == null || val === undefined) return '-'
  return `${Number(val).toFixed(1)}s`
}

const formatNumber = (val: number | null | undefined) => {
  if (val == null || val === undefined) return '-'
  const n = Number(val)
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`
  return String(n)
}

const selectedRangeLabel = computed(() => {
  if (!dateRange.value?.length) return '今天'
  return `${dayjs(dateRange.value[0]).format('MM.DD HH:mm')} - ${dayjs(dateRange.value[1]).format('MM.DD HH:mm')}`
})

const overviewCards = computed(() => {
  const overview = data.value?.overview
  if (!overview) return []
  return [
    {
      key: 'queries',
      label: '区间问数',
      value: formatNumber(overview.total_queries),
      hint: `${overview.success_queries ?? 0} 次成功`,
      tone: 'primary',
    },
    {
      key: 'users',
      label: '区间用户数',
      value: formatNumber(overview.active_users),
      hint: '按当前筛选区间统计',
      tone: 'emerald',
    },
    {
      key: 'datasources',
      label: '区间数据源数',
      value: formatNumber(overview.active_datasources),
      hint: '按当前筛选区间统计',
      tone: 'violet',
    },
    {
      key: 'success',
      label: '成功率',
      value: formatPercent(overview.success_rate),
      hint: `${overview.failed_queries ?? 0} 次失败/异常`,
      tone: 'amber',
    },
    {
      key: 'tokens',
      label: 'Token 消耗',
      value: formatNumber(overview.total_tokens),
      hint: `活跃会话 ${formatNumber(overview.active_chats)}`,
      tone: 'cyan',
    },
    {
      key: 'duration',
      label: '平均耗时',
      value: formatDuration(overview.avg_duration_seconds),
      hint: `P90 ${formatDuration(overview.duration_p90_seconds)}`,
      tone: 'rose',
    },
  ]
})

const hasTrendData = computed(() => Boolean(data.value?.daily_trend?.length))
const hasDatasourceTopData = computed(() => Boolean(topDatasourceItems.value.length))
const hasFailureData = computed(() => Boolean(failureData.value.length))

const FAIL_TOP_N = 5
const failTopDatasourceIds = computed(() => {
  const sorted = [...datasourceRows.value].sort((a, b) => (b.failed_queries || 0) - (a.failed_queries || 0))
  return new Set(sorted.slice(0, FAIL_TOP_N).map((item) => item.datasource_id).filter((id): id is number => id != null))
})
const failTopUserIds = computed(() => {
  const sorted = [...userRows.value].sort((a, b) => (b.failed_queries || 0) - (a.failed_queries || 0))
  return new Set(sorted.slice(0, FAIL_TOP_N).map((item) => item.user_id).filter((id): id is number => id != null))
})

const dsRowClassName = ({ row }: { row: DatasourceDetailedItem }) =>
  row.datasource_id != null && failTopDatasourceIds.value.has(row.datasource_id) ? 'row-fail-top' : ''
const userRowClassName = ({ row }: { row: UserDetailedItem }) =>
  row.user_id != null && failTopUserIds.value.has(row.user_id) ? 'row-fail-top' : ''

const datasourceQueryParams = computed(() => ({
  ...(overviewParams.value as { start_time?: string; end_time?: string }),
  page: datasourcePage.value,
  size: datasourcePageSize.value,
  keyword: datasourceKeyword.value || undefined,
  order_by: datasourceOrderBy.value,
  desc: datasourceOrderDesc.value,
}))

const userQueryParams = computed(() => ({
  ...(overviewParams.value as { start_time?: string; end_time?: string }),
  page: userPage.value,
  size: userPageSize.value,
  keyword: userKeyword.value || undefined,
  order_by: userOrderBy.value,
  desc: userOrderDesc.value,
}))

const recordParams = computed(() => ({
  ...(overviewParams.value as { start_time?: string; end_time?: string }),
  page: recordsPage.value,
  size: recordsPageSize.value,
  user_id: recordFilter.value.user_id,
  datasource_id: recordFilter.value.datasource_id,
  failed_only: false,
}))

async function loadOverview() {
  const res = await statisticsApi.getOverview(overviewParams.value)
  data.value = res
}

async function loadFailureAnalysis() {
  try {
    const res = await statisticsApi.getFailureAnalysis(overviewParams.value)
    failureData.value = (res.by_reason || []).map((item) => ({ error_type: item.error_type, count: item.count }))
  } catch {
    failureData.value = []
  }
}

async function loadDatasourceTop() {
  try {
    const res = await statisticsApi.getDatasourceTop({
      ...(overviewParams.value as { start_time?: string; end_time?: string }),
      sort_by: topSortBy.value,
      limit: 10,
    })
    topDatasourceItems.value = (res.items || []).map((item) => ({
      name: item.datasource_name || '未知',
      value: Number(item.value || 0),
    }))
  } catch {
    topDatasourceItems.value = []
  }
}

async function loadDatasourceTable() {
  datasourceTableLoading.value = true
  try {
    const res = await statisticsApi.getDatasourceDetailed(datasourceQueryParams.value)
    datasourceRows.value = res.items ?? []
    datasourceTotal.value = res.total ?? 0
  } catch (e: any) {
    datasourceRows.value = []
    datasourceTotal.value = 0
    ElMessage.error(e?.message || '加载数据源统计失败')
  } finally {
    datasourceTableLoading.value = false
  }
}

async function loadUserTable() {
  userTableLoading.value = true
  try {
    const res = await statisticsApi.getUserDetailed(userQueryParams.value)
    userRows.value = res.items ?? []
    userTotal.value = res.total ?? 0
  } catch (e: any) {
    userRows.value = []
    userTotal.value = 0
    ElMessage.error(e?.message || '加载用户统计失败')
  } finally {
    userTableLoading.value = false
  }
}

async function loadData(resetTablePage = true) {
  if (resetTablePage) {
    datasourcePage.value = 1
    userPage.value = 1
  }
  loading.value = true
  try {
    await Promise.all([
      loadOverview(),
      loadFailureAnalysis(),
      loadDatasourceTop(),
      loadDatasourceTable(),
      loadUserTable(),
    ])
  } catch (e: any) {
    ElMessage.error(e?.message || '加载统计数据失败')
  } finally {
    loading.value = false
  }
}

function buildTrendChart() {
  if (!chartContainer.value || !data.value?.daily_trend?.length) return
  const trend = data.value.daily_trend
  const keyMap = {
    total: { key: 'total_queries', label: '总问数' },
    success: { key: 'success_queries', label: '成功问数' },
    failed: { key: 'failed_queries', label: '失败问数' },
    duration: { key: 'avg_duration_seconds', label: '平均耗时(s)' },
    tokens: { key: 'total_tokens', label: 'Token 消耗' },
  } as const
  const { key, label } = keyMap[trendMetric.value]
  const dateFormat = trend.length > 14 ? 'MM/DD' : 'MM-DD'
  const flat = trend.map((item) => ({
    date: dayjs(item.date).format(dateFormat),
    value: Number(key === 'avg_duration_seconds' ? item.avg_duration_seconds ?? 0 : item[key as keyof typeof item] ?? 0),
  }))

  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
  chartInstance = new Chart({
    container: chartContainer.value,
    autoFit: true,
    paddingTop: 28,
    paddingRight: 20,
    paddingBottom: 42,
    paddingLeft: 58,
  })
  chartInstance.options({
    type: 'view',
    data: flat,
    encode: { x: 'date', y: 'value' },
    scale: {
      x: { nice: true },
      y: { nice: true, min: 0, tickCount: 5 },
    },
    axis: {
      x: {
        title: '日期',
        titleSpacing: 10,
        labelFontSize: 11,
        labelFill: '#5d6b82',
        line: true,
        tick: true,
      },
      y: {
        title: label,
        titleSpacing: 12,
        labelFontSize: 11,
        labelFill: '#5d6b82',
        line: true,
        tick: true,
        grid: true,
      },
    },
    children: [
      {
        type: 'line',
        encode: { shape: 'smooth' },
        style: { stroke: '#2f6bff', lineWidth: 3 },
      },
      {
        type: 'point',
        encode: { size: 3 },
        style: { fill: '#ffffff', stroke: '#2f6bff', lineWidth: 2 },
      },
    ],
  })
  chartInstance.render()
}

function buildTopChart() {
  if (!topChartContainer.value || !topDatasourceItems.value.length) return
  if (topChartInstance) {
    topChartInstance.destroy()
    topChartInstance = null
  }
  topChartInstance = new Chart({
    container: topChartContainer.value,
    autoFit: true,
    paddingTop: 16,
    paddingRight: 16,
    paddingBottom: 24,
    paddingLeft: 56,
  })
  topChartInstance.options({
    type: 'view',
    data: topDatasourceItems.value,
    encode: { x: 'name', y: 'value' },
    scale: { x: { nice: true }, y: { nice: true, min: 0 } },
    axis: {
      x: { title: false, labelAutoHide: true, labelFill: '#5d6b82' },
      y: { title: false, labelFill: '#5d6b82', grid: true },
    },
    children: [{ type: 'interval', style: { fill: '#2f6bff', radiusTopLeft: 6, radiusTopRight: 6 } }],
  })
  topChartInstance.render()
}

function buildFailureChart() {
  if (!failureChartContainer.value || !failureData.value.length) return
  if (failureChartInstance) {
    failureChartInstance.destroy()
    failureChartInstance = null
  }
  failureChartInstance = new Chart({
    container: failureChartContainer.value,
    autoFit: true,
    paddingTop: 16,
    paddingRight: 16,
    paddingBottom: 28,
    paddingLeft: 56,
  })
  failureChartInstance.options({
    type: 'view',
    data: failureData.value,
    encode: { x: 'error_type', y: 'count' },
    scale: { x: { nice: true }, y: { nice: true, min: 0 } },
    axis: {
      x: { title: false, labelAutoHide: true, labelFill: '#5d6b82' },
      y: { title: false, labelFill: '#5d6b82', grid: true },
    },
    children: [{ type: 'interval', style: { fill: '#ea6548', radiusTopLeft: 6, radiusTopRight: 6 } }],
  })
  failureChartInstance.render()
}

watch(
  () => [data.value?.daily_trend, trendMetric.value],
  async () => {
    await nextTick()
    buildTrendChart()
  },
  { deep: true }
)

watch(
  () => [topDatasourceItems.value, topChartContainer.value],
  async () => {
    await nextTick()
    buildTopChart()
  },
  { deep: true }
)

watch(
  () => [failureData.value, failureChartContainer.value],
  async () => {
    await nextTick()
    buildFailureChart()
  },
  { deep: true }
)

watch(topSortBy, () => {
  loadDatasourceTop()
})

onBeforeUnmount(() => {
  if (chartInstance) chartInstance.destroy()
  if (topChartInstance) topChartInstance.destroy()
  if (failureChartInstance) failureChartInstance.destroy()
})

onMounted(() => {
  loadData()
})

async function loadRecords() {
  recordsLoading.value = true
  try {
    const res = await statisticsApi.getRecords(recordParams.value)
    records.value = res.items ?? []
    recordsTotal.value = res.total ?? 0
  } catch (e: any) {
    ElMessage.error(e?.message || '加载明细失败')
  } finally {
    recordsLoading.value = false
  }
}

function openDsDetail(row: DatasourceDetailedItem) {
  recordFilter.value = { datasource_id: row.datasource_id ?? undefined }
  drawerTitle.value = row.datasource_name ? `问数明细 - ${row.datasource_name}` : '问数明细'
  recordsPage.value = 1
  drawerVisible.value = true
  loadRecords()
}

function openUserDetail(row: UserDetailedItem) {
  recordFilter.value = { user_id: row.user_id ?? undefined }
  drawerTitle.value = row.user_name ? `问数明细 - ${row.user_name}` : '问数明细'
  recordsPage.value = 1
  drawerVisible.value = true
  loadRecords()
}

function applyDatasourceSearch() {
  datasourceKeyword.value = datasourceKeywordInput.value.trim()
  datasourcePage.value = 1
  loadDatasourceTable()
}

function applyUserSearch() {
  userKeyword.value = userKeywordInput.value.trim()
  userPage.value = 1
  loadUserTable()
}

function onDatasourceOrderChange() {
  datasourcePage.value = 1
  loadDatasourceTable()
}

function onUserOrderChange() {
  userPage.value = 1
  loadUserTable()
}

function onDatasourcePageChange(page: number) {
  datasourcePage.value = page
  loadDatasourceTable()
}

function onDatasourceSizeChange(size: number) {
  datasourcePageSize.value = size
  datasourcePage.value = 1
  loadDatasourceTable()
}

function onUserPageChange(page: number) {
  userPage.value = page
  loadUserTable()
}

function onUserSizeChange(size: number) {
  userPageSize.value = size
  userPage.value = 1
  loadUserTable()
}

function onRecordsPageChange(page: number) {
  recordsPage.value = page
  loadRecords()
}

function onRecordsSizeChange(size: number) {
  recordsPageSize.value = size
  recordsPage.value = 1
  loadRecords()
}

function goChat(chatId: number | null) {
  if (chatId != null) router.push({ path: '/chat/index', query: { chat_id: String(chatId) } })
}
</script>

<template>
  <div v-loading="loading" class="statistics-page">
    <div class="page-ornament page-ornament-left" />
    <div class="page-ornament page-ornament-right" />

    <section class="hero-panel">
      <div class="hero-copy">
        <span class="hero-eyebrow">System Intelligence</span>
        <div class="hero-title-row">
          <div>
            <h2 class="statistics-title">统计分析</h2>
            <p class="hero-subtitle">这一版统一了时间筛选口径，并将用户与数据源统计切换成分页查询，适合更大规模数据。</p>
          </div>
          <div class="hero-pill">
            <span class="hero-pill-label">分析区间</span>
            <strong>{{ selectedRangeLabel }}</strong>
          </div>
        </div>
      </div>
      <div class="filter-panel">
        <div class="filter-labels">
          <span class="time-label">时间范围</span>
          <span class="filter-caption">默认今天，所有核心统计结果都会跟随当前筛选区间刷新</span>
        </div>
        <div class="header-actions">
          <el-date-picker
            v-model="dateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始"
            end-placeholder="结束"
            value-format="YYYY-MM-DD HH:mm:ss"
            :shortcuts="[
              { text: '今天', value: () => [dayjs().startOf('day').toDate(), dayjs().endOf('day').toDate()] },
              { text: '最近7天', value: () => [dayjs().subtract(6, 'day').toDate(), dayjs().endOf('day').toDate()] },
              { text: '最近30天', value: () => [dayjs().subtract(29, 'day').toDate(), dayjs().endOf('day').toDate()] },
            ]"
            style="width: 360px"
          />
          <el-button type="primary" class="query-button" @click="loadData">查询</el-button>
        </div>
      </div>
    </section>

    <div v-if="data" class="statistics-content">
      <section class="overview-shell">
        <div class="spotlight-card">
          <div class="spotlight-head">
            <span class="spotlight-tag">时间口径已统一</span>
            <span class="spotlight-trace">Range Driven</span>
          </div>
          <div class="spotlight-main">
            <div>
              <div class="spotlight-label">区间用户 / 区间数据源</div>
              <div class="spotlight-value">
                {{ formatNumber(data.overview.active_users) }}
                <span>/</span>
                {{ formatNumber(data.overview.active_datasources) }}
              </div>
            </div>
            <div class="spotlight-metrics">
              <div class="spotlight-metric">
                <span>活跃会话</span>
                <strong>{{ formatNumber(data.overview.active_chats) }}</strong>
              </div>
              <div class="spotlight-metric">
                <span>P90 耗时</span>
                <strong>{{ formatDuration(data.overview.duration_p90_seconds) }}</strong>
              </div>
            </div>
          </div>
          <p class="spotlight-note">概览卡片、趋势图、排行图和明细列表都会跟随当前时间区间重新统计。</p>
        </div>
        <section class="statistics-cards">
          <div v-for="card in overviewCards" :key="card.key" class="stat-card" :class="`tone-${card.tone}`">
            <div class="card-topline">
              <span class="label">{{ card.label }}</span>
              <span class="dot" />
            </div>
            <div class="value">{{ card.value }}</div>
            <div class="hint">{{ card.hint }}</div>
          </div>
        </section>
      </section>

      <section class="statistics-panel trend-panel">
        <div class="section-header">
          <div>
            <h3>每日趋势</h3>
            <p class="section-desc">强化了坐标轴、刻度与网格线，让横纵坐标更清晰，便于直接阅读趋势变化。</p>
          </div>
          <div class="section-actions">
            <el-radio-group v-model="trendMetric" size="small" class="metric-switch">
              <el-radio-button value="total">总问数</el-radio-button>
              <el-radio-button value="success">成功</el-radio-button>
              <el-radio-button value="failed">失败</el-radio-button>
              <el-radio-button value="duration">平均耗时</el-radio-button>
              <el-radio-button value="tokens">Token 消耗</el-radio-button>
            </el-radio-group>
          </div>
        </div>
        <div v-if="hasTrendData" ref="chartContainer" class="trend-chart" />
        <div v-else class="panel-empty">
          <div class="empty-title">暂无趋势数据</div>
          <div class="empty-text">当前筛选区间没有可展示的问答趋势记录。</div>
        </div>
      </section>

      <section class="statistics-grid">
        <div class="statistics-panel section-block">
          <div class="section-header">
            <div>
              <h3>数据源 TOP10</h3>
              <p class="section-desc">使用独立接口按当前排序条件请求 Top 10，不再依赖全量概览数据派生。</p>
            </div>
            <div class="section-actions">
              <el-select v-model="topSortBy" size="small" style="width: 148px">
                <el-option value="total_queries" label="访问次数" />
                <el-option value="failed_queries" label="失败次数" />
                <el-option value="total_tokens" label="Token 消耗" />
                <el-option value="avg_duration_seconds" label="平均耗时" />
              </el-select>
            </div>
          </div>
          <div v-if="hasDatasourceTopData" ref="topChartContainer" class="small-chart" />
          <div v-else class="panel-empty compact">
            <div class="empty-title">暂无排行数据</div>
            <div class="empty-text">当前区间没有命中任何数据源访问记录。</div>
          </div>
        </div>

        <div class="statistics-panel section-block">
          <div class="section-header">
            <div>
              <h3>失败原因分析</h3>
              <p class="section-desc">错误类型分布也跟随同一时间区间刷新，便于观察稳定性问题集中点。</p>
            </div>
          </div>
          <div v-if="hasFailureData" ref="failureChartContainer" class="small-chart" />
          <div v-else class="panel-empty compact">
            <div class="empty-title">暂无失败数据</div>
            <div class="empty-text">当前筛选区间没有失败记录，或失败原因尚未归类。</div>
          </div>
        </div>
      </section>

      <section class="statistics-panel">
        <div class="section-header">
          <div>
            <h3>按数据源统计</h3>
            <p class="section-desc">已改为服务端分页、搜索和排序，适合大规模数据源场景。</p>
          </div>
          <span class="section-tip">总数 {{ datasourceTotal }}</span>
        </div>
        <div class="list-toolbar">
          <el-input
            v-model="datasourceKeywordInput"
            clearable
            placeholder="搜索数据源名称"
            class="toolbar-search"
            @clear="applyDatasourceSearch"
            @keyup.enter="applyDatasourceSearch"
          >
            <template #append>
              <el-button @click="applyDatasourceSearch">搜索</el-button>
            </template>
          </el-input>
          <div class="toolbar-filters">
            <el-select v-model="datasourceOrderBy" size="small" style="width: 168px" @change="onDatasourceOrderChange">
              <el-option value="total_queries" label="按问数排序" />
              <el-option value="failed_queries" label="按失败次数排序" />
              <el-option value="success_rate" label="按成功率排序" />
              <el-option value="avg_duration_seconds" label="按平均耗时排序" />
              <el-option value="total_tokens" label="按 Token 排序" />
            </el-select>
            <el-switch
              v-model="datasourceOrderDesc"
              inline-prompt
              active-text="倒序"
              inactive-text="正序"
              @change="onDatasourceOrderChange"
            />
          </div>
        </div>
        <el-table
          v-loading="datasourceTableLoading"
          :data="datasourceRows"
          border
          size="small"
          :row-class-name="dsRowClassName"
          style="width: 100%"
          class="statistics-table"
          empty-text="当前区间暂无数据源统计"
        >
          <el-table-column prop="datasource_name" label="数据源" min-width="180" />
          <el-table-column prop="total_queries" label="问数" width="100" />
          <el-table-column label="成功率" width="110">
            <template #default="{ row }">{{ formatPercent(row.success_rate) }}</template>
          </el-table-column>
          <el-table-column prop="failed_queries" label="失败/异常次数" width="140" />
          <el-table-column prop="active_users" label="区间用户数" width="110" />
          <el-table-column label="平均耗时" width="110">
            <template #default="{ row }">{{ formatDuration(row.avg_duration_seconds) }}</template>
          </el-table-column>
          <el-table-column label="Token 消耗" width="110">
            <template #default="{ row }">{{ formatNumber(row.total_tokens) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="openDsDetail(row)">查看明细</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="table-pagination">
          <el-pagination
            :current-page="datasourcePage"
            :page-size="datasourcePageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="datasourceTotal"
            layout="total, sizes, prev, pager, next"
            @current-change="onDatasourcePageChange"
            @size-change="onDatasourceSizeChange"
          />
        </div>
      </section>

      <section class="statistics-panel">
        <div class="section-header">
          <div>
            <h3>按用户统计</h3>
            <p class="section-desc">用户视角同样改为服务端分页，避免数据量过大时页面直接膨胀。</p>
          </div>
          <span class="section-tip">总数 {{ userTotal }}</span>
        </div>
        <div class="list-toolbar">
          <el-input
            v-model="userKeywordInput"
            clearable
            placeholder="搜索用户名"
            class="toolbar-search"
            @clear="applyUserSearch"
            @keyup.enter="applyUserSearch"
          >
            <template #append>
              <el-button @click="applyUserSearch">搜索</el-button>
            </template>
          </el-input>
          <div class="toolbar-filters">
            <el-select v-model="userOrderBy" size="small" style="width: 168px" @change="onUserOrderChange">
              <el-option value="total_queries" label="按问数排序" />
              <el-option value="success_rate" label="按成功率排序" />
              <el-option value="avg_duration_seconds" label="按平均耗时排序" />
              <el-option value="total_tokens" label="按 Token 排序" />
            </el-select>
            <el-switch
              v-model="userOrderDesc"
              inline-prompt
              active-text="倒序"
              inactive-text="正序"
              @change="onUserOrderChange"
            />
          </div>
        </div>
        <el-table
          v-loading="userTableLoading"
          :data="userRows"
          border
          size="small"
          :row-class-name="userRowClassName"
          style="width: 100%"
          class="statistics-table"
          empty-text="当前区间暂无用户统计"
        >
          <el-table-column prop="user_name" label="用户" min-width="160" />
          <el-table-column prop="total_queries" label="问数" width="100" />
          <el-table-column label="成功率" width="110">
            <template #default="{ row }">{{ formatPercent(row.success_rate) }}</template>
          </el-table-column>
          <el-table-column prop="failed_queries" label="失败/异常次数" width="140" />
          <el-table-column prop="active_datasources" label="区间数据源数" width="120" />
          <el-table-column label="平均耗时" width="110">
            <template #default="{ row }">{{ formatDuration(row.avg_duration_seconds) }}</template>
          </el-table-column>
          <el-table-column label="Token 消耗" width="110">
            <template #default="{ row }">{{ formatNumber(row.total_tokens) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="openUserDetail(row)">查看明细</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="table-pagination">
          <el-pagination
            :current-page="userPage"
            :page-size="userPageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="userTotal"
            layout="total, sizes, prev, pager, next"
            @current-change="onUserPageChange"
            @size-change="onUserSizeChange"
          />
        </div>
      </section>
    </div>

    <el-drawer
      v-model="drawerVisible"
      :title="drawerTitle"
      size="70%"
      direction="rtl"
      class="statistics-drawer"
      @open="loadRecords"
    >
      <div v-loading="recordsLoading" class="drawer-body">
        <div class="drawer-summary">
          <span>明细记录</span>
          <strong>{{ recordsTotal }}</strong>
        </div>
        <el-table :data="records" border size="small" style="width: 100%" class="statistics-table" empty-text="暂无明细记录">
          <el-table-column prop="create_time" label="时间" width="160">
            <template #default="{ row }">
              {{ row.create_time ? dayjs(row.create_time).format('YYYY-MM-DD HH:mm:ss') : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="user_name" label="用户" width="100" />
          <el-table-column prop="datasource_name" label="数据源" width="120" />
          <el-table-column prop="question" label="问题摘要" min-width="180" show-overflow-tooltip />
          <el-table-column prop="finish" label="结果" width="80">
            <template #default="{ row }">
              <el-tag :type="row.finish ? 'success' : 'danger'" size="small">
                {{ row.finish ? '成功' : '失败' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="error_type" label="错误类型" width="100" />
          <el-table-column label="耗时(s)" width="80">
            <template #default="{ row }">{{ row.duration_seconds != null ? Number(row.duration_seconds).toFixed(1) : '-' }}</template>
          </el-table-column>
          <el-table-column label="Token" width="80">
            <template #default="{ row }">{{ formatNumber(row.total_tokens) }}</template>
          </el-table-column>
          <el-table-column prop="error" label="错误摘要" min-width="140" show-overflow-tooltip />
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button v-if="row.chat_id" link type="primary" size="small" @click="goChat(row.chat_id)">
                打开会话
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="drawer-pagination">
          <el-pagination
            :current-page="recordsPage"
            :page-size="recordsPageSize"
            :total="recordsTotal"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @current-change="onRecordsPageChange"
            @size-change="onRecordsSizeChange"
          />
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<style lang="less" scoped>
.statistics-page {
  --page-bg: #f4f7fb;
  --panel-bg: rgba(255, 255, 255, 0.78);
  --panel-border: rgba(151, 164, 186, 0.22);
  --text-main: #122033;
  --text-sub: #5d6b82;
  --text-faint: #8c98ad;
  --shadow-soft: 0 18px 45px rgba(25, 47, 89, 0.10);
  --accent: #2864ff;
  --accent-soft: rgba(40, 100, 255, 0.10);
  --accent-emerald: #16a085;
  --accent-violet: #6756ff;
  --accent-amber: #f59e0b;
  --accent-cyan: #0891b2;
  --accent-rose: #ef5a78;

  position: relative;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(40, 100, 255, 0.14), transparent 28%),
    radial-gradient(circle at top right, rgba(103, 86, 255, 0.10), transparent 24%),
    linear-gradient(180deg, #f8fbff 0%, var(--page-bg) 42%, #eef3f9 100%);
  overflow: hidden;

  .page-ornament {
    position: absolute;
    border-radius: 999px;
    filter: blur(6px);
    pointer-events: none;
    opacity: 0.7;
  }

  .page-ornament-left {
    width: 220px;
    height: 220px;
    left: -90px;
    top: 20px;
    background: radial-gradient(circle, rgba(40, 100, 255, 0.22) 0%, rgba(40, 100, 255, 0) 72%);
  }

  .page-ornament-right {
    width: 280px;
    height: 280px;
    right: -140px;
    top: 90px;
    background: radial-gradient(circle, rgba(103, 86, 255, 0.18) 0%, rgba(103, 86, 255, 0) 74%);
  }

  .hero-panel,
  .statistics-panel,
  .spotlight-card,
  .stat-card {
    position: relative;
    border: 1px solid var(--panel-border);
    background: var(--panel-bg);
    box-shadow: var(--shadow-soft);
    backdrop-filter: blur(18px);
  }

  .hero-panel {
    margin-bottom: 24px;
    padding: 26px 28px;
    border-radius: 28px;
    overflow: hidden;

    &::before {
      content: '';
      position: absolute;
      inset: 0;
      background:
        linear-gradient(135deg, rgba(255, 255, 255, 0.72) 0%, rgba(255, 255, 255, 0.28) 52%, rgba(40, 100, 255, 0.08) 100%);
      pointer-events: none;
    }
  }

  .hero-copy,
  .filter-panel,
  .statistics-content,
  .overview-shell,
  .drawer-body {
    position: relative;
    z-index: 1;
  }

  .hero-eyebrow {
    display: inline-flex;
    align-items: center;
    padding: 6px 12px;
    margin-bottom: 14px;
    border-radius: 999px;
    background: rgba(18, 32, 51, 0.06);
    color: var(--text-sub);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  .hero-title-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 22px;
  }

  .statistics-title {
    margin: 0 0 8px;
    font-size: 32px;
    font-weight: 700;
    letter-spacing: -0.03em;
    color: var(--text-main);
  }

  .hero-subtitle {
    margin: 0;
    max-width: 700px;
    color: var(--text-sub);
    font-size: 14px;
    line-height: 1.7;
  }

  .hero-pill {
    min-width: 220px;
    padding: 14px 18px;
    border-radius: 20px;
    background: linear-gradient(135deg, rgba(18, 32, 51, 0.95), rgba(40, 100, 255, 0.92));
    color: #fff;
    box-shadow: 0 20px 45px rgba(33, 56, 112, 0.22);

    .hero-pill-label {
      display: block;
      margin-bottom: 6px;
      font-size: 11px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: rgba(255, 255, 255, 0.72);
    }

    strong {
      font-size: 15px;
      font-weight: 600;
      line-height: 1.5;
    }
  }

  .filter-panel {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 16px;
    padding: 20px;
    border-radius: 22px;
    background: rgba(255, 255, 255, 0.72);
    border: 1px solid rgba(255, 255, 255, 0.9);
  }

  .filter-labels {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .time-label {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-main);
  }

  .filter-caption {
    font-size: 12px;
    color: var(--text-faint);
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .query-button {
    min-width: 92px;
    height: 40px;
    border-radius: 12px;
    box-shadow: 0 10px 20px rgba(40, 100, 255, 0.22);
  }

  .statistics-content {
    display: flex;
    flex-direction: column;
    gap: 22px;
  }

  .overview-shell {
    display: grid;
    grid-template-columns: minmax(260px, 1.15fr) minmax(0, 2fr);
    gap: 18px;
  }

  .spotlight-card {
    padding: 24px;
    border-radius: 24px;
    background:
      radial-gradient(circle at top right, rgba(40, 100, 255, 0.16), transparent 40%),
      linear-gradient(160deg, rgba(16, 26, 48, 0.98), rgba(28, 52, 104, 0.94));
    color: #fff;
    overflow: hidden;
  }

  .spotlight-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 24px;
  }

  .spotlight-tag,
  .spotlight-trace {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.72);
  }

  .spotlight-main {
    display: flex;
    flex-direction: column;
    gap: 18px;
  }

  .spotlight-label {
    margin-bottom: 8px;
    font-size: 13px;
    color: rgba(255, 255, 255, 0.72);
  }

  .spotlight-value {
    display: flex;
    align-items: baseline;
    gap: 10px;
    font-size: 40px;
    font-weight: 700;
    letter-spacing: -0.04em;

    span {
      font-size: 22px;
      color: rgba(255, 255, 255, 0.48);
    }
  }

  .spotlight-metrics {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .spotlight-metric {
    padding: 14px 16px;
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.12);

    span {
      display: block;
      margin-bottom: 6px;
      font-size: 12px;
      color: rgba(255, 255, 255, 0.65);
    }

    strong {
      font-size: 18px;
      font-weight: 700;
      color: #fff;
    }
  }

  .spotlight-note {
    margin: 20px 0 0;
    font-size: 13px;
    line-height: 1.8;
    color: rgba(255, 255, 255, 0.72);
  }

  .statistics-cards {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 16px;
  }

  .stat-card {
    padding: 18px 18px 16px;
    border-radius: 22px;
    transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;

    &:hover {
      transform: translateY(-4px);
      box-shadow: 0 24px 48px rgba(25, 47, 89, 0.13);
    }
  }

  .card-topline {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 22px;
  }

  .label {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-sub);
  }

  .dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: currentColor;
    box-shadow: 0 0 0 6px rgba(0, 0, 0, 0.04);
  }

  .value {
    margin-bottom: 8px;
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.03em;
    color: var(--text-main);
  }

  .hint {
    font-size: 12px;
    color: var(--text-faint);
  }

  .tone-primary {
    color: var(--accent);
    background: linear-gradient(180deg, rgba(40, 100, 255, 0.10), rgba(255, 255, 255, 0.86));
  }

  .tone-emerald {
    color: var(--accent-emerald);
    background: linear-gradient(180deg, rgba(22, 160, 133, 0.10), rgba(255, 255, 255, 0.86));
  }

  .tone-violet {
    color: var(--accent-violet);
    background: linear-gradient(180deg, rgba(103, 86, 255, 0.10), rgba(255, 255, 255, 0.86));
  }

  .tone-amber {
    color: var(--accent-amber);
    background: linear-gradient(180deg, rgba(245, 158, 11, 0.10), rgba(255, 255, 255, 0.86));
  }

  .tone-cyan {
    color: var(--accent-cyan);
    background: linear-gradient(180deg, rgba(8, 145, 178, 0.10), rgba(255, 255, 255, 0.86));
  }

  .tone-rose {
    color: var(--accent-rose);
    background: linear-gradient(180deg, rgba(239, 90, 120, 0.10), rgba(255, 255, 255, 0.86));
  }

  .statistics-panel {
    padding: 22px;
    border-radius: 24px;
  }

  .section-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 18px;

    h3 {
      margin: 0 0 6px;
      font-size: 18px;
      font-weight: 700;
      color: var(--text-main);
      letter-spacing: -0.02em;
    }
  }

  .section-desc {
    margin: 0;
    color: var(--text-sub);
    font-size: 13px;
    line-height: 1.7;
  }

  .section-actions {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .section-tip {
    display: inline-flex;
    align-items: center;
    padding: 8px 12px;
    border-radius: 999px;
    background: rgba(18, 32, 51, 0.06);
    color: var(--text-sub);
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
  }

  .metric-switch {
    :deep(.el-radio-button__inner) {
      border-radius: 12px;
      border: 1px solid rgba(151, 164, 186, 0.28);
      background: rgba(255, 255, 255, 0.8);
      box-shadow: none;
    }
  }

  .trend-panel {
    overflow: hidden;
  }

  .trend-chart {
    height: 320px;
    width: 100%;
  }

  .statistics-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 22px;
  }

  .section-block {
    min-height: 300px;
  }

  .small-chart {
    height: 240px;
    width: 100%;
  }

  .panel-empty {
    min-height: 220px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    border-radius: 18px;
    background:
      linear-gradient(180deg, rgba(248, 251, 255, 0.95), rgba(244, 247, 251, 0.95)),
      repeating-linear-gradient(
        135deg,
        rgba(40, 100, 255, 0.03) 0,
        rgba(40, 100, 255, 0.03) 10px,
        rgba(255, 255, 255, 0.75) 10px,
        rgba(255, 255, 255, 0.75) 20px
      );
    border: 1px dashed rgba(151, 164, 186, 0.35);
    text-align: center;
  }

  .panel-empty.compact {
    min-height: 240px;
  }

  .empty-title {
    margin-bottom: 8px;
    color: var(--text-main);
    font-size: 16px;
    font-weight: 700;
  }

  .empty-text {
    max-width: 260px;
    color: var(--text-faint);
    font-size: 13px;
    line-height: 1.7;
  }

  .list-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    margin-bottom: 16px;
  }

  .toolbar-search {
    max-width: 360px;
  }

  .toolbar-filters {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .statistics-table {
    :deep(.el-table) {
      --el-table-border-color: rgba(151, 164, 186, 0.18);
      --el-table-header-bg-color: #f7f9fc;
      --el-table-row-hover-bg-color: #f5f9ff;
    }

    :deep(th.el-table__cell) {
      color: var(--text-sub);
      font-weight: 700;
      background: #f7f9fc;
    }

    :deep(td.el-table__cell) {
      padding-top: 13px;
      padding-bottom: 13px;
    }
  }

  .table-pagination,
  .drawer-pagination {
    margin-top: 16px;
    display: flex;
    justify-content: flex-end;
  }

  .drawer-body {
    padding: 0 8px 8px;
  }

  .drawer-summary {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    margin-bottom: 14px;
    border-radius: 999px;
    background: var(--accent-soft);
    color: var(--text-sub);
    font-size: 12px;
    font-weight: 600;

    strong {
      color: var(--accent);
      font-size: 13px;
    }
  }
}

:deep(.statistics-drawer .el-drawer__header) {
  margin-bottom: 12px;
  padding-bottom: 0;
  color: #122033;
  font-weight: 700;
}

:deep(.statistics-drawer .el-drawer__body) {
  padding-top: 4px;
}

:deep(.row-fail-top) {
  background: linear-gradient(90deg, rgba(254, 240, 240, 0.92), rgba(255, 247, 237, 0.82)) !important;
}

@media (max-width: 1280px) {
  .statistics-page {
    .overview-shell {
      grid-template-columns: 1fr;
    }

    .statistics-cards {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
}

@media (max-width: 960px) {
  .statistics-page {
    padding: 16px;

    .hero-title-row,
    .filter-panel,
    .section-header,
    .list-toolbar {
      flex-direction: column;
      align-items: stretch;
    }

    .hero-pill,
    .toolbar-search {
      width: 100%;
      max-width: none;
    }

    .header-actions,
    .section-actions,
    .toolbar-filters {
      width: 100%;
      flex-wrap: wrap;
    }

    .statistics-grid,
    .spotlight-metrics,
    .statistics-cards {
      grid-template-columns: 1fr;
    }
  }
}
</style>
