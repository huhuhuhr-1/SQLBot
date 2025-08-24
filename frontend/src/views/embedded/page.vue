<template>
  <div class="sqlbot--embedded-page">
    <chat-component v-if="!loading" ref="chatRef" />
  </div>
</template>
<script setup lang="ts">
import ChatComponent from '@/views/chat/index.vue'
import { onBeforeMount, onBeforeUnmount, ref } from 'vue'
import { useRoute } from 'vue-router'
import { assistantApi } from '@/api/assistant'
import { useAssistantStore } from '@/stores/assistant'

const chatRef = ref()
const assistantStore = useAssistantStore()
const route = useRoute()
const assistantName = ref('')

const validator = ref({
  id: '',
  valid: false,
  id_match: false,
  token: '',
})
const loading = ref(true)
const eventName = 'sqlbot_embedded_event'
const communicationCb = async (event: any) => {
  if (event.data?.eventName === eventName) {
    if (event.data?.messageId !== route.query.id) {
      return
    }
    if (event.data?.busi == 'certificate') {
      const type = parseInt(event.data['type'])
      const certificate = event.data['certificate']
      assistantStore.setType(type || 3)
      if (type === 4) {
        assistantStore.setToken(certificate)
        assistantStore.setAssistant(true)
        loading.value = false
        return
      }
      assistantStore.setCertificate(certificate)
      assistantStore.resolveCertificate(certificate)
    }
    if (event.data?.busi == 'setOnline') {
      setFormatOnline(event.data.online)
    }
  }
}
const setFormatOnline = (text?: any) => {
  if (text === null || typeof text === 'undefined') {
    assistantStore.setOnline(false)
    return
  }
  if (typeof text === 'boolean') {
    assistantStore.setOnline(text)
    return
  }
  if (typeof text === 'string') {
    assistantStore.setOnline(text.toLowerCase() === 'true')
    return
  }
  assistantStore.setOnline(false)
}

const registerReady = (assistantId: any) => {
  window.addEventListener('message', communicationCb)
  const readyData = {
    eventName: 'sqlbot_embedded_event',
    busi: 'ready',
    ready: true,
    messageId: assistantId,
  }
  window.parent.postMessage(readyData, '*')
}

onBeforeMount(async () => {
  const assistantId = route.query.id
  if (!assistantId) {
    ElMessage.error('Miss embedded id, please check embedded url')
    return
  }
  const typeParam = route.query.type
  let assistantType = 2
  if (typeParam) {
    assistantType = parseInt(typeParam.toString())
    assistantStore.setType(assistantType)
  }
  const online = route.query.online
  setFormatOnline(online)

  let name = route.query.name
  if (name) {
    assistantName.value = decodeURIComponent(name.toString())
  }
  const now = Date.now()
  assistantStore.setFlag(now)
  assistantStore.setId(assistantId?.toString() || '')
  if (assistantType === 4) {
    assistantStore.setAssistant(true)
    registerReady(assistantId)
    return
  }
  const param = {
    id: assistantId,
    virtual: assistantStore.getFlag,
    online,
  }
  validator.value = await assistantApi.validate(param)
  assistantStore.setToken(validator.value.token)
  assistantStore.setAssistant(true)
  loading.value = false

  registerReady(assistantId)
})

onBeforeUnmount(() => {
  window.removeEventListener('message', communicationCb)
})
</script>

<style lang="less" scoped>
.sqlbot--embedded-page {
  width: 100%;
  height: 100%;
  position: relative;
  background: #f7f8fa;
}
</style>
