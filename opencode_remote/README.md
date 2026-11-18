# OpenCode 远程操控注入

给 Agents Anywhere 注册 **OpenCode** 作为 ACP runtime，让你在 AA 里直接创建 OpenCode 会话、远程下发任务。

## 为什么需要

Agents Anywhere 2.2.0 自带的 runtime 只有 Codex / Claude / DSH / Pi / Hermes，**没有 OpenCode**。但 OpenCode v2 支持 `opencode acp`（Agent Client Protocol），可以作为一个标准 ACP Agent 接入。

本补丁把 OpenCode 的 ACP definition 注册进 AA 的 Connector 源码，重开 AA 后「添加 Agent」列表里就会出现 OpenCode。

## 用法

先完全退出 Agents Anywhere，然后：

```powershell
python apply_opencode.py             # 注入
python apply_opencode.py --status    # 查看状态
python apply_opencode.py --revert    # 恢复
```

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
