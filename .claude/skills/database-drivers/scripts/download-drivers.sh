#!/bin/bash
# 批量下载数据库 JDBC 驱动脚本
# 从 Maven Central 下载主流数据库驱动

DRIVERS_DIR=".claude/skills/database-drivers/drivers"
BASE_URL="https://repo.maven.apache.org/maven2"

# 创建驱动目录
mkdir -p "$DRIVERS_DIR"

echo "========================================="
echo "开始下载数据库 JDBC 驱动"
echo "目标目录: $DRIVERS_DIR"
echo "========================================="
echo ""

# 下载函数
download_driver() {
    local url=$1
    local output=$2
    local name=$3

    echo "📥 下载 $name ..."
    if curl -L -s -f "$url" -o "$output"; then
        size=$(ls -lh "$output" | awk '{print $5}')
        echo "   ✅ $name 下载成功 ($size)"
        return 0
    else
        echo "   ❌ $name 下载失败"
        return 1
    fi
}

# 1. Oracle JDBC (ojdbc11-23.26.0.0.0)
download_driver \
    "$BASE_URL/com/oracle/database/jdbc/ojdbc11/23.26.0.0.0/ojdbc11-23.26.0.0.0.jar" \
    "$DRIVERS_DIR/ojdbc11-23.26.0.0.0.jar" \
    "Oracle JDBC"

# 2. SQL Server JDBC (mssql-jdbc-12.8.0.jre8)
download_driver \
    "$BASE_URL/com/microsoft/sqlserver/mssql-jdbc/12.8.0.jre8/mssql-jdbc-12.8.0.jre8.jar" \
    "$DRIVERS_DIR/mssql-jdbc-12.8.0.jre8.jar" \
    "SQL Server JDBC"

# 3. MariaDB JDBC (mariadb-java-client-3.5.2)
download_driver \
    "$BASE_URL/org/mariadb/jdbc/mariadb-java-client/3.5.2/mariadb-java-client-3.5.2.jar" \
    "$DRIVERS_DIR/mariadb-java-client-3.5.2.jar" \
    "MariaDB JDBC"

# 4. H2 Database (h2-2.4.240)
download_driver \
    "$BASE_URL/com/h2database/h2/2.4.240/h2-2.4.240.jar" \
    "$DRIVERS_DIR/h2-2.4.240.jar" \
    "H2 Database"

# 5. DB2 JDBC (jcc-12.1.3.0)
download_driver \
    "$BASE_URL/com/ibm/db2/jcc/12.1.3.0/jcc-12.1.3.0.jar" \
    "$DRIVERS_DIR/jcc-12.1.3.0.jar" \
    "IBM DB2 JDBC"

# 6. OceanBase JDBC (oceanbase-client-2.4.15)
download_driver \
    "$BASE_URL/com/oceanbase/oceanbase-client/2.4.15/oceanbase-client-2.4.15.jar" \
    "$DRIVERS_DIR/oceanbase-client-2.4.15.jar" \
    "OceanBase JDBC"

# 7. ClickHouse JDBC (clickhouse-jdbc-0.6.0)
download_driver \
    "$BASE_URL/com/clickhouse/clickhouse-jdbc/0.6.0/clickhouse-jdbc-0.6.0.jar" \
    "$DRIVERS_DIR/clickhouse-jdbc-0.6.0.jar" \
    "ClickHouse JDBC"

# 8. Hive JDBC (hive-jdbc-4.2.0)
download_driver \
    "$BASE_URL/org/apache/hive/hive-jdbc/4.2.0/hive-jdbc-4.2.0.jar" \
    "$DRIVERS_DIR/hive-jdbc-4.2.0.jar" \
    "Apache Hive JDBC"

echo ""
echo "========================================="
echo "下载完成！"
echo "========================================="
echo ""

# 统计下载结果
total_files=$(ls -1 "$DRIVERS_DIR"/*.jar 2>/dev/null | wc -l)
total_size=$(du -sh "$DRIVERS_DIR" | cut -f1)

echo "📊 统计信息："
echo "   已下载驱动数量: $total_files"
echo "   总大小: $total_size"
echo ""

# 列出已下载的驱动
echo "📁 已下载的驱动文件："
ls -lh "$DRIVERS_DIR"/*.jar 2>/dev/null | awk '{print "   " $9 " (" $5 ")"}'
echo ""

echo "⚠️  注意：以下驱动需要手动下载："
echo "   - 达梦数据库 (DmJdbcDriver18.jar) - 从达梦安装目录获取"
echo "   - 人大金仓 (kingbase8jdbc.jar) - 从 KingbaseES 安装目录获取"
echo "   - GaussDB/openGauss (opengauss-jdbc.jar) - 从华为云或 openGauss 官网获取"
echo "   - Sybase ASE (jconn4.jar) - 从 SAP/Sybase 官网获取"
echo ""

echo "✅ 驱动下载完成！请查看 drivers.json 获取详细的驱动配置信息。"
