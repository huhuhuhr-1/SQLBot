import random
import uuid
import argparse
from datetime import datetime, timedelta

class GCSGDataFactory:
    def __init__(self, conn_ops=None, conn_gov=None, conn_intel=None):
        # 三个库的连接句柄
        self.conn_ops = conn_ops
        self.conn_gov = conn_gov
        self.conn_intel = conn_intel
        
        # 预设业务锚点（确保跨库一致性）
        self.device_ids = [f"DEV-HQ-{i:04d}" for i in range(1, 501)]
        self.dept_ids = [f"DEPT-GLB-{i:03d}" for i in range(1, 101)]
        self.cve_names = [f"CVE-2024-{random.randint(1000, 9999)}" for _ in range(200)]

    def build_infrastructure(self):
        """第一阶段：在治理库和情报库构建基础数据（锚点）"""
        print("--- [Step 1] 正在同步治理库资产 (Governance)... ---")
        # 模拟执行: INSERT INTO sys_device_info ... (500 records)
        # 模拟执行: INSERT INTO sys_department ... (100 records)
        
        print("--- [Step 2] 正在同步情报库知识 (Intelligence)... ---")
        # 模拟执行: INSERT INTO ioc_cve_info ... (200 records)

    def irrigate_ops_data(self, count: int):
        """第二阶段：在运营库进行 10w+ 饱和式数据灌溉"""
        print(f"--- [Step 3] 正在向运营库 (Ops) 灌入 {count} 条核心告警数据... ---")
        batch_size = 5000
        start_time = datetime.now() - timedelta(days=30)
        
        for i in range(0, count, batch_size):
            chunk = []
            for _ in range(min(batch_size, count - i)):
                record = (
                    random.choice(self.device_ids),
                    f"ALRT-{uuid.uuid4().hex[:12].upper()}",
                    start_time + timedelta(seconds=random.randint(0, 30*24*3600)),
                    random.choice(["SQL Injection", "XSS", "RCE", "Malware", "Leak"]),
                    random.randint(1, 4),
                    random.choice(self.cve_names),
                    random.choice(self.dept_ids)
                )
                chunk.append(record)
            # 批量提交到 Ops 库
            # self.conn_ops.bulk_insert("alert_attack_all", chunk)
            print(f"进度: {min(i + batch_size, count)} / {count} 已就绪")

def main():
    parser = argparse.ArgumentParser(description="GCSG 跨库数据工厂")
    parser.add_argument("--count", type=int, default=100000, help="运营库灌溉总量")
    args = parser.parse_args()

    # 启动工厂
    factory = GCSGDataFactory()
    factory.build_infrastructure() # 构建跨库锚点
    factory.irrigate_ops_data(args.count) # 饱和式灌溉

if __name__ == "__main__":
    main()
