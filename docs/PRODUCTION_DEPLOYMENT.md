# SQLBot 生产部署指南

## 📋 目录

- [部署架构](#部署架构)
- [环境准备](#环境准备)
- [部署方式](#部署方式)
- [配置优化](#配置优化)
- [监控运维](#监控运维)
- [安全加固](#安全加固)
- [备份恢复](#备份恢复)
- [故障处理](#故障处理)

## 🏗️ 部署架构

### 推荐架构

```
                    ┌─────────────────┐
                    │   负载均衡器    │
                    │   (Nginx/ALB)   │
                    └─────────┬───────┘
                              │
                    ┌─────────▼───────┐
                    │   SQLBot 集群   │
                    │                 │
                    │  ┌─────────────┐│
                    │  │  Backend    ││
                    │  │   (8000)    ││
                    │  └─────────────┘│
                    │  ┌─────────────┐│
                    │  │    MCP      ││
                    │  │   (8001)    ││
                    │  └─────────────┘│
                    │  ┌─────────────┐│
                    │  │   g2-ssr    ││
                    │  │   (3000)    ││
                    │  └─────────────┘│
                    └─────────────────┘
                              │
                    ┌─────────▼───────┐
                    │   数据库集群     │
                    │                 │
                    │  ┌─────────────┐│
                    │  │ PostgreSQL  ││
                    │  │   Master    ││
                    │  └─────────────┘│
                    │  ┌─────────────┐│
                    │  │ PostgreSQL  ││
                    │  │   Slave     ││
                    │  └─────────────┘│
                    └─────────────────┘
```

### 组件说明

- **负载均衡器**: 分发请求，提供高可用性
- **SQLBot 集群**: 多个实例提供负载分担
- **数据库集群**: 主从复制，读写分离
- **缓存层**: Redis 缓存热点数据
- **存储层**: 对象存储和文件系统

## 🛠️ 环境准备

### 硬件要求

#### 最小配置
- **CPU**: 4 核心
- **内存**: 8GB RAM
- **磁盘**: 100GB SSD
- **网络**: 1Gbps

#### 推荐配置
- **CPU**: 8+ 核心
- **内存**: 16GB+ RAM
- **磁盘**: 500GB+ SSD
- **网络**: 10Gbps

#### 生产环境配置
- **CPU**: 16+ 核心
- **内存**: 32GB+ RAM
- **磁盘**: 1TB+ NVMe SSD
- **网络**: 25Gbps+

### 软件要求

#### 操作系统
- **Linux**: Ubuntu 22.04 LTS, CentOS 8+, RHEL 8+
- **容器**: Docker 20.10+, Kubernetes 1.24+

#### 依赖软件
- **Python**: 3.11+
- **Node.js**: 18+
- **PostgreSQL**: 14+
- **Redis**: 6.0+ (可选)
- **Nginx**: 1.20+

### 网络要求

#### 端口配置
```bash
# 必需端口
8000  # 后端 API
8001  # MCP 服务
3000  # 图表服务
5432  # PostgreSQL
6379  # Redis (可选)

# 管理端口
22    # SSH
80    # HTTP
443   # HTTPS
```

#### 防火墙配置
```bash
# Ubuntu/Debian
sudo ufw allow 8000/tcp
sudo ufw allow 8001/tcp
sudo ufw allow 3000/tcp
sudo ufw allow 5432/tcp

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --permanent --add-port=8001/tcp
sudo firewall-cmd --permanent --add-port=3000/tcp
sudo firewall-cmd --permanent --add-port=5432/tcp
sudo firewall-cmd --reload
```

## 🚀 部署方式

### 方式一：Docker 部署（推荐）

#### 1. 准备 Docker 环境

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 2. 部署配置

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  sqlbot:
    image: dataease/sqlbot:v1.0.1
    container_name: sqlbot-prod
    restart: unless-stopped
    ports:
      - "8000:8000"
      - "8001:8001"
      - "3000:3000"
    environment:
      - POSTGRES_SERVER=postgres
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - LOG_LEVEL=INFO
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./data:/opt/sqlbot/data
      - ./logs:/opt/sqlbot/logs
      - ./uploads:/opt/sqlbot/uploads
    depends_on:
      - postgres
      - redis
    networks:
      - sqlbot-network

  postgres:
    image: pgvector/pgvector:pg17
    container_name: sqlbot-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=sqlbot
      - POSTGRES_USER=sqlbot
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - sqlbot-network

  redis:
    image: redis:7-alpine
    container_name: sqlbot-redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - sqlbot-network

  nginx:
    image: nginx:alpine
    container_name: sqlbot-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - sqlbot
    networks:
      - sqlbot-network

volumes:
  postgres_data:
  redis_data:

networks:
  sqlbot-network:
    driver: bridge
```

#### 3. 启动服务

```bash
# 创建环境变量文件
cat > .env << EOF
DB_PASSWORD=your-secure-password
SECRET_KEY=your-secret-key-here
EOF

# 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

### 方式二：Kubernetes 部署

#### 1. 准备 Kubernetes 环境

```bash
# 安装 kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# 安装 Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

#### 2. 部署配置

```yaml
# sqlbot-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sqlbot
  labels:
    app: sqlbot
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sqlbot
  template:
    metadata:
      labels:
        app: sqlbot
    spec:
      containers:
      - name: sqlbot
        image: dataease/sqlbot:v1.0.1
        ports:
        - containerPort: 8000
        - containerPort: 8001
        - containerPort: 3000
        env:
        - name: POSTGRES_SERVER
          value: "postgres-service"
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: sqlbot-secret
              key: db-password
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

#### 3. 部署服务

```bash
# 创建命名空间
kubectl create namespace sqlbot

# 部署应用
kubectl apply -f sqlbot-deployment.yaml

# 查看部署状态
kubectl get pods -n sqlbot

# 查看服务状态
kubectl get services -n sqlbot
```

### 方式三：传统部署

#### 1. 系统准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装依赖
sudo apt install -y python3.11 python3.11-venv python3.11-pip nodejs npm postgresql postgresql-contrib nginx redis-server

# 创建用户
sudo useradd -m -s /bin/bash sqlbot
sudo usermod -aG sudo sqlbot
```

#### 2. 部署应用

```bash
# 切换到用户
sudo su - sqlbot

# 克隆项目
git clone https://github.com/dataease/SQLBot.git
cd SQLBot

# 构建项目
./quick_build.sh

# 部署到生产目录
sudo cp -r package/opt/sqlbot/* /opt/sqlbot/
sudo chown -R sqlbot:sqlbot /opt/sqlbot
```

#### 3. 配置服务

```bash
# 创建 systemd 服务
sudo tee /etc/systemd/system/sqlbot.service > /dev/null << EOF
[Unit]
Description=SQLBot Application
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=sqlbot
WorkingDirectory=/opt/sqlbot
ExecStart=/opt/sqlbot/start.sh
Restart=always
RestartSec=10
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
EOF

# 启用服务
sudo systemctl daemon-reload
sudo systemctl enable sqlbot
sudo systemctl start sqlbot
```

## ⚙️ 配置优化

### 性能优化

#### 1. 数据库优化

```sql
-- 创建索引
CREATE INDEX idx_sales_date ON sales(sale_date);
CREATE INDEX idx_sales_department ON sales(department_id);

-- 分区表
CREATE TABLE sales_partitioned (
  LIKE sales INCLUDING ALL
) PARTITION BY RANGE (sale_date);

-- 连接池配置
max_connections = 200
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
```

#### 2. 应用优化

```python
# backend/apps/core/config.py
class Settings(BaseSettings):
    # 数据库连接池
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 30
    DB_POOL_TIMEOUT: int = 30
    
    # 缓存配置
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 3600
    
    # 并发控制
    MAX_WORKERS: int = 4
    WORKER_TIMEOUT: int = 30
```

#### 3. Nginx 配置

```nginx
# nginx.conf
upstream sqlbot_backend {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:3000;
}

server {
    listen 80;
    server_name your-domain.com;
    
    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    # SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # 代理配置
    location / {
        proxy_pass http://sqlbot_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    # 静态文件缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

## 📊 监控运维

### 监控指标

#### 1. 系统指标
- **CPU 使用率**: 保持在 70% 以下
- **内存使用率**: 保持在 80% 以下
- **磁盘使用率**: 保持在 85% 以下
- **网络流量**: 监控带宽使用情况

#### 2. 应用指标
- **响应时间**: API 平均响应时间 < 500ms
- **错误率**: 错误率 < 1%
- **并发数**: 支持的最大并发用户数
- **吞吐量**: 每秒处理的请求数

#### 3. 数据库指标
- **连接数**: 活跃连接数 < 最大连接数的 80%
- **查询性能**: 慢查询数量
- **锁等待**: 锁等待时间
- **缓存命中率**: 查询缓存命中率

### 监控工具

#### 1. 系统监控
```bash
# 使用 Prometheus + Grafana
# 安装 Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-amd64.tar.gz
tar xvf prometheus-*.tar.gz
cd prometheus-*

# 配置 Prometheus
cat > prometheus.yml << EOF
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'sqlbot'
    static_configs:
      - targets: ['localhost:8000', 'localhost:8001', 'localhost:3000']
EOF

# 启动 Prometheus
./prometheus --config.file=prometheus.yml
```

#### 2. 日志监控
```bash
# 使用 ELK Stack (Elasticsearch + Logstash + Kibana)
# 或使用 Fluentd + Elasticsearch

# 配置日志收集
cat > /etc/fluentd/fluent.conf << EOF
<source>
  @type tail
  path /opt/sqlbot/logs/*.log
  pos_file /var/log/fluentd/sqlbot.log.pos
  tag sqlbot
  format json
</source>

<match sqlbot>
  @type elasticsearch
  host localhost
  port 9200
  index_name sqlbot-logs
</match>
EOF
```

### 告警配置

#### 1. 告警规则
```yaml
# alerting.yml
groups:
  - name: sqlbot_alerts
    rules:
      - alert: HighCPUUsage
        expr: cpu_usage > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "CPU 使用率过高"
          description: "CPU 使用率超过 80% 持续 5 分钟"
      
      - alert: HighMemoryUsage
        expr: memory_usage > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "内存使用率过高"
          description: "内存使用率超过 85% 持续 5 分钟"
      
      - alert: HighErrorRate
        expr: error_rate > 5
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "错误率过高"
          description: "错误率超过 5% 持续 2 分钟"
```

#### 2. 告警通知
```yaml
# 配置告警通知到钉钉/企业微信/邮件
receivers:
  - name: 'team-alerts'
    email_configs:
      - to: 'team@company.com'
        send_resolved: true
    webhook_configs:
      - url: 'https://oapi.dingtalk.com/robot/send?access_token=xxx'
        send_resolved: true
```

## 🔒 安全加固

### 网络安全

#### 1. 防火墙配置
```bash
# 使用 UFW (Ubuntu)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# 使用 firewalld (CentOS/RHEL)
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --remove-service=dhcpv6-client
sudo firewall-cmd --reload
```

#### 2. SSL/TLS 配置
```bash
# 使用 Let's Encrypt 免费证书
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo crontab -e
# 添加以下行
0 12 * * * /usr/bin/certbot renew --quiet
```

### 应用安全

#### 1. 环境变量安全
```bash
# 使用 .env 文件存储敏感信息
# 确保 .env 文件权限正确
chmod 600 .env
chown sqlbot:sqlbot .env

# 定期轮换密钥
SECRET_KEY=$(openssl rand -hex 32)
echo "SECRET_KEY=$SECRET_KEY" >> .env
```

#### 2. 数据库安全
```sql
-- 创建只读用户
CREATE USER sqlbot_readonly WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE sqlbot TO sqlbot_readonly;
GRANT USAGE ON SCHEMA public TO sqlbot_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO sqlbot_readonly;

-- 启用行级安全
ALTER TABLE sales ENABLE ROW LEVEL SECURITY;

-- 创建安全策略
CREATE POLICY sales_policy ON sales
    FOR SELECT USING (department_id = current_setting('app.department_id')::int);
```

#### 3. API 安全
```python
# 启用 CORS 保护
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# 启用速率限制
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/chat")
@limiter.limit("10/minute")
async def chat(request: Request, chat_request: ChatRequest):
    # 聊天逻辑
    pass
```

## 💾 备份恢复

### 数据备份

#### 1. 数据库备份
```bash
# 创建备份脚本
cat > /opt/sqlbot/scripts/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/sqlbot/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="sqlbot"
DB_USER="sqlbot"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据库
pg_dump -U $DB_USER -h localhost $DB_NAME | gzip > $BACKUP_DIR/sqlbot_$DATE.sql.gz

# 备份上传文件
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz /opt/sqlbot/uploads/

# 保留最近 30 天的备份
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "备份完成: $BACKUP_DIR/sqlbot_$DATE.sql.gz"
EOF

# 设置执行权限
chmod +x /opt/sqlbot/scripts/backup.sh

# 添加到 crontab
sudo crontab -e
# 添加以下行，每天凌晨 2 点执行备份
0 2 * * * /opt/sqlbot/scripts/backup.sh
```

#### 2. 配置文件备份
```bash
# 备份配置文件
tar -czf /opt/sqlbot/backups/config_$(date +%Y%m%d_%H%M%S).tar.gz \
  /opt/sqlbot/app/.env \
  /opt/sqlbot/nginx.conf \
  /etc/nginx/sites-available/sqlbot
```

### 数据恢复

#### 1. 数据库恢复
```bash
# 恢复数据库
gunzip -c /opt/sqlbot/backups/sqlbot_20231201_020000.sql.gz | \
psql -U sqlbot -h localhost -d sqlbot

# 恢复上传文件
tar -xzf /opt/sqlbot/backups/uploads_20231201_020000.tar.gz -C /
```

#### 2. 配置恢复
```bash
# 恢复配置文件
tar -xzf /opt/sqlbot/backups/config_20231201_020000.tar.gz -C /

# 重启服务
sudo systemctl restart nginx
sudo systemctl restart sqlbot
```

## 🚨 故障处理

### 常见故障

#### 1. 服务无法启动
```bash
# 检查服务状态
sudo systemctl status sqlbot

# 查看日志
sudo journalctl -u sqlbot -f

# 检查端口占用
sudo netstat -tlnp | grep :8000

# 检查依赖服务
sudo systemctl status postgresql
sudo systemctl status redis
```

#### 2. 数据库连接失败
```bash
# 检查数据库状态
sudo systemctl status postgresql

# 测试数据库连接
psql -h localhost -U sqlbot -d sqlbot -c "SELECT 1;"

# 检查数据库日志
sudo tail -f /var/log/postgresql/postgresql-*.log

# 检查防火墙
sudo ufw status
```

#### 3. 性能问题
```bash
# 检查系统资源
top -p $(pgrep -f "uvicorn|node")
free -h
df -h

# 检查慢查询
sudo -u postgres psql -c "
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
"

# 检查连接数
sudo -u postgres psql -c "
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE state = 'active';
"
```

### 故障恢复流程

#### 1. 故障识别
- 监控告警触发
- 用户反馈问题
- 系统日志异常

#### 2. 故障分析
- 收集错误日志
- 分析系统指标
- 确定故障原因

#### 3. 故障修复
- 执行修复操作
- 验证修复结果
- 监控系统状态

#### 4. 故障总结
- 记录故障过程
- 分析根本原因
- 制定预防措施

---

更多详细信息请参考：[构建指南](./BUILD_GUIDE.md) 和 [调试指南](./DEBUG_GUIDE.md)
