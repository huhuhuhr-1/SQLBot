<script lang="ts" setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import icon_add_outlined from '@/assets/svg/icon_add_outlined.svg'
import IconOpeEdit from '@/assets/svg/icon_edit_outlined.svg'
import IconOpeDelete from '@/assets/svg/icon_delete.svg'
import icon_searchOutline_outlined from '@/assets/svg/icon_search-outline_outlined.svg'
import EmptyBackground from '@/views/dashboard/common/EmptyBackground.vue'
import { metricApi, type MetricSuggestResult } from '@/api/metric'
import { datasourceApi } from '@/api/datasource'
import { formatTimestamp } from '@/utils/date'
const { t } = useI18n()

interface MetricRow {
  id: number
  code: string
  name: string
  metric_kind: string
  enabled: boolean
  create_time?: string
  specific_ds?: boolean
  description?: string
  aliases?: string[]
  datasource_ids?: number[]
  measure_sql?: string
  base_metric_id?: number
  modifiers?: Record<string, unknown>
  expansion_hint?: string
  expression?: string
  components?: { slot_code: string; child_metric_id: number }[]
}

const searchLoading = ref(false)
const keywords = ref('')
/** 是否与术语页一致：用于空状态区分「暂无数据」与「无筛选结果」 */
const filterActive = ref(false)
const kindFilter = ref<string | undefined>(undefined)
const list = ref<MetricRow[]>([])
const pageInfo = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0,
})

const drawerVisible = ref(false)
const saveLoading = ref(false)
const allDsList = ref<any[]>([])
const metricOptions = ref<
  { id: number; code: string; name: string; metric_kind: string; datasource_ids?: number[] }[]
>([])
const filterDsId = ref<number | undefined>(undefined)

const defaultForm = () => ({
  id: null as number | null,
  code: '',
  name: '',
  description: '',
  aliases: [] as string[],
  metric_kind: 'atomic',
  enabled: true,
  datasource_id: undefined as number | undefined,
  measure_sql: '',
  base_metric_id: undefined as number | undefined,
  modifiers_json: '',
  expansion_hint: '',
  expression: '',
  components: [] as { slot_code: string; child_metric_id: number | undefined }[],
})

const form = ref(defaultForm())

/** 新建：简单模式仅原子指标；编辑：始终完整表单 */
const formMode = ref<'simple' | 'full'>('simple')
const smartDesc = ref('')
const smartLoading = ref(false)
const smartSaveLoading = ref(false)

/** 表字段助手：当前选中的唯一数据源 */
const primarySchemaDsId = computed(() => form.value.datasource_id ?? null)
const schemaCollapse = ref<string[]>([])
/** 智能生成后固定在折叠外的回显（表/字段） */
const schemaSuggestEcho = ref<{ table?: string; field?: string } | null>(null)
const schemaProgrammatic = ref(false)
const pickSchemaTable = ref('')
const pickSchemaField = ref('')
const pickAgg = ref<'SUM' | 'COUNT' | 'COUNT_STAR' | 'AVG' | 'MAX' | 'MIN' | 'NONE'>('SUM')
const schemaTablesLoading = ref(false)
const schemaFieldsLoading = ref(false)
const schemaTableOptions = ref<{ label: string; value: string }[]>([])
const schemaFieldOptions = ref<{ label: string; value: string }[]>([])

const mapTableRows = (rows: any[]) =>
  (rows || []).map((r: any) => {
    const tn = r.table_name || ''
    const tip = r.custom_comment || r.table_comment || ''
    return { label: tip ? `${tip} (${tn})` : tn, value: tn }
  })

const loadSchemaTablesForce = async () => {
  const id = primarySchemaDsId.value
  if (!id) return
  schemaTablesLoading.value = true
  schemaTableOptions.value = []
  try {
    const rows = await datasourceApi.tableList(id)
    schemaTableOptions.value = mapTableRows(rows)
  } finally {
    schemaTablesLoading.value = false
  }
}

const loadSchemaTables = () => {
  const id = primarySchemaDsId.value
  if (!id || schemaTableOptions.value.length) return
  loadSchemaTablesForce()
}

const loadSchemaFieldsFor = async (id: number, tname: string) => {
  schemaFieldsLoading.value = true
  try {
    const rows = await datasourceApi.getFields(id, tname)
    schemaFieldOptions.value = (rows || []).map((r: any) => {
      const fn = r.fieldName || r.field_name || ''
      const fc = r.fieldComment || r.field_comment || ''
      return { label: fc ? `${fc} (${fn})` : fn || '—', value: fn }
    })
  } finally {
    schemaFieldsLoading.value = false
  }
}

watch(primarySchemaDsId, () => {
  pickSchemaTable.value = ''
  pickSchemaField.value = ''
  schemaTableOptions.value = []
  schemaFieldOptions.value = []
  schemaSuggestEcho.value = null
})

const pickAggLabel = computed(() => {
  const k = pickAgg.value
  if (k === 'SUM') return t('metric.agg_sum')
  if (k === 'COUNT') return t('metric.agg_count_col')
  if (k === 'COUNT_STAR') return t('metric.agg_count_star')
  if (k === 'AVG') return t('metric.agg_avg')
  if (k === 'MAX') return t('metric.agg_max')
  if (k === 'MIN') return t('metric.agg_min')
  return t('metric.agg_none')
})

const resolveTableOption = (name: string) => {
  const x = name.trim()
  if (!x) return null
  return (
    schemaTableOptions.value.find((o) => o.value === x) ||
    schemaTableOptions.value.find((o) => String(o.value).toLowerCase() === x.toLowerCase()) ||
    null
  )
}

const resolveFieldOption = (name: string) => {
  const x = name.trim()
  if (!x) return null
  return (
    schemaFieldOptions.value.find((o) => o.value === x) ||
    schemaFieldOptions.value.find((o) => String(o.value).toLowerCase() === x.toLowerCase()) ||
    null
  )
}

watch(pickSchemaTable, (tname) => {
  if (schemaProgrammatic.value) return
  pickSchemaField.value = ''
  schemaFieldOptions.value = []
  const id = primarySchemaDsId.value
  if (!id || !tname) return
  loadSchemaFieldsFor(id, tname)
})

const identSql = (s: string) => {
  const x = String(s).replace(/`/g, '')
  if (/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(x)) return x
  return `\`${x}\``
}

const insertSchemaFragment = () => {
  const tb = pickSchemaTable.value
  const fd = pickSchemaField.value
  if (!tb) {
    ElMessage.warning(t('metric.schema_need_table'))
    return
  }
  if (pickAgg.value !== 'COUNT_STAR' && !fd) {
    ElMessage.warning(t('metric.schema_need_field'))
    return
  }
  const refExpr = pickAgg.value === 'COUNT_STAR' ? '' : `${identSql(tb)}.${identSql(fd)}`
  let frag = ''
  switch (pickAgg.value) {
    case 'SUM':
      frag = `SUM(${refExpr})`
      break
    case 'COUNT':
      frag = `COUNT(${refExpr})`
      break
    case 'COUNT_STAR':
      frag = 'COUNT(*)'
      break
    case 'AVG':
      frag = `AVG(${refExpr})`
      break
    case 'MAX':
      frag = `MAX(${refExpr})`
      break
    case 'MIN':
      frag = `MIN(${refExpr})`
      break
    default:
      frag = refExpr
  }
  const cur = form.value.measure_sql?.trim() || ''
  form.value.measure_sql = cur ? `${cur}\n${frag}` : frag
  ElMessage.success(t('metric.schema_insert_ok'))
}

const loadOptions = (datasourceIds?: number[]) => {
  metricApi.options(datasourceIds).then((res: any) => {
    metricOptions.value = res?.data || []
  })
}

const loadPage = () => {
  searchLoading.value = true
  const params: Record<string, string> = {}
  if (keywords.value.trim()) params.name = keywords.value.trim()
  if (kindFilter.value) params.metric_kind = kindFilter.value
  if (filterDsId.value != null) params.datasource_id = String(filterDsId.value)
  metricApi
    .page(pageInfo.currentPage, pageInfo.pageSize, params)
    .then((res: any) => {
      list.value = res.data || []
      pageInfo.total = res.total_count || 0
    })
    .finally(() => {
      searchLoading.value = false
    })
}

const search = () => {
  filterActive.value = !!(
    keywords.value.trim() ||
    kindFilter.value ||
    filterDsId.value != null
  )
  pageInfo.currentPage = 1
  loadPage()
}

const handleSizeChange = (val: number) => {
  pageInfo.currentPage = 1
  pageInfo.pageSize = val
  loadPage()
}

const handleCurrentChange = (val: number) => {
  pageInfo.currentPage = val
  loadPage()
}

const openCreate = () => {
  formMode.value = 'simple'
  smartDesc.value = ''
  schemaSuggestEcho.value = null
  form.value = defaultForm()
  form.value.components = [{ slot_code: 'M1', child_metric_id: undefined }]
  drawerVisible.value = true
}

const openEdit = (row: MetricRow) => {
  formMode.value = 'full'
  schemaSuggestEcho.value = null
  let modifiers_json = ''
  if (row.modifiers && typeof row.modifiers === 'object') {
    try {
      modifiers_json = JSON.stringify(row.modifiers, null, 2)
    } catch {
      modifiers_json = ''
    }
  }
  form.value = {
    id: row.id,
    code: row.code,
    name: row.name,
    description: row.description || '',
    aliases: row.aliases || [],
    metric_kind: row.metric_kind,
    enabled: row.enabled !== false,
    datasource_id: row.datasource_ids?.[0],
    measure_sql: row.measure_sql || '',
    base_metric_id: row.base_metric_id,
    modifiers_json,
    expansion_hint: row.expansion_hint || '',
    expression: row.expression || '',
    components:
      (row.components?.length ?? 0) > 0
        ? (row.components ?? []).map((c) => ({
            slot_code: c.slot_code,
            child_metric_id: c.child_metric_id,
          }))
        : [{ slot_code: 'M1', child_metric_id: undefined }],
  }
  drawerVisible.value = true
}

const addComponentRow = () => {
  form.value.components.push({ slot_code: `M${form.value.components.length + 1}`, child_metric_id: undefined })
}

const removeComponentRow = (i: number) => {
  form.value.components.splice(i, 1)
}

const parseModifiers = (): Record<string, unknown> | null => {
  const s = form.value.modifiers_json?.trim()
  if (!s) return null
  try {
    return JSON.parse(s) as Record<string, unknown>
  } catch {
    ElMessage.error(t('metric.modifiers_json_invalid'))
    throw new Error('modifiers')
  }
}

const applySuggestPayload = (data: MetricSuggestResult) => {
  form.value.code = data.code
  form.value.name = data.name
  form.value.measure_sql = data.measure_sql
  form.value.aliases = Array.isArray(data.aliases) ? [...data.aliases] : []
  if (data.description) form.value.description = data.description
  form.value.expansion_hint = data.expansion_hint?.trim() ?? ''
}

const inferPickAgg = (sql: string) => {
  const u = sql.trim().toUpperCase()
  if (/\bCOUNT\s*\(\s*\*\s*\)/.test(u)) {
    pickAgg.value = 'COUNT_STAR'
    return
  }
  if (/\bCOUNT\s*\(/.test(u)) {
    pickAgg.value = 'COUNT'
    return
  }
  if (/\bSUM\s*\(/.test(u)) pickAgg.value = 'SUM'
  else if (/\bAVG\s*\(/.test(u)) pickAgg.value = 'AVG'
  else if (/\bMAX\s*\(/.test(u)) pickAgg.value = 'MAX'
  else if (/\bMIN\s*\(/.test(u)) pickAgg.value = 'MIN'
  else pickAgg.value = 'NONE'
}

const inferEchoFieldFromSql = (sql: string, tableName?: string) => {
  const refs = [...sql.matchAll(/([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)/g)]
  if (!refs.length) return ''
  const fields = refs
    .filter((m) => !tableName || m[1].toLowerCase() === tableName.toLowerCase())
    .map((m) => m[2])
  if (!fields.length) return ''
  const uniq = [...new Set(fields)]
  return uniq.join(' - ')
}

const syncSchemaPicksFromSuggest = async (res: MetricSuggestResult) => {
  const tbRaw = res.used_table?.trim()
  const fdRaw = res.used_field?.trim()
  const id = primarySchemaDsId.value
  if (!id) return

  schemaCollapse.value = ['schema']
  await nextTick()

  if (!tbRaw) {
    const sqlField = inferEchoFieldFromSql(res.measure_sql)
    schemaSuggestEcho.value = {
      table: undefined,
      field: fdRaw || sqlField || undefined,
    }
    return
  }

  await loadSchemaTablesForce()
  const tableOpt = resolveTableOption(tbRaw)
  if (!tableOpt) {
    const sqlField = inferEchoFieldFromSql(res.measure_sql, tbRaw)
    schemaSuggestEcho.value = { table: tbRaw, field: fdRaw || sqlField || undefined }
    return
  }

  const canonicalTable = String(tableOpt.value)
  schemaProgrammatic.value = true
  pickSchemaField.value = ''
  pickSchemaTable.value = canonicalTable
  try {
    await loadSchemaFieldsFor(id, canonicalTable)
    await nextTick()
    let canonicalField = ''
    if (fdRaw) {
      const fo = resolveFieldOption(fdRaw)
      canonicalField = fo ? String(fo.value) : ''
      pickSchemaField.value = canonicalField
    }
    const sqlField = inferEchoFieldFromSql(res.measure_sql, canonicalTable)
    schemaSuggestEcho.value = {
      table: canonicalTable,
      field: canonicalField || fdRaw || sqlField || undefined,
    }
    await nextTick()
  } finally {
    schemaProgrammatic.value = false
  }
}

const runSmartSuggest = async () => {
  const d = smartDesc.value.trim()
  if (!d) {
    ElMessage.warning(t('metric.smart_need_desc'))
    return
  }
  if (form.value.datasource_id == null) {
    ElMessage.warning(t('metric.smart_need_ds_first'))
    return
  }
  smartLoading.value = true
  try {
    const res = await metricApi.suggest(d, form.value.datasource_id)
    applySuggestPayload(res)
    inferPickAgg(res.measure_sql)
    await syncSchemaPicksFromSuggest(res)
    if (!schemaSuggestEcho.value) {
      const sqlField = inferEchoFieldFromSql(res.measure_sql, res.used_table?.trim())
      schemaSuggestEcho.value = {
        table: res.used_table?.trim() || undefined,
        field: res.used_field?.trim() || sqlField || undefined,
      }
    }
    ElMessage.success(t('metric.smart_ok'))
  } catch (e: unknown) {
    const ax = e as { response?: { data?: { detail?: string } } }
    const detail = ax?.response?.data?.detail
    ElMessage.error(typeof detail === 'string' ? detail : t('metric.smart_fail'))
  } finally {
    smartLoading.value = false
  }
}

const runSmartSuggestAndSave = async () => {
  const d = smartDesc.value.trim()
  if (!d) {
    ElMessage.warning(t('metric.smart_need_desc'))
    return
  }
  if (form.value.datasource_id == null) {
    ElMessage.warning(t('metric.smart_need_ds_first'))
    return
  }
  smartSaveLoading.value = true
  try {
    const res = await metricApi.suggest(d, form.value.datasource_id)
    applySuggestPayload(res)
    inferPickAgg(res.measure_sql)
    await syncSchemaPicksFromSuggest(res)
    if (!schemaSuggestEcho.value) {
      const sqlField = inferEchoFieldFromSql(res.measure_sql, res.used_table?.trim())
      schemaSuggestEcho.value = {
        table: res.used_table?.trim() || undefined,
        field: res.used_field?.trim() || sqlField || undefined,
      }
    }
    const body = buildSaveBody()
    if (!body) return
    await metricApi.save(body)
    ElMessage.success(t('metric.smart_save_ok'))
    drawerVisible.value = false
    loadPage()
  } catch (e: unknown) {
    const ax = e as { response?: { data?: { detail?: string } } }
    const detail = ax?.response?.data?.detail
    ElMessage.error(typeof detail === 'string' ? detail : t('metric.smart_save_fail'))
  } finally {
    smartSaveLoading.value = false
  }
}

const applyLocalTemplate = () => {
  const d = smartDesc.value.trim()
  if (!d) {
    ElMessage.warning(t('metric.smart_need_desc'))
    return
  }
  form.value.name = d.length > 64 ? d.slice(0, 64) : d
  form.value.code = `m_${Date.now().toString(36)}`
  form.value.measure_sql = '/* 请改为真实表名与列名 */\nCOUNT(*)'
  form.value.description = d
  ElMessage.success(t('metric.smart_local_ok'))
}

const buildSaveBody = (): Record<string, unknown> | null => {
  if (!form.value.id && formMode.value === 'simple') {
    form.value.metric_kind = 'atomic'
  }
  if (!form.value.code?.trim() || !form.value.name?.trim()) {
    ElMessage.warning(t('metric.code') + ' / ' + t('metric.name'))
    return null
  }
  if (form.value.datasource_id == null) {
    ElMessage.warning(t('metric.datasource_required'))
    return null
  }
  if (form.value.metric_kind === 'atomic' && !form.value.measure_sql?.trim()) {
    ElMessage.warning(t('metric.measure_sql_required'))
    return null
  }
  if (form.value.metric_kind === 'derived' && !form.value.base_metric_id) {
    ElMessage.warning(t('metric.base_required'))
    return null
  }
  if (form.value.metric_kind === 'composite') {
    if (!form.value.expression?.trim()) {
      ElMessage.warning(t('metric.expression_required'))
      return null
    }
    const comps = form.value.components.filter((c) => c.slot_code?.trim() && c.child_metric_id)
    if (!comps.length) {
      ElMessage.warning(t('metric.components_required'))
      return null
    }
  }

  let modifiers: Record<string, unknown> | null = null
  if (form.value.metric_kind === 'derived') {
    try {
      modifiers = parseModifiers()
    } catch {
      return null
    }
  }

  return {
    id: form.value.id,
    code: form.value.code.trim(),
    name: form.value.name.trim(),
    description: form.value.description || null,
    aliases: form.value.aliases.filter(Boolean),
    metric_kind: form.value.metric_kind,
    enabled: form.value.enabled,
    specific_ds: true,
    datasource_ids: [form.value.datasource_id],
    measure_sql: form.value.metric_kind === 'atomic' ? form.value.measure_sql : null,
    base_metric_id: form.value.metric_kind === 'derived' ? form.value.base_metric_id : null,
    modifiers: form.value.metric_kind === 'derived' ? modifiers : null,
    expansion_hint:
      form.value.metric_kind === 'atomic' || form.value.metric_kind === 'derived'
        ? form.value.expansion_hint?.trim() || null
        : null,
    expression: form.value.metric_kind === 'composite' ? form.value.expression : null,
    components:
      form.value.metric_kind === 'composite'
        ? form.value.components
            .filter((c) => c.slot_code?.trim() && c.child_metric_id)
            .map((c) => ({ slot_code: c.slot_code.trim(), child_metric_id: c.child_metric_id! }))
        : [],
  }
}

const save = () => {
  const body = buildSaveBody()
  if (!body) return

  saveLoading.value = true
  metricApi
    .save(body)
    .then(() => {
      ElMessage.success(t('common.save_success'))
      drawerVisible.value = false
      loadPage()
    })
    .finally(() => {
      saveLoading.value = false
    })
}

const remove = (row: MetricRow) => {
  ElMessageBox.confirm(t('metric.delete_confirm', { name: row.name }), {
    confirmButtonType: 'primary',
    confirmButtonText: t('common.delete'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
  }).then(() => {
    metricApi.delete([row.id]).then(() => {
      ElMessage.success(t('common.delete_success'))
      loadPage()
    })
  })
}

const toggleEnable = (row: MetricRow, enabled: boolean) => {
  metricApi.enable(row.id, enabled).then(() => {
    ElMessage.success(t('common.save_success'))
    loadPage()
  })
}

const kindLabel = (k: string) => {
  if (k === 'atomic') return t('metric.kind_atomic')
  if (k === 'derived') return t('metric.kind_derived')
  if (k === 'composite') return t('metric.kind_composite')
  return k
}

const baseMetricChoices = () => metricOptions.value.filter((m) => m.id !== form.value.id)

const childMetricChoices = (excludeId: number | null) => {
  return metricOptions.value.filter((m) => m.id !== excludeId)
}

const applyDerivedGuide = () => {
  form.value.metric_kind = 'derived'
  const base = metricOptions.value.find((m) => m.metric_kind === 'atomic') || baseMetricChoices()[0]
  form.value.base_metric_id = base?.id
  form.value.modifiers_json = '{"time_grain":"day"}'
  form.value.expansion_hint =
    '按自然日统计；生成 SQL 时需按日期分组或筛选。measure_sql 保持聚合片段，不在其中写 GROUP BY。'
}

const applyCompositeGuide = () => {
  form.value.metric_kind = 'composite'
  const choices = childMetricChoices(form.value.id)
  const c1 = choices[0]
  const c2 = choices[1]
  form.value.components = [
    { slot_code: 'M1', child_metric_id: c1?.id },
    { slot_code: 'M2', child_metric_id: c2?.id },
  ]
  form.value.expression = '{{M1}} / NULLIF({{M2}}, 0)'
}

const dsNames = (ids?: number[]) => {
  if (!ids?.length) return '—'
  const names = ids
    .map((id) => allDsList.value.find((d) => d.id === id)?.name)
    .filter(Boolean)
  return names.length ? names.join(', ') : ids.join(', ')
}

watch(
  () => form.value.datasource_id,
  () => {
    if (form.value.datasource_id != null) loadOptions([form.value.datasource_id])
    else metricOptions.value = []
  }
)

onMounted(() => {
  datasourceApi.list().then((res) => {
    allDsList.value = res || []
  })
  loadPage()
})
</script>

<template>
  <div v-loading="searchLoading" class="metric">
    <div class="tool-left">
      <span class="page-title">{{ t('metric.title') }}</span>
      <div class="tool-row">
        <el-input
          v-model="keywords"
          style="width: 240px; margin-right: 12px"
          clearable
          :placeholder="t('metric.search_placeholder')"
          @keydown.enter.exact.prevent="search"
        >
          <template #prefix>
            <el-icon>
              <icon_searchOutline_outlined />
            </el-icon>
          </template>
        </el-input>
        <el-select
          v-model="kindFilter"
          clearable
          style="width: 160px"
          :placeholder="t('metric.kind_filter')"
          @change="search"
        >
          <el-option :label="t('metric.kind_atomic')" value="atomic" />
          <el-option :label="t('metric.kind_derived')" value="derived" />
          <el-option :label="t('metric.kind_composite')" value="composite" />
        </el-select>
        <el-select
          v-model="filterDsId"
          clearable
          filterable
          style="width: 200px"
          :placeholder="t('metric.filter_by_datasource')"
          @change="search"
        >
          <el-option v-for="d in allDsList" :key="d.id" :label="d.name" :value="d.id" />
        </el-select>
        <el-button class="no-margin" type="primary" @click="openCreate">
          <template #icon>
            <icon_add_outlined />
          </template>
          {{ t('metric.create') }}
        </el-button>
      </div>
    </div>

    <el-alert class="metric-intro" type="info" :closable="false" show-icon>
      <template #title>{{ t('metric.intro_title') }}</template>
      <ol class="metric-intro-list">
        <li>{{ t('metric.intro_step1') }}</li>
        <li>{{ t('metric.intro_step2') }}</li>
        <li>{{ t('metric.intro_step3') }}</li>
      </ol>
    </el-alert>

    <div v-if="!searchLoading" class="table-content">
      <div class="preview-or-schema">
        <el-table :data="list" style="width: 100%">
          <el-table-column prop="code" :label="t('metric.code')" min-width="120" />
          <el-table-column prop="name" :label="t('metric.name')" min-width="140" />
          <el-table-column :label="t('metric.kind')" width="100">
            <template #default="scope">
              {{ kindLabel(scope.row.metric_kind) }}
            </template>
          </el-table-column>
          <el-table-column :label="t('metric.datasources')" min-width="200">
            <template #default="scope">
              <div class="field-comment_d">
                <span :title="dsNames(scope.row.datasource_ids)" class="notes-in_table">{{
                  dsNames(scope.row.datasource_ids)
                }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column :label="t('ds.status')" width="100">
            <template #default="scope">
              <div style="display: flex; align-items: center" @click.stop>
                <el-switch
                  :model-value="scope.row.enabled"
                  size="small"
                  @change="(v: boolean) => toggleEnable(scope.row, v)"
                />
              </div>
            </template>
          </el-table-column>
          <el-table-column
            prop="create_time"
            sortable
            :label="t('dashboard.create_time')"
            width="240"
          >
            <template #default="scope">
              <span>{{ formatTimestamp(scope.row.create_time, 'YYYY-MM-DD HH:mm:ss') }}</span>
            </template>
          </el-table-column>
          <el-table-column fixed="right" width="80" :label="t('ds.actions')">
            <template #default="scope">
              <div class="field-comment">
                <el-tooltip
                  :offset="14"
                  effect="dark"
                  :content="t('datasource.edit')"
                  placement="top"
                >
                  <el-icon class="action-btn" size="16" @click.stop="openEdit(scope.row)">
                    <IconOpeEdit />
                  </el-icon>
                </el-tooltip>
                <el-tooltip
                  :offset="14"
                  effect="dark"
                  :content="t('dashboard.delete')"
                  placement="top"
                >
                  <el-icon class="action-btn" size="16" @click.stop="remove(scope.row)">
                    <IconOpeDelete />
                  </el-icon>
                </el-tooltip>
              </div>
            </template>
          </el-table-column>
          <template #empty>
            <EmptyBackground
              v-if="!filterActive && !list.length"
              :description="t('metric.empty')"
              img-type="noneWhite"
            />
            <EmptyBackground
              v-if="filterActive && !list.length"
              :description="t('datasource.relevant_content_found')"
              img-type="tree"
            />
          </template>
        </el-table>
      </div>
    </div>

    <div v-if="list.length" class="pagination-container">
      <el-pagination
        v-model:current-page="pageInfo.currentPage"
        v-model:page-size="pageInfo.pageSize"
        :page-sizes="[10, 20, 30]"
        :background="true"
        layout="total, sizes, prev, pager, next, jumper"
        :total="pageInfo.total"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <el-drawer
      v-model="drawerVisible"
      :title="form.id ? t('metric.edit') : t('metric.create')"
      destroy-on-close
      size="600px"
      modal-class="metric-add_drawer"
    >
      <el-form label-position="top" class="form-content_error" @submit.prevent>
        <el-form-item :label="t('metric.datasource_one')" required>
          <el-select
            v-model="form.datasource_id"
            filterable
            clearable
            class="w100"
            :placeholder="t('metric.datasource_one_placeholder')"
          >
            <el-option v-for="d in allDsList" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
          <div class="form-hint">{{ t('metric.datasource_one_hint') }}</div>
        </el-form-item>
        <template v-if="!form.id">
          <el-form-item :label="t('metric.mode_label')">
            <el-radio-group v-model="formMode">
              <el-radio-button value="simple">{{ t('metric.mode_simple') }}</el-radio-button>
              <el-radio-button value="full">{{ t('metric.mode_full') }}</el-radio-button>
            </el-radio-group>
            <div class="form-hint">{{ t('metric.mode_hint') }}</div>
          </el-form-item>
          <el-form-item v-if="formMode === 'simple'" :label="t('metric.smart_title')">
            <el-input
              v-model="smartDesc"
              type="textarea"
              :rows="3"
              :placeholder="t('metric.smart_placeholder')"
            />
            <div class="smart-actions">
              <el-button type="primary" plain :loading="smartLoading" @click="runSmartSuggest">
                {{ t('metric.smart_ai') }}
              </el-button>
              <el-button type="primary" :loading="smartSaveLoading" @click="runSmartSuggestAndSave">
                {{ t('metric.smart_ai_save') }}
              </el-button>
              <el-button @click="applyLocalTemplate">{{ t('metric.smart_local') }}</el-button>
            </div>
            <div class="form-hint">{{ t('metric.smart_hint') }}</div>
          </el-form-item>
        </template>
        <el-form-item :label="t('metric.code')" required>
          <el-input v-model="form.code" maxlength="128" :disabled="!!form.id" />
        </el-form-item>
        <el-form-item :label="t('metric.name')" required>
          <el-input v-model="form.name" maxlength="255" />
        </el-form-item>
        <el-form-item v-if="!!form.id || formMode === 'full'" :label="t('metric.kind')" required>
          <el-select v-model="form.metric_kind" :disabled="!!form.id" class="w100">
            <el-option :label="t('metric.kind_atomic')" value="atomic" />
            <el-option :label="t('metric.kind_derived')" value="derived" />
            <el-option :label="t('metric.kind_composite')" value="composite" />
          </el-select>
          <div v-if="!form.id && formMode === 'full'" class="form-hint">{{ t('metric.kind_hint_full') }}</div>
        </el-form-item>
        <el-alert
          v-if="!form.id && formMode === 'full'"
          class="advanced-guide-alert"
          type="info"
          :closable="false"
          show-icon
        >
          <template #title>{{ t('metric.advanced_guide_title') }}</template>
          <div class="advanced-guide-body">{{ t('metric.advanced_guide_desc') }}</div>
          <div class="advanced-guide-actions">
            <el-button plain @click="applyDerivedGuide">{{ t('metric.advanced_quick_derived') }}</el-button>
            <el-button plain @click="applyCompositeGuide">{{ t('metric.advanced_quick_composite') }}</el-button>
          </div>
        </el-alert>
        <el-form-item :label="t('professional.synonyms')">
          <el-select v-model="form.aliases" multiple filterable allow-create default-first-option class="w100" />
        </el-form-item>
        <el-form-item :label="t('dictionary.description')">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>

        <template v-if="form.metric_kind === 'atomic'">
          <el-alert
            v-if="schemaSuggestEcho && primarySchemaDsId"
            class="schema-echo-alert"
            type="success"
            :closable="false"
            show-icon
          >
            <template #title>{{ t('metric.schema_echo_title') }}</template>
            <div class="schema-echo-lines">
              <div>
                <span class="schema-echo-k">{{ t('metric.schema_echo_table') }}</span>
                {{ schemaSuggestEcho.table || '—' }}
              </div>
              <div>
                <span class="schema-echo-k">{{ t('metric.schema_echo_field') }}</span>
                {{ schemaSuggestEcho.field || '—' }}
              </div>
              <div>
                <span class="schema-echo-k">{{ t('metric.schema_echo_agg') }}</span>
                {{ pickAggLabel }}
              </div>
              <div v-if="!schemaSuggestEcho.table && !schemaSuggestEcho.field" class="form-hint no-margin">
                {{ t('metric.schema_echo_hint_only_sql') }}
              </div>
            </div>
          </el-alert>
          <el-collapse v-if="primarySchemaDsId" v-model="schemaCollapse" class="schema-helper-collapse">
            <el-collapse-item name="schema" :title="t('metric.schema_helper_title')">
              <p class="form-hint no-margin">{{ t('metric.schema_helper_hint') }}</p>
              <div class="schema-helper-row">
                <el-select
                  :key="'tbl-' + String(primarySchemaDsId) + '-' + schemaTableOptions.length"
                  v-model="pickSchemaTable"
                  filterable
                  clearable
                  class="schema-select"
                  :placeholder="t('metric.schema_table_ph')"
                  :loading="schemaTablesLoading"
                  @visible-change="(open: boolean) => open && loadSchemaTables()"
                >
                  <el-option
                    v-for="opt in schemaTableOptions"
                    :key="opt.value"
                    :label="opt.label"
                    :value="opt.value"
                  />
                </el-select>
                <el-select
                  :key="'fld-' + pickSchemaTable + '-' + schemaFieldOptions.length"
                  v-model="pickSchemaField"
                  filterable
                  clearable
                  class="schema-select"
                  :placeholder="t('metric.schema_field_ph')"
                  :disabled="!pickSchemaTable"
                  :loading="schemaFieldsLoading"
                >
                  <el-option
                    v-for="opt in schemaFieldOptions"
                    :key="opt.value"
                    :label="opt.label"
                    :value="opt.value"
                  />
                </el-select>
              </div>
              <div class="schema-helper-row">
                <el-select v-model="pickAgg" class="schema-agg">
                  <el-option :label="t('metric.agg_sum')" value="SUM" />
                  <el-option :label="t('metric.agg_count_col')" value="COUNT" />
                  <el-option :label="t('metric.agg_count_star')" value="COUNT_STAR" />
                  <el-option :label="t('metric.agg_avg')" value="AVG" />
                  <el-option :label="t('metric.agg_max')" value="MAX" />
                  <el-option :label="t('metric.agg_min')" value="MIN" />
                  <el-option :label="t('metric.agg_none')" value="NONE" />
                </el-select>
                <el-button type="primary" plain @click="insertSchemaFragment">
                  {{ t('metric.schema_insert') }}
                </el-button>
              </div>
            </el-collapse-item>
          </el-collapse>
          <el-form-item :label="t('metric.measure_sql')" required>
            <el-input v-model="form.measure_sql" type="textarea" :rows="5" :placeholder="t('metric.measure_sql_ph')" />
            <div class="form-hint">{{ t('metric.measure_sql_beginner') }}</div>
          </el-form-item>
          <el-form-item :label="t('metric.time_grain_hint')">
            <el-input
              v-model="form.expansion_hint"
              type="textarea"
              :rows="3"
              :placeholder="t('metric.time_grain_hint_ph')"
            />
          </el-form-item>
        </template>

        <template v-else-if="form.metric_kind === 'derived'">
          <el-form-item :label="t('metric.base_metric')" required>
            <el-select v-model="form.base_metric_id" filterable clearable class="w100">
              <el-option
                v-for="m in baseMetricChoices()"
                :key="m.id"
                :label="`${m.code} — ${m.name}`"
                :value="m.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('metric.modifiers_json')">
            <el-input v-model="form.modifiers_json" type="textarea" :rows="4" :placeholder="t('metric.modifiers_ph')" />
          </el-form-item>
          <el-form-item :label="t('metric.expansion_hint')">
            <el-input v-model="form.expansion_hint" type="textarea" :rows="3" />
          </el-form-item>
        </template>

        <template v-else-if="form.metric_kind === 'composite'">
          <el-form-item :label="t('metric.expression')" required>
            <el-input
              v-model="form.expression"
              type="textarea"
              :rows="3"
              :placeholder="t('metric.expression_ph')"
            />
          </el-form-item>
          <div class="components-head">
            <span>{{ t('metric.components') }}</span>
            <el-button text type="primary" @click="addComponentRow">{{ t('metric.add_slot') }}</el-button>
          </div>
          <div v-for="(c, i) in form.components" :key="i" class="component-row">
            <el-input v-model="c.slot_code" :placeholder="t('metric.slot_code')" class="slot-input" />
            <el-select v-model="c.child_metric_id" filterable clearable class="child-select">
              <el-option
                v-for="m in childMetricChoices(form.id)"
                :key="m.id"
                :label="`${m.code} — ${m.name}`"
                :value="m.id"
              />
            </el-select>
            <el-button text type="danger" @click="removeComponentRow(i)">×</el-button>
          </div>
        </template>

        <el-form-item :label="t('dictionary.enabled')">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div v-loading="saveLoading" class="dialog-footer">
          <el-button @click="drawerVisible = false">{{ t('common.cancel') }}</el-button>
          <el-button type="primary" :loading="saveLoading" @click="save">{{ t('common.save') }}</el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<style lang="less" scoped>
.no-margin {
  margin: 0;
}

.metric-intro {
  margin-bottom: 12px;
}

.metric-intro-list {
  margin: 4px 0 0;
  padding-left: 1.2em;
  line-height: 1.55;
  font-size: 13px;
}

.smart-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.schema-echo-alert {
  margin-bottom: 12px;
}

.schema-echo-lines {
  font-size: 13px;
  line-height: 1.6;
}

.schema-echo-k {
  color: var(--el-text-color-secondary);
  margin-right: 6px;
}

.schema-helper-collapse {
  margin-bottom: 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  overflow: hidden;
}

.schema-helper-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
  align-items: center;
}

.schema-select {
  flex: 1;
  min-width: 140px;
}

.schema-agg {
  width: 160px;
}

.metric {
  height: 100%;
  position: relative;

  .tool-left {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;

    .page-title {
      font-weight: 500;
      font-size: 20px;
      line-height: 28px;
    }

    .tool-row {
      display: flex;
      align-items: center;
      flex-direction: row;
      flex-wrap: wrap;
      gap: 8px;
    }
  }

  .pagination-container {
    display: flex;
    justify-content: end;
    align-items: center;
    margin-top: 16px;
  }

  .table-content {
    max-height: calc(100% - 104px);
    overflow-y: auto;

    .preview-or-schema {
      .field-comment_d {
        display: flex;
        align-items: center;
        min-height: 24px;
      }

      .notes-in_table {
        max-width: 100%;
        display: -webkit-box;
        max-height: 66px;
        -webkit-box-orient: vertical;
        -webkit-line-clamp: 3;
        overflow: hidden;
        text-overflow: ellipsis;
        word-break: break-word;
      }

      .field-comment {
        height: 24px;

        .action-btn {
          position: relative;
          cursor: pointer;
          margin-top: 4px;
          color: #646a73;

          &::after {
            content: '';
            background-color: #1f23291a;
            position: absolute;
            border-radius: 6px;
            width: 24px;
            height: 24px;
            transform: translate(-50%, -50%);
            top: 50%;
            left: 50%;
            display: none;
          }

          &:hover::after {
            display: block;
          }
        }

        .action-btn + .action-btn {
          margin-left: 12px;
        }
      }
    }
  }
}

.form-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 6px;
  line-height: 1.4;
}

.w100 {
  width: 100%;
}

.components-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.component-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.advanced-guide-alert {
  margin-bottom: 12px;
}

.advanced-guide-body {
  line-height: 1.5;
}

.advanced-guide-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.slot-input {
  width: 120px;
}

.child-select {
  flex: 1;
}
</style>

<style lang="less">
.metric-add_drawer {
  .ed-form-item--label-top .ed-form-item__label {
    margin-bottom: 4px;
  }

  .ed-form-item__label {
    color: #646a73;
  }
}
</style>
