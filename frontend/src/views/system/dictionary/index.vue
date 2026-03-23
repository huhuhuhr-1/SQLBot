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
const activeTab = ref<'dict' | 'binding'>('dict')
const searchLoading = ref(false)
const keywords = ref('')
const oldDictKeywords = ref('')
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

const bindingDrawer = ref(false)
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

const onTabChange = () => {
  if (activeTab.value === 'dict') {
    dictPage.currentPage = 1
    loadDictPage()
  } else {
    bindingPage.currentPage = 1
    loadBindingPage()
  }
}

const dictSearch = () => {
  oldDictKeywords.value = keywords.value
  dictPage.currentPage = 1
  loadDictPage()
}

const handleDictSizeChange = () => {
  dictPage.currentPage = 1
  loadDictPage()
}

const handleDictCurrentChange = () => {
  loadDictPage()
}

const handleBindingSizeChange = () => {
  bindingPage.currentPage = 1
  loadBindingPage()
}

const handleBindingCurrentChange = () => {
  loadBindingPage()
}

const onBindingFilterDsChange = () => {
  bindingPage.currentPage = 1
  loadBindingPage()
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

const onBindingEnableChange = (row: any, val: boolean) => {
  dictionaryApi
    .saveBinding({
      id: row.id,
      dict_id: row.dict_id,
      datasource_id: row.datasource_id,
      table_name: row.table_name,
      column_name: row.column_name,
      enabled: val,
    })
    .then(() => {
      ElMessage.success(t('common.save_success'))
      loadBindingPage()
    })
}

const loadTablesForBinding = (dsId: number) => {
  tableOptions.value = []
  columnOptions.value = []
  bindingForm.value.table_name = ''
  bindingForm.value.column_name = ''
  if (!dsId) return
  datasourceApi.getTables(dsId).then((res: any) => {
    tableOptions.value = (res || []).map((tbl: any) => ({
      label: tbl.tableName + (tbl.tableComment ? ` (${tbl.tableComment})` : ''),
      value: tbl.tableName,
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
  bindingDrawer.value = true
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
  bindingDrawer.value = true
}

const closeDictDrawer = () => {
  dictDrawer.value = false
}

const closeBindingDrawer = () => {
  bindingDrawer.value = false
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
      bindingDrawer.value = false
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
  <div v-loading="searchLoading" class="dictionary">
    <div class="tool-left">
      <div class="tool-left-start">
        <span class="page-title">{{ t('dictionary.title') }}</span>
        <el-radio-group v-model="activeTab" class="dict-tab-switch" @change="onTabChange">
          <el-radio-button value="dict">{{ t('dictionary.dict_tab') }}</el-radio-button>
          <el-radio-button value="binding">{{ t('dictionary.binding_tab') }}</el-radio-button>
        </el-radio-group>
      </div>
      <div v-if="activeTab === 'dict'" class="tool-row">
        <el-input
          v-model="keywords"
          style="width: 240px"
          :placeholder="t('dictionary.search')"
          clearable
          @keydown.enter.exact.prevent="dictSearch"
        >
          <template #prefix>
            <el-icon>
              <icon_searchOutline_outlined />
            </el-icon>
          </template>
        </el-input>
        <el-button secondary @click="dictSearch">{{ t('common.search') }}</el-button>
        <el-button type="primary" @click="openCreateDict">
          <template #icon>
            <icon_add_outlined />
          </template>
          {{ t('dictionary.create') }}
        </el-button>
      </div>
      <div v-else class="tool-row">
        <el-select
          v-model="bindingFilterDs"
          clearable
          filterable
          style="width: 240px"
          :placeholder="t('dictionary.datasource')"
          @change="onBindingFilterDsChange"
        >
          <el-option v-for="d in dsOptions" :key="d.id" :label="d.name" :value="d.id" />
        </el-select>
        <el-button type="primary" @click="openCreateBinding">
          <template #icon>
            <icon_add_outlined />
          </template>
          {{ t('dictionary.add_binding') }}
        </el-button>
      </div>
    </div>

    <div v-if="!searchLoading" class="table-content">
      <div v-show="activeTab === 'dict'" class="preview-or-schema">
        <el-table :data="dictList" style="width: 100%">
          <el-table-column prop="name" :label="t('dictionary.name')" min-width="160" />
          <el-table-column prop="code" :label="t('dictionary.code')" width="160" />
          <el-table-column :label="t('dictionary.description')" min-width="220">
            <template #default="scope">
              <div class="field-comment_d">
                <span :title="scope.row.description" class="notes-in_table">{{
                  scope.row.description || '—'
                }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="item_count" :label="t('dictionary.item_count')" width="100" />
          <el-table-column :label="t('ds.status')" width="120">
            <template #default="scope">
              <div style="display: flex; align-items: center" @click.stop>
                <el-switch
                  :model-value="scope.row.enabled"
                  size="small"
                  @change="(val: boolean) => onDictEnableChange(scope.row, val)"
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
                  <el-icon class="action-btn" size="16" @click.stop="openEditDict(scope.row)">
                    <IconOpeEdit />
                  </el-icon>
                </el-tooltip>
                <el-tooltip
                  :offset="14"
                  effect="dark"
                  :content="t('dashboard.delete')"
                  placement="top"
                >
                  <el-icon class="action-btn" size="16" @click.stop="deleteDictRow(scope.row)">
                    <IconOpeDelete />
                  </el-icon>
                </el-tooltip>
              </div>
            </template>
          </el-table-column>
          <template #empty>
            <EmptyBackground
              v-if="!oldDictKeywords && !dictList.length"
              :description="t('dictionary.empty_no_dict')"
              img-type="noneWhite"
            />
            <EmptyBackground
              v-if="!!oldDictKeywords && !dictList.length"
              :description="t('datasource.relevant_content_found')"
              img-type="tree"
            />
          </template>
        </el-table>
      </div>

      <div v-show="activeTab === 'binding'" class="preview-or-schema">
        <el-table :data="bindingList" style="width: 100%">
          <el-table-column prop="dict_name" :label="t('dictionary.name')" min-width="140" />
          <el-table-column prop="dict_code" :label="t('dictionary.code')" width="140" />
          <el-table-column prop="datasource_name" :label="t('dictionary.datasource')" min-width="160" />
          <el-table-column prop="table_name" :label="t('dictionary.table')" width="160" />
          <el-table-column prop="column_name" :label="t('dictionary.column')" width="140" />
          <el-table-column :label="t('ds.status')" width="120">
            <template #default="scope">
              <div style="display: flex; align-items: center" @click.stop>
                <el-switch
                  :model-value="scope.row.enabled"
                  size="small"
                  @change="(val: boolean) => onBindingEnableChange(scope.row, val)"
                />
              </div>
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
                  <el-icon class="action-btn" size="16" @click.stop="openEditBinding(scope.row)">
                    <IconOpeEdit />
                  </el-icon>
                </el-tooltip>
                <el-tooltip
                  :offset="14"
                  effect="dark"
                  :content="t('dashboard.delete')"
                  placement="top"
                >
                  <el-icon class="action-btn" size="16" @click.stop="deleteBindingRow(scope.row)">
                    <IconOpeDelete />
                  </el-icon>
                </el-tooltip>
              </div>
            </template>
          </el-table-column>
          <template #empty>
            <EmptyBackground
              :description="t('dictionary.empty_no_binding')"
              img-type="noneWhite"
            />
          </template>
        </el-table>
      </div>
    </div>

    <div v-if="activeTab === 'dict' && dictPage.total > 0" class="pagination-container">
      <el-pagination
        v-model:current-page="dictPage.currentPage"
        v-model:page-size="dictPage.pageSize"
        :page-sizes="[10, 20, 30]"
        :background="true"
        layout="total, sizes, prev, pager, next, jumper"
        :total="dictPage.total"
        @size-change="handleDictSizeChange"
        @current-change="handleDictCurrentChange"
      />
    </div>
    <div v-if="activeTab === 'binding' && bindingPage.total > 0" class="pagination-container">
      <el-pagination
        v-model:current-page="bindingPage.currentPage"
        v-model:page-size="bindingPage.pageSize"
        :page-sizes="[10, 20, 30]"
        :background="true"
        layout="total, sizes, prev, pager, next, jumper"
        :total="bindingPage.total"
        @size-change="handleBindingSizeChange"
        @current-change="handleBindingCurrentChange"
      />
    </div>
  </div>

  <el-drawer
    v-model="dictDrawer"
    :title="dictForm.id ? t('dictionary.edit_dict') : t('dictionary.create')"
    destroy-on-close
    size="600px"
    :before-close="closeDictDrawer"
    modal-class="dictionary-drawer"
  >
    <el-form
      label-width="180px"
      label-position="top"
      class="form-content_error dictionary-form"
      @submit.prevent
    >
      <el-form-item :label="t('dictionary.name')">
        <el-input
          v-model="dictForm.name"
          :placeholder="t('datasource.please_enter') + t('dictionary.name')"
          clearable
          maxlength="255"
        />
      </el-form-item>
      <el-form-item :label="t('dictionary.code')">
        <el-input
          v-model="dictForm.code"
          :disabled="!!dictForm.id"
          :placeholder="t('datasource.please_enter') + t('dictionary.code')"
          clearable
          maxlength="128"
        />
      </el-form-item>
      <el-form-item :label="t('dictionary.description')">
        <el-input
          v-model="dictForm.description"
          type="textarea"
          :autosize="{ minRows: 3, maxRows: 8 }"
          :placeholder="t('datasource.please_enter')"
        />
      </el-form-item>
      <el-form-item :label="t('dictionary.enabled')">
        <el-switch v-model="dictForm.enabled" size="small" />
      </el-form-item>
      <el-form-item>
        <template #label>
          <div class="dict-items-label">
            <span>{{ t('dictionary.items') }}</span>
            <span class="dict-add-item-btn" @click="addItemRow">
              <el-icon size="16">
                <icon_add_outlined />
              </el-icon>
              {{ t('dictionary.add_item') }}
            </span>
          </div>
        </template>
        <div class="dict-items-wrap">
          <el-scrollbar>
            <div
              v-for="(it, index) in dictForm.items"
              :key="index"
              class="dict-item-row"
            >
              <el-input
                v-model="it.item_code"
                class="dict-item-input"
                :placeholder="t('dictionary.item_code')"
                clearable
              />
              <el-input
                v-model="it.item_name"
                class="dict-item-input"
                :placeholder="t('dictionary.item_name')"
                clearable
              />
              <el-input-number
                v-model="it.sort"
                class="dict-item-sort"
                :controls="false"
                :placeholder="t('dictionary.sort')"
              />
              <el-tooltip :offset="14" effect="dark" :content="t('dashboard.delete')" placement="top">
                <el-icon
                  class="hover-icon_with_bg"
                  size="16"
                  style="color: #646a73"
                  @click.stop="removeItemRow(index)"
                >
                  <IconOpeDelete />
                </el-icon>
              </el-tooltip>
            </div>
          </el-scrollbar>
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <div v-loading="dictSaving" class="dialog-footer">
        <el-button secondary @click="closeDictDrawer">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="saveDict">{{ t('common.save') }}</el-button>
      </div>
    </template>
  </el-drawer>

  <el-drawer
    v-model="bindingDrawer"
    :title="bindingForm.id ? t('dictionary.edit_binding') : t('dictionary.add_binding')"
    destroy-on-close
    size="600px"
    :before-close="closeBindingDrawer"
    modal-class="dictionary-drawer"
  >
    <el-form label-position="top" class="form-content_error dictionary-form" @submit.prevent>
      <el-form-item :label="t('dictionary.select_dict')">
        <el-select
          v-model="bindingForm.dict_id"
          filterable
          style="width: 100%"
          :placeholder="t('datasource.Please_select')"
        >
          <el-option
            v-for="o in dictOptions"
            :key="o.id"
            :label="`${o.name} (${o.code})`"
            :value="o.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('dictionary.datasource')">
        <el-select
          v-model="bindingForm.datasource_id"
          filterable
          style="width: 100%"
          :disabled="!!bindingForm.id"
          :placeholder="t('datasource.Please_select')"
          @change="(v: number) => loadTablesForBinding(v)"
        >
          <el-option v-for="d in dsOptions" :key="d.id" :label="d.name" :value="d.id" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('dictionary.table')">
        <el-select
          v-model="bindingForm.table_name"
          filterable
          allow-create
          default-first-option
          style="width: 100%"
          :disabled="!bindingForm.datasource_id || !!bindingForm.id"
          :placeholder="t('datasource.Please_select')"
          @change="(v: string) => bindingForm.datasource_id && loadColumnsForBinding(bindingForm.datasource_id!, v)"
        >
          <el-option v-for="tbl in tableOptions" :key="tbl.value" :label="tbl.label" :value="tbl.value" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('dictionary.column')">
        <el-select
          v-model="bindingForm.column_name"
          filterable
          allow-create
          default-first-option
          style="width: 100%"
          :disabled="!bindingForm.table_name || !!bindingForm.id"
          :placeholder="t('datasource.Please_select')"
        >
          <el-option v-for="c in columnOptions" :key="c.value" :label="c.label" :value="c.value" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('dictionary.enabled')">
        <el-switch v-model="bindingForm.enabled" size="small" />
      </el-form-item>
    </el-form>
    <template #footer>
      <div v-loading="bindingSaving" class="dialog-footer">
        <el-button secondary @click="closeBindingDrawer">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="saveBinding">{{ t('common.save') }}</el-button>
      </div>
    </template>
  </el-drawer>
</template>

<style lang="less" scoped>
.dictionary {
  height: 100%;
  position: relative;

  .tool-left {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    flex-wrap: wrap;
    gap: 12px;

    .tool-left-start {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
    }

    .page-title {
      font-weight: 500;
      font-size: 20px;
      line-height: 28px;
    }

    .dict-tab-switch {
      :deep(.ed-radio-button__inner) {
        padding: 6px 16px;
      }
    }

    .tool-row {
      display: flex;
      align-items: center;
      flex-direction: row;
      gap: 8px;
      flex-wrap: wrap;
    }
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

        .ed-icon {
          position: relative;
          cursor: pointer;
          margin-top: 4px;

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

        .ed-icon + .ed-icon {
          margin-left: 12px;
        }
      }
    }
  }

  .pagination-container {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    margin-top: 16px;
  }
}
</style>

<style lang="less">
.dictionary-drawer {
  .ed-form-item--label-top .ed-form-item__label {
    margin-bottom: 4px;
  }

  .ed-form-item__label {
    color: #646a73;
  }

  .ed-textarea__inner {
    line-height: 22px;
  }

  .dict-items-label {
    display: flex;
    align-items: center;
    width: 100%;
    padding-right: 0;
  }

  .dict-add-item-btn {
    margin-left: auto;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    height: 26px;
    padding: 0 8px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 14px;
    color: var(--ed-color-primary);

    &:hover {
      background-color: #1f23291a;
    }
  }

  .dict-items-wrap {
    width: 100%;
    max-height: min(360px, 45vh);
  }

  .dict-item-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
    padding-right: 4px;
  }

  .dict-item-input {
    flex: 1;
    min-width: 0;
  }

  .dict-item-sort {
    width: 88px;
    flex-shrink: 0;
  }

  .hover-icon_with_bg {
    cursor: pointer;
    flex-shrink: 0;
  }
}
</style>
