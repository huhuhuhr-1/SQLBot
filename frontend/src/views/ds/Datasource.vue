<script lang="ts" setup>
import { ref, computed, shallowRef, h } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus-secondary'
import icon_searchOutline_outlined from '@/assets/svg/icon_search-outline_outlined.svg'
import arrow_down from '@/assets/svg/arrow-down.svg'
import icon_add_outlined from '@/assets/svg/icon_add_outlined.svg'
import EmptyBackground from '@/views/dashboard/common/EmptyBackground.vue'
import { useRouter } from 'vue-router'
import DataTable from './DataTable.vue'
import icon_done_outlined from '@/assets/svg/icon_done_outlined.svg'
import { datasourceApi } from '@/api/datasource'
import AddDrawer from '@/views/ds/AddDrawer.vue'
import Card from './Card.vue'
import { useEmitt } from '@/utils/useEmitt'
import DelMessageBox from './DelMessageBox.vue'
import { dsTypeWithImg } from './js/ds-type'
import { useI18n } from 'vue-i18n'
import { useUserStore } from '@/stores/user'
import { chatApi } from '@/api/chat'
import RecommendedProblemConfigDialog from '@/views/ds/RecommendedProblemConfigDialog.vue'
import { highlightKeyword } from '@/utils/xss'
const userStore = useUserStore()
const recommendedProblemConfigRef = ref()

export interface Datasource {
  name: string
  num: string
  type_name: string
  type: string
  img: string
  description: string
  id?: string
  recommended_config?: string
}

const router = useRouter()
const { t } = useI18n()
const keywords = ref('')
const defaultDatasourceKeywords = ref('')
const addDrawerRef = ref()
const searchLoading = ref(false)

const datasourceList = shallowRef([] as Datasource[])
const defaultDatasourceList = shallowRef(dsTypeWithImg as (Datasource & { img: string })[])

const currentDefaultDatasource = ref('')
const datasourceListWithSearch = computed(() => {
  if (!keywords.value && !currentDatasourceType.value) return datasourceList.value
  return datasourceList.value.filter(
    (ele) =>
      ele.name.toLowerCase().includes(keywords.value.toLowerCase()) &&
      (ele.type === currentDatasourceType.value || !currentDatasourceType.value)
  )
})
const defaultDatasourceListWithSearch = computed(() => {
  if (!defaultDatasourceKeywords.value) return defaultDatasourceList.value
  return defaultDatasourceList.value.filter((ele) =>
    ele.name.toLowerCase().includes(defaultDatasourceKeywords.value.toLowerCase())
  )
})

const currentDatasourceType = ref('')

const handleDefaultDatasourceChange = (item: any) => {
  if (currentDatasourceType.value === item.type) {
    currentDefaultDatasource.value = ''
    currentDatasourceType.value = ''
  } else {
    currentDefaultDatasource.value = item.name
    currentDatasourceType.value = item.type
  }
}

const formatKeywords = (item: string) => {
  // Use XSS-safe highlight function
  return highlightKeyword(item, defaultDatasourceKeywords.value, 'isSearch')
}
const handleEditDatasource = (res: any) => {
  addDrawerRef.value.handleEditDatasource(res)
}

const handleCopyDatasource = (item: Datasource) => {
  addDrawerRef.value.handleCopyDatasource(item)
}

const handleRecommendation = (res: Datasource) => {
  recommendedProblemConfigRef.value?.init(res)
}

const handleQuestion = async (id: string) => {
  try {
    await chatApi.checkLLMModel()
  } catch (error: any) {
    console.error(error)
    let errorMsg = t('model.default_miss')
    let confirm_text = t('datasource.got_it')
    if (userStore.isAdmin) {
      errorMsg = t('model.default_miss_admin')
      confirm_text = t('model.to_config')
    }
    ElMessageBox.confirm(t('qa.ask_failed'), {
      confirmButtonType: 'primary',
      tip: errorMsg,
      showCancelButton: userStore.isAdmin,
      confirmButtonText: confirm_text,
      cancelButtonText: t('common.cancel'),
      customClass: 'confirm-no_icon',
      autofocus: false,
      showClose: false,
      callback: (val: string) => {
        if (userStore.isAdmin && val === 'confirm') {
          router.push('/system/model')
        }
      },
    })
    return
  }
  router.push({
    path: '/chat/index',
    query: {
      start_chat: id,
    },
  })
}

const handleAddDatasource = () => {
  addDrawerRef.value.handleAddDatasource()
}

const refreshData = () => {
  search()
}

const panelClick = () => {
  console.info('panelClick')
}

const smartClick = () => {
  console.info('smartClick')
}

const deleteHandler = (item: any) => {
  ElMessageBox.confirm('', {
    confirmButtonType: 'danger',
    tip: t('datasource.operate_with_caution'),
    confirmButtonText: t('dashboard.delete'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
    dangerouslyUseHTMLString: true,
    message: h(
      DelMessageBox,
      {
        name: item.name,
        panelNum: 1,
        smartNum: 4,
        onPanelClick: panelClick,
        onSmartClick: smartClick,
        t,
      },
      ''
    ),
  }).then(() => {
    datasourceApi.delete(item.id, item.name).then(() => {
      ElMessage({
        type: 'success',
        message: t('dashboard.delete_success'),
      })
      search()
    })
  })
  // .catch(() => {
  //   ElMessageBox.confirm(t('datasource.data_source_de', { msg: item.name }), {
  //     tip: t('datasource.cannot_be_deleted'),
  //     cancelButtonText: t('datasource.got_it'),
  //     showConfirmButton: false,
  //     customClass: 'confirm-no_icon',
  //     autofocus: false,
  //   })
  // })
}

const search = () => {
  searchLoading.value = true
  datasourceApi
    .list()
    .then((res: any) => {
      datasourceList.value = res
    })
    .finally(() => {
      searchLoading.value = false
    })
}
search()

const currentDataTable = ref()
const dataTableDetail = (ele: any) => {
  currentDataTable.value = ele
}

const selectedIds = ref<string[]>([])
const exportLoading = ref(false)
const importFileRef = ref<HTMLInputElement | null>(null)

const hasSelection = computed(() => selectedIds.value.length > 0)

const allVisibleIds = computed<string[]>(() =>
  datasourceListWithSearch.value.map((ele: any) => String(ele.id))
)

const allSelected = computed(
  () =>
    allVisibleIds.value.length > 0 &&
    allVisibleIds.value.every((id) => selectedIds.value.includes(id))
)

const isSelected = (item: Datasource) => {
  return selectedIds.value.includes(String(item.id))
}

const toggleSelect = (item: Datasource) => {
  const id = String(item.id)
  if (selectedIds.value.includes(id)) {
    selectedIds.value = selectedIds.value.filter((x) => x !== id)
  } else {
    selectedIds.value = [...selectedIds.value, id]
  }
}

const clearSelection = () => {
  selectedIds.value = []
}

const toggleSelectAll = () => {
  if (allSelected.value) {
    clearSelection()
    return
  }
  selectedIds.value = [...allVisibleIds.value]
}

const handleBatchDelete = async () => {
  if (!selectedIds.value.length) return
  try {
    await ElMessageBox.confirm(
      `将删除选中的 ${selectedIds.value.length} 个数据源，且无法恢复，是否继续？`,
      t('common.confirm'),
      {
        confirmButtonText: t('dashboard.delete'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      }
    )
  } catch {
    return
  }

  const ids = [...selectedIds.value]
  const all = datasourceList.value as any[]

  for (const id of ids) {
    const item = all.find((d: any) => String(d.id) === id)
    if (!item) continue
    try {
      await datasourceApi.delete(item.id, item.name)
    } catch (e: any) {
      ElMessage({
        type: 'error',
        message: e?.message || '删除数据源失败',
      })
    }
  }

  clearSelection()
  search()
}

const back = () => {
  currentDataTable.value = null
}

const loading = ref(false)

function startLoading() {
  loading.value = true
}
function endLoading() {
  loading.value = false
}

const exportBatch = () => {
  const ids = (datasourceList.value || []).map((d: any) => d.id).filter(Boolean)
  if (!ids.length) {
    ElMessage.warning(t('ds.batch_export_empty'))
    return
  }
  exportLoading.value = true
  datasourceApi
    .exportBatch(ids)
    .then((res) => {
      const blob = new Blob([JSON.stringify(res, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `datasources_export_${Date.now()}.json`
      a.click()
      URL.revokeObjectURL(url)
      ElMessage.success(t('ds.batch_export_success'))
    })
    .finally(() => {
      exportLoading.value = false
    })
}

const triggerImportFile = () => {
  importFileRef.value?.click()
}

const onImportFile = (e: Event) => {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    try {
      const payload = JSON.parse(reader.result as string)
      if (!payload.datasources || !Array.isArray(payload.datasources)) {
        ElMessage.error(t('ds.batch_import_invalid'))
        return
      }
      searchLoading.value = true
      datasourceApi
        .importBatch(payload)
        .then((created) => {
          ElMessage.success(t('ds.batch_import_success', { count: created?.length ?? 0 }))
          search()
        })
        .catch((err) => {
          ElMessage.error(err?.message || t('ds.batch_import_failed'))
        })
        .finally(() => {
          searchLoading.value = false
        })
    } catch {
      ElMessage.error(t('ds.batch_import_invalid'))
    }
    input.value = ''
  }
  reader.readAsText(file)
}

useEmitt({
  name: 'ds-index-click',
  callback: back,
})
</script>

<template>
  <div v-show="!currentDataTable" v-loading="loading" class="datasource-config no-padding">
    <div class="datasource-methods">
      <span class="title">{{ $t('ds.title') }}</span>
      <div class="button-input">
        <el-input
          v-model="keywords"
          clearable
          style="width: 240px; margin-right: 12px"
          :placeholder="$t('datasource.search')"
        >
          <template #prefix>
            <el-icon>
              <icon_searchOutline_outlined class="svg-icon" />
            </el-icon>
          </template>
        </el-input>

        <el-popover popper-class="system-default_datasource" placement="bottom-end">
          <template #reference>
            <el-button secondary>
              {{ currentDefaultDatasource || $t('datasource.all_types') }}
              <el-icon style="margin-left: 8px">
                <arrow_down></arrow_down>
              </el-icon> </el-button
          ></template>
          <div class="popover">
            <el-input
              v-model="defaultDatasourceKeywords"
              clearable
              style="width: 100%; margin-right: 12px"
              :placeholder="$t('datasource.search_by_name')"
            >
              <template #prefix>
                <el-icon>
                  <icon_searchOutline_outlined class="svg-icon" />
                </el-icon>
              </template>
            </el-input>
            <div class="popover-content">
              <div
                v-for="ele in defaultDatasourceListWithSearch"
                :key="ele.name"
                class="popover-item"
                :class="currentDefaultDatasource === ele.name && 'isActive'"
                @click="handleDefaultDatasourceChange(ele)"
              >
                <img :src="ele.img" width="24px" height="24px" />
                <div class="datasource-name" v-html="formatKeywords(ele.name)"></div>
                <el-icon size="16" class="done">
                  <icon_done_outlined></icon_done_outlined>
                </el-icon>
              </div>
              <div v-if="!defaultDatasourceListWithSearch.length" class="popover-item empty">
                {{ t('model.relevant_results_found') }}
              </div>
            </div>
          </div>
        </el-popover>

        <el-button @click="exportBatch" :loading="exportLoading">
          {{ $t('ds.batch_export') }}
        </el-button>
        <el-button @click="triggerImportFile">
          {{ $t('ds.batch_import') }}
        </el-button>
        <input
          ref="importFileRef"
          type="file"
          accept=".json"
          style="display: none"
          @change="onImportFile"
        />
        <el-button type="primary" @click="handleAddDatasource">
          <template #icon>
            <icon_add_outlined></icon_add_outlined>
          </template>
          {{ $t('datasource.new_data_source') }}
        </el-button>
      </div>
    </div>

    <!-- 列表选择工具栏：与卡片列表视觉关联，仅在有数据时展示 -->
    <div
      v-if="datasourceListWithSearch.length"
      class="selection-toolbar"
    >
      <el-checkbox
        class="selection-toolbar__select-all"
        :indeterminate="selectedIds.length > 0 && !allSelected"
        :model-value="allSelected"
        @change="toggleSelectAll"
      >
        {{ $t('datasource.select_all') }}
      </el-checkbox>
      <template v-if="hasSelection">
        <span class="selection-toolbar__count">
          {{ $t('user.selected_2_items', { msg: selectedIds.length }) }}
        </span>
        <el-button
          type="danger"
          text
          class="selection-toolbar__delete"
          @click="handleBatchDelete"
        >
          {{ $t('dashboard.delete') }}
        </el-button>
        <el-button text @click="clearSelection">
          {{ $t('common.cancel') }}
        </el-button>
      </template>
    </div>

    <EmptyBackground
      v-if="!!keywords && !datasourceListWithSearch.length"
      :description="$t('datasource.relevant_content_found')"
      class="datasource-yet"
      img-type="tree"
    />

    <div v-else class="card-content">
      <el-row :gutter="16" class="w-full">
        <el-col
          v-for="ele in datasourceListWithSearch"
          :key="ele.id"
          :xs="24"
          :sm="12"
          :md="12"
          :lg="8"
          :xl="6"
          class="mb-16"
        >
          <div class="card-with-select">
            <el-checkbox
              class="card-select"
              :model-value="isSelected(ele)"
              @change="() => toggleSelect(ele)"
            />
            <Card
              :id="ele.id"
              :key="ele.id"
              :name="ele.name"
              :type="ele.type"
              :type-name="ele.type_name"
              :num="ele.num"
              :description="ele.description"
              @start-checking="startLoading"
              @end-checking="endLoading"
              @question="handleQuestion"
              @edit="handleEditDatasource(ele)"
              @copy="handleCopyDatasource(ele)"
              @recommendation="handleRecommendation(ele)"
              @del="deleteHandler(ele)"
              @data-table-detail="dataTableDetail(ele)"
            ></Card>
          </div>
        </el-col>
      </el-row>
    </div>
    <template v-if="!keywords && !datasourceListWithSearch.length && !searchLoading">
      <EmptyBackground
        class="datasource-yet"
        :description="$t('datasource.data_source_yet')"
        img-type="noneWhite"
      />

      <div style="text-align: center; margin-top: -10px">
        <el-button type="primary" @click="handleAddDatasource">
          <template #icon>
            <icon_add_outlined></icon_add_outlined>
          </template>
          {{ $t('datasource.new_data_source') }}
        </el-button>
      </div>
    </template>
    <RecommendedProblemConfigDialog
      ref="recommendedProblemConfigRef"
      @recommended-problem-change="search"
    ></RecommendedProblemConfigDialog>
    <AddDrawer ref="addDrawerRef" @search="search"></AddDrawer>
  </div>
  <DataTable
    v-if="currentDataTable"
    :info="currentDataTable"
    @refresh="refreshData"
    @back="back"
  ></DataTable>
</template>

<style lang="less" scoped>
.datasource-config {
  height: calc(100% - 16px);
  padding: 16px 0 16px 0;
  .datasource-methods {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    padding: 0 24px 0 24px;
    .title {
      font-weight: 500;
      font-size: 20px;
      line-height: 28px;
    }
  }

  .selection-toolbar {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 10px 24px;
    margin-bottom: 8px;
    min-height: 44px;
    background: var(--ed-fill-color-light, #f7f8fa);
    border-radius: 8px;
    margin-left: 24px;
    margin-right: 24px;

    .selection-toolbar__select-all {
      font-size: 14px;
      color: var(--ed-text-color-regular, #646a73);
    }

    .selection-toolbar__count {
      font-size: 14px;
      color: var(--ed-text-color-secondary, #8f959e);
      margin-right: auto;
    }
  }

  .card-content {
    max-height: calc(100% - 40px);
    overflow-y: auto;
    padding: 0 8px 0 24px;

    .w-full {
      width: 100%;
    }

    .mb-16 {
      margin-bottom: 16px;
    }
  }

  .datasource-yet {
    padding-bottom: 0;
    height: auto;
    padding-top: 200px;
  }
}
</style>

<style lang="less">
.system-default_datasource.system-default_datasource {
  padding: 4px 0;
  width: 325px !important;
  box-shadow: 0px 4px 8px 0px #1f23291a;
  border: 1px solid #dee0e3;
  .ed-input {
    .ed-input__wrapper {
      box-shadow: none;
    }

    border-bottom: 1px solid #1f232926;
  }

  .popover {
    .popover-content {
      padding: 4px;
    }
    .popover-item {
      height: 32px;
      display: flex;
      align-items: center;
      padding-left: 12px;
      padding-right: 8px;
      margin-bottom: 2px;
      position: relative;
      border-radius: 4px;
      cursor: pointer;
      &:not(.empty):hover {
        background: #1f23291a;
      }

      &.empty {
        font-weight: 400;
        font-size: 14px;
        line-height: 22px;
        color: #8f959e;
        cursor: default;
      }

      .datasource-name {
        margin-left: 8px;
        font-weight: 400;
        font-size: 14px;
        line-height: 22px;
      }

      .done {
        margin-left: auto;
        display: none;
      }

      .isSearch {
        color: var(--ed-color-primary);
      }

      &.isActive {
        color: var(--ed-color-primary);

        .done {
          display: block;
        }
      }
    }
  }
}

.confirm-no_icon {
  border-radius: 12px;
  padding: 24px;
  .tip {
    margin-top: 24px;
  }
}
</style>
