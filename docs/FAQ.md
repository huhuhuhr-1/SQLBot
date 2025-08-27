# SQLBot 常见问题解答 (FAQ)

## 📋 目录

- [安装问题](#安装问题)
- [使用问题](#使用问题)
- [性能问题](#性能问题)
- [安全问题](#安全问题)
- [故障排除](#故障排除)
- [技术支持](#技术支持)

## 🔧 安装问题

### Q1: 安装时提示 "Python 版本不兼容" 怎么办？

**A**: SQLBot 需要 Python 3.11+ 版本。

```bash
# 检查当前 Python 版本
python3 --version

# 如果版本低于 3.11，请升级 Python
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-pip

# CentOS/RHEL
sudo yum install python3.11 python3.11-pip

# macOS
brew install python@3.11

# 创建虚拟环境
python3.11 -m venv .venv
source .venv/bin/activate
```

### Q2: 安装依赖时出现网络超时错误怎么办？

**A**: 这通常是网络连接问题，可以尝试以下解决方案：

```bash
# 使用国内镜像源
# Python pip
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ package_name

# Node.js npm
npm config set registry https://registry.npmmirror.com

# 或者使用 uv (推荐)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv config set pip.index-url https://pypi.tuna.tsinghua.edu.cn/simple/
```

### Q3: Docker 安装时提示 "端口被占用" 怎么办？

**A**: 检查并释放被占用的端口：

```bash
# 检查端口占用
sudo lsof -i :8000
sudo lsof -i :8001
sudo lsof -i :3000
sudo lsof -i :5432

# 杀死占用进程
sudo kill -9 <PID>

# 或者修改 docker-compose.yaml 中的端口映射
ports:
  - "8001:8000"  # 将 8000 改为 8001
  - "8002:8001"  # 将 8001 改为 8002
  - "3001:3000"  # 将 3000 改为 3001
```

### Q4: 安装完成后无法访问 Web 界面怎么办？

**A**: 按以下步骤检查：

```bash
# 1. 检查服务状态
sudo systemctl status sqlbot
# 或
docker-compose ps

# 2. 检查端口监听
sudo netstat -tlnp | grep -E "(8000|8001|3000)"

# 3. 检查防火墙
sudo ufw status
# 或
sudo firewall-cmd --list-all

# 4. 检查日志
sudo journalctl -u sqlbot -f
# 或
docker-compose logs -f
```

## 🤖 使用问题

### Q5: 如何添加新的数据源？

**A**: 按照以下步骤添加数据源：

1. **登录系统** → 进入"数据源管理"
2. **点击"添加数据源"**
3. **选择数据源类型** (PostgreSQL, MySQL, SQL Server 等)
4. **填写连接信息**:
   - 名称: 给数据源起一个描述性名称
   - 主机: 数据库服务器地址
   - 端口: 数据库端口
   - 数据库名: 要连接的数据库
   - 用户名: 数据库用户名
   - 密码: 数据库密码
5. **测试连接** → 点击"测试连接"验证配置
6. **保存配置** → 连接成功后点击"保存"

### Q6: 如何配置 AI 模型？

**A**: 配置 AI 模型的步骤：

1. **进入"系统设置"** → "AI 模型配置"
2. **选择模型类型**:
   - OpenAI GPT-4
   - Azure OpenAI
   - 本地模型
3. **填写配置信息**:
   ```yaml
   API Key: sk-xxxxxxxxxxxxxxxxxxxxxxxx
   模型: gpt-4
   温度: 0.7
   最大 Token: 4000
   ```
4. **测试连接** → 验证 API 是否可用
5. **保存配置**

### Q7: 如何创建仪表板？

**A**: 创建仪表板的步骤：

1. **进入"仪表板管理"** → "新建仪表板"
2. **设置基本信息**:
   - 名称: 仪表板名称
   - 描述: 仪表板说明
   - 布局: 选择网格布局
3. **添加组件**:
   - 拖拽图表组件到画布
   - 配置图表数据源和样式
   - 添加筛选器和文本组件
4. **配置样式**:
   - 设置颜色主题
   - 调整字体和间距
   - 配置交互行为
5. **保存并发布**

### Q8: 如何设置用户权限？

**A**: 设置用户权限的步骤：

1. **进入"用户管理"** → "用户列表"
2. **选择用户** → 点击"编辑权限"
3. **设置角色**:
   - 系统管理员: 所有权限
   - 数据分析师: 数据查询、图表创建、仪表板管理
   - 普通用户: 数据查看、基础查询
4. **配置数据权限**:
   - 行级权限: 用户只能看到指定部门的数据
   - 列级权限: 用户不能看到敏感字段
5. **保存权限设置**

## ⚡ 性能问题

### Q9: 查询响应速度慢怎么办？

**A**: 可以尝试以下优化方法：

#### 1. 数据库优化
```sql
-- 创建索引
CREATE INDEX idx_sales_date ON sales(sale_date);
CREATE INDEX idx_sales_department ON sales(department_id);

-- 分析表统计信息
ANALYZE sales;

-- 检查慢查询
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
```

#### 2. 应用优化
```python
# 启用查询缓存
CACHE_TTL = 3600  # 缓存 1 小时

# 优化连接池
DB_POOL_SIZE = 20
DB_MAX_OVERFLOW = 30
```

#### 3. 系统优化
```bash
# 增加系统内存
# 使用 SSD 存储
# 优化网络配置
```

### Q10: 系统内存使用率过高怎么办？

**A**: 内存优化建议：

#### 1. 应用层面
```python
# 限制并发连接数
MAX_WORKERS = 4

# 启用内存缓存
REDIS_URL = "redis://localhost:6379/0"
CACHE_TTL = 3600
```

#### 2. 系统层面
```bash
# 检查内存使用
free -h
top -p $(pgrep -f "uvicorn|node")

# 清理缓存
sudo sync && sudo echo 3 > /proc/sys/vm/drop_caches

# 增加交换空间
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Q11: 如何提高并发处理能力？

**A**: 提高并发能力的方案：

#### 1. 水平扩展
```yaml
# docker-compose.yml
services:
  sqlbot:
    deploy:
      replicas: 3  # 启动 3 个实例
    environment:
      - WORKER_PROCESSES=4
```

#### 2. 负载均衡
```nginx
# nginx.conf
upstream sqlbot_backend {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}
```

#### 3. 异步处理
```python
# 使用异步任务队列
from celery import Celery

app = Celery('sqlbot')
app.config_from_object('celeryconfig')

@app.task
def process_query(query):
    # 异步处理查询
    pass
```

## 🔒 安全问题

### Q12: 如何保护敏感数据？

**A**: 数据安全保护措施：

#### 1. 数据库安全
```sql
-- 创建只读用户
CREATE USER sqlbot_readonly WITH PASSWORD 'secure_password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO sqlbot_readonly;

-- 启用行级安全
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- 创建安全策略
CREATE POLICY users_policy ON users
    FOR SELECT USING (department_id = current_setting('app.department_id')::int);
```

#### 2. 应用安全
```python
# 启用 CORS 保护
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],
    allow_credentials=True,
)

# 启用速率限制
@app.post("/api/chat")
@limiter.limit("10/minute")
async def chat(request: Request, chat_request: ChatRequest):
    pass
```

#### 3. 传输安全
```bash
# 启用 HTTPS
sudo certbot --nginx -d your-domain.com

# 配置安全头
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header X-XSS-Protection "1; mode=block";
```

### Q13: 如何防止 SQL 注入攻击？

**A**: SQL 注入防护措施：

#### 1. 使用参数化查询
```python
# 正确做法
query = "SELECT * FROM users WHERE id = :user_id"
result = await db.execute(query, {"user_id": user_id})

# 错误做法 (容易受到 SQL 注入攻击)
query = f"SELECT * FROM users WHERE id = {user_id}"
```

#### 2. 输入验证
```python
from pydantic import BaseModel, validator

class UserQuery(BaseModel):
    user_id: int
    
    @validator('user_id')
    def validate_user_id(cls, v):
        if v <= 0:
            raise ValueError('用户ID必须大于0')
        return v
```

#### 3. 权限控制
```sql
-- 限制用户权限
GRANT SELECT ON users TO sqlbot_user;
REVOKE DELETE, UPDATE, INSERT ON users FROM sqlbot_user;
```

### Q14: 如何设置访问控制？

**A**: 访问控制配置：

#### 1. IP 白名单
```bash
# 防火墙配置
sudo ufw allow from 192.168.1.0/24 to any port 8000
sudo ufw allow from 10.0.0.0/8 to any port 8000
```

#### 2. 时间限制
```python
# 工作时间访问控制
from datetime import datetime, time

def check_work_hours():
    now = datetime.now().time()
    work_start = time(9, 0)  # 9:00
    work_end = time(18, 0)   # 18:00
    
    if not (work_start <= now <= work_end):
        raise HTTPException(status_code=403, detail="非工作时间禁止访问")
```

#### 3. 会话管理
```python
# 会话超时设置
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 强制登出
@app.post("/logout")
async def logout():
    # 清除用户会话
    pass
```

## 🚨 故障排除

### Q15: 服务启动失败怎么办？

**A**: 按以下步骤排查：

#### 1. 检查服务状态
```bash
# 检查服务状态
sudo systemctl status sqlbot

# 查看详细日志
sudo journalctl -u sqlbot -f --no-pager
```

#### 2. 检查依赖服务
```bash
# 检查数据库状态
sudo systemctl status postgresql

# 检查 Redis 状态
sudo systemctl status redis

# 检查端口占用
sudo netstat -tlnp | grep -E "(8000|8001|3000|5432|6379)"
```

#### 3. 检查配置文件
```bash
# 检查环境变量
cat /opt/sqlbot/app/.env

# 检查权限
ls -la /opt/sqlbot/
sudo chown -R sqlbot:sqlbot /opt/sqlbot/
```

### Q16: 数据库连接失败怎么办？

**A**: 数据库连接问题排查：

#### 1. 检查数据库服务
```bash
# 检查 PostgreSQL 状态
sudo systemctl status postgresql

# 检查数据库进程
ps aux | grep postgres

# 检查数据库日志
sudo tail -f /var/log/postgresql/postgresql-*.log
```

#### 2. 测试连接
```bash
# 测试本地连接
psql -h localhost -U sqlbot -d sqlbot -c "SELECT 1;"

# 检查用户权限
sudo -u postgres psql -c "\du sqlbot"

# 检查数据库是否存在
sudo -u postgres psql -c "\l" | grep sqlbot
```

#### 3. 网络配置
```bash
# 检查防火墙
sudo ufw status
sudo firewall-cmd --list-all

# 检查 PostgreSQL 配置
sudo cat /etc/postgresql/*/main/postgresql.conf | grep listen_addresses
sudo cat /etc/postgresql/*/main/pg_hba.conf
```

### Q17: 前端页面显示异常怎么办？

**A**: 前端问题排查：

#### 1. 检查浏览器控制台
```javascript
// 打开浏览器开发者工具 (F12)
// 查看 Console 标签页的错误信息
// 查看 Network 标签页的网络请求
```

#### 2. 检查 API 接口
```bash
# 测试后端 API
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/datasource/list

# 检查 CORS 配置
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: X-Requested-With" \
     -X OPTIONS http://localhost:8000/api/v1/chat
```

#### 3. 检查前端配置
```bash
# 检查环境变量
cat frontend/.env.development
cat frontend/.env.production

# 重新构建前端
cd frontend
npm run build
```

### Q18: 图表渲染失败怎么办？

**A**: 图表服务问题排查：

#### 1. 检查 g2-ssr 服务
```bash
# 检查服务状态
ps aux | grep "node.*app.js"

# 检查端口监听
netstat -tlnp | grep :3000

# 检查日志
tail -f g2-ssr/g2-ssr.log
```

#### 2. 测试图表服务
```bash
# 测试健康检查
curl http://localhost:3000/health

# 测试图表渲染
curl -X POST http://localhost:3000/render \
  -H "Content-Type: application/json" \
  -d '{"type": "line", "data": [{"x": 1, "y": 2}]}'
```

#### 3. 检查依赖
```bash
# 重新安装依赖
cd g2-ssr
rm -rf node_modules package-lock.json
npm install

# 检查 Node.js 版本
node --version  # 需要 18+
```

## 📞 技术支持

### Q19: 如何获取技术支持？

**A**: 技术支持渠道：

#### 1. 官方渠道
- **GitHub Issues**: [提交问题](https://github.com/dataease/SQLBot/issues)
- **技术交流群**: 扫描二维码加入
- **在线文档**: [文档中心](https://docs.sqlbot.com)

#### 2. 自助排查
- **查看日志**: 系统日志、应用日志、错误日志
- **检查配置**: 环境变量、配置文件、权限设置
- **性能监控**: 系统资源、应用指标、数据库性能

#### 3. 问题报告
提交问题时请包含以下信息：
- **问题描述**: 详细描述问题现象
- **环境信息**: 操作系统、版本、配置
- **错误日志**: 完整的错误信息和日志
- **复现步骤**: 如何重现这个问题
- **期望结果**: 期望的正确行为

### Q20: 如何参与项目贡献？

**A**: 参与贡献的方式：

#### 1. 代码贡献
```bash
# Fork 项目
# 创建功能分支
git checkout -b feature/your-feature

# 提交代码
git commit -m "feat: add new feature"

# 推送分支
git push origin feature/your-feature

# 创建 Pull Request
```

#### 2. 文档贡献
- 完善文档内容
- 翻译文档
- 修复文档错误
- 添加使用示例

#### 3. 问题反馈
- 报告 Bug
- 提出功能建议
- 分享使用经验
- 帮助其他用户

---

更多详细信息请参考：
- [安装指南](./INSTALLATION_GUIDE.md)
- [用户指南](./USER_GUIDE.md)
- [开发指南](./DEVELOPMENT_GUIDE.md)
- [生产部署指南](./PRODUCTION_DEPLOYMENT.md)
