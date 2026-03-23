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

/** 「设置」菜单与 getRoutes() 完全解耦；统计分析已提至一级 /st，不在此子菜单 */
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
    { name: 'dictionary', path: '/set/dictionary', titleKey: 'dictionary.title' },
    { name: 'prompt', path: '/set/prompt', titleKey: 'prompt.customize_prompt_words' },
  ],
}

/** 根据固定配置生成「设置」菜单节点；「自定义提示词」仅系统管理员可见 */
function buildSetMenuNode(
  spec: typeof SET_MENU_SPEC,
  tFn: (key: string) => string,
  options?: { includePrompt?: boolean }
): { path: string; name: string; meta: { title: string; iconActive: string; iconDeActive: string }; children: any[] } {
  let children = spec.children
  if (options?.includePrompt === false) {
    children = children.filter((item: any) => item.name !== 'prompt')
  }
  const setChildren = children.map((item: any) => ({
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
/** 仅系统管理员（uid 为 1）：普通成员不可见「自定义提示词」；「统计分析」见一级菜单 /st */
const isSystemAdmin = computed(() => String(userStore.uid) === '1')

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
    // 系统管理下不允许有「统计分析」：不把 statistics 放入侧栏
    const systemChildrenWithoutStatistics = (sysRouter?.children || []).filter(
      (r: any) => r.name !== 'statistics'
    )
    // 系统管理下的「系统设置」里不允许有「自定义提示词」
    const systemChildren = systemChildrenWithoutStatistics.map((r: any) => {
      if (r.name === 'setting' && r.children?.length) {
        return {
          ...r,
          children: r.children.filter(
            (c: any) => c.name !== 'prompt' && c.name !== 'customPrompt'
          ),
        }
      }
      return r
    })
    return systemChildren
  }
  // 排除「设置」及 /set/*，避免 xpack 修改 router 后菜单仍用 getRoutes() 的 set 子项
  const list = router.getRoutes().filter((route) => {
    if (route.name === 'set' || route.path === '/set' || String(route.path || '').startsWith('/set/')) {
      return false
    }
    return (
      !route.path.includes('embeddedPage') &&
      !route.path.includes('assistant') &&
      !route.path.includes('canvas') &&
      !route.path.includes('member') &&
      !route.path.includes('professional') &&
      !route.path.includes('401') &&
      !route.path.includes('training') &&
      !route.path.includes('dictionary') &&
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

  if (!userStore.isSpaceAdmin) {
    return list
  }
  // 「设置」完全由固定配置生成；「自定义提示词」仅系统管理员可见
  const syntheticSet = buildSetMenuNode(SET_MENU_SPEC, t, {
    includePrompt: isSystemAdmin.value,
  })
  // 「设置」放到菜单最后一项
  return [...list, syntheticSet]
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
