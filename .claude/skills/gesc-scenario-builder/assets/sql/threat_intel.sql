-- Global Threat Intelligence Domain
-- Focused on CVEs, Malware Signatures and Infrastructure Topology

-- ioc_cve_info
CREATE TABLE IF NOT EXISTS "public"."ioc_cve_info" (
  "id" SERIAL PRIMARY KEY,
  "name" varchar(255),
  "name_cn" varchar(255),
  "publish_date" timestamp(0),
  "hazard_level" varchar(255),
  "leak_type" varchar(255),
  "description" text,
  "create_time" timestamp(6) DEFAULT CURRENT_TIMESTAMP,
  "update_time" timestamp(6) DEFAULT CURRENT_TIMESTAMP
);

-- kb_malware_type
CREATE TABLE IF NOT EXISTS "public"."kb_malware_type" (
  "id" SERIAL PRIMARY KEY,
  "alert_name" varchar(255),
  "threat_rule_type" varchar(16)
);

-- sys_device_info
CREATE TABLE IF NOT EXISTS "public"."sys_device_info" (
  "id" SERIAL PRIMARY KEY,
  "device_id" varchar(32) UNIQUE,
  "device_type" int2 NOT NULL,
  "soft_version" varchar(128),
  "organs" varchar(128),
  "address" varchar(128),
  "state" varchar(2),
  "create_date" timestamp(6) DEFAULT CURRENT_TIMESTAMP,
  "update_date" timestamp(6) DEFAULT CURRENT_TIMESTAMP
);

-- Mock Data for Threat Intelligence
INSERT INTO "public"."ioc_cve_info" (name, name_cn, hazard_level, leak_type, description)
VALUES ('CVE-2024-1234', 'Log4j Enterprise Vulnerability', 'Critical', 'Remote Code Execution', 'A critical RCE vulnerability in enterprise log4j installations.');

INSERT INTO "public"."kb_malware_type" (alert_name, threat_rule_type)
VALUES ('WannaCry.v2', 'Ransomware');

INSERT INTO "public"."sys_device_info" (device_id, device_type, soft_version, organs, address, state)
VALUES ('DEV-001', 1, 'v3.11-20260320', 'Regional SOC Unit', 'Floor 5, Building B', '1');
