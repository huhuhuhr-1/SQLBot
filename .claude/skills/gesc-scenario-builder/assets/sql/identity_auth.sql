-- Identity & Auth Domain
-- Focused on Organizational Structure and Compliance Policies

-- sys_department
CREATE TABLE IF NOT EXISTS "public"."sys_department" (
  "id" SERIAL PRIMARY KEY,
  "depart_id" varchar(64) UNIQUE,
  "depart_name" varchar(128) NOT NULL,
  "depart_address" varchar(128),
  "device_id" varchar(32) NOT NULL,
  "depart_full_name" text,
  "company_name" varchar(64),
  "create_date" timestamp(6) DEFAULT CURRENT_TIMESTAMP,
  "update_date" timestamp(6) DEFAULT CURRENT_TIMESTAMP
);

-- policy_sensitive_info
CREATE TABLE IF NOT EXISTS "public"."policy_sensitive_info" (
  "id" SERIAL PRIMARY KEY,
  "dns_info" varchar(64),
  "rule_type" varchar(32),
  "match_type" varchar(16),
  "alert_level" varchar(16),
  "enable" int2 DEFAULT 1
);

-- Mock Data for Identity & Auth
INSERT INTO "public"."sys_department" (depart_id, depart_name, depart_address, device_id, depart_full_name, company_name)
VALUES ('DEP-101', 'Research & Development', 'Shanghai High-Tech Park', 'DEV-001', 'Global HQ / China Branch / R&D', 'Global-Tech Inc');

INSERT INTO "public"."policy_sensitive_info" (dns_info, rule_type, match_type, alert_level, enable)
VALUES ('*.github.com', 'DataExfiltration', 'Regex', 'High', 1);
