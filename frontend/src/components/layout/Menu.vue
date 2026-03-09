<script lang="ts" setup>
import { computed } from 'vue'
import { ElMenu } from 'element-plus-secondary'
import { useRoute, useRouter } from 'vue-router'
import MenuItem from './MenuItem.vue'
import { useUserStore } from '@/stores/user'
import { i18n } from '@/i18n'
// import { routes } from '@/router'
const userStore = useUserStore()
const router = useRouter()
const t = i18n.global.t

/** 「设置」菜单与 getRoutes() 完全解耦：用固定配置生成整节点，避免 xpack/LicenseGenerator 修改路由后子项丢失 */
const SET_MENU_SPEC = {
  path: '/set',
  name: 'set',
  meta: {
    titleKey: 'workspace.set',
    iconActive: 'set',
    iconDeActive: 'noSet',
  },
  children: [
    { name: 'member', path: '/set/member', titleKey: 'workspace.member_management' },
    { name: 'permission', path: '/set/permission', titleKey: 'workspace.permission_configuration' },
    { name: 'professional', path: '/set/professional', titleKey: 'professional.professional_terminology' },
    { name: 'training', path: '/set/training', titleKey: 'training.data_training' },
    { name: 'prompt', path: '/set/prompt', titleKey: 'prompt.customize_prompt_words' },
  ],
}

/** 根据固定配置生成「设置」菜单节点（与 getRoutes 解耦），供侧栏使用 */
function buildSetMenuNode(
  spec: typeof SET_MENU_SPEC,
  tFn: (key: string) => string
): { path: string; name: string; meta: { title: string; iconActive: string; iconDeActive: string }; children: any[] } {
  const setChildren = spec.children.map((item) => ({
    name: item.name,
    path: item.path,
    meta: { title: tFn(item.titleKey) },
  }))
  return {
    path: spec.path,
    name: spec.name,
    meta: {
      title: tFn(spec.meta.titleKey),
      iconActive: spec.meta.iconActive,
      iconDeActive: spec.meta.iconDeActive,
    },
    children: setChildren,
  }
}

defineProps({
  collapse: Boolean,
})

const route = useRoute()
// const menuList = computed(() => route.matched[0]?.children || [])
const activeMenu = computed(() => route.path)
/* const activeIndex = computed(() => {
  const arr = route.path.split('/')
  return arr[arr.length - 1]
}) */
const showSysmenu = computed(() => {
  return route.path.includes('/system')
})

const formatRoute = (arr: any, parentPath = '') => {
  return arr.map((element: any) => {
    let children: any = []
    const path = `${parentPath ? parentPath + '/' : ''}${element.path}`
    if (element.children?.length) {
      children = formatRoute(element.children, path)
    }
    return {
      ...element,
      path,
      children,
    }
  })
}

const routerList = computed(() => {
  if (showSysmenu.value) {
    const [sysRouter] = formatRoute(
      router.getRoutes().filter((route: any) => route?.name === 'system')
    )
    return sysRouter.children
  }
  const list = router.getRoutes().filter((route) => {
    return (
      !route.path.includes('embeddedPage') &&
      !route.path.includes('assistant') &&
      !route.path.includes('embeddedPage') &&
      !route.path.includes('canvas') &&
      !route.path.includes('member') &&
      !route.path.includes('professional') &&
      !route.path.includes('401') &&
      !route.path.includes('training') &&
      !route.path.includes('permission') &&
      !route.path.includes('embeddedCommon') &&
      !route.path.includes('preview') &&
      !route.path.includes('audit') &&
      route.path !== '/login' &&
      route.path !== '/admin-login' &&
      route.path !== '/chatPreview' &&
      !route.path.includes('/system') &&
      ((route.path.includes('set') && userStore.isSpaceAdmin) || !route.redirect) &&
      route.path !== '/:pathMatch(.*)*' &&
      !route.path.includes('dsTable')
    )
  })

  // 「设置」节点与 getRoutes() 完全解耦：用固定配置生成，不读 router 的 children，避免 xpack 修改路由后少项
  const setIndex = list.findIndex((r: any) => r.name === 'set' || r.path === '/set')
  if (!userStore.isSpaceAdmin) {
    return list.filter((r: any) => r.name !== 'set' && r.path !== '/set')
  }
  const syntheticSet = buildSetMenuNode(SET_MENU_SPEC, t)
  // 只保留「设置」下的入口：排除 /set 及其子路径（如 /set/prompt），避免出现两个「自定义提示词」
  const listWithoutSet = list.filter(
    (r: any) =>
      r.name !== 'set' &&
      r.path !== '/set' &&
      !String(r.path || '').startsWith('/set/')
  )
  if (setIndex === -1) {
    return [...listWithoutSet, syntheticSet] as any[]
  }
  const result: any[] = [...listWithoutSet]
  result.splice(setIndex, 0, syntheticSet)
  return result
})
</script>

<template>
  <el-menu :default-active="activeMenu" class="el-menu-demo ed-menu-vertical" :collapse="collapse">
    <MenuItem v-for="menu in routerList" :key="menu.path" :menu="menu"></MenuItem>
  </el-menu>
</template>

<style lang="less">
.ed-menu-vertical {
  --ed-menu-item-height: 40px;
  --ed-menu-bg-color: transparent;
  --ed-menu-base-level-padding: 4px;
  border-right: none;
  .ed-menu-item {
    height: 40px !important;
    border-radius: 6px !important;
    margin-bottom: 2px;
    &.is-active {
      background-color: #fff !important;
      border-radius: 6px;
      font-weight: 500;
    }
  }

  .ed-sub-menu .ed-sub-menu__title {
    border-radius: 6px;
  }

  .ed-sub-menu.is-active:not(.is-opened) {
    .ed-sub-menu__title {
      background-color: #fff !important;
      color: var(--ed-color-primary) !important;
      font-weight: 500;
    }
  }

  .ed-sub-menu.is-active.is-opened {
    .ed-sub-menu__title {
      color: var(--ed-color-primary) !important;
      font-weight: 500;
    }
  }

  .ed-sub-menu .ed-icon {
    margin-right: 8px;
  }
}
.ed-popper.is-light:has(.ed-menu--popup) {
  border: 1px solid #dee0e3;
  border-radius: 6px;
  box-shadow: 0px 4px 8px 0px #1f23291a;
  background: #eff1f0;
  overflow: hidden;
}
.ed-menu--popup {
  padding: 8px;
  background: #eff1f0;

  .ed-menu-item {
    padding: 9px 16px;
    height: 40px !important;
    border-radius: 6px;
    &.is-active {
      background-color: #fff !important;
      font-weight: 500;
    }
  }
}
.ed-sub-menu {
  .subTitleMenu {
    display: none;
  }
}

.ed-menu--popup-container .subTitleMenu {
  color: #646a73 !important;
  pointer-events: none;
}
</style>
