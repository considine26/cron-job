import sys
import time
import questionary
from scripts.cron_sdk import CronJobClient
from scripts.account_manager import get_config, select_account
from scripts.job_manager import manage_job, clear_screen

def main():
    config = get_config()
    accounts = config["accounts"]
    api_base_url = config["api_base_url"]
    
    current_account_name, current_token, current_mail = select_account(accounts)
    client = CronJobClient(current_token, user_id=current_account_name, api_base_url=api_base_url)
    
    while True:
        clear_screen()
        try:
            usage = client.get_usage_count()
            print(f"=== Cron-Job.org 管理面板 [{current_account_name}] ===")
            print(f"账号邮箱: {current_mail}")
            print(f"当日API调用: {usage}/100")
        except Exception as e:
            print(f"=== Cron-Job.org 管理面板 [{current_account_name}] ===")
            print(f"账号邮箱: {current_mail}")
            print(f"⚠️ 获取API调用计数失败: {e}")

        choice = questionary.select(
            "主菜单:",
            choices=[
                "任务列表",
                "新建任务",
                "切换账号",
                "退出脚本"
            ]
        ).ask()

        if choice == "任务列表":
            try:
                time.sleep(0.3)
                jobs = client.get_jobs()
                if not jobs:
                    print("\n账户下没有任务。")
                    questionary.press_any_key_to_continue().ask()
                    continue
                
                job_choices = [
                    questionary.Choice(
                        title=f"{'🟢' if j.enabled else '🔴'} {j.title} ({j.url}) [{client.to_cron_str(j.schedule)}]",
                        value=j.job_id
                    ) for j in jobs
                ]
                job_choices.append("返回")
                selected_job_id = questionary.select("选择要管理的任务:", choices=job_choices).ask()
                
                if selected_job_id and selected_job_id != "返回":
                    manage_job(client, selected_job_id)
            except Exception as e:
                if "429" in str(e):
                    print("\n⚠️ 请求太频繁，请稍等...")
                    time.sleep(2)
                else:
                    print(f"\n❌ 操作失败: {e}")
                questionary.press_any_key_to_continue().ask()

        elif choice == "新建任务":
            title = questionary.text("任务名称:").ask()
            url = questionary.text("目标URL:").ask()
            cron_str = questionary.text(
                "Cron表达式 (分 时 日 月 周):",
                default="*/15 * * * *"
            ).ask()

            if title and url:
                try:
                    schedule = client.parse_standard_cron(cron_str)
                    job_id = client.create_job(title, url, schedule=schedule)
                    print(f"\n🎉 成功创建任务！ID: {job_id}")
                    print(f"⏰ 调度配置: {cron_str}")
                except Exception as e:
                    print(f"\n❌ 创建或解析失败: {e}")
                questionary.press_any_key_to_continue().ask()

        elif choice == "切换账号":
            current_account_name, current_token, current_mail = select_account(accounts)
            client = CronJobClient(current_token, user_id=current_account_name, api_base_url=api_base_url)
            print(f"\n✅ 已切换到账号: {current_account_name}")
            time.sleep(1)

        elif choice == "退出脚本" or choice is None:
            print("\n再见！")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        clear_screen()
        print("\n已退出。")
