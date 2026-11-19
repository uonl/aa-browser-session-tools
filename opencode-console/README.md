# OpenCode 会话控制台

在 **Agents Anywhere 原生会话界面**里查看并操作 OpenCode 的所有会话——通过输入框工具栏的
「🌐 会话」按钮弹出的下拉面板（不是浏览器 tab）。

## 功能

- 输入框工具栏的「🌐 会话」按钮 → 弹出原生下拉面板
- 列出 OpenCode 的全部会话（按目录分组、可筛选）
- 点任意会话查看完整历史消息
- 底部输入框直接给该会话发消息继续聊

会话由你自己选，能看能操作。

## 用法

先启动本地服务：
```powershell
python opencode-console/server.py
```
（在 `aa-native-browser-tab` 目录下）

然后在 AA 的**新会话输入框**（或正常会话输入框）工具栏点「🌐 会话」按钮即可。

## 原理

- 前端补丁（`patch_asar_minimal.py`）在会话输入框工具栏注入按钮，并注入面板逻辑
  （`opencode-console/panel_inject.js`）——纯原生 DOM 面板，不依赖浏览器 tab
- 本地服务 `server.py`（默认 8891）通过 `opencode api` 命令（自动带认证）访问 OpenCode
  的 background service，不依赖固定端口（OpenCode 端口会变，`opencode api` 自动找）
- 列会话：`GET /api/session`；读消息：`GET /api/session/{id}/message`；
  发消息：`POST /api/session/{id}/prompt`

## 注意

- 需要 OpenCode Desktop 的 background service 在运行（`opencode service status` 可查看）
- 本地服务是前台进程，机器重启或被回收后需要重新运行启动命令
- 服务绑定 127.0.0.1，带 CORS 头供 aa-workbench 前端跨域访问
- 服务未启动时，面板会显示"服务未启动"，此时跑一下 `python opencode-console/server.py`
