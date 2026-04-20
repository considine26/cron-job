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
        # 核心修复：API 详情返回 jobDetails，列表返回直接的对象，或者嵌套在 job 里
        j = data
        for key in ["jobDetails", "job"]:
            if isinstance(data.get(key), dict):
                j = data[key]
                break
        
        # 映射字段
        self.job_id = j.get("jobId") or j.get("job_id") or data.get("jobId") or 0
        self.title = j.get("title") or data.get("title") or "未命名任务"
        self.url = j.get("url") or data.get("url") or "无 URL"
        self.enabled = j.get("enabled", data.get("enabled", False))
        self.folder_id = j.get("folderId", data.get("folderId", 0))
        self.schedule = j.get("schedule") or data.get("schedule", {})

    def update(self, **kwargs):
        return self.client.update_job(self.job_id, kwargs)

    def delete(self):
        return self.client.delete_job(self.job_id)

    def get_history(self):
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
        return {}

    def get_jobs(self):
        data = self._request("GET", "/jobs")
        jobs_data = data.get("jobs", []) if isinstance(data, dict) else []
        return [CronJob(self, j) for j in jobs_data]

    def get_job(self, job_id):
        data = self._request("GET", f"/jobs/{job_id}")
        return CronJob(self, data if isinstance(data, dict) else {})

    @staticmethod
    def _parse_part(cron_part, max_val, min_val=0):
        if cron_part == "*": return [-1]
        if "," in cron_part: return sorted(list(set(int(x.strip()) for x in cron_part.split(","))))
        if cron_part.startswith("*/"):
            step = int(cron_part.split("/")[1])
            return list(range(min_val, max_val + 1, step))
        if "-" in cron_part:
            start, end = map(int, cron_part.split("-"))
            return list(range(start, end + 1))
        return [int(cron_part)]

    @classmethod
    def parse_standard_cron(cls, cron_str):
        parts = cron_str.split()
        if len(parts) != 5: raise ValueError("需要 5 位 Cron 表达式")
        return {
            "minutes": cls._parse_part(parts[0], 59),
            "hours":   cls._parse_part(parts[1], 23),
            "mdays":   cls._parse_part(parts[2], 31, 1),
            "months":  cls._parse_part(parts[3], 12, 1),
            "wdays":   cls._parse_part(parts[4], 6, 0)
        }

    @staticmethod
    def to_cron_str(schedule):
        if not schedule: return "* * * * *"
        def _part_to_str(part_list, max_val):
            if not part_list or part_list == [-1]: return "*"
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
        if not schedule:
            schedule = {"timezone": "Asia/Shanghai", "hours": [-1], "mdays": [-1], "minutes": [-1], "months": [-1], "wdays": [-1]}
        payload = {"job": {"title": title, "url": url, "enabled": enabled, "schedule": schedule}}
        data = self._request("PUT", "/jobs", json=payload)
        return data.get("jobId")

    def update_job(self, job_id, job_data):
        return self._request("PATCH", f"/jobs/{job_id}", json={"job": job_data})

    def delete_job(self, job_id):
        return self._request("DELETE", f"/jobs/{job_id}")

    def get_job_history(self, job_id):
        data = self._request("GET", f"/jobs/{job_id}/history")
        return [HistoryItem(h) for h in data.get("history", [])]
