<script lang="ts" setup>
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import icon_add_outlined from '@/assets/svg/icon_add_outlined.svg'
import IconOpeEdit from '@/assets/svg/icon_edit_outlined.svg'
import IconOpeDelete from '@/assets/svg/icon_delete.svg'
import icon_searchOutline_outlined from '@/assets/svg/icon_search-outline_outlined.svg'
import EmptyBackground from '@/views/dashboard/common/EmptyBackground.vue'
import { dictionaryApi } from '@/api/dictionary'
import { datasourceApi } from '@/api/datasource'
import { formatTimestamp } from '@/utils/date'

const { t } = useI18n()
const activeTab = ref('dict')
const searchLoading = ref(false)
const keywords = ref('')
const dictList = ref<any[]>([])
const dictPage = reactive({ currentPage: 1, pageSize: 10, total: 0 })
const bindingList = ref<any[]>([])
const bindingPage = reactive({ currentPage: 1, pageSize: 10, total: 0 })
const bindingFilterDs = ref<number | undefined>(undefined)

const dictDrawer = ref(false)
const dictSaving = ref(false)
const dictForm = ref({
  id: null as number | null,
  name: '',
  code: '',
  description: '',
  enabled: true,
  items: [] as { item_code: string; item_name: string; sort: number; enabled: boolean }[],
})

const bindingDialog = ref(false)
const bindingSaving = ref(false)
const dictOptions = ref<{ id: number; name: string; code: string }[]>([])
const dsOptions = ref<any[]>([])
const tableOptions = ref<{ label: string; value: string }[]>([])
const columnOptions = ref<{ label: string; value: string }[]>([])
const bindingForm = ref({
  id: null as number | null,
  dict_id: undefined as number | undefined,
  datasource_id: undefined as number | undefined,
  table_name: '',
  column_name: '',
  enabled: true,
})

const loadDictPage = () => {
  searchLoading.value = true
  const params: Record<string, string> = {}
  if (keywords.value.trim()) params.keyword = keywords.value.trim()
  dictionaryApi
    .page(dictPage.currentPage, dictPage.pageSize, params)
    .then((res: any) => {
      dictList.value = res.data || []
      dictPage.total = res.total_count || 0
    })
    .finally(() => {
      searchLoading.value = false
    })
}

const loadBindingPage = () => {
  searchLoading.value = true
  const params: Record<string, unknown> = {}
  if (bindingFilterDs.value) params.datasource_id = bindingFilterDs.value
  dictionaryApi
    .bindingPage(bindingPage.currentPage, bindingPage.pageSize, params)
    .then((res: any) => {
      bindingList.value = res.data || []
      bindingPage.total = res.total_count || 0
    })
    .finally(() => {
      searchLoading.value = false
    })
}

const loadDictOptions = () => {
  dictionaryApi.options().then((res: any) => {
    dictOptions.value = res || []
  })
}

const openCreateDict = () => {
  dictForm.value = {
    id: null,
    name: '',
    code: '',
    description: '',
    enabled: true,
    items: [{ item_code: '', item_name: '', sort: 0, enabled: true }],
  }
  dictDrawer.value = true
}

const openEditDict = (row: any) => {
  dictionaryApi.detail(row.id).then((res: any) => {
    dictForm.value = {
      id: res.id,
      name: res.name,
      code: res.code,
      description: res.description || '',
      enabled: res.enabled !== false,
      items:
        (res.items || []).length > 0
          ? res.items.map((x: any, i: number) => ({
              item_code: x.item_code,
              item_name: x.item_name,
              sort: x.sort ?? i,
              enabled: x.enabled !== false,
            }))
          : [{ item_code: '', item_name: '', sort: 0, enabled: true }],
    }
    dictDrawer.value = true
  })
}

const addItemRow = () => {
  dictForm.value.items.push({
    item_code: '',
    item_name: '',
    sort: dictForm.value.items.length,
    enabled: true,
  })
}

const removeItemRow = (index: number) => {
  dictForm.value.items.splice(index, 1)
}

const saveDict = () => {
  if (!dictForm.value.name?.trim() || !dictForm.value.code?.trim()) {
    ElMessage.warning(t('dictionary.name') + ' / ' + t('dictionary.code'))
    return
  }
  const items = dictForm.value.items.filter((x) => x.item_code?.trim())
  dictSaving.value = true
  dictionaryApi
    .save({
      id: dictForm.value.id,
      name: dictForm.value.name.trim(),
      code: dictForm.value.code.trim(),
      description: dictForm.value.description || null,
      enabled: dictForm.value.enabled,
      items: items.map((x, i) => ({
        item_code: x.item_code.trim(),
        item_name: (x.item_name || x.item_code).trim(),
        sort: x.sort ?? i,
        enabled: x.enabled,
      })),
    })
    .then(() => {
      ElMessage.success(t('common.save_success'))
      dictDrawer.value = false
      loadDictPage()
      loadDictOptions()
    })
    .finally(() => {
      dictSaving.value = false
    })
}

const deleteDictRow = (row: any) => {
  ElMessageBox.confirm(t('dictionary.delete_dict_confirm', { msg: row.name }), {
    confirmButtonType: 'danger',
    confirmButtonText: t('dashboard.delete'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
  }).then(() => {
    dictionaryApi.delete([row.id]).then(() => {
      ElMessage.success(t('dashboard.delete_success'))
      loadDictPage()
      loadDictOptions()
    })
  })
}

const onDictEnableChange = (row: any, val: boolean) => {
  dictionaryApi.enable(row.id, val).then(() => {
    ElMessage.success(t('common.save_success'))
    loadDictPage()
    loadDictOptions()
  })
}

const loadTablesForBinding = (dsId: number) => {
  tableOptions.value = []
  columnOptions.value = []
  bindingForm.value.table_name = ''
  bindingForm.value.column_name = ''
  if (!dsId) return
  datasourceApi.getTables(dsId).then((res: any) => {
    tableOptions.value = (res || []).map((t: any) => ({
      label: t.tableName + (t.tableComment ? ` (${t.tableComment})` : ''),
      value: t.tableName,
    }))
  })
}

const loadColumnsForBinding = (dsId: number, table: string) => {
  columnOptions.value = []
  bindingForm.value.column_name = ''
  if (!dsId || !table) return
  datasourceApi.getFields(dsId, table).then((res: any) => {
    columnOptions.value = (res || []).map((c: any) => ({
      label: c.fieldName + (c.fieldType ? ` : ${c.fieldType}` : ''),
      value: c.fieldName,
    }))
  })
}

const openCreateBinding = () => {
  bindingForm.value = {
    id: null,
    dict_id: undefined,
    datasource_id: undefined,
    table_name: '',
    column_name: '',
    enabled: true,
  }
  tableOptions.value = []
  columnOptions.value = []
  bindingDialog.value = true
}

const openEditBinding = (row: any) => {
  bindingForm.value = {
    id: row.id,
    dict_id: row.dict_id,
    datasource_id: row.datasource_id,
    table_name: row.table_name,
    column_name: row.column_name,
    enabled: row.enabled !== false,
  }
  if (row.datasource_id) {
    loadTablesForBinding(row.datasource_id)
    loadColumnsForBinding(row.datasource_id, row.table_name)
  }
  bindingDialog.value = true
}

const saveBinding = () => {
  if (
    !bindingForm.value.dict_id ||
    !bindingForm.value.datasource_id ||
    !bindingForm.value.table_name?.trim() ||
    !bindingForm.value.column_name?.trim()
  ) {
    ElMessage.warning(t('common.require'))
    return
  }
  bindingSaving.value = true
  dictionaryApi
    .saveBinding({
      id: bindingForm.value.id,
      dict_id: bindingForm.value.dict_id,
      datasource_id: bindingForm.value.datasource_id,
      table_name: bindingForm.value.table_name.trim(),
      column_name: bindingForm.value.column_name.trim(),
      enabled: bindingForm.value.enabled,
    })
    .then(() => {
      ElMessage.success(t('common.save_success'))
      bindingDialog.value = false
      loadBindingPage()
    })
    .finally(() => {
      bindingSaving.value = false
    })
}

const deleteBindingRow = (row: any) => {
  ElMessageBox.confirm(t('dictionary.delete_binding_confirm'), {
    confirmButtonType: 'danger',
    confirmButtonText: t('dashboard.delete'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
  }).then(() => {
    dictionaryApi.deleteBinding([row.id]).then(() => {
      ElMessage.success(t('dashboard.delete_success'))
      loadBindingPage()
    })
  })
}

onMounted(() => {
  datasourceApi.list().then((res: any) => {
    dsOptions.value = res || []
  })
  loadDictOptions()
  loadDictPage()
  loadBindingPage()
})
</script>

<template>
  <div class="dictionary-page">
    <span class="page-title">{{ t('dictionary.title') }}</span>
    <el-tabs v-model="activeTab" class="dict-tabs" @tab-change="(n: string) => (n === 'dict' ? loadDictPage() : loadBindingPage())">
      <el-tab-pane :label="t('dictionary.dict_tab')" name="dict">
        <div class="toolbar">
          <el-input
            v-model="keywords"
            clearable
            :placeholder="t('dictionary.search')"
            class="search-input"
            @keyup.enter="loadDictPage"
          >
            <template #prefix>
              <icon_searchOutline_outlined class="svg-icon" />
            </template>
          </el-input>
          <el-button type="primary" @click="loadDictPage">
            {{ t('common.search') }}
          </el-button>
          <el-button type="primary" @click="openCreateDict">
            <template #icon>
              <icon_add_outlined class="svg-icon" />
            </template>
            {{ t('dictionary.create') }}
          </el-button>
        </div>
        <div v-loading="searchLoading" class="table-wrap">
          <el-table v-if="dictList.length" :data="dictList" style="width: 100%">
            <el-table-column prop="name" :label="t('dictionary.name')" min-width="140" />
            <el-table-column prop="code" :label="t('dictionary.code')" min-width="120" />
            <el-table-column prop="description" :label="t('dictionary.description')" min-width="180" show-overflow-tooltip />
            <el-table-column prop="item_count" :label="t('dictionary.item_count')" width="90" />
            <el-table-column prop="enabled" :label="t('dictionary.enabled')" width="100">
              <template #default="{ row }">
                <el-switch :model-value="row.enabled" @change="(v: boolean) => onDictEnableChange(row, v)" />
              </template>
            </el-table-column>
            <el-table-column prop="create_time" :label="t('common.start_time')" width="170">
              <template #default="{ row }">
                {{ formatTimestamp(row.create_time) }}
              </template>
            </el-table-column>
            <el-table-column fixed="right" :label="t('ds.actions')" width="140">
              <template #default="{ row }">
                <el-button text @click="openEditDict(row)">
                  <IconOpeEdit class="svg-icon" />
                </el-button>
                <el-button text type="danger" @click="deleteDictRow(row)">
                  <IconOpeDelete class="svg-icon" />
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <EmptyBackground v-else :description="t('professional.no_term')" />
        </div>
        <div v-if="dictPage.total > dictPage.pageSize" class="pager">
          <el-pagination
            v-model:current-page="dictPage.currentPage"
            v-model:page-size="dictPage.pageSize"
            layout="total, prev, pager, next"
            :total="dictPage.total"
            @current-change="loadDictPage"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane :label="t('dictionary.binding_tab')" name="binding">
        <div class="toolbar">
          <el-select
            v-model="bindingFilterDs"
            clearable
            filterable
            :placeholder="t('dictionary.datasource')"
            style="width: 240px"
            @change="
              () => {
                bindingPage.currentPage = 1
                loadBindingPage()
              }
            "
          >
            <el-option v-for="d in dsOptions" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
          <el-button type="primary" @click="openCreateBinding">
            <template #icon>
              <icon_add_outlined class="svg-icon" />
            </template>
            {{ t('dictionary.add_binding') }}
          </el-button>
        </div>
        <div v-loading="searchLoading" class="table-wrap">
          <el-table v-if="bindingList.length" :data="bindingList" style="width: 100%">
            <el-table-column prop="dict_name" :label="t('dictionary.name')" min-width="120" />
            <el-table-column prop="datasource_name" :label="t('dictionary.datasource')" min-width="140" />
            <el-table-column prop="table_name" :label="t('dictionary.table')" width="160" />
            <el-table-column prop="column_name" :label="t('dictionary.column')" width="140" />
            <el-table-column prop="enabled" :label="t('dictionary.enabled')" width="100">
              <template #default="{ row }">
                <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? 'Y' : 'N' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column fixed="right" :label="t('ds.actions')" width="120">
              <template #default="{ row }">
                <el-button text @click="openEditBinding(row)">
                  <IconOpeEdit class="svg-icon" />
                </el-button>
                <el-button text type="danger" @click="deleteBindingRow(row)">
                  <IconOpeDelete class="svg-icon" />
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <EmptyBackground v-else :description="t('professional.no_term')" />
        </div>
        <div v-if="bindingPage.total > bindingPage.pageSize" class="pager">
          <el-pagination
            v-model:current-page="bindingPage.currentPage"
            v-model:page-size="bindingPage.pageSize"
            layout="total, prev, pager, next"
            :total="bindingPage.total"
            @current-change="loadBindingPage"
          />
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-drawer v-model="dictDrawer" size="640px" :title="dictForm.id ? t('dictionary.edit_dict') : t('dictionary.create')">
      <el-form label-position="top">
        <el-form-item :label="t('dictionary.name')" required>
          <el-input v-model="dictForm.name" />
        </el-form-item>
        <el-form-item :label="t('dictionary.code')" required>
          <el-input v-model="dictForm.code" :disabled="!!dictForm.id" />
        </el-form-item>
        <el-form-item :label="t('dictionary.description')">
          <el-input v-model="dictForm.description" type="textarea" rows="2" />
        </el-form-item>
        <el-form-item :label="t('dictionary.enabled')">
          <el-switch v-model="dictForm.enabled" />
        </el-form-item>
        <div class="items-head">
          <span>{{ t('dictionary.items') }}</span>
          <el-button type="primary" link @click="addItemRow">{{ t('dictionary.add_item') }}</el-button>
        </div>
        <el-table :data="dictForm.items" border size="small">
          <el-table-column :label="t('dictionary.item_code')" min-width="120">
            <template #default="{ row }">
              <el-input v-model="row.item_code" />
            </template>
          </el-table-column>
          <el-table-column :label="t('dictionary.item_name')" min-width="120">
            <template #default="{ row }">
              <el-input v-model="row.item_name" />
            </template>
          </el-table-column>
          <el-table-column :label="t('dictionary.sort')" width="90">
            <template #default="{ row }">
              <el-input-number v-model="row.sort" :controls="false" style="width: 100%" />
            </template>
          </el-table-column>
          <el-table-column width="70" align="center">
            <template #default="{ $index }">
              <el-button type="danger" link @click="removeItemRow($index)">×</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-form>
      <template #footer>
        <el-button @click="dictDrawer = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="dictSaving" @click="saveDict">{{ t('common.confirm2') }}</el-button>
      </template>
    </el-drawer>

    <el-dialog v-model="bindingDialog" :title="bindingForm.id ? t('dictionary.edit_binding') : t('dictionary.add_binding')" width="520px">
      <el-form label-position="top">
        <el-form-item :label="t('dictionary.select_dict')" required>
          <el-select v-model="bindingForm.dict_id" filterable style="width: 100%">
            <el-option v-for="o in dictOptions" :key="o.id" :label="`${o.name} (${o.code})`" :value="o.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('dictionary.datasource')" required>
          <el-select
            v-model="bindingForm.datasource_id"
            filterable
            style="width: 100%"
            :disabled="!!bindingForm.id"
            @change="(v: number) => loadTablesForBinding(v)"
          >
            <el-option v-for="d in dsOptions" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('dictionary.table')" required>
          <el-select
            v-model="bindingForm.table_name"
            filterable
            allow-create
            default-first-option
            style="width: 100%"
            :disabled="!bindingForm.datasource_id || !!bindingForm.id"
            @change="(v: string) => bindingForm.datasource_id && loadColumnsForBinding(bindingForm.datasource_id!, v)"
          >
            <el-option v-for="t in tableOptions" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('dictionary.column')" required>
          <el-select
            v-model="bindingForm.column_name"
            filterable
            allow-create
            default-first-option
            style="width: 100%"
            :disabled="!bindingForm.table_name || !!bindingForm.id"
          >
            <el-option v-for="c in columnOptions" :key="c.value" :label="c.label" :value="c.value" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('dictionary.enabled')">
          <el-switch v-model="bindingForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="bindingDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="bindingSaving" @click="saveBinding">{{ t('common.confirm2') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="less">
.dictionary-page {
  padding: 16px 24px;
}
.page-title {
  font-size: 18px;
  font-weight: 600;
  display: block;
  margin-bottom: 12px;
}
.dict-tabs {
  margin-top: 8px;
}
.toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.search-input {
  width: 280px;
}
.table-wrap {
  min-height: 200px;
}
.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
.items-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 12px 0 8px;
  font-weight: 500;
}
.svg-icon {
  width: 16px;
  height: 16px;
}
</style>
