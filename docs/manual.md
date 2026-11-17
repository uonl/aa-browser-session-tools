# 手动安装 / 开发说明

## 目录结构

```
aa-native-browser-tab/
├── apply.py                  # 一键安装/回滚
├── patch_webnext.py          # web-next 源码补丁（加 browser tab）
├── asar_packer.py            # asar 读写工具
├── opencode_remote/          # 附赠：OpenCode 远程操控注入
│   ├── apply_opencode.py
│   └── README.md
└── README.md
```

## 改了哪些前端文件

补丁 `patch_webnext.py` 修改 v2.2.0 源码的 4 个文件：

1. `web-next/src/components/session-tool-tabs.ts`
   - `SessionToolKind` 加 `"browser"`
2. `web-next/src/components/session-tool-sidebar.tsx`
   - import `Globe` 图标
   - `TOOL_META` / `TOOL_KINDS` 加 browser（含 labelKey/descriptionKey 类型）
   - `handleOpenTool` 里排除 browser（它不是 workspace panel）
   - 内容区加 `tab.kind === "browser"` → `<BrowserPanel />`
   - 文件末尾加 `BrowserPanel` 组件：地址栏（前进/后退/刷新）+ Recent（localStorage）+ iframe
3. `web-next/messages/zh-CN.json` — 加 `browser` / `browserDescription`
4. `web-next/messages/en.json` — 同上

## 构建环境

- Node.js 22.16.0（`apply.py` 自动下载）
- Yarn 4.6.0（通过 Node 自带的 corepack 启用）
- 构建命令：`NEXT_OUTPUT=export yarn build`

`NEXT_OUTPUT=export` 让 Next.js 做静态导出，产物在 `web-next/out/`。

## asar 写回

`apply.py` 用 `asar_packer.py` 把 `out/` 下所有文件写进 `app.asar` 的 `renderer/out/`，并保留已有的 electron IPC 文件（main.js / preload.js / builtin-browser.js / browser-preload.js）。

## 开发调试

可以用 AA 的 dev 模式加载独立前端，避免反复替换 asar：

```powershell
$env:WORKBENCH_WEB_OUT_DIR = "path\to\web-next\out"
# 启动 AA
```

## 回滚

```powershell
python apply.py --revert
```

会把 `app.asar.bak_before_native_browser` 覆盖回去。
