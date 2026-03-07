-- ========================================
-- execution_records 表多维度分析 SQL
-- 数据库: PostgreSQL 17.6
-- ========================================

-- 查询1: 执行状态分布分析
SELECT
  "status" AS "执行状态",
  COUNT("id") AS "任务数量",
  ROUND(COUNT("id") * 100.0 / SUM(COUNT("id")) OVER(), 2) AS "占比%"
FROM "public"."execution_records"
GROUP BY "status"
ORDER BY "任务数量" DESC;

-- 查询2: 任务执行频率 TOP 10
SELECT
  "task_id" AS "任务ID",
  "task_name" AS "任务名称",
  COUNT("id") AS "执行次数",
  ROUND(AVG("elapsed_time") / 1000.0, 2) AS "平均耗时_秒"
FROM "public"."execution_records"
GROUP BY "task_id", "task_name"
ORDER BY "执行次数" DESC
LIMIT 10;

-- 查询3: 执行耗时统计分析
SELECT
  ROUND(AVG("elapsed_time") / 1000.0, 2) AS "平均耗时_秒",
  ROUND(MAX("elapsed_time") / 1000.0, 2) AS "最大耗时_秒",
  ROUND(MIN("elapsed_time") / 1000.0, 2) AS "最小耗时_秒",
  ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY "elapsed_time") / 1000.0, 2) AS "中位数耗时_秒",
  ROUND(STDDEV("elapsed_time") / 1000.0, 2) AS "标准差_秒"
FROM "public"."execution_records"
WHERE "elapsed_time" IS NOT NULL;

-- 查询4: 每日执行趋势分析
SELECT
  TO_CHAR(TO_TIMESTAMP("start_time" / 1000), 'YYYY-MM-DD') AS "日期",
  COUNT("id") AS "执行次数",
  ROUND(AVG("elapsed_time") / 1000.0, 2) AS "平均耗时_秒",
  COUNT(CASE WHEN "status" = 'SUCCESS' THEN 1 END) AS "成功数",
  COUNT(CASE WHEN "status" != 'SUCCESS' THEN 1 END) AS "失败数"
FROM "public"."execution_records"
WHERE "start_time" IS NOT NULL
GROUP BY TO_CHAR(TO_TIMESTAMP("start_time" / 1000), 'YYYY-MM-DD')
ORDER BY "日期" ASC;

-- 查询5: 触发类型分布分析
SELECT
  COALESCE("trigger_type", '未知') AS "触发类型",
  COUNT("id") AS "任务数量",
  ROUND(COUNT("id") * 100.0 / SUM(COUNT("id")) OVER(), 2) AS "占比%",
  ROUND(AVG("elapsed_time") / 1000.0, 2) AS "平均耗时_秒"
FROM "public"."execution_records"
GROUP BY "trigger_type"
ORDER BY "任务数量" DESC;

-- 查询6: 执行队列分布分析
SELECT
  COALESCE("execute_queue_name", '默认队列') AS "队列名称",
  COUNT("id") AS "任务数量",
  ROUND(AVG("elapsed_time") / 1000.0, 2) AS "平均耗时_秒",
  ROUND(MAX("elapsed_time") / 1000.0, 2) AS "最大耗时_秒"
FROM "public"."execution_records"
GROUP BY "execute_queue_name"
ORDER BY "任务数量" DESC;

-- 查询7: 任务状态与耗时关系分析
SELECT
  "status" AS "执行状态",
  COUNT("id") AS "任务数量",
  ROUND(AVG("elapsed_time") / 1000.0, 2) AS "平均耗时_秒",
  ROUND(MIN("elapsed_time") / 1000.0, 2) AS "最小耗时_秒",
  ROUND(MAX("elapsed_time") / 1000.0, 2) AS "最大耗时_秒"
FROM "public"."execution_records"
WHERE "elapsed_time" IS NOT NULL
GROUP BY "status"
ORDER BY "平均耗时_秒" DESC;