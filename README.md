# Cron-Job.org CLI

这是一个专为 [Cron-Job.org](https://cron-job.org) 打造的交互式命令行（CLI）管理工具。支持多账号切换、任务状态控制、调度修改、执行历史与性能指标统计。

## ✨ 特性

- 🔑 **多账号灵活管理**：通过根目录的 `users.json` 轻松配置和管理多个账号及 API Token。
- 📊 **可视化数据**：提供当日 API 调用计数器（自动跟踪 `100` 次每日上限）、DNS解析/连接/首字节(TTFB)等性能指标历史。
- 🔄 **完善的任务管理**：
  - 支持交互式**新建任务**（自动解析 standard 5-field Cron 表达式）。
  - **单任务二级菜单**：支持启禁用切换、修改基本信息（标题、URL）、修改调度（Cron 表达式）、删除任务。
  - 查看最近 10 次的**调度执行历史**及耗时分析。

---

## 🛠️ 安装与准备

本工具使用 `uv` 统一进行项目与依赖管理。

1. **安装 uv**：
   如果您还未安装 `uv`，可以执行以下命令快速安装：

   ```bash
   # Windows (PowerShell)
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   
   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **克隆/进入项目目录**并安装依赖：

   ```bash
   uv sync
   ```

---

## ⚙️ 配置文件 `users.json`

请在项目根目录下创建 `users.json` 文件（项目已内置示例），格式如下：

```json
{
    "version": "1.0",
    "api_base_url": "https://api.cron-job.org",
    "profiles": {
        "edge": {
            "mail": "your-email-1@example.com",
            "api_token": "API Token"
        },
        "chrome": {
            "mail": "your-email-2@example.com",
            "api_token": "API Token"
        }
    }
}
```

> 📌 **如何获取 API Token**：
>
> 1. 登录 [Cron-Job.org 控制台](https://cron-job.org)。
> 2. 进入 `Settings` -> `API Tokens`。
> 3. 创建一个新的 Token 并将其复制到 `api_token` 字段中。

---

## 🚀 快速上手使用

在项目根目录下，您可以通过以下方式运行该管理工具：

### 方法一：通过命令行启动（推荐）

```bash
uv run main.py
```

### 方法二：双击批处理文件启动 (Windows)

在 Windows 环境下，您可以直接双击运行项目根目录下的：

```text
RunPython[uv].bat
```

它将自动使用 `uv` 环境拉起 `main.py` 主程序。

---

## 📂 代码结构说明

项目采用清晰的模块化拆分，方便维护与扩展：

```text
cron-job/
├── main.py                    # 主入口，控制 CLI 主循环菜单与跳转
├── users.json                 # 账号及全局 API 配置（需自行配置）
├── pyproject.toml             # uv 项目依赖与配置
├── RunPython[uv].bat          # Windows 快捷启动批处理
└── scripts/
    ├── __init__.py
    ├── cron_sdk.py            # 底层 API 封装与每日 API 限制计数器
    ├── account_manager.py     # 账号配置读取、解析与切换交互逻辑
    ├── job_manager.py         # 任务管理交互菜单与控制流程
    └── api_usage.json         # 自动生成，记录每个账号每日 API 的调用次数
```

---

## ⚠️ 注意事项

1. **API 调用限制**：Cron-Job.org 官方对免费账户的 API 调用有每日 `100` 次的限制。工具会在每次发出请求前自动校验并更新 `scripts/api_usage.json` 中的调用计数，以防超限被锁。
2. **Cron 表达式**：新建或修改调度时，请输入标准的 5 位 Cron 表达式（如 `*/15 * * * *` 表示每 15 分钟执行一次）。
