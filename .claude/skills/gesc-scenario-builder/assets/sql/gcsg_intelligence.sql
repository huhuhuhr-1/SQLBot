-- GCSG-Intelligence: Threat Intel & Analytics Domain
-- Tables extracted and organized from public.sql (IOC/KB/Stats)

-- 1-10: IOC (Indicator of Compromise) Tables
CREATE TABLE IF NOT EXISTS "ioc_cve_info" (LIKE "public"."ioc_cve_info" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "ioc_record_info" (LIKE "public"."ioc_record_info" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "ioc_compromise" (LIKE "public"."ioc_compromise" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "ioc_outer_compromise" (LIKE "public"."ioc_outer_compromise" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "ioc_outer_source" (LIKE "public"."ioc_outer_source" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "ioc_tag_mapping" (LIKE "public"."ioc_tag_mapping" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "ioc_industry_mapping" (LIKE "public"."ioc_industry_mapping" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "ioc_platform" (LIKE "public"."ioc_platform" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "ioc_ip_reputation" (LIKE "public"."ioc_ip_reputation" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "ioc_domain_reputation" (LIKE "public"."ioc_domain_reputation" INCLUDING ALL);

-- 11-20: Knowledge Base (KB) Tables
CREATE TABLE IF NOT EXISTS "kb_cve_info" (LIKE "public"."kb_cve_info" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "kb_apt_rule" (LIKE "public"."kb_apt_rule" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "kb_malware_type" (LIKE "public"."kb_malware_type" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "kb_attack_rule" (LIKE "public"."kb_attack_rule" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "kb_attck_grid" (LIKE "public"."kb_attck_grid" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "kb_trojan_encyclopedia" (LIKE "public"."kb_trojan_encyclopedia" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "kb_cube_info" (LIKE "public"."kb_cube_info" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "kb_rule_import_record" (LIKE "public"."kb_rule_import_record" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "kb_malware_rule" (LIKE "public"."kb_malware_rule" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "kb_attack_desc" (LIKE "public"."kb_attack_desc" INCLUDING ALL);

-- 21-30: Intelligence Processing & Stats Tables
CREATE TABLE IF NOT EXISTS "intelligence_process_leak" (LIKE "public"."intelligence_process_leak" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "intelligence_process_sample" (LIKE "public"."intelligence_process_sample" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "intelligence_process_apt" (LIKE "public"."intelligence_process_apt" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "intelligence_process_task" (LIKE "public"."intelligence_process_task" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "stats_attack_all" (LIKE "public"."stats_attack_all" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "stats_attack_type" (LIKE "public"."stats_attack_type" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "stats_attack_source" (LIKE "public"."stats_attack_source" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "stats_attack_target" (LIKE "public"."stats_attack_target" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "stats_attack_virus" (LIKE "public"."stats_attack_virus" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "stats_security_index" (LIKE "public"."stats_security_index" INCLUDING ALL);

-- Cross-DB Sample Data
INSERT INTO "ioc_cve_info" (name, name_cn, hazard_level, description)
VALUES ('CVE-2024-1234', 'Log4j Enterprise Vulnerability', 'Critical', 'Remote Code Execution in Enterprise Apps');

INSERT INTO "kb_malware_type" (alert_name, threat_rule_type)
VALUES ('WannaCry.v2', 'Ransomware');
