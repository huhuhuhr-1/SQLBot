<template>
  <div class="da-page">
    <el-container class="da-layout">
      <!-- 左侧：会话列表 -->
      <el-aside v-if="sidebarShow" class="da-sidebar" width="280px">
        <header class="da-sidebar-header">
          <div class="da-sidebar-title-row">
            <span class="da-sidebar-title">{{ t('menu.deep_analysis') }}</span>
            <el-button link class="da-icon-btn" @click="sidebarShow = false">
              <el-icon><icon_sidebar_outlined /></el-icon>
            </el-button>
          </div>
          <el-button type="primary" class="da-new-btn" @click="newChat">
            <el-icon style="margin-right: 6px"><icon_new_chat_outlined /></el-icon>
            {{ t('deep_analysis.new_analysis') }}
          </el-button>
          <el-input
            v-model="sessionSearch"
            :prefix-icon="Search"
            clearable
            size="small"
            :placeholder="t('deep_analysis.session_search_placeholder')"
          />
        </header>
        <el-scrollbar class="da-session-scroll">
          <div class="da-session-list">
            <div v-if="!filteredSessions.length" class="da-empty">
              {{ t('deep_analysis.no_sessions') }}
            </div>
            <div v-for="group in sessionGroups" :key="group.key" class="da-group">
              <div class="da-group-title" @click="groupExpand[group.key] = !groupExpand[group.key]">
                <el-icon :class="{ collapsed: !groupExpand[group.key] }" size="10"
                  ><icon_expand_down_filled
                /></el-icon>
                {{ group.key }}
              </div>
              <template v-for="item in group.list" :key="item.id">
                <div
                  v-show="groupExpand[group.key]"
                  class="da-session-item"
                  :class="{ active: currentSessionId === item.id }"
                  @click="selectSession(item)"
                >
                  <span class="da-session-brief">{{
                    item.brief || t('deep_analysis.report_title')
                  }}</span>
                  <el-popover
                    trigger="click"
                    :teleported="false"
                    popper-class="da-session-popover"
                    placement="bottom"
                  >
                    <template #reference>
                      <el-icon class="da-session-more" size="14" @click.stop
                        ><icon_more_outlined
                      /></el-icon>
                    </template>
                    <div class="da-popover-menu">
                      <div class="da-popover-item" @click.stop="openRename(item)">
                        <el-icon size="14"><icon_rename /></el-icon>{{ t('dashboard.rename') }}
                      </div>
                      <div class="da-popover-item danger" @click.stop="deleteSession(item)">
                        <el-icon size="14"><icon_delete /></el-icon>{{ t('dashboard.delete') }}
                      </div>
                    </div>
                  </el-popover>
                </div>
              </template>
            </div>
          </div>
        </el-scrollbar>
      </el-aside>

      <!-- 收起时的浮动按钮 -->
      <div v-if="!sidebarShow" class="da-float-btns">
        <el-button link class="da-icon-btn" @click="sidebarShow = true">
          <el-icon><icon_sidebar_outlined /></el-icon>
        </el-button>
        <el-tooltip :content="t('deep_analysis.new_analysis')" placement="bottom">
          <el-button link class="da-icon-btn" @click="newChat">
            <el-icon><icon_new_chat_outlined /></el-icon>
          </el-button>
        </el-tooltip>
      </div>

      <!-- 中间：聊天窗口 -->
      <el-main class="da-chat-main">
        <div class="da-chat-container">
          <!-- 消息列表 -->
          <el-scrollbar ref="chatScrollRef" class="da-messages-scroll">
            <div class="da-messages">
              <!-- 欢迎态 -->
              <div v-if="!messages.length && !loading" class="da-welcome">
                <div class="da-welcome-icon">🤖</div>
                <h2 class="da-welcome-title">{{ t('deep_analysis.starter_title') }}</h2>
                <p class="da-welcome-desc">{{ t('deep_analysis.starter_desc') }}</p>
              </div>
              <!-- 消息气泡 -->
              <template v-for="(msg, idx) in messages" :key="idx">
                <!-- 用户消息 -->
                <div v-if="msg.role === 'user'" class="da-msg da-msg-user">
                  <div class="da-msg-bubble da-bubble-user">{{ msg.content }}</div>
                </div>
                <!-- Agent 消息 -->
                <div v-else class="da-msg da-msg-agent">
                  <div class="da-msg-bubble da-bubble-agent">
                    <!-- 步骤时间线 -->
                    <div v-if="msg.steps && msg.steps.length" class="da-steps-timeline">
                      <div
                        v-for="(step, sIdx) in msg.steps"
                        :key="sIdx"
                        class="da-step-item"
                        :class="{
                          'da-step-active': step.status === 'running',
                          'da-step-done': step.status === 'done',
                        }"
                      >
                        <div class="da-step-indicator">
                          <el-icon
                            v-if="step.status === 'running'"
                            class="is-loading da-step-icon-loading"
                            ><Loading
                          /></el-icon>
                          <span v-else-if="step.status === 'done'" class="da-step-check">✓</span>
                          <span v-else class="da-step-dot"></span>
                        </div>
                        <div class="da-step-body">
                          <div class="da-step-title" @click="step.expanded = !step.expanded">
                            <span class="da-step-label">{{ step.title }}</span>
                            <el-icon
                              v-if="step.details"
                              class="da-step-toggle"
                              :class="{ 'da-step-toggle-open': step.expanded }"
                              size="12"
                              ><ArrowRight
                            /></el-icon>
                          </div>
                          <transition name="da-step-expand">
                            <div
                              v-if="step.expanded && step.details"
                              class="da-step-details markdown-body"
                              v-html="step.details"
                            ></div>
                          </transition>
                        </div>
                      </div>
                    </div>
                    <!-- 主文本 -->
                    <div
                      v-if="msg.contentHtml"
                      class="markdown-body da-agent-text"
                      v-html="msg.contentHtml"
                    ></div>
                    <div v-else-if="msg.content" class="da-agent-text">{{ msg.content }}</div>
                    <!-- 报告卡片（可点击） -->
                    <div v-if="msg.reportHtml" class="da-report-card" @click="openReport(msg)">
                      <el-icon size="20" class="da-report-icon"><Document /></el-icon>
                      <span class="da-report-card-text">📊 查看分析报告</span>
                      <el-icon size="16"><ArrowRight /></el-icon>
                    </div>
                  </div>
                </div>
              </template>
              <!-- 加载状态 -->
              <div v-if="loading" class="da-msg da-msg-agent">
                <div class="da-msg-bubble da-bubble-agent da-loading-bubble">
                  <el-icon class="is-loading"><Loading /></el-icon>
                  <span>{{ currentStage || t('deep_analysis.waiting') }}</span>
                </div>
              </div>
            </div>
          </el-scrollbar>

          <!-- 输入栏 -->
          <div class="da-input-bar">
            <el-input
              v-model="question"
              :placeholder="t('deep_analysis.question_placeholder')"
              :disabled="loading"
              size="large"
              class="da-input"
              @keydown.enter.exact.prevent="sendMessage"
            >
              <template #append>
                <el-button
                  :icon="loading ? undefined : Promotion"
                  :loading="loading"
                  type="primary"
                  class="da-send-btn"
                  :disabled="!question.trim()"
                  @click="sendMessage"
                >
                </el-button>
              </template>
            </el-input>
          </div>
        </div>
      </el-main>

      <!-- 右侧：报告面板 -->
      <transition name="da-panel-slide">
        <aside v-if="reportPanelOpen" class="da-report-panel">
          <header class="da-report-header">
            <span class="da-report-title">{{ t('deep_analysis.report_title') }}</span>
            <div class="da-report-actions">
              <el-button
                v-if="activeReportMd"
                type="primary"
                plain
                size="small"
                @click="exportReport"
              >
                {{ t('deep_analysis.export_report') }}
              </el-button>
              <el-button link class="da-icon-btn" @click="reportPanelOpen = false">
                <el-icon><Close /></el-icon>
              </el-button>
            </div>
          </header>
          <el-scrollbar class="da-report-body-scroll">
            <div class="markdown-body da-report-body" v-html="activeReportHtml"></div>
          </el-scrollbar>
        </aside>
      </transition>
    </el-container>

    <!-- 重命名弹窗 -->
    <el-dialog
      v-model="renameVisible"
      :title="t('qa.rename_conversation_title')"
      width="420"
      destroy-on-close
    >
      <el-input v-model="renameValue" maxlength="100" show-word-limit clearable />
      <template #footer>
        <el-button @click="renameVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="renameLoading" @click="submitRename">{{
          t('common.save')
        }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus-secondary'
import { Search, Loading, Close, Promotion, ArrowRight, Document } from '@element-plus/icons-vue'
import { request } from '@/utils/request'
import { deepAnalysisApi } from '@/api/deepAnalysis'
import { chatApi } from '@/api/chat'
import type { ChatInfo } from '@/api/chat'
import md from '@/utils/markdown.ts'
import dayjs from 'dayjs'
import { getDate } from '@/utils/utils'
import { groupBy } from 'lodash-es'
import icon_new_chat_outlined from '@/assets/svg/icon_new_chat_outlined.svg'
import icon_sidebar_outlined from '@/assets/svg/icon_sidebar_outlined.svg'
import icon_expand_down_filled from '@/assets/svg/icon_expand-down_filled.svg'
import icon_more_outlined from '@/assets/svg/icon_more_outlined.svg'
import icon_rename from '@/assets/svg/icon_rename_outlined.svg'
import icon_delete from '@/assets/svg/icon_delete.svg'
import 'github-markdown-css/github-markdown-light.css'

const { t } = useI18n()

// ===== Types =====
interface StepItem {
  title: string
  status: 'pending' | 'running' | 'done'
  details: string
  detailsMd: string
  expanded: boolean
}

interface ChatMessage {
  role: 'user' | 'agent'
  content: string
  contentHtml?: string
  processHtml?: string
  reportHtml?: string
  reportMd?: string
  stage?: string
  loading?: boolean
  steps?: StepItem[]
}

// ===== State =====
const sidebarShow = ref(true)
const sessionList = ref<ChatInfo[]>([])
const sessionSearch = ref('')
const currentSessionId = ref<number | undefined>()
const question = ref('')
const loading = ref(false)
const currentStage = ref('')
const messages = ref<ChatMessage[]>([])
const chatScrollRef = ref()
const reportPanelOpen = ref(false)
const activeReportHtml = ref('')
const activeReportMd = ref('')
let abortController: AbortController | null = null
const groupExpand = ref<Record<string, boolean>>({
  [t('qa.today')]: true,
  [t('qa.week')]: true,
  [t('qa.earlier')]: true,
  [t('qa.no_time')]: true,
})

// Rename
const renameVisible = ref(false)
const renameLoading = ref(false)
const renameValue = ref('')
const renameId = ref(0)

// ===== Computed =====
const filteredSessions = computed(() => {
  if (!sessionSearch.value.trim()) return sessionList.value
  const q = sessionSearch.value.toLowerCase()
  return sessionList.value.filter((s) => (s.brief || '').toLowerCase().includes(q))
})

const sessionGroups = computed(() => {
  const grouped = groupBy(filteredSessions.value, (item: ChatInfo) => {
    const time = getDate(item.create_time)
    if (!time) return t('qa.no_time')
    const todayStart = dayjs(dayjs().format('YYYY-MM-DD') + ' 00:00:00').toDate()
    const weekStart = dayjs(dayjs().subtract(7, 'day').format('YYYY-MM-DD') + ' 00:00:00').toDate()
    if (time >= todayStart) return t('qa.today')
    if (time >= weekStart) return t('qa.week')
    return t('qa.earlier')
  })
  return [t('qa.today'), t('qa.week'), t('qa.earlier'), t('qa.no_time')]
    .filter((k) => grouped[k]?.length)
    .map((k) => ({ key: k, list: grouped[k] }))
})

// ===== Functions =====
function renderMd(raw: string): string {
  if (!raw) return ''
  try {
    return md.render(raw)
  } catch {
    return raw
  }
}

function scrollToBottom() {
  nextTick(() => {
    const el = chatScrollRef.value?.$el?.querySelector('.el-scrollbar__wrap')
    if (el) el.scrollTop = el.scrollHeight
  })
}

async function loadSessions() {
  try {
    sessionList.value = (await deepAnalysisApi.sessions()) || []
  } catch {
    sessionList.value = []
  }
}

function newChat() {
  currentSessionId.value = undefined
  messages.value = []
  question.value = ''
  reportPanelOpen.value = false
  sessionStorage.removeItem('da_session')
}

function selectSession(item: ChatInfo) {
  currentSessionId.value = item.id
  sessionStorage.setItem('da_session', String(item.id))
  messages.value = []
  reportPanelOpen.value = false
  if (item.id != null) loadHistory(item.id)
}

function buildStepsFromHistory(plan?: string, process?: any[], report?: string): StepItem[] {
  const steps: StepItem[] = []

  if (plan) {
    const planStep: StepItem = {
      title: '任务规划',
      status: 'done',
      detailsMd: plan,
      details: renderMd(plan),
      expanded: false,
    }
    steps.push(planStep)
  }

  if (process && Array.isArray(process)) {
    let currentStep: StepItem | null = null
    for (const item of process) {
      const t = item?.type || 'process'
      const c = item?.content || ''
      if (!c) continue

      if (t === 'stage') {
        if (currentStep) currentStep.details = renderMd(currentStep.detailsMd)
        const title = classifyStageTitle(c)
        currentStep = { title, status: 'done', detailsMd: '', details: '', expanded: false }
        steps.push(currentStep)
        continue
      }

      if (currentStep) {
        currentStep.detailsMd += c
      } else {
        currentStep = {
          title: '执行过程',
          status: 'done',
          detailsMd: c,
          details: '',
          expanded: false,
        }
        steps.push(currentStep)
      }
    }
    if (currentStep && !currentStep.details) {
      currentStep.details = renderMd(currentStep.detailsMd)
    }
  }

  if (report) {
    steps.push({
      title: '生成报告',
      status: 'done',
      detailsMd: '报告已生成，点击下方卡片查看。',
      details: renderMd('报告已生成，点击下方卡片查看。'),
      expanded: false,
    })
  }

  return steps
}

async function loadHistory(chatId: number) {
  try {
    const res = await chatApi.get(chatId)
    const info = chatApi.toChatInfo(res)
    const records = info?.records || []
    const msgs: ChatMessage[] = []
    for (const r of records) {
      if (!r.analysis || typeof r.analysis !== 'string') continue
      try {
        const data = JSON.parse(r.analysis)
        if (typeof data !== 'object' || (!data.plan && !data.report)) continue
        if (data.config?.question) {
          msgs.push({ role: 'user', content: data.config.question })
        }
        const agentMsg: ChatMessage = { role: 'agent', content: '' }
        agentMsg.steps = buildStepsFromHistory(data.plan, data.process, data.report)
        if (data.report) {
          agentMsg.reportHtml = renderMd(data.report)
          agentMsg.reportMd = data.report
          agentMsg.content = '分析完成，点击查看报告 👇'
          agentMsg.contentHtml = renderMd('**分析完成** — 点击下方卡片查看完整报告')
        }
        msgs.push(agentMsg)
      } catch {
        continue
      }
    }
    messages.value = msgs
    scrollToBottom()
  } catch {
    messages.value = []
  }
}

function openReport(msg: ChatMessage) {
  if (msg.reportHtml) {
    activeReportHtml.value = msg.reportHtml
    activeReportMd.value = msg.reportMd || ''
    reportPanelOpen.value = true
  }
}

function exportReport() {
  if (!activeReportMd.value) return
  const blob = new Blob([activeReportMd.value], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `Data_Agent_Report_${dayjs().format('YYYYMMDD_HHmmss')}.md`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success(t('deep_analysis.export_success'))
}

function createStep(title: string, status: StepItem['status'] = 'running'): StepItem {
  return { title, status, details: '', detailsMd: '', expanded: false }
}

function finalizeStep(step: StepItem) {
  step.status = 'done'
  if (step.detailsMd) {
    step.details = renderMd(step.detailsMd)
  }
}

function appendToStep(step: StepItem, text: string) {
  step.detailsMd += text
  step.details = renderMd(step.detailsMd)
}

function classifyStageTitle(raw: string): string {
  const s = raw.replace(/^当前阶段：/, '').trim()
  if (/任务拆解|plan/i.test(s)) return '任务规划'
  if (/智能取数/i.test(s)) return '智能取数'
  if (/分析洞察|insight/i.test(s)) return '分析洞察'
  if (/沉淀结论|save/i.test(s)) return '沉淀结论'
  if (/数据变换/i.test(s)) return '数据变换'
  if (/汇总报告|report/i.test(s)) return '生成报告'
  return s || '执行中'
}

async function sendMessage() {
  const q = question.value.trim()
  if (!q || loading.value) return

  messages.value.push({ role: 'user', content: q })
  question.value = ''
  scrollToBottom()

  loading.value = true
  currentStage.value = ''
  abortController = new AbortController()

  const agentMsg: ChatMessage = { role: 'agent', content: '', steps: [] }
  messages.value.push(agentMsg)

  let reportMd = ''
  let currentStep: StepItem | null = null

  try {
    const response = await request.fetchStream(
      '/openapi/deep-analysis',
      {
        question: q,
        chat_id: currentSessionId.value ?? undefined,
        no_reasoning: false,
        max_data_length: 1000,
        is_chart_output: true,
      },
      abortController
    )

    if (!response.ok || !response.body) {
      agentMsg.content = response.statusText || '请求失败'
      loading.value = false
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split(/\n\n/)
      buffer = parts.pop() || ''

      for (const part of parts) {
        const line = part.trim()
        if (!line.startsWith('data:')) continue
        try {
          const data = JSON.parse(line.slice(5).trim())
          const c = typeof data.content === 'string' ? data.content : ''

          if (data.type === 'error') {
            if (currentStep) finalizeStep(currentStep)
            const errStep = createStep('错误', 'done')
            errStep.detailsMd = c || '未知错误'
            errStep.details = renderMd(errStep.detailsMd)
            agentMsg.steps!.push(errStep)
            agentMsg.content = `❌ ${c || '未知错误'}`
            break
          }

          if (data.type === 'start' && data.chat_id) {
            currentSessionId.value = data.chat_id
            sessionStorage.setItem('da_session', String(data.chat_id))
            await loadSessions()
            continue
          }

          if (data.type === 'finish') {
            if (currentStep) finalizeStep(currentStep)
            if (data.chat_id) {
              currentSessionId.value = data.chat_id
              await loadSessions()
            }
            break
          }

          if (data.type === 'plan' && c) {
            if (currentStep) finalizeStep(currentStep)
            currentStep = createStep('任务规划')
            currentStep.detailsMd = c
            currentStep.details = renderMd(c)
            currentStep.expanded = false
            agentMsg.steps!.push(currentStep)
            scrollToBottom()
            continue
          }

          if (data.type === 'stage' && c) {
            const stageTitle = classifyStageTitle(c)
            currentStage.value = stageTitle

            if (currentStep && currentStep.status === 'running') {
              finalizeStep(currentStep)
            }
            currentStep = createStep(stageTitle)
            agentMsg.steps!.push(currentStep)
            scrollToBottom()
            continue
          }

          if (data.type === 'report' && c) {
            reportMd += c
            continue
          }

          if (c && data.type !== 'report') {
            if (currentStep) {
              appendToStep(currentStep, c)
            } else {
              currentStep = createStep('分析中')
              agentMsg.steps!.push(currentStep)
              appendToStep(currentStep, c)
            }
            scrollToBottom()
          }
        } catch {
          continue
        }
      }
    }

    if (currentStep && currentStep.status === 'running') {
      finalizeStep(currentStep)
    }

    if (reportMd) {
      const reportStep = createStep('生成报告', 'done')
      reportStep.detailsMd = '报告已生成，点击下方卡片查看完整报告。'
      reportStep.details = renderMd(reportStep.detailsMd)
      agentMsg.steps!.push(reportStep)

      agentMsg.reportHtml = renderMd(reportMd)
      agentMsg.reportMd = reportMd
      agentMsg.content = '分析完成，点击查看报告 👇'
      agentMsg.contentHtml = renderMd('**分析完成** — 点击下方卡片查看完整报告')
    } else {
      agentMsg.content = '分析完成'
      agentMsg.contentHtml = renderMd('**分析完成**')
    }
  } catch (e: any) {
    if (e?.name !== 'AbortError') {
      agentMsg.content = `❌ ${e?.message || String(e)}`
    }
  } finally {
    loading.value = false
    abortController = null
    scrollToBottom()
  }
}

// Rename
function openRename(item: ChatInfo) {
  if (item.id == null) return
  renameId.value = item.id
  renameValue.value = item.brief || ''
  renameVisible.value = true
}

async function submitRename() {
  renameLoading.value = true
  try {
    const res = await chatApi.renameChat(renameId.value, renameValue.value)
    const c = sessionList.value.find((x) => x.id === renameId.value)
    if (c) c.brief = res
    renameVisible.value = false
    ElMessage.success(t('common.save_success'))
  } catch (e: any) {
    ElMessage.error(e?.message || 'Rename failed')
  } finally {
    renameLoading.value = false
  }
}

async function deleteSession(item: ChatInfo) {
  if (item.id == null) return
  try {
    await ElMessageBox.confirm(`确定删除会话「${item.brief || ''}」？`, {
      confirmButtonType: 'danger',
      confirmButtonText: t('dashboard.delete'),
      cancelButtonText: t('common.cancel'),
    })
    await chatApi.deleteChat(item.id, item.brief ?? '')
    sessionList.value = sessionList.value.filter((s) => s.id !== item.id)
    if (currentSessionId.value === item.id) newChat()
    ElMessage.success(t('dashboard.delete_success'))
  } catch {
    // user cancelled
  }
}

// ===== Lifecycle =====
onMounted(async () => {
  await loadSessions()
  const saved = sessionStorage.getItem('da_session')
  if (saved) {
    const id = Number(saved)
    const item = sessionList.value.find((s) => s.id === id)
    if (item) selectSession(item)
  }
})
</script>

<style scoped>
.da-page {
  height: 100%;
  background: #f5f6f7;
}
.da-layout {
  height: 100%;
}

/* ===== Sidebar ===== */
.da-sidebar {
  background: #f5f6f7;
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(31, 35, 41, 0.08);
}
.da-sidebar-header {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.da-sidebar-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.da-sidebar-title {
  font-weight: 600;
  font-size: 15px;
}
.da-icon-btn {
  min-width: unset;
  width: 28px;
  height: 28px;
  font-size: 18px;
  --ed-button-text-color: #1f2329;
}
.da-icon-btn:hover {
  background: rgba(31, 35, 41, 0.08);
  border-radius: 6px;
}
.da-new-btn {
  width: 100%;
  height: 38px;
  font-weight: 500;
  --ed-button-text-color: var(--ed-color-primary);
  --ed-button-bg-color: rgba(28, 186, 144, 0.1);
  --ed-button-border-color: rgba(28, 186, 144, 0.3);
}
.da-session-scroll {
  flex: 1;
  min-height: 0;
}
.da-session-list {
  padding: 0 12px 16px;
}
.da-empty {
  padding: 24px;
  text-align: center;
  color: #8f959e;
  font-size: 13px;
}
.da-group {
  margin-bottom: 8px;
}
.da-group-title {
  padding: 4px 8px;
  font-size: 12px;
  font-weight: 500;
  color: #8f959e;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
}
.da-group-title .collapsed {
  transform: rotate(-90deg);
}
.da-session-item {
  height: 38px;
  padding: 0 10px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  cursor: pointer;
  margin-bottom: 2px;
  position: relative;
}
.da-session-item:hover {
  background: rgba(31, 35, 41, 0.06);
}
.da-session-item.active {
  background: #fff;
  font-weight: 500;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}
.da-session-brief {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.da-session-more {
  color: #8f959e;
  opacity: 0;
  flex-shrink: 0;
}
.da-session-item:hover .da-session-more {
  opacity: 1;
}

/* Float buttons */
.da-float-btns {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 10;
  padding: 12px;
  display: flex;
  gap: 4px;
}

/* ===== Chat Main ===== */
.da-chat-main {
  padding: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  flex: 1;
  min-width: 0;
}
.da-chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.da-messages-scroll {
  flex: 1;
  min-height: 0;
}
.da-messages {
  padding: 24px 32px;
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 100%;
}

/* Welcome */
.da-welcome {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 12px;
  color: #646a73;
}
.da-welcome-icon {
  font-size: 48px;
  margin-bottom: 8px;
}
.da-welcome-title {
  font-size: 20px;
  font-weight: 600;
  color: #1f2329;
  margin: 0;
}
.da-welcome-desc {
  font-size: 14px;
  max-width: 400px;
  line-height: 1.6;
  margin: 0;
}

/* Messages */
.da-msg {
  display: flex;
}
.da-msg-user {
  justify-content: flex-end;
}
.da-msg-agent {
  justify-content: flex-start;
}
.da-msg-bubble {
  max-width: 80%;
  border-radius: 16px;
  padding: 12px 16px;
  font-size: 14px;
  line-height: 1.6;
}
.da-bubble-user {
  background: var(--ed-color-primary, #1cba90);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.da-bubble-agent {
  background: #f5f6f7;
  color: #1f2329;
  border-bottom-left-radius: 4px;
}
.da-loading-bubble {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #8f959e;
}

/* Steps timeline */
.da-steps-timeline {
  margin-bottom: 12px;
}
.da-step-item {
  display: flex;
  gap: 10px;
  position: relative;
  padding-bottom: 4px;
}
.da-step-item:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 10px;
  top: 24px;
  bottom: 0;
  width: 1.5px;
  background: #e4e7ed;
}
.da-step-item.da-step-done:not(:last-child)::before {
  background: var(--ed-color-primary, #1cba90);
}
.da-step-indicator {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 1px;
  z-index: 1;
}
.da-step-check {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--ed-color-primary, #1cba90);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
.da-step-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #dcdfe6;
}
.da-step-icon-loading {
  color: var(--ed-color-primary, #1cba90);
  font-size: 18px;
}
.da-step-body {
  flex: 1;
  min-width: 0;
  padding-bottom: 8px;
}
.da-step-title {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  user-select: none;
  padding: 2px 0;
}
.da-step-title:hover .da-step-label {
  color: var(--ed-color-primary, #1cba90);
}
.da-step-label {
  font-size: 14px;
  font-weight: 500;
  color: #1f2329;
  transition: color 0.15s;
}
.da-step-done .da-step-label {
  color: #1f2329;
}
.da-step-active .da-step-label {
  color: var(--ed-color-primary, #1cba90);
}
.da-step-toggle {
  color: #8f959e;
  transition: transform 0.2s;
  flex-shrink: 0;
}
.da-step-toggle-open {
  transform: rotate(90deg);
}
.da-step-details {
  font-size: 13px;
  color: #4e5969;
  padding: 6px 0 2px;
  line-height: 1.6;
  max-height: 400px;
  overflow-y: auto;
}
.da-step-details :deep(pre) {
  background: #fff;
  padding: 8px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 12px;
}
.da-step-details :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 6px 0;
  font-size: 12px;
}
.da-step-details :deep(th),
.da-step-details :deep(td) {
  border: 1px solid #dee0e3;
  padding: 4px 8px;
}
.da-step-expand-enter-active,
.da-step-expand-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}
.da-step-expand-enter-from,
.da-step-expand-leave-to {
  opacity: 0;
  max-height: 0;
}

/* Agent text */
.da-agent-text {
  word-break: break-word;
}
.da-agent-text :deep(pre) {
  background: #fff;
  padding: 10px;
  border-radius: 8px;
  overflow-x: auto;
}
.da-agent-text :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
}
.da-agent-text :deep(th),
.da-agent-text :deep(td) {
  border: 1px solid #dee0e3;
  padding: 6px 10px;
}

/* Report card */
.da-report-card {
  margin-top: 10px;
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid rgba(28, 186, 144, 0.3);
  background: rgba(28, 186, 144, 0.05);
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: all 0.15s;
}
.da-report-card:hover {
  background: rgba(28, 186, 144, 0.12);
  border-color: var(--ed-color-primary);
}
.da-report-icon {
  color: var(--ed-color-primary);
}
.da-report-card-text {
  flex: 1;
  font-weight: 500;
  font-size: 14px;
  color: var(--ed-color-primary);
}

/* Input bar */
.da-input-bar {
  padding: 16px 32px 20px;
  border-top: 1px solid rgba(31, 35, 41, 0.06);
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}
.da-input :deep(.el-input__wrapper) {
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
.da-input :deep(.el-input-group__append) {
  padding: 0;
  border-radius: 0 12px 12px 0;
}
.da-send-btn {
  height: 40px;
  width: 48px;
  border-radius: 0 12px 12px 0;
}

/* ===== Report Panel ===== */
.da-report-panel {
  width: 520px;
  min-width: 400px;
  max-width: 600px;
  background: #fff;
  border-left: 1px solid rgba(31, 35, 41, 0.08);
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 16px rgba(0, 0, 0, 0.04);
}
.da-report-header {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(31, 35, 41, 0.06);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.da-report-title {
  font-size: 16px;
  font-weight: 600;
}
.da-report-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.da-report-body-scroll {
  flex: 1;
  min-height: 0;
}
.da-report-body {
  padding: 20px;
  line-height: 1.75;
}
.da-report-body :deep(h1) {
  font-size: 1.3rem;
  margin: 1em 0 0.5em;
}
.da-report-body :deep(h2) {
  font-size: 1.1rem;
  margin: 0.9em 0 0.4em;
  border-bottom: 1px solid #eee;
  padding-bottom: 6px;
}
.da-report-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 10px 0;
}
.da-report-body :deep(th),
.da-report-body :deep(td) {
  border: 1px solid #dee0e3;
  padding: 8px 10px;
}

/* Panel slide animation */
.da-panel-slide-enter-active,
.da-panel-slide-leave-active {
  transition: all 0.25s ease;
}
.da-panel-slide-enter-from,
.da-panel-slide-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

/* Popover */
.da-popover-menu {
  padding: 4px 0;
}
.da-popover-item {
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 13px;
}
.da-popover-item:hover {
  background: rgba(31, 35, 41, 0.06);
}
.da-popover-item.danger {
  color: var(--ed-color-danger);
}

@media (max-width: 1200px) {
  .da-report-panel {
    width: 400px;
    min-width: 320px;
  }
}
@media (max-width: 900px) {
  .da-layout {
    flex-direction: column;
  }
  .da-sidebar {
    width: 100% !important;
    max-height: 200px;
  }
  .da-report-panel {
    width: 100% !important;
    max-height: 50vh;
  }
}
</style>

<style>
.da-session-popover.da-session-popover {
  box-shadow: 0 4px 12px rgba(31, 35, 41, 0.1);
  border-radius: 8px;
  border: 1px solid #dee0e3;
  padding: 4px 0;
  min-width: 120px;
}
</style>
