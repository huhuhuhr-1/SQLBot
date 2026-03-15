<template>
  <div class="deep-analysis-page">
    <el-container class="da-layout">
      <!-- 左侧：会话列表（参考智能问数） -->
      <el-aside class="da-aside" width="280px">
        <div class="da-aside-header">
          <span class="da-aside-title">{{ t('menu.deep_analysis') }}</span>
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
            <span class="da-session-brief">{{ item.brief || t('deep_analysis.report_title') }}</span>
            <span class="da-session-time">{{ formatSessionTime(item.create_time) }}</span>
          </div>
        </el-scrollbar>
      </el-aside>

      <!-- 右侧：内容区 -->
      <el-main class="da-main">
        <div class="page-header">
          <div class="header-left">
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

        <div class="config-row">
          <div class="form-item">
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
          <div class="form-item question-item">
            <label>{{ t('deep_analysis.question') }}</label>
            <el-input
              v-model="question"
              type="textarea"
              :rows="3"
              :placeholder="t('deep_analysis.question_placeholder')"
              maxlength="2000"
              show-word-limit
              :disabled="loading"
            />
          </div>
          <div class="form-item">
            <label>{{ t('deep_analysis.max_rows') }}</label>
            <el-input-number
              v-model="maxDataLength"
              :min="100"
              :max="5000"
              :step="100"
              :disabled="loading"
              class="max-rows-input"
            />
          </div>
          <div class="actions">
            <el-button
              type="primary"
              :loading="loading"
              :disabled="!datasourceId || !question.trim()"
              @click="startAnalysis"
            >
              {{ loading ? t('deep_analysis.analyzing') : t('deep_analysis.start') }}
            </el-button>
            <el-button v-if="loading" @click="stopAnalysis">{{ t('deep_analysis.stop') }}</el-button>
          </div>
        </div>

        <div v-if="errorMsg" class="error-block">
          <el-alert type="error" :title="errorMsg" show-icon />
        </div>

        <!-- 主报告：卡片样式 -->
        <div v-if="reportHtml" class="report-block">
          <div class="report-title">{{ t('deep_analysis.report_title') }}</div>
          <div class="report-body markdown-body" v-html="reportHtml"></div>
        </div>

        <!-- 取数 / 推理过程：默认收起 -->
        <div v-if="processChunks.length > 0 || (loading && !reportHtml)" class="process-block">
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
                          <span class="thinking-title">{{ t('deep_analysis.thinking') }} ({{ idx + 1 }})</span>
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

        <div
          v-if="!loading && !errorMsg && !reportHtml && processChunks.length === 0"
          class="empty-tip process-block empty-only"
        >
          {{ t('deep_analysis.empty_tip') }}
        </div>
      </el-main>
    </el-container>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted } from 'vue'
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
const reportMarkdown = ref('')
const reportHtml = ref('')
const processChunks = ref<Array<{ content?: string; reasoning_content?: string; type?: string }>>([])
const processCollapse = ref<string[]>([])
let abortController: AbortController | null = null
let stopFlag = false

const sessionList = ref<ChatInfo[]>([])
const sessionLoading = ref(false)
const currentSessionId = ref<number | undefined>()

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
  reportMarkdown.value = ''
  reportHtml.value = ''
  processChunks.value = []
  processCollapse.value = []
  question.value = ''
}

function selectSession(item: ChatInfo) {
  currentSessionId.value = item.id
  question.value = item.brief || ''
}

async function startAnalysis() {
  if (!datasourceId.value || !question.value.trim()) return
  errorMsg.value = ''
  reportMarkdown.value = ''
  reportHtml.value = ''
  processChunks.value = []
  processCollapse.value = []
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
          if (data.type === 'report' && c) {
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
}
.da-layout {
  height: 100%;
  min-height: 0;
}
.da-aside {
  background: var(--el-fill-color-light);
  border-right: 1px solid var(--el-border-color-lighter);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.da-aside-header {
  padding: 16px;
  flex-shrink: 0;
}
.da-aside-title {
  font-size: 16px;
  font-weight: 600;
  display: block;
  margin-bottom: 12px;
  color: var(--el-text-color-primary);
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
}
.da-session-item {
  padding: 10px 16px;
  cursor: pointer;
  border-bottom: 1px solid var(--el-border-color-lighter);
  transition: background 0.15s;
}
.da-session-item:hover {
  background: var(--el-fill-color);
}
.da-session-item.active {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}
.da-session-brief {
  display: block;
  font-size: 13px;
  color: var(--el-text-color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.da-session-time {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
  display: block;
}

.da-main {
  padding: 16px 24px;
  overflow-y: auto;
  max-width: 960px;
  margin: 0 auto;
  width: 100%;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}
.header-left {
  flex: 1;
  min-width: 0;
}
.page-header .router-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 8px 0;
}
.page-header .page-desc {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin: 0;
}
.export-btn {
  flex-shrink: 0;
}

.config-row .form-item {
  margin-bottom: 16px;
}
.config-row .form-item label {
  display: block;
  font-size: 13px;
  margin-bottom: 6px;
  color: var(--el-text-color-regular);
}
.config-row .form-item .ds-select {
  width: 100%;
  max-width: 360px;
}
.max-rows-input {
  width: 160px;
}
.config-row .question-item :deep(.el-textarea__inner) {
  font-family: inherit;
}
.config-row .actions {
  margin-top: 12px;
}
.config-row .actions .el-button + .el-button {
  margin-left: 8px;
}
.error-block {
  margin: 16px 0;
}

.report-block {
  margin-top: 20px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  padding: 24px;
  background: var(--el-fill-color-blank);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}
.report-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  color: var(--el-text-color-primary);
}
.report-body {
  font-size: 14px;
  line-height: 1.65;
}
.report-body :deep(h2) {
  font-size: 15px;
  margin: 20px 0 10px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  padding-bottom: 6px;
}
.report-body :deep(pre) {
  background: var(--el-fill-color-light);
  padding: 10px;
  border-radius: 4px;
  overflow-x: auto;
}
.report-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 10px 0;
}
.report-body :deep(th),
.report-body :deep(td) {
  border: 1px solid var(--el-border-color-lighter);
  padding: 8px 10px;
}

.process-block {
  margin-top: 16px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 8px 16px 16px;
  background: var(--el-fill-color-blank);
}
.process-block.empty-only {
  text-align: center;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.steps-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.step-item .step-thinking {
  margin-bottom: 6px;
}
.step-item .thinking-title {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.step-item .thinking-content {
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--el-text-color-secondary);
}
.step-item .step-content {
  font-size: 13px;
  line-height: 1.6;
}
.step-item .step-content :deep(pre) {
  background: var(--el-fill-color-light);
  padding: 10px;
  border-radius: 4px;
  overflow-x: auto;
}
.step-item .step-content :deep(code) {
  background: var(--el-fill-color-light);
  padding: 2px 6px;
  border-radius: 4px;
}
.step-item .step-content :deep(table) {
  border-collapse: collapse;
  width: 100%;
}
.step-item .step-content :deep(th),
.step-item .step-content :deep(td) {
  border: 1px solid var(--el-border-color-lighter);
  padding: 6px 10px;
}
.loading-tip {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  padding: 16px 0;
  text-align: center;
}
.loading-tip .el-icon {
  margin-right: 6px;
  vertical-align: middle;
}
</style>
