# SQLBot 安全漏洞修复 TODO

> 本文档记录了在 `backend/apps/openapi` 代码扫描中发现的安全问题及修复计划
>
> 扫描时间：2025-11-27
> 扫描范围：backend/apps/openapi 目录下所有代码文件
> 扫描类型：SQL注入、文件上传、身份验证、输入验证、配置安全等

## 📊 问题统计

- 🔴 **高危问题**: 2个
- 🟡 **中危问题**: 3个
- 🟢 **低危问题**: 2个
- ✅ **最佳实践**: 4个建议

---

## 🔴 高危问题 (立即修复)

### 1. SQL注入防护不完整
**文件位置:** `backend/apps/openapi/openapi.py:321`
**风险等级:** 🔴 高危
**CVSS评分:** 8.1 (AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)

#### 问题描述
当前的 `is_safe_sql` 函数存在以下安全问题：
- 仅检查SQL语句开头，可能被注释绕过
- 未处理大小写混合的情况
- 缺少对UNION注入的防护
- 未检测多语句执行

#### 漏洞代码
```python
def is_safe_sql(sql: str) -> bool:
    # 当前实现 - 存在安全风险
    safe_prefixes = ('select', 'show', 'describe', 'explain', 'with')
    if sql_lower.startswith(safe_prefixes):
        # 检查是否出现明显的破坏性关键字
        forbidden = [r'\bdelete\b', r'\bupdate\b', ...]
        # 可被绕过
```

#### 修复方案
```python
def is_safe_sql(sql: str) -> bool:
    """改进的SQL安全检查函数"""
    import re

    if not sql or not isinstance(sql, str):
        return False

    # 1. 移除SQL注释和多余空白，防止注释绕过
    cleaned_sql = re.sub(r'/\*.*?\*/|--.*$', '', sql, flags=re.MULTILINE | re.DOTALL)
    cleaned_sql = re.sub(r'\s+', ' ', cleaned_sql).strip()
    sql_lower = cleaned_sql.lower()

    # 2. 检查危险操作（使用更严格的正则表达式）
    dangerous_patterns = [
        r'\b(drop|delete|update|insert|create|alter|truncate|replace|exec|execute|grant|revoke)\b',
        r'\b(union)\s+.*\b(from|into)\b',  # 防止UNION注入
        r';\s*(drop|delete|update|insert|create|alter)',  # 防止多语句
        r'(load_file|into\s+outfile|into\s+dumpfile)',  # 防止文件操作
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, sql_lower, re.IGNORECASE):
            return False

    # 3. 只允许特定操作开头
    allowed_starts = ('select', 'show', 'describe', 'explain', 'with', 'analyze')

    return any(sql_lower.startswith(start) for start in allowed_starts)
```

#### 修复文件
- [ ] `backend/apps/openapi/service/openapi_service.py:613-644`

#### 验证测试
```python
# 需要通过的测试用例
safe_cases = [
    "SELECT * FROM users",
    "select id from products where price > 100",
    "SHOW TABLES",
    "DESCRIBE users",
    "EXPLAIN SELECT * FROM products"
]

# 需要被阻止的测试用例
dangerous_cases = [
    "SELECT * FROM users; DROP TABLE users",
    "/*comment*/SELECT * FROM users",
    "SELECT * FROM users UNION SELECT * FROM passwords",
    "SeLeCt * FROM users; DeLeTe users",
    "SELECT 'test' INTO OUTFILE '/tmp/test.txt'"
]
```

---

### 2. 文件上传安全漏洞
**文件位置:** `backend/apps/openapi/openapi.py:551-579`
**风险等级:** 🔴 高危
**CVSS评分:** 7.8 (AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)

#### 问题描述
Excel文件上传功能存在多个安全问题：
- 仅检查文件扩展名，未验证实际内容类型
- 缺少文件大小限制
- 文件名未经过安全处理，可能包含路径遍历字符
- 未设置允许的MIME类型白名单

#### 漏洞代码
```python
extensions = {"xlsx", "xls", "csv"}
if not file.filename.lower().endswith(tuple(extensions)):
    raise HTTPException(400, "Only support .xlsx/.xls/.csv")
# 仅通过扩展名验证，存在安全风险
```

#### 修复方案
```python
import magic
from pathlib import Path
import hashlib
import uuid

# 安全配置
ALLOWED_MIME_TYPES = {
    'application/vnd.ms-excel',           # .xls
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
    'text/csv',                           # .csv
    'application/csv'                     # .csv
}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

@router.post("/uploadExcelAndCreateDatasource", response_model=CoreDatasource)
async def upload_excel_and_create_datasource(
    session: SessionDep,
    trans: Trans,
    user: CurrentUser,
    file: UploadFile = File(...),
    example_size: int = Form(10),
    ai: bool = Form(False),
):
    # 1. 文件大小检查
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"文件大小超过限制 ({MAX_FILE_SIZE // (1024*1024)}MB)"
        )

    if len(file_content) == 0:
        raise HTTPException(400, detail="上传文件为空")

    # 2. 安全的文件名生成
    original_ext = Path(file.filename).suffix.lower()
    if original_ext not in {'.xlsx', '.xls', '.csv'}:
        raise HTTPException(400, detail="不支持的文件类型")

    # 生成安全的文件名（不含路径遍历字符）
    safe_filename = f"{hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:16]}{original_ext}"
    save_path = os.path.join(path, safe_filename)

    # 3. 内容类型验证
    try:
        file_type = magic.from_buffer(file_content, mime=True)
        if file_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                400,
                f"文件内容类型 ({file_type}) 与扩展名不匹配"
            )
    except Exception as e:
        raise HTTPException(400, detail="文件类型检测失败")

    # 4. 病毒扫描（可选）
    # if SCAN_VIRUS:
    #     if await scan_for_malware(file_content):
    #         raise HTTPException(400, detail="检测到恶意文件")

    # 5. 安全保存文件
    try:
        # 确保目录存在且权限正确
        os.makedirs(path, exist_ok=True)

        with open(save_path, "wb") as f:
            f.write(file_content)

        # 设置文件权限（只有用户可读写）
        os.chmod(save_path, 0o600)

    except Exception as e:
        # 清理可能创建的文件
        if os.path.exists(save_path):
            os.remove(save_path)
        raise HTTPException(500, detail="文件保存失败")

    # 继续原有逻辑...
```

#### 修复文件
- [ ] `backend/apps/openapi/openapi.py:551-579`
- [ ] 添加文件类型验证库依赖 (`python-magic`)

#### 依赖安装
```bash
# Ubuntu/Debian
sudo apt-get install libmagic1

# CentOS/RHEL
sudo yum install file-devel

# Python包
pip install python-magic
```

---

## 🟡 中危问题 (尽快修复)

### 3. 默认密码安全风险
**文件位置:** `backend/.env.example:11`
**风险等级:** 🟡 中危
**CVSS评分:** 6.8 (AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N)

#### 问题描述
示例配置文件中包含明文默认密码，容易在部署时被直接使用。

#### 当前问题
```bash
# .env.example
DEFAULT_PWD=SQLBot@123456  # 存在安全风险
```

#### 修复方案

##### 3.1 移除示例中的具体密码
```bash
# .env.example
DEFAULT_PWD=CHANGE_ME_IN_PRODUCTION  # 强制修改
```

##### 3.2 在应用启动时检查是否使用默认密码
```python
# backend/main.py 或 backend/common/core/config.py
def validate_security_config():
    """检查安全配置"""
    if settings.DEFAULT_PWD in ['SQLBot@123456', 'CHANGE_ME_IN_PRODUCTION', 'password', '123456']:
        raise RuntimeError(
            "检测到不安全的默认密码，请立即修改环境变量 DEFAULT_PWD"
        )

    if settings.SECRET_KEY == '52d67303b57c3ab74664bd9d83f254681a78204931f80036100b3f53321c1d8d':
        raise RuntimeError(
            "检测到默认的SECRET_KEY，请立即修改环境变量 SECRET_KEY"
        )

# 在应用启动时调用
validate_security_config()
```

##### 3.3 强制密码复杂度检查
```python
import re

def validate_password_complexity(password: str) -> bool:
    """验证密码复杂度"""
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    return True
```

#### 修复文件
- [ ] `backend/.env.example:11`
- [ ] `backend/main.py` (添加启动检查)
- [ ] `backend/common/core/config.py` (添加验证函数)

---

### 4. Token过期时间过长
**文件位置:** `backend/.env.example:27`
**风险等级:** 🟡 中危
**CVSS评分:** 6.3 (AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:N/A:N)

#### 问题描述
Token过期时间设置为11520分钟（8天），时间过长，增加token被滥用的风险。

#### 当前问题
```bash
# .env.example
ACCESS_TOKEN_EXPIRE_MINUTES=11520  # 8天，时间过长
```

#### 修复方案

##### 4.1 调整为合理时间
```bash
# .env.example
ACCESS_TOKEN_EXPIRE_MINUTES=240  # 4小时
# 或者更严格
ACCESS_TOKEN_EXPIRE_MINUTES=120  # 2小时
```

##### 4.2 实现Refresh Token机制
```python
# backend/common/core/security.py (新增)
from datetime import datetime, timedelta
import secrets

def create_refresh_token() -> str:
    """创建refresh token"""
    return secrets.token_urlsafe(32)

def create_tokens_with_refresh(user_dict: dict) -> tuple:
    """创建access token和refresh token"""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=30)  # refresh token有效期30天

    access_token = create_access_token(
        data=user_dict,
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token()

    return access_token, refresh_token
```

##### 4.3 添加token使用日志和监控
```python
# backend/apps/openapi/middleware/token_monitor.py
from fastapi import Request, Response
import time
from collections import defaultdict

class TokenMonitor:
    def __init__(self):
        self.token_usage = defaultdict(list)
        self.blocked_tokens = set()

    async def track_token_usage(self, token: str, user_id: int, ip: str):
        """跟踪token使用情况"""
        current_time = time.time()
        hour_key = int(current_time // 3600)  # 按小时分组

        self.token_usage[token].append({
            'timestamp': current_time,
            'hour_key': hour_key,
            'user_id': user_id,
            'ip': ip
        })

        # 检查是否异常使用
        recent_count = len([
            usage for usage in self.token_usage[token]
            if current_time - usage['timestamp'] < 300  # 5分钟内
        ])

        if recent_count > 100:  # 5分钟内超过100次请求
            # 可疑行为，记录并可能阻止
            self.blocked_tokens.add(token)
            await self.alert_suspicious_activity(token, user_id, ip, recent_count)

    async def alert_suspicious_activity(self, token, user_id, ip, count):
        """告警可疑活动"""
        from common.utils.utils import SQLBotLogUtil
        SQLBotLogUtil.warning(
            f"检测到可疑token使用: token={token[:10]}..., "
            f"user_id={user_id}, ip={ip}, 5分钟内请求次数={count}"
        )
```

#### 修复文件
- [ ] `backend/.env.example:27`
- [ ] `backend/common/core/security.py` (新增refresh token)
- [ ] `backend/apps/openapi/models/openapiModels.py` (添加refresh token字段)
- [ ] `backend/apps/openapi/openapi.py` (更新token生成逻辑)

---

### 5. 敏感信息泄露
**文件位置:** `backend/apps/openapi/service/openapi_db.py:218`
**风险等级:** 🟡 中危
**CVSS评分:** 5.9 (AV:N/AC:H/PR:N/UI:N/S:C/C:L/I:N/A:N)

#### 问题描述
错误处理时可能暴露敏感的数据库结构信息，给攻击者提供有用信息。

#### 当前问题
```python
except Exception as e:
    # 可能泄露敏感信息
    raise HTTPException(status_code=500, detail=f"Delete datasource failed: {e}")
```

#### 修复方案
```python
# backend/apps/openapi/service/openapi_db.py
import traceback
from common.utils.utils import SQLBotLogUtil

def delete_ds(session: SessionDep, id: int):
    try:
        # 业务逻辑...

    except HTTPException:
        # 已知的HTTP异常直接抛出
        raise

    except Exception as e:
        # 记录详细错误到日志
        error_id = f"DS_DELETE_{id}_{int(time.time())}"
        SQLBotLogUtil.error(
            f"[{error_id}] 删除数据源失败: {str(e)}\n{traceback.format_exc()}"
        )

        # 返回通用错误信息给客户端
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "DATASOURCE_DELETE_FAILED",
                "error_id": error_id,
                "message": "数据源删除失败，请联系系统管理员",
                "timestamp": datetime.now().isoformat()
            }
        ) from None
```

#### 修复文件
- [ ] `backend/apps/openapi/service/openapi_db.py`
- [ ] `backend/apps/openapi/openapi.py` (统一错误处理)
- [ ] `backend/apps/openapi/agent/chat_agent.py` (统一错误处理)
- [ ] `backend/apps/openapi/agent/plan_agent.py` (统一错误处理)

---

## 🟢 低危问题 (计划修复)

### 6. 输入验证语法错误
**文件位置:** `backend/apps/openapi/models/openapiModels.py:35`
**风险等级:** 🟢 低危
**CVSS评分:** 3.7 (AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N)

#### 问题描述
`OpenClean`模型中存在语法错误，可能导致数据验证问题。

#### 当前问题
```python
class OpenClean(BaseModel):
    chat_ids: Union[int, List[int]] = Body(  # 多了一个方括号
        None,
        description='会话标识或会话标识列表，为空时清理所有记录'
    )
```

#### 修复方案
```python
class OpenClean(BaseModel):
    chat_ids: Union[int, List[int]] = Body(  # 修复语法
        None,
        description='会话标识或会话标识列表，为空时清理所有记录'
    )

    def get_chat_ids(self) -> List[int]:
        """获取标准化的chat_id列表"""
        if isinstance(self.chat_ids, int):
            return [self.chat_ids]
        return self.chat_ids or []

    @field_validator('chat_ids', mode='before')
    @classmethod
    def validate_chat_ids(cls, v):
        """验证chat_ids字段"""
        if v is None:
            return None
        if isinstance(v, int):
            if v <= 0:
                raise ValueError("chat_id必须是正整数")
            return v
        if isinstance(v, list):
            if not v:
                return None
            if len(v) > 100:  # 限制批量操作数量
                raise ValueError("单次最多可清理100条记录")
            validated_ids = []
            for item in v:
                if not isinstance(item, int) or item <= 0:
                    raise ValueError("chat_id列表必须包含正整数")
                validated_ids.append(item)
            return validated_ids
        raise ValueError("chat_ids必须是整数或整数列表")
```

#### 修复文件
- [ ] `backend/apps/openapi/models/openapiModels.py:35`

---

### 7. 配置文件安全问题
**文件位置:** `backend/.env.example:14`
**风险等级:** 🟢 低危
**CVSS评分:** 3.2 (AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:N)

#### 问题描述
示例配置文件使用固定的SECRET_KEY，可能在部署时被直接使用。

#### 当前问题
```bash
# .env.example
SECRET_KEY=52d67303b57c3ab74664bd9d83f254681a78204931f80036100b3f53321c1d8d
```

#### 修复方案

##### 7.1 移除固定密钥
```bash
# .env.example
SECRET_KEY=GENERATE_NEW_SECRET_KEY_HERE
# 在部署时必须替换为安全的随机密钥

# 密钥生成命令（添加到文档中）
# openssl rand -hex 32
# 或者使用Python:
# python -c "import secrets; print(secrets.token_urlsafe(32))"
```

##### 7.2 启动时检查密钥强度
```python
# backend/common/core/config.py
import secrets

def validate_secret_key():
    """验证SECRET_KEY的安全性"""
    secret_key = settings.SECRET_KEY

    # 检查是否使用默认密钥
    default_keys = [
        '52d67303b57c3ab74664bd9d83f254681a78204931f80036100b3f53321c1d8d',
        'GENERATE_NEW_SECRET_KEY_HERE',
        'secret',
        'your-secret-key'
    ]

    if secret_key in default_keys:
        raise RuntimeError(
            "检测到不安全的SECRET_KEY，请生成新的密钥。"
            "使用命令: openssl rand -hex 32"
        )

    # 检查密钥长度
    if len(secret_key) < 32:
        raise RuntimeError("SECRET_KEY长度必须至少32个字符")

    # 检查密钥复杂度
    if secret_key.isalpha() or secret_key.isdigit() or secret_key.isalnum():
        raise RuntimeError(
            "SECRET_KEY应包含字母、数字和特殊字符的组合"
        )

# 在配置加载后验证
validate_secret_key()
```

##### 7.3 密钥轮换机制
```python
# backend/common/core/key_rotation.py
from datetime import datetime, timedelta
import json
import os

class KeyManager:
    def __init__(self):
        self.keys_file = os.path.join(os.getcwd(), 'keys.json')
        self.load_keys()

    def load_keys(self):
        """加载密钥"""
        try:
            with open(self.keys_file, 'r') as f:
                self.keys = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.keys = {
                'current': settings.SECRET_KEY,
                'previous': [],
                'rotation_date': datetime.now().isoformat()
            }

    def rotate_key(self):
        """轮换密钥"""
        old_key = self.keys['current']
        new_key = secrets.token_urlsafe(32)

        self.keys['previous'].append({
            'key': old_key,
            'valid_until': (datetime.now() + timedelta(days=1)).isoformat()
        })
        self.keys['current'] = new_key
        self.keys['rotation_date'] = datetime.now().isoformat()

        # 保持最多5个旧密钥
        if len(self.keys['previous']) > 5:
            self.keys['previous'] = self.keys['previous'][-5:]

        with open(self.keys_file, 'w') as f:
            json.dump(self.keys, f, indent=2)

        return new_key

    def verify_token_with_rotation(self, token: str):
        """支持密钥轮换的token验证"""
        # 尝试当前密钥
        try:
            return jwt.decode(token, self.keys['current'], algorithms=[ALGORITHM])
        except jwt.InvalidTokenError:
            pass

        # 尝试之前的密钥
        for prev_key_info in self.keys['previous']:
            try:
                payload = jwt.decode(
                    token,
                    prev_key_info['key'],
                    algorithms=[ALGORITHM]
                )
                # 检查是否还在有效期内
                valid_until = datetime.fromisoformat(prev_key_info['valid_until'])
                if datetime.now() < valid_until:
                    return payload
            except jwt.InvalidTokenError:
                continue

        raise jwt.InvalidTokenError("Invalid token")
```

#### 修复文件
- [ ] `backend/.env.example:14`
- [ ] `backend/common/core/config.py` (添加密钥验证)
- [ ] `backend/main.py` (添加启动检查)
- [ ] 创建 `backend/common/core/key_rotation.py` (密钥轮换机制)

---

## ✅ 安全最佳实践 (建议实施)

### 8. 添加安全HTTP头部
**风险等级:** 信息泄露
**实施优先级:** 高

#### 修复方案
```python
# backend/main.py
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # 添加安全头部
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'"
        )

        return response

# 应用中间件
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"]
)
app.add_middleware(SecurityHeadersMiddleware)

# 生产环境强制HTTPS
if settings.ENVIRONMENT == "production":
    app.add_middleware(HTTPSRedirectMiddleware)
```

#### 修复文件
- [ ] `backend/main.py` (添加安全中间件)

---

### 9. 实施API速率限制
**风险等级:** DoS攻击防护
**实施优先级:** 高

#### 修复方案
```python
# 安装依赖
# pip install slowapi

# backend/common/middleware/rate_limiter.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
import redis
import json

# 创建limiter实例
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL or "memory://",
    default_limits=["100/minute"]  # 默认每分钟100次请求
)

# 速率限制异常处理
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 在API端点上应用限制
@app.post("/openapi/getToken")
@limiter.limit("10/minute")  # 登录接口每分钟10次
async def get_token(request: Request, ...):
    pass

@app.post("/openapi/chat")
@limiter.limit("60/minute")  # 聊天接口每分钟60次
async def chat(request: Request, ...):
    pass

@app.post("/openapi/uploadExcelAndCreateDatasource")
@limiter.limit("5/minute")  # 上传接口每分钟5次
async def upload_file(request: Request, ...):
    pass

# 智能速率限制（基于用户ID）
@limiter.limit("1000/hour", key_func=lambda request: request.user.id if hasattr(request, 'user') else get_remote_address(request))
async def user_specific_api(request: Request, ...):
    pass
```

#### 修复文件
- [ ] `backend/requirements.txt` (添加slowapi依赖)
- [ ] `backend/common/middleware/rate_limiter.py` (新建)
- [ ] `backend/main.py` (配置速率限制)
- [ ] `backend/apps/openapi/openapi.py` (应用速率限制)

---

### 10. 增强安全日志记录
**风险等级:** 审计追踪
**实施优先级:** 中

#### 修复方案
```python
# backend/common/security/audit_logger.py
import structlog
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import Request

# 配置结构化日志
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

class SecurityAuditLogger:
    def __init__(self):
        self.logger = logger.bind(security=True)

    def log_authentication_event(
        self,
        username: str,
        success: bool,
        ip_address: str,
        user_agent: str,
        user_id: Optional[int] = None
    ):
        """记录认证事件"""
        self.logger.info(
            "security.authentication",
            username=username,
            success=success,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.now().isoformat()
        )

    def log_authorization_event(
        self,
        user_id: int,
        resource: str,
        action: str,
        success: bool,
        ip_address: str,
        reason: Optional[str] = None
    ):
        """记录授权事件"""
        self.logger.info(
            "security.authorization",
            user_id=user_id,
            resource=resource,
            action=action,
            success=success,
            ip_address=ip_address,
            reason=reason,
            timestamp=datetime.now().isoformat()
        )

    def log_data_access_event(
        self,
        user_id: int,
        datasource_id: int,
        query: str,
        ip_address: str
    ):
        """记录数据访问事件"""
        self.logger.info(
            "security.data_access",
            user_id=user_id,
            datasource_id=datasource_id,
            query_hash=hashlib.sha256(query.encode()).hexdigest(),  # 记录hash而非明文
            ip_address=ip_address,
            timestamp=datetime.now().isoformat()
        )

    def log_file_upload_event(
        self,
        user_id: int,
        filename: str,
        file_size: int,
        file_type: str,
        success: bool,
        ip_address: str,
        threat_detected: Optional[str] = None
    ):
        """记录文件上传事件"""
        self.logger.info(
            "security.file_upload",
            user_id=user_id,
            filename=filename,
            file_size=file_size,
            file_type=file_type,
            success=success,
            ip_address=ip_address,
            threat_detected=threat_detected,
            timestamp=datetime.now().isoformat()
        )

    def log_suspicious_activity(
        self,
        description: str,
        severity: str,  # low, medium, high, critical
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """记录可疑活动"""
        self.logger.warning(
            "security.suspicious_activity",
            description=description,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            details=details,
            timestamp=datetime.now().isoformat()
        )

# 创建全局审计日志实例
audit_logger = SecurityAuditLogger()

# 中间件集成
class SecurityAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = datetime.now()

        response = await call_next(request)

        # 记录安全相关事件
        if request.url.path.startswith("/openapi/"):
            user_id = getattr(request.state, 'user_id', None)
            ip_address = request.client.host
            user_agent = request.headers.get("user-agent", "")

            # 记录API访问
            if response.status_code == 401:
                audit_logger.log_authentication_event(
                    username=request.headers.get("X-Sqlbot-Token", "unknown"),
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            elif response.status_code == 403:
                audit_logger.log_authorization_event(
                    user_id=user_id or 0,
                    resource=request.url.path,
                    action=request.method,
                    success=False,
                    ip_address=ip_address,
                    reason="权限不足"
                )

        return response
```

#### 修复文件
- [ ] `backend/requirements.txt` (添加structlog依赖)
- [ ] `backend/common/security/audit_logger.py` (新建)
- [ ] `backend/main.py` (添加审计中间件)
- [ ] 在各个API端点中添加审计日志调用

---

### 11. 数据库连接安全加固
**风险等级:** 数据库安全
**实施优先级:** 中

#### 修复方案
```python
# backend/common/core/database_security.py
from sqlalchemy import create_engine, event
from sqlalchemy.pool import QueuePool
import ssl

def create_secure_database_url() -> str:
    """创建安全的数据库连接URL"""
    db_config = {
        'username': settings.POSTGRES_USER,
        'password': settings.POSTGRES_PASSWORD,
        'host': settings.POSTGRES_SERVER,
        'port': settings.POSTGRES_PORT,
        'database': settings.POSTGRES_DB
    }

    # 基础连接字符串
    base_url = (
        f"postgresql+psycopg2://{db_config['username']}:{db_config['password']}"
        f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    )

    # 添加安全参数
    secure_params = {
        'sslmode': 'require',  # 强制SSL连接
        'sslcert': '/path/to/client-cert.pem',
        'sslkey': '/path/to/client-key.pem',
        'sslrootcert': '/path/to/ca-cert.pem',
        'connect_timeout': 10,
        'application_name': 'sqlbot_secure',
        'ssl_min_protocol_version': 'TLSv1.2'
    }

    return base_url + '?' + '&'.join([f"{k}={v}" for k, v in secure_params.items() if v])

def create_secure_engine():
    """创建安全的数据库引擎"""
    engine = create_engine(
        create_secure_database_url(),
        poolclass=QueuePool,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
        pool_recycle=3600,  # 1小时回收连接
        echo=settings.SQL_DEBUG,
        connect_args={
            'connect_timeout': 10,
            'application_name': 'sqlbot_secure',
            'options': '-c statement_timeout=300000ms'  # 5分钟查询超时
        }
    )

    # 添加连接事件监听器
    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_connection, connection_record):
        """数据库连接建立时的安全设置"""
        with dbapi_connection.cursor() as cursor:
            # 设置会话安全参数
            cursor.execute("SET SESSION statement_timeout = '5min'")
            cursor.execute("SET SESSION idle_in_transaction_session_timeout = '1min'")
            cursor.execute("SET SESSION lock_timeout = '2min'")
            cursor.execute("SET SESSION row_security = ON")  # 启用行级安全

    return engine

# 数据库权限配置
DB_PERMISSIONS = {
    'readonly_user': {
        'SELECT': True,
        'INSERT': False,
        'UPDATE': False,
        'DELETE': False,
        'CREATE': False,
        'DROP': False
    },
    'readwrite_user': {
        'SELECT': True,
        'INSERT': True,
        'UPDATE': True,
        'DELETE': False,
        'CREATE': False,
        'DROP': False
    },
    'admin_user': {
        'SELECT': True,
        'INSERT': True,
        'UPDATE': True,
        'DELETE': True,
        'CREATE': True,
        'DROP': True
    }
}

def create_secure_user_sql(username: str, permissions: dict) -> list:
    """生成创建安全用户的SQL语句"""
    password = secrets.token_urlsafe(16)

    statements = [
        f"CREATE USER {username} WITH PASSWORD '{password}';",
        f"REVOKE ALL ON SCHEMA public FROM {username};",
        f"GRANT CONNECT ON DATABASE {settings.POSTGRES_DB} TO {username};"
    ]

    if permissions.get('SELECT'):
        statements.append(f"GRANT USAGE ON SCHEMA public TO {username};")

    if permissions.get('SELECT') and not permissions.get('INSERT') and not permissions.get('UPDATE') and not permissions.get('DELETE'):
        # 只读用户
        statements.extend([
            f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {username};",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {username};"
        ])
    elif permissions.get('INSERT') or permissions.get('UPDATE'):
        # 读写用户（不含删除）
        statements.extend([
            f"GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO {username};",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE ON TABLES TO {username};"
        ])

    return statements, password
```

#### 修复文件
- [ ] `backend/common/core/database_security.py` (新建)
- [ ] `backend/common/core/config.py` (更新数据库连接配置)
- [ ] `backend/common/core/db.py` (使用安全引擎)
- [ ] 数据库安全配置脚本

---

## 📋 修复计划和时间表

### 第一阶段：紧急修复 (1-2周)
| 任务 | 优先级 | 预计时间 | 负责人 | 依赖 |
|------|--------|----------|--------|------|
| 修复SQL注入防护 | 🔴 P0 | 3天 | 开发团队 | 无 |
| 加强文件上传验证 | 🔴 P0 | 2天 | 开发团队 | python-magic库 |
| 修复输入验证语法错误 | 🟢 P2 | 半天 | 开发团队 | 无 |
| 移除默认密码示例 | 🟡 P1 | 1天 | 开发团队 | 无 |

### 第二阶段：安全加固 (2-3周)
| 任务 | 优先级 | 预计时间 | 负责人 | 依赖 |
|------|--------|----------|--------|------|
| 实施安全HTTP头部 | ✅ P1 | 1天 | 开发团队 | 第一阶段完成 |
| 缩短token过期时间 | 🟡 P1 | 2天 | 开发团队 | 前端配合 |
| 统一错误处理 | 🟡 P1 | 3天 | 开发团队 | 无 |
| 实施API速率限制 | ✅ P1 | 2天 | 开发团队 | Redis环境 |

### 第三阶段：监控和审计 (3-4周)
| 任务 | 优先级 | 预计时间 | 负责人 | 依赖 |
|------|--------|----------|--------|------|
| 增强安全日志记录 | ✅ P2 | 3天 | 开发团队 | ELK环境 |
| 数据库连接安全加固 | ✅ P2 | 2天 | DBA | 无 |
| 配置文件安全加固 | 🟢 P2 | 1天 | 运维团队 | 无 |

### 第四阶段：高级特性 (4-6周)
| 任务 | 优先级 | 预计时间 | 负责人 | 依赖 |
|------|--------|----------|--------|------|
| 实施Refresh Token | 🟡 P2 | 5天 | 开发团队 | 第二阶段完成 |
| 密钥轮换机制 | 🟢 P3 | 3天 | 开发团队 | 第三阶段完成 |
| token使用监控 | 🟡 P2 | 4天 | 开发团队 | 第三阶段完成 |

---

## 🔧 部署和验证清单

### 修复验证测试
- [ ] 所有高危问题修复后进行回归测试
- [ ] 使用OWASP ZAP或Burp Suite进行安全扫描
- [ ] 进行渗透测试验证
- [ ] 性能测试确保安全措施不影响正常使用

### 部署检查
- [ ] 备份生产环境数据
- [ ] 在测试环境验证所有修复
- [ ] 更新部署脚本和配置
- [ ] 监控部署后的系统性能和错误率
- [ ] 验证日志记录正常工作

### 文档更新
- [ ] 更新API文档（错误码变更）
- [ ] 更新部署指南（安全配置要求）
- [ ] 更新运维手册（监控指标）
- [ ] 创建安全响应流程文档

---

## 📞 联系方式

如有关于安全问题的疑问，请联系：
- **安全团队**: security@yourcompany.com
- **开发团队**: dev-team@yourcompany.com
- **紧急安全事件**: security-emergency@yourcompany.com

---

## 📝 变更记录

| 日期 | 版本 | 变更内容 | 作者 |
|------|------|----------|------|
| 2025-11-27 | 1.0 | 初始版本，完成安全扫描 | 安全团队 |

---

*本文档应定期审查和更新，确保安全措施持续有效。*