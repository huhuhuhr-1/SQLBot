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
            class="da-session-search"
            name="quick-search"
            autocomplete="off"
            :placeholder="t('qa.chat_search')"
            clearable
            size="small"
            @click.stop
          />
        </header>
        <el-scrollbar v-loading="sessionListLoading" class="da-session-scroll">
          <div class="da-session-list-inner">
            <template v-if="filteredSessions.length">
              <div class="bulk-bar">
                <div class="bulk-left">
                  <el-checkbox
                    :indeterminate="selectedIds.length > 0 && !allSelected"
                    :model-value="allSelected"
                    @change="toggleSelectAll"
                  >
                    {{ t('datasource.select_all') }}
                  </el-checkbox>
                  <span v-if="hasSelection" class="bulk-selected">
                    {{ t('user.selected_2_items', { msg: selectedIds.length }) }}
                  </span>
                </div>
                <div class="bulk-right">
                  <el-dropdown @command="handleClearByScope">
                    <span class="bulk-clear-link">
                      {{ t('qa.clear_history') }}
                    </span>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="before_today">
                          {{ t('qa.clear_history_before_today') }}
                        </el-dropdown-item>
                        <el-dropdown-item command="before_7_days">
                          {{ t('qa.clear_history_before_7_days') }}
                        </el-dropdown-item>
                        <el-dropdown-item command="all">
                          {{ t('qa.clear_history_all') }}
                        </el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                  <el-button
                    v-if="hasSelection"
                    size="small"
                    type="danger"
                    text
                    class="bulk-delete-btn"
                    @click="handleBulkDeleteSelected"
                  >
                    {{ t('dashboard.delete') }}
                  </el-button>
                </div>
              </div>
            </template>
            <div v-if="!filteredSessions.length" class="da-empty">
              {{
                sessionSearch.trim()
                  ? t('datasource.relevant_content_found')
                  : t('deep_analysis.no_sessions')
              }}
            </div>
            <div v-else class="da-session-list">
              <div v-for="group in sessionGroups" :key="group.key" class="da-group">
                <div class="da-group-title" @click="groupExpand[group.key] = !groupExpand[group.key]">
                  <el-icon :class="{ collapsed: !groupExpand[group.key] }" size="10">
                    <icon_expand_down_filled />
                  </el-icon>
                  {{ group.key }}
                </div>
                <template v-for="item in group.list" :key="item.id">
                  <div
                    v-show="groupExpand[group.key]"
                    class="da-session-item"
                    :class="{ active: currentSessionId === item.id }"
                    @click="selectSession(item)"
                  >
                    <el-checkbox
                      class="select-checkbox"
                      :model-value="isSelected(item.id)"
                      @click.stop
                      @change="() => toggleSelect(item)"
                    />
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
                      <el-icon class="da-session-more" size="14" @click.stop>
                        <icon_more_outlined />
                      </el-icon>
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
                <div class="da-welcome-avatar">
                  <icon_ai class="da-avatar-svg" />
                </div>
                <h2 class="da-welcome-title">{{ t('deep_analysis.starter_title') }}</h2>
                <p class="da-welcome-desc">{{ t('deep_analysis.starter_desc') }}</p>
                <div class="da-welcome-caps">
                  <div class="da-cap-item">
                    <el-icon size="16" color="#1cba90"><icon_mindnote_outlined /></el-icon>
                    <span>{{ t('deep_analysis.capability_plan') }}</span>
                  </div>
                  <div class="da-cap-item">
                    <el-icon size="16" color="#1cba90"><icon_logs_outlined /></el-icon>
                    <span>{{ t('deep_analysis.capability_trace') }}</span>
                  </div>
                  <div class="da-cap-item">
                    <el-icon size="16" color="#1cba90"><icon_export_outlined /></el-icon>
                    <span>{{ t('deep_analysis.capability_report') }}</span>
                  </div>
                </div>
              </div>

              <!-- 消息列表 -->
              <template v-for="(msg, idx) in messages" :key="idx">
                <!-- 用户消息 -->
                <div v-if="msg.role === 'user'" class="da-msg da-msg-user">
                  <div class="da-user-avatar">
                    <el-icon size="16"><icon_user /></el-icon>
                  </div>
                  <div class="da-msg-content">
                    <div class="da-bubble-user">{{ msg.content }}</div>
                  </div>
                </div>

                <!-- Agent 消息 -->
                <div v-else class="da-msg da-msg-agent">
                  <div class="da-agent-avatar">
                    <icon_ai class="da-avatar-svg" />
                  </div>
                  <div class="da-msg-content">
                    <!-- 状态标签 -->
                    <div class="da-agent-status">
                      <span v-if="msg.loading" class="da-status-tag da-status-running">
                        <el-icon class="is-loading" size="12"><Loading /></el-icon>
                        Agent 正在执行...
                      </span>
                      <span v-else class="da-status-tag da-status-done">
                        <el-icon size="12"><CircleCheckFilled /></el-icon>
                        {{ msg.thinkingLabel || '思考完成' }}
                      </span>
                    </div>

                    <!-- 计划 — 可展开的思考区块 -->
                    <div v-if="msg.planHtml" class="da-plan-wrapper">
                      <div class="da-plan-toggle" @click="msg.planExpanded = !msg.planExpanded">
                        <el-icon v-if="msg.loading" class="is-loading" size="14">
                          <Loading />
                        </el-icon>
                        <el-icon v-else size="14" color="#1cba90">
                          <CircleCheckFilled />
                        </el-icon>
                        <span class="da-plan-toggle-text">
                          {{ msg.loading ? 'Agent 正在规划...' : '执行计划' }}
                        </span>
                        <span v-if="!msg.loading" class="da-plan-toggle-link">{{
                          msg.planExpanded ? '收起' : '查看详情'
                        }}</span>
                      </div>
                      <div v-if="msg.planExpanded" class="da-plan-block markdown-body">
                        <div v-html="msg.planHtml"></div>
                      </div>
                    </div>

                    <!-- 步骤时间线 -->
                    <div v-if="msg.steps && msg.steps.length" class="da-steps-timeline">
                      <div
                        v-for="(step, sIdx) in msg.steps"
                        :key="sIdx"
                        class="da-step-item"
                        :class="{
                          'da-step-active': step.status === 'running',
                          'da-step-done': step.status === 'done',
                          'da-step-error': step.status === 'error',
                          'da-step-selected': isStepSelected(idx, sIdx),
                          'da-step-item--interactive': !!step.detailsMd,
                        }"
                        @click="step.detailsMd && selectStep(idx, sIdx, step)"
                      >
                        <div class="da-step-indicator">
                          <el-icon
                            v-if="step.status === 'running'"
                            class="is-loading da-step-icon-loading"
                            size="16"
                            ><Loading
                          /></el-icon>
                          <span v-else-if="step.status === 'done'" class="da-step-check">
                            <el-icon size="12"><Check /></el-icon>
                          </span>
                          <span v-else-if="step.status === 'error'" class="da-step-error-dot">
                            <el-icon size="12"><CloseBold /></el-icon>
                          </span>
                          <span v-else class="da-step-dot"></span>
                        </div>
                        <div class="da-step-body">
                          <div class="da-step-header">
                            <span class="da-step-label">{{ getStepDisplayTitle(step) }}</span>
                            <span
                              v-if="step.status !== 'running' && step.durationMs != null"
                              class="da-step-duration"
                              >{{ formatStepDuration(step.durationMs) }}</span
                            >
                          </div>
                          <div v-if="getStepDesc(step)" class="da-step-desc">
                            {{ getStepDesc(step) }}
                          </div>
                          <div v-if="step.resultSummary" class="da-step-result">
                            {{ step.resultSummary }}
                          </div>
                          <!-- 子流程指示 -->
                          <div
                            v-if="step.status === 'done' && step.detailsMd"
                            class="da-step-substeps"
                          >
                            <template v-for="(sub, subIdx) in getSubSteps(step)" :key="subIdx">
                              <span v-if="subIdx > 0" class="da-substep-divider">›</span>
                              <span class="da-substep-item da-substep-done">{{ sub }}</span>
                            </template>
                          </div>
                          <div v-else-if="step.status === 'running'" class="da-step-substeps">
                            <span class="da-substep-item da-substep-done">开始执行</span>
                            <span class="da-substep-divider">›</span>
                            <span class="da-substep-item da-substep-active">
                              <el-icon class="is-loading" size="10"><Loading /></el-icon>
                              执行中...
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>

                    <!-- Agent 流式文本 — 正在输出时展示当前 step 的内容 -->
                    <div
                      v-if="msg.loading && getLastRunningStep(msg)"
                      class="da-stream-block markdown-body"
                      v-html="getLastRunningStep(msg)!.details"
                    ></div>

                    <!-- 主文本（简短总结） -->
                    <div
                      v-if="!msg.loading && msg.contentHtml"
                      class="markdown-body da-agent-text"
                      v-html="msg.contentHtml"
                    ></div>
                    <div
                      v-else-if="!msg.loading && msg.content && !msg.planHtml && !msg.steps?.length"
                      class="da-agent-text"
                    >
                      {{ msg.content }}
                    </div>

                    <!-- 报告卡片 -->
                    <div v-if="msg.reportHtml" class="da-report-card" @click="openReport(msg)">
                      <div class="da-report-card-icon">
                        <el-icon size="20"><Document /></el-icon>
                      </div>
                      <div class="da-report-card-body">
                        <div class="da-report-card-title">
                          {{ t('deep_analysis.report_title') }}
                        </div>
                        <div class="da-report-card-desc">点击查看完整分析报告</div>
                      </div>
                      <el-icon size="16" color="#8f959e"><ArrowRight /></el-icon>
                    </div>
                  </div>
                </div>
              </template>

              <!-- 加载占位 -->
              <div v-if="loading && !messages.length" class="da-msg da-msg-agent">
                <div class="da-agent-avatar">
                  <icon_ai class="da-avatar-svg" />
                </div>
                <div class="da-msg-content">
                  <div class="da-agent-status">
                    <span class="da-status-tag da-status-running">
                      <el-icon class="is-loading" size="12"><Loading /></el-icon>
                      {{ currentStage || t('deep_analysis.waiting') }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </el-scrollbar>

          <!-- 输入栏 -->
          <div class="da-input-bar">
            <div class="da-input-wrapper">
              <el-input
                v-model="question"
                :placeholder="t('deep_analysis.question_placeholder')"
                :disabled="loading"
                :autosize="{ minRows: 1, maxRows: 4 }"
                type="textarea"
                resize="none"
                class="da-input"
                @keydown.enter.exact.prevent="sendMessage"
              />
              <el-button
                :icon="loading ? undefined : Promotion"
                :loading="loading"
                type="primary"
                class="da-send-btn"
                :disabled="!question.trim()"
                circle
                @click="sendMessage"
              />
            </div>
          </div>
        </div>
      </el-main>

      <!-- 右侧：执行事件详情面板 -->
      <transition name="da-panel-slide">
        <aside v-if="detailPanelOpen" class="da-detail-panel">
          <header class="da-detail-header">
            <span class="da-detail-title">执行事件详情</span>
            <el-button link class="da-icon-btn" @click="detailPanelOpen = false">
              <el-icon><Close /></el-icon>
            </el-button>
          </header>

          <!-- 报告模式 -->
          <template v-if="detailMode === 'report'">
            <div class="da-detail-toolbar">
              <span class="da-detail-tab active">{{ t('deep_analysis.report_title') }}</span>
              <div class="da-detail-actions">
                <el-button
                  v-if="activeReportMd"
                  type="primary"
                  plain
                  size="small"
                  @click="exportReport"
                >
                  {{ t('deep_analysis.export_report') }}
                </el-button>
              </div>
            </div>
            <el-scrollbar class="da-detail-body-scroll">
              <div class="markdown-body da-detail-body" v-html="activeReportHtml"></div>
            </el-scrollbar>
          </template>

          <!-- 步骤详情模式 -->
          <template v-else-if="detailMode === 'step'">
            <div class="da-detail-toolbar">
              <div class="da-detail-toolbar-main">
                <span class="da-detail-tab active">{{
                  activeStepDetail?.title || '查询数据'
                }}</span>
                <span v-if="activeStepDetail?.durationMs != null" class="da-step-duration-header">{{
                  formatStepDuration(activeStepDetail.durationMs)
                }}</span>
                <span
                  v-if="activeStepDetail?.resultSummary"
                  class="da-detail-result-chip"
                  :title="activeStepDetail.resultSummary"
                  >{{ activeStepDetail.resultSummary }}</span
                >
              </div>
              <div class="da-detail-status-badge">
                <template v-if="activeStepDetail?.status === 'running'">
                  <el-icon class="is-loading" size="12"><Loading /></el-icon>
                  <span>Agent 正在执行...</span>
                </template>
                <template v-else-if="activeStepDetail?.status === 'done'">
                  <el-icon size="12" color="#1cba90"><CircleCheckFilled /></el-icon>
                  <span>已完成</span>
                </template>
                <template v-else-if="activeStepDetail?.status === 'error'">
                  <el-icon size="12" color="#f56c6c"><CircleCloseFilled /></el-icon>
                  <span>执行失败</span>
                </template>
              </div>
            </div>
            <el-scrollbar class="da-detail-body-scroll">
              <div class="da-detail-events">
                <!-- 主区域：Markdown 流式全文（不再依赖「查看原始输出」折叠） -->
                <div
                  v-if="activeStepDetail?.details"
                  class="markdown-body da-detail-body da-detail-stream"
                  v-html="activeStepDetail.details"
                ></div>
                <!-- 事件卡片列表 -->
                <div
                  v-for="(evt, eIdx) in activeStepEvents"
                  :key="eIdx"
                  class="da-event-card"
                  :class="{ expanded: evt.expanded, 'da-event-card-sql': evt.type === 'sql' }"
                >
                  <div class="da-event-card-header" @click="evt.expanded = !evt.expanded">
                    <div class="da-event-card-icon" :class="'da-evt-' + evt.type">
                      <el-icon size="14">
                        <component :is="getEventIcon(evt.type)" />
                      </el-icon>
                    </div>
                    <span class="da-event-card-title">{{ evt.title }}</span>
                    <span v-if="evt.badge" class="da-event-badge">{{ evt.badge }}</span>
                    <el-icon class="da-event-toggle" :class="{ open: evt.expanded }" size="12"
                      ><ArrowRight
                    /></el-icon>
                  </div>
                  <transition name="da-evt-expand">
                    <div v-if="evt.expanded" class="da-event-card-body">
                      <!-- SQL 展示 -->
                      <div v-if="evt.sql" class="da-evt-sql">
                        <div class="da-evt-section-title">
                          <el-icon size="12"><icon_sql_outlined /></el-icon>
                          {{ evt.title && /sql/i.test(evt.title) ? evt.title : '执行的 SQL' }}
                        </div>
                        <pre class="da-sql-code"><code>{{ evt.sql }}</code></pre>
                        <div v-if="evt.duration" class="da-evt-meta">
                          执行耗时 {{ evt.duration }}
                        </div>
                      </div>
                      <!-- 数据表信息 -->
                      <div v-if="evt.tableSchema && evt.tableSchema.length" class="da-evt-schema">
                        <div class="da-evt-section-title">
                          <el-icon size="12"><Grid /></el-icon> 字段列表
                        </div>
                        <table class="da-schema-table">
                          <thead>
                            <tr>
                              <th>字段名</th>
                              <th>字段类型</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr v-for="(col, cIdx) in evt.tableSchema" :key="cIdx">
                              <td>{{ col.name }}</td>
                              <td>{{ col.type }}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                      <!-- Markdown 内容 -->
                      <div
                        v-if="evt.contentHtml"
                        class="markdown-body da-evt-content"
                        v-html="evt.contentHtml"
                      ></div>
                      <div v-else-if="evt.content" class="da-evt-content da-evt-text">
                        {{ evt.content }}
                      </div>
                    </div>
                  </transition>
                </div>
              </div>
            </el-scrollbar>
          </template>
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
import { computed, nextTick, onMounted, ref, shallowRef, type Component } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus-secondary'
import {
  Search,
  Loading,
  Close,
  Promotion,
  ArrowRight,
  Document,
  Check,
  CloseBold,
  CircleCheckFilled,
  CircleCloseFilled,
  Grid,
  Coin,
  DataLine,
  FolderOpened,
  Monitor,
  Reading,
  SetUp,
} from '@element-plus/icons-vue'
import { request } from '@/utils/request'
import { deepAnalysisApi } from '@/api/deepAnalysis'
import { chatApi } from '@/api/chat'
import type { ChatInfo } from '@/api/chat'
import md from '@/utils/markdown.ts'
import { parseToolBodyStructured, unwrapToolMessageRepr } from '@/utils/deepAnalysisToolParse'
import dayjs from 'dayjs'
import { getDate } from '@/utils/utils'
import { groupBy } from 'lodash-es'
import icon_new_chat_outlined from '@/assets/svg/icon_new_chat_outlined.svg'
import icon_sidebar_outlined from '@/assets/svg/icon_sidebar_outlined.svg'
import icon_expand_down_filled from '@/assets/svg/icon_expand-down_filled.svg'
import icon_more_outlined from '@/assets/svg/icon_more_outlined.svg'
import icon_rename from '@/assets/svg/icon_rename_outlined.svg'
import icon_delete from '@/assets/svg/icon_delete.svg'
import icon_mindnote_outlined from '@/assets/svg/icon_mindnote_outlined.svg'
import icon_logs_outlined from '@/assets/svg/icon_logs_outlined.svg'
import icon_export_outlined from '@/assets/svg/icon_export_outlined.svg'
import icon_user from '@/assets/svg/icon_user.svg'
import icon_sql_outlined from '@/assets/svg/icon_sql_outlined.svg'
import icon_ai from '@/assets/svg/icon_ai.svg'
import 'github-markdown-css/github-markdown-light.css'

const { t } = useI18n()

// ===== Types =====
interface EventItem {
  type: 'data' | 'sql' | 'transform' | 'tool' | 'info' | 'error'
  title: string
  badge?: string
  content?: string
  contentHtml?: string
  sql?: string
  duration?: string
  tableSchema?: { name: string; type: string }[]
  expanded: boolean
}

interface StepItem {
  title: string
  status: 'pending' | 'running' | 'done' | 'error'
  details: string
  detailsMd: string
  expanded: boolean
  stepType: string
  events: EventItem[]
  /** 本步开始时间（客户端，用于无服务端耗时的兜底） */
  startedAt?: number
  /** 本步耗时（优先服务端 duration_ms） */
  durationMs?: number
  /** 工具结束一行摘要（命令结果 / sqlbot 等） */
  resultSummary?: string
}

interface ChatMessage {
  role: 'user' | 'agent'
  content: string
  contentHtml?: string
  planHtml?: string
  planMd?: string
  planExpanded?: boolean
  reportHtml?: string
  reportMd?: string
  stage?: string
  loading?: boolean
  thinkingLabel?: string
  steps?: StepItem[]
}

// ===== State =====
const sidebarShow = ref(true)
const sessionList = ref<ChatInfo[]>([])
const sessionSearch = ref('')
const selectedIds = ref<number[]>([])
const sessionListLoading = ref(false)
const currentSessionId = ref<number | undefined>()
const question = ref('')
const loading = ref(false)
const currentStage = ref('')
const messages = ref<ChatMessage[]>([])
const chatScrollRef = ref()
let abortController: AbortController | null = null
const groupExpand = ref<Record<string, boolean>>({
  [t('qa.today')]: true,
  [t('qa.week')]: true,
  [t('qa.earlier')]: true,
  [t('qa.no_time')]: true,
})

// Detail panel state
const detailPanelOpen = ref(false)
const detailMode = ref<'report' | 'step'>('step')
const activeReportHtml = ref('')
const activeReportMd = ref('')
const activeStepDetail = shallowRef<StepItem | null>(null)
const activeStepEvents = ref<EventItem[]>([])
const selectedMsgIdx = ref(-1)
const selectedStepIdx = ref(-1)

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

const allVisibleIds = computed<number[]>(() => {
  const ids: number[] = []
  sessionGroups.value.forEach((group: { list: ChatInfo[] }) => {
    group.list?.forEach((chat: ChatInfo) => {
      if (chat.id !== undefined) ids.push(chat.id)
    })
  })
  return ids
})

const hasSelection = computed(() => selectedIds.value.length > 0)

const allSelected = computed(
  () =>
    allVisibleIds.value.length > 0 &&
    allVisibleIds.value.every((id) => selectedIds.value.includes(id))
)

// ===== Helpers =====
function renderMd(raw: string): string {
  if (!raw) return ''
  try {
    return md.render(raw)
  } catch {
    return raw
  }
}

function formatStepDuration(ms: number | undefined): string {
  if (ms == null || ms < 0) return ''
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)} s`
  return `${ms} ms`
}

function scrollToBottom() {
  nextTick(() => {
    const el = chatScrollRef.value?.$el?.querySelector('.el-scrollbar__wrap')
    if (el) el.scrollTop = el.scrollHeight
  })
}

function getStepDisplayTitle(step: StepItem): string {
  const t = step.title
  const colonIdx = t.indexOf('：')
  if (colonIdx > 0 && colonIdx < 8) return t.slice(0, colonIdx)
  const colonIdx2 = t.indexOf(': ')
  if (colonIdx2 > 0 && colonIdx2 < 8) return t.slice(0, colonIdx2)
  return t
}

function getStepDesc(step: StepItem): string {
  const t = step.title
  const colonIdx = t.indexOf('：')
  if (colonIdx > 0 && colonIdx < 8) return t.slice(colonIdx + 1).trim()
  const colonIdx2 = t.indexOf(': ')
  if (colonIdx2 > 0 && colonIdx2 < 8) return t.slice(colonIdx2 + 2).trim()
  return ''
}

function getSubSteps(step: StepItem): string[] {
  if (!step.detailsMd) return []
  const subs: string[] = []
  const md = step.detailsMd
  if (md.includes('开始执行')) subs.push('开始执行')
  if (/调用工具|调用模型/.test(md)) subs.push('调用工具')
  if (/```sql/i.test(md) || /生成.*SQL/i.test(md)) subs.push('生成SQL')
  if (/执行.*SQL|SQL.*执行/i.test(md)) subs.push('执行SQL')
  if (/执行结束|执行.*结果/.test(md)) subs.push('执行结束')
  return subs.length ? subs : ['执行']
}

function getLastRunningStep(msg: ChatMessage): StepItem | null {
  if (!msg.steps?.length) return null
  for (let i = msg.steps.length - 1; i >= 0; i--) {
    if (msg.steps[i].status === 'running' && msg.steps[i].details) {
      return msg.steps[i]
    }
  }
  return null
}

function isStepSelected(msgIdx: number, stepIdx: number): boolean {
  return selectedMsgIdx.value === msgIdx && selectedStepIdx.value === stepIdx
}

function selectStep(msgIdx: number, stepIdx: number, step: StepItem) {
  selectedMsgIdx.value = msgIdx
  selectedStepIdx.value = stepIdx
  activeStepDetail.value = step
  activeStepEvents.value = step.events.length ? step.events : buildEventsFromMd(step)
  detailMode.value = 'step'
  detailPanelOpen.value = true
}

/** 新 stage 时强制跟随当前执行步（打开右侧详情并选中最后一步） */
function followExecutingStep() {
  const mi = messages.value.length - 1
  const am = messages.value[mi]
  if (!am || am.role !== 'agent' || !am.steps?.length) return
  const si = am.steps.length - 1
  const step = am.steps[si]
  selectStep(mi, si, step)
}

function getEventIcon(type: string): Component {
  const map: Record<string, Component> = {
    data: Coin,
    sql: DataLine,
    transform: SetUp,
    tool: Monitor,
    info: Reading,
    error: CloseBold,
  }
  return map[type] || FolderOpened
}

function buildEventsFromMd(step: StepItem): EventItem[] {
  if (!step.detailsMd) return []
  return parseProcessContent(step.detailsMd, step.stepType || step.title)
}

function sqlbotBadgeFromStepType(stepType: string): string | undefined {
  const m = stepType.match(/sqlbot_[\w]+/)
  return m ? m[0] : undefined
}

// ===== Parse process content for structured events =====
function parseProcessContent(content: string, stepType: string): EventItem[] {
  const events: EventItem[] = []
  const durationMatch = content.match(/耗时[为：:]\s*(\d+[.\d]*\s*(?:ms|毫秒|秒|s))/i)
  const durationStr = durationMatch ? durationMatch[1] : undefined

  const { body, toolName: reprTool } = unwrapToolMessageRepr(content)
  const st = parseToolBodyStructured(body, reprTool)
  const toolBadge = st.toolName || sqlbotBadgeFromStepType(stepType)

  for (const { sql, field } of st.sqlFromJson) {
    events.push({
      type: 'sql',
      title: field ? `生成的 SQL（${field}）` : '生成的 SQL',
      sql,
      badge: toolBadge,
      duration: durationStr,
      expanded: true,
    })
  }

  for (const sql of st.sqlFromFences) {
    events.push({
      type: 'sql',
      title: 'SQL',
      sql,
      badge: toolBadge,
      duration: durationStr,
      expanded: true,
    })
  }

  if (st.jsonPretty) {
    events.push({
      type: 'data',
      title: st.toolName ? `工具返回（${st.toolName}）` : '结构化结果',
      badge: toolBadge,
      contentHtml: renderMd(`\`\`\`json\n${st.jsonPretty}\n\`\`\``),
      expanded: false,
    })
  }

  const hadStructured = events.length > 0
  if (st.narrativeMd) {
    events.push({
      type: 'info',
      title: st.toolName ? `说明（${st.toolName}）` : classifyStageTitle(stepType || '执行过程'),
      contentHtml: renderMd(st.narrativeMd),
      expanded: !hadStructured,
    })
  }

  const codeBlocks = content.match(/```(?:python|pandas)\n([\s\S]*?)```/gi)
  if (codeBlocks?.length) {
    events.push({
      type: 'transform',
      title: 'Pandas 代码转换',
      contentHtml: renderMd(content),
      expanded: false,
    })
  }

  const toolMatch = content.match(/### 调用工具[：:]\s*`?(\w+)`?/i)
  if (toolMatch && !st.toolName) {
    const tn = toolMatch[1]
    const titleMap: Record<string, string> = {
      execute_one_sql: 'SQL 执行',
      execute_sql: 'SQL 执行',
      describe_table: '获取数据集信息',
      get_table_sample_data: '获取数据样本',
      get_data: '智能取数',
      save_data: '沉淀数据',
      data_transform: '数据变换',
    }
    if (!st.sqlFromFences.length && !st.sqlFromJson.length) {
      events.push({
        type: tn.includes('sql') || tn.includes('execute') ? 'sql' : 'tool',
        title: titleMap[tn] || tn,
        contentHtml: renderMd(content),
        expanded: false,
      })
    }
  }

  const tableMatch = content.match(/表\s*(?:ID|名)[：:]\s*(\d+|[\w_]+)/i)
  const schemaMatch = content.match(/字段列表[：:]?\s*\n([\s\S]*?)(?=\n\n|\n###|$)/i)
  if (tableMatch || schemaMatch) {
    const schema: { name: string; type: string }[] = []
    if (schemaMatch) {
      const lines = schemaMatch[1].split('\n').filter((l) => l.includes('|'))
      for (const line of lines) {
        const cells = line
          .split('|')
          .map((c) => c.trim())
          .filter(Boolean)
        if (cells.length >= 2 && !cells[0].startsWith('-')) {
          schema.push({ name: cells[0], type: cells[1] })
        }
      }
    }
    if (!events.some((e) => e.tableSchema?.length)) {
      events.push({
        type: 'data',
        title: '获取数据集信息',
        badge: tableMatch ? tableMatch[1] : undefined,
        tableSchema: schema.length ? schema : undefined,
        contentHtml: renderMd(content),
        expanded: true,
      })
    }
  }

  if (!events.length && content.trim()) {
    events.push({
      type: 'info',
      title: classifyStageTitle(stepType || '执行过程'),
      contentHtml: renderMd(content),
      expanded: true,
    })
  }

  return events
}

// ===== Sessions =====
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
  detailPanelOpen.value = false
  selectedMsgIdx.value = -1
  selectedStepIdx.value = -1
  sessionStorage.removeItem('da_session')
  selectedIds.value = []
}

function isSelected(id?: number) {
  if (id === undefined) return false
  return selectedIds.value.includes(id)
}

function clearSelection() {
  selectedIds.value = []
}

function toggleSelect(item: ChatInfo) {
  if (item.id === undefined) return
  if (isSelected(item.id)) {
    selectedIds.value = selectedIds.value.filter((x) => x !== item.id)
  } else {
    selectedIds.value = [...selectedIds.value, item.id]
  }
}

function toggleSelectAll() {
  if (allSelected.value) {
    clearSelection()
    return
  }
  selectedIds.value = [...allVisibleIds.value]
}

type ClearScope = 'before_today' | 'before_7_days' | 'all'

function getCleanParamsByScope(scope: ClearScope): { start_time?: string; end_time?: string } | undefined {
  if (scope === 'all') return undefined
  if (scope === 'before_today') {
    const end = dayjs().format('YYYY-MM-DD') + 'T00:00:00'
    return { end_time: end }
  }
  if (scope === 'before_7_days') {
    const end = dayjs().subtract(7, 'day').format('YYYY-MM-DD') + 'T00:00:00'
    return { end_time: end }
  }
  return undefined
}

async function handleClearByScope(scope: ClearScope) {
  try {
    await ElMessageBox.confirm(t('qa.clear_history_confirm'), t('qa.clear_history'), {
      confirmButtonType: 'danger',
      confirmButtonText: t('dashboard.delete'),
      cancelButtonText: t('common.cancel'),
      customClass: 'confirm-no_icon',
      autofocus: false,
    })
  } catch {
    return
  }

  sessionListLoading.value = true
  try {
    const params = getCleanParamsByScope(scope)
    const res = await deepAnalysisApi.cleanSessions(params ?? {})
    if (res.total_count === 0) {
      ElMessage({ type: 'info', message: t('workspace.historical_dialogue') })
    } else {
      ElMessage({
        type: 'success',
        message: res.message || t('dashboard.delete_success'),
      })
      await loadSessions()
      const still = sessionList.value.some((s) => s.id === currentSessionId.value)
      if (!still) newChat()
    }
  } catch (err: any) {
    ElMessage({
      type: 'error',
      message: err?.message || '删除失败',
    })
  } finally {
    sessionListLoading.value = false
    clearSelection()
  }
}

async function handleBulkDeleteSelected() {
  if (!selectedIds.value.length) return
  try {
    await ElMessageBox.confirm(
      t('qa.selected_chats_delete_confirm', { msg: selectedIds.value.length }),
      t('qa.clear_history'),
      {
        confirmButtonType: 'danger',
        tip: t('common.proceed_with_caution'),
        confirmButtonText: t('dashboard.delete'),
        cancelButtonText: t('common.cancel'),
        customClass: 'confirm-no_icon',
        autofocus: false,
      }
    )
  } catch {
    return
  }

  const ids = [...selectedIds.value]
  if (!ids.length) return

  sessionListLoading.value = true
  try {
    const res = await deepAnalysisApi.batchDeleteSessions(ids)
    const skipped = new Set(res.skipped_ids)
    const removed = ids.filter((id) => !skipped.has(id))
    sessionList.value = sessionList.value.filter((s) => s.id == null || !removed.includes(s.id))
    if (currentSessionId.value != null && removed.includes(currentSessionId.value)) {
      newChat()
    }
    ElMessage({ type: 'success', message: t('dashboard.delete_success') })
    if (skipped.size > 0) {
      ElMessage.warning(t('deep_analysis.batch_partial_skip', { n: skipped.size }))
    }
  } catch (err: any) {
    ElMessage({
      type: 'error',
      message: err?.message || '删除失败',
    })
  } finally {
    sessionListLoading.value = false
    clearSelection()
  }
}

function selectSession(item: ChatInfo) {
  currentSessionId.value = item.id
  sessionStorage.setItem('da_session', String(item.id))
  messages.value = []
  detailPanelOpen.value = false
  if (item.id != null) loadHistory(item.id)
}

function classifyStageTitle(raw: string): string {
  const s = raw.replace(/^当前阶段：/, '').trim()
  if (/推理与生成\s*SQL|llm_reasoning/i.test(s)) return '生成 SQL'
  if (/撰写报告|llm_report_draft/i.test(s)) return '撰写报告'
  if (s.includes('：') || s.includes(': ')) return s
  if (/任务拆解|plan/i.test(s)) return '任务规划'
  if (/启动|start|agent/i.test(s)) return t('deep_analysis.agent_start_step')
  if (/智能取数|query|get_data/i.test(s)) return '智能取数'
  if (/执行.*命令|execute|bash|command/i.test(s)) return '执行命令'
  if (/读取文件|read.*file/i.test(s)) return '读取文件'
  if (/浏览目录|browse|list.*dir/i.test(s)) return '浏览目录'
  if (/分析洞察|insight/i.test(s)) return '分析洞察'
  if (/沉淀结论|save/i.test(s)) return '沉淀结论'
  if (/数据变换|transform/i.test(s)) return '数据变换'
  if (/汇总报告|report/i.test(s)) return '生成报告'
  if (/describe|表结构|schema/i.test(s)) return '获取数据集信息'
  if (/sample|样本/i.test(s)) return '获取数据样本'
  if (/sql/i.test(s)) return 'SQL 执行'
  return s || '执行中'
}

// ===== History =====
function buildStepsFromHistory(plan?: string, process?: any[], report?: string): StepItem[] {
  const steps: StepItem[] = []

  if (plan) {
    steps.push({
      title: '任务规划',
      status: 'done',
      detailsMd: plan,
      details: renderMd(plan),
      expanded: false,
      stepType: 'plan',
      events: [
        {
          type: 'info',
          title: '任务规划',
          contentHtml: renderMd(plan),
          expanded: true,
        },
      ],
    })
  }

  if (process && Array.isArray(process)) {
    let currentStep: StepItem | null = null
    for (const item of process) {
      const typ = item?.type || 'process'
      const c = item?.content || ''
      if (!c) continue

      if (typ === 'stage') {
        if (currentStep) {
          currentStep.details = renderMd(currentStep.detailsMd)
          currentStep.events = parseProcessContent(currentStep.detailsMd, currentStep.stepType)
        }
        const title = classifyStageTitle(c)
        currentStep = {
          title,
          status: 'done',
          detailsMd: '',
          details: '',
          expanded: false,
          stepType: c,
          events: [],
        }
        steps.push(currentStep)
        continue
      }

      if (currentStep) {
        currentStep.detailsMd += c
        if (typeof item.duration_ms === 'number') {
          currentStep.durationMs = item.duration_ms
        }
        if (typeof item.result_summary === 'string' && item.result_summary) {
          currentStep.resultSummary = item.result_summary
        }
      } else {
        currentStep = {
          title: '执行过程',
          status: 'done',
          detailsMd: c,
          details: '',
          expanded: false,
          stepType: 'process',
          events: [],
        }
        steps.push(currentStep)
      }
    }
    if (currentStep) {
      if (!currentStep.details) currentStep.details = renderMd(currentStep.detailsMd)
      if (!currentStep.events.length) {
        currentStep.events = parseProcessContent(currentStep.detailsMd, currentStep.stepType)
      }
    }
  }

  if (report) {
    steps.push({
      title: '生成报告',
      status: 'done',
      detailsMd: '报告已生成，点击下方卡片查看。',
      details: renderMd('报告已生成，点击下方卡片查看。'),
      expanded: false,
      stepType: 'report',
      events: [
        {
          type: 'info',
          title: '生成报告',
          content: '报告已生成，点击下方卡片查看完整报告。',
          expanded: true,
        },
      ],
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
        const agentMsg: ChatMessage = {
          role: 'agent',
          content: '',
          thinkingLabel: '分析完成',
        }
        agentMsg.steps = buildStepsFromHistory(data.plan, data.process, data.report)

        if (data.plan) {
          agentMsg.planHtml = renderMd(data.plan)
          agentMsg.planMd = data.plan
        }

        if (data.report) {
          agentMsg.reportHtml = renderMd(data.report)
          agentMsg.reportMd = data.report
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

// ===== Report =====
function openReport(msg: ChatMessage) {
  if (msg.reportHtml) {
    activeReportHtml.value = msg.reportHtml
    activeReportMd.value = msg.reportMd || ''
    detailMode.value = 'report'
    detailPanelOpen.value = true
    selectedMsgIdx.value = -1
    selectedStepIdx.value = -1
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

// ===== Step helpers =====
function createStep(
  title: string,
  status: StepItem['status'] = 'running',
  stepType = ''
): StepItem {
  const s: StepItem = {
    title,
    status,
    details: '',
    detailsMd: '',
    expanded: false,
    stepType,
    events: [],
  }
  if (status === 'running') {
    s.startedAt = Date.now()
  }
  return s
}

function finalizeStep(step: StepItem) {
  step.status = 'done'
  if (step.startedAt != null && step.durationMs == null) {
    step.durationMs = Date.now() - step.startedAt
  }
  if (step.detailsMd) {
    step.details = renderMd(step.detailsMd)
    if (!step.events.length) {
      step.events = parseProcessContent(step.detailsMd, step.stepType)
    }
  }
}

function appendToStep(step: StepItem, text: string) {
  step.detailsMd += text
  step.details = renderMd(step.detailsMd)
}

// ===== Send Message =====
function getAgentMsg(): ChatMessage {
  return messages.value[messages.value.length - 1]
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

  messages.value.push({
    role: 'agent',
    content: '',
    loading: true,
    steps: [],
  })

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
      const amBad = getAgentMsg()
      amBad.content = response.statusText || '请求失败'
      amBad.loading = false
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
            const errStep = createStep('错误', 'error', 'error')
            errStep.detailsMd = c || '未知错误'
            errStep.details = renderMd(errStep.detailsMd)
            errStep.events = [
              { type: 'error', title: '执行错误', content: c || '未知错误', expanded: true },
            ]
            const am = getAgentMsg()
            am.steps!.push(errStep)
            am.content = `${c || '未知错误'}`
            am.thinkingLabel = '执行失败'
            break
          }

          if (data.type === 'start' && data.chat_id) {
            currentSessionId.value = data.chat_id
            sessionStorage.setItem('da_session', String(data.chat_id))
            await loadSessions()

            if (!currentStep) {
              const startStep = createStep(t('deep_analysis.agent_start_step'), 'done', 'start')
              startStep.events = [
                {
                  type: 'info',
                  title: t('deep_analysis.agent_start_step'),
                  content: t('deep_analysis.agent_session_created'),
                  expanded: true,
                },
              ]
              getAgentMsg().steps!.push(startStep)
            }
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
            currentStep = createStep('任务规划', 'done', 'plan')
            currentStep.detailsMd = c
            currentStep.details = renderMd(c)
            currentStep.events = [
              { type: 'info', title: '任务规划', contentHtml: renderMd(c), expanded: true },
            ]
            const am = getAgentMsg()
            am.steps!.push(currentStep)
            am.planHtml = renderMd(c)
            am.planMd = c
            am.planExpanded = true
            currentStep = null
            scrollToBottom()
            continue
          }

          if (data.type === 'stage' && c) {
            const stageTitle = classifyStageTitle(c)
            currentStage.value = stageTitle

            if (currentStep && currentStep.status === 'running') {
              finalizeStep(currentStep)
            }
            currentStep = createStep(stageTitle, 'running', c)
            getAgentMsg().steps!.push(currentStep)
            scrollToBottom()
            nextTick(() => followExecutingStep())
            continue
          }

          if (data.type === 'report' && c) {
            reportMd += c
            continue
          }

          if (c && data.type !== 'report') {
            const dm = (data as { duration_ms?: number }).duration_ms
            const rs = (data as { result_summary?: string }).result_summary
            if (currentStep) {
              appendToStep(currentStep, c)
              if (typeof dm === 'number') {
                currentStep.durationMs = dm
              }
              if (typeof rs === 'string' && rs) {
                currentStep.resultSummary = rs
              }
            } else {
              currentStep = createStep('分析中', 'running', 'process')
              getAgentMsg().steps!.push(currentStep)
              appendToStep(currentStep, c)
              if (typeof dm === 'number') {
                currentStep.durationMs = dm
              }
              if (typeof rs === 'string' && rs) {
                currentStep.resultSummary = rs
              }
              nextTick(() => followExecutingStep())
            }

            const am = getAgentMsg()
            const mi = messages.value.length - 1
            const si = am.steps!.indexOf(currentStep!)
            if (si >= 0 && selectedMsgIdx.value === mi && selectedStepIdx.value === si) {
              activeStepDetail.value = currentStep
              activeStepEvents.value = parseProcessContent(
                currentStep!.detailsMd,
                currentStep!.stepType
              )
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

    const amFinal = getAgentMsg()
    if (reportMd) {
      const reportStep = createStep('生成报告', 'done', 'report')
      reportStep.detailsMd = '报告已生成，点击下方卡片查看完整报告。'
      reportStep.details = renderMd(reportStep.detailsMd)
      reportStep.events = [
        { type: 'info', title: '生成报告', content: '报告已生成', expanded: true },
      ]
      amFinal.steps!.push(reportStep)

      amFinal.reportHtml = renderMd(reportMd)
      amFinal.reportMd = reportMd
      amFinal.contentHtml = renderMd('**分析完成** — 点击下方卡片查看完整报告')
      amFinal.thinkingLabel = '分析完成'
    } else {
      amFinal.thinkingLabel = '分析完成'
    }
  } catch (e: any) {
    if (e?.name !== 'AbortError') {
      const amErr = getAgentMsg()
      amErr.content = `${e?.message || String(e)}`
      amErr.thinkingLabel = '执行异常'
    }
  } finally {
    getAgentMsg().loading = false
    loading.value = false
    abortController = null
    scrollToBottom()
  }
}

// ===== Rename / Delete =====
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
  background: #f7f8fa;
}
.da-layout {
  height: 100%;
}

/* ===== Sidebar ===== */
.da-sidebar {
  background: #f7f8fa;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e8e9eb;
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
  color: #1f2329;
}
.da-icon-btn {
  min-width: unset;
  width: 28px;
  height: 28px;
  font-size: 18px;
  --ed-button-text-color: #646a73;
}
.da-icon-btn:hover {
  background: rgba(31, 35, 41, 0.08);
  border-radius: 6px;
}
.da-new-btn {
  width: 100%;
  height: 38px;
  font-weight: 500;
  border-radius: 8px;
}
.da-session-search {
  height: 32px;
  width: 100%;
}
.da-session-search :deep(.ed-input__wrapper) {
  background-color: #f5f6f7;
}
.da-session-scroll {
  flex: 1;
  min-height: 0;
}
.da-session-list-inner {
  padding-left: 16px;
  padding-right: 16px;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.da-session-list-inner .bulk-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 8px;
  margin-top: 4px;
  border-radius: 6px;
}
.da-session-list-inner .bulk-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.da-session-list-inner .bulk-selected {
  font-size: 12px;
  color: #646a73;
}
.da-session-list-inner .bulk-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.da-session-list-inner .bulk-clear-link {
  font-size: 12px;
  color: #646a73;
  cursor: pointer;
}
.da-session-list {
  padding: 0 0 16px;
}
.da-empty {
  width: 100%;
  text-align: center;
  margin-top: 48px;
  padding: 24px 16px;
  color: #646a73;
  font-size: 14px;
  line-height: 22px;
}
.da-group {
  margin-bottom: 4px;
}
.da-group-title {
  padding: 6px 8px;
  font-size: 12px;
  font-weight: 500;
  color: #8f959e;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  user-select: none;
}
.da-group-title .collapsed {
  transform: rotate(-90deg);
}
.da-session-item {
  min-height: 40px;
  padding: 8px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  cursor: pointer;
  margin-bottom: 2px;
  position: relative;
  transition: background 0.15s;
}
.da-session-item .select-checkbox {
  margin-right: 8px;
  flex-shrink: 0;
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
  color: #1f2329;
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
  max-width: 860px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
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
.da-welcome-avatar {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  background: linear-gradient(135deg, #e6f7f2, #d0f0e8);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 4px;
}
.da-avatar-svg {
  width: 28px;
  height: 28px;
}
.da-avatar-svg :deep(path) {
  fill: #1cba90;
}
.da-welcome-title {
  font-size: 20px;
  font-weight: 600;
  color: #1f2329;
  margin: 0;
}
.da-welcome-desc {
  font-size: 14px;
  max-width: 460px;
  line-height: 1.6;
  margin: 0;
}
.da-welcome-caps {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
  align-items: flex-start;
}
.da-cap-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #4e5969;
}

/* Messages */
.da-msg {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.da-msg-user {
  flex-direction: row-reverse;
}
.da-user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #e8e9eb;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #646a73;
}
.da-agent-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #e6f7f2, #d0f0e8);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.da-agent-avatar .da-avatar-svg {
  width: 18px;
  height: 18px;
}
.da-msg-content {
  flex: 1;
  min-width: 0;
  max-width: 90%;
}

.da-bubble-user {
  background: var(--ed-color-primary, #1cba90);
  color: #fff;
  border-radius: 16px 16px 4px 16px;
  padding: 10px 16px;
  font-size: 14px;
  line-height: 1.6;
  display: inline-block;
}

/* Agent status */
.da-agent-status {
  margin-bottom: 8px;
}
.da-status-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}
.da-status-running {
  background: rgba(28, 186, 144, 0.08);
  color: #1cba90;
}
.da-status-done {
  background: rgba(28, 186, 144, 0.08);
  color: #1cba90;
}

/* Plan wrapper — collapsible thinking block */
.da-plan-wrapper {
  margin-bottom: 12px;
}
.da-plan-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #f7f8fa;
  border: 1px solid #e8e9eb;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  color: #646a73;
  transition: background 0.15s;
}
.da-plan-toggle:hover {
  background: #f0f1f3;
}
.da-plan-toggle-text {
  flex: 1;
  font-weight: 500;
  color: #1f2329;
}
.da-plan-toggle-link {
  font-size: 12px;
  color: var(--ed-color-primary, #1cba90);
  font-weight: 500;
}
.da-plan-block {
  background: #f7f8fa;
  border-radius: 0 0 12px 12px;
  border: 1px solid #e8e9eb;
  border-top: none;
  padding: 16px;
  margin-top: -1px;
  font-size: 14px;
  line-height: 1.7;
  max-height: 400px;
  overflow-y: auto;
}
.da-plan-block :deep(h1),
.da-plan-block :deep(h2),
.da-plan-block :deep(h3) {
  margin-top: 0.6em;
  margin-bottom: 0.4em;
}
.da-plan-block :deep(ol),
.da-plan-block :deep(ul) {
  padding-left: 1.5em;
}

/* Steps timeline */
.da-steps-timeline {
  margin-bottom: 12px;
  padding: 4px 0;
}
.da-step-item {
  display: flex;
  gap: 10px;
  position: relative;
  padding: 6px 8px;
  border-radius: 8px;
  cursor: default;
  transition: background 0.15s;
}
.da-step-item.da-step-item--interactive {
  cursor: pointer;
}
.da-step-item.da-step-item--interactive:hover {
  background: rgba(31, 35, 41, 0.04);
}
.da-step-item.da-step-item--interactive.da-step-selected:hover {
  background: rgba(28, 186, 144, 0.12);
}
.da-step-item:not(.da-step-item--interactive):hover {
  background: transparent;
}
.da-step-item.da-step-selected {
  background: rgba(28, 186, 144, 0.08);
}
.da-step-item:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 19px;
  top: 30px;
  bottom: -2px;
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
  z-index: 1;
}
.da-step-check {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--ed-color-primary, #1cba90);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}
.da-step-error-dot {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #f56c6c;
  color: #fff;
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
}
.da-step-body {
  flex: 1;
  min-width: 0;
  padding: 1px 0;
}
.da-step-header {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}
.da-step-item--interactive .da-step-label {
  transition: color 0.15s;
}
.da-step-item--interactive:hover .da-step-label {
  color: var(--ed-color-primary, #1cba90);
}
.da-step-label {
  font-size: 14px;
  font-weight: 500;
  color: #1f2329;
}
.da-step-done .da-step-label {
  color: #1f2329;
}
.da-step-active .da-step-label {
  color: var(--ed-color-primary, #1cba90);
}
.da-step-error .da-step-label {
  color: #f56c6c;
}
.da-step-desc {
  font-size: 12px;
  color: #646a73;
  line-height: 1.5;
  margin-top: 2px;
  word-break: break-all;
}
.da-step-result {
  font-size: 12px;
  color: #1f2329;
  line-height: 1.45;
  margin-top: 4px;
  padding: 6px 8px;
  background: #f4f6ff;
  border-radius: 6px;
  border-left: 3px solid #4b6ef5;
  word-break: break-word;
}
.da-detail-result-chip {
  flex: 1;
  min-width: 0;
  max-width: 220px;
  font-size: 11px;
  color: #646a73;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.da-step-substeps {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
  font-size: 11px;
}
.da-substep-item {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 1px 6px;
  border-radius: 4px;
}
.da-substep-done {
  color: #1cba90;
  background: rgba(28, 186, 144, 0.06);
}
.da-substep-active {
  color: var(--ed-color-primary, #1cba90);
  background: rgba(28, 186, 144, 0.1);
  font-weight: 500;
}
.da-substep-divider {
  color: #c0c4cc;
  font-size: 12px;
}

/* Stream block — realtime agent output */
.da-stream-block {
  background: #f7f8fa;
  border-radius: 10px;
  padding: 12px 14px;
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.6;
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid #e8e9eb;
}
.da-stream-block :deep(pre) {
  background: #fff;
  padding: 8px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 12px;
}
.da-stream-block :deep(table) {
  border-collapse: collapse;
  width: 100%;
  font-size: 12px;
}
.da-stream-block :deep(th),
.da-stream-block :deep(td) {
  border: 1px solid #dee0e3;
  padding: 4px 8px;
}

/* Agent text */
.da-agent-text {
  word-break: break-word;
  font-size: 14px;
  line-height: 1.6;
}
.da-agent-text :deep(pre) {
  background: #f7f8fa;
  padding: 10px;
  border-radius: 8px;
  overflow-x: auto;
}

/* Report card */
.da-report-card {
  margin-top: 12px;
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid #e8e9eb;
  background: #fff;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.da-report-card:hover {
  border-color: var(--ed-color-primary, #1cba90);
  box-shadow: 0 2px 8px rgba(28, 186, 144, 0.12);
}
.da-report-card-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, #e6f7f2, #d0f0e8);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ed-color-primary, #1cba90);
  flex-shrink: 0;
}
.da-report-card-body {
  flex: 1;
  min-width: 0;
}
.da-report-card-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2329;
}
.da-report-card-desc {
  font-size: 12px;
  color: #8f959e;
  margin-top: 2px;
}

/* Input bar */
.da-input-bar {
  padding: 16px 32px 20px;
  border-top: 1px solid #f0f1f3;
  max-width: 860px;
  margin: 0 auto;
  width: 100%;
}
.da-input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: #f7f8fa;
  border: 1px solid #e8e9eb;
  border-radius: 16px;
  padding: 8px 12px;
  transition: border-color 0.2s;
}
.da-input-wrapper:focus-within {
  border-color: var(--ed-color-primary, #1cba90);
}
.da-input {
  flex: 1;
}
.da-input :deep(.el-textarea__inner) {
  background: transparent;
  box-shadow: none;
  border: none;
  padding: 4px 0;
  font-size: 14px;
  line-height: 1.5;
}
.da-send-btn {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
}

/* ===== Detail Panel ===== */
.da-detail-panel {
  width: 440px;
  min-width: 360px;
  max-width: 520px;
  background: #fff;
  border-left: 1px solid #e8e9eb;
  display: flex;
  flex-direction: column;
}
.da-detail-header {
  padding: 14px 16px;
  border-bottom: 1px solid #f0f1f3;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.da-detail-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2329;
}
.da-detail-toolbar {
  padding: 10px 16px;
  border-bottom: 1px solid #f0f1f3;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.da-detail-toolbar-main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}
.da-step-duration-header {
  flex-shrink: 0;
  font-size: 12px;
  color: #8f959e;
}
.da-step-duration {
  margin-left: auto;
  font-size: 12px;
  color: #8f959e;
  flex-shrink: 0;
}
.da-detail-stream {
  padding: 12px 16px 16px;
  border-bottom: 1px solid #f0f1f3;
}
.da-detail-tab {
  font-size: 13px;
  font-weight: 500;
  color: #1f2329;
}
.da-detail-tab.active {
  color: var(--ed-color-primary, #1cba90);
}
.da-detail-actions {
  display: flex;
  gap: 8px;
}
.da-detail-status-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #8f959e;
}
.da-detail-body-scroll {
  flex: 1;
  min-height: 0;
}
.da-detail-body {
  padding: 16px;
  line-height: 1.75;
  font-size: 14px;
}
.da-detail-body :deep(h1) {
  font-size: 1.3rem;
  margin: 1em 0 0.5em;
}
.da-detail-body :deep(h2) {
  font-size: 1.1rem;
  margin: 0.9em 0 0.4em;
  border-bottom: 1px solid #eee;
  padding-bottom: 6px;
}
.da-detail-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 10px 0;
}
.da-detail-body :deep(th),
.da-detail-body :deep(td) {
  border: 1px solid #dee0e3;
  padding: 8px 10px;
}
.da-detail-events {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Event Cards */
.da-event-card {
  border: 1px solid #e8e9eb;
  border-radius: 10px;
  overflow: hidden;
  transition: border-color 0.15s;
}
.da-event-card:hover {
  border-color: #c0c4cc;
}
.da-event-card-sql {
  border-color: #b8c7ff;
  box-shadow: 0 0 0 1px rgba(75, 110, 245, 0.14);
}
.da-event-card-sql .da-event-card-header {
  background: #f4f6ff;
}
.da-event-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  cursor: pointer;
  user-select: none;
  background: #fafbfc;
}
.da-event-card-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.da-evt-data {
  background: #e6f7f2;
  color: #1cba90;
}
.da-evt-sql {
  background: #e8eeff;
  color: #4b6ef5;
}
.da-evt-transform {
  background: #fef3e6;
  color: #e6a23c;
}
.da-evt-tool {
  background: #f0e6ff;
  color: #9b6ed6;
}
.da-evt-info {
  background: #f0f1f3;
  color: #646a73;
}
.da-evt-error {
  background: #fef0f0;
  color: #f56c6c;
}
.da-event-card-title {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
  color: #1f2329;
}
.da-event-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: #f0f1f3;
  color: #646a73;
}
.da-event-toggle {
  color: #c0c4cc;
  transition: transform 0.2s;
  flex-shrink: 0;
}
.da-event-toggle.open {
  transform: rotate(90deg);
}
.da-event-card-body {
  padding: 12px;
  border-top: 1px solid #f0f1f3;
}

/* SQL code */
.da-evt-sql-block .da-evt-section-title,
.da-evt-section-title {
  font-size: 12px;
  font-weight: 500;
  color: #8f959e;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.da-sql-code {
  background: #1e1e2e;
  color: #cdd6f4;
  border-radius: 8px;
  padding: 12px;
  overflow-x: auto;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.5;
  margin: 0;
}
.da-evt-meta {
  margin-top: 8px;
  font-size: 12px;
  color: #8f959e;
}

/* Schema table */
.da-schema-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  margin-top: 4px;
}
.da-schema-table th {
  background: #f7f8fa;
  font-weight: 500;
  color: #646a73;
  text-align: left;
  padding: 6px 10px;
  border: 1px solid #e8e9eb;
}
.da-schema-table td {
  padding: 6px 10px;
  border: 1px solid #e8e9eb;
  color: #1f2329;
}

/* Event content */
.da-evt-content {
  font-size: 13px;
  line-height: 1.6;
  color: #4e5969;
}
.da-evt-content :deep(pre) {
  background: #f7f8fa;
  padding: 8px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 12px;
}
.da-evt-content :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 6px 0;
  font-size: 12px;
}
.da-evt-content :deep(th),
.da-evt-content :deep(td) {
  border: 1px solid #dee0e3;
  padding: 4px 8px;
}
.da-evt-text {
  white-space: pre-wrap;
  word-break: break-word;
}

/* Animations */
.da-panel-slide-enter-active,
.da-panel-slide-leave-active {
  transition: all 0.25s ease;
}
.da-panel-slide-enter-from,
.da-panel-slide-leave-to {
  transform: translateX(100%);
  opacity: 0;
}
.da-evt-expand-enter-active,
.da-evt-expand-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}
.da-evt-expand-enter-from,
.da-evt-expand-leave-to {
  opacity: 0;
  max-height: 0;
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
  border-radius: 6px;
}
.da-popover-item:hover {
  background: rgba(31, 35, 41, 0.06);
}
.da-popover-item.danger {
  color: var(--ed-color-danger);
}

/* Responsive */
@media (max-width: 1200px) {
  .da-detail-panel {
    width: 360px;
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
  .da-detail-panel {
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
