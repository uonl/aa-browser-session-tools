# aa-native-browser-tab

> 给 **Agents Anywhere 2.2.0** 桌面版加一个原生「浏览器」工具 tab，并附赠 **OpenCode 远程操控**注入。

## 这是什么

Agents Anywhere（AA）的会话页右侧工具有三个 tab：**审阅 / 终端 / 文件**。本项目加第四个：**🌐 浏览器**——和另外三个同一 React 组件层级、同样式，不是浮层窗口。

## 效果

- 右侧工具侧栏出现四个整齐的卡片：审阅 / 终端 / 文件 / 🌐 浏览器
- 点「浏览器」tab 打开浏览器面板：地址栏（前进/后退/刷新/关闭）+ Recent 最近访问 + iframe 网页显示
- 深色主题，和 AA 界面一致

## 原理（重要）

AA 桌面端前端是 `aa-workbench://web/` → `app.asar` 里的 `renderer/out/`（编译后的 Next.js chunk）。

**本项目只在原版编译 chunk 上做最小手术**：
- `patch_asar_minimal.py` 只改 2 个 chunk 文件（`0axsoae8j5mxk.js` UI + `233tc332t4hy3.js` 翻译），往里注入 browser tab 定义和 BrowserPanel 组件
- 其它 233 个 chunk **完全不动** —— 登录、WebSocket、API 全部保持原版行为

> ⚠️ **不要用 `apply.py` / `patch_webnext.py`**（源码重建方案）！从 GitHub v2.2.0 源码重新构建的前端和实际打包版本不一致，会导致 WebSocket 连成 `ws://web/...` 而 502、界面卡死。`patch_asar_minimal.py` 是当前唯一可用的方案。

## 安装

### 前置条件
- Windows，已安装 Agents Anywhere 2.2.0
- Python 3（任意版本）

### 一键安装
```powershell
cd D:\文字\tools\aa-native-browser-tab
python patch_asar_minimal.py --apply
```
脚本会：
1. 自动备份原版 `app.asar`（`app.asar.bak_before_minimal_browser`）
2. 在原版 chunk 上注入浏览器 tab
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

## 注意事项

- AA 升级会覆盖 `app.asar`，升级后重跑 `patch_asar_minimal.py --apply`。
- iframe 受目标网站 X-Frame-Options / CSP 限制，本地 HTML（`file://`）和允许嵌入的网站可正常使用。
- 本项目修改本地安装文件，不上传任何数据。

## 许可

MIT
