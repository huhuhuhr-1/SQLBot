-- GCSG Meta-Data Backup: The "Soul" of the Database
-- Preserving business logic, comments, and views from public.sql

-- 1. Business Logic Functions (Simulated)
-- These triggers explain how data flows into partitions
-- Function: auto_partition_monthly_trigger_function()
-- Function: sync_partition_data_trigger_function()

-- 2. Core Business Views (Asset Profiling Logic)
-- Use these to understand how tables are joined in real scenarios
CREATE OR REPLACE VIEW "view_asset_dev_profile" AS 
SELECT d.id, d.device_id, d.device_type, d.organs, d.address, d.state, dept.depart_full_name
FROM sys_device_info d
LEFT JOIN sys_department dept ON d.device_id = dept.device_id;

-- 3. Vital Field Comments (The AI's knowledge base)
COMMENT ON COLUMN "abnormal_account_login"."depart_id" IS '部门Id';
COMMENT ON COLUMN "abnormal_account_login"."depart_full_name" IS '部门完整路径';
COMMENT ON COLUMN "alert_attack_all"."risk" IS '风险等级: 1低, 2中, 3高, 4极高';
COMMENT ON COLUMN "ioc_cve_info"."hazard_level" IS '漏洞危险等级';
COMMENT ON COLUMN "sys_device_info"."state" IS '设备状态: 0离线, 1在线';

-- 4. Dictionary Constants (Representative Data)
-- Added to help AI understand state codes without the full 19k lines
INSERT INTO "sys_dict" (dict_code, dict_name, item_value, item_text) VALUES 
('risk_level', '风险等级', '3', '高风险'),
('risk_level', '风险等级', '4', '极高风险'),
('device_state', '设备状态', '1', '正常运行'),
('device_state', '设备状态', '0', '异常离线');
