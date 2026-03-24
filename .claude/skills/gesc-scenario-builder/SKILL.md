---
name: gcsg-scenario-builder
description: 用于构建“全球企业网安协同与风险治理平台 (GCSG)”超大规模跨库测试场景。该场景为 data-explorer 提供深度压力测试，每个数据库包含至少 30 张表，总计 90+ 张表。当用户提到“构建复杂测试场景”、“进行多库联查测试”或“初始化 GCSG 场景”时，请务必使用此技能。
---

# gcsg-scenario-builder (GCSG 场景构建器)

一个用于构建超大规模、跨库业务场景（“全球企业网安协同与风险治理平台” - GCSG）的技能，专为 `data-explorer` 的复杂联查和多表关联设计。

## 工作流

1. **配置三个核心数据源**: 
   - **数据源 A (GCSG-Ops)**: 运营域。执行 `assets/sql/gcsg_ops.sql` (30 张表)。
   - **数据源 B (GCSG-Governance)**: 治理域。执行 `assets/sql/gcsg_governance.sql` (30 张表)。
   - **数据源 C (GCSG-Intelligence)**: 情报域。执行 `assets/sql/gcsg_intelligence.sql` (30 张表)。

2. **跨库业务联查示例**:
   该场景支持以下高度复杂的跨库业务查询，用于验证 `data-explorer` 的智能推断能力：
   - **风险溯源**: 查找过去 1 小时内触发“严重”告警的设备（Ops 库），并关联其所属部门的负责人和物理位置（Governance 库）。
   - **情报预警**: 根据情报库中最新发布的 CVE 漏洞（Intelligence 库），检索 Governance 库中受影响的资产版本，并从 Ops 库中调取这些资产近期的流量审计记录。
   - **UEBA 分析**: 分析某个异常登录账号（Ops 库）是否在治理库（Governance 库）的账号黑名单中，并查询该账号是否涉及已知 APT 组织的攻击手法（Intelligence 库）。

3. **验证与交付**:
   - 验证 90+ 张表是否全部加载。
   - 提供 5 个以上的业务测试问题给用户。

## 成功标准
- 每个数据库不少于 30 张表定义。
- 表结构包含完整的字段注释以辅助 AI 理解。
- 跨库关联点（device_id, depart_id, cve, account_id）均已通过模拟数据跑通。
