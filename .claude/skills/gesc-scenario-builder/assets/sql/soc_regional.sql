-- SOC Regional Domain
-- Focused on real-time abnormal behavior and alerts

-- abnormal_account_login
CREATE TABLE IF NOT EXISTS "public"."abnormal_account_login" (
  "id" SERIAL PRIMARY KEY,
  "device_id" varchar(16) NOT NULL,
  "sip" varchar(46) NOT NULL,
  "dip" varchar(46) NOT NULL,
  "start_time" timestamp(6),
  "depart_name" varchar(128),
  "login_count" int8,
  "success_count" int8,
  "failed_count" int8,
  "model_name" varchar(50),
  "abnormal_value" varchar(500),
  "update_time" timestamp(0) DEFAULT CURRENT_TIMESTAMP,
  "country" varchar(32),
  "depart_id" varchar(64)
);

-- abnormal_account_operation
CREATE TABLE IF NOT EXISTS "public"."abnormal_account_operation" (
  "id" SERIAL PRIMARY KEY,
  "device_id" varchar(16) NOT NULL,
  "sip" varchar(46) NOT NULL,
  "dip" varchar(46) NOT NULL,
  "start_time" timestamp(6),
  "depart_name" varchar(128),
  "sender" varchar(128),
  "receiver" varchar(1024),
  "subject" varchar(128),
  "forward_count" int8 DEFAULT 0,
  "model_name" varchar(50),
  "abnormal_value" varchar(500),
  "update_time" timestamp(0) DEFAULT CURRENT_TIMESTAMP,
  "depart_id" varchar(64)
);

-- alert_attack_all
CREATE TABLE IF NOT EXISTS "public"."alert_attack_all" (
  "id" SERIAL PRIMARY KEY,
  "device_id" varchar(32),
  "alert_id" varchar(64),
  "alert_time" timestamp(0),
  "rule_name" varchar(128),
  "risk" int2,
  "sip" varchar(46),
  "dip" varchar(46),
  "attacker" varchar(46),
  "victim" varchar(46),
  "attack_result" int2 DEFAULT 0,
  "threat_type" varchar(16),
  "attack_class" int2,
  "attack_group" varchar(64),
  "vulnerability" varchar(128),
  "cve" varchar(64),
  "depart_name" varchar(128),
  "country" varchar(64),
  "create_time" timestamp(0),
  "depart_id" varchar(64)
);

-- Mock Data for SOC Regional
INSERT INTO "public"."abnormal_account_login" (device_id, sip, dip, start_time, depart_name, login_count, success_count, failed_count, model_name, abnormal_value, country, depart_id) 
VALUES ('DEV-001', '192.168.1.10', '10.0.0.5', NOW(), 'Research & Development', 50, 2, 48, 'BruteForceDetection', 'High frequency failed logins from unknown IP', 'USA', 'DEP-101');

INSERT INTO "public"."alert_attack_all" (device_id, alert_id, alert_time, rule_name, risk, sip, dip, attacker, victim, attack_result, threat_type, attack_class, depart_name, depart_id)
VALUES ('DEV-001', 'ALT-999', NOW(), 'SQL Injection Attempt', 3, '203.0.113.5', '192.168.1.10', 'External-Hacker', 'Internal-WebSrv', 0, 'Exploit', 1, 'Research & Development', 'DEP-101');
