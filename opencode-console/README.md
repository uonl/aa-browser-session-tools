# OpenCode 会话控制台

一个本地 Web 工具，让你在 **Agents Anywhere 的浏览器 tab 里**查看并操作 OpenCode 的所有会话。

## 功能

- 列出 OpenCode 的全部会话（按目录分组、可筛选、可刷新）
- 点击任意会话查看完整历史消息
- 在任意会话里直接发消息继续对话（调用 OpenCode 的 `/api/session/{id}/prompt`）

这样你就能在 AA 里"看"和"操作"任意 OpenCode 会话，会话由你自己选。

## 启动

```powershell
python tools\opencode-console\server.py --port 8891
```

然后在 AA 里打开任意一个会话 → 右侧工具侧栏点「🌐 浏览器」→ 地址栏输入：

```
http://127.0.0.1:8891
```

> 需要先在 AA 里打开一个会话，工具侧栏（审阅/终端/文件/浏览器）才会出现。

## 原理

- 服务启动时通过 `opencode api` 命令（自动带认证）访问 OpenCode 的本地 background service，
  所以不依赖固定端口（OpenCode 端口会变，`opencode api` 会自动找）
- 列会话：`GET /api/session`
- 读消息：`GET /api/session/{id}/message`
- 发消息：`POST /api/session/{id}/prompt`

## 注意

- 需要 OpenCode Desktop 的 background service 在运行（`opencode service status` 可查看）。
  如果 AA 里访问 8891 显示"连接失败"，先在终端跑一下 `opencode service status` 确认。
- 这个本地服务是前台进程，机器重启或被回收后需要重新运行启动命令。
- 服务绑定在 127.0.0.1，只有本机可访问。
