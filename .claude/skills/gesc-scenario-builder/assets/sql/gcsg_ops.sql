-- GCSG-Ops: Real-time Cyber Security Operations Domain
-- Tables extracted and organized from public.sql (SOC/UEBA/Audit)

-- 1-10: Abnormal Behavior (UEBA) Tables
CREATE TABLE IF NOT EXISTS "abnormal_account_login" (LIKE "public"."abnormal_account_login" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "abnormal_account_operation" (LIKE "public"."abnormal_account_operation" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "abnormal_account_transfer" (LIKE "public"."abnormal_account_transfer" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "abnormal_app_access" (LIKE "public"."abnormal_app_access" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "abnormal_app_account" (LIKE "public"."abnormal_app_account" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "abnormal_app_behavior" (LIKE "public"."abnormal_app_behavior" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "abnormal_app_transfer" (LIKE "public"."abnormal_app_transfer" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "abnormal_device_access" (LIKE "public"."abnormal_device_access" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "abnormal_device_netlog" (LIKE "public"."abnormal_device_netlog" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "abnormal_device_transfer" (LIKE "public"."abnormal_device_transfer" INCLUDING ALL);

-- 11-20: Audit Behavior (Detailed Traffic) Tables
CREATE TABLE IF NOT EXISTS "audit_behavior_web" (LIKE "public"."audit_behavior_web" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "audit_behavior_dns" (LIKE "public"."audit_behavior_dns" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "audit_behavior_db" (LIKE "public"."audit_behavior_db" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "audit_behavior_ssl" (LIKE "public"."audit_behavior_ssl" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "audit_behavior_file" (LIKE "public"."audit_behavior_file" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "audit_behavior_command" (LIKE "public"."audit_behavior_command" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "audit_behavior_login" (LIKE "public"."audit_behavior_login" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "audit_behavior_email" (LIKE "public"."audit_behavior_email" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "audit_behavior_ip" (LIKE "public"."audit_behavior_ip" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "audit_net_log" (LIKE "public"."audit_net_log" INCLUDING ALL);

-- 21-30: Real-time Alerts & Incident Tables
CREATE TABLE IF NOT EXISTS "alert_attack_all" (LIKE "public"."alert_attack_all" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "alert_attack_abnormal" (LIKE "public"."alert_attack_abnormal" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "alert_attack_blacklist" (LIKE "public"."alert_attack_blacklist" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "alert_attack_file" (LIKE "public"."alert_attack_file" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "alert_attack_lateral" (LIKE "public"."alert_attack_lateral" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "alert_attack_malware" (LIKE "public"."alert_attack_malware" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "alert_attack_sensitive" (LIKE "public"."alert_attack_sensitive" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "alert_security_incident" (LIKE "public"."alert_security_incident" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "alert_steal_incident" (LIKE "public"."alert_steal_incident" INCLUDING ALL);
CREATE TABLE IF NOT EXISTS "pcap_analyze" (LIKE "public"."pcap_analyze" INCLUDING ALL);

-- Cross-DB Sample Data
INSERT INTO "alert_attack_all" (device_id, alert_id, alert_time, rule_name, risk, sip, dip, cve, depart_id)
VALUES ('DEV-HQ-001', 'ALRT-2026-X1', NOW(), 'Log4j RCE Attempt', 3, '103.45.12.1', '192.168.50.10', 'CVE-2024-1234', 'DEPT-ASIA-01');
