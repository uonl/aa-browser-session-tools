# 会话绑定同步功能 —— 可行性研究

日期：2026-11-19

## 需求

在 AA 会话界面加「绑定 OpenCode 会话」按钮，用户选一个 OpenCode session 绑定后，
能读取对方的会话历史消息，之后消息实时互通。

## 现状调研

### 数据结构
- **OpenCode sessions/messages**：`G:\opencode-data\share\opencode\opencode.db`
  - `session_v2`：135 个 session（id / title / directory / time_updated）
  - `session_message`：32789 条消息（id / session_id / type / seq / data）
  - user 消息文本在 `data.text`；assistant 消息文本在 `data.content` 的 text 块里
- **AA sessions**：`%APPDATA%/Agents Anywhere/connector/connector-source/*/.../coordination.sqlite`
  - `records` 表（kind / id / body），关键 kind：`binding` / `projection` / `configuration`
  - `binding`：每个 AA session 已绑定一个 `agent_session_id`（即底层 OpenCode session）
  - `projection`：AA 会话的消息 timeline（type=message/tool，含 orderSeq / contentHash / source）

### 关键结论：AA 会话和它绑定的 OpenCode session 本来就是实时互通的
AA 通过 ACP 驱动底层 OpenCode session，二者是「同一个会话的两个界面」。所以
「绑定一对会话」本质是：**把某个 AA 会话的 `agent_session_id` 改成用户选的 OpenCode
session，并把那个 session 的历史消息灌进 AA 的 timeline**。

## POC 验证结果：直接改 sqlite 失败（已恢复原状）

尝试：停 AA → 直接改 coordination.sqlite（灌 17 条转换后的消息 + 改 binding）→ 重启 AA。

结果：
1. **AA 前端仍显示原会话内容** —— AA 前端读的是**云端 dashboard** 的数据，
   本地 projection 变更没有被推送到云端
2. **改 binding 后 Connector resume 新 session 失败** —— 会话变成「执行者已断开」
3. 已用备份 + 清除 WAL 完全恢复原状 ✓

**结论：不能靠直接改数据库实现。**

## 同步机制分析（为什么本地改动不生效）

Connector 的同步链路（`server/runtime_sync.py`）：
```
sync_existing_loop（每 30 秒）
  → sync_existing_once（遍历所有 runtime/session）
    → sync_existing_session
      → 若 session.metadata.sync.requires_timeline_sync == True：
           get_session_snapshot（从本地 projection 表读 timeline）
           → ingest_snapshot（推送到云端 dashboard）
      → 否则只推 meta/state，不推完整 timeline
```

**关键点**：普通空闲会话的 `requires_timeline_sync` 是 False，所以即使本地 projection
被改了，Connector 也不会重新推送 timeline —— 这就是 POC 失败的原因。

## 正规实现方案（可行，但工程量大）

要真正实现，必须走 Connector 的正规 store API + 触发同步：

1. **新增 Connector RPC**（如 `session.bindExternal`）：
   - 用 `app.store.put("projection", ...)` 写入转换后的消息（而非直接改 sqlite）
   - 用 `app.store.put("binding", ...)` 改 agent_session_id（保留 generation 一致性）
   - 把 session 标记为 changed / `requires_timeline_sync = True`，触发下一次同步推送
   - 走正规 `resume` 流程加载新 session（处理 generation 匹配）
2. **前端加按钮**：在 AA 会话界面注入「绑定 OpenCode 会话」按钮 + 会话选择下拉，
   调用新 RPC
3. **处理消息格式转换**：OpenCode content 块 → AA projection（user/assistant/tool）

### 难点 / 风险
- 改 binding 后 `resume` 的 generation 一致性（`owner_generation` / `connection_generation`）
  必须正确处理，否则会话变成「执行者已断开」（POC 中已遇到）
- 历史消息里有大量 tool 调用（POC 的 session 24 条消息里 17 条文本、其余 tool），
  tool 消息的 AA 格式转换更复杂
- Connector / AA 升级会覆盖注入的 RPC 和前端 patch，需要重跑注入脚本
- 改动 AA 核心会话机制，出错可能损坏会话数据

## 建议

- **如果要做**：先做 Connector RPC（命令行调用验证同步链路），确认能正确推送历史消息
  到云端并在 AA 界面显示，再加前端按钮
- **如果要稳**：保持现状不做。AA 会话已经和各自绑定的 OpenCode session 实时互通，
  用户想用哪个 OpenCode 会话，直接在 AA 里「新会话 → 选 OpenCode + 对应项目」即可

## 相关文件
- `session_bridge.py`：探索用脚本，`--list` 能列两边会话，`--bind ...`（不带 --apply）
  能预览消息转换。**注意：其 `--apply` 直接改 sqlite 的方式经验证不生效，不要使用。**
