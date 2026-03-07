# 元数据探查技能

本技能提供数据库元数据探查的完整解决方案，支持多种数据库类型的表结构、字段信息、索引、外键等元数据的自动发现与查询。通过统一的接口设计，AI 可以轻松获取任意数据源的 schema 信息，为后续的 SQL 生成、数据分析提供基础支撑。

## 技能概述

元数据探查是数据库应用开发中的基础能力，它帮助开发者快速了解数据库的结构组成，掌握表与字段的详细信息。本技能封装了 11 种主流数据库的元数据查询逻辑，包括关系型数据库、OLAP 数据库以及全文检索引擎，每种数据库都使用其原生的系统表或信息 Schema 进行查询，确保获取到的信息准确完整。技能提供四个核心功能：数据库连接测试、Schema 列表获取、表列表获取以及字段信息获取，这四个功能覆盖了元数据探查的完整生命周期。

在实际应用中，元数据探查常用于以下场景：数据库迁移时需要了解源库结构、数据治理时需要梳理企业数据资产、BI 报表开发时需要关联多表数据、SQL 生成时需要获取表结构上下文。技能设计时充分考虑了这些场景的需求，提供了灵活的参数配置和丰富的返回信息，让 AI 能够根据探查结果做出准确的判断和决策。

## 支持的数据库类型

本技能支持以下数据库类型的元数据探查，每种数据库都经过专门适配，使用其最佳实践进行元数据获取：

| 数据库类型 | 类型标识 | 连接方式 | 说明 |
|-----------|---------|---------|------|
| MySQL | mysql | SQLAlchemy | 使用 information_schema 系统库 |
| PostgreSQL | pg | SQLAlchemy | 使用 pg_catalog 系统目录 |
| Oracle | oracle | SQLAlchemy | 使用 ALL_* 数据字典视图 |
| SQL Server | sqlServer | SQLAlchemy | 使用 sys 系统视图 |
| ClickHouse | ck | SQLAlchemy | 使用 system 系统库 |
| Excel/CSV | excel | SQLAlchemy | 使用 SQLAlchemy 反射机制 |
| 达梦 | dm | Python 驱动 (dmPython) | 使用 ALL_TAB_* 数据字典 |
| StarRocks | doris | Python 驱动 (pymysql) | 使用 information_schema |
| Doris | starrocks | Python 驱动 (pymysql) | 使用 information_schema |
| Redshift | redshift | Python 驱动 (redshift_connector) | 使用 pg_catalog 目录 |
| Kingbase | kingbase | Python 驱动 (psycopg2) | 使用 pg_catalog 目录 |
| Elasticsearch | es | REST API | 使用 _mapping 端点 |

## 核心数据结构

在执行元数据探查之前，需要了解几个核心数据结构。这些数据结构定义了探查结果的标准化格式，使得 AI 可以用统一的方式处理不同数据库的探查结果。

数据源配置类 `DatasourceConf` 用于存储连接数据库所需的所有配置信息，包括主机地址、端口号、用户名密码、数据库名称、Schema 名称等关键字段。该类还支持额外的 JDBC 参数配置，可以灵活应对各种特殊的连接需求。配置类采用 Pydantic 模型定义，具备自动类型验证和默认值填充能力，在实际使用中可以有效避免配置错误导致的连接失败问题。

表结构类 `TableSchema` 用于存储表的元数据信息，包含表名和表注释两个核心字段。在不同数据库中，表名的获取来源各不相同：MySQL 来自 information_schema.TABLES 表，PostgreSQL 来自 pg_class 系统目录，Oracle 来自 ALL_TABLES 视图。表注释的获取方式也因数据库而异，但统一通过该类进行封装，返回给调用者。`ColumnSchema` 类则用于存储字段的元数据信息，包含字段名、字段类型和字段注释三个字段，这三个字段是描述字段结构的最基本信息，足以支撑大部分 SQL 生成场景的需求。

```python
# 数据源配置类 - 定义数据库连接的所有必要参数
class DatasourceConf(BaseModel):
    host: str = ''           # 数据库主机地址
    port: int = 0            # 数据库端口号
    username: str = ''        # 连接用户名
    password: str = ''       # 连接密码
    database: str = ''       # 数据库名称
    driver: str = ''         # JDBC 驱动类名
    extraJdbc: str = ''      # 额外的 JDBC 连接参数
    dbSchema: str = ''       # Schema 名称（部分数据库使用）
    filename: str = ''       # 文件名（Excel/CSV 数据源使用）
    sheets: List = ''        # 工作表列表（Excel 数据源使用）
    mode: str = ''           # 连接模式（Oracle 使用，如 service_name）
    timeout: int = 30        # 连接超时时间（秒）

# 表结构类 - 存储表级别的元数据
class TableSchema:
    def __init__(self, attr1, attr2):
        self.tableName = attr1                    # 表名
        self.tableComment = attr2                # 表注释/说明

    tableName: str        # 表的名称
    tableComment: str     # 表的业务含义说明

# 字段结构类 - 存储字段级别的元数据
class ColumnSchema:
    def __init__(self, attr1, attr2, attr3):
        self.fieldName = attr1                   # 字段名
        self.fieldType = attr2                   # 字段类型
        self.fieldComment = attr3                # 字段注释

    fieldName: str       # 字段的名称
    fieldType: str       # 字段的数据类型
    fieldComment: str    # 字段的业务含义说明
```

## 数据库连接管理

数据库连接是元数据探查的前提条件，连接质量直接影响探查的效率和成功率。本技能采用两种连接模式：SQLAlchemy 模式用于标准的关系型数据库，原生 Python 驱动模式用于需要特殊处理的数据库。连接管理类负责根据数据源类型选择合适的连接方式，构建正确的连接字符串，并处理连接过程中的各种异常情况。

连接字符串的构建是连接管理的核心任务。不同数据库的连接字符串格式差异较大，MySQL 使用 mysql+pymysql:// 前缀，PostgreSQL 使用 postgresql+psycopg2:// 前缀，Oracle 则需要根据连接模式（service_name 或 SID）选择不同的格式。构建时需要对用户名和密码进行 URL 编码，以处理包含特殊字符的情况。此外，额外的 JDBC 参数可以通过 extraJdbc 字段配置，这些参数会以查询参数的形式追加到连接字符串末尾。

连接测试功能用于验证数据库连接是否正常，这在数据源配置阶段非常重要。测试连接时使用较短的超时时间（通常 10 秒），避免因网络问题导致长时间等待。测试结果会返回布尔值表示连接是否成功，如果连接失败还会记录详细的错误信息，帮助开发者定位问题原因。

```python
# 连接类型枚举 - 区分两种连接模式
class ConnectType(Enum):
    sqlalchemy = 'sqlalchemy'    # 使用 SQLAlchemy 引擎连接
    py_driver = 'py_driver'      # 使用原生 Python 驱动连接

# 数据库类型枚举 - 定义所有支持的数据库
class DB(Enum):
    mysql = ('mysql', 'MySQL', '`', '`', ConnectType.sqlalchemy, 'MySQL')
    pg = ('pg', 'PostgreSQL', '"', '"', ConnectType.sqlalchemy, 'PostgreSQL')
    oracle = ('oracle', 'Oracle', '"', '"', ConnectType.sqlalchemy, 'Oracle')
    sqlServer = ('sqlServer', 'SQL Server', '[', ']', ConnectType.sqlalchemy, 'Microsoft_SQL_Server')
    ck = ('ck', 'ClickHouse', '"', '"', ConnectType.sqlalchemy, 'ClickHouse')
    doris = ('doris', 'Doris', '`', '`', ConnectType.py_driver, 'Doris')
    starrocks = ('starrocks', 'StarRocks', '`', '`', ConnectType.py_driver, 'StarRocks')
    dm = ('dm', '达梦', '"', '"', ConnectType.py_driver, 'DM')
    redshift = ('redshift', 'Redshift', '"', '"', ConnectType.py_driver, 'AWS_Redshift')
    kingbase = ('kingbase', 'Kingbase', '"', '"', ConnectType.py_driver, 'Kingbase')
    es = ('es', 'Elasticsearch', '"', '"', ConnectType.py_driver, 'Elasticsearch')
    excel = ('excel', 'Excel', '"', '"', ConnectType.sqlalchemy, 'PostgreSQL')

# 根据配置类型获取数据库枚举
def get_db(type: str) -> DB:
    for db in DB:
        if equals_ignore_case(db.type, type):
            return db
    raise ValueError(f"不支持的数据库类型: {type}")

# 从数据源对象构建连接 URI
def get_uri(ds: CoreDatasource) -> str:
    """根据数据源类型和配置构建数据库连接 URI"""
    conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration)))
    return get_uri_from_config(ds.type, conf)

# 根据数据库类型构建连接字符串
def get_uri_from_config(type: str, conf: DatasourceConf) -> str:
    """根据数据库类型生成对应的 SQLAlchemy 连接 URI"""
    if equals_ignore_case(type, "mysql"):
        # MySQL 连接字符串格式
        db_url = f"mysql+pymysql://{quote(conf.username)}:{quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}"
    elif equals_ignore_case(type, "pg"):
        # PostgreSQL 连接字符串格式
        db_url = f"postgresql+psycopg2://{quote(conf.username)}:{quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}"
    elif equals_ignore_case(type, "sqlServer"):
        # SQL Server 连接字符串格式
        db_url = f"mssql+pymssql://{quote(conf.username)}:{quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}"
    elif equals_ignore_case(type, "oracle"):
        # Oracle 连接需要根据模式选择 service_name 或 SID
        if equals_ignore_case(conf.mode, "service_name"):
            db_url = f"oracle+oracledb://{quote(conf.username)}:{quote(conf.password)}@{conf.host}:{conf.port}?service_name={conf.database}"
        else:
            db_url = f"oracle+oracledb://{quote(conf.username)}:{quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}"
    elif equals_ignore_case(type, "ck"):
        # ClickHouse 连接字符串格式
        db_url = f"clickhouse+http://{quote(conf.username)}:{quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}"
    else:
        raise ValueError(f"不支持的数据库类型: {type}")
    return db_url

# 获取数据库连接引擎
def get_engine(ds: CoreDatasource, timeout: int = 0) -> Engine:
    """创建 SQLAlchemy 引擎对象，支持超时配置"""
    conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration)))
    if conf.timeout is None:
        conf.timeout = timeout
    if timeout > 0:
        conf.timeout = timeout

    # 不同数据库使用不同的连接参数
    if equals_ignore_case(ds.type, "pg"):
        # PostgreSQL 需要设置 search_path
        engine = create_engine(
            get_uri(ds),
            connect_args={
                "options": f"-c search_path={quote(conf.dbSchema)}",
                "connect_timeout": conf.timeout
            },
            pool_timeout=conf.timeout
        )
    elif equals_ignore_case(ds.type, 'sqlServer'):
        # SQL Server 使用自定义连接函数
        engine = create_engine(
            'mssql+pymssql://',
            creator=lambda: get_origin_connect(ds.type, conf),
            pool_timeout=conf.timeout
        )
    else:
        # 其他数据库使用标准连接
        engine = create_engine(
            get_uri(ds),
            connect_args={"connect_timeout": conf.timeout},
            pool_timeout=conf.timeout
        )
    return engine

# 获取数据库会话
def get_session(ds: CoreDatasource):
    """获取数据库会话对象，用于执行查询"""
    engine = get_engine(ds)
    session_maker = sessionmaker(bind=engine)
    return session_maker()

# 测试数据库连接
def check_connection(ds: CoreDatasource, is_raise: bool = False) -> bool:
    """测试数据库连接是否正常"""
    db = DB.get_db(ds.type)
    if db.connect_type == ConnectType.sqlalchemy:
        conn = get_engine(ds, 10)
        try:
            with conn.connect() as connection:
                return True
        except Exception as e:
            if is_raise:
                raise HTTPException(status_code=500, detail=f'数据库连接失败: {e}')
            return False
    else:
        # 原生驱动连接测试
        conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration)))
        if equals_ignore_case(ds.type, 'doris', 'starrocks'):
            with pymysql.connect(
                user=conf.username, passwd=conf.password, host=conf.host,
                port=conf.port, db=conf.database, connect_timeout=10
            ) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('select 1')
                    return True
        # 其他原生驱动的连接测试类似
        return False
```

## 获取数据库版本

数据库版本信息在元数据探查中具有重要作用，某些 SQL 查询需要根据版本差异进行调整。不同数据库获取版本的方式各不相同：MySQL 直接执行 SELECT VERSION()，PostgreSQL 查询 current_setting('server_version')，Oracle 则查询 v$instance 视图，SQL Server 使用 SERVERPROPERTY 函数。本技能将各数据库的版本查询 SQL 封装在 `get_version_sql` 函数中，对外提供统一的调用接口。

```python
# 获取数据库版本的 SQL 查询
def get_version_sql(ds: CoreDatasource, conf: DatasourceConf):
    """根据数据库类型返回获取版本的 SQL"""
    if equals_ignore_case(ds.type, "mysql", "doris", "starrocks"):
        return "SELECT VERSION()"
    elif equals_ignore_case(ds.type, "sqlServer"):
        return "SELECT SERVERPROPERTY('ProductVersion')"
    elif equals_ignore_case(ds.type, "pg", "kingbase", "excel"):
        return "SELECT current_setting('server_version')"
    elif equals_ignore_case(ds.type, "oracle"):
        return "SELECT version FROM v$instance"
    elif equals_ignore_case(ds.type, "ck"):
        return "SELECT version()"
    elif equals_ignore_case(ds.type, "dm"):
        return "SELECT * FROM v$version"
    elif equals_ignore_case(ds.type, "redshift"):
        return ''  # Redshift 不支持版本查询

# 执行版本查询
def get_version(ds: CoreDatasource) -> str:
    """获取数据库版本号"""
    conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration)))
    sql = get_version_sql(ds, conf)
    db = DB.get_db(ds.type)

    try:
        if db.connect_type == ConnectType.sqlalchemy:
            with get_session(ds) as session:
                with session.execute(text(sql)) as result:
                    version = result.fetchall()[0][0]
        else:
            # 原生驱动的版本查询
            if equals_ignore_case(ds.type, 'doris', 'starrocks'):
                with pymysql.connect(
                    user=conf.username, passwd=conf.password, host=conf.host,
                    port=conf.port, db=conf.database, connect_timeout=10
                ) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(sql)
                        version = cursor.fetchall()[0][0]
        return version.decode() if isinstance(version, bytes) else version
    except Exception as e:
        return ''
```

## 获取 Schema 列表

Schema 是数据库对象的命名空间，不同数据库对 Schema 的支持和使用方式不同。PostgreSQL 和 Redshift 强制使用 Schema，MySQL 的 Schema 概念弱化为数据库本身，SQL Server 的 Schema 是独立于数据库的对象命名空间，Oracle 则使用用户（OWNER）作为 Schema 的等价概念。本技能通过 `get_schema` 函数屏蔽这些差异，向上层提供统一的 Schema 列表获取能力。

获取 Schema 列表的 SQL 各有特点：PostgreSQL 查询 pg_namespace 系统表，SQL Server 查询 sys.schemas 系统视图，Oracle 查询 all_users 视图（因为 Oracle 中用户与 Schema 一一对应）。在处理返回结果时，需要将元组列表转换为字符串列表，方便上层调用者使用。

```python
# 获取数据库 Schema 列表
def get_schema(ds: CoreDatasource) -> List[str]:
    """获取数据库中的所有 Schema 名称"""
    conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration)))
    db = DB.get_db(ds.type)

    if db.connect_type == ConnectType.sqlalchemy:
        with get_session(ds) as session:
            sql = ''
            if equals_ignore_case(ds.type, "sqlServer"):
                sql = "SELECT name FROM sys.schemas"
            elif equals_ignore_case(ds.type, "pg", "excel"):
                sql = "SELECT nspname FROM pg_namespace"
            elif equals_ignore_case(ds.type, "oracle"):
                sql = "SELECT username FROM all_users"

            with session.execute(text(sql)) as result:
                res = result.fetchall()
                return [item[0] for item in res]
    else:
        # 原生驱动的 Schema 查询
        if equals_ignore_case(ds.type, 'dm'):
            with dmPython.connect(
                user=conf.username, password=conf.password,
                server=conf.host, port=conf.port
            ) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT OBJECT_NAME FROM dba_objects WHERE object_type='SCHEMA'")
                    return [item[0] for item in cursor.fetchall()]
        elif equals_ignore_case(ds.type, 'redshift'):
            with redshift_connector.connect(
                host=conf.host, port=conf.port, database=conf.database,
                user=conf.username, password=conf.password
            ) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT nspname FROM pg_namespace")
                    return [item[0] for item in cursor.fetchall()]
```

## 获取表列表

表列表获取是元数据探查的核心功能之一，它返回指定 Schema 下的所有表及其注释信息。不同数据库查询表列表的 SQL 差异较大，主要体现在系统表的选择和过滤条件的设置上。MySQL 使用 information_schema.TABLES，PostgreSQL 使用 pg_class 配合 pg_namespace 和 pg_description，Oracle 使用 ALL_TABLES、ALL_VIEWS 和 ALL_MVIEWS 的联合查询。

在查询表列表时，需要注意以下几点：过滤掉系统表（如 PostgreSQL 的 pg_*、sql_* 前缀的表），正确处理视图和物化视图的区分，获取准确的表注释信息。部分数据库（如 ClickHouse）的版本差异也会影响 SQL 的写法，22 版本之前不支持 comment 字段。

```python
# 获取表列表的 SQL（按数据库类型封装）
def get_table_sql(ds: CoreDatasource, conf: DatasourceConf, db_version: str = ''):
    """根据数据库类型返回获取表列表的 SQL 和参数"""

    if equals_ignore_case(ds.type, "mysql"):
        # MySQL: 从 information_schema 获取表信息
        return """
            SELECT TABLE_NAME, TABLE_COMMENT
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = :param
        """, conf.database

    elif equals_ignore_case(ds.type, "sqlServer"):
        # SQL Server: 联合 extended_properties 获取注释
        return """
            SELECT t.TABLE_NAME, ISNULL(ep.value, '') AS TABLE_COMMENT
            FROM INFORMATION_SCHEMA.TABLES t
            LEFT JOIN sys.extended_properties ep
                ON ep.major_id = OBJECT_ID(t.TABLE_SCHEMA + '.' + t.TABLE_NAME)
                AND ep.minor_id = 0 AND ep.name = 'MS_Description'
            WHERE t.TABLE_TYPE IN ('BASE TABLE', 'VIEW')
                AND t.TABLE_SCHEMA = :param
        """, conf.dbSchema

    elif equals_ignore_case(ds.type, "pg", "excel"):
        # PostgreSQL: 使用 pg_class 和 pg_description
        return """
            SELECT c.relname AS TABLE_NAME,
                   COALESCE(d.description, obj_description(c.oid)) AS TABLE_COMMENT
            FROM pg_class c
            LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
            LEFT JOIN pg_description d ON d.objoid = c.oid AND d.objsubid = 0
            WHERE n.nspname = :param
                AND c.relkind IN ('r', 'v', 'p', 'm')
                AND c.relname NOT LIKE 'pg_%'
                AND c.relname NOT LIKE 'sql_%'
            ORDER BY c.relname
        """, conf.dbSchema

    elif equals_ignore_case(ds.type, "oracle"):
        # Oracle: 联合 ALL_TABLES、ALL_VIEWS、ALL_MVIEWS
        return """
            SELECT t.TABLE_NAME, NVL(c.COMMENTS, '') AS TABLE_COMMENT
            FROM (
                SELECT TABLE_NAME, 'TABLE' AS OBJECT_TYPE FROM ALL_TABLES WHERE OWNER = :param
                UNION ALL
                SELECT VIEW_NAME, 'VIEW' AS OBJECT_TYPE FROM ALL_VIEWS WHERE OWNER = :param
                UNION ALL
                SELECT MVIEW_NAME, 'MATERIALIZED VIEW' AS OBJECT_TYPE FROM ALL_MVIEWS WHERE OWNER = :param
            ) t
            LEFT JOIN ALL_TAB_COMMENTS c
                ON t.TABLE_NAME = c.TABLE_NAME AND c.OWNER = :param
            ORDER BY t.TABLE_NAME
        """, conf.dbSchema

    elif equals_ignore_case(ds.type, "ck"):
        # ClickHouse: 根据版本选择不同的字段
        version = int(db_version.split('.')[0]) if db_version else 0
        if version < 22:
            return """
                SELECT name, NULL AS comment
                FROM system.tables
                WHERE database = :param AND engine NOT IN ('Dictionary')
                ORDER BY name
            """, conf.database
        else:
            return """
                SELECT name, comment
                FROM system.tables
                WHERE database = :param AND engine NOT IN ('Dictionary')
                ORDER BY name
            """, conf.database

    elif equals_ignore_case(ds.type, "dm"):
        # 达梦: 使用 all_tab_comments
        return """
            SELECT table_name, comments
            FROM all_tab_comments
            WHERE owner = :param AND (table_type = 'TABLE' OR table_type = 'VIEW')
        """, conf.dbSchema

    elif equals_ignore_case(ds.type, "doris", "starrocks"):
        # Doris/StarRocks: 使用 information_schema
        return """
            SELECT TABLE_NAME, TABLE_COMMENT
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s
        """, conf.database

    elif equals_ignore_case(ds.type, "redshift"):
        # Redshift: 使用 pg_class
        return """
            SELECT relname AS TableName,
                   obj_description(relfilenode::regclass, 'pg_class') AS TableDescription
            FROM pg_class
            WHERE relkind IN ('r', 'p', 'f')
                AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = %s)
        """, conf.dbSchema

    elif equals_ignore_case(ds.type, "es"):
        # Elasticsearch: 无表概念，返回空
        return "", None

# 执行表列表查询
def get_tables(ds: CoreDatasource) -> List[TableSchema]:
    """获取指定数据源的所有表信息"""
    conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration)))
    db = DB.get_db(ds.type)
    sql, sql_param = get_table_sql(ds, conf, get_version(ds))

    if db.connect_type == ConnectType.sqlalchemy:
        with get_session(ds) as session:
            with session.execute(text(sql), {"param": sql_param}) as result:
                res = result.fetchall()
                return [TableSchema(*item) for item in res]
    else:
        # 原生驱动的查询
        if equals_ignore_case(ds.type, 'doris', 'starrocks'):
            with pymysql.connect(
                user=conf.username, passwd=conf.password, host=conf.host,
                port=conf.port, db=conf.database, connect_timeout=conf.timeout
            ) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (sql_param,))
                    return [TableSchema(*item) for item in cursor.fetchall()]
```

## 获取字段信息

字段信息获取是元数据探查中最细致的功能，它需要返回每个字段的名称、类型和注释。这些信息对于 SQL 生成至关重要，特别是字段类型的准确性直接影响生成 SQL 的兼容性。不同数据库查询字段信息的来源不同：MySQL 使用 information_schema.COLUMNS，PostgreSQL 使用 pg_attribute 和 pg_catalog.format_type，Oracle 使用 ALL_TAB_COLUMNS 并需要特殊处理 NUMBER 类型的精度。

在查询字段信息时，可以指定 table_name 参数来获取特定表的字段，也可以不指定来获取该 Schema 下所有表的字段。后者在需要生成全局数据字典时非常有用。返回的字段类型需要特别注意：Oracle 的 NUMBER 类型需要包含精度信息，VARCHAR2 需要包含长度信息，这些细节都需要在 SQL 中处理。

```python
# 获取字段信息的 SQL（按数据库类型封装）
def get_field_sql(ds: CoreDatasource, conf: DatasourceConf, table_name: str = None):
    """根据数据库类型返回获取字段信息的 SQL 和参数"""

    if equals_ignore_case(ds.type, "mysql"):
        # MySQL: 从 information_schema.COLUMNS 获取
        sql1 = """
            SELECT COLUMN_NAME, DATA_TYPE, COLUMN_COMMENT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = :param1
        """
        sql2 = " AND TABLE_NAME = :param2" if table_name else ""
        return sql1 + sql2, conf.database, table_name

    elif equals_ignore_case(ds.type, "sqlServer"):
        # SQL Server: 联合 sys.extended_properties 获取字段注释
        sql1 = """
            SELECT C.COLUMN_NAME, C.DATA_TYPE, ISNULL(EP.value, '') AS COLUMN_COMMENT
            FROM INFORMATION_SCHEMA.COLUMNS C
            LEFT JOIN sys.extended_properties EP
                ON EP.major_id = OBJECT_ID(C.TABLE_SCHEMA + '.' + C.TABLE_NAME)
                AND EP.minor_id = C.ORDINAL_POSITION
                AND EP.name = 'MS_Description'
            WHERE C.TABLE_SCHEMA = :param1
        """
        sql2 = " AND C.TABLE_NAME = :param2" if table_name else ""
        return sql1 + sql2, conf.dbSchema, table_name

    elif equals_ignore_case(ds.type, "pg", "excel"):
        # PostgreSQL: 使用 pg_attribute 和 format_type
        sql1 = """
            SELECT a.attname AS COLUMN_NAME,
                   pg_catalog.format_type(a.atttypid, a.atttypmod) AS DATA_TYPE,
                   col_description(c.oid, a.attnum) AS COLUMN_COMMENT
            FROM pg_catalog.pg_attribute a
            JOIN pg_catalog.pg_class c ON a.attrelid = c.oid
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = :param1 AND a.attnum > 0 AND NOT a.attisdropped
        """
        sql2 = " AND c.relname = :param2" if table_name else ""
        return sql1 + sql2, conf.dbSchema, table_name

    elif equals_ignore_case(ds.type, "oracle"):
        # Oracle: 需要处理 NUMBER 和 VARCHAR2 的精度信息
        sql1 = """
            SELECT col.COLUMN_NAME,
                   CASE
                       WHEN col.DATA_TYPE IN ('VARCHAR2', 'CHAR', 'NVARCHAR2', 'NCHAR')
                           THEN col.DATA_TYPE || '(' || col.DATA_LENGTH || ')'
                       WHEN col.DATA_TYPE = 'NUMBER' AND col.DATA_PRECISION IS NOT NULL
                           THEN col.DATA_TYPE || '(' || col.DATA_PRECISION ||
                                CASE WHEN col.DATA_SCALE > 0 THEN ',' || col.DATA_SCALE END || ')'
                       ELSE col.DATA_TYPE
                   END AS DATA_TYPE,
                   NVL(com.COMMENTS, '') AS COLUMN_COMMENT
            FROM ALL_TAB_COLUMNS col
            LEFT JOIN ALL_COL_COMMENTS com
                ON col.OWNER = com.OWNER AND col.TABLE_NAME = com.TABLE_NAME
                AND col.COLUMN_NAME = com.COLUMN_NAME
            WHERE col.OWNER = :param1
        """
        sql2 = " AND col.TABLE_NAME = :param2" if table_name else ""
        return sql1 + sql2, conf.dbSchema, table_name

    elif equals_ignore_case(ds.type, "ck"):
        # ClickHouse: 使用 system.columns
        sql1 = """
            SELECT name AS COLUMN_NAME, type AS DATA_TYPE, comment AS COLUMN_COMMENT
            FROM system.columns WHERE database = :param1
        """
        sql2 = " AND table = :param2" if table_name else ""
        return sql1 + sql2, conf.database, table_name

    elif equals_ignore_case(ds.type, "dm"):
        # 达梦: 使用 ALL_TAB_COLS 和 ALL_COL_COMMENTS
        sql1 = """
            SELECT c.COLUMN_NAME, c.DATA_TYPE, COALESCE(com.COMMENTS, '') AS COMMENTS
            FROM ALL_TAB_COLS c
            LEFT JOIN ALL_COL_COMMENTS com
                ON c.OWNER = com.OWNER AND c.TABLE_NAME = com.TABLE_NAME
                AND c.COLUMN_NAME = com.COLUMN_NAME
            WHERE c.OWNER = :param1
        """
        sql2 = " AND c.TABLE_NAME = :param2" if table_name else ""
        return sql1 + sql2, conf.dbSchema, table_name

    elif equals_ignore_case(ds.type, "doris", "starrocks"):
        # Doris/StarRocks: 使用 information_schema
        sql1 = """
            SELECT COLUMN_NAME, DATA_TYPE, COLUMN_COMMENT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
        """
        sql2 = " AND TABLE_NAME = %s" if table_name else ""
        return sql1 + sql2, conf.database, table_name

# 执行字段信息查询
def get_fields(ds: CoreDatasource, table_name: str = None) -> List[ColumnSchema]:
    """获取表或 Schema 下所有表的字段信息"""
    conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration)))
    db = DB.get_db(ds.type)
    sql, p1, p2 = get_field_sql(ds, conf, table_name)

    if db.connect_type == ConnectType.sqlalchemy:
        with get_session(ds) as session:
            with session.execute(text(sql), {"param1": p1, "param2": p2}) as result:
                res = result.fetchall()
                return [ColumnSchema(*item) for item in res]
    else:
        # 原生驱动的查询
        if equals_ignore_case(ds.type, 'doris', 'starrocks'):
            with pymysql.connect(
                user=conf.username, passwd=conf.password, host=conf.host,
                port=conf.port, db=conf.database, connect_timeout=conf.timeout
            ) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (p1, p2))
                    return [ColumnSchema(*item) for item in cursor.fetchall()]
```

## 完整使用示例

以下是一个完整的元数据探查使用示例，演示了如何初始化数据源配置、测试连接、获取 Schema 列表、表列表以及字段信息的完整流程。这个示例可以作为 AI 执行元数据探查的标准参考。

```python
# -*- coding: utf-8 -*-
"""
元数据探查完整示例
展示如何系统地探查数据库的元数据信息
"""

from typing import List, Optional
from dataclasses import dataclass
from enum import Enum
import json

# ==================== 数据结构定义 ====================

@dataclass
class TableInfo:
    """表信息结构"""
    name: str
    comment: str
    columns: List['ColumnInfo'] = None

@dataclass
class ColumnInfo:
    """字段信息结构"""
    name: str
    type: str
    comment: str = ""

@dataclass
class SchemaInfo:
    """Schema 信息结构，包含所有表和字段"""
    schema_name: str
    tables: List[TableInfo]

# ==================== 数据库连接配置 ====================

class DatabaseType(Enum):
    """支持的数据库类型"""
    MYSQL = "mysql"
    POSTGRESQL = "pg"
    ORACLE = "oracle"
    SQL_SERVER = "sqlServer"
    CLICKHOUSE = "ck"
    DORIS = "doris"
    STARROCKS = "starrocks"
    DM = "dm"
    REDSHIFT = "redshift"
    KINGBASE = "kingbase"
    ELASTICSEARCH = "es"

@dataclass
class DbConfig:
    """数据库连接配置"""
    db_type: DatabaseType
    host: str
    port: int
    username: str
    password: str
    database: str
    schema: str = ""
    timeout: int = 30

# ==================== 元数据探查器 ====================

class MetadataDiscoverer:
    """元数据探查器 - 封装所有探查功能"""

    def __init__(self, config: DbConfig):
        self.config = config
        self._connection = None

    def test_connection(self) -> bool:
        """
        测试数据库连接是否正常
        返回: True 表示连接成功，False 表示连接失败
        """
        try:
            # 根据数据库类型选择连接方式
            if self.config.db_type == DatabaseType.MYSQL:
                import pymysql
                with pymysql.connect(
                    host=self.config.host,
                    port=self.config.port,
                    user=self.config.username,
                    password=self.config.password,
                    database=self.config.database,
                    connect_timeout=10
                ) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                        return True

            elif self.config.db_type == DatabaseType.POSTGRESQL:
                import psycopg2
                with psycopg2.connect(
                    host=self.config.host,
                    port=self.config.port,
                    user=self.config.username,
                    password=self.config.password,
                    database=self.config.database,
                    connect_timeout=10
                ) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                        return True

            # 其他数据库的连接测试类似...
            return False

        except Exception as e:
            print(f"连接失败: {e}")
            return False

    def get_schemas(self) -> List[str]:
        """
        获取数据库中的所有 Schema
        返回: Schema 名称列表
        """
        schema_list = []

        if self.config.db_type == DatabaseType.POSTGRESQL:
            import psycopg2
            with psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.username,
                password=self.config.password,
                database=self.config.database
            ) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT nspname FROM pg_namespace WHERE nspname NOT LIKE 'pg_%'")
                    schema_list = [row[0] for row in cursor.fetchall()]

        elif self.config.db_type == DatabaseType.MYSQL:
            # MySQL 的 Schema 就是数据库本身
            schema_list = [self.config.database]

        elif self.config.db_type == DatabaseType.SQL_SERVER:
            import pymssql
            with pymssql.connect(
                server=self.config.host,
                port=self.config.port,
                user=self.config.username,
                password=self.config.password,
                database=self.config.database
            ) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT name FROM sys.schemas")
                    schema_list = [row[0] for row in cursor.fetchall()]

        return schema_list

    def get_tables(self, schema: str = None) -> List[TableInfo]:
        """
        获取指定 Schema 下的所有表信息
        参数: schema - Schema 名称，默认为配置的 schema
        返回: TableInfo 列表
        """
        schema = schema or self.config.schema
        tables = []

        if self.config.db_type == DatabaseType.MYSQL:
            import pymysql
            with pymysql.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.username,
                password=self.config.password,
                database=schema
            ) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT TABLE_NAME, IFNULL(TABLE_COMMENT, '')
                        FROM information_schema.TABLES
                        WHERE TABLE_SCHEMA = %s AND TABLE_TYPE IN ('BASE TABLE', 'VIEW')
                    """, (schema,))
                    for row in cursor.fetchall():
                        tables.append(TableInfo(name=row[0], comment=row[1]))

        elif self.config.db_type == DatabaseType.POSTGRESQL:
            import psycopg2
            with psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.username,
                password=self.config.password,
                database=self.config.database
            ) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT c.relname AS table_name,
                               COALESCE(d.description, '') AS table_comment
                        FROM pg_class c
                        LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
                        LEFT JOIN pg_description d ON d.objoid = c.oid AND d.objsubid = 0
                        WHERE n.nspname = %s
                            AND c.relkind IN ('r', 'v', 'm')
                            AND c.relname NOT LIKE 'pg_%'
                        ORDER BY c.relname
                    """, (schema,))
                    for row in cursor.fetchall():
                        tables.append(TableInfo(name=row[0], comment=row[1]))

        elif self.config.db_type == DatabaseType.ORACLE:
            import oracledb
            conn = oracledb.connect(
                user=self.config.username,
                password=self.config.password,
                dsn=f"{self.config.host}:{self.config.port}/{self.config.database}"
            )
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT t.table_name, NVL(c.comments, '')
                    FROM (
                        SELECT table_name FROM all_tables WHERE owner = %s
                        UNION ALL
                        SELECT view_name FROM all_views WHERE owner = %s
                    ) t
                    LEFT JOIN all_tab_comments c ON t.table_name = c.table_name
                """, (schema, schema))
                for row in cursor.fetchall():
                    tables.append(TableInfo(name=row[0], comment=row[1]))
            conn.close()

        return tables

    def get_table_columns(self, schema: str, table_name: str) -> List[ColumnInfo]:
        """
        获取指定表的字段信息
        参数:
            schema - Schema 名称
            table_name - 表名称
        返回: ColumnInfo 列表
        """
        columns = []

        if self.config.db_type == DatabaseType.MYSQL:
            import pymysql
            with pymysql.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.username,
                password=self.config.password,
                database=schema
            ) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT COLUMN_NAME, DATA_TYPE, IFNULL(COLUMN_COMMENT, '')
                        FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                        ORDER BY ORDINAL_POSITION
                    """, (schema, table_name))
                    for row in cursor.fetchall():
                        columns.append(ColumnInfo(name=row[0], type=row[1], comment=row[2]))

        elif self.config.db_type == DatabaseType.POSTGRESQL:
            import psycopg2
            with psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.username,
                password=self.config.password,
                database=self.config.database
            ) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT a.attname AS column_name,
                               pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
                               COALESCE(col_description(c.oid, a.attnum), '') AS column_comment
                        FROM pg_catalog.pg_attribute a
                        JOIN pg_catalog.pg_class c ON a.attrelid = c.oid
                        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                        WHERE n.nspname = %s AND c.relname = %s
                            AND a.attnum > 0 AND NOT a.attisdropped
                        ORDER BY a.attnum
                    """, (schema, table_name))
                    for row in cursor.fetchall():
                        columns.append(ColumnInfo(name=row[0], type=row[1], comment=row[2]))

        elif self.config.db_type == DatabaseType.ORACLE:
            import oracledb
            conn = oracledb.connect(
                user=self.config.username,
                password=self.config.password,
                dsn=f"{self.config.host}:{self.config.port}/{self.config.database}"
            )
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT col.column_name,
                           CASE
                               WHEN col.data_type IN ('VARCHAR2', 'CHAR')
                                   THEN col.data_type || '(' || col.data_length || ')'
                               WHEN col.data_type = 'NUMBER' AND col.data_precision IS NOT NULL
                                   THEN col.data_type || '(' || col.data_precision ||
                                        CASE WHEN col.data_scale > 0 THEN ',' || col.data_scale END || ')'
                               ELSE col.data_type
                           END AS data_type,
                           NVL(com.comments, '') AS column_comment
                    FROM all_tab_columns col
                    LEFT JOIN all_col_comments com
                        ON col.owner = com.owner AND col.table_name = com.table_name
                        AND col.column_name = com.column_name
                    WHERE col.owner = %s AND col.table_name = %s
                    ORDER BY col.column_id
                """, (schema, table_name))
                for row in cursor.fetchall():
                    columns.append(ColumnInfo(name=row[0], type=row[1], comment=row[2]))
            conn.close()

        return columns

    def discover_full(self) -> List[SchemaInfo]:
        """
        执行完整的元数据探查
        返回: 包含所有 Schema、表、字段信息的结构
        """
        schemas = self.get_schemas()
        result = []

        for schema in schemas:
            tables = self.get_tables(schema)
            for table in tables:
                table.columns = self.get_table_columns(schema, table.name)
            result.append(SchemaInfo(schema_name=schema, tables=tables))

        return result

    def generate_schema_description(self) -> str:
        """
        生成面向 LLM 的 Schema 描述文本
        返回: 格式化的文本描述
        """
        schema_info = self.discover_full()
        lines = []

        for schema in schema_info:
            lines.append(f"[Schema: {schema.schema_name}]")
            for table in schema.tables:
                lines.append(f"  Table: {table.name} - {table.comment}")
                for col in table.columns:
                    lines.append(f"    - {col.name}: {col.type} ({col.comment})")

        return "\n".join(lines)

# ==================== 使用示例 ====================

def main():
    """主函数 - 演示元数据探查的完整使用流程"""

    # 1. 配置数据库连接
    config = DbConfig(
        db_type=DatabaseType.POSTGRESQL,
        host="localhost",
        port=5432,
        username="postgres",
        password="password",
        database="mydb",
        schema="public"
    )

    # 2. 创建探查器
    discoverer = MetadataDiscoverer(config)

    # 3. 测试连接
    if not discoverer.test_connection():
        print("数据库连接失败")
        return

    print("数据库连接成功")

    # 4. 获取 Schema 列表
    schemas = discoverer.get_schemas()
    print(f"Schemas: {schemas}")

    # 5. 获取表列表
    tables = discoverer.get_tables()
    print(f"Tables: {[t.name for t in tables]}")

    # 6. 获取表字段信息
    for table in tables[:2]:  # 只演示前两个表
        columns = discoverer.get_table_columns(config.schema, table.name)
        print(f"\n{table.name} 的字段:")
        for col in columns:
            print(f"  - {col.name}: {col.type}")

    # 7. 生成完整描述
    description = discoverer.generate_schema_description()
    print("\n完整 Schema 描述:")
    print(description)

if __name__ == "__main__":
    main()
```

## 特殊数据库处理

### Elasticsearch 探查

Elasticsearch 是文档型数据库，其数据模型与传统关系型数据库有本质区别。在 Elasticsearch 中，索引（Index）对应关系型数据库的表，映射（Mapping）对应表结构，文档（Document）对应数据行。探查 Elasticsearch 时，需要使用 REST API 获取索引列表和映射信息。

```python
# Elasticsearch 元数据探查

def get_es_connect(conf: DatasourceConf):
    """创建 Elasticsearch 连接"""
    from elasticsearch import Elasticsearch
    return Elasticsearch(
        hosts=[f"http://{conf.host}:{conf.port}"],
        basic_auth=(conf.username, conf.password)
    )

def get_es_index(conf: DatasourceConf):
    """获取所有索引（对应表）"""
    es = get_es_connect(conf)
    indices = es.indices.get_alias(index="*")
    result = []
    for index_name in indices:
        # 获取索引的 comment（如果有）
        index_info = indices[index_name]
        comment = ""
        if 'aliases' in index_info:
            for alias, alias_info in index_info['aliases'].items():
                comment = alias
        result.append((index_name, comment))
    return result

def get_es_fields(conf: DatasourceConf, index_name: str):
    """获取索引的字段映射（对应表结构）"""
    es = get_es_connect(conf)
    mapping = es.indices.get_mapping(index=index_name)

    properties = mapping[index_name]['mappings'].get('properties', {})
    columns = []

    for field_name, field_info in properties.items():
        field_type = field_info.get('type', 'object')
        field_comment = field_info.get('fields', {}).get('keyword', {}).get('type', '')
        columns.append((field_name, field_type, field_comment))

    return columns
```

### 达梦数据库探查

达梦数据库是国产关系型数据库，其系统表结构与 Oracle 类似，使用 dmPython 驱动进行连接。在探查时需要特别注意中文编码问题和驱动依赖。

```python
# 达梦数据库元数据探查

import dmPython

def get_dm_tables(conf: DatasourceConf):
    """获取达梦数据库的表列表"""
    with dmPython.connect(
        user=conf.username,
        password=conf.password,
        server=conf.host,
        port=conf.port
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT table_name, NVL(comments, '')
                FROM all_tab_comments
                WHERE owner = %s AND table_type = 'TABLE'
            """, (conf.dbSchema,))
            return [TableSchema(*row) for row in cursor.fetchall()]

def get_dm_fields(conf: DatasourceConf, table_name: str):
    """获取达梦数据库的字段信息"""
    with dmPython.connect(
        user=conf.username,
        password=conf.password,
        server=conf.host,
        port=conf.port
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT c.COLUMN_NAME, c.DATA_TYPE, NVL(com.COMMENTS, '')
                FROM ALL_TAB_COLS c
                LEFT JOIN ALL_COL_COMMENTS com
                    ON c.OWNER = com.OWNER
                    AND c.TABLE_NAME = com.TABLE_NAME
                    AND c.COLUMN_NAME = com.COLUMN_NAME
                WHERE c.OWNER = %s AND c.TABLE_NAME = %s
                ORDER BY c.COLUMN_ID
            """, (conf.dbSchema, table_name))
            return [ColumnSchema(*row) for row in cursor.fetchall()]
```

## 常见问题处理

在元数据探查过程中，可能会遇到各种异常情况。以下是常见问题的处理方法和建议：

第一类是连接失败问题。连接失败可能由多种原因造成：网络不通、认证信息错误、数据库服务未启动、防火墙限制等。建议在连接测试阶段使用较短的超时时间（10 秒），避免长时间等待。对于需要特殊配置的数据库（如 Oracle 需要 Instant Client），需要提前准备好运行环境。连接失败时应该捕获异常并返回清晰的错误信息，便于问题定位。

第二类是权限不足问题。元数据查询通常需要访问系统表或数据字典视图，如果用户权限不足，可能只能看到部分表或字段。建议在创建探查专用用户时，授予必要的系统视图访问权限。对于 Oracle，需要有 SELECT ANY DICTIONARY 权限或显式授权访问 ALL_* 视图。

第三类是字符编码问题。中文注释在存储和传输过程中可能出现编码问题，常见于从数据库读取时的 bytes 类型。建议在读取后统一进行 decode 处理，将 bytes 转换为 str。对于不确定编码的情况，可以尝试使用 errors='ignore' 或 errors='replace' 参数。

第四类是数据库版本差异问题。不同版本的同一数据库可能存在系统表结构差异，如 ClickHouse 22 版本之后才支持 comment 字段。建议在查询前先获取数据库版本，根据版本选择合适的 SQL 语句。使用版本检测可以提高探查器的兼容性。

## 与其他技能的集成

元数据探查技能通常与其他技能配合使用，形成完整的数据库应用工作流。以下是典型的集成场景：

与 SQL 生成技能集成时，元数据探查负责获取数据库结构信息，为 SQL 生成提供上下文。SQL 生成技能根据探查结果了解表之间的关联关系、字段类型约束等信息，生成符合目标数据库语法的 SQL 语句。集成时需要注意保持数据库类型的识别方式一致，确保 SQL 生成能正确处理各数据库的特性。

与数据可视化技能集成时，元数据探查提供表结构和字段信息，帮助可视化技能理解数据的含义和类型。字段注释可以用于生成更友好的图表标签，字段类型可以指导可视化时选择合适的聚合方式和图表类型。

与数据质量检查技能集成时，元数据探查提供表的元数据作为质量规则的基础。例如可以根据字段类型定义域约束，根据字段注释理解业务含义，根据表之间的关系定义跨表验证规则。

## 最佳实践总结

在实际项目中应用元数据探查技能时，建议遵循以下最佳实践：

首先，建立标准化的探查流程。无论探查何种数据库，都应该遵循连接测试、Schema 获取、表列表获取、字段信息获取的标准流程。标准化的流程有助于代码复用和问题排查，也便于团队成员理解和维护代码。

其次，实现统一的返回格式。无论底层使用何种数据库查询方式，对外接口都应该返回统一格式的数据结构。这样上层应用无需关心数据库差异，只需处理统一的 Schema 信息结构。

第三，处理边界情况和异常。在探查过程中，可能遇到空 Schema、无表数据库、系统表过滤等边界情况，也可能出现连接超时、权限不足等异常。良好的异常处理机制可以提高探查器的鲁棒性，避免因个别问题导致整个探查流程失败。

第四，注重性能优化。对于包含大量表的数据库，完整的元数据探查可能耗时较长。可以考虑使用缓存机制存储探查结果，在数据库结构未发生变化时复用缓存。对于实时性要求不高的场景，可以异步执行探查任务，避免阻塞主流程。

第五，支持增量探查。在大型数据库环境中，完整探查可能非常耗时。增量探查功能可以只探查新增或变更的对象，提高探查效率。这需要维护一个探查历史记录，用于判断哪些对象需要重新探查。
