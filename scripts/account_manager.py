import json
import os
import sys
import questionary

def get_config():
    """从 users.json 加载账号配置与全局配置"""
    # 查找 users.json，兼容从根目录或 scripts 目录下运行的情况
    possible_paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "users.json"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json"),
        "users.json"
    ]
    json_path = None
    for path in possible_paths:
        if os.path.exists(path):
            json_path = path
            break
            
    config = {
        "api_base_url": "https://api.cron-job.org",
        "accounts": []
    }
    
    if not json_path:
        print("⚠️ 警告: 未找到 users.json 配置文件，将使用默认配置。")
        return config
        
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            config["api_base_url"] = data.get("api_base_url", "https://api.cron-job.org")
            profiles = data.get("profiles", {})
            for username, profile in profiles.items():
                config["accounts"].append({
                    "USER": username,
                    "MAIL": profile.get("mail", ""),
                    "CRON_ORG_TOKEN": profile.get("api_token", "")
                })
    except Exception as e:
        print(f"❌ 解析 users.json 失败: {e}")
        
    return config

def select_account(accounts):
    """选择要使用的账号"""
    if not accounts:
        print("❌ 错误: users.json 中未发现有效的账号配置（profiles）。请检查配置文件。")
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
