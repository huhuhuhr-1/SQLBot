#!/bin/bash
# 批量拉取数据库 Docker 镜像脚本
# 使用华为云镜像源加速：swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/

MIRROR_PREFIX="swr.cn-north-4.myhuaweicloud.com/ddn-k8s"

echo "========================================="
echo "批量拉取数据库 Docker 镜像"
echo "镜像源: $MIRROR_PREFIX"
echo "========================================="
echo ""

# 镜像列表（只包含可从 Docker Hub 或公开仓库拉取的镜像）
declare -A IMAGES=(
    ["PostgreSQL"]="docker.io/postgres:16"
    ["MySQL"]="docker.io/mysql:8.4"
    ["MariaDB"]="docker.io/mariadb:latest"
    ["MongoDB"]="docker.io/mongo:latest"
    ["H2 Database"]="docker.io/oscarfonts/h2:latest"
    ["OceanBase"]="docker.io/oceanbase/oceanbase-ce:latest"
    ["ClickHouse"]="docker.io/clickhouse/clickhouse-server:latest"
    ["openGauss"]="docker.io/opengauss/opengauss:latest"
    ["SQL Server"]="mcr.microsoft.com/mssql/server:2025-latest"
)

# 需要特殊处理的镜像
declare -A SPECIAL_IMAGES=(
    ["IBM DB2"]="icr.io/db2_community/db2:latest"
    ["人大金仓"]="docker.io/huzhihui/kingbase:latest"
)

# 拉取函数
pull_image() {
    local name=$1
    local image=$2

    echo "📥 拉取 $name ..."
    echo "   镜像: $image"

    if [[ $image == mcr.microsoft.com/* ]]; then
        # MCR 镜像
        full_image="$MIRROR_PREFIX/$image"
    elif [[ $image == icr.io/* ]]; then
        # IBM Cloud 镜像（不使用镜像源）
        full_image="$image"
    else
        # Docker Hub 镜像
        full_image="$MIRROR_PREFIX/$image"
    fi

    if docker pull "$full_image"; then
        echo "   ✅ $name 拉取成功"
        echo ""

        # 可选：添加 tag（去掉镜像源前缀，便于使用）
        short_name=$(echo "$image" | sed 's|docker.io/||')
        if [[ "$full_image" != "$short_name" ]]; then
            echo "   🏷️  添加 tag: $short_name"
            docker tag "$full_image" "$short_name"
            docker rmi "$full_image" 2>/dev/null
        fi

        return 0
    else
        echo "   ❌ $name 拉取失败"
        echo ""
        return 1
    fi
}

# 拉取主要镜像
echo ">>> 拉取主流数据库镜像"
echo ""
for name in "${!IMAGES[@]}"; do
    pull_image "$name" "${IMAGES[$name]}"
done

# 拉取特殊镜像
echo ">>> 拉取特殊数据库镜像"
echo ""
for name in "${!SPECIAL_IMAGES[@]}"; do
    pull_image "$name" "${SPECIAL_IMAGES[$name]}"
done

# 统计结果
echo ""
echo "========================================="
echo "拉取完成！"
echo "========================================="
echo ""

echo "📊 统计信息："
total_count=$((${#IMAGES[@]} + ${#SPECIAL_IMAGES[@]}))
echo "   尝试拉取: $total_count 个镜像"
echo ""

echo "📁 已下载的镜像："
docker images --format "   - {{.Repository}}:{{.Tag}} ({{.Size}})" | grep -E "postgres|mysql|mariadb|mongo|h2|oceanbase|clickhouse|opengauss|mssql|db2|kingbase"
echo ""

echo "⚠️  注意：以下镜像需要手动获取"
echo "   - Oracle Database - 从 Oracle 官方 GitHub 仓库构建"
echo "   - 达梦数据库 (DM) - 从达梦官网下载"
echo "   - Apache Hive - 使用大数据平台镜像或社区镜像"
echo ""

echo "💡 运行容器示例："
echo "   PostgreSQL: docker run -d --name postgres -p 5432:5432 -e POSTGRES_PASSWORD=yourpassword postgres:16"
echo "   MySQL:      docker run -d --name mysql -p 3306:3306 -e MYSQL_ROOT_PASSWORD=yourpassword mysql:8.4"
echo "   详情请参考: docs/docker-pull-guide.md"
echo ""

echo "✅ 镜像拉取脚本执行完成！"
