# -*- coding: utf-8 -*-
"""OpenCode 会话控制台 —— 本地 Web App，供 AA 浏览器 tab 打开。

功能：
  - 列出 OpenCode 所有会话（按项目/目录分组）
  - 查看任意会话的历史消息
  - 在任意会话里发消息（调 opencode api POST /api/session/{id}/prompt）

启动：python server.py [--port 8891]
然后到 AA 浏览器 tab 打开 http://127.0.0.1:8891
"""
import os, sys, json, glob, subprocess, argparse, urllib.request, urllib.parse, sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AA_DB_GLOB = r'C:\Users\sun67\.agents-anywhere\conn_CBGhjuuMLb6KGg\**\coordination.sqlite'

def aa_db():
    dbs = glob.glob(AA_DB_GLOB, recursive=True)
    return dbs[0] if dbs else None

def find_aa_binding(aa_session_id):
    """读取 AA coordination.sqlite，返回该 AA 会话绑定的底层 session id。"""
    db=aa_db()
    if not db: return None
    c = sqlite3.connect('file:' + db + '?mode=ro', uri=True)
    row = c.execute("SELECT body FROM records WHERE kind='binding' AND id=?", (aa_session_id,)).fetchone()
    c.close()
    if not row: return None
    d = json.loads(row[0])
    return d.get('agent_session_id')

def aa_sessions():
    """列出 AA 自己的所有会话（含 runtime 类型/标题），来自 AA 的云端同步数据不可用时用本地。"""
    db=aa_db()
    if not db: return []
    c = sqlite3.connect('file:' + db + '?mode=ro', uri=True)
    out=[]
    for k,b in c.execute("SELECT id,body FROM records WHERE kind='binding'").fetchall():
        try:
            d=json.loads(b)
            out.append({'id':k,'agent_session_id':d.get('agent_session_id'),'profile':d.get('profile_id'),
                        'release':d.get('release_id'),'cwd':(d.get('workspace') or {}).get('canonical_path','')})
        except: pass
    c.close()
    return out

def aa_messages(aa_session_id):
    """从 AA projection 表读任意会话的消息（适用所有 runtime：opencode/dsh/claude...）。"""
    db=aa_db()
    if not db: return []
    c = sqlite3.connect('file:' + db + '?mode=ro', uri=True)
    rows=c.execute("SELECT body FROM records WHERE kind='projection' AND json_extract(body,'$.sessionId')=? ORDER BY CAST(json_extract(body,'$.orderSeq') AS INTEGER)",(aa_session_id,)).fetchall()
    c.close()
    out=[]
    for (b,) in rows:
        try:
            d=json.loads(b)
            role=d.get('role','')
            if role not in ('user','assistant'): continue
            content=d.get('content') or {}
            text=content.get('text','') if isinstance(content,dict) else str(content)
            if text and str(text).strip(): out.append({'role':role,'text':text})
        except: pass
    return out

CLI_CANDIDATES = [
    r'C:\Users\sun67\AppData\Roaming\ai.opencode.desktop\cli\2.3.2-x64\opencode-cli.exe',
]
for base in (
    os.path.join(os.environ.get('APPDATA', ''), 'ai.opencode.desktop', 'cli'),
    os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'ai.opencode.desktop', 'resources'),
):
    CLI_CANDIDATES += sorted(glob.glob(os.path.join(base, '*', 'opencode-cli.exe')), reverse=True)
    direct = os.path.join(base, 'opencode-cli.exe')
    if os.path.isfile(direct): CLI_CANDIDATES.append(direct)

def cli():
    for p in CLI_CANDIDATES:
        if os.path.isfile(p): return p
    raise RuntimeError('opencode-cli.exe not found')

def oc_api(method, path, body=None):
    cmd = [cli(), 'api', method, path]
    if body is not None:
        cmd += ['-d', json.dumps(body, ensure_ascii=False)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, encoding='utf-8', errors='replace')
    out = (r.stdout or '').strip()
    # strip non-JSON log lines
    i = out.find('{')
    if i < 0: i = out.find('[')
    if i >= 0: out = out[i:]
    return out

HTML = r'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OpenCode 会话控制台</title>
<style>
:root{color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;font:14px/1.5 -apple-system,"Segoe UI",sans-serif;background:#0d0d0f;color:#e8e8ea;height:100vh;display:flex;flex-direction:column}
header{padding:10px 16px;border-bottom:1px solid #26262b;display:flex;align-items:center;gap:12px;flex-shrink:0}
header b{font-size:16px}
header .hint{color:#888;font-size:12px}
#main{display:flex;flex:1;min-height:0}
#list{width:320px;border-right:1px solid #26262b;overflow:auto;flex-shrink:0}
#list .grp{padding:8px 12px;color:#777;font-size:11px;text-transform:uppercase;letter-spacing:.5px;position:sticky;top:0;background:#0d0d0f}
#list .item{padding:9px 12px;cursor:pointer;border-bottom:1px solid #1c1c20;display:flex;flex-direction:column;gap:2px}
#list .item:hover{background:#1a1a1f}
#list .item.active{background:#232329;border-left:3px solid #6ea8fe;padding-left:9px}
#list .item .t{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#list .item .m{color:#777;font-size:11px}
#view{flex:1;display:flex;flex-direction:column;min-width:0}
#msgs{flex:1;overflow:auto;padding:16px}
#msgs .msg{margin-bottom:18px;padding:12px 14px;border-radius:10px;max-width:85%;white-space:pre-wrap;word-break:break-word}
#msgs .user{background:#1d2a3a;margin-left:auto}
#msgs .assistant{background:#1a1a1f;border:1px solid #2a2a30}
#msgs .meta{font-size:11px;color:#777;margin-bottom:4px}
#empty{color:#666;text-align:center;margin-top:40%}
#composer{border-top:1px solid #26262b;padding:12px;display:flex;gap:8px;flex-shrink:0}
#composer textarea{flex:1;resize:none;height:48px;background:#16161a;color:#e8e8ea;border:1px solid #333;border-radius:8px;padding:8px;font:inherit}
#composer button{padding:0 18px;background:#2b6cb0;color:#fff;border:0;border-radius:8px;cursor:pointer}
#composer button:disabled{opacity:.5;cursor:not-allowed}
#bar{display:flex;gap:8px;align-items:center}
#bar input{flex:1;background:#16161a;color:#e8e8ea;border:1px solid #333;border-radius:6px;padding:6px 10px;font:inherit}
</style></head>
<body>
<header><b>OpenCode 会话控制台</b><span class="hint" id="status">加载中…</span>
<div id="bar" style="margin-left:auto"><input id="filter" placeholder="筛选会话标题…"><button id="refresh">刷新列表</button></div></header>
<div id="main">
  <div id="list"></div>
  <div id="view">
    <div id="msgs"><div id="empty">← 从左侧选择一个会话</div></div>
    <div id="composer">
      <textarea id="input" placeholder="输入消息，Ctrl+Enter 发送…（在任意会话里继续对话）"></textarea>
      <button id="send">发送</button>
    </div>
  </div>
</div>
<script>
let sessions=[], current=null;
function esc(s){return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
async function load(){
  document.getElementById('status').textContent='加载中…';
  let r=await fetch('/api/sessions').then(r=>r.json()).catch(e=>({error:String(e)}));
  if(r.error){document.getElementById('status').textContent='错误: '+r.error;return}
  sessions=r.sessions||[];
  document.getElementById('status').textContent=sessions.length+' 个会话';
  renderList();
}
function renderList(){
  const f=document.getElementById('filter').value.toLowerCase();
  const groups={};
  sessions.filter(s=>!f||(s.title||'').toLowerCase().includes(f)||s.id.includes(f)).forEach(s=>{
    const g=s.location?.directory||'?'; (groups[g]=groups[g]||[]).push(s);
  });
  const el=document.getElementById('list'); el.innerHTML='';
  for(const g in groups){
    const gh=document.createElement('div');gh.className='grp';gh.textContent=g;el.appendChild(gh);
    groups[g].forEach(s=>{
      const d=document.createElement('div');d.className='item'+(current===s.id?' active':'');
      d.innerHTML='<div class="t">'+esc(s.title||'(无标题)')+'</div><div class="m">'+esc(s.id.slice(0,20))+' · '+(s.model?.id||'')+'</div>';
      d.onclick=()=>openSession(s);el.appendChild(d);
    });
  }
}
async function openSession(s){
  current=s.id;renderList();
  const msgs=document.getElementById('msgs');msgs.innerHTML='<div id="empty">加载消息…</div>';
  let r=await fetch('/api/messages/'+encodeURIComponent(s.id)).then(r=>r.json()).catch(e=>({error:String(e)}));
  if(r.error||r.messages===undefined){msgs.innerHTML='<div id="empty">错误: '+esc(r.error||'unknown')+'</div>';return}
  msgs.innerHTML='';
  if(!r.messages.length){msgs.innerHTML='<div id="empty">(无消息)</div>';return}
  r.messages.forEach(m=>{
    const d=document.createElement('div');d.className='msg '+(m.role==='user'?'user':'assistant');
    d.innerHTML='<div class="meta">'+(m.role==='user'?'你':'OpenCode')+'</div>'+esc(m.text);
    msgs.appendChild(d);
  });
  msgs.scrollTop=msgs.scrollHeight;
}
async function send(){
  if(!current)return;
  const inp=document.getElementById('input');const text=inp.value.trim();if(!text)return;
  const btn=document.getElementById('send');btn.disabled=true;
  let r=await fetch('/api/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session:current,text})}).then(r=>r.json()).catch(e=>({error:String(e)}));
  btn.disabled=false;
  if(r.error){alert('发送失败: '+r.error);return}
  inp.value='';await openSession(sessions.find(s=>s.id===current));
}
document.getElementById('send').onclick=send;
document.getElementById('input').onkeydown=e=>{if(e.ctrlKey&&e.key==='Enter'){e.preventDefault();send()}};
document.getElementById('refresh').onclick=load;
document.getElementById('filter').oninput=renderList;
load();
</script>
</body></html>'''

class H(BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin','*')
        self.send_header('Access-Control-Allow-Methods','GET,POST,OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Content-Type')
    def do_OPTIONS(self):
        self.send_response(204);self._cors();self.end_headers()
    def send_json(self,obj,code=200):
        b=json.dumps(obj,ensure_ascii=False).encode('utf-8')
        self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8')
        self._cors()
        self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
    def do_GET(self):
        path=urllib.parse.urlparse(self.path).path
        if path=='/' or path=='/index.html':
            b=HTML.encode('utf-8');self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
        if path=='/api/sessions':
            try:
                raw=oc_api('GET','/api/session')
                d=json.loads(raw)
                arr=d.get('data',d) if isinstance(d,dict) else d
                self.send_json({'sessions':arr});return
            except Exception as e:
                self.send_json({'error':str(e),'raw':raw[:200] if 'raw' in dir() else ''});return
        if path.startswith('/api/messages/'):
            sid=urllib.parse.unquote(path.split('/api/messages/')[1])
            try:
                raw=oc_api('GET',f'/api/session/{sid}/message')
                d=json.loads(raw)
                arr=d.get('data',[]) if isinstance(d,dict) else d
                out=[]
                for m in arr:
                    role=m.get('type','')  # 'user' / 'assistant' / 'idle' ...
                    if role not in ('user','assistant'): continue
                    content=m.get('content',[])
                    if isinstance(content,list):
                        text='\n'.join(c.get('text','') for c in content if isinstance(c,dict) and c.get('type')=='text' and c.get('text'))
                    else:
                        text=str(content)
                    if text.strip(): out.append({'role':role,'text':text})
                self.send_json({'messages':out});return
            except Exception as e:
                self.send_json({'error':str(e)});return
        if path=='/api/binding':
            aa=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('aa',[''])[0]
            try:
                ocid=find_aa_binding(aa)
                self.send_json({'aa':aa,'opencode_session':ocid});return
            except Exception as e:
                self.send_json({'error':str(e)});return
        if path=='/api/aa/sessions':
            try:
                self.send_json({'sessions':aa_sessions()});return
            except Exception as e:
                self.send_json({'error':str(e)});return
        if path=='/api/aa/messages':
            aa=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('aa',[''])[0]
            try:
                self.send_json({'messages':aa_messages(aa)});return
            except Exception as e:
                self.send_json({'error':str(e)});return
        self.send_json({'error':'not found'},404)
    def do_POST(self):
        path=urllib.parse.urlparse(self.path).path
        if path=='/api/send':
            try:
                n=int(self.headers.get('Content-Length',0));body=json.loads(self.rfile.read(n))
                sid=body['session'];text=body['text']
                raw=oc_api('POST',f'/api/session/{sid}/prompt',{'parts':[{'type':'text','text':text}]})
                self.send_json({'ok':True,'result':raw[:300]});return
            except Exception as e:
                self.send_json({'error':str(e)});return
        self.send_json({'error':'not found'},404)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=8891);a=ap.parse_args()
    print(f'OpenCode Console: http://127.0.0.1:{a.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',a.port),H).serve_forever()
