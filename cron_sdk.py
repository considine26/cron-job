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
    def parse_cron_list(cron_str, max_val):
        """
        将简单的 cron 字符串解析为列表
        '*' -> [-1]
        '*/5' -> [0, 5, 10, ...]
        '1,2,3' -> [1, 2, 3]
        '0-5' -> [0, 1, 2, 3, 4, 5]
        """
        if cron_str == "*":
            return [-1]
        
        if cron_str.startswith("*/"):
            step = int(cron_str.split("/")[1])
            return list(range(0, max_val + 1, step))
        
        if "," in cron_str:
            return [int(x.strip()) for x in cron_str.split(",")]
        
        if "-" in cron_str:
            start, end = map(int, cron_str.split("-"))
            return list(range(start, end + 1))
        
        try:
            return [int(cron_str)]
        except ValueError:
            return [-1]

    def create_job(self, title, url, enabled=True, minutes=None):
        """创建新任务，支持自定义分钟"""
        schedule = {
            "timezone": "Asia/Shanghai",  # 默认改为北京时间
            "hours": [-1],
            "mdays": [-1],
            "minutes": minutes if minutes else [-1],
            "months": [-1],
            "wdays": [-1]
        }
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
