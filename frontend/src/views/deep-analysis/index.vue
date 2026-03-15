<template>
  <div class="deep-analysis-page">
    <div class="page-header">
      <p class="router-title">{{ t('menu.deep_analysis') }}</p>
      <p class="page-desc">{{ t('deep_analysis.desc') }}</p>
    </div>

    <div class="config-row">
      <div class="form-item">
        <label>{{ t('deep_analysis.datasource') }}</label>
        <el-select
          v-model="datasourceId"
          :placeholder="t('deep_analysis.select_datasource')"
          filterable
          class="ds-select"
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

    <div class="process-block">
      <div v-if="steps.length > 0" class="process-title">
        {{ t('deep_analysis.process') }}
      </div>
      <div class="steps-container">
        <div v-for="(step, idx) in steps" :key="idx" class="step-item">
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
      <div v-if="loading && steps.length === 0" class="loading-tip">
        <el-icon class="is-loading"><Loading /></el-icon>
        {{ t('deep_analysis.waiting') }}
      </div>
      <div v-else-if="!loading && steps.length === 0 && !errorMsg" class="empty-tip">
        {{ t('deep_analysis.empty_tip') }}
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus-secondary'
import { Loading } from '@element-plus/icons-vue'
import { request } from '@/utils/request'
import { datasourceApi } from '@/api/datasource'
import md from '@/utils/markdown.ts'
import 'github-markdown-css/github-markdown-light.css'

const { t } = useI18n()

const datasourceList = ref<any[]>([])
const datasourceId = ref<number | undefined>()
const question = ref('')
const loading = ref(false)
const errorMsg = ref('')
const steps = ref<Array<{ content?: string; reasoning_content?: string; type?: string }>>([])
let abortController: AbortController | null = null
let stopFlag = false

function renderedContent(raw: string): string {
  if (!raw || typeof raw !== 'string') return ''
  try {
    return md.render(raw)
  } catch {
    return String(raw)
  }
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

async function startAnalysis() {
  if (!datasourceId.value || !question.value.trim()) return
  errorMsg.value = ''
  steps.value = []
  loading.value = true
  stopFlag = false
  abortController = new AbortController()

  try {
    const response = await request.fetchStream(
      '/openapi/deep-analysis',
      {
        datasource_id: datasourceId.value,
        question: question.value.trim(),
        no_reasoning: false,
        max_data_length: 1000,
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
            break
          }
          const c = typeof data.content === 'string' ? data.content : ''
          const r = typeof data.reasoning_content === 'string' ? data.reasoning_content : ''
          if (c || r) {
            steps.value.push({ content: c, reasoning_content: r, type: data.type })
          }
        } catch (e) {
          console.warn('Parse SSE chunk failed', e)
        }
      }
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

onMounted(() => loadDatasources())
</script>

<style scoped>
.deep-analysis-page {
  padding: 16px 24px;
  max-width: 900px;
  margin: 0 auto;
}
.page-header {
  margin-bottom: 20px;
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
.process-block {
  margin-top: 24px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 16px;
  min-height: 120px;
  background: var(--el-fill-color-blank);
}
.process-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
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
.loading-tip,
.empty-tip {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  padding: 24px 0;
  text-align: center;
}
.loading-tip .el-icon {
  margin-right: 6px;
  vertical-align: middle;
}
</style>
