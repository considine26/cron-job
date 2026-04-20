import os
import sys
import requests
import questionary
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class CronJobAPI:
    BASE_URL = "https://api.cron-job.org"

    def __init__(self, token):
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def _request(self, method, endpoint, json=None):
        try:
            url = f"{self.BASE_URL}{endpoint}"
            response = requests.request(method, url, headers=self.headers, json=json)
            response.raise_for_status()
            return response.json() if response.content else True
        except requests.exceptions.HTTPError as e:
            print(f"API 错误: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            print(f"请求失败: {e}")
            return None

    # Jobs API
    def list_jobs(self): return self._request("GET", "/jobs")
    def get_job(self, job_id): return self._request("GET", f"/jobs/{job_id}")
    def create_job(self, data): return self._request("PUT", "/jobs", json={"job": data})
    def update_job(self, job_id, data): return self._request("PATCH", f"/jobs/{job_id}", json={"job": data})
    def delete_job(self, job_id): return self._request("DELETE", f"/jobs/{job_id}")
    
    # History API
    def get_history(self, job_id): return self._request("GET", f"/jobs/{job_id}/history")
    def get_history_detail(self, job_id, identifier): 
        return self._request("GET", f"/jobs/{job_id}/history/{identifier}")

def format_stats(stats):
    if not stats: return "无统计数据"
    return (
        f"\n[ 性能统计 (HistoryItemStats) ]\n"
        f"DNS解析: {stats.get('nameLookup')}μs | TCP连接: {stats.get('connect')}μs\n"
        f"SSL握手: {stats.get('appConnect')}μs | 首字节(TTFB): {stats.get('startTransfer')}μs\n"
        f"总耗时: {stats.get('total')}μs"
    )

def manage_job(api, job_id):
    while True:
        # 获取最新详情
        res = api.get_job(job_id)
        if not res: break
        job = res.get("job", {})
        
        status_icon = "🟢" if job.get("enabled") else "🔴"
        print(f"\n--- 任务详情: {job.get('title')} [{status_icon}] ---")
        print(f"ID: {job_id} | URL: {job.get('url')}")
        
        action = questionary.select(
            "选择操作:",
            choices=[
                "查看最近执行历史",
                "切换 启用/禁用 状态",
                "修改任务信息 (标题/URL)",
                "删除任务",
                "返回主菜单"
            ]
        ).ask()

        if action == "查看最近执行历史":
            history_res = api.get_history(job_id)
            history = history_res.get("history", []) if history_res else []
            if not history:
                print("暂无执行历史。")
                continue
            
            h_choices = [
                questionary.Choice(
                    title=f"[{'OK' if h['status']==1 else 'ERR'}] {h['identifier']} - {h['httpStatus']}",
                    value=h
                ) for h in history[:10] # 仅显示最近10条
            ]
            h_choices.append("返回")
            selected_h = questionary.select("选择历史记录查看详情:", choices=h_choices).ask()
            
            if selected_h and selected_h != "返回":
                print(format_stats(selected_h.get("stats")))
                # 文档提到可以获取详情看 header/body，但列表已含大部分信息
                questionary.press_any_key_to_continue().ask()

        elif action == "切换 启用/禁用 状态":
            new_status = not job.get("enabled")
            if api.update_job(job_id, {"enabled": new_status}):
                print(f"已切换为: {'开启' if new_status else '关闭'}")
            questionary.press_any_key_to_continue().ask()

        elif action == "修改任务信息 (标题/URL)":
            new_title = questionary.text("新标题:", default=job.get('title')).ask()
            new_url = questionary.text("新URL:", default=job.get('url')).ask()
            if api.update_job(job_id, {"title": new_title, "url": new_url}):
                print("更新成功！")
            questionary.press_any_key_to_continue().ask()

        elif action == "删除任务":
            if questionary.confirm("确定要永久删除该任务吗？").ask():
                if api.delete_job(job_id):
                    print("任务已删除。")
                    break

        elif action == "返回主菜单" or action is None:
            break

def main():
    token = os.getenv("CRONJOB_TOKEN")
    if not token:
        print("错误: 请在 .env 中设置 CRONJOB_TOKEN")
        return

    api = CronJobAPI(token)
    
    while True:
        print("\n=== Cron-Job.org 专家管理面板 ===")
        choice = questionary.select(
            "请选择:",
            choices=[
                "列出所有任务",
                "创建新任务",
                "退出"
            ]
        ).ask()

        if choice == "列出所有任务":
            res = api.list_jobs()
            jobs = res.get("jobs", []) if res else []
            if not jobs:
                print("账户下没有任务。")
                continue
            
            job_choices = [
                questionary.Choice(
                    title=f"{'🟢' if j['enabled'] else '🔴'} {j['title']} (ID: {j['jobId']})",
                    value=j['jobId']
                ) for j in jobs
            ]
            job_choices.append("返回")
            selected_job_id = questionary.select("选择要管理的任务:", choices=job_choices).ask()
            
            if selected_job_id and selected_job_id != "返回":
                manage_job(api, selected_job_id)

        elif choice == "创建新任务":
            title = questionary.text("任务名称:").ask()
            url = questionary.text("目标 URL (需包含 http/https):").ask()
            if title and url:
                # 默认创建一个简单的每分钟执行一次的任务
                data = {
                    "title": title,
                    "url": url,
                    "enabled": True,
                    "saveResponses": True,
                    "schedule": {
                        "timezone": "Europe/Berlin",
                        "hours": [-1],
                        "mdays": [-1],
                        "minutes": [-1],
                        "months": [-1],
                        "wdays": [-1]
                    }
                }
                res = api.create_job(data)
                if res:
                    print(f"成功创建任务！ID: {res.get('jobId')}")
                questionary.press_any_key_to_continue().ask()

        elif choice == "退出" or choice is None:
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n退出。")
