# 深度分析原型页面设计文档

**创建时间**: 2026-03-15 23:45  
**参考现有**: `frontend/src/views/deep-analysis/index.vue`  
**设计目标**: 增强证据链可视化、查询链追踪、结论展示

---

## 一、页面布局

### 1.1 整体结构

```
┌────────────────────────────────────────────────────────────┐
│  页面头部                                                   │
│  [标题 + 描述              |           📊 导出报告 按钮]     │
├────────────────────────────────────────────────────────────┤
│  配置区域（卡片）                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 数据源选择  │  问题输入框 (多行)                      │   │
│  │             │                                      │   │
│  │             │   [开始分析] [停止]                    │   │
│  └─────────────────────────────────────────────────────┘   │
├────────────────────────────────────────────────────────────┤
│  错误提示（如有）                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ⚠️ 错误信息                                          │   │
│  └─────────────────────────────────────────────────────┘   │
├────────────────────────────────────────────────────────────┤
│  主内容区（左右两栏布局）                                     │
│  ┌─────────────────────────┬─────────────────────────────┐ │
│  │   左侧面板 (70%)        │    右侧面板 (30%)           │ │
│  │                         │                             │ │
│  │  分析过程               │   查询链时间线              │ │
│  │  - 思考过程（折叠）     │   - Step 1 ✅              │ │
│  │  - Markdown 内容        │   - Step 2 ⏳              │ │
│  │  - SQL 代码块           │   - Step 3 ❌              │ │
│  │                         │                             │ │
│  │                         │   证据链面板                │ │
│  │                         │   - 证据 1 [q1] [Trend]    │ │
│  │                         │   - 证据 2 [q2] [Outstand] │ │
│  │                         │                             │ │
│  │                         │   分析结论卡片              │ │
│  │                         │   - 结论文本                │ │
│  │                         │   - 总步骤：3  证据数：2    │ │
│  └─────────────────────────┴─────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

---

## 二、组件设计

### 2.1 页面头部

**元素**:
- 标题：`🔍 深度分析`
- 描述：`通过 AI 自动规划查询路径，执行复杂数据分析任务`
- 导出按钮：分析完成后显示

**状态**:
- 导出按钮默认隐藏
- `analysisComplete = true` 时显示

---

### 2.2 配置区域（卡片样式）

**字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| 数据源 | Select | 下拉选择，支持搜索 |
| 问题 | Textarea | 3 行，2000 字限制 |
| 开始按钮 | Button | 禁用条件：无数据源或问题为空 |
| 停止按钮 | Button | 仅在分析中显示 |

**交互**:
- 分析开始后，配置区域禁用（`disabled`）
- 数据源下拉显示类型标签（如 `MySQL`, `PostgreSQL`）

---

### 2.3 左侧面板：分析过程

**结构**:
```
┌─────────────────────────────────────┐
│ 📊 分析过程  [进行中/已完成]         │
├─────────────────────────────────────┤
│                                     │
│ ┌─────────────────────────────┐    │
│ │ 💡 思考过程 #1  [展开]       │    │
│ │ 这里是思考内容...            │    │
│ └─────────────────────────────┘    │
│                                     │
│ ### 智能取数                        │
│ （Markdown 渲染内容）                │
│                                     │
│ ────────────────────────────        │
│                                     │
│ ┌─────────────────────────────┐    │
│ │ 💡 思考过程 #2  [展开]       │    │
│ └─────────────────────────────┘    │
│                                     │
│ ### 数据分析                        │
│ （Markdown 渲染内容）                │
│                                     │
└─────────────────────────────────────┘
```

**组件**:
- 面板标题 + 状态标签
- 步骤列表（循环渲染 `steps` 数组）
- 每个步骤包含：
  - `reasoning_content` → 折叠面板（思考过程）
  - `content` → Markdown 渲染

**状态**:
- 加载中 + 无步骤：显示 loading 动画
- 已完成 + 无步骤：显示空状态

---

### 2.4 右侧面板：查询链 + 证据链 + 结论

#### 查询链时间线

**结构**:
```
┌─────────────────────────────────────┐
│ 🔗 查询链  [3]                      │
├─────────────────────────────────────┤
│                                     │
│ ✅ q1                               │
│    筛选高风险登录，按设备类型分组     │
│    [查看 SQL]                       │
│                                     │
│ ⏳ q2                               │
│    计算占比                         │
│                                     │
│ ❌ q3                               │
│    Top10 排序                        │
│                                     │
│ （无查询时）暂无查询记录             │
└─────────────────────────────────────┘
```

**数据源**: `queryChain` 数组

| 字段 | 类型 | 说明 |
|------|------|------|
| query_id | string | 查询 ID（如 "q1"） |
| query | string | 查询描述 |
| sql | string | 生成的 SQL |
| status | enum | running/completed/failed |

**图标**:
- ✅ `CircleCheckFilled` - completed
- ⏳ `Loading` (旋转) - running
- ❌ `CircleCloseFilled` - failed

**交互**:
- 点击"查看 SQL" → 弹出对话框显示 SQL
- 对话框支持复制 SQL

---

#### 证据链面板

**结构**:
```
┌─────────────────────────────────────┐
│ 📄 证据链  [2]                      │
├─────────────────────────────────────┤
│                                     │
│ ┌─────────────────────────────┐    │
│ │ [q1] [OutstandingFirst]     │    │
│ │ 分析最高风险登录的设备...    │    │
│ │ 数据：100 行 × 2 列           │    │
│ └─────────────────────────────┘    │
│                                     │
│ ┌─────────────────────────────┐    │
│ │ [q2] [Trend]                │    │
│ │ 分析最近 7 天的趋势...        │    │
│ │ 数据：168 行 × 3 列           │    │
│ └─────────────────────────────┘    │
│                                     │
│ （无证据时）暂无证据                │
└─────────────────────────────────────┘
```

**数据源**: `evidenceList` 数组

| 字段 | 类型 | 说明 |
|------|------|------|
| query_id | string | 关联的查询 ID |
| insight | string | 分析类型（如 "OutstandingFirst"） |
| analysis_process | string | 分析过程描述 |
| data_summary | object | 数据摘要 |

---

#### 分析结论卡片

**结构**:
```
┌─────────────────────────────────────┐
│ ✅ 分析结论                         │
├─────────────────────────────────────┤
│                                     │
│ 最近一周高风险登录主要集中在移动端， │
│ 占总数的 78%                        │
│                                     │
│ ────────────────────────────        │
│ 总步骤：3    证据数：2               │
│                                     │
└─────────────────────────────────────┘
```

**数据源**: `rpack` 对象

| 字段 | 类型 | 说明 |
|------|------|------|
| conclusion | string | 最终结论 |
| total_steps | number | 总步骤数 |
| evidence | array | 证据列表 |

---

## 三、数据流

### 3.1 状态变量

```typescript
// 基础数据
const datasourceList = ref<any[]>([])      // 数据源列表
const datasourceId = ref<number | undefined>()
const question = ref('')

// 分析状态
const loading = ref(false)
const errorMsg = ref('')
const analysisStarted = ref(false)
const analysisComplete = ref(false)

// 分析结果
const steps = ref<Array<{ content?: string; reasoning_content?: string; type?: string }>>([])
const queryChain = ref<Array<{ query_id?: string; query?: string; sql?: string; status?: string }>>([])
const evidenceList = ref<Array<{ query_id?: string; insight?: string; analysis_process?: string; data_summary?: any }>>([])
const rpack = ref<any>(null)

// 控制变量
let abortController: AbortController | null = null
let stopFlag = false

// UI 状态
const sqlDialogVisible = ref(false)
const currentSql = ref('')
```

---

### 3.2 SSE 消息处理

**消息类型**:

| type | 说明 | 处理逻辑 |
|------|------|----------|
| `error` | 错误 | 设置 `errorMsg`，显示 Alert |
| `finish` | 完成 | `loading = false`, `analysisComplete = true` |
| `rpack` | 结果包 | 解析 JSON，提取 `query_chain` 和 `evidence` |
| 其他 | 分析步骤 | 推送到 `steps` 数组 |

**RPACK 解析**:
```typescript
if (data.type === 'rpack' && data.content) {
  rpack.value = JSON.parse(data.content)
  if (rpack.value.query_chain) {
    queryChain.value = rpack.value.query_chain
  }
  if (rpack.value.evidence) {
    evidenceList.value = rpack.value.evidence
  }
}
```

---

## 四、交互设计

### 4.1 开始分析

**前置条件**:
- 已选择数据源
- 问题不为空

**流程**:
1. 重置所有状态（steps, queryChain, evidenceList, rpack）
2. `analysisStarted = true`, `loading = true`
3. 发起 SSE 请求
4. 循环读取流式响应
5. 根据消息类型更新对应状态
6. 完成后 `loading = false`, `analysisComplete = true`

---

### 4.2 停止分析

**操作**: 点击"停止"按钮

**流程**:
1. `stopFlag = true`
2. `abortController.abort()`
3. 显示提示："分析已停止"

---

### 4.3 查看 SQL

**操作**: 点击查询链中的"查看 SQL"

**流程**:
1. 设置 `currentSql = query.sql`
2. `sqlDialogVisible = true`
3. 对话框显示 SQL（只读 textarea）
4. 支持复制

---

### 4.4 导出报告

**操作**: 点击"导出报告"按钮

**前置条件**: `rpack !== null`

**流程**:
1. 构建报告对象（包含 conclusion, query_chain, evidence）
2. 生成 JSON Blob
3. 触发下载（文件名：`深度分析报告_时间戳.json`）
4. 显示提示："报告已导出"

---

## 五、样式设计

### 5.1 配色方案

| 元素 | 背景色 | 边框色 | 文字色 |
|------|--------|--------|--------|
| 页面背景 | `--el-bg-color-page` | - | - |
| 卡片 | `--el-bg-color` | `--el-border-color-light` | `--el-text-color-regular` |
| 面板头部 | `--el-fill-color-light` | - | `--el-text-color-primary` |
| 状态标签（进行中） | - | - | `--el-color-warning` |
| 状态标签（已完成） | - | - | `--el-color-success` |

### 5.2 布局尺寸

```css
.page {
  max-width: 1600px;
  margin: 0 auto;
  padding: 20px 24px;
}

.main-content {
  display: grid;
  grid-template-columns: 7fr 3fr;  /* 7:3 比例 */
  gap: 16px;
}

.panel-card {
  border-radius: 8px;
  border: 1px solid var(--el-border-color-lighter);
  background: var(--el-bg-color);
}
```

### 5.3 响应式

```css
/* 小屏幕：单栏布局 */
@media (max-width: 1200px) {
  .main-content {
    grid-template-columns: 1fr;
  }
  
  .right-panel {
    order: -1;  /* 右侧面板在上 */
  }
}
```

---

## 六、文件结构

```
frontend/src/views/deep-analysis/
├── index.vue              # 主页面（改造目标）
├── PROTOTYPE_DESIGN.md    # 本文档
└── components/            # （可选）拆分组件
    ├── ProcessPanel.vue   # 分析过程面板
    ├── QueryChain.vue     # 查询链组件
    ├── EvidenceChain.vue  # 证据链组件
    └── ConclusionCard.vue # 结论卡片
```

---

## 七、实现步骤

### Step 1: 修改 `index.vue` 模板

1. 添加页面头部（标题 + 导出按钮）
2. 重构配置区域（卡片样式）
3. 添加左右两栏布局
4. 左侧：分析过程面板
5. 右侧：查询链 + 证据链 + 结论卡片
6. 添加 SQL 对话框

### Step 2: 添加状态变量

```typescript
const analysisStarted = ref(false)
const analysisComplete = ref(false)
const queryChain = ref([])
const evidenceList = ref([])
const rpack = ref(null)
const sqlDialogVisible = ref(false)
const currentSql = ref('')
```

### Step 3: 修改 SSE 处理

1. 增加 `rpack` 类型消息处理
2. 从 RPACK 中提取 `query_chain` 和 `evidence`
3. 更新对应状态

### Step 4: 添加功能函数

```typescript
function showSql(sql: string) { ... }
function copySql() { ... }
function exportReport() { ... }
```

### Step 5: 添加样式

参考第 5 节样式设计

---

## 八、验收标准

- [ ] 页面布局符合设计（左右 7:3 比例）
- [ ] 查询链正确显示状态图标（✅⏳❌）
- [ ] 点击"查看 SQL"弹出对话框
- [ ] 复制 SQL 功能正常
- [ ] 分析完成后显示"导出报告"按钮
- [ ] 导出报告包含完整 RPACK 数据
- [ ] 响应式布局正常（小屏幕单栏）
- [ ] 加载状态、空状态显示正确

---

**文档结束**
