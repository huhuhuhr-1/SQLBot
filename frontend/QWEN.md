# SQLBot Frontend 项目说明

## 项目概述

SQLBot 是一个基于 Vue 3 + TypeScript 构建的前端应用程序，使用 Vite 作为构建工具。该项目是一个现代化的单页应用 (SPA)，提供 SQL 相关的功能界面，包括聊天、仪表盘、数据源管理、工作区等功能模块。

## 技术栈

### 核心框架
- **Vue 3.5.13** - 渐进式 JavaScript 框架
- **TypeScript 5.7.2** - 类型安全的 JavaScript 超集
- **Vite 6.3.1** - 下一代前端构建工具

### 状态管理
- **Pinia 3.0.2** - Vue 3 官方推荐的状态管理库

### UI 组件库
- **Element Plus 2.10.1** - Vue 3 组件库
- **Element Plus Secondary 1.0.0** - Element Plus 扩展组件

### 路由
- **Vue Router 4.5.0** - Vue.js 官方路由

### 国际化
- **Vue I18n 9.14.4** - 支持多语言（中文、英文、韩文）

### 数据可视化
- **@antv/g2 5.3.3** - 可视化图表库
- **@antv/s2 2.4.3** - 多维表格分析组件
- **@antv/x6 3.1.3** - 图编辑引擎

### 网络请求
- **Axios 1.8.4** - HTTP 客户端

### 工具库
- **Lodash / Lodash-es** - JavaScript 实用工具库
- **Day.js 1.11.13** - 日期处理库
- **@vueuse/core 14.1.0** - Vue 组合式 API 工具集
- **Crypto-js 4.2.0** - 加密库

### 富文本与代码高亮
- **TinyMCE 7.9.1** - 富文本编辑器
- **Highlight.js 11.11.1** - 代码语法高亮
- **Markdown-it 14.1.0** - Markdown 解析器

### 代码质量
- **ESLint 9.28.0** - 代码检查
- **Prettier 3.5.3** - 代码格式化
- **TypeScript ESLint** - TypeScript 规则支持

## 项目结构

```
frontend/
├── public/                 # 静态资源目录
├── src/
│   ├── api/               # API 接口定义
│   │   ├── assistant.ts
│   │   ├── audit.ts
│   │   ├── auth.ts
│   │   ├── chat.ts
│   │   ├── dashboard.ts
│   │   ├── datasource.ts
│   │   ├── embedded.ts
│   │   ├── license.ts
│   │   ├── login.ts
│   │   ├── permissions.ts
│   │   ├── professional.ts
│   │   ├── prompt.ts
│   │   ├── recommendedApi.ts
│   │   ├── setting.ts
│   │   ├── system.ts
│   │   ├── training.ts
│   │   ├── user.ts
│   │   ├── variables.ts
│   │   └── workspace.ts
│   ├── assets/            # 资源文件（图片、样式等）
│   ├── components/        # 公共组件
│   │   ├── about/
│   │   ├── drawer-filter/
│   │   ├── drawer-main/
│   │   ├── filter-text/
│   │   ├── icon-custom/
│   │   ├── Language-selector/
│   │   ├── layout/
│   │   └── rich-text/
│   ├── entity/            # 数据实体/类型定义
│   ├── i18n/              # 国际化配置
│   │   ├── en.json
│   │   ├── zh-CN.json
│   │   └── ko-KR.json
│   ├── router/            # 路由配置
│   ├── stores/            # Pinia 状态管理
│   │   ├── dashboard/
│   │   ├── appearance.ts
│   │   ├── assistant.ts
│   │   ├── chatConfig.ts
│   │   ├── index.ts
│   │   └── user.ts
│   ├── utils/             # 工具函数
│   ├── views/             # 页面视图组件
│   │   ├── chat/          # 聊天模块
│   │   ├── dashboard/     # 仪表盘模块
│   │   ├── ds/            # 数据源模块
│   │   ├── embedded/      # 嵌入模块
│   │   ├── error/         # 错误页面
│   │   ├── login/         # 登录模块
│   │   ├── system/        # 系统设置
│   │   ├── work/          # 工作区模块
│   │   └── WelcomeView.vue
│   ├── App.vue            # 根组件
│   ├── main.ts            # 应用入口
│   └── style.less         # 全局样式
├── .env.development       # 开发环境变量
├── .env.production        # 生产环境变量
├── index.html             # HTML 模板
├── package.json           # 项目依赖配置
├── tsconfig.json          # TypeScript 配置
├── vite.config.ts         # Vite 构建配置
└── .prettierrc            # Prettier 格式化配置
```

## 构建与运行

### 环境要求
- Node.js (推荐 v18+)
- npm 或 pnpm

### 安装依赖
```bash
npm install
```

### 开发模式
```bash
npm run dev
```
启动开发服务器，支持热重载。开发环境 API 地址：`http://localhost:8000/api/v1`

### 生产构建
```bash
npm run build
```
构建生产版本，输出到 `dist/` 目录。生产环境 API 地址为相对路径 `./api/v1`

### 预览构建结果
```bash
npm run preview
```

### 代码检查
```bash
npm run lint
```
运行 ESLint 检查并自动修复问题

## 开发规范

### 代码风格
- **单引号**：使用单引号 `'` 而非双引号
- **无分号**：语句末尾不加分号
- **行尾逗号**：ES5 兼容的多行对象/数组末尾加逗号
- **行宽限制**：最大行宽 100 字符
- **缩进**：2 空格缩进

### 路径别名
项目中配置了 `@` 别名指向 `src/` 目录：
```typescript
import { xxx } from '@/utils/xxx'
```

### 自动导入
项目使用 `unplugin-auto-import` 和 `unplugin-vue-components` 实现：
- Vue API 自动导入（如 `ref`, `computed` 等）
- Element Plus 组件自动导入
- 无需手动导入常用组件和 API

### 国际化
支持三种语言：
- 中文 (zh-CN) - 默认语言
- 英文 (en)
- 韩文 (ko-KR)

使用 `vue-i18n` 进行国际化，语言设置会保存在缓存中。

### 状态管理
使用 Pinia 进行状态管理，stores 目录包含：
- `user.ts` - 用户相关状态
- `assistant.ts` - 助手相关状态
- `chatConfig.ts` - 聊天配置状态
- `appearance.ts` - 外观设置状态
- `dashboard/` - 仪表盘相关状态

## 环境变量

| 变量名 | 开发环境 | 生产环境 | 说明 |
|--------|----------|----------|------|
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | `./api/v1` | API 基础地址 |
| `VITE_APP_TITLE` | `SQLBot (Development)` | `SQLBot` | 应用标题 |

## 注意事项

1. **TypeScript 类型检查**：构建前会运行 `vue-tsc` 进行类型检查
2. **代码分割**：生产构建配置了 `element-plus-secondary` 的单独 chunk
3. **SVG 支持**：使用 `vite-svg-loader` 直接导入 SVG 文件作为 Vue 组件
4. **Less 预处理器**：全局样式使用 Less，配置了 `javascriptEnabled: true`
