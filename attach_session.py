# -*- coding: utf-8 -*-
"""把某个 AA 会话 attach 到任意 OpenCode session（能看能操作）。

用法：先完全退出 AA，再运行：
    python attach_session.py --list
    python attach_session.py attach <aa前缀> <opencode前缀>
    python attach_session.py detach              # 从备份恢复

原理：改 AA binding 的 agent_session_id 指向目标 OpenCode session（保持 generation 等
其它字段不变），灌入该 session 的历史消息，清除 WAL 使改动落盘。启动 AA 后需在会话里
点一次「恢复会话」，Connector 会用新 agent_session_id 走正规 resume 流程。

操作前自动备份 coordination.sqlite。
"""
import os, sys, glob, json, sqlite3, hashlib, shutil, time, argparse

AA_DB_GLOB = r'C:\Users\sun67\.agents-anywhere\conn_CBGhjuuMLb6KGg\**\coordination.sqlite'
OC_DB = r'G:\opencode-data\share\opencode\opencode.db'


def aa_db():
    dbs = glob.glob(AA_DB_GLOB, recursive=True)
    if not dbs: raise SystemExit('未找到 AA coordination.sqlite')
    return dbs[0]


def list_all():
    db = aa_db()
    c = sqlite3.connect('file:' + db + '?mode=ro', uri=True)
    print('=== AA sessions ===')
    for k, b in c.execute("SELECT id,body FROM records WHERE kind='binding'").fetchall():
        d = json.loads(b)
        print(f'  {k}  -> {d.get("agent_session_id")}  gen={d.get("owner_generation","")[:12]}  {d.get("workspace",{}).get("canonical_path","")}')
    c.close()
    print('\n=== OpenCode sessions ===')
    c = sqlite3.connect('file:' + OC_DB + '?mode=ro', uri=True)
    for r in c.execute("""SELECT s.id,s.title,s.directory,(SELECT COUNT(*) FROM session_message m WHERE m.session_id=s.id) n
        FROM session_v2 s WHERE s.title IS NOT NULL ORDER BY s.time_updated DESC LIMIT 40"""):
        print(f'  {r[0]}  {r[1]}  ({r[3]} msg)  {r[2]}')
    c.close()


def read_oc_messages(sid):
    c = sqlite3.connect('file:' + OC_DB + '?mode=ro', uri=True)
    rows = c.execute("SELECT id,type,seq,data FROM session_message WHERE session_id=? ORDER BY seq", (sid,)).fetchall()
    c.close()
    out = []
    for mid, typ, seq, data in rows:
        try: d = json.loads(data)
        except: continue
        text = d.get('text', '')
        if (not text or not str(text).strip()) and isinstance(d.get('content'), list):
            parts = [b['text'] for b in d['content'] if isinstance(b, dict) and b.get('type') == 'text' and b.get('text')]
            text = '\n\n'.join(parts)
        if not isinstance(text, str): text = str(text)
        out.append((mid, typ, seq, text))
    return out


def attach(aa_prefix, oc_prefix):
    db = aa_db()
    # resolve
    c = sqlite3.connect('file:' + db + '?mode=ro', uri=True)
    aa = [(k, json.loads(b)) for k, b in c.execute("SELECT id,body FROM records WHERE kind='binding'").fetchall()]
    c.close()
    am = [x for x in aa if x[0].startswith(aa_prefix)]
    if len(am) != 1: raise SystemExit(f'AA 前缀匹配 {len(am)} 个')
    aa_sid, binding = am[0]
    old_agent = binding.get('agent_session_id')

    c = sqlite3.connect('file:' + OC_DB + '?mode=ro', uri=True)
    ocs = c.execute("SELECT id,title FROM session_v2 WHERE id LIKE ?", (oc_prefix + '%',)).fetchall()
    c.close()
    if len(ocs) != 1: raise SystemExit(f'OpenCode 前缀匹配 {len(ocs)} 个')
    oc_sid, oc_title = ocs[0]

    msgs = read_oc_messages(oc_sid)
    print(f'AA: {aa_sid} (原 {old_agent})')
    print(f'OpenCode: {oc_sid} {oc_title} ({len(msgs)} 条)')

    # backup + clear WAL
    ts = str(int(time.time()))
    for suffix in ['', '-wal', '-shm']:
        p = db + suffix
        if os.path.exists(p):
            shutil.copy2(p, p + '.bak_attach_' + ts)
    for suffix in ['-wal', '-shm']:
        p = db + suffix
        if os.path.exists(p): os.remove(p)
    print('备份 + 清除 WAL 完成')

    c = sqlite3.connect(db)
    # 1) write history messages
    start = c.execute("""SELECT COALESCE(MAX(CAST(json_extract(body,'$.orderSeq') AS INTEGER)),0)
        FROM records WHERE kind='projection' AND json_extract(body,'$.sessionId')=?""", (aa_sid,)).fetchone()[0]
    n = 0
    for mid, typ, oseq, text in msgs:
        if typ not in ('user', 'assistant') or not text.strip(): continue
        n += 1
        rec = {
            'id': 'att_' + mid,
            'sessionId': aa_sid,
            'type': 'message',
            'role': 'user' if typ == 'user' else 'assistant',
            'status': 'done',
            'content': {'kind': 'markdown', 'format': 'markdown', 'text': text, 'isThinking': False},
            'source': {'runtime': 'opencode', 'clientMessageId': mid},
            'orderSeq': start + n,
            'revision': 1,
            'contentHash': 'sha256:' + hashlib.sha256(text.encode('utf-8')).hexdigest(),
        }
        c.execute("INSERT OR REPLACE INTO records(kind,id,body) VALUES('projection',?,?)", (rec['id'], json.dumps(rec, ensure_ascii=False)))
    # 2) change binding agent_session_id ONLY (keep generation etc.)
    binding['agent_session_id'] = oc_sid
    binding['revision'] = binding.get('revision', 0) + 1
    c.execute("UPDATE records SET body=? WHERE kind='binding' AND id=?", (json.dumps(binding, ensure_ascii=False), aa_sid))
    c.commit()
    # force checkpoint to flush WAL then clear it again
    try: c.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    except: pass
    c.close()
    for suffix in ['-wal', '-shm']:
        p = db + suffix
        if os.path.exists(p):
            try: os.remove(p)
            except: pass
    print(f'完成：写入 {n} 条历史，绑定改为 {oc_sid}')
    print('请启动 AA，然后在该会话点一次「恢复会话」。')


def detach():
    db = aa_db()
    baks = sorted(glob.glob(db + '.bak_attach_*'))
    if not baks: raise SystemExit('没有 attach 备份')
    src = baks[-1]
    print('恢复自', src)
    for suffix in ['', '-wal', '-shm']:
        p = db + suffix
        if os.path.exists(p):
            try: os.remove(p)
            except: pass
    shutil.copy2(src, db)
    print('已恢复')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['list', 'attach', 'detach'])
    ap.add_argument('args', nargs='*')
    a = ap.parse_args()
    if a.cmd == 'list': list_all()
    elif a.cmd == 'attach': attach(a.args[0], a.args[1])
    elif a.cmd == 'detach': detach()
