<template>
  <div class="deep-analysis-page no-padding">
    <el-container class="da-layout da-chat-layout">
      <!-- 左侧：会话历史（与智能问数一致的标题+收起+新建+搜索） -->
      <el-aside
        v-if="sessionSideBarShow"
        class="da-aside da-session-aside chat-container-left"
        width="280px"
      >
        <header class="da-aside-header chat-list-header">
          <div class="title">
            <div>{{ t('menu.deep_analysis') }}</div>
            <el-button link type="primary" class="icon-btn" @click="hideSessionSideBar">
              <el-icon><icon_sidebar_outlined /></el-icon>
            </el-button>
          </div>
          <el-button type="primary" class="btn" @click="goNewAnalysis">
            <el-icon style="margin-right: 6px"><icon_new_chat_outlined /></el-icon>
            {{ t('deep_analysis.new_analysis') }}
          </el-button>
          <el-input
            v-model="sessionSearch"
            :prefix-icon="Search"
            class="search"
            clearable
            :placeholder="t('deep_analysis.session_search_placeholder')"
          />
        </header>
        <div v-if="sessionList.length === 0 && !sessionLoading" class="da-empty-sessions">
          {{ t('deep_analysis.no_sessions') }}
        </div>
        <el-scrollbar v-else class="da-session-list-wrap">
          <div class="da-session-list-inner">
            <div class="da-session-bulk-bar">
              <div class="da-session-bulk-left">
                <el-checkbox
                  :indeterminate="hasSessionSelection && !allSessionSelected"
                  :model-value="allSessionSelected"
                  @change="toggleSessionSelectAll"
                >
                  {{ t('datasource.select_all') }}
                </el-checkbox>
                <span v-if="hasSessionSelection" class="da-session-bulk-selected">
                  {{ t('user.selected_2_items', { msg: sessionSelectedIds.length }) }}
                </span>
              </div>
              <div class="da-session-bulk-right">
                <el-dropdown @command="handleClearSessionsByScope">
                  <span class="da-session-bulk-clear-link">
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
                  v-if="hasSessionSelection"
                  size="small"
                  type="danger"
                  text
                  class="da-session-bulk-delete-btn"
                  @click="handleBulkDeleteSessions"
                >
                  {{ t('dashboard.delete') }}
                </el-button>
              </div>
            </div>
            <div v-for="group in computedSessionGroups" :key="group.key" class="da-session-group">
              <div
                class="da-session-group-title"
                @click="toggleGroup(group.key)"
              >
                <el-icon :class="{ expand: !sessionExpandMap[group.key] }" size="10">
                  <icon_expand_down_filled />
                </el-icon>
                {{ group.key }}
              </div>
              <template v-for="item in group.list" :key="item.id">
                <div
                  v-show="sessionExpandMap[group.key]"
                  class="da-session-item"
                  :class="{ active: currentSessionId === item.id }"
                  @click="selectSession(item)"
                >
                  <el-checkbox
                    class="da-session-item-checkbox"
                    :model-value="isSessionSelected(item.id)"
                    @click.stop
                    @change="() => toggleSessionSelect(item)"
                  />
                  <span class="da-session-brief">{{ item.brief || t('deep_analysis.report_title') }}</span>
                  <el-popover
                    trigger="click"
                    :teleported="false"
                    popper-class="popover-card_deep_analysis"
                    placement="bottom"
                  >
                    <template #reference>
                      <el-icon class="da-session-more" size="16" @click.stop>
                        <icon_more_outlined />
                      </el-icon>
                    </template>
                    <div class="content">
                      <div class="item" @click.stop="openRename(item)">
                        <el-icon size="16"><icon_rename /></el-icon>
                        {{ t('dashboard.rename') }}
                      </div>
                      <div class="item" @click.stop="confirmDeleteSession(item)">
                        <el-icon size="16"><icon_delete /></el-icon>
                        {{ t('dashboard.delete') }}
                      </div>
                    </div>
                  </el-popover>
                </div>
              </template>
            </div>
          </div>
        </el-scrollbar>
      </el-aside>

      <!-- 收起后：与智能问数一致的浮动按钮（历史 | 新建分析） -->
      <div v-if="!sessionSideBarShow" class="hidden-sidebar-btn">
        <el-popover
          v-model:visible="sessionPopoverVisible"
          :width="280"
          placement="bottom-start"
          popper-class="popover-chat_history"
          trigger="click"
        >
          <template #reference>
            <el-button link type="primary" class="icon-btn" @click="showSessionSideBar">
              <el-icon><icon_sidebar_outlined /></el-icon>
            </el-button>
          </template>
          <div class="chat-container-right-container da-popover-inner">
            <header class="chat-list-header in-popover">
              <div class="title">
                <div>{{ t('menu.deep_analysis') }}</div>
                <el-button link type="primary" class="icon-btn" @click="closeSessionPopover">
                  <el-icon><icon_sidebar_outlined /></el-icon>
                </el-button>
              </div>
              <el-button type="primary" class="btn" @click="goNewAnalysis">
                <el-icon style="margin-right: 6px"><icon_new_chat_outlined /></el-icon>
                {{ t('deep_analysis.new_analysis') }}
              </el-button>
              <el-input
                v-model="sessionSearch"
                :prefix-icon="Search"
                class="search"
                clearable
                :placeholder="t('deep_analysis.session_search_placeholder')"
              />
            </header>
            <div v-if="sessionList.length === 0 && !sessionLoading" class="da-empty-sessions">
              {{ t('deep_analysis.no_sessions') }}
            </div>
            <el-scrollbar v-else class="da-session-list-wrap" style="max-height: 400px">
              <div class="da-session-list-inner">
                <div class="da-session-bulk-bar">
                  <div class="da-session-bulk-left">
                    <el-checkbox
                      :indeterminate="hasSessionSelection && !allSessionSelected"
                      :model-value="allSessionSelected"
                      @change="toggleSessionSelectAll"
                    >
                      {{ t('datasource.select_all') }}
                    </el-checkbox>
                    <span v-if="hasSessionSelection" class="da-session-bulk-selected">
                      {{ t('user.selected_2_items', { msg: sessionSelectedIds.length }) }}
                    </span>
                  </div>
                  <div class="da-session-bulk-right">
                    <el-dropdown @command="handleClearSessionsByScope">
                      <span class="da-session-bulk-clear-link">
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
                      v-if="hasSessionSelection"
                      size="small"
                      type="danger"
                      text
                      class="da-session-bulk-delete-btn"
                      @click="handleBulkDeleteSessions"
                    >
                      {{ t('dashboard.delete') }}
                    </el-button>
                  </div>
                </div>
                <div v-for="group in computedSessionGroups" :key="group.key" class="da-session-group">
                  <div class="da-session-group-title" @click="toggleGroup(group.key)">
                    <el-icon :class="{ expand: !sessionExpandMap[group.key] }" size="10">
                      <icon_expand_down_filled />
                    </el-icon>
                    {{ group.key }}
                  </div>
                  <template v-for="item in group.list" :key="item.id">
                    <div
                      v-show="sessionExpandMap[group.key]"
                      class="da-session-item"
                      :class="{ active: currentSessionId === item.id }"
                      @click="selectSession(item); closeSessionPopover()"
                    >
                      <el-checkbox
                        class="da-session-item-checkbox"
                        :model-value="isSessionSelected(item.id)"
                        @click.stop
                        @change="() => toggleSessionSelect(item)"
                      />
                      <span class="da-session-brief">{{ item.brief || t('deep_analysis.report_title') }}</span>
                    </div>
                  </template>
                </div>
              </div>
            </el-scrollbar>
          </div>
        </el-popover>
        <el-tooltip effect="dark" :offset="8" :content="t('deep_analysis.new_analysis')" placement="bottom">
          <el-button link type="primary" class="icon-btn" @click="goNewAnalysis">
            <el-icon><icon_new_chat_outlined /></el-icon>
          </el-button>
        </el-tooltip>
      </div>

      <!-- 中间：无 session 欢迎态 / 有 session 工作台 -->
      <el-main
        class="da-center-main"
        :class="{ 'hide-sidebar': !sessionSideBarShow }"
      >
        <div class="da-center-inner">
          <!-- 无 session：欢迎 + 选择数据源入口 -->
          <template v-if="currentSessionId === undefined">
            <div class="da-welcome-block">
              <div class="da-welcome-desc">{{ t('deep_analysis.starter_desc') }}</div>
              <el-button type="primary" size="large" class="da-welcome-btn" @click="openBindDsPopup">
                <el-icon style="margin-right: 8px"><icon_database_colorful /></el-icon>
                {{ t('deep_analysis.bind_datasource_start') }}
              </el-button>
            </div>
          </template>

          <!-- 有 session：数据源只读 + 分析工作台 -->
          <template v-else>
            <section class="da-datasource-section">
              <div class="da-section-head">
                <span class="da-section-title">{{ t('deep_analysis.select_datasource_title') }}</span>
              </div>
              <div class="da-ds-readonly">
                <el-icon size="16" class="da-ds-icon"><icon_database_colorful /></el-icon>
                <span class="da-ds-name">{{ currentSessionDatasourceName || t('deep_analysis.select_datasource') }}</span>
              </div>
            </section>

            <!-- 分析记录卡片：数据源下、工作台上，横向滑动，默认约 2 张可见 -->
            <section v-if="currentSessionId != null && analysisCards.length > 0" class="da-cards-section">
              <div class="da-section-head">
                <span class="da-section-title">{{ t('deep_analysis.analysis_cards') }}</span>
              </div>
              <el-scrollbar class="da-cards-scroll" wrap-style="overflow-x: auto;">
                <div class="da-cards-inner">
                  <div
                    v-for="card in analysisCards"
                    :key="card.id"
                    class="da-analysis-card"
                    :class="{ active: selectedRecordId === card.id }"
                    @click="selectCard(card)"
                  >
                    <el-icon
                      class="da-card-delete"
                      @click.stop="confirmDeleteCard(card)"
                    >
                      <icon_delete />
                    </el-icon>
                    <div class="da-card-question">{{ (card.question || '').slice(0, 36) }}{{ (card.question || '').length > 36 ? '…' : '' }}</div>
                    <div class="da-card-time">{{ card.create_time ? dayjs(card.create_time).format('YYYY-MM-DD HH:mm') : '' }}</div>
                  </div>
                </div>
              </el-scrollbar>
            </section>

            <!-- 新建分析：输入与操作 -->
            <section class="da-composer-section">
            <div class="da-section-head">
              <span class="da-section-title">{{ t('deep_analysis.workspace_label') }}</span>
            </div>
            <div class="da-composer-card">
              <div class="da-composer-top">
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
                <div class="composer-field steps-field">
                  <label>{{ t('deep_analysis.max_steps') }}</label>
                  <el-input-number
                    v-model="maxSteps"
                    :min="4"
                    :max="30"
                    :step="1"
                    :disabled="loading"
                    clearable
                    :placeholder="t('deep_analysis.max_steps_hint')"
                    class="max-steps-input"
                  />
                  <span class="field-hint">{{ t('deep_analysis.max_steps_hint') }}</span>
                </div>
              </div>
              <div class="composer-field question-field">
                <label>{{ t('deep_analysis.question') }}</label>
                <el-input
                  v-model="question"
                  type="textarea"
                  :rows="5"
                  :placeholder="t('deep_analysis.question_placeholder')"
                  maxlength="2000"
                  show-word-limit
                  :disabled="loading"
                  @keydown.enter.exact.prevent="startAnalysis"
                  @keydown.ctrl.enter.exact.prevent="handleCtrlEnter"
                />
              </div>
              <div v-if="false && (recommendLoading || quickExamples.length)" class="da-example-block">
                <div class="da-example-title">{{ t('deep_analysis.examples') }}</div>
                <div class="da-example-list">
                  <template v-if="recommendLoading">
                    <span class="da-example-loading">{{ t('deep_analysis.recommend_loading') }}</span>
                  </template>
                  <template v-else>
                    <button
                      v-for="ex in quickExamples"
                      :key="ex"
                      type="button"
                      class="da-example-chip"
                      @click="applyExample(ex)"
                    >
                      {{ ex }}
                    </button>
                  </template>
                </div>
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
          </section>
          </template>
        </div>
      </el-main>

      <!-- 右侧：分析窗口 -->
      <aside class="da-result-aside">
        <header class="da-result-header">
          <span class="da-result-title">{{ t('deep_analysis.result_panel_title') }}</span>
          <el-button
            v-if="reportMarkdown && !loading"
            type="primary"
            plain
            size="small"
            class="da-export-btn"
            @click="exportReport"
          >
            {{ t('deep_analysis.export_report') }}
          </el-button>
        </header>
        <el-scrollbar class="da-result-body">
          <div v-if="!hasContent && !loading" class="da-result-empty">
            <div class="da-result-empty-icon"></div>
            <p class="da-result-empty-text">{{ t('deep_analysis.result_empty_tip') }}</p>
          </div>
          <template v-else>
            <div v-if="selectedRecordConfig && (selectedRecordConfig.question != null || selectedRecordConfig.max_data_length != null || selectedRecordConfig.max_steps != null)" class="da-config-block">
              <div class="da-section-head">
                <span class="da-section-title">{{ t('deep_analysis.config_at_time') }}</span>
              </div>
              <div class="da-config-body">
                <div v-if="selectedRecordConfig.question" class="da-config-row">
                  <span class="da-config-label">{{ t('deep_analysis.question') }}</span>
                  <span class="da-config-value">{{ selectedRecordConfig.question }}</span>
                </div>
                <div v-if="selectedRecordConfig.max_data_length != null" class="da-config-row">
                  <span class="da-config-label">{{ t('deep_analysis.max_rows') }}</span>
                  <span class="da-config-value">{{ selectedRecordConfig.max_data_length }}</span>
                </div>
                <div v-if="selectedRecordConfig.max_steps != null" class="da-config-row">
                  <span class="da-config-label">{{ t('deep_analysis.max_steps') }}</span>
                  <span class="da-config-value">{{ selectedRecordConfig.max_steps }}</span>
                </div>
              </div>
            </div>
            <div v-if="datasourceId || currentStage || loading || hasContent" class="da-summary-grid">
              <div class="da-summary-card">
                <div class="summary-label">{{ t('deep_analysis.selected_datasource') }}</div>
                <div class="summary-value">{{ currentSessionDatasourceName || selectedDatasourceName || '--' }}</div>
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
              <div class="da-summary-card">
                <div class="summary-label">{{ t('deep_analysis.max_steps') }}</div>
                <div class="summary-value">{{ maxSteps ?? t('deep_analysis.max_steps_auto') }}</div>
              </div>
            </div>
            <div v-if="errorMsg" class="error-block">
              <el-alert type="error" :title="errorMsg" show-icon />
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
            <transition-group name="da-result-chain" tag="div" class="da-result-chain-wrap">
              <div v-if="planHtml" key="plan" class="plan-block da-result-card">
                <el-collapse v-model="planCollapse">
                  <el-collapse-item :title="t('deep_analysis.task_plan')" name="plan">
                    <div class="report-body markdown-body" v-html="planHtml"></div>
                  </el-collapse-item>
                </el-collapse>
              </div>
              <div
                v-if="processChunks.length > 0 || (loading && !reportHtml)"
                key="process"
                class="process-block da-result-card"
              >
                <el-collapse v-model="processCollapse">
                  <el-collapse-item :title="t('deep_analysis.thinking_process')" name="process">
                    <div v-if="loading && processChunks.length === 0" class="loading-tip">
                      <el-icon class="is-loading"><Loading /></el-icon>
                      {{ t('deep_analysis.waiting') }}
                    </div>
                    <div v-else class="steps-container">
                      <template v-for="(block, idx) in processBlocks" :key="idx">
                        <div class="step-item">
                          <div v-if="block.reasoning_content" class="step-thinking">
                            <el-collapse>
                              <el-collapse-item :name="'p-' + idx">
                                <template #title>
                                  <span class="thinking-title">{{ t('deep_analysis.thinking') }} {{ idx + 1 }}</span>
                                </template>
                                <div class="thinking-content">{{ block.reasoning_content }}</div>
                              </el-collapse-item>
                            </el-collapse>
                          </div>
                          <div
                            v-if="block.kind === 'text' && block.content"
                            class="step-content markdown-body"
                            v-html="renderedContent(block.content)"
                          ></div>
                          <div v-else-if="block.kind === 'chart' && block.chartConfig" class="step-chart-wrap">
                            <ChartComponent
                              :id="'da-chart-' + currentSessionId + '-' + idx"
                              :type="(block.chartType || 'table') as string"
                              :columns="block.chartColumns || []"
                              :x="block.chartX || []"
                              :y="block.chartY || []"
                              :series="block.chartSeries || []"
                              :data="block.chartData || []"
                            />
                          </div>
                        </div>
                      </template>
                    </div>
                  </el-collapse-item>
                </el-collapse>
              </div>
              <div v-if="reportHtml" key="report" class="report-block da-result-card">
                <el-collapse v-model="reportCollapse">
                  <el-collapse-item :title="t('deep_analysis.report_title')" name="report">
                    <div class="report-body markdown-body da-report-body" v-html="reportHtml"></div>
                  </el-collapse-item>
                </el-collapse>
              </div>
            </transition-group>
          </template>
        </el-scrollbar>
      </aside>
    </el-container>

    <!-- 绑定数据源弹层（新建分析） -->
    <el-dialog
      v-model="bindDsPopupVisible"
      :title="t('deep_analysis.bind_datasource_title')"
      width="560"
      :close-on-click-modal="false"
      class="da-bind-ds-dialog"
      @closed="bindDsSelectedId = undefined"
    >
      <el-input
        v-model="datasourceSearch"
        clearable
        class="da-ds-search"
        :placeholder="t('deep_analysis.datasource_search_placeholder')"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-scrollbar class="da-bind-ds-list">
        <div
          v-for="ds in filteredDatasourceList"
          :key="ds.id"
          class="da-ds-item"
          :class="{ isActive: bindDsSelectedId === ds.id }"
          @click="selectDsInBindPopup(ds.id)"
        >
          <el-icon size="16" class="da-ds-icon"><icon_database_colorful /></el-icon>
          <span class="da-ds-name">{{ ds.name }}</span>
        </div>
        <div v-if="filteredDatasourceList.length === 0" class="da-ds-empty">
          {{ t('datasource.relevant_content_found') }}
        </div>
      </el-scrollbar>
      <template #footer>
        <el-button @click="closeBindDsPopup">{{ t('common.cancel') }}</el-button>
        <el-button
          type="primary"
          :loading="bindDsLoading"
          :disabled="bindDsSelectedId == null"
          @click="confirmBindDs"
        >
          {{ t('datasource.confirm') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 重命名弹窗 -->
    <el-dialog
      v-model="renameDialogVisible"
      :title="t('qa.rename_conversation_title')"
      width="420"
      destroy-on-close
      @closed="renameForm.name = ''"
    >
      <el-form ref="renameFormRef" :model="renameForm" :rules="renameRules" label-position="top">
        <el-form-item prop="name" :label="t('qa.conversation_title')">
          <el-input
            v-model="renameForm.name"
            maxlength="100"
            show-word-limit
            clearable
            :placeholder="t('deep_analysis.report_title')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="renameDialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="renameLoading" @click="submitRename">
          {{ t('common.save') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, ref, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus-secondary'
import { Search, Loading } from '@element-plus/icons-vue'
import { request } from '@/utils/request'
import { datasourceApi } from '@/api/datasource'
import { deepAnalysisApi } from '@/api/deepAnalysis'
import { chatApi } from '@/api/chat'
import type { ChatInfo } from '@/api/chat'
import md from '@/utils/markdown.ts'
import dayjs from 'dayjs'
import { getDate } from '@/utils/utils'
import { filter, includes, groupBy } from 'lodash-es'
import icon_new_chat_outlined from '@/assets/svg/icon_new_chat_outlined.svg'
import icon_sidebar_outlined from '@/assets/svg/icon_sidebar_outlined.svg'
import icon_expand_down_filled from '@/assets/svg/icon_expand-down_filled.svg'
import icon_more_outlined from '@/assets/svg/icon_more_outlined.svg'
import icon_rename from '@/assets/svg/icon_rename_outlined.svg'
import icon_delete from '@/assets/svg/icon_delete.svg'
import icon_database_colorful from '@/assets/svg/icon_database_colorful.svg'
import ChartComponent from '@/views/chat/component/ChartComponent.vue'
import 'github-markdown-css/github-markdown-light.css'

const { t } = useI18n()

const datasourceList = ref<any[]>([])
const datasourceSearch = ref('')
const datasourceId = ref<number | undefined>()
const question = ref('')
const maxDataLength = ref(1000)
const maxSteps = ref<number | undefined>(undefined)
const loading = ref(false)
const errorMsg = ref('')
const planMarkdown = ref('')
const planHtml = ref('')
const reportMarkdown = ref('')
const reportHtml = ref('')
const processChunks = ref<
  Array<{ content?: string; reasoning_content?: string; type?: string; chart?: unknown; data?: unknown }>
>([])
const planCollapse = ref<string[]>([])
const processCollapse = ref<string[]>([])
const reportCollapse = ref<string[]>([])
const currentStage = ref('')
let abortController: AbortController | null = null
let stopFlag = false

const sessionList = ref<ChatInfo[]>([])
const sessionLoading = ref(false)
const currentSessionId = ref<number | undefined>()
const sessionRecords = ref<any[]>([])
const selectedRecordId = ref<number | undefined>()
const selectedRecordConfig = ref<{ question?: string; max_data_length?: number; max_steps?: number } | null>(null)
const sessionSearch = ref('')
const sessionSideBarShow = ref(true)
const sessionPopoverVisible = ref(false)
const sessionExpandMap = ref<Record<string, boolean>>({
  [t('qa.today')]: true,
  [t('qa.week')]: true,
  [t('qa.earlier')]: true,
  [t('qa.no_time')]: true,
})

const renameDialogVisible = ref(false)
const renameLoading = ref(false)
const renameFormRef = ref()
const renameForm = reactive({ name: '', id: 0 })

const bindDsPopupVisible = ref(false)
const bindDsSelectedId = ref<number | undefined>()
const bindDsLoading = ref(false)
const currentSessionDatasourceName = ref('')
const renameRules = {
  name: [
    {
      required: true,
      message: t('datasource.please_enter') + t('common.empty') + t('qa.conversation_title'),
      trigger: 'blur',
    },
  ],
}

function groupByDate(item: ChatInfo) {
  const time = getDate(item.create_time)
  if (!time) return t('qa.no_time')
  const todayStart = dayjs(dayjs().format('YYYY-MM-DD') + ' 00:00:00').toDate()
  const todayEnd = dayjs(dayjs().format('YYYY-MM-DD') + ' 23:59:59').toDate()
  const weekStart = dayjs(dayjs().subtract(7, 'day').format('YYYY-MM-DD') + ' 00:00:00').toDate()
  if (time >= todayStart && time <= todayEnd) return t('qa.today')
  if (time < todayStart && time >= weekStart) return t('qa.week')
  if (time < weekStart) return t('qa.earlier')
  return t('qa.no_time')
}

const filteredSessionList = computed(() => {
  if (!sessionSearch.value.trim()) return sessionList.value
  return filter(sessionList.value, (c) =>
    includes((c.brief || '').toLowerCase(), sessionSearch.value.toLowerCase())
  )
})

const computedSessionGroups = computed(() => {
  const grouped = groupBy(filteredSessionList.value, groupByDate)
  const order = [t('qa.today'), t('qa.week'), t('qa.earlier'), t('qa.no_time')]
  return order
    .filter((key) => grouped[key]?.length)
    .map((key) => ({ key, list: grouped[key] }))
})

function toggleGroup(key: string) {
  sessionExpandMap.value[key] = !sessionExpandMap.value[key]
}

// 会话批量删除（与智能问数一致）
const sessionSelectedIds = ref<number[]>([])
const allVisibleSessionIds = computed<number[]>(() => {
  const ids: number[] = []
  computedSessionGroups.value.forEach((group: { list: ChatInfo[] }) => {
    group.list?.forEach((item: ChatInfo) => {
      if (item.id !== undefined) ids.push(item.id)
    })
  })
  return ids
})
const allSessionSelected = computed(
  () =>
    allVisibleSessionIds.value.length > 0 &&
    allVisibleSessionIds.value.every((id) => sessionSelectedIds.value.includes(id))
)
const hasSessionSelection = computed(() => sessionSelectedIds.value.length > 0)

function isSessionSelected(id?: number) {
  if (id === undefined) return false
  return sessionSelectedIds.value.includes(id)
}

function toggleSessionSelect(item: ChatInfo) {
  if (item.id === undefined) return
  if (isSessionSelected(item.id)) {
    sessionSelectedIds.value = sessionSelectedIds.value.filter((id) => id !== item.id)
  } else {
    sessionSelectedIds.value = [...sessionSelectedIds.value, item.id]
  }
}

function clearSessionSelection() {
  sessionSelectedIds.value = []
}

function toggleSessionSelectAll() {
  if (allSessionSelected.value) {
    clearSessionSelection()
    return
  }
  sessionSelectedIds.value = [...allVisibleSessionIds.value]
}

type ClearScope = 'before_today' | 'before_7_days' | 'all'

function getSessionIdsByScope(scope: ClearScope): number[] {
  const todayStart = dayjs(dayjs().format('YYYY-MM-DD') + ' 00:00:00').toDate()
  const weekStart = dayjs(dayjs().subtract(7, 'day').format('YYYY-MM-DD') + ' 00:00:00').toDate()
  const ids: number[] = []
  filteredSessionList.value.forEach((item: ChatInfo) => {
    if (item.id === undefined) return
    const time = getDate(item.create_time)
    if (!time) return
    if (scope === 'all') {
      ids.push(item.id)
      return
    }
    if (scope === 'before_today' && time < todayStart) {
      ids.push(item.id)
      return
    }
    if (scope === 'before_7_days' && time < weekStart) {
      ids.push(item.id)
    }
  })
  return ids
}

async function handleBulkDeleteSessions() {
  if (!sessionSelectedIds.value.length) return
  try {
    await ElMessageBox.confirm(
      t('qa.selected_chats_delete_confirm', { msg: sessionSelectedIds.value.length }),
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
  const ids = [...sessionSelectedIds.value]
  const sessionMap = new Map<number, ChatInfo>()
  sessionList.value.forEach((s) => {
    if (s.id !== undefined) sessionMap.set(s.id, s)
  })
  sessionLoading.value = true
  try {
    await Promise.all(
      ids.map((id) => {
        const s = sessionMap.get(id)
        return chatApi.deleteChat(id, s?.brief ?? '')
      })
    )
    ids.forEach((id) => {
      sessionList.value = sessionList.value.filter((s) => s.id !== id)
      if (currentSessionId.value === id) goNewAnalysis()
    })
    ElMessage.success(t('dashboard.delete_success'))
  } catch (err: any) {
    ElMessage.error(err?.message || '删除失败')
  } finally {
    sessionLoading.value = false
    clearSessionSelection()
  }
}

async function handleClearSessionsByScope(scope: ClearScope) {
  const ids = getSessionIdsByScope(scope)
  if (!ids.length) {
    ElMessage.info(t('workspace.historical_dialogue'))
    return
  }
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
  const sessionMap = new Map<number, ChatInfo>()
  sessionList.value.forEach((s) => {
    if (s.id !== undefined) sessionMap.set(s.id, s)
  })
  sessionLoading.value = true
  try {
    await Promise.all(
      ids.map((id) => {
        const s = sessionMap.get(id)
        return chatApi.deleteChat(id, s?.brief ?? '')
      })
    )
    ids.forEach((id) => {
      sessionList.value = sessionList.value.filter((s) => s.id !== id)
      if (currentSessionId.value === id) goNewAnalysis()
    })
    ElMessage.success(t('dashboard.delete_success'))
  } catch (err: any) {
    ElMessage.error(err?.message || '删除失败')
  } finally {
    sessionLoading.value = false
    clearSessionSelection()
  }
}

const filteredDatasourceList = computed(() => {
  if (!datasourceSearch.value.trim()) return datasourceList.value
  const q = datasourceSearch.value.toLowerCase()
  return datasourceList.value.filter((d) => d.name?.toLowerCase().includes(q))
})

function isDeepAnalysisRecord(r: any): boolean {
  if (!r?.analysis || typeof r.analysis !== 'string') return false
  const s = r.analysis.trim()
  if (!s.startsWith('{')) return false
  try {
    const data = JSON.parse(r.analysis)
    return typeof data === 'object' && (data.plan != null || data.report != null)
  } catch {
    return false
  }
}

const analysisCards = computed(() => sessionRecords.value.filter((r: any) => isDeepAnalysisRecord(r)))

const hasContent = computed(
  () => !!errorMsg.value || !!planHtml.value || !!reportHtml.value || processChunks.value.length > 0
)
const selectedDatasourceName = computed(() => {
  return datasourceList.value.find((item) => item.id === datasourceId.value)?.name || ''
})
const recommendedQuestions = ref<string[]>([])
const recommendLoading = ref(false)
const quickExamples = computed(() => recommendedQuestions.value)

/** 将 processChunks 转为展示块：合并 chart + chart-data，并解析图表配置供 ChartComponent 使用 */
const processBlocks = computed(() => {
  const chunks = processChunks.value
  const blocks: Array<{
    kind: 'text' | 'chart'
    content?: string
    reasoning_content?: string
    chartConfig?: string
    chartType?: string
    chartColumns?: Array<{ name: string; value: string }>
    chartX?: Array<{ name: string; value: string }>
    chartY?: Array<{ name: string; value: string }>
    chartSeries?: Array<{ name: string; value: string }>
    chartData?: Array<Record<string, unknown>>
  }> = []
  for (let i = 0; i < chunks.length; i++) {
    const step = chunks[i]
    if (step.type === 'data-finish') continue
    if (step.type === 'chart-data') {
      if (blocks.length && blocks[blocks.length - 1].kind === 'chart') {
        const raw = step.content
        const arr = typeof raw === 'string' ? (() => { try { return JSON.parse(raw) } catch { return raw } })() : raw
        const data = Array.isArray(arr) ? arr : (arr && typeof arr === 'object' && Array.isArray((arr as any).data) ? (arr as any).data : [])
        blocks[blocks.length - 1].chartData = data
      }
      continue
    }
    if (step.type === 'chart' && step.content) {
      try {
        const cfg = typeof step.content === 'string' ? JSON.parse(step.content) : step.content
        const axis = cfg?.axis || {}
        const x = axis.x ? [Array.isArray(axis.x) ? axis.x[0] : axis.x] : []
        const y = axis.y ? (Array.isArray(axis.y) ? axis.y : [axis.y]) : []
        const series = axis.series ? [axis.series] : []
        blocks.push({
          kind: 'chart',
          chartConfig: typeof step.content === 'string' ? step.content : JSON.stringify(step.content),
          chartType: cfg?.type || 'table',
          chartColumns: Array.isArray(cfg?.columns) ? cfg.columns : [],
          chartX: x,
          chartY: y,
          chartSeries: series,
          chartData: [],
        })
      } catch {
        blocks.push({ kind: 'text', content: step.content, reasoning_content: step.reasoning_content })
      }
      continue
    }
    blocks.push({
      kind: 'text',
      content: step.content,
      reasoning_content: step.reasoning_content,
    })
  }
  return blocks
})

function renderedContent(raw: string): string {
  if (!raw || typeof raw !== 'string') return ''
  try {
    return md.render(raw)
  } catch {
    return String(raw)
  }
}

const DEEP_ANALYSIS_SESSION_KEY = 'deep_analysis_current_session'
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
function persistCurrentSession() {
  if (currentSessionId.value != null) {
    sessionStorage.setItem(DEEP_ANALYSIS_SESSION_KEY, String(currentSessionId.value))
  } else {
    sessionStorage.removeItem(DEEP_ANALYSIS_SESSION_KEY)
  }
}

function hideSessionSideBar() {
  sessionSideBarShow.value = false
}
function showSessionSideBar() {
  sessionSideBarShow.value = true
}
function closeSessionPopover() {
  sessionPopoverVisible.value = false
}
function goNewAnalysis() {
  currentSessionId.value = undefined
  currentSessionDatasourceName.value = ''
  persistCurrentSession()
  errorMsg.value = ''
  planMarkdown.value = ''
  planHtml.value = ''
  reportMarkdown.value = ''
  reportHtml.value = ''
  processChunks.value = []
  planCollapse.value = []
  processCollapse.value = []
  reportCollapse.value = []
  currentStage.value = ''
  question.value = ''
  datasourceId.value = undefined
  openBindDsPopup()
}

function openBindDsPopup() {
  bindDsSelectedId.value = undefined
  datasourceSearch.value = ''
  bindDsPopupVisible.value = true
  loadDatasources()
}

function closeBindDsPopup() {
  bindDsPopupVisible.value = false
  bindDsSelectedId.value = undefined
}

function selectDsInBindPopup(dsId: number) {
  bindDsSelectedId.value = dsId
}

async function confirmBindDs() {
  if (bindDsSelectedId.value == null) return
  bindDsLoading.value = true
  try {
    await datasourceApi.check_by_id(bindDsSelectedId.value)
  } catch {
    bindDsLoading.value = false
    return
  }
  try {
    const chat = await deepAnalysisApi.startSession(bindDsSelectedId.value)
    sessionList.value.unshift(chat)
    currentSessionId.value = chat.id
    datasourceId.value = chat.datasource
    question.value = chat.brief || ''
    currentSessionDatasourceName.value = chat.datasource_name || ''
    persistCurrentSession()
    await loadSessions()
    closeBindDsPopup()
    if (chat.id != null) loadSessionDetail(chat.id)
    loadRecommendedQuestions(chat.datasource)
  } catch (e: any) {
    ElMessage.error(e?.message || String(e))
  } finally {
    bindDsLoading.value = false
  }
}

async function loadRecommendedQuestions(_dsId: number | undefined) {
  // 由于推荐问题较慢，这里直接禁用推荐逻辑，保持空列表
  recommendedQuestions.value = []
  recommendLoading.value = false
}

function applyRecordToDetail(record: any) {
  if (!record?.analysis) return
  try {
    const data = JSON.parse(record.analysis)
    planMarkdown.value = data.plan || ''
    planHtml.value = data.plan ? renderedContent(data.plan) : ''
    reportMarkdown.value = data.report || ''
    reportHtml.value = data.report ? renderedContent(data.report) : ''
    processChunks.value = Array.isArray(data.process) ? data.process : []
    selectedRecordConfig.value = data.config && typeof data.config === 'object' ? data.config : null
  } catch {
    planMarkdown.value = ''
    planHtml.value = ''
    reportMarkdown.value = ''
    reportHtml.value = ''
    processChunks.value = []
    selectedRecordConfig.value = null
  }
}

async function loadSessionDetail(chatId: number) {
  try {
    const res = await chatApi.get(chatId)
    const info = chatApi.toChatInfo(res)
    currentSessionDatasourceName.value = info?.datasource_name || ''
    const records = info?.records || []
    sessionRecords.value = records
    const withAnalysis = records.filter((r: any) => isDeepAnalysisRecord(r))
    const targetRecord =
      selectedRecordId.value != null && withAnalysis.some((r: any) => r.id === selectedRecordId.value)
        ? withAnalysis.find((r: any) => r.id === selectedRecordId.value)
        : withAnalysis.length
          ? withAnalysis[withAnalysis.length - 1]
          : null
    if (targetRecord) {
      if (selectedRecordId.value == null && targetRecord.id != null) selectedRecordId.value = targetRecord.id
      applyRecordToDetail(targetRecord)
    } else {
      planMarkdown.value = ''
      planHtml.value = ''
      reportMarkdown.value = ''
      reportHtml.value = ''
      processChunks.value = []
      selectedRecordConfig.value = null
    }
  } catch {
    planMarkdown.value = ''
    planHtml.value = ''
    reportMarkdown.value = ''
    reportHtml.value = ''
    processChunks.value = []
    sessionRecords.value = []
    selectedRecordConfig.value = null
  }
}

function selectSession(item: ChatInfo) {
  currentSessionId.value = item.id
  datasourceId.value = item.datasource
  question.value = item.brief || ''
  currentSessionDatasourceName.value = item.datasource_name || ''
  selectedRecordId.value = undefined
  persistCurrentSession()
  if (item.id != null) loadSessionDetail(item.id)
}

function selectCard(card: any) {
  if (card?.id == null) return
  selectedRecordId.value = card.id
  applyRecordToDetail(card)
}

function confirmDeleteCard(card: any) {
  if (card?.id == null || currentSessionId.value == null) return
  ElMessageBox.confirm(
    t('deep_analysis.delete_card_confirm'),
    t('common.proceed_with_caution'),
    {
      confirmButtonText: t('dashboard.delete'),
      cancelButtonText: t('common.cancel'),
      type: 'warning',
    }
  ).then(() => {
    chatApi.deleteRecord(card.id).then(() => {
      ElMessage.success(t('dashboard.delete_success'))
      const wasSelected = selectedRecordId.value === card.id
      if (wasSelected) selectedRecordId.value = undefined
      loadSessionDetail(currentSessionId.value!)
    }).catch((err: any) => {
      ElMessage.error(err?.message || t('common.error'))
    })
  }).catch(() => {})
}

function openRename(item: ChatInfo) {
  if (item.id == null) return
  renameForm.id = item.id
  renameForm.name = item.brief || ''
  renameDialogVisible.value = true
}

function submitRename() {
  renameFormRef.value?.validate((valid: boolean) => {
    if (!valid) return
    renameLoading.value = true
    chatApi
      .renameChat(renameForm.id, renameForm.name)
      .then((res) => {
        ElMessage.success(t('common.save_success'))
        const c = sessionList.value.find((x) => x.id === renameForm.id)
        if (c) c.brief = res
        if (currentSessionId.value === renameForm.id) question.value = renameForm.name
        renameDialogVisible.value = false
      })
      .catch((err: any) => {
        ElMessage.error(err?.message || 'Rename failed')
      })
      .finally(() => {
        renameLoading.value = false
      })
  })
}

function confirmDeleteSession(item: ChatInfo) {
  if (item.id == null) return
  ElMessageBox.confirm(t('common.sales_in_2024', { msg: item.brief || t('deep_analysis.report_title') }), {
    confirmButtonType: 'danger',
    tip: t('common.proceed_with_caution'),
    confirmButtonText: t('dashboard.delete'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
  }).then(() => {
    sessionLoading.value = true
    chatApi
      .deleteChat(item.id, item.brief ?? '')
      .then(() => {
        ElMessage.success(t('dashboard.delete_success'))
        sessionList.value = sessionList.value.filter((s) => s.id !== item.id)
        if (currentSessionId.value === item.id) goNewAnalysis()
      })
      .catch((err: any) => {
        ElMessage.error(err?.message || 'Delete failed')
      })
      .finally(() => {
        sessionLoading.value = false
      })
  })
}

async function startAnalysis() {
  if (!datasourceId.value || !question.value.trim()) return
  errorMsg.value = ''
  planMarkdown.value = ''
  planHtml.value = ''
  reportMarkdown.value = ''
  reportHtml.value = ''
  processChunks.value = []
  planCollapse.value = []
  processCollapse.value = []
  reportCollapse.value = []
  selectedRecordId.value = undefined
  selectedRecordConfig.value = null
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
        max_steps: maxSteps.value,
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
          if (data.type === 'start' && data.chat_id) {
            currentSessionId.value = data.chat_id
            persistCurrentSession()
            await loadSessions()
            continue
          }
          if (data.type === 'finish') {
            loading.value = false
            if (reportMarkdown.value) {
              reportHtml.value = renderedContent(reportMarkdown.value)
            }
            if (data.chat_id) {
              currentSessionId.value = data.chat_id
              persistCurrentSession()
              await loadSessions()
              await loadSessionDetail(data.chat_id)
              const cards = sessionRecords.value.filter((r: any) => isDeepAnalysisRecord(r))
              if (cards.length > 0) {
                const lastCard = cards[cards.length - 1]
                selectedRecordId.value = lastCard.id
                applyRecordToDetail(lastCard)
              }
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
          } else if ((data.type === 'process' || data.type === 'analysis-result' || data.type === 'chart' || data.type === 'chart-data' || data.type === 'data-finish') && (c !== undefined || r)) {
            processChunks.value.push({
              content: c,
              reasoning_content: r,
              type: data.type,
              chart: data.chart,
              data: data.data,
            })
          } else if (c || r) {
            processChunks.value.push({
              content: c,
              reasoning_content: r,
              type: data.type,
              chart: data.chart,
              data: data.data,
            })
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
  const blob = new Blob([reportMarkdown.value], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `深度分析报告_${dayjs().format('YYYYMMDD_HHmmss')}.md`
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

watch(datasourceId, (id) => {
  loadRecommendedQuestions(id)
}, { immediate: true })

onMounted(async () => {
  await loadDatasources()
  await loadSessions()
  const saved = sessionStorage.getItem(DEEP_ANALYSIS_SESSION_KEY)
  if (saved) {
    const id = Number(saved)
    const item = sessionList.value.find((s) => s.id === id)
    if (item) {
      selectSession(item)
    }
  }
})
</script>

<style scoped>
.deep-analysis-page {
  height: 100%;
  min-height: 0;
  background: #f5f6f7;
}
.da-layout {
  height: 100%;
  min-height: 0;
}

/* ========== 左侧会话历史（智能问数风格） ========== */
.da-session-aside.chat-container-left {
  --ed-aside-width: 280px;
  border-radius: 12px 0 0 12px;
  background: rgba(245, 246, 247, 1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
/* 收起后浮动按钮区（与智能问数一致） */
.hidden-sidebar-btn {
  z-index: 11;
  position: absolute;
  padding: 16px;
  top: 0;
  left: 0;
  display: flex;
  align-items: center;
  gap: 0;
}
.hidden-sidebar-btn .icon-btn {
  min-width: unset;
  width: 26px;
  height: 26px;
  font-size: 18px;
  --ed-button-text-color: rgba(31, 35, 41, 1);
  --ed-button-hover-text-color: var(--ed-button-text-color);
}
.hidden-sidebar-btn .icon-btn:hover {
  background: rgba(31, 35, 41, 0.1);
}
.da-popover-inner.chat-container-right-container {
  background: rgba(245, 246, 247, 1);
  padding: 0;
}
.da-popover-inner .chat-list-header {
  padding: 16px;
}
.da-popover-inner .chat-list-header.in-popover {
  --ed-header-height: auto;
}
.da-popover-inner .da-session-list-inner {
  padding: 0 16px 20px;
}
/* 与智能问数 ChatListContainer 一致的 header */
.da-aside-header.chat-list-header {
  padding: 16px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 16px;
}
.da-aside-header .title {
  height: 24px;
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  font-weight: 500;
}
.da-aside-header .icon-btn {
  min-width: unset;
  width: 26px;
  height: 26px;
  font-size: 18px;
}
.da-aside-header .icon-btn:hover {
  background: rgba(31, 35, 41, 0.1);
}
.da-aside-header .btn {
  width: 100%;
  height: 40px;
  font-size: 16px;
  font-weight: 500;
  --ed-button-text-color: var(--ed-color-primary, rgba(28, 186, 144, 1));
  --ed-button-bg-color: var(--ed-color-primary-1a, #1cba901a);
  --ed-button-border-color: var(--ed-color-primary-60, #a4e3d3);
  --ed-button-hover-bg-color: var(--ed-color-primary-80, #d2f1e9);
  --ed-button-hover-text-color: var(--ed-color-primary, rgba(28, 186, 144, 1));
  --ed-button-hover-border-color: var(--ed-color-primary, rgba(28, 186, 144, 1));
  --ed-button-active-bg-color: var(--ed-color-primary-60, #a4e3d3);
  --ed-button-active-border-color: var(--ed-color-primary, rgba(28, 186, 144, 1));
}
.da-aside-header .search {
  height: 32px;
  width: 100%;
}
.da-aside-header .search :deep(.el-input__wrapper) {
  background-color: #f5f6f7;
}
.da-empty-sessions {
  padding: 24px 16px;
  color: #646a73;
  font-size: 14px;
  text-align: center;
}
.da-session-list-wrap {
  flex: 1;
  min-height: 0;
}
.da-session-list-inner {
  padding: 0 16px 20px;
}
.da-session-bulk-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 8px;
  margin-top: 4px;
  margin-bottom: 8px;
  border-radius: 6px;
}
.da-session-bulk-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.da-session-bulk-selected {
  font-size: 12px;
  color: #646a73;
}
.da-session-bulk-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.da-session-bulk-clear-link {
  font-size: 12px;
  color: #646a73;
  cursor: pointer;
}
.da-session-bulk-clear-link:hover {
  color: var(--ed-color-primary, rgba(28, 186, 144, 1));
}
.da-session-group {
  margin-bottom: 16px;
}
.da-session-group-title {
  padding: 0 8px 6px;
  font-size: 12px;
  font-weight: 500;
  color: #646a73;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
}
.da-session-group-title .expand {
  transform: rotate(-90deg);
}
.da-session-item {
  height: 40px;
  padding: 0 8px;
  margin-bottom: 2px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  cursor: pointer;
  overflow: hidden;
}
.da-session-item:hover {
  background: rgba(31, 35, 41, 0.08);
}
.da-session-item.active {
  background: #fff;
  font-weight: 500;
}
.da-session-item-checkbox {
  margin-right: 8px;
  flex-shrink: 0;
}
.da-session-brief {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  line-height: 22px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.da-session-more {
  flex-shrink: 0;
  color: #646a73;
  display: none;
}
.da-session-item:hover .da-session-more {
  display: block;
}

/* ========== 中间：选表 + 新建分析（固定宽度，不留空白，把空间留给右侧） ========== */
.da-center-main {
  flex: 0 0 auto;
  width: 420px;
  max-width: 420px;
  padding: 0;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-right: 1px solid rgba(31, 35, 41, 0.08);
  border-radius: 0 12px 12px 0;
}
.da-center-main.hide-sidebar {
  border-radius: 12px;
}
.da-chat-layout {
  position: relative;
}
.da-center-inner {
  width: 100%;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
.da-datasource-section,
.da-composer-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.da-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.da-section-title {
  font-size: 15px;
  font-weight: 600;
  color: rgba(31, 35, 41, 1);
}
.da-ds-search {
  width: 100%;
}
.da-ds-search :deep(.el-input__wrapper) {
  border-radius: 8px;
  background: #f5f6f7;
}
.da-ds-list {
  max-height: 220px;
  border: 1px solid rgba(222, 224, 227, 1);
  border-radius: 12px;
  background: #fafbfc;
}
.da-ds-item {
  height: 40px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  border-radius: 6px;
  margin: 4px 8px;
  transition: background 0.15s;
}
.da-ds-item:hover {
  background: rgba(31, 35, 41, 0.06);
}
.da-ds-item.isActive {
  background: rgba(28, 186, 144, 0.12);
  color: var(--el-color-primary);
}
.da-ds-icon {
  flex-shrink: 0;
}
.da-ds-name {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.da-ds-empty {
  padding: 24px;
  text-align: center;
  font-size: 13px;
  color: #646a73;
}
.da-welcome-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 280px;
  padding: 40px 24px;
  text-align: center;
}
.da-welcome-desc {
  font-size: 14px;
  color: #646a73;
  margin-bottom: 24px;
  max-width: 360px;
  line-height: 1.6;
}
.da-welcome-btn {
  font-size: 15px;
}
.da-ds-readonly {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 40px;
  padding: 0 12px;
  border: 1px solid rgba(222, 224, 227, 1);
  border-radius: 12px;
  background: #fafbfc;
  color: rgba(31, 35, 41, 0.88);
  font-size: 14px;
}
.da-cards-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.da-cards-scroll {
  --el-scrollbar-opacity: 0.6;
}
.da-cards-scroll :deep(.el-scrollbar__wrap) {
  overflow-x: auto;
  overflow-y: hidden;
}
.da-cards-inner {
  display: flex;
  gap: 12px;
  padding: 4px 0;
  min-width: min-content;
}
.da-analysis-card {
  flex: 0 0 280px;
  min-width: 280px;
  padding: 12px 14px;
  border: 1px solid rgba(222, 224, 227, 1);
  border-radius: 12px;
  background: #fafbfc;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  position: relative;
}
.da-analysis-card:hover {
  background: #f5f6f7;
  border-color: rgba(28, 186, 144, 0.4);
}
.da-analysis-card.active {
  border-color: var(--el-color-primary);
  background: rgba(28, 186, 144, 0.06);
}
.da-card-delete {
  position: absolute;
  top: 8px;
  right: 8px;
  font-size: 14px;
  color: #646a73;
  opacity: 0.7;
}
.da-card-delete:hover {
  color: var(--el-color-danger);
  opacity: 1;
}
.da-card-question {
  font-size: 13px;
  color: rgba(31, 35, 41, 0.88);
  line-height: 1.4;
  padding-right: 20px;
  margin-bottom: 6px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.da-card-time {
  font-size: 12px;
  color: #646a73;
}
.da-config-block {
  margin-bottom: 12px;
  padding: 12px 14px;
  border: 1px solid rgba(222, 224, 227, 1);
  border-radius: 12px;
  background: #fafbfc;
}
.da-config-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}
.da-config-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  font-size: 13px;
}
.da-config-label {
  flex: 0 0 120px;
  color: #646a73;
}
.da-config-value {
  flex: 1;
  min-width: 0;
  color: rgba(31, 35, 41, 0.88);
  word-break: break-word;
}
.da-bind-ds-list {
  max-height: 320px;
  margin-top: 12px;
  border: 1px solid rgba(222, 224, 227, 1);
  border-radius: 12px;
  background: #fafbfc;
}
.da-bind-ds-list .da-ds-item {
  margin: 4px 8px;
}
.da-composer-card {
  border: 1px solid rgba(222, 224, 227, 1);
  border-radius: 16px;
  padding: 20px;
  background: #fafbfc;
}
.da-composer-top {
  margin-bottom: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
}
.composer-field {
  min-width: 0;
}
.composer-field label {
  display: block;
  font-size: 13px;
  color: #646a73;
  margin-bottom: 8px;
}
.max-rows-input,
.max-steps-input {
  width: 160px;
}
.field-hint {
  margin-top: 6px;
  font-size: 12px;
  color: #8f959e;
  display: block;
}
.question-field :deep(.el-textarea__inner) {
  font-family: inherit;
  padding: 14px 16px;
  min-height: 120px;
  border-radius: 12px;
  background: #fff;
  line-height: 1.7;
}
.da-example-block {
  margin-top: 16px;
}
.da-example-title {
  font-size: 12px;
  font-weight: 600;
  color: #646a73;
  margin-bottom: 10px;
}
.da-example-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.da-example-loading {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.da-example-chip {
  border: 1px solid #d9dcdf;
  background: #fff;
  color: rgba(31, 35, 41, 0.88);
  border-radius: 999px;
  padding: 8px 14px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}
.da-example-chip:hover {
  color: var(--el-color-primary);
  border-color: rgba(28, 186, 144, 0.35);
  background: rgba(28, 186, 144, 0.06);
}
.da-composer-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 16px;
}
.composer-hint {
  font-size: 12px;
  color: #8f959e;
}
.composer-actions {
  display: flex;
  gap: 8px;
}

/* ========== 右侧分析窗口（占满剩余空间） ========== */
.da-result-aside {
  flex: 1 1 0;
  min-width: 460px;
  display: flex;
  flex-direction: column;
  background: #fafbfc;
  border-left: 1px solid rgba(31, 35, 41, 0.08);
  overflow: hidden;
}
.da-result-header {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(31, 35, 41, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}
.da-result-title {
  font-size: 16px;
  font-weight: 600;
  color: rgba(31, 35, 41, 1);
}
.da-export-btn {
  flex-shrink: 0;
}
.da-result-body {
  flex: 1;
  min-height: 0;
  padding: 16px 20px;
}
.da-result-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 280px;
  color: #8f959e;
}
.da-result-empty-icon {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  background: rgba(31, 35, 41, 0.06);
  margin-bottom: 16px;
}
.da-result-empty-text {
  font-size: 14px;
  margin: 0;
}
.da-summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.da-summary-card {
  border: 1px solid rgba(222, 224, 227, 1);
  border-radius: 12px;
  padding: 14px 16px;
  background: #fff;
}
.summary-label {
  font-size: 12px;
  color: #646a73;
  margin-bottom: 6px;
}
.summary-value {
  font-size: 14px;
  font-weight: 600;
  color: rgba(31, 35, 41, 1);
  word-break: break-word;
}
.summary-value.running {
  color: var(--el-color-primary);
}
.error-block {
  margin-bottom: 16px;
}
.da-status-card {
  display: flex;
  align-items: center;
  gap: 16px;
  border: 1px solid rgba(222, 224, 227, 1);
  border-radius: 16px;
  padding: 20px;
  background: #fff;
  margin-bottom: 16px;
}
.da-status-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(28, 186, 144, 0.1);
  color: var(--el-color-primary);
  flex-shrink: 0;
}
.da-status-body {
  min-width: 0;
}
.da-status-title {
  font-size: 15px;
  font-weight: 600;
  color: rgba(31, 35, 41, 1);
}
.da-status-desc {
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.6;
  color: #646a73;
}
.da-result-chain-wrap {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.da-result-chain-enter-active,
.da-result-chain-move {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.da-result-chain-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.da-result-card.plan-block,
.da-result-card.report-block,
.da-result-card.process-block {
  margin-bottom: 0;
}
.plan-block,
.report-block,
.process-block {
  border: 1px solid rgba(222, 224, 227, 1);
  border-radius: 16px;
  padding: 20px;
  background: #fff;
  margin-bottom: 16px;
}
.plan-block {
  border-color: rgba(28, 186, 144, 0.2);
  background: linear-gradient(180deg, rgba(28, 186, 144, 0.06), #fff);
}
.da-report-body {
  line-height: 1.75;
}
.da-report-body :deep(h1) { font-size: 1.25rem; margin: 1em 0 0.5em; }
.da-report-body :deep(h2) { font-size: 1.1rem; margin: 0.9em 0 0.4em; }
.da-report-body :deep(h3) { font-size: 1rem; margin: 0.8em 0 0.4em; }
.da-report-body :deep(p) { margin: 0.5em 0; }
.da-report-body :deep(ul), .da-report-body :deep(ol) { margin: 0.5em 0; padding-left: 1.5em; }
.step-chart-wrap {
  margin-top: 12px;
  min-height: 200px;
  border-radius: 12px;
  background: rgba(224, 224, 226, 0.29);
  padding: 12px;
}
.card-head {
  margin-bottom: 14px;
}
.report-title {
  font-size: 16px;
  font-weight: 600;
  color: rgba(31, 35, 41, 1);
}
.report-body {
  font-size: 14px;
  line-height: 1.75;
  color: rgba(31, 35, 41, 0.92);
}
.report-body :deep(h2) {
  font-size: 15px;
  margin: 16px 0 8px;
  border-bottom: 1px solid rgba(222, 224, 227, 1);
  padding-bottom: 6px;
}
.report-body :deep(pre) {
  background: #f5f6f7;
  padding: 12px;
  border-radius: 10px;
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
.steps-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.step-item {
  padding: 12px 14px;
  border-radius: 12px;
  background: #f5f6f7;
  border: 1px solid rgba(222, 224, 227, 0.8);
}
.step-item .step-thinking {
  margin-bottom: 8px;
}
.thinking-title {
  font-size: 12px;
  color: #646a73;
}
.thinking-content {
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-word;
  color: #646a73;
}
.step-item .step-content :deep(pre) {
  background: #fff;
  padding: 10px;
  border-radius: 8px;
  overflow-x: auto;
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
  color: #646a73;
  font-size: 13px;
  padding: 12px 0;
  text-align: center;
}

@media (max-width: 1200px) {
  .da-result-aside {
    min-width: 400px;
  }
  .da-summary-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .da-layout {
    flex-direction: column;
  }
  .da-session-aside {
    width: 100% !important;
    max-height: 240px;
    border-right: none;
    border-bottom: 1px solid rgba(31, 35, 41, 0.1);
  }
  .da-center-main {
    padding: 16px;
  }
  .da-result-aside {
    width: 100% !important;
    min-width: 0;
    max-height: 50vh;
  }
}
</style>

<style>
.popover-card_deep_analysis.popover-card_deep_analysis {
  box-shadow: 0 4px 12px rgba(31, 35, 41, 0.1);
  border-radius: 8px;
  border: 1px solid #dee0e3;
  padding: 0;
  min-width: 120px;
}
.popover-card_deep_analysis .content .item {
  height: 40px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
  color: #1f2329;
}
.popover-card_deep_analysis .content .item:hover {
  background: rgba(31, 35, 41, 0.06);
}
</style>
