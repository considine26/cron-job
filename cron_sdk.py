import requests

class JobStats:
    def __init__(self, data):
        self.name_lookup = data.get("nameLookup", 0)
        self.connect = data.get("connect", 0)
        self.app_connect = data.get("appConnect", 0)
        self.pre_transfer = data.get("preTransfer", 0)
        self.start_transfer = data.get("startTransfer", 0)
        self.total = data.get("total", 0)

class HistoryItem:
    def __init__(self, data):
        self.identifier = data.get("identifier")
        self.status = data.get("status")
        self.http_status = data.get("httpStatus")
        self.date = data.get("date")
        self.stats = JobStats(data.get("stats", {}))

class CronJob:
    def __init__(self, client, data):
        self.client = client
        self.job_id = data.get("jobId")
        self.title = data.get("title")
        self.url = data.get("url")
        self.enabled = data.get("enabled")
        self.folder_id = data.get("folderId")
        self.schedule = data.get("schedule", {})

    def update(self, **kwargs):
        """更新任务属性"""
        return self.client.update_job(self.job_id, kwargs)

    def delete(self):
        """删除任务"""
        return self.client.delete_job(self.job_id)

    def get_history(self):
        """获取执行历史"""
        return self.client.get_job_history(self.job_id)

class CronJobClient:
    BASE_URL = "https://api.cron-job.org"

    def __init__(self, token):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def _request(self, method, endpoint, json=None):
        url = f"{self.BASE_URL}{endpoint}"
        response = requests.request(method, url, headers=self.headers, json=json)
        response.raise_for_status()
        if response.content:
            return response.json()
        return True

    def get_jobs(self):
        """列出所有任务"""
        data = self._request("GET", "/jobs")
        return [CronJob(self, j) for j in data.get("jobs", [])]

    def get_job(self, job_id):
        """获取单个任务详情"""
        data = self._request("GET", f"/jobs/{job_id}")
        return CronJob(self, data.get("job", {}))

    @staticmethod
    def _parse_part(cron_part, max_val, min_val=0):
        """解析 cron 的单个部分 (支持 *, */n, a-b, a,b)"""
        if cron_part == "*":
            return [-1]
        
        # 处理 1,2,3
        if "," in cron_part:
            return sorted(list(set(int(x.strip()) for x in cron_part.split(","))))
        
        # 处理 */5
        if cron_part.startswith("*/"):
            step = int(cron_part.split("/")[1])
            return list(range(min_val, max_val + 1, step))
        
        # 处理 0-5
        if "-" in cron_part:
            start, end = map(int, cron_part.split("-"))
            return list(range(start, end + 1))
        
        # 单个数字
        return [int(cron_part)]

    @classmethod
    def parse_standard_cron(cls, cron_str):
        """解析标准 5 位 Cron 表达式"""
        parts = cron_str.split()
        if len(parts) != 5:
            raise ValueError("Cron 表达式必须包含 5 个部分: 分 时 日 月 周")
        
        return {
            "minutes": cls._parse_part(parts[0], 59),
            "hours":   cls._parse_part(parts[1], 23),
            "mdays":   cls._parse_part(parts[2], 31, 1),
            "months":  cls._parse_part(parts[3], 12, 1),
            "wdays":   cls._parse_part(parts[4], 6, 0)
        }

    @staticmethod
    def to_cron_str(schedule):
        """将 API 的 schedule 字典转回 5 位 Cron 字符串"""
        if not schedule:
            return "* * * * *"
        
        def _part_to_str(part_list, max_val):
            if not part_list or part_list == [-1]:
                return "*"
            # 如果是连续的完整范围
            if len(part_list) > 1 and part_list == list(range(min(part_list), max(part_list) + 1)):
                if len(part_list) == max_val + 1: return "*"
                return f"{min(part_list)}-{max(part_list)}"
            return ",".join(map(str, sorted(part_list)))

        return " ".join([
            _part_to_str(schedule.get("minutes"), 59),
            _part_to_str(schedule.get("hours"), 23),
            _part_to_str(schedule.get("mdays"), 31),
            _part_to_str(schedule.get("months"), 12),
            _part_to_str(schedule.get("wdays"), 6)
        ])

    def create_job(self, title, url, enabled=True, schedule=None):
        """创建新任务，支持完整调度"""
        if not schedule:
            schedule = {
                "timezone": "Asia/Shanghai",
                "hours": [-1], "mdays": [-1], "minutes": [-1],
                "months": [-1], "wdays": [-1]
            }
        else:
            schedule["timezone"] = "Asia/Shanghai"

        payload = {
            "job": {
                "title": title,
                "url": url,
                "enabled": enabled,
                "schedule": schedule
            }
        }
        data = self._request("PUT", "/jobs", json=payload)
        return data.get("jobId")

    def update_job(self, job_id, job_data):
        """更新任务"""
        return self._request("PATCH", f"/jobs/{job_id}", json={"job": job_data})

    def delete_job(self, job_id):
        """删除任务"""
        return self._request("DELETE", f"/jobs/{job_id}")

    def get_job_history(self, job_id):
        """获取历史记录"""
        data = self._request("GET", f"/jobs/{job_id}/history")
        return [HistoryItem(h) for h in data.get("history", [])]
