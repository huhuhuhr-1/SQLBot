<template>
  <div class="deep-analysis-page">
    <el-container class="da-layout">
      <el-aside class="da-aside" width="280px">
        <div class="da-aside-header">
          <div class="da-aside-heading">
            <span class="da-aside-title">{{ t('menu.deep_analysis') }}</span>
            <span class="da-aside-subtitle">{{ sessionCountText }}</span>
          </div>
          <el-button type="primary" class="da-new-btn" @click="goNewAnalysis">
            {{ t('deep_analysis.new_analysis') }}
          </el-button>
        </div>
        <div v-if="sessionList.length === 0 && !sessionLoading" class="da-empty-sessions">
          {{ t('deep_analysis.no_sessions') }}
        </div>
        <el-scrollbar v-else class="da-session-list">
          <div
            v-for="item in sessionList"
            :key="item.id"
            class="da-session-item"
            :class="{ active: currentSessionId === item.id }"
            @click="selectSession(item)"
          >
            <div class="da-session-top">
              <span class="da-session-brief">{{ item.brief || t('deep_analysis.report_title') }}</span>
              <span v-if="currentSessionId === item.id" class="da-session-dot"></span>
            </div>
            <span class="da-session-time">{{ formatSessionTime(item.create_time) }}</span>
          </div>
        </el-scrollbar>
      </el-aside>

      <el-main class="da-main">
        <div class="da-workspace">
          <div class="page-header">
            <div class="header-left">
              <div class="header-kicker">{{ t('deep_analysis.workspace_label') }}</div>
              <p class="router-title">{{ t('menu.deep_analysis') }}</p>
              <p class="page-desc">{{ t('deep_analysis.desc') }}</p>
            </div>
            <el-button
              v-if="reportMarkdown && !loading"
              type="primary"
              plain
              class="export-btn"
              @click="exportReport"
            >
              {{ t('deep_analysis.export_report') }}
            </el-button>
          </div>

          <div class="da-content" :class="{ 'is-welcome': showWelcome }">
            <template v-if="showWelcome">
              <div class="da-welcome-card">
                <div class="da-welcome-badge">{{ t('deep_analysis.workspace_label') }}</div>
                <h2 class="da-welcome-title">{{ t('deep_analysis.starter_title') }}</h2>
                <p class="da-welcome-desc">{{ t('deep_analysis.starter_desc') }}</p>

                <div class="da-capability-grid">
                  <div class="da-capability-card">
                    <span class="capability-index">01</span>
                    <span class="capability-text">{{ t('deep_analysis.capability_plan') }}</span>
                  </div>
                  <div class="da-capability-card">
                    <span class="capability-index">02</span>
                    <span class="capability-text">{{ t('deep_analysis.capability_trace') }}</span>
                  </div>
                  <div class="da-capability-card">
                    <span class="capability-index">03</span>
                    <span class="capability-text">{{ t('deep_analysis.capability_report') }}</span>
                  </div>
                </div>

                <div class="da-example-block">
                  <div class="da-example-title">{{ t('deep_analysis.examples') }}</div>
                  <div class="da-example-list">
                    <button
                      v-for="example in quickExamples"
                      :key="example"
                      type="button"
                      class="da-example-chip"
                      @click="applyExample(example)"
                    >
                      {{ example }}
                    </button>
                  </div>
                </div>
              </div>
            </template>

            <template v-else>
              <div v-if="datasourceId || currentStage || loading || hasContent" class="da-summary-grid">
                <div class="da-summary-card">
                  <div class="summary-label">{{ t('deep_analysis.selected_datasource') }}</div>
                  <div class="summary-value">{{ selectedDatasourceName || '--' }}</div>
                </div>
                <div class="da-summary-card">
                  <div class="summary-label">{{ t('deep_analysis.current_stage') }}</div>
                  <div class="summary-value" :class="{ running: loading }">
                    {{ currentStage || (loading ? t('deep_analysis.waiting') : '--') }}
                  </div>
                </div>
                <div class="da-summary-card">
                  <div class="summary-label">{{ t('deep_analysis.max_rows') }}</div>
                  <div class="summary-value">{{ maxDataLength }}</div>
                </div>
              </div>

              <div v-if="errorMsg" class="error-block">
                <el-alert type="error" :title="errorMsg" show-icon />
              </div>

              <div v-if="!loading && !hasContent" class="da-status-card da-status-card-idle">
                <div class="da-status-icon idle"></div>
                <div class="da-status-body">
                  <div class="da-status-title">{{ t('deep_analysis.empty_tip') }}</div>
                  <div class="da-status-desc">{{ t('deep_analysis.composer_hint') }}</div>
                </div>
              </div>

              <div v-if="loading && !hasContent" class="da-status-card">
                <div class="da-status-icon">
                  <el-icon class="is-loading"><Loading /></el-icon>
                </div>
                <div class="da-status-body">
                  <div class="da-status-title">{{ currentStage || t('deep_analysis.waiting') }}</div>
                  <div class="da-status-desc">{{ t('deep_analysis.starter_desc') }}</div>
                </div>
              </div>

              <div v-if="planHtml" class="plan-block">
                <div class="card-head">
                  <div class="report-title">{{ t('deep_analysis.task_plan') }}</div>
                </div>
                <div class="report-body markdown-body" v-html="planHtml"></div>
              </div>

              <div v-if="reportHtml" class="report-block">
                <div class="card-head">
                  <div class="report-title">{{ t('deep_analysis.report_title') }}</div>
                </div>
                <div class="report-body markdown-body" v-html="reportHtml"></div>
              </div>

              <div v-if="processChunks.length > 0 || (loading && !reportHtml)" class="process-block">
                <div class="card-head">
                  <div class="report-title">{{ t('deep_analysis.process') }}</div>
                </div>
                <el-collapse v-model="processCollapse">
                  <el-collapse-item :title="t('deep_analysis.process_collapsed')" name="1">
                    <div v-if="loading && processChunks.length === 0" class="loading-tip">
                      <el-icon class="is-loading"><Loading /></el-icon>
                      {{ t('deep_analysis.waiting') }}
                    </div>
                    <div class="steps-container">
                      <div v-for="(step, idx) in processChunks" :key="idx" class="step-item">
                        <div v-if="step.reasoning_content" class="step-thinking">
                          <el-collapse>
                            <el-collapse-item :name="idx">
                              <template #title>
                                <span class="thinking-title">{{ t('deep_analysis.thinking') }} {{ idx + 1 }}</span>
                              </template>
                              <div class="thinking-content">{{ step.reasoning_content }}</div>
                            </el-collapse-item>
                          </el-collapse>
                        </div>
                        <div
                          v-if="step.content"
                          class="step-content markdown-body"
                          v-html="renderedContent(step.content)"
                        ></div>
                      </div>
                    </div>
                  </el-collapse-item>
                </el-collapse>
              </div>
            </template>
          </div>

          <div class="da-composer">
            <div class="da-composer-top">
              <div class="composer-field datasource-field">
                <label>{{ t('deep_analysis.datasource') }}</label>
                <el-select
                  v-model="datasourceId"
                  :placeholder="t('deep_analysis.select_datasource')"
                  filterable
                  class="ds-select"
                  :disabled="loading"
                >
                  <el-option
                    v-for="ds in datasourceList"
                    :key="ds.id"
                    :label="ds.name"
                    :value="ds.id"
                  />
                </el-select>
              </div>
              <div class="composer-field rows-field">
                <label>{{ t('deep_analysis.max_rows') }}</label>
                <el-input-number
                  v-model="maxDataLength"
                  :min="100"
                  :max="5000"
                  :step="100"
                  :disabled="loading"
                  class="max-rows-input"
                />
                <span class="field-hint">{{ t('deep_analysis.rows_hint') }}</span>
              </div>
            </div>

            <div class="composer-field question-field">
              <label>{{ t('deep_analysis.question') }}</label>
              <el-input
                v-model="question"
                type="textarea"
                :rows="4"
                :placeholder="t('deep_analysis.question_placeholder')"
                maxlength="2000"
                show-word-limit
                :disabled="loading"
                @keydown.enter.exact.prevent="startAnalysis"
                @keydown.ctrl.enter.exact.prevent="handleCtrlEnter"
              />
            </div>

            <div class="da-composer-bottom">
              <span class="composer-hint">{{ t('deep_analysis.composer_hint') }}</span>
              <div class="composer-actions">
                <el-button v-if="loading" @click="stopAnalysis">{{ t('deep_analysis.stop') }}</el-button>
                <el-button
                  type="primary"
                  :loading="loading"
                  :disabled="!datasourceId || !question.trim()"
                  @click="startAnalysis"
                >
                  {{ loading ? t('deep_analysis.analyzing') : t('deep_analysis.start') }}
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </el-main>
    </el-container>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus-secondary'
import { Loading } from '@element-plus/icons-vue'
import { request } from '@/utils/request'
import { datasourceApi } from '@/api/datasource'
import { deepAnalysisApi } from '@/api/deepAnalysis'
import type { ChatInfo } from '@/api/chat'
import md from '@/utils/markdown.ts'
import dayjs from 'dayjs'
import 'github-markdown-css/github-markdown-light.css'

const { t } = useI18n()

const datasourceList = ref<any[]>([])
const datasourceId = ref<number | undefined>()
const question = ref('')
const maxDataLength = ref(1000)
const loading = ref(false)
const errorMsg = ref('')
const planMarkdown = ref('')
const planHtml = ref('')
const reportMarkdown = ref('')
const reportHtml = ref('')
const processChunks = ref<Array<{ content?: string; reasoning_content?: string; type?: string }>>([])
const processCollapse = ref<string[]>([])
const currentStage = ref('')
let abortController: AbortController | null = null
let stopFlag = false

const sessionList = ref<ChatInfo[]>([])
const sessionLoading = ref(false)
const currentSessionId = ref<number | undefined>()

const hasContent = computed(
  () => !!errorMsg.value || !!planHtml.value || !!reportHtml.value || processChunks.value.length > 0
)
const showWelcome = computed(() => !loading.value && !hasContent.value && !question.value.trim())
const selectedDatasourceName = computed(() => {
  return datasourceList.value.find((item) => item.id === datasourceId.value)?.name || ''
})
const quickExamples = computed(() => [
  t('deep_analysis.example_sales'),
  t('deep_analysis.example_users'),
  t('deep_analysis.example_quality'),
])
const sessionCountText = computed(() => t('deep_analysis.session_count', { count: sessionList.value.length }))

function formatSessionTime(time: Date | string | undefined): string {
  if (!time) return ''
  const d = dayjs(time)
  if (d.isSame(dayjs(), 'day')) return d.format('HH:mm')
  if (d.isAfter(dayjs().subtract(7, 'day'))) return d.format('MM-DD HH:mm')
  return d.format('YYYY-MM-DD')
}

function renderedContent(raw: string): string {
  if (!raw || typeof raw !== 'string') return ''
  try {
    return md.render(raw)
  } catch {
    return String(raw)
  }
}

async function loadSessions() {
  sessionLoading.value = true
  try {
    const list = await deepAnalysisApi.sessions()
    sessionList.value = list || []
  } catch (e) {
    console.error(e)
    sessionList.value = []
  } finally {
    sessionLoading.value = false
  }
}

function goNewAnalysis() {
  currentSessionId.value = undefined
  errorMsg.value = ''
  planMarkdown.value = ''
  planHtml.value = ''
  reportMarkdown.value = ''
  reportHtml.value = ''
  processChunks.value = []
  processCollapse.value = []
  currentStage.value = ''
  question.value = ''
}

function selectSession(item: ChatInfo) {
  currentSessionId.value = item.id
  datasourceId.value = item.datasource
  question.value = item.brief || ''
}

async function startAnalysis() {
  if (!datasourceId.value || !question.value.trim()) return
  errorMsg.value = ''
  planMarkdown.value = ''
  planHtml.value = ''
  reportMarkdown.value = ''
  reportHtml.value = ''
  processChunks.value = []
  processCollapse.value = []
  currentStage.value = ''
  loading.value = true
  stopFlag = false
  abortController = new AbortController()

  try {
    const response = await request.fetchStream(
      '/openapi/deep-analysis',
      {
        datasource_id: datasourceId.value,
        question: question.value.trim(),
        chat_id: currentSessionId.value ?? undefined,
        no_reasoning: false,
        max_data_length: maxDataLength.value,
        is_chart_output: true,
      },
      abortController
    )

    if (!response.ok || !response.body) {
      errorMsg.value = response.statusText || 'Request failed'
      loading.value = false
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let tempResult = ''

    while (true) {
      if (stopFlag) {
        abortController?.abort()
        break
      }
      const { done, value } = await reader.read()
      if (done) break

      tempResult += decoder.decode(value, { stream: true })
      const parts = tempResult.split(/\n\n/)
      tempResult = parts.pop() || ''
      for (const part of parts) {
        const line = part.trim()
        if (!line.startsWith('data:')) continue
        try {
          const data = JSON.parse(line.slice(5).trim())
          if (data.type === 'error') {
            errorMsg.value = data.content || 'Unknown error'
            ElMessage.error(errorMsg.value)
            break
          }
          if (data.type === 'finish') {
            loading.value = false
            if (reportMarkdown.value) {
              reportHtml.value = renderedContent(reportMarkdown.value)
            }
            if (data.chat_id) {
              currentSessionId.value = data.chat_id
              await loadSessions()
            }
            break
          }
          const c = typeof data.content === 'string' ? data.content : ''
          const r = typeof data.reasoning_content === 'string' ? data.reasoning_content : ''
          if (data.type === 'plan' && c) {
            planMarkdown.value = c
            planHtml.value = renderedContent(c)
          } else if (data.type === 'stage' && c) {
            currentStage.value = c.replace(/^当前阶段：/, '').trim()
          } else if (data.type === 'report' && c) {
            reportMarkdown.value = c
            reportHtml.value = renderedContent(c)
          } else if ((data.type === 'process' || data.type === 'analysis-result') && (c || r)) {
            processChunks.value.push({ content: c, reasoning_content: r, type: data.type })
          } else if (c || r) {
            processChunks.value.push({ content: c, reasoning_content: r, type: data.type })
          }
        } catch (e) {
          console.warn('Parse SSE chunk failed', e)
        }
      }
    }
    if (reportMarkdown.value && !reportHtml.value) {
      reportHtml.value = renderedContent(reportMarkdown.value)
    }
  } catch (e: any) {
    if (e?.name !== 'AbortError') {
      errorMsg.value = e?.message || String(e)
      ElMessage.error(errorMsg.value)
    }
  } finally {
    loading.value = false
    abortController = null
  }
}

function stopAnalysis() {
  stopFlag = true
  abortController?.abort()
}

function exportReport() {
  if (!reportMarkdown.value) return
  const payload = {
    question: question.value,
    plan: planMarkdown.value,
    current_stage: currentStage.value,
    report: reportMarkdown.value,
    process_steps: processChunks.value.map((s) => ({
      content: s.content,
      reasoning_content: s.reasoning_content,
      type: s.type,
    })),
    exported_at: dayjs().format('YYYY-MM-DD HH:mm:ss'),
  }
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `深度分析报告_${dayjs().format('YYYYMMDD_HHmmss')}.json`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success(t('deep_analysis.export_success'))
}

function applyExample(example: string) {
  question.value = example
}

function handleCtrlEnter(e: KeyboardEvent) {
  const textarea = e.target as HTMLTextAreaElement
  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  const value = textarea.value
  question.value = value.substring(0, start) + '\n' + value.substring(end)
  requestAnimationFrame(() => {
    textarea.selectionStart = textarea.selectionEnd = start + 1
  })
}

async function loadDatasources() {
  try {
    const res = await datasourceApi.list()
    datasourceList.value = Array.isArray(res) ? res : []
  } catch (e) {
    console.error(e)
    datasourceList.value = []
  }
}

onMounted(() => {
  loadDatasources()
  loadSessions()
})
</script>

<style scoped>
.deep-analysis-page {
  height: 100%;
  min-height: 0;
  background: linear-gradient(180deg, #f7f9fc 0%, #f3f5f8 100%);
}
.da-layout {
  height: 100%;
  min-height: 0;
}
.da-aside {
  background: #f5f6f7;
  border-right: 1px solid rgba(222, 224, 227, 1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.da-aside-header {
  padding: 16px;
  flex-shrink: 0;
}
.da-aside-heading {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}
.da-aside-title {
  font-size: 16px;
  font-weight: 600;
  color: rgba(31, 35, 41, 1);
}
.da-aside-subtitle {
  font-size: 12px;
  color: rgba(100, 106, 115, 1);
}
.da-new-btn {
  width: 100%;
}
.da-empty-sessions {
  padding: 16px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  text-align: center;
}
.da-session-list {
  flex: 1;
  min-height: 0;
  padding: 0 8px 12px;
}
.da-session-item {
  margin-bottom: 8px;
  padding: 12px;
  cursor: pointer;
  border: 1px solid transparent;
  border-radius: 12px;
  transition:
    background 0.15s,
    border-color 0.15s,
    box-shadow 0.15s;
}
.da-session-item:hover {
  background: rgba(255, 255, 255, 0.72);
}
.da-session-item.active {
  background: rgba(255, 255, 255, 0.92);
  border-color: rgba(28, 186, 144, 0.18);
  box-shadow: 0 8px 20px rgba(31, 35, 41, 0.06);
}
.da-session-top {
  display: flex;
  align-items: center;
  gap: 8px;
}
.da-session-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--el-color-primary);
  flex-shrink: 0;
}
.da-session-brief {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: rgba(31, 35, 41, 1);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}
.da-session-time {
  font-size: 12px;
  color: rgba(100, 106, 115, 1);
  margin-top: 6px;
  display: block;
}

.da-main {
  padding: 20px 24px;
  overflow: hidden;
  max-width: 1120px;
  margin: 0 auto;
  width: 100%;
}
.da-workspace {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.header-left {
  flex: 1;
  min-width: 0;
}
.header-kicker {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(28, 186, 144, 0.1);
  color: var(--el-color-primary);
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 10px;
}
.page-header .router-title {
  font-size: 28px;
  line-height: 1.2;
  font-weight: 600;
  margin: 0 0 10px 0;
  color: rgba(31, 35, 41, 1);
}
.page-header .page-desc {
  font-size: 14px;
  color: rgba(100, 106, 115, 1);
  margin: 0;
}
.export-btn {
  flex-shrink: 0;
  align-self: flex-start;
}
.da-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-right: 4px;
}
.da-content.is-welcome {
  justify-content: center;
}
.da-welcome-card,
.da-status-card,
.da-composer,
.report-block,
.plan-block,
.process-block,
.da-summary-card {
  border: 1px solid rgba(222, 224, 227, 1);
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 10px 30px rgba(31, 35, 41, 0.04);
  backdrop-filter: blur(10px);
}
.da-welcome-card {
  max-width: 860px;
  margin: 0 auto;
  padding: 36px;
  border-radius: 24px;
}
.da-welcome-badge {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(31, 35, 41, 0.06);
  color: rgba(31, 35, 41, 0.72);
  font-size: 12px;
  font-weight: 600;
}
.da-welcome-title {
  margin: 18px 0 10px;
  font-size: 36px;
  line-height: 1.2;
  font-weight: 600;
  color: rgba(31, 35, 41, 1);
}
.da-welcome-desc {
  margin: 0;
  max-width: 680px;
  font-size: 15px;
  line-height: 1.8;
  color: rgba(100, 106, 115, 1);
}
.da-capability-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-top: 28px;
}
.da-capability-card {
  padding: 18px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(248, 249, 250, 1), rgba(255, 255, 255, 1));
  border: 1px solid rgba(222, 224, 227, 1);
}
.capability-index {
  display: block;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--el-color-primary);
  margin-bottom: 10px;
}
.capability-text {
  display: block;
  font-size: 14px;
  line-height: 1.6;
  color: rgba(31, 35, 41, 1);
}
.da-example-block {
  margin-top: 28px;
}
.da-example-title {
  font-size: 13px;
  font-weight: 600;
  color: rgba(31, 35, 41, 0.88);
  margin-bottom: 12px;
}
.da-example-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.da-example-chip {
  border: 1px solid rgba(217, 220, 223, 1);
  background: rgba(248, 249, 250, 1);
  color: rgba(31, 35, 41, 0.88);
  border-radius: 999px;
  padding: 10px 14px;
  font-size: 13px;
  line-height: 1.5;
  cursor: pointer;
  transition:
    color 0.15s,
    border-color 0.15s,
    background 0.15s;
}
.da-example-chip:hover {
  color: var(--el-color-primary);
  border-color: rgba(28, 186, 144, 0.35);
  background: rgba(28, 186, 144, 0.08);
}
.error-block {
  margin: 0;
}
.da-summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
.da-summary-card {
  border-radius: 18px;
  padding: 18px 20px;
}
.summary-label {
  font-size: 12px;
  color: rgba(100, 106, 115, 1);
  margin-bottom: 10px;
}
.summary-value {
  font-size: 16px;
  line-height: 1.5;
  font-weight: 600;
  color: rgba(31, 35, 41, 1);
  word-break: break-word;
}
.summary-value.running {
  color: var(--el-color-primary);
}
.da-status-card {
  display: flex;
  align-items: center;
  gap: 16px;
  border-radius: 20px;
  padding: 22px 24px;
}
.da-status-icon {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(28, 186, 144, 0.1);
  color: var(--el-color-primary);
  font-size: 20px;
  flex-shrink: 0;
}
.da-status-icon.idle {
  background: rgba(31, 35, 41, 0.08);
  color: rgba(31, 35, 41, 0.5);
}
.da-status-icon.idle::before {
  content: '';
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: currentColor;
}
.da-status-body {
  min-width: 0;
}
.da-status-title {
  font-size: 16px;
  font-weight: 600;
  color: rgba(31, 35, 41, 1);
}
.da-status-desc {
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.6;
  color: rgba(100, 106, 115, 1);
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.report-block {
  border-radius: 24px;
  padding: 24px;
}
.plan-block {
  border-color: rgba(28, 186, 144, 0.18);
  border-radius: 24px;
  padding: 24px;
  background: linear-gradient(180deg, rgba(28, 186, 144, 0.08), rgba(255, 255, 255, 0.92));
}
.report-title {
  font-size: 18px;
  font-weight: 600;
  color: rgba(31, 35, 41, 1);
}
.report-body {
  font-size: 14px;
  line-height: 1.75;
  color: rgba(31, 35, 41, 0.92);
}
.report-body :deep(h2) {
  font-size: 16px;
  margin: 20px 0 10px;
  border-bottom: 1px solid rgba(222, 224, 227, 1);
  padding-bottom: 6px;
}
.report-body :deep(pre) {
  background: rgba(245, 246, 247, 1);
  padding: 12px;
  border-radius: 12px;
  overflow-x: auto;
}
.report-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 10px 0;
}
.report-body :deep(th),
.report-body :deep(td) {
  border: 1px solid rgba(222, 224, 227, 1);
  padding: 8px 10px;
}

.process-block {
  border-radius: 24px;
  padding: 24px;
}
.steps-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.step-item {
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(248, 249, 250, 0.88);
  border: 1px solid rgba(222, 224, 227, 1);
}
.step-item .step-thinking {
  margin-bottom: 6px;
}
.step-item .thinking-title {
  font-size: 12px;
  color: rgba(100, 106, 115, 1);
}
.step-item .thinking-content {
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-word;
  color: rgba(100, 106, 115, 1);
}
.step-item .step-content {
  font-size: 13px;
  line-height: 1.6;
}
.step-item .step-content :deep(pre) {
  background: rgba(255, 255, 255, 1);
  padding: 10px;
  border-radius: 10px;
  overflow-x: auto;
}
.step-item .step-content :deep(code) {
  background: rgba(255, 255, 255, 1);
  padding: 2px 6px;
  border-radius: 4px;
}
.step-item .step-content :deep(table) {
  border-collapse: collapse;
  width: 100%;
}
.step-item .step-content :deep(th),
.step-item .step-content :deep(td) {
  border: 1px solid rgba(222, 224, 227, 1);
  padding: 6px 10px;
}
.loading-tip {
  color: rgba(100, 106, 115, 1);
  font-size: 13px;
  padding: 12px 0 8px;
  text-align: center;
}
.loading-tip .el-icon {
  margin-right: 6px;
  vertical-align: middle;
}
.da-composer {
  border-radius: 24px;
  padding: 18px;
}
.da-composer-top {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(220px, 0.8fr);
  gap: 16px;
  margin-bottom: 16px;
}
.composer-field {
  min-width: 0;
}
.composer-field label {
  display: block;
  font-size: 13px;
  line-height: 1.5;
  margin-bottom: 8px;
  color: rgba(100, 106, 115, 1);
}
.composer-field .ds-select {
  width: 100%;
}
.rows-field {
  display: flex;
  flex-direction: column;
}
.max-rows-input {
  width: 180px;
}
.field-hint {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.5;
  color: rgba(143, 149, 158, 1);
}
.question-field :deep(.el-textarea__inner) {
  font-family: inherit;
  padding: 14px 16px;
  min-height: 128px;
  border-radius: 18px;
  background: rgba(248, 249, 250, 1);
  line-height: 1.7;
}
.da-composer-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 14px;
}
.composer-hint {
  font-size: 12px;
  color: rgba(143, 149, 158, 1);
}
.composer-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

@media (max-width: 1100px) {
  .da-capability-grid,
  .da-summary-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .da-layout {
    flex-direction: column;
  }
  .da-aside {
    width: 100% !important;
    max-height: 220px;
    border-right: none;
    border-bottom: 1px solid rgba(222, 224, 227, 1);
  }
  .da-main {
    padding: 16px;
  }
  .da-composer-top,
  .da-composer-bottom {
    grid-template-columns: 1fr;
    display: flex;
    flex-direction: column;
    align-items: stretch;
  }
  .composer-actions {
    justify-content: flex-end;
  }
  .da-welcome-card {
    padding: 24px;
  }
  .da-welcome-title {
    font-size: 28px;
  }
}
</style>
