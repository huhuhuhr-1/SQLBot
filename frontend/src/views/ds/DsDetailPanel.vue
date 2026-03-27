<script lang="ts" setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { datasourceApi } from '@/api/datasource'
import { Edit } from '@element-plus/icons-vue'

const props = defineProps<{
  ds: { id?: number | string; name: string; type: string; description?: string; type_name?: string } | null
}>()
const emit = defineEmits<{
  (e: 'manage-tables'): void
  (e: 'edit'): void
  (e: 'copy'): void
  (e: 'recommendation'): void
  (e: 'delete'): void
  (e: 'go-to-analysis', id: number | string): void
}>()

const { t } = useI18n()
const activeSubTab = ref('preview')
const tableList = ref<any[]>([])
const currentTable = ref<any>(null)
const fieldList = ref<any[]>([])
const previewData = ref<{ data?: any[]; fields?: string[] }>({})
const loading = ref(false)
const descriptionEdit = ref('')
const descriptionEditing = ref(false)

const loadDetail = () => {
  if (!props.ds?.id) {
    tableList.value = []
    currentTable.value = null
    fieldList.value = []
    previewData.value = {}
    return
  }
  loading.value = true
  datasourceApi
    .tableList(Number(props.ds.id))
    .then((res: any) => {
      tableList.value = res || []
      const first = tableList.value[0]
      currentTable.value = first || null
      if (first) loadTableData(first)
    })
    .finally(() => {
      loading.value = false
    })
}

const loadTableData = (table: any) => {
  if (!props.ds?.id) return
  currentTable.value = table
  datasourceApi.fieldList(table.id).then((res: any) => {
    fieldList.value = res || []
    return datasourceApi.previewData(Number(props.ds!.id), { table, fields: fieldList.value })
  }).then((res: any) => {
    previewData.value = res || {}
  })
}

const goToAnalysis = () => {
  if (props.ds?.id != null) {
    emit('go-to-analysis', props.ds.id)
  }
}

const startEditDesc = () => {
  descriptionEdit.value = props.ds?.description ?? ''
  descriptionEditing.value = true
}

const saveDesc = () => {
  if (!props.ds?.id || descriptionEditing.value === false) return
  datasourceApi
    .update({ ...props.ds, id: Number(props.ds.id), description: descriptionEdit.value })
    .then(() => {
      descriptionEditing.value = false
      if (props.ds) (props.ds as any).description = descriptionEdit.value
    })
}

watch(
  () => props.ds?.id,
  (id) => {
    if (id) {
      descriptionEdit.value = props.ds?.description ?? ''
      descriptionEditing.value = false
      loadDetail()
    } else {
      tableList.value = []
      currentTable.value = null
      fieldList.value = []
      previewData.value = {}
    }
  },
  { immediate: true }
)
</script>

<template>
  <div v-if="!ds" class="ds-detail-empty">
    <p class="hint">{{ t('ds.select_one_hint') }}</p>
  </div>
  <div v-else class="ds-detail-panel">
    <div class="breadcrumb">
      <span>{{ t('ds.data_center') }}</span>
      <span class="sep">/</span>
      <span>{{ ds.name }}</span>
      <template v-if="currentTable">
        <span class="sep">/</span>
        <span>{{ currentTable.table_name }}</span>
      </template>
    </div>
    <div class="header-row">
      <h2 class="detail-title">
        <span>{{ currentTable ? currentTable.table_name : ds.name }}</span>
      </h2>
      <div class="header-actions">
        <el-button size="small" @click="emit('edit')">{{ t('datasource.edit') }}</el-button>
        <el-button size="small" @click="emit('copy')">{{ t('datasource.copy') }}</el-button>
        <el-button size="small" @click="emit('recommendation')">{{ t('datasource.recommended_problem_configuration') }}</el-button>
        <el-button size="small" type="danger" text @click="emit('delete')">{{ t('dashboard.delete') }}</el-button>
        <el-button size="small" @click="emit('manage-tables')">{{ t('ds.tables') }}</el-button>
        <el-button type="primary" size="small" @click="goToAnalysis">
          + {{ t('ds.go_to_analysis') }}
        </el-button>
      </div>
    </div>
    <div class="description-block">
      <span class="label">{{ t('ds.form.description') }}</span>
      <el-icon v-if="!descriptionEditing" class="edit-icon" @click="startEditDesc"><Edit /></el-icon>
      <div v-if="!descriptionEditing" class="desc-text">{{ ds.description || '-' }}</div>
      <div v-else class="desc-edit">
        <el-input v-model="descriptionEdit" type="textarea" :rows="2" />
        <el-button size="small" type="primary" @click="saveDesc">{{ t('common.confirm') }}</el-button>
        <el-button size="small" @click="descriptionEditing = false">{{ t('common.cancel') }}</el-button>
      </div>
    </div>
    <el-tabs v-model="activeSubTab" class="detail-tabs">
      <el-tab-pane :label="t('ds.column_info')" name="columns">
        <div v-loading="loading" class="tab-content">
          <el-table :data="fieldList" size="small" max-height="400">
            <el-table-column prop="field_name" :label="t('ds.field.name')" min-width="120" />
            <el-table-column prop="field_type" :label="t('datasource.field_type')" width="120" />
            <el-table-column prop="custom_comment" :label="t('ds.field.comment')" min-width="140" />
          </el-table>
          <p v-if="!loading && !fieldList.length" class="no-data">{{ t('ds.no_data_tip') }}</p>
        </div>
      </el-tab-pane>
      <el-tab-pane :label="t('ds.table_preview')" name="preview">
        <div v-loading="loading" class="tab-content">
          <el-table :data="previewData.data" size="small" max-height="400">
            <el-table-column
              v-for="(col, idx) in (previewData.fields || [])"
              :key="idx"
              :prop="col"
              :label="col"
              min-width="120"
            />
          </el-table>
          <p v-if="!loading && !(previewData.data && previewData.data.length)" class="no-data">{{ t('ds.no_data_tip') }}</p>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style lang="less" scoped>
.ds-detail-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-text-color-secondary);
  .hint {
    font-size: 14px;
  }
}

.ds-detail-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 16px 24px;
  overflow: auto;

  .breadcrumb {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    margin-bottom: 12px;
    .sep {
      margin: 0 6px;
    }
  }

  .header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    .detail-title {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
    }
    .header-actions {
      display: flex;
      gap: 8px;
    }
  }

  .description-block {
    margin-bottom: 16px;
    position: relative;
    .label {
      font-size: 14px;
      color: var(--el-text-color-regular);
      margin-right: 8px;
    }
    .edit-icon {
      font-size: 14px;
      cursor: pointer;
      color: var(--el-text-color-secondary);
      &:hover {
        color: var(--el-color-primary);
      }
    }
    .desc-text {
      margin-top: 4px;
      font-size: 14px;
      color: var(--el-text-color-secondary);
    }
    .desc-edit {
      margin-top: 8px;
      display: flex;
      align-items: flex-start;
      gap: 8px;
    }
  }

  .detail-tabs {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    :deep(.el-tabs__content) {
      flex: 1;
      overflow: auto;
    }
  }

  .tab-content {
    min-height: 200px;
    .no-data {
      color: var(--el-text-color-secondary);
      font-size: 14px;
      padding: 24px;
    }
  }
}
</style>
