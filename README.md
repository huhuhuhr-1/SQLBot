<p align="center"><img src="https://resource-fit2cloud-com.oss-cn-hangzhou.aliyuncs.com/sqlbot/sqlbot.png" alt="SQLBot" width="300" /></p>
<h3 align="center">基于大模型和 RAG 的智能问数系统</h3>
<p align="center">
  <a href="https://github.com/dataease/SQLBot/releases/latest"><img src="https://img.shields.io/github/v/release/dataease/SQLBot" alt="Latest release"></a>
  <a href="https://github.com/dataease/SQLBot"><img src="https://img.shields.io/github/stars/dataease/SQLBot?color=%231890FF&style=flat-square" alt="Stars"></a>    
  <a href="https://hub.docker.com/r/dataease/SQLbot"><img src="https://img.shields.io/docker/pulls/dataease/sqlbot?label=downloads" alt="Download"></a><br/>

</p>
<hr/>


**基于大模型与 RAG 的智能问数系统**

[![GitHub stars](https://img.shields.io/github/stars/dataease/SQLBot?style=social)](https://github.com/dataease/SQLBot/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/dataease/SQLBot?style=social)](https://github.com/dataease/SQLBot/network/members)
[![GitHub issues](https://img.shields.io/github/issues/dataease/SQLBot)](https://github.com/dataease/SQLBot/issues)
[![GitHub license](https://img.shields.io/github/license/dataease/SQLBot)](https://github.com/dataease/SQLBot/blob/main/LICENSE)

[🚀 快速开始](#快速开始) • [📚 文档中心](./docs/README.md) • [🐛 问题反馈](https://github.com/dataease/SQLBot/issues) • [💬 技术交流](https://github.com/dataease/SQLBot/discussions)


## ✨ 项目简介

SQLBot 是一个基于大语言模型（LLM）和 RAG（Retrieval Augmented Generation）的智能问数系统，让用户能够通过自然语言与数据库进行交互，自动生成 SQL 查询、数据可视化和业务洞察。

### 🌟 核心特性

- **🤖 智能问答**: 自然语言转 SQL，支持复杂业务查询
- **📊 自动图表**: 智能推荐图表类型，一键生成可视化
- **🎛️ 仪表板**: 拖拽式仪表板设计，支持多数据源
- **🔌 多数据源**: 支持 PostgreSQL、MySQL、SQL Server 等主流数据库
- **👥 权限管理**: 细粒度数据权限控制，支持行级和列级权限
- **🚀 高性能**: 异步架构，支持高并发查询处理

## 🚀 快速开始

### Docker 部署（推荐）

```bash
# 拉取官方镜像
docker pull dataease/sqlbot:v1.0.1

# 运行容器
docker run -d \
  --name sqlbot \
  -p 8000:8000 \
  -p 8001:8001 \
  -p 3000:3000 \
  -e POSTGRES_SERVER=your-db-host \
  -e POSTGRES_PASSWORD=your-password \
  dataease/sqlbot:v1.0.1
```

### 一键安装

```bash
# 下载安装脚本
curl -fsSL https://raw.githubusercontent.com/dataease/SQLBot/main/installer/install.sh | bash
```

### 源码构建

```bash
# 克隆项目
git clone https://github.com/dataease/SQLBot.git
cd SQLBot

# 快速构建
chmod +x quick_build.sh
./quick_build.sh

# 启动服务
./start.sh
```

## 🌐 访问系统

- **前端界面**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **默认账号**: admin
- **默认密码**: SQLBot@123456

## 📚 文档中心

我们重新整理了文档结构，按照不同用户角色和使用场景进行分类：

| 文档类型 | 适用用户 | 主要内容 | 快速链接 |
|----------|----------|----------|----------|
| [📖 安装指南](./docs/INSTALLATION_GUIDE.md) | 系统管理员、运维人员 | 系统安装、环境配置、快速部署 | [立即查看](./docs/INSTALLATION_GUIDE.md) |
| [👥 用户指南](./docs/USER_GUIDE.md) | 最终用户、数据分析师 | 功能使用、操作指南、最佳实践 | [立即查看](./docs/USER_GUIDE.md) |
| [💻 开发指南](./docs/DEVELOPMENT_GUIDE.md) | 开发者、贡献者 | 开发环境、代码规范、调试指南 | [立即查看](./docs/DEVELOPMENT_GUIDE.md) |
| [🚀 生产部署指南](./docs/PRODUCTION_DEPLOYMENT.md) | 运维工程师、架构师 | 生产部署、性能优化、监控运维 | [立即查看](./docs/PRODUCTION_DEPLOYMENT.md) |
| [❓ 常见问题解答](./docs/FAQ.md) | 所有用户 | 问题排查、故障排除、技术支持 | [立即查看](./docs/FAQ.md) |

**📖 [完整文档中心](./docs/README.md)** - 按场景查找文档，快速解决问题

## 🏗️ 技术架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Vue 3 前端    │    │  FastAPI 后端   │    │  PostgreSQL     │
│   TypeScript    │◄──►│   Python 3.11+  │◄──►│   pgvector      │
│   Element Plus  │    │   SQLModel      │    │   数据库        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         └──────────────►│   g2-ssr       │◄─────────────┘
                         │   图表渲染服务  │
                         │   @antv/g2     │
                         └─────────────────┘
```

### 技术栈

- **后端**: FastAPI + SQLModel + Alembic + PostgreSQL
- **前端**: Vue 3 + TypeScript + Vite + Element Plus
- **图表**: @antv/g2 + @antv/g2-ssr
- **AI**: OpenAI GPT-4, Azure OpenAI, 本地模型
- **部署**: Docker, Kubernetes, 传统部署

## 🔧 系统要求

- **操作系统**: Linux (Ubuntu 20.04+), macOS 10.15+, Windows 10+
- **Python**: 3.11+
- **Node.js**: 18+
- **PostgreSQL**: 12+
- **内存**: 4GB+ RAM
- **磁盘**: 10GB+ 可用空间

## 🤝 参与贡献

我们欢迎社区贡献！请查看 [贡献指南](./docs/DEVELOPMENT_GUIDE.md#贡献指南) 了解如何参与：

1. **Fork 项目** → 创建功能分支
2. **开发功能** → 编写代码和测试
3. **提交 PR** → 创建 Pull Request

### 贡献类型

- 🐛 **Bug 修复**: 报告和修复问题
- ✨ **新功能**: 添加新特性和改进
- 📚 **文档**: 完善文档和翻译
- 🧪 **测试**: 添加测试用例
- 💡 **建议**: 提出改进建议

## 📞 获取帮助

- **📖 文档**: [完整文档中心](./docs/README.md)
- **🐛 问题**: [GitHub Issues](https://github.com/dataease/SQLBot/issues)
- **💬 讨论**: [GitHub Discussions](https://github.com/dataease/SQLBot/discussions)
- **📧 邮箱**: 通过 GitHub 联系我们

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=dataease/sqlbot&type=Date)](https://www.star-history.com/#dataease/sqlbot&Date)

## 飞致云旗下的其他明星项目

- [DataEase](https://github.com/dataease/dataease/) - 人人可用的开源 BI 工具
- [1Panel](https://github.com/1panel-dev/1panel/) - 现代化、开源的 Linux 服务器运维管理面板
- [MaxKB](https://github.com/1panel-dev/MaxKB/) - 强大易用的企业级智能体平台
- [JumpServer](https://github.com/jumpserver/jumpserver/) - 广受欢迎的开源堡垒机
- [Halo](https://github.com/halo-dev/halo/) - 强大易用的开源建站工具
- [MeterSphere](https://github.com/metersphere/metersphere/) - 新一代的开源持续测试工具

## License

本仓库遵循 [FIT2CLOUD Open Source License](LICENSE) 开源协议，该许可证本质上是 GPLv3，但有一些额外的限制。

