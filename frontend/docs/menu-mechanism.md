# 前端菜单管理机制 - 深度分析

## 1. 总体架构

### 1.1 双布局体系

| 布局组件 | 路径 | 使用场景 | 菜单数据来源 |
|----------|------|----------|--------------|
| **LayoutDsl.vue** | `components/layout/LayoutDsl.vue` | `/chat`、`/dashboard`、`/set`、`/ds`、`/as` 等 | **Menu.vue**：`router.getRoutes()` 过滤 + 对「设置」子项覆盖 |
| **index.vue** (Layout) | `components/layout/index.vue` | 当前路由表未使用该布局 | 自身 computed：`getRoutes().filter(!redirect)`，与侧边栏不同逻辑 |

**实际生效的侧边栏**：仅 **LayoutDsl → Menu.vue**。因此「设置」下是否出现「自定义提示词」完全由 `Menu.vue` 的 `routerList` 决定。

### 1.2 路由定义（静态）

- **router/index.ts** 中 `/set` 定义为：
  - `path: '/set'`, `name: 'set'`, `redirect: '/set/member'`
  - **children**：member、permission、professional、training、**prompt**（共 5 项）
- **router/dynamic.ts** 在 `isAdmin || isSpaceAdmin` 时向 router **addRoute** 增加 `/ds`、`/as`，否则 **removeRoute** 移除这些 name。
- **router/watch.ts** 的 `beforeEach` 中会执行 **LicenseGenerator.generateRouters(router)**（来自 xpack 远程脚本），可能**动态增删或修改路由**，且脚本不在本仓库，无法保证 `/set` 或其 children 不被修改。

---

## 2. Menu.vue 数据流（当前逻辑）

```
routerList (computed)
    │
    ├─ 若 route.path 包含 '/system'
    │      → 走「系统」分支：getRoutes().filter(name==='system') → formatRoute → 返回 system 的 children
    │
    └─ 否则（工作空间布局）
           → list = getRoutes().filter( 一长串条件 )
           → setIndex = list.findIndex( name==='set' || path==='/set' )
           → 若 setIndex !== -1：list[setIndex] = { ...setRoute, children: SET_CHILDREN_SPEC.map(...) }  // 5 项
           → return list
```

### 2.1 过滤条件（工作空间下）摘要

- **排除**：embeddedPage、assistant、canvas、**member**、**professional**、training、**permission**、embeddedCommon、preview、audit、login、admin-login、chatPreview、/system、dsTable、/:pathMatch(.*)*
- **保留「设置」**：`(path.includes('set') && userStore.isSpaceAdmin) || !route.redirect`
  - 即：要么是「 set 且 空间管理员」，要么是「无 redirect 的一级路由」（如 chat、dashboard、ds、as 等）。

因此非 spaceAdmin 时整块「设置」不会出现在 list 中；能看到「设置」说明当前用户是 spaceAdmin，list 中会有一条 `name==='set'` / `path==='/set'` 的项。

### 2.2 Vue Router 4 的 getRoutes() 行为

- `getRoutes()` 返回的是**当前已注册**的 route 记录数组（标准化后的 RouteRecordNormalized）。
- 若 **LicenseGenerator.generateRouters(router)** 或 **dynamic.ts** 的 addRoute/removeRoute 修改了 router，则下次 getRoutes() 会反映修改后的状态。
- 对嵌套路由，父记录通常带有 `children` 数组；若 xpack 或其它逻辑删除了 `prompt` 子路由，则从 getRoutes() 拿到的「设置」可能只剩 4 个子项。当前做法是用 **SET_CHILDREN_SPEC** 覆盖该节点的 `children`，理论上可避免受 router 内部 children 影响。

### 2.3 渲染链路

- **Menu.vue**：`<MenuItem v-for="menu in routerList" :key="menu.path" :menu="menu" />`
- **MenuItem.vue**：
  - 若 `menu.hidden` → 不渲染
  - 若 `menu.children?.length` → 渲染为 **ElSubMenu**，子项为 `children.map(ele => h(MenuItem, { menu: ele }))`
  - 否则 → 渲染为 **ElMenuItem**

子项是否显示只依赖传入的 `menu.children` 和 `menu.hidden`，无其它过滤。

---

## 3. 为何「自定义提示词」可能不显示（根因归纳）

1. **路由被外部修改**  
   `LicenseGenerator.generateRouters(router)` 在 beforeEach 中执行，可能移除或调整 `/set` 的 children。若在「替换 set 的 children」之前 getRoutes() 已被修改，且我们的替换逻辑未正确覆盖（见下），则仍会显示 4 项。

2. **替换的是「列表项」而非「路由表」**  
   当前做法是：从 `list = getRoutes().filter(...)` 得到 list，再 `list[setIndex] = { ...setRoute, children: setChildren }`。若 `setRoute` 来自 getRoutes() 的引用且其 `children` 在别处被读（例如通过 getter），理论上存在仍读到旧 children 的可能；用新对象覆盖 list[setIndex] 后，MenuItem 拿到的应是新对象，一般可避免该问题。

3. **构建/缓存未更新**  
   若线上或本地访问的是旧前端构建，则仍会是「只显示 4 项」的旧逻辑。

4. **存在其它菜单数据源**  
   若还有其它组件或布局根据 getRoutes() 渲染「设置」子菜单且未做同样覆盖，则可能某处仍显示 4 项。当前代码中侧边栏仅 Menu.vue 一处。

---

## 4. 加固思路：与 getRoutes() 完全解耦

为保证「设置」下 5 项（含「自定义提示词」）在任何情况下都一致，建议：

- **工作空间菜单**中，「设置」这一项**不依赖** `getRoutes()` 返回的 `/set` 的 `children`。
- 用**固定配置**（如现有 SET_CHILDREN_SPEC）**单独构建「设置」菜单节点**，再与其它一级菜单（chat、dashboard、ds、as 等）拼成最终 `routerList`。
- 这样无论 LicenseGenerator 或后续如何改动 router，侧边栏「设置」下始终是固定的 5 项。

实现上可：

- 在 computed 中：先得到「除 set 外的一级菜单」列表，再若 `userStore.isSpaceAdmin` 则追加一条**完全由 SET_CHILDREN_SPEC 生成的「设置」节点**（path、name、meta、children 均来自常量），不再从 getRoutes() 的 set 项拷贝 children。

---

## 5. 关键文件索引

| 文件 | 作用 |
|------|------|
| `router/index.ts` | 静态路由定义，/set 及其 5 个子路由 |
| `router/dynamic.ts` | 动态 addRoute/removeRoute（/ds、/as） |
| `router/watch.ts` | beforeEach：xpack 脚本、LicenseGenerator.generateRouters(router) |
| `components/layout/LayoutDsl.vue` | 使用 Menu.vue 的布局 |
| `components/layout/Menu.vue` | 侧边栏菜单数据 routerList + SET_CHILDREN_SPEC 覆盖 |
| `components/layout/MenuItem.vue` | 递归渲染 ElSubMenu / ElMenuItem |

---

## 6. 常见问题（Q&A）

- **自定义菜单**、**为何侧栏会少项**、**如何绕过 xpack 控制**、**修改设置子项应改哪里**：**[qa-custom-menu-xpack.md](./qa-custom-menu-xpack.md)**
- **「统计分析」「自定义提示词」为何普通成员仍可见、与 xpack 的关系、根因反思与正确做法**：**[qa-set-menu-permission-and-xpack.md](./qa-set-menu-permission-and-xpack.md)**

---

**文档版本**：v1  
**最后更新**：基于当前代码与对话摘要整理。
