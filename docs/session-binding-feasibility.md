# 会话绑定同步功能 —— 可行性研究（最终）

日期：2026-11-19

## 需求
让 AA 能读取任意 OpenCode session（不只是它绑定的那个），用户自己选读哪个。

## 核心发现：AA 后端本来就有这个机制！

深入研究 Connector 源码（`runtimes/acp/runtime.py`、`server/runtime_session_rpc.py`）发现：

1. **`session.discover` RPC**（`server/runtime_session_rpc.py:21`）：
   - 调 `runtime.list_sessions()`（`runtimes/acp/runtime.py:462`）
   - 后者通过 `inventory_client.list_sessions()` 调 OpenCode ACP 的 `session/list`，
     实测 OpenCode 声明了 `sessionCapabilities.list` 且能返回全部 135 个 session
   - 为每个未绑定的 session 生成 `acp_native_xxx` 的 AA sessionId，存 `native_inventory`，
     标记 `readOnly: True`

2. **`session.sync` RPC**（`server/runtime_session_rpc.py:58`）：
   - `runtime.get_session_snapshot()`（`runtimes/acp/runtime.py:505`）对 native session
     调用 **`aa/read_history`** 扩展读取该 session 的完整历史消息
   - 通过 `host.timeline_sync()` 把历史推送到云端 dashboard

3. 所以理论上：调用 `session.discover` 导入 sessions → AA 前端打开某个 native session →
   Connector 用 `aa/read_history` 读历史 → 推到云端 → AA 界面显示。**整条链路后端都现成。**

## 障碍（为什么现在用不了）

1. **ACP runtime 的 `sync_mode = "events"`**（`runtimes/acp/runtime.py:71`）：
   `sync_existing_once` 对 events runtime 直接 `continue`，所以 `list_sessions` 从不被
   自动调用，`native_inventory` 永远是空（实测 0 条）

2. **AA 前端完全没有 discover 入口**：
   遍历 app.asar 所有 JS chunk，搜不到任何 `discover` / `session.discover` 代码。
   前端不会主动调用这个 RPC。

3. **connector-source 目录不稳定**：实验性手动 patch `runtime.py` 后，AA 重启会把
   connector-source 还原/换新 hash 目录，非注入脚本的改动会丢失。所有持久补丁必须
   写进 `apply_opencode.py` 并在每次重启后重跑。

## 直接改 sqlite 的方案（已证伪，已恢复）
POC：停 AA → 灌 projection + 改 binding → 重启。结果：AA 前端读云端数据，本地改动
不同步；改 binding 导致 resume 失败「执行者已断开」。已用备份完全恢复。

## 可行的实现路径（若要继续）
1. 把「自动 discover」写进 `apply_opencode.py`（注入时 patch ACP runtime 的
   `list_sessions` 调用逻辑），重启后重跑注入使其生效
2. 解决 events 模式下 native sessions 的 meta 如何推到云端（events runtime 的
   `discover_sessions` 不推 meta，需走 `resynchronize` 或类似路径）
3. 前端加「导入/选择 OpenCode 会话」按钮，调用 dashboard 的 discover RPC，展示列表

工作量：中等偏大；风险：改动 Connector 核心同步机制 + 前端，升级易失效。

## 保守建议
AA 会话已和各自绑定的 OpenCode session 实时互通。若要读某个 OpenCode session 的历史，
最稳妥的是在 OpenCode 里直接看，或在 AA 里「新会话 → 选 OpenCode」开新会话。

## 相关文件
- `session_bridge.py`：`--list` 可列两边会话；`--bind ...` 可预览转换。其 `--apply`
  直接改 sqlite 经验证不生效，不要使用。
- `apply_opencode.py`：所有持久补丁的正确入口。
