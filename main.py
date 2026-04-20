import os
import sys
import questionary
from dotenv import load_dotenv
from cron_sdk import CronJobClient

# 加载环境变量
load_dotenv()

# 使用新的环境变量名
TOKEN = os.getenv("CRON_ORG_TOKEN")

def clear_screen():
    """跨平台清屏"""
    os.system('cls' if os.name == 'nt' else 'clear')

def format_stats(stats):
    return (
        f"\n[ 性能统计 ]\n"
        f"----------------------------------\n"
        f"DNS解析:    {stats.name_lookup:>10}μs\n"
        f"TCP连接:    {stats.connect:>10}μs\n"
        f"SSL握手:    {stats.app_connect:>10}μs\n"
        f"准备传输:   {stats.pre_transfer:>10}μs\n"
        f"首字节(TTFB): {stats.start_transfer:>10}μs\n"
        f"总耗时:      {stats.total:>10}μs\n"
        f"----------------------------------"
    )

def manage_job(job):
    while True:
        clear_screen()
        status_icon = "🟢" if job.enabled else "🔴"
        print(f"=== 任务管理: {job.title} ===")
        print(f"状态: {status_icon} | ID: {job.job_id}")
        print(f"URL:  {job.url}\n")
        
        action = questionary.select(
            "选择操作:",
            choices=[
                "查看历史详情 (HistoryItemStats)",
                "切换 启用/禁用",
                "修改基本信息 (标题/URL)",
                "修改 Cron 表达式",
                "删除任务",
                "返回主菜单"
            ]
        ).ask()

        if action == "查看历史详情 (HistoryItemStats)":
            # ... (保持不变)
            history = job.get_history()
            if not history:
                print("\n暂无执行历史。")
                questionary.press_any_key_to_continue().ask()
                continue
            
            h_choices = [
                questionary.Choice(
                    title=f"[{'OK' if h.status==1 else 'ERR'}] {h.identifier} - {h.http_status}",
                    value=h
                ) for h in history[:10]
            ]
            h_choices.append("返回")
            selected_h = questionary.select("选择历史:", choices=h_choices).ask()
            
            if selected_h and selected_h != "返回":
                print(format_stats(selected_h.stats))
                questionary.press_any_key_to_continue().ask()

        elif action == "切换 启用/禁用":
            new_status = not job.enabled
            if job.update(enabled=new_status):
                job.enabled = new_status
                print(f"\n✅ 已切换为: {'开启' if new_status else '关闭'}")
            questionary.press_any_key_to_continue().ask()

        elif action == "修改基本信息 (标题/URL)":
            new_title = questionary.text("新标题:", default=job.title).ask()
            new_url = questionary.text("新URL:", default=job.url).ask()
            if job.update(title=new_title, url=new_url):
                job.title, job.url = new_title, new_url
                print("\n✅ 基本信息更新成功！")
            questionary.press_any_key_to_continue().ask()

        elif action == "修改 Cron 表达式":
            new_cron_str = questionary.text(
                "新 Cron 表达式 (分 时 日 月 周):",
                default="* * * * *"
            ).ask()
            try:
                new_schedule = client.parse_standard_cron(new_cron_str)
                if job.update(schedule=new_schedule):
                    print(f"\n✅ Cron 表达式更新成功！")
                    print(f"⏰ 新调度: {new_cron_str}")
            except Exception as e:
                print(f"\n❌ 修改失败: {e}")
            questionary.press_any_key_to_continue().ask()

        elif action == "删除任务":
            if questionary.confirm("⚠️ 确定要永久删除该任务吗？").ask():
                if job.delete():
                    print("\n🗑️ 任务已删除。")
                    questionary.press_any_key_to_continue().ask()
                    break

        elif action == "返回主菜单" or action is None:
            break

def main():
    if not TOKEN:
        print("错误: 请在 .env 中设置 CRON_ORG_TOKEN")
        sys.exit(1)

    client = CronJobClient(TOKEN)
    
    while True:
        clear_screen()
        print("=== Cron-Job.org 管理面板 (Local SDK) ===")
        choice = questionary.select(
            "主菜单:",
            choices=[
                "列出所有任务",
                "创建新任务",
                "退出"
            ]
        ).ask()

        if choice == "列出所有任务":
            try:
                jobs = client.get_jobs()
                if not jobs:
                    print("\n账户下没有任务。")
                    questionary.press_any_key_to_continue().ask()
                    continue
                
                job_choices = [
                    questionary.Choice(
                        title=f"{'🟢' if j.enabled else '🔴'} {j.title} ({j.url})",
                        value=j
                    ) for j in jobs
                ]
                job_choices.append("返回")
                selected_job = questionary.select("选择要管理的任务:", choices=job_choices).ask()
                
                if selected_job and selected_job != "返回":
                    manage_job(selected_job)
            except Exception as e:
                print(f"\n❌ 操作失败: {e}")
                questionary.press_any_key_to_continue().ask()

        elif choice == "创建新任务":
            title = questionary.text("任务名称:").ask()
            url = questionary.text("目标 URL:").ask()
            cron_str = questionary.text(
                "Cron 表达式 (分 时 日 月 周, 例如: */15 * * * *):",
                default="* * * * *"
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

        elif choice == "退出" or choice is None:
            print("\n再见！")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        clear_screen()
        print("\n已退出。")
