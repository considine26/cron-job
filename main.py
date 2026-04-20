import os
import sys
import time
import questionary
from dotenv import load_dotenv
from scripts.cron_sdk import CronJobClient

# 加载环境变量
load_dotenv()

# 加载环境变量 (不推荐使用 load_dotenv 处理这类结构)

def get_accounts():
    """从 .env 文件手动解析块状结构的账号信息"""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    accounts = []
    current_account = {}
    
    if not os.path.exists(env_path):
        return []
        
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    
                    # 遇到 USER 且当前已有数据，说明新的一块开始了
                    if key == "USER" and current_account:
                        accounts.append(current_account)
                        current_account = {}
                    
                    current_account[key] = value
            if current_account:
                accounts.append(current_account)
    except Exception as e:
        print(f"解析 .env 失败: {e}")
        
    return accounts

def select_account(accounts):
    """选择要使用的账号"""
    if not accounts:
        print("错误: .env 文件为空或格式不正确。请确保包含 USER, MAIL, CRON_ORG_TOKEN。")
        sys.exit(1)
        
    if len(accounts) == 1:
        acc = accounts[0]
        return acc.get("USER", "未命名"), acc.get("CRON_ORG_TOKEN"), acc.get("MAIL", "")
        
    choices = [
        questionary.Choice(
            title=f"{acc.get('USER')} ({acc.get('MAIL')})",
            value=acc
        ) for acc in accounts
    ]
    choices.append(questionary.Choice(title="退出脚本", value="EXIT"))
    
    selected = questionary.select(
        "请选择要管理的账号:",
        choices=choices
    ).ask()
    
    if selected == "EXIT" or selected is None:
        sys.exit(0)
        
    return selected.get("USER", "未命名"), selected.get("CRON_ORG_TOKEN"), selected.get("MAIL", "")

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

def manage_job(client, job_id):
    while True:
        try:
            time.sleep(0.3) # 防抖
            job = client.get_job(job_id)
            if not job:
                print("\n❌ 无法获取任务详情。")
                questionary.press_any_key_to_continue().ask()
                break
        except Exception as e:
            if "429" in str(e):
                print("\n⚠️ 请求太频繁 (429)，正在自动重试...")
                time.sleep(2)
                continue
            print(f"\n❌ 操作失败: {e}")
            questionary.press_any_key_to_continue().ask()
            break

        clear_screen()
        status_icon = "🟢" if job.enabled else "🔴"
        current_cron = client.to_cron_str(job.schedule)
        
        print(f"=== 任务管理: {job.title} ===")
        print(f"状态: {status_icon} | ID: {job.job_id}")
        print(f"URL:  {job.url}")
        print(f"调度: {current_cron}\n")
        
        action = questionary.select(
            "选择操作:",
            choices=[
                "调度历史 (HistoryItemStats)",
                "切换状态 (启用/禁用)",
                "修改信息 (标题/URL)",
                "修改调度 (Cron表达式)",
                "删除任务",
                "返回菜单"
            ]
        ).ask()

        if action == "调度历史 (HistoryItemStats)":
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

        elif action == "切换状态 (启用/禁用)":
            new_status = not job.enabled
            if job.update(enabled=new_status):
                print(f"\n✅ 已切换为: {'开启' if new_status else '关闭'}")
            questionary.press_any_key_to_continue().ask()

        elif action == "修改信息 (标题/URL)":
            new_title = questionary.text("新标题:", default=str(job.title or "")).ask()
            new_url = questionary.text("新URL:", default=str(job.url or "")).ask()
            if new_title and new_url:
                if job.update(title=new_title, url=new_url):
                    print("\n✅ 基本信息更新成功！")
            questionary.press_any_key_to_continue().ask()

        elif action == "修改调度 (Cron表达式)":
            new_cron_str = questionary.text(
                "输入新 Cron 表达式 (分 时 日 月 周):",
                default=current_cron
            ).ask()
            try:
                new_schedule = job.client.parse_standard_cron(new_cron_str)
                if job.update(schedule=new_schedule):
                    print(f"\n✅ Cron 表达式更新成功！")
            except Exception as e:
                print(f"\n❌ 修改失败: {e}")
            questionary.press_any_key_to_continue().ask()

        elif action == "删除任务":
            if questionary.confirm("⚠️ 确定要永久删除该任务吗？").ask():
                if job.delete():
                    print("\n🗑️ 任务已删除。")
                    questionary.press_any_key_to_continue().ask()
                    break

        elif action == "返回菜单" or action is None:
            break

def main():
    accounts = get_accounts()
    current_account_name, current_token, current_mail = select_account(accounts)
    
    client = CronJobClient(current_token, user_id=current_account_name)
    
    while True:
        clear_screen()
        usage = client.get_usage_count()
        print(f"=== Cron-Job.org 管理面板 [{current_account_name}] ===")
        print(f"账号邮箱: {current_mail}")
        print(f"当日API调用: {usage}/100")
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
            client = CronJobClient(current_token, user_id=current_account_name)
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
