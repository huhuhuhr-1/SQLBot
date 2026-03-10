import { ElMessage } from 'element-plus-secondary'
import { useCache } from '@/utils/useCache'
import { useAppearanceStoreWithOut } from '@/stores/appearance'
import { useUserStore } from '@/stores/user'
import { request } from '@/utils/request'
import type { Router } from 'vue-router'
import { generateDynamicRouters } from './dynamic'
import { toLoginPage } from '@/utils/utils'
import { i18n } from '@/i18n'

const appearanceStore = useAppearanceStoreWithOut()
const userStore = useUserStore()
const { wsCache } = useCache()
const whiteList = ['/login', '/admin-login']
const assistantWhiteList = ['/assistant', '/embeddedPage', '/embeddedCommon', '/401']

const wsAdminRouterList = ['/ds/index', '/as/index']

/** xpack 会删掉 /set 下的 prompt 子路由，导致点击「自定义提示词」白屏。此处在其执行后补回。 */
function ensureSetPromptRoute(router: Router) {
  const setRoute = router.getRoutes().find((r: any) => r.name === 'set')
  const hasPrompt = setRoute?.children?.some((c: any) => c.name === 'prompt')
  if (setRoute && !hasPrompt) {
    router.addRoute('set', {
      path: 'prompt',
      name: 'prompt',
      component: () => import('@/views/system/prompt/index.vue'),
      meta: { title: i18n.global.t('prompt.customize_prompt_words') },
    })
  }
}

export const watchRouter = (router: Router) => {
  router.beforeEach(async (to: any, from: any, next: any) => {
    await loadXpackStatic()
    await appearanceStore.setAppearance()
    LicenseGenerator.generateRouters(router)
    ensureSetPromptRoute(router)
    if (to.path.startsWith('/login') && userStore.getUid) {
      next(to?.query?.redirect || '/')
      return
    }
    if (assistantWhiteList.includes(to.path)) {
      next()
      return
    }
    const token = wsCache.get('user.token')
    if (whiteList.includes(to.path)) {
      next()
      return
    }
    if (!token) {
      // ElMessage.error('Please login first')
      next(toLoginPage(to.fullPath))
      return
    }
    if (!userStore.getUid) {
      await userStore.info()
      generateDynamicRouters(router)
      const isFirstDynamicPath = to?.path && ['/ds/index', '/as/index'].includes(to.path)
      if (isFirstDynamicPath) {
        if (userStore.isSpaceAdmin) {
          next({ ...to, replace: true })
          return
        }
      }
    }
    if (to.path === '/docs') {
      location.href = to.fullPath
      return
    }
    if (to.path === '/' || accessCrossPermission(to)) {
      next('/chat')
      return
    }
    if (to.path === '/login' || to.path === '/admin-login') {
      console.info(from)
      next('/chat')
    } else {
      next()
    }
  })
}

const accessCrossPermission = (to: any) => {
  if (!to?.path) return false
  // 自定义提示词：空间管理员可访问（与可见数据源一致）；统计分析仅系统 admin 可访问
  if (to.path.startsWith('/set/prompt') && !userStore.isSpaceAdmin) return true
  if (to.path.startsWith('/set/statistics') && !userStore.isAdmin) return true
  return (
    (to.path.startsWith('/system') && !userStore.isAdmin) ||
    (to.path.startsWith('/set') && !userStore.isSpaceAdmin) ||
    (isWsAdminRouter(to) && !userStore.isSpaceAdmin)
  )
}

const isWsAdminRouter = (to?: any) => {
  return wsAdminRouterList.some((item: string) => to?.path?.startsWith(item))
}
const loadXpackStatic = () => {
  if (document.getElementById('sqlbot_xpack_static')) {
    return Promise.resolve()
  }
  const url = `/xpack_static/license-generator.umd.js?t=${Date.now()}`
  return new Promise((resolve, reject) => {
    request
      .loadRemoteScript(url, 'sqlbot_xpack_static', () => {
        LicenseGenerator?.init(import.meta.env.VITE_API_BASE_URL).then(() => {
          resolve(true)
        })
      })
      .catch((error) => {
        console.error('Failed to load xpack_static script:', error)
        ElMessage.error('Failed to load license generator script')
        reject(error)
      })
  })
}
