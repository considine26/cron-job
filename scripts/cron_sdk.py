import requests
import json
import os
from datetime import datetime

class JobStats:
# ... (rest of the file classes)
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
        self.duration = data.get("duration", 0)
        self.stats = JobStats(data.get("stats", {}))

class CronJob:
    def __init__(self, client, data):
        self.client = client
        # 兼容处理
        inner_data = data
        for wrapper in ["jobDetails", "job"]:
            if isinstance(data.get(wrapper), dict):
                inner_data = data[wrapper]
                break
        
        self.job_id = inner_data.get("jobId") or data.get("jobId")
        self.title = inner_data.get("title") or "未命名任务"
        self.url = inner_data.get("url") or "无 URL"
        self.enabled = inner_data.get("enabled", False)
        self.folder_id = inner_data.get("folderId", 0)
        self.schedule = inner_data.get("schedule", {})
        self.save_responses = inner_data.get("saveResponses", False)

    def update(self, **kwargs):
        return self.client.update_job(self.job_id, kwargs)

    def delete(self):
        return self.client.delete_job(self.job_id)

    def get_history(self):
        return self.client.get_job_history(self.job_id)

class CronJobClient:
    BASE_URL = "https://api.cron-job.org"
    USAGE_FILE = os.path.join(os.path.dirname(__file__), "api_usage.json")
    LIMIT = 100

    def __init__(self, token):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def _check_and_increment_usage(self):
        today = datetime.now().strftime("%Y-%m-%d")
        usage = {"date": today, "count": 0}
        
        if os.path.exists(self.USAGE_FILE):
            try:
                with open(self.USAGE_FILE, "r") as f:
                    data = json.load(f)
                    if data.get("date") == today:
                        usage = data
            except:
                pass

        if usage["count"] >= self.LIMIT:
            raise Exception(f"每日 API 调用已达上限 ({self.LIMIT})，请明日再试。")

        usage["count"] += 1
        with open(self.USAGE_FILE, "w") as f:
            json.dump(usage, f)

    def get_usage_count(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if os.path.exists(self.USAGE_FILE):
            try:
                with open(self.USAGE_FILE, "r") as f:
                    data = json.load(f)
                    if data.get("date") == today:
                        return data.get("count", 0)
            except:
                pass
        return 0

    def _request(self, method, endpoint, json=None):
        self._check_and_increment_usage()
        url = f"{self.BASE_URL}{endpoint}"
        response = requests.request(method, url, headers=self.headers, json=json)
        
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if method == "DELETE" and response.status_code == 404:
                return True
            raise e

        if response.content:
            try:
                data = response.json()
                # 如果返回的是空字典，也视为 True
                return data if data else True
            except:
                return True
        return True

    def get_jobs(self):
        data = self._request("GET", "/jobs")
        return [CronJob(self, j) for j in data.get("jobs", [])]

    def get_job(self, job_id):
        data = self._request("GET", f"/jobs/{job_id}")
        return CronJob(self, data)

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

    def get_history_detail(self, job_id, identifier):
        data = self._request("GET", f"/jobs/{job_id}/history/{identifier}")
        return HistoryItem(data.get("jobHistoryDetails", {}))

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
