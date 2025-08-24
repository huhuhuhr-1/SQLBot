import { defineStore } from 'pinia'
import { store } from './index'
import { chatApi, ChatInfo } from '@/api/chat'
import { useCache } from '@/utils/useCache'

const { wsCache } = useCache()
const flagKey = 'sqlbit-assistant-flag'
type Resolver<T = any> = (value: T | PromiseLike<T>) => void
type Rejecter = (reason?: any) => void
interface PendingRequest<T = any> {
  resolve: Resolver<T>
  reject: Rejecter
}
interface AssistantState {
  id: string
  token: string
  assistant: boolean
  flag: number
  type: number
  certificate: string
  online: boolean
  requestPromiseMap: Map<string, PendingRequest>
}

export const AssistantStore = defineStore('assistant', {
  state: (): AssistantState => {
    return {
      id: '',
      token: '',
      assistant: false,
      flag: 0,
      type: 0,
      certificate: '',
      online: false,
      requestPromiseMap: new Map<string, PendingRequest>(),
    }
  },
  getters: {
    getCertificate(): string {
      return this.certificate
    },
    getId(): string {
      return this.id
    },
    getToken(): string {
      return this.token
    },
    getAssistant(): boolean {
      return this.assistant
    },
    getFlag(): number {
      return this.flag
    },
    getType(): number {
      return this.type
    },
    getOnline(): boolean {
      return this.online
    },
    getEmbedded(): boolean {
      return this.assistant && this.type === 4
    },
  },
  actions: {
    refreshCertificate<T>() {
      const timeout = 5000
      return new Promise((resolve, reject) => {
        const timeoutId = setTimeout(() => {
          this.requestPromiseMap.delete(this.id)
          reject(new Error(`Request ${this.id} timed out after ${timeout}ms`))
        }, timeout)
        this.requestPromiseMap.set(this.id, {
          resolve: (value: T) => {
            clearTimeout(timeoutId)
            this.requestPromiseMap.delete(this.id)
            resolve(value)
          },
          reject: (reason) => {
            clearTimeout(timeoutId)
            this.requestPromiseMap.delete(this.id)
            reject(reason)
          },
        })
        const readyData = {
          eventName: 'sqlbot_assistant_event',
          busi: 'ready',
          ready: true,
          messageId: this.id,
        }
        window.parent.postMessage(readyData, '*')
      })
    },
    resolveCertificate(data?: any) {
      const peddingRequest = this.requestPromiseMap.get(this.id)
      if (peddingRequest) {
        peddingRequest.resolve(data)
      }
    },
    setId(id: string) {
      this.id = id
    },
    setCertificate(certificate: string) {
      this.certificate = certificate
    },
    setType(type: number) {
      this.type = type
    },
    setToken(token: string) {
      this.token = token
    },
    setAssistant(assistant: boolean) {
      this.assistant = assistant
    },
    setFlag(flag: number) {
      if (wsCache.get(flagKey)) {
        this.flag = wsCache.get(flagKey)
      } else {
        this.flag = flag
        wsCache.set(flagKey, flag)
      }
    },
    setOnline(online: boolean) {
      this.online = !!online
    },
    async setChat() {
      if (!this.assistant) {
        return null
      }
      const res = await chatApi.startAssistantChat()
      const chat: ChatInfo | undefined = chatApi.toChatInfo(res)
      return chat
    },
    clear() {
      wsCache.delete(flagKey)
      this.$reset()
    },
  },
})

export const useAssistantStore = () => {
  return AssistantStore(store)
}
