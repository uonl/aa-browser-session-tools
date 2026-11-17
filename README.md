# aa-native-browser-tab

> 给 **Agents Anywhere 2.2.0** 桌面版加一个真正原生的「浏览器」工具 tab，并附赠 **OpenCode 远程操控**注入。

## 这是什么

Agents Anywhere（AA）的会话页右侧有个工具侧栏，原生只有三个 tab：**审阅 / 终端 / 文件**。

本项目通过修改 AA 前端源码（`web-next`）并重新构建，往这个侧栏里加第四个原生 tab：**浏览器**。它和另外三个是同一层级、同一套 React 组件、同样的样式——不是浮在界面上的外挂窗口。

同时附赠一个 **OpenCode 远程操控**注入包：把 OpenCode 注册为 AA 的 ACP runtime，让你能在 AA 里直接创建 OpenCode 会话、远程下发任务。

## 效果

- 右侧工具侧栏出现四个整齐的卡片：审阅 / 终端 / 文件 / 🌐 浏览器
- 点「浏览器」tab，顶部 tab 标签栏出现 `🌐 Browser ×`，和原生 tab 完全一致
- 浏览器面板包含：地址栏（前进/后退/刷新）、Recent 最近访问、iframe 网页显示
- 深色主题，和 AA 界面一致

## 原理

AA 桌面端加载的前端是 `aa-workbench://web/` → `app.asar` 里的 `renderer/out/`（Next.js 静态导出）。

本项目：
1. 下载 AA **v2.2.0** 官方源码
2. 修改 4 个前端文件，加入 browser tab
3. 用 Node 22 + Yarn 4 构建静态前端
4. 把构建产物替换进 `app.asar` 的 `renderer/out/`

因为改的是源码而非压缩产物，所以 tab 是**真正原生**的。

## 安装

### 前置条件

- Windows，已安装 Agents Anywhere 2.2.0
- Node.js 22（脚本会检测，没有则自动下载到临时目录）
- 网络可访问 GitHub / nodejs.org

### 一键安装

```powershell
cd tools\aa-native-browser-tab
python apply.py
```

脚本会：
1. 备份当前 `app.asar`（`app.asar.bak_before_native_browser`）
2. 下载 v2.2.0 源码
3. 应用 `patch_webnext.py`
4. `yarn install && yarn build`（静态导出）
5. 把新前端写回 asar

**执行前请完全退出 Agents Anywhere**（托盘图标 → 退出）。完成后重新打开 AA 即可。

### 手动安装

见 [docs/manual.md](docs/manual.md)。

## 附赠：OpenCode 远程操控

目录 `opencode_remote/` 里是把 OpenCode 注入为 AA runtime 的补丁。

用法（同样需先退出 AA）：

```powershell
cd opencode_remote
python apply_opencode.py
```

它会把 OpenCode 注册为 ACP runtime（入口 `opencode acp`），重开 AA 后在「添加 Agent」里就能看到 OpenCode，创建会话即可远程操控。

详见 [opencode_remote/README.md](opencode_remote/README.md)。

## 卸载

```powershell
python apply.py --revert
python opencode_remote/apply_opencode.py --revert
```

或者手动把 `.bak` 备份文件覆盖回 `app.asar`。

## 注意事项

- AA 升级会覆盖 `app.asar`，升级后重跑安装脚本即可。
- 本项目修改的是本地安装文件，不会上传任何数据；构建脚本纯本地。
- iframe 受目标网站的 X-Frame-Options / CSP 限制，部分网站可能拒绝嵌入。本地 HTML（`file://`）和大多数允许嵌入的网站可正常使用。

## 许可

MIT
