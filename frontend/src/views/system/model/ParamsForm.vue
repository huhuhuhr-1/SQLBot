<script lang="ts" setup>
import { computed, ref, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const paramsRef = ref()
const paramsForm = reactive<{
  name: string
  key: string
  val: any
  id: string
}>({
  name: '',
  key: '',
  val: '',
  id: '',
})

const THINK_SWITCH_KEYS = new Set(['global_think_switch', 'quick_question_think_switch'])
const isThinkSwitch = computed(() => THINK_SWITCH_KEYS.has((paramsForm.key || '').trim()))
const toBoolean = (value: any) => {
  if (typeof value === 'boolean') return value
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase()
    if (['true', '1', 'yes', 'on'].includes(normalized)) return true
    if (['false', '0', 'no', 'off'].includes(normalized)) return false
  }
  if (typeof value === 'number') return value !== 0
  return true
}

const rules = {
  name: [
    {
      required: true,
      message: t('datasource.please_enter') + t('common.empty') + t('model.display_name'),
      trigger: 'blur',
    },
  ],
  key: [
    {
      required: true,
      message: t('datasource.please_enter') + t('common.empty') + t('model.parameters'),
      trigger: 'blur',
    },
  ],
  val: [
    {
      required: true,
      message: t('datasource.please_enter') + t('common.empty') + t('model.parameter_value'),
      trigger: 'blur',
    },
  ],
}

const initForm = (item: any) => {
  if (item) {
    Object.assign(paramsForm, { ...item })
  }
  if (isThinkSwitch.value) {
    paramsForm.val = toBoolean(paramsForm.val)
  }
  if (!paramsForm.id) {
    paramsForm.id = `${+new Date()}`
  }
  paramsRef.value.clearValidate()
}

watch(
  () => paramsForm.key,
  () => {
    if (isThinkSwitch.value) {
      paramsForm.val = toBoolean(paramsForm.val)
    }
  }
)

const emits = defineEmits(['submit'])

const submit = () => {
  paramsRef.value.validate((res: any) => {
    if (res) {
      emits('submit', paramsForm)
    }
  })
}

const close = () => {
  paramsForm.name = ''
  paramsForm.key = ''
  paramsForm.val = ''
  paramsForm.id = ''
}
defineExpose({
  initForm,
  submit,
  close,
})
</script>

<template>
  <div class="params-form">
    <el-form
      ref="paramsRef"
      :rules="rules"
      label-position="top"
      :model="paramsForm"
      style="width: 100%"
      @submit.prevent
    >
      <el-form-item prop="key" :label="$t('model.parameters')">
        <el-input
          v-model="paramsForm.key"
          clearable
          :placeholder="$t('datasource.please_enter') + $t('common.empty') + $t('model.parameters')"
        />
      </el-form-item>
      <el-form-item prop="name" :label="$t('model.display_name')">
        <el-input
          v-model="paramsForm.name"
          clearable
          :placeholder="
            $t('datasource.please_enter') + $t('common.empty') + $t('model.display_name')
          "
        />
      </el-form-item>
      <el-form-item prop="val" :label="$t('model.parameter_value')">
        <el-switch v-if="isThinkSwitch" v-model="paramsForm.val" />
        <el-input
          v-else
          v-model="paramsForm.val"
          clearable
          :placeholder="
            $t('datasource.please_enter') + $t('common.empty') + $t('model.parameter_value')
          "
        />
      </el-form-item>
    </el-form>
  </div>
</template>

<style lang="less" scoped>
.params-form {
  .ed-form-item--default {
    margin-bottom: 16px;

    &.is-error {
      margin-bottom: 40px;
    }
  }

  .ed-input-number {
    width: 100%;
  }
}
</style>
