# 自定义菜单与绕过 xpack 控制 — 常见问题（Q&A）

本文以问答形式说明：如何自定义侧边栏「设置」菜单、为何会出现少项、以及如何绕过 xpack 对路由的修改，保证菜单项稳定显示。

---

## Q1：侧边栏「设置」下为什么有时只有 4 项，没有「自定义提示词」？

**A：** 侧边栏菜单来自 `Menu.vue` 的 `routerList`，而 `routerList` 基于 **Vue Router 的 `getRoutes()`**。在路由守卫 `router/watch.ts` 的 `beforeEach` 里会执行 **xpack 的 `LicenseGenerator.generateRouters(router)`**，该逻辑会**动态增删或修改路由**。若 xpack 把 `/set` 的 children 改少了（例如移除了 `prompt`），则从 `getRoutes()` 拿到的「设置」子项就只剩 4 个，侧栏也就只显示 4 项。

因此「少项」的根本原因是：**菜单直接依赖了被 xpack 修改后的路由表**。

---

## Q2：如何绕过 xpack，让「设置」下始终显示我们想要的菜单项？

**A：** 让「设置」这一项**不再依赖** `getRoutes()` 里 `/set` 的 `children`，而是用**前端固定配置**单独生成「设置」节点，再拼进最终菜单列表。

当前实现方式：

1. 在 `Menu.vue` 中定义 **SET_MENU_SPEC**：写死「设置」的 path、name、meta 以及 **children 列表**（含 member、permission、professional、training、**prompt** 共 5 项）。
2. 用 **buildSetMenuNode(SET_MENU_SPEC, t)** 根据该配置生成一个「合成设置节点」（path、name、meta、children 均来自配置，不读 router）。
3. 在 `routerList` 的 computed 里：先得到「除 set 外的一级菜单」列表，若是空间管理员则把**合成设置节点**插入/替换进去，作为「设置」菜单项返回。

这样无论 xpack 如何改 router，侧边栏「设置」下的 5 项都由 SET_MENU_SPEC 决定，与 `getRoutes()` 的 children 解耦。

---

## Q3：如何自定义「设置」下的菜单（增删改）？

**A：** 需要动两处，保持一致即可：

1. **菜单展示（侧栏项）**  
   编辑 **`frontend/src/components/layout/Menu.vue`** 里的 **SET_MENU_SPEC**：  
   - 在 `children` 数组中增删或修改项，每项需包含 `name`、`path`、`titleKey`（i18n 键）。  
   - 这样侧边栏「设置」下显示的条目和顺序由这里决定。

2. **路由（页面可访问性）**  
   编辑 **`frontend/src/router/index.ts`**（或实际定义 `/set` 的地方）：  
   - 在 `/set` 的 **children** 里对应地增删或修改路由（path、name、component 等）。  
   - 否则只有菜单没有路由，点击会 404；只有路由没有菜单项，则侧栏不会出现该入口。

两处保持一致后，既能在侧栏看到目标项，又能正常打开对应页面。

---

## Q4：实现「绕过 xpack」时，具体改了哪些代码？

**A：** 核心改动在 **Menu.vue**：

- **SET_MENU_SPEC**：固定配置「设置」整节点及其 5 个子项（含 prompt）。
- **buildSetMenuNode(spec, t)**：根据 spec 和国际化函数 `t` 生成一棵「设置」菜单树（path、name、meta、children）。
- **routerList 的 computed**：  
  - 先按原逻辑用 `getRoutes().filter(...)` 得到一级列表，并找到「设置」在列表中的位置（若有）。  
  - 若是空间管理员，则用 **buildSetMenuNode(SET_MENU_SPEC, t)** 得到 **syntheticSet**，用 syntheticSet 替换或追加到列表中，作为「设置」节点。  
  - 这样最终渲染的「设置」及其子项完全来自 SET_MENU_SPEC，不依赖 `getRoutes()` 里 `/set` 的 children。

路由守卫 **router/watch.ts** 中仍有 xpack 的 `LicenseGenerator.generateRouters(router)`，我们**没有去掉**它，只是**不再用**它影响「设置」菜单的展示来源。

---

## Q5：调试时如何确认「设置」菜单来自配置而非路由？

**A：** 若需排查，可在 **Menu.vue** 的 `routerList` 里临时打印：从 `list` 中取到的 set 节点的 `children`（即 getRoutes 的 /set 子项）与 `syntheticSet.children`（来自 SET_MENU_SPEC）对比。若前者少项而后者为 5 项且含 prompt，说明合成逻辑已生效。

---

## 相关文档

- 菜单数据流与 xpack 影响分析：**`frontend/docs/menu-mechanism.md`**

---

**文档版本**：v1  
**最后更新**：基于自定义菜单与绕过 xpack 的实现整理。
