-- GCSG-Governance: Org Structure & Compliance Domain
-- Tables extracted and organized from public.sql (System/Policy/Asset)

-- 1-10: System Organization & Geo Tables
CREATE TABLE IF NOT EXISTS "sys_department" (LIKE "public"."sys_department" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "sys_department_org" (LIKE "public"."sys_department_org" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "sys_geo_code" (LIKE "public"."sys_geo_code" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "sys_geo_c2c" (LIKE "public"."sys_geo_c2c" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "sys_industry_info" (LIKE "public"."sys_industry_info" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "sys_info" (LIKE "public"."sys_info" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "sys_log" (LIKE "public"."sys_log" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "sys_sequences" (LIKE "public"."sys_sequences" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "sys_troubleshooting_info" (LIKE "public"."sys_troubleshooting_info" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "sys_dict" (LIKE "public"."sys_dict" INCLUDING ALL);

-- 11-20: Device & Infrastructure Asset Tables
CREATE TABLE IF NOT EXISTS "sys_device_info" (LIKE "public"."sys_device_info" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "sys_device_info_protect" (LIKE "public"."sys_device_info_protect" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "sys_device_mapping" (LIKE "public"."sys_device_mapping" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "sys_terminal_info" (LIKE "public"."sys_terminal_info" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "asset_device" (LIKE "public"."asset_device" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "asset_app" (LIKE "public"."asset_app" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "asset_account" (LIKE "public"."asset_account" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "asset_mark_rule" (LIKE "public"."asset_mark_rule" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "asset_sys_info" (LIKE "public"."asset_sys_info" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "asset_vendor" (LIKE "public"."asset_vendor" INCLUDING ALL);

-- 21-30: Policy & Compliance Tables
CREATE TABLE IF NOT EXISTS "policy_account_blacklist" (LIKE "public"."policy_account_blacklist" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "policy_ip_blacklist" (LIKE "public"."policy_ip_blacklist" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "policy_domain_blacklist" (LIKE "public"."policy_domain_blacklist" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "policy_sensitive_info" (LIKE "public"."policy_sensitive_info" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "policy_attack" (LIKE "public"."policy_attack" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "policy_audit_net_log" (LIKE "public"."policy_audit_net_log" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "policy_audit_ip" (LIKE "public"."policy_audit_ip" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "policy_audit_domain" (LIKE "public"."policy_audit_domain" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "policy_audit_url" (LIKE "public"."policy_audit_url" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "policy_malware" (LIKE "public"."policy_malware" INCLUDING ALL);

-- Cross-DB Sample Data
INSERT INTO "sys_department" (depart_id, depart_name, company_name)
VALUES ('DEPT-ASIA-01', 'Asia-Pacific R&D Center', 'Global Cyber Corp');

INSERT INTO "sys_device_info" (device_id, organs, address, state)
VALUES ('DEV-HQ-001', 'Headquarters SOC', 'Cyber Tower, Floor 42', '1');
