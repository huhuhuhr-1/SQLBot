<script lang="ts" setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus-secondary'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { Chart } from '@antv/g2'
import { statisticsApi, type DatasourceStats, type StatisticsOverviewResponse, type UserStats, type RecordItem } from '@/api/statistics'

const router = useRouter()

const loading = ref(false)
const data = ref<StatisticsOverviewResponse | null>(null)

// 时间范围，默认最近 30 天
const dateRange = ref<[string, string]>([
  dayjs().subtract(30, 'day').format('YYYY-MM-DD 00:00:00'),
  dayjs().format('YYYY-MM-DD 23:59:59'),
])

const overviewParams = computed(() => {
  if (!dateRange.value || dateRange.value.length !== 2) return {}
  return {
    start_time: dayjs(dateRange.value[0]).toISOString(),
    end_time: dayjs(dateRange.value[1]).toISOString(),
  }
})

const loadData = async () => {
  loading.value = true
  try {
    const res = await statisticsApi.getOverview(overviewParams.value)
    data.value = res
  } catch (e: any) {
    ElMessage.error(e?.message || '加载统计数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})

const formatPercent = (val: number | null | undefined) => {
  if (!val) return '0%'
  return `${(val * 100).toFixed(1)}%`
}

// 失败 TopN（前 5）用于高亮
const FAIL_TOP_N = 5
const failTopDatasourceIds = computed(() => {
  if (!data.value?.by_datasource?.length) return new Set<number | null>()
  const sorted = [...data.value.by_datasource].sort((a, b) => (b.failed_queries || 0) - (a.failed_queries || 0))
  return new Set(sorted.slice(0, FAIL_TOP_N).map((d) => d.datasource_id).filter((id): id is number => id != null))
})
const failTopUserIds = computed(() => {
  if (!data.value?.by_user?.length) return new Set<number | null>()
  const sorted = [...data.value.by_user].sort((a, b) => (b.failed_queries || 0) - (a.failed_queries || 0))
  return new Set(sorted.slice(0, FAIL_TOP_N).map((u) => u.user_id).filter((id): id is number => id != null))
})

const dsRowClassName = ({ row }: { row: DatasourceStats }) =>
  row.datasource_id != null && failTopDatasourceIds.value.has(row.datasource_id) ? 'row-fail-top' : ''
const userRowClassName = ({ row }: { row: UserStats }) =>
  row.user_id != null && failTopUserIds.value.has(row.user_id) ? 'row-fail-top' : ''

// 趋势图
const chartContainer = ref<HTMLDivElement | null>(null)
let chartInstance: Chart | null = null

function buildTrendChart() {
  if (!chartContainer.value || !data.value?.daily_trend?.length) return
  const trend = data.value.daily_trend
  const flat: { date: string; type: string; value: number }[] = []
  trend.forEach((d) => {
    const dateStr = dayjs(d.date).format('MM-DD')
    flat.push({ date: dateStr, type: '总问数', value: d.total_queries })
    flat.push({ date: dateStr, type: '成功', value: d.success_queries })
    flat.push({ date: dateStr, type: '失败', value: d.failed_queries })
  })
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
  chartInstance = new Chart({
    container: chartContainer.value,
    autoFit: true,
    paddingTop: 24,
    paddingRight: 16,
    paddingBottom: 32,
    paddingLeft: 48,
  })
  chartInstance.options({
    type: 'view',
    data: flat,
    encode: { x: 'date', y: 'value', color: 'type' },
    scale: {
      x: { nice: true },
      y: { nice: true, min: 0 },
    },
    axis: {
      x: { title: false, labelFontSize: 10 },
      y: { title: false },
    },
    legend: { color: { position: 'top-right' } },
    children: [
      {
        type: 'line',
        encode: { shape: 'smooth' },
      },
      {
        type: 'point',
        encode: { size: 2 },
        style: { fill: 'white', stroke: (d: any) => d.color },
      },
    ],
  })
  chartInstance.render()
}

watch(
  () => data.value?.daily_trend,
  async () => {
    await nextTick()
    buildTrendChart()
  },
  { deep: true }
)
onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
})

// 明细抽屉
const drawerVisible = ref(false)
const drawerTitle = ref('问数明细')
const recordFilter = ref<{ user_id?: number; user_name?: string; datasource_id?: number; datasource_name?: string }>({})
const records = ref<RecordItem[]>([])
const recordsTotal = ref(0)
const recordsPage = ref(1)
const recordsPageSize = ref(20)
const recordsLoading = ref(false)

const recordParams = computed(() => ({
  page: recordsPage.value,
  size: recordsPageSize.value,
  ...(overviewParams.value as { start_time?: string; end_time?: string }),
  user_id: recordFilter.value.user_id,
  datasource_id: recordFilter.value.datasource_id,
  failed_only: false,
}))

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

function openDsDetail(row: DatasourceStats) {
  recordFilter.value = {
    datasource_id: row.datasource_id ?? undefined,
    datasource_name: row.datasource_name ?? undefined,
  }
  drawerTitle.value = row.datasource_name ? `问数明细 - ${row.datasource_name}` : '问数明细'
  recordsPage.value = 1
  drawerVisible.value = true
  loadRecords()
}

function openUserDetail(row: UserStats) {
  recordFilter.value = {
    user_id: row.user_id ?? undefined,
    user_name: row.user_name ?? undefined,
  }
  drawerTitle.value = row.user_name ? `问数明细 - ${row.user_name}` : '问数明细'
  recordsPage.value = 1
  drawerVisible.value = true
  loadRecords()
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
    <div class="statistics-header">
      <h2 class="statistics-title">统计分析</h2>
      <div class="header-actions">
        <span class="time-label">时间范围</span>
        <el-date-picker
          v-model="dateRange"
          type="datetimerange"
          range-separator="至"
          start-placeholder="开始"
          end-placeholder="结束"
          value-format="YYYY-MM-DD HH:mm:ss"
          :shortcuts="[
            { text: '最近7天', value: () => [dayjs().subtract(7, 'day').toDate(), dayjs().toDate()] },
            { text: '最近30天', value: () => [dayjs().subtract(30, 'day').toDate(), dayjs().toDate()] },
          ]"
          style="width: 360px"
        />
        <el-button type="primary" @click="loadData">查询</el-button>
      </div>
    </div>

    <div v-if="data" class="statistics-content">
      <section class="statistics-cards">
        <div class="stat-card">
          <div class="label">总问数</div>
          <div class="value">{{ data.overview.total_queries }}</div>
        </div>
        <div class="stat-card">
          <div class="label">成功率</div>
          <div class="value">{{ formatPercent(data.overview.success_rate) }}</div>
        </div>
        <div class="stat-card">
          <div class="label">活跃用户数</div>
          <div class="value">{{ data.overview.active_users }}</div>
        </div>
        <div class="stat-card">
          <div class="label">活跃数据源数</div>
          <div class="value">{{ data.overview.active_datasources }}</div>
        </div>
      </section>

      <section v-if="data.daily_trend?.length" class="statistics-section">
        <div class="section-header">
          <h3>每日趋势</h3>
        </div>
        <div ref="chartContainer" class="trend-chart" />
      </section>

      <section class="statistics-section">
        <div class="section-header">
          <h3>按数据源统计</h3>
          <span class="section-tip">失败次数前 5 行高亮</span>
        </div>
        <el-table
          :data="data.by_datasource"
          border
          size="small"
          :row-class-name="dsRowClassName"
          style="width: 100%"
        >
          <el-table-column prop="datasource_name" label="数据源" min-width="160" />
          <el-table-column prop="total_queries" label="问数" width="100" />
          <el-table-column
            prop="success_rate"
            label="成功率"
            width="120"
            :formatter="(_: unknown, __: unknown, value: unknown) => formatPercent(value as number)"
          />
          <el-table-column prop="failed_queries" label="失败/异常次数" width="140" />
          <el-table-column prop="active_users" label="活跃用户数" width="120" />
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="openDsDetail(row)">查看明细</el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <section class="statistics-section">
        <div class="section-header">
          <h3>按用户统计</h3>
          <span class="section-tip">失败次数前 5 行高亮</span>
        </div>
        <el-table
          :data="data.by_user"
          border
          size="small"
          :row-class-name="userRowClassName"
          style="width: 100%"
        >
          <el-table-column prop="user_name" label="用户" min-width="160" />
          <el-table-column prop="total_queries" label="问数" width="100" />
          <el-table-column
            prop="success_rate"
            label="成功率"
            width="120"
            :formatter="(_: unknown, __: unknown, value: unknown) => formatPercent(value as number)"
          />
          <el-table-column prop="failed_queries" label="失败/异常次数" width="140" />
          <el-table-column prop="active_datasources" label="访问数据源数" width="120" />
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="openUserDetail(row)">查看明细</el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </div>

    <el-drawer
      v-model="drawerVisible"
      :title="drawerTitle"
      size="70%"
      direction="rtl"
      @open="loadRecords"
    >
      <div v-loading="recordsLoading" class="drawer-body">
        <el-table :data="records" border size="small" style="width: 100%">
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
          <el-table-column prop="error" label="错误摘要" min-width="160" show-overflow-tooltip />
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="row.chat_id"
                link
                type="primary"
                size="small"
                @click="goChat(row.chat_id)"
              >
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
  padding: 16px 24px;

  .statistics-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 16px;

    .statistics-title {
      font-size: 18px;
      font-weight: 500;
      color: #1f2329;
      margin: 0;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 8px;

      .time-label {
        font-size: 14px;
        color: #646a73;
      }
    }
  }

  .statistics-cards {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 20px;

    .stat-card {
      padding: 12px 16px;
      border-radius: 8px;
      background: #f5f6f7;
      border: 1px solid #e5e6eb;
      .label {
        font-size: 12px;
        color: #646a73;
        margin-bottom: 4px;
      }
      .value {
        font-size: 18px;
        font-weight: 600;
        color: #1f2329;
      }
    }
  }

  .trend-chart {
    height: 280px;
    width: 100%;
  }

  .statistics-section {
    margin-bottom: 24px;

    .section-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;

      h3 {
        font-size: 14px;
        font-weight: 500;
        color: #1f2329;
        margin: 0;
      }

      .section-tip {
        font-size: 12px;
        color: #8f959e;
      }
    }
  }

  .drawer-body {
    padding: 0 8px;

    .drawer-pagination {
      margin-top: 16px;
      display: flex;
      justify-content: flex-end;
    }
  }
}

:deep(.row-fail-top) {
  background-color: #fef0f0 !important;
}
</style>
