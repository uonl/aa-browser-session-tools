# aa-native-browser-tab

> 给 **Agents Anywhere 2.2.0** 桌面版加一个原生「浏览器」工具 tab，并附赠 **OpenCode 远程操控**注入。

## 这是什么

Agents Anywhere（AA）的会话页右侧工具有三个 tab：**审阅 / 终端 / 文件**。本项目加第四个：**🌐 浏览器**——和另外三个同一 React 组件层级、同样式，不是浮层窗口。

## 效果

- 右侧工具侧栏出现四个整齐的卡片：审阅 / 终端 / 文件 / 🌐 浏览器（中英文自动适配）
- 点「浏览器」tab 打开浏览器面板：地址栏（后退/前进/刷新/关闭）+ 新标签页大搜索栏 + Recent 最近访问 + iframe 网页显示
- 地址栏输入网址直接打开，输入关键词 800ms 后自动用 Bing 搜索（回车/搜索按钮也行）
- 对话里的链接、`<code>` URL、文件路径点击会在浏览器 tab 打开，不跳系统浏览器
- 搜索结果页里的链接（含 `target="_blank"`）**在内置浏览器里跳转**，不开系统浏览器
- 多个浏览器标签页各有独立 id，关一个不会把其它的一起关掉
- 深色主题，和 AA 界面一致

## 原理（重要）

AA 桌面端前端是 `aa-workbench://web/` → `app.asar` 里的 `renderer/out/`（编译后的 Next.js chunk）。主进程在 `dist/electron/main.js`，preload 在 `dist/electron/preload.js`。

**本项目只在原版文件上做最小手术**（`patch_asar_minimal.py`）：

| 文件 | 改动 |
|---|---|
| `renderer/out/_next/static/chunks/0axsoae8j5mxk.js` | 注入 browser tab 定义 + BrowserPanel 组件 + 地址栏/搜索栏 + 全局点击拦截 |
| `renderer/out/_next/static/chunks/233tc332t4hy3.js` | 加中英文界面标签 |
| `renderer/out/_next/static/chunks/31airuwdveg0l.js` | markdown 链接/文件路径点击拦截 |
| `dist/electron/main.js` | `setWindowOpenHandler`：外链弹窗不再 `shell.openExternal`，改发 IPC `aa:open-in-browser` |
| `dist/electron/preload.js` | 暴露 `browser.onOpen` 给渲染层订阅该 IPC |

其余 231 个 chunk **完全不动** —— 登录、WebSocket、API 全部保持原版行为。

> ⚠️ **不要从 GitHub v2.2.0 源码重新构建前端**：重建产物和实际打包版本不一致，会导致 WebSocket 连成 `ws://web/...` 而 502、界面卡死。`patch_asar_minimal.py` 是在原版文件上做最小注入，是当前唯一可用的方案。

## 安装

### 前置条件
- Windows，已安装 Agents Anywhere 2.2.0
- Python 3（任意版本）

### 一键安装
```powershell
cd <本项目目录>
python patch_asar_minimal.py --apply
```
脚本会：
1. 自动备份原版 `app.asar`（`app.asar.bak_before_minimal_browser`）
2. 在上述 5 个文件上做最小注入
3. 写回 asar

**执行前请完全退出 Agents Anywhere**（托盘图标 → 退出）。完成后重新打开即可。

## 卸载

```powershell
# 把备份覆盖回去
Copy-Item "G:\anywhere\Agents Anywhere\resources\app.asar.bak_before_minimal_browser" "G:\anywhere\Agents Anywhere\resources\app.asar" -Force
```
（同样需先退出 AA）

## 附赠：OpenCode 远程操控

`opencode_remote/` 目录里是把 OpenCode 注册为 AA ACP runtime 的注入包。详情见 [opencode_remote/README.md](opencode_remote/README.md)。

## 附赠：在 AA 原生界面查看/操作 OpenCode 会话

AA 输入框工具栏里注入了一个 **「🌐 会话」按钮**（在附件图标旁边）。点它弹出原生下拉面板：

- 列出 OpenCode 的全部会话（按目录分组、可筛选）
- 点任意会话查看完整历史消息
- 底部输入框可直接给该会话发消息继续聊

实现：本补丁在前端注入按钮和面板 JS（`opencode-console/panel_inject.js`），数据源是本地服务
`opencode-console/server.py`（默认 8891 端口），它通过 `opencode api` 命令访问 OpenCode。

**使用前先启动本地服务**：
```powershell
python opencode-console/server.py
```
然后点 AA 输入框的「🌐 会话」按钮即可。服务绑定 127.0.0.1，机器重启后需重跑。

详情见 [opencode-console/README.md](opencode-console/README.md)。

## 注意事项

- AA 升级会覆盖 `app.asar`，升级后重跑 `patch_asar_minimal.py --apply`。
- iframe 受目标网站 X-Frame-Options / CSP 限制，本地 HTML（`file://`）和允许嵌入的网站可正常使用。
- 本项目修改本地安装文件，不上传任何数据。

## 许可

MIT
