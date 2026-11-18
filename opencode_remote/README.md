# OpenCode 远程操控注入

给 Agents Anywhere 注册 **OpenCode** 作为 ACP runtime，让你在 AA 里直接创建 OpenCode 会话、远程下发任务。

## 为什么需要

Agents Anywhere 2.2.0 自带的 runtime 只有 Codex / Claude / DSH / Pi / Hermes，**没有 OpenCode**。但 OpenCode v2 支持 `opencode acp`（Agent Client Protocol），可以作为一个标准 ACP Agent 接入。

本补丁把 OpenCode 的 ACP definition 注册进 AA 的 Connector 源码，重开 AA 后「添加 Agent」列表里就会出现 OpenCode。

## 用法

先完全退出 Agents Anywhere，然后：

```powershell
python apply_opencode.py             # 注入（含模型选择修复）
python apply_opencode.py --check     # 自动更新检测
python apply_opencode.py --status    # 查看状态
python apply_opencode.py --revert    # 恢复（含模型选择修复）
```

### 模型选择修复

AA 的全局模型选择器原本对 ACP runtime 返回空列表（ACP runtime 的 `list_model_catalog` 写死返回空），导致 OpenCode 会话里不能自由选模型。注入脚本会同时 patch `runtimes/acp/runtime.py`，让全局模型目录**合并所有 session 上报的模型配置**（OpenCode 在 `session/new` 时会上报全部可选模型），这样模型选择器就能正常列出所有模型。

`--revert` 会把这个 patch 一并还原。

脚本会自动找到 `~/.agents-anywhere/...` 或 `%APPDATA%/Agents Anywhere/connector/connector-source/<hash>/` 下正在运行的 Connector 源码并进行注册。

## 前置条件

- 本机已安装 OpenCode，且 `opencode acp` 可用
- 如果 `opencode` 不在 PATH，脚本会尝试常见安装路径（如 OpenCode Desktop 的 CLI 目录）

## 远程操控

注入后，在 AA 里：
1. 打开设备详情 → 添加 Agent → OpenCode
2. 选项目目录，创建会话
3. 在手机 / 平板 / Web 登录同一账号，即可远程继续这个会话、回复审批

Agent 在连接的工作设备上执行，模型和登录沿用本机 OpenCode 配置。

## 自动更新检测

注入的 `definition.py` 在每次被 Connector import 时会**动态探测**本机已安装的 `opencode-cli.exe`，按版本号从新到旧排序。所以：

- **OpenCode Desktop 升级后无需重跑注入脚本** —— 重启 AA（Connector 重新 import）就会自动使用新版本 CLI。
- `--check` 一键检测：显示当前探测到的 CLI 版本，并确认所有源码目录都是动态探测版（若发现旧版固定路径或未注入的目录会提示重跑）。
- `--status` 查看各源码目录的注入状态。

```powershell
python apply_opencode.py --check    # 自动更新检测
python apply_opencode.py --status   # 查看状态
```

## 注意

- **AA 升级会覆盖 Connector 源码**并重生成缓存目录，升级后重跑一次注入；脚本会自动发现所有目录（含新生成的）并注入。
- 本补丁只改 Connector 的 Python 源码（definition + provider 注册），不碰主程序。

### 疑难：模型下拉框点不开 / 悬停点击没反应

如果模型选择器能显示，但鼠标悬停/点击都没反应，先检查是不是 **OpenCode Desktop 的 GUI 窗口盖在了 AA 主窗口上**（标题可能带「远程控制 - OpenCode」）。OpenCode Desktop 窗口会抢焦点并拦截鼠标事件，导致 AA 收不到点击。

解决：把那个 OpenCode Desktop 窗口最小化或关掉（关 GUI 不影响 headless 的 `opencode-cli.exe acp` server，ACP 按需重启）。可以用任务管理器，或 PowerShell：

```powershell
Get-Process OpenCode -ErrorAction SilentlyContinue | Stop-Process -Force
```

另：带 `>` 箭头的模型需要**悬停展开二级菜单，再点具体档位**（Low/Medium/High/Default）才会真正切换；只点模型名本身不会切换。
