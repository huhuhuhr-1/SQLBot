# 「设置」菜单权限与 xpack 影响 — 问题反思与 Q&A

本文总结：为何普通成员会看到「统计分析」「自定义提示词」、为何与 xpack 有关、以及如何避免类似问题。适合做事故复盘与新人理解菜单/权限设计。

---

## 一、现象与诉求

- **现象**：普通成员（非系统管理员）在侧边栏仍能看到「设置」下的「统计分析」和「自定义提示词」。
- **诉求**：仅系统管理员（uid 为 1）可见这两项；普通成员不可见；且不受 xpack 对路由的修改影响。

---

## 二、根因反思：为什么会写成这样？

### 2.1 菜单数据来源与 xpack 的耦合

| 层级 | 原实现 | 导致的问题 |
|------|--------|-------------|
| **数据来源** | `routerList` 用 `router.getRoutes().filter(...)` 得到一级菜单，其中包含 **router 里的「设置」节点**（`name === 'set'`） | 「设置」的 **children 来自路由表**，而路由表会在 `beforeEach` 里被 **xpack 的 `LicenseGenerator.generateRouters(router)` 动态修改** |
| **权限控制** | 对「自定义提示词」「统计分析」的可见性用 `includePrompt` / `includeStatistics` 控制，但**仅作用在我们「替换」进列表的 syntheticSet 上** | 若 list 里仍包含 **router 的 set**（从 getRoutes 来的那一棵），则可能出现：我们插入了 syntheticSet，但**列表里同时还有 router 的 set**，或 xpack 恢复/保留了 set 的 children，导致某处仍渲染了 router 的 set 子项 |

也就是说：**既有「用固定配置生成 syntheticSet」的逻辑，又没有彻底弃用 router 里的 set」**，两套来源并存，就容易出现「你以为只渲染了 syntheticSet，实际某次渲染仍用到了 getRoutes() 的 set」。

### 2.2 为何会依赖 getRoutes() 的「设置」？

- **历史原因**：侧栏菜单最初很自然地从「路由表」推导：路由里有 `/set` 及其 children，菜单就展示这些项，实现简单、与路由一致。
- **xpack 介入**：后来引入 xpack，在 `beforeEach` 里调用 `LicenseGenerator.generateRouters(router)`，会增删或修改路由（例如删掉 `/set` 下的 `prompt` 以做能力控制）。为补救「自定义提示词」不显示，又加了 **ensureSetPromptRoute** 补回 prompt 路由，并增加了「用 SET_MENU_SPEC 生成 syntheticSet 再替换进列表」的逻辑。
- **未彻底解耦**：替换逻辑是「在 list 里找到 set，删掉后插入 syntheticSet」，但 **list 的生成仍然把 router 里 path 含 `set` 的项放进 list**。一旦 xpack 或路由注册顺序有变化，list 里可能仍是「router 的 set」或混入其子项，**菜单展示与「仅用 syntheticSet」的预期不一致**，权限控制（只对 syntheticSet 做 includePrompt/includeStatistics）就无法完全生效。

### 2.3 权限判断本身

- 「仅系统管理员可见」依赖 `userStore.isAdmin` 或等价地 `String(userStore.uid) === '1'`。
- 若菜单项来自 **router 的 set**，则根本没有走 `buildSetMenuNode(..., { includePrompt, includeStatistics })` 的过滤，**权限逻辑形同虚设**，所以会出现普通成员仍看到这两项。

---

## 三、正确做法（当前实现要点）

1. **菜单与 router 的「设置」彻底解耦**
   - 在 `router.getRoutes().filter(...)` 时**直接排除**「设置」相关路由：`name === 'set'`、`path === '/set'`、`path.startsWith('/set/')`。
   - 这样 **list 中不再包含任何来自 router 的 set**，xpack 对 router 的增删改都不会影响「设置」菜单由谁提供。

2. **「设置」只来自固定配置**
   - 仅当 `userStore.isSpaceAdmin` 时，用 **buildSetMenuNode(SET_MENU_SPEC, t, { includePrompt, includeStatistics })** 生成 **syntheticSet**。
   - `includePrompt` / `includeStatistics` 仅依赖 **isSystemAdmin**（`String(userStore.uid) === '1'`），保证只有系统管理员能看到这两项。

3. **插入位置固定**
   - 将 syntheticSet 插入到「仪表板」之后，不再依赖 `getRoutes()` 里 set 的位置，避免因路由顺序变化导致菜单位置或数量异常。

---

## 四、Q&A 速查

### Q1：为什么普通成员能看到「统计分析」「自定义提示词」？

**A：** 菜单在部分情况下仍使用了 **router 里「设置」节点的 children**（来自 `getRoutes()`），而该树可能被 xpack 恢复或保留 prompt/statistics。权限过滤只作用在我们手写的 **syntheticSet** 上，没有作用在 router 的 set 上，所以会出现「权限写了但普通成员仍能看到」的现象。

### Q2：为什么说和 xpack 有关？

**A：** `LicenseGenerator.generateRouters(router)` 会修改路由表；若菜单继续从 `getRoutes()` 里取「设置」或其子项，则展示结果就受 xpack 行为影响。只有**完全不从 getRoutes() 取「设置」**，改为只用固定配置生成的 syntheticSet，才能保证「谁可见」完全由我们自己的权限逻辑决定。

### Q3：修复后「设置」菜单还依赖路由吗？

**A：** **展示上不依赖**。展示用的「设置」节点 100% 来自 **SET_MENU_SPEC + buildSetMenuNode**；路由表里仍保留 `/set` 及其 children 是为了**能打开对应页面**，不再参与「侧栏显示哪些子项」。

### Q4：以后要加/改「设置」下的菜单项要注意什么？

**A：**  
1. 在 **Menu.vue** 的 **SET_MENU_SPEC.children** 里增删或改项（控制侧栏显示与顺序）。  
2. 若某项需「仅系统管理员可见」，在 **buildSetMenuNode** 的 options 里增加对应 `includeXxx: isSystemAdmin.value`，并在 **buildSetMenuNode** 内对 `spec.children` 做过滤。  
3. 在 **router/index.ts** 的 `/set` 的 children 里同步路由，保证点击能打开页面。  
4. **不要**再依赖 `getRoutes()` 里 `/set` 的 children 来驱动「设置」子菜单。

### Q5：如何避免类似「权限写了却不生效」的问题？

**A：**  
- **单一数据源**：对「谁能看到」有要求的菜单，只从一处数据源生成（这里是 SET_MENU_SPEC + 权限），不要和「可能被外部改动的路由表」混用。  
- **显式排除**：若存在会修改路由的第三方（如 xpack），在构建菜单时**显式排除**这些路由节点，再插入自己控制的节点。  
- **权限与展示一致**：凡按角色/权限过滤的项，确保**最终渲染的菜单树**一定来自做过过滤的那份数据（例如只渲染 syntheticSet，不渲染 router 的 set）。

---

## 五、相关文档

- 菜单数据流与 xpack 影响：**`frontend/docs/menu-mechanism.md`**
- 自定义菜单与绕过 xpack（少项、如何改菜单）：**`frontend/docs/qa-custom-menu-xpack.md`**

---

**文档版本**：v1  
**最后更新**：基于「设置」下「统计分析」「自定义提示词」仅系统管理员可见的修复与 xpack 解耦实现整理。
