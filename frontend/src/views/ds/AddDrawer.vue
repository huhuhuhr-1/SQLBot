<script lang="ts" setup>
import { ref, nextTick } from 'vue'
import { datasourceApi } from '@/api/datasource'
import { useI18n } from 'vue-i18n'
import icon_close_outlined from '@/assets/svg/operate/ope-close.svg'
import DatasourceList from './DatasourceList.vue'
import DatasourceListSide from './DatasourceListSide.vue'
import DatasourceForm from './DatasourceForm.vue'

const { t } = useI18n()
const datasourceConfigVisible = ref(false)
const activeStep = ref(0)
const currentType = ref('')
const editDatasource = ref(false)
const copyMode = ref(false)
const activeName = ref('')
const activeType = ref('')
const datasourceFormRef = ref()

const beforeClose = () => {
  datasourceConfigVisible.value = false
  activeStep.value = 0
  copyMode.value = false
  datasourceApi.cancelRequests()
}
const clickDatasource = (ele: any) => {
  activeStep.value = 1
  activeName.value = ele.name
  activeType.value = ele.type
}

const clickDatasourceSide = (ele: any) => {
  activeName.value = ele.name
  activeType.value = ele.type
}

const emits = defineEmits(['search'])

const refresh = () => {
  activeName.value = ''
  activeStep.value = 0
  activeType.value = ''
  copyMode.value = false
  datasourceConfigVisible.value = false
  emits('search')
}

const handleEditDatasource = (res: any) => {
  activeStep.value = 1
  datasourceConfigVisible.value = true
  editDatasource.value = true
  currentType.value = res.type_name
  nextTick(() => {
    datasourceFormRef.value.initForm(res)
  })
}

const handleAddDatasource = () => {
  editDatasource.value = false
  copyMode.value = false
  datasourceConfigVisible.value = true
}

const handleCopyDatasource = (item: any) => {
  editDatasource.value = false
  copyMode.value = true
  datasourceApi.getDs(item.id).then((res: any) => {
    activeStep.value = 1
    activeName.value = res.type_name
    activeType.value = res.type
    currentType.value = res.type_name
    datasourceConfigVisible.value = true
    nextTick(() => {
      datasourceFormRef.value?.initFormForCopy(res)
    })
  })
}

const changeActiveStep = (val: number) => {
  activeStep.value = val > 2 ? 2 : val
}

defineExpose({
  handleEditDatasource,
  handleAddDatasource,
  handleCopyDatasource,
})
</script>

<template>
  <el-drawer
    v-model="datasourceConfigVisible"
    :close-on-click-modal="false"
    destroy-on-close
    size="calc(100% - 100px)"
    modal-class="datasource-drawer-fullscreen"
    direction="btt"
    :before-close="beforeClose"
    :show-close="false"
  >
    <template #header="{ close }">
      <span style="white-space: nowrap">{{
        editDatasource
          ? t('datasource.mysql_data_source', { msg: currentType })
          : copyMode
            ? t('datasource.copy_data_source')
            : $t('datasource.new_data_source')
      }}</span>
      <div v-if="!editDatasource" class="flex-center" style="width: 100%">
        <el-steps custom style="max-width: 800px; flex: 1" :active="activeStep" align-center>
          <el-step>
            <template #title> {{ $t('qa.select_datasource') }} </template>
          </el-step>
          <el-step>
            <template #title> {{ $t('datasource.configuration_information') }} </template>
          </el-step>
          <el-step>
            <template #title> {{ $t('ds.form.choose_tables') }} </template>
          </el-step>
        </el-steps>
      </div>
      <el-icon class="ed-dialog__headerbtn mrt" style="cursor: pointer" @click="close">
        <icon_close_outlined></icon_close_outlined>
      </el-icon>
    </template>
    <DatasourceList v-if="activeStep === 0" @click-datasource="clickDatasource"></DatasourceList>
    <DatasourceListSide
      v-if="activeStep === 1 && !editDatasource && !copyMode"
      :active-name="activeName"
      @click-datasource="clickDatasourceSide"
    ></DatasourceListSide>
    <DatasourceForm
      v-if="[1, 2].includes(activeStep)"
      ref="datasourceFormRef"
      :is-data-table="false"
      :active-step="activeStep"
      :active-name="activeName"
      :active-type="activeType"
      @refresh="refresh"
      @close="beforeClose"
      @change-active-step="changeActiveStep"
    ></DatasourceForm>
  </el-drawer>
</template>

<style lang="less">
.datasource-drawer-fullscreen {
  .ed-drawer__body {
    padding: 0;
  }
  .is-process .ed-step__line {
    background-color: var(--ed-color-primary);
  }
}
</style>
