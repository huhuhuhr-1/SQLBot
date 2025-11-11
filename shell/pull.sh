#!/bin/bash

# ================================
# 自动切换到指定分支并拉取最新代码
# 用途：本地只打包，不提交
# ================================

# 要切换的远程分支
REMOTE_BRANCH="hr/v1.1.x/202509"
LOCAL_BRANCH="${REMOTE_BRANCH}"

# 保存当前工作目录修改
echo "📦 暂存本地修改..."
git stash -q

# 获取远程分支最新信息
echo "🔄 获取远程分支信息..."
git fetch origin

# 切换到本地分支，如果不存在则创建，重置为远程分支状态
echo "➡️ 切换到本地分支 $LOCAL_BRANCH ..."
git checkout -B "$LOCAL_BRANCH" "origin/$REMOTE_BRANCH"

# 拉取远程最新代码
echo "⬇️ 拉取远程最新代码..."
git pull origin "$REMOTE_BRANCH"

# 恢复本地修改（可选，如果只打包可以注释掉）
# echo "♻️ 恢复本地修改..."
# git stash pop -q

echo "✅ 分支切换并更新完成，可以打包！"
