# -*- coding: utf-8 -*-
"""AA 会话 ↔ OpenCode 会话绑定与消息桥接（脚本版 POC）。

⚠️ 注意：本脚本的 --apply（直接改 coordination.sqlite）经验证**不生效**——
AA 前端读云端 dashboard 数据，本地 projection 改动不会被推送到云端。
详见 docs/session-binding-feasibility.md。保留 --list / 预览功能供研究用，
不要用 --apply 修改生产数据。

流程：
  1. --list        列出 OpenCode sessions 和 AA sessions
  2. --bind <aa-session-prefix> <opencode-session-prefix> [--apply]
                   把选定 OpenCode session 的历史消息转换成 AA projection 格式，
                   写入 AA 会话，并改 binding 的 agent_session_id（--apply 才真正写）。
                   不带 --apply 只预览转换结果。

数据位置：
  OpenCode:  G:\\opencode-data\\share\\opencode\\opencode.db (session_message / session_v2)
  AA:        %APPDATA%/Agents Anywhere/connector/connector-source/*/.../coordination.sqlite
             的 records 表 (kind=binding / projection)

直接改内部数据库有风险：操作前请完全退出 Agents Anywhere 和 OpenCode Desktop。
脚本会自动备份 AA 的 coordination.sqlite。
"""
import os, sys, glob, json, sqlite3, hashlib, shutil, argparse, time

OC_DB = r'G:\opencode-data\share\opencode\opencode.db'
AA_DB_GLOB = r'C:\Users\sun67\.agents-anywhere\conn_CBGhjuuMLb6KGg\**\coordination.sqlite'


def open_aa_db(readonly=True):
    dbs = glob.glob(AA_DB_GLOB, recursive=True)
    if not dbs:
        raise SystemExit('未找到 AA coordination.sqlite')
    db = dbs[0]
    if readonly:
        return sqlite3.connect('file:' + db + '?mode=ro', uri=True), db
    return sqlite3.connect(db), db


def list_opencode_sessions(limit=40):
    c = sqlite3.connect('file:' + OC_DB + '?mode=ro', uri=True)
    rows = c.execute("""SELECT id, title, directory, time_updated,
        (SELECT COUNT(*) FROM session_message m WHERE m.session_id=s.id) AS nmsg
        FROM session_v2 s ORDER BY time_updated DESC LIMIT ?""", (limit,)).fetchall()
    c.close()
    return rows


def list_aa_sessions():
    c, db = open_aa_db()
    rows = c.execute("SELECT id,body FROM records WHERE kind='binding'").fetchall()
    out = []
    for k, b in rows:
        d = json.loads(b)
        out.append((k, d.get('agent_session_id', ''), d.get('profile_id', ''),
                    d.get('workspace', {}).get('canonical_path', '')))
    c.close()
    return out, db


def read_oc_messages(sid):
    c = sqlite3.connect('file:' + OC_DB + '?mode=ro', uri=True)
    rows = c.execute("SELECT id,type,seq,data FROM session_message WHERE session_id=? ORDER BY seq", (sid,)).fetchall()
    c.close()
    out = []
    for mid, typ, seq, data in rows:
        try:
            d = json.loads(data)
        except Exception:
            continue
        # user: text 字段；assistant: content 数组里的 text 块
        text = d.get('text', '')
        if (not text or not str(text).strip()) and isinstance(d.get('content'), list):
            parts = []
            for blk in d['content']:
                if isinstance(blk, dict) and blk.get('type') == 'text' and blk.get('text'):
                    parts.append(blk['text'])
            text = '\n\n'.join(parts)
        if isinstance(text, dict):
            text = json.dumps(text, ensure_ascii=False)
        if not isinstance(text, str):
            text = str(text)
        out.append((mid, typ, seq, text))
    return out


def to_aa_projection(aa_sid, msgs, start_seq):
    """把 OpenCode 消息转成 AA projection dict 列表。只处理 user/assistant 文本。"""
    out = []
    seq = start_seq
    for mid, typ, oc_seq, text in msgs:
        role = 'user' if typ == 'user' else 'assistant'
        if typ not in ('user', 'assistant'):
            continue
        if not text.strip():
            continue
        seq += 1
        content_hash = 'sha256:' + hashlib.sha256(text.encode('utf-8')).hexdigest()
        oid = 'br_' + mid
        rec = {
            'id': oid,
            'sessionId': aa_sid,
            'type': 'message',
            'role': role,
            'status': 'done',
            'content': {'kind': 'markdown', 'format': 'markdown', 'text': text, 'isThinking': False},
            'source': {'runtime': 'opencode', 'clientMessageId': mid},
            'orderSeq': seq,
            'revision': 1,
            'contentHash': content_hash,
        }
        out.append(rec)
    return out, seq


def max_order_seq(c, aa_sid):
    row = c.execute("""SELECT MAX(CAST(json_extract(body,'$.orderSeq') AS INTEGER))
        FROM records WHERE kind='projection' AND json_extract(body,'$.sessionId')=?""", (aa_sid,)).fetchone()
    return row[0] or 0


def do_bind(aa_prefix, oc_prefix, apply):
    # resolve sessions
    aa, _ = list_aa_sessions()
    aa_match = [x for x in aa if x[0].startswith(aa_prefix)]
    if len(aa_match) != 1:
        raise SystemExit(f'AA 会话前缀匹配到 {len(aa_match)} 个，请更精确: {aa_prefix}')
    aa_sid, old_agent, profile, ws = aa_match[0]

    ocs = list_opencode_sessions(200)
    oc_match = [x for x in ocs if x[0].startswith(oc_prefix)]
    if len(oc_match) != 1:
        raise SystemExit(f'OpenCode 会话前缀匹配到 {len(oc_match)} 个，请更精确: {oc_prefix}')
    oc_sid, oc_title = oc_match[0][0], oc_match[0][1]

    msgs = read_oc_messages(oc_sid)
    print(f'AA 会话: {aa_sid} (原绑定 {old_agent})')
    print(f'OpenCode: {oc_sid}  {oc_title}  ({len(msgs)} 条消息)')

    c, db = open_aa_db(readonly=not apply)
    start = max_order_seq(c, aa_sid)
    converted, end_seq = to_aa_projection(aa_sid, msgs, start)
    print(f'将写入 {len(converted)} 条 AA 消息, orderSeq {start+1}..{end_seq}')
    if converted:
        print('预览首条:', json.dumps(converted[0], ensure_ascii=False)[:400])

    if not apply:
        print('\n[预览模式] 未写入。加 --apply 才会真正写入并改绑定。')
        c.close()
        return

    # backup
    bak = db + '.bak_sessionbridge_' + str(int(time.time()))
    shutil.copy2(db, bak)
    print('备份:', bak)

    # write projections
    for rec in converted:
        c.execute("INSERT OR REPLACE INTO records(kind,id,body) VALUES('projection',?,?)",
                  (rec['id'], json.dumps(rec, ensure_ascii=False)))
    # update binding agent_session_id
    brow = c.execute("SELECT body FROM records WHERE kind='binding' AND id=?", (aa_sid,)).fetchone()
    if brow:
        b = json.loads(brow[0])
        b['agent_session_id'] = oc_sid
        b['revision'] = b.get('revision', 0) + 1
        c.execute("UPDATE records SET body=? WHERE kind='binding' AND id=?",
                  (json.dumps(b, ensure_ascii=False), aa_sid))
    c.commit()
    c.close()
    print('完成。请重启 AA 后查看会话。')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--bind', nargs=2, metavar=('AA_PREFIX', 'OC_PREFIX'))
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    if args.list:
        print('=== OpenCode sessions ===')
        for r in list_opencode_sessions():
            print(f'  {r[0]}  {r[1]}  ({r[4]} msg)  {r[2]}')
        print('\n=== AA sessions ===')
        aa, _ = list_aa_sessions()
        for k, agent, prof, ws in aa:
            print(f'  {k}  -> {agent}  [{prof}]  {ws}')
    elif args.bind:
        do_bind(args.bind[0], args.bind[1], args.apply)
    else:
        ap.print_help()


if __name__ == '__main__':
    main()
