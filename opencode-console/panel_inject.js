(function(){
  var BASE='http://127.0.0.1:8891';
  window.__aaOCPanel=function(){
    var old=document.getElementById('aa-oc-panel');
    if(old){old.remove();return}
    var panel=document.createElement('div');
    panel.id='aa-oc-panel';
    panel.style.cssText='position:fixed;top:56px;right:16px;width:560px;height:72vh;z-index:100000;background:#0d0d10;border:1px solid #2a2a32;border-radius:12px;display:flex;flex-direction:column;box-shadow:0 12px 40px rgba(0,0,0,.6);font:13px/1.5 -apple-system,"Segoe UI",sans-serif;color:#e8e8ea';
    panel.innerHTML='<div style="padding:12px 14px;border-bottom:1px solid #26262b;display:flex;align-items:center;gap:8px"><b style="font-size:15px">会话记录</b><span id="aa-oc-count" style="color:#888;font-size:11px">加载中…</span><input id="aa-oc-filter" placeholder="筛选…" style="margin-left:auto;background:#16161a;color:#e8e8ea;border:1px solid #333;border-radius:6px;padding:5px 8px;width:130px;font:inherit"><button id="aa-oc-close" style="background:transparent;color:#aaa;border:0;cursor:pointer;font-size:18px">×</button></div>'+
      '<div style="display:flex;flex:1;min-height:0"><div id="aa-oc-list" style="width:220px;border-right:1px solid #26262b;overflow:auto;flex-shrink:0"></div><div style="flex:1;display:flex;flex-direction:column;min-width:0"><div id="aa-oc-msg" style="flex:1;overflow:auto;padding:12px"><div style="color:#666;text-align:center;margin-top:40%">← 选一个会话</div></div><div style="border-top:1px solid #26262b;padding:8px;display:flex;gap:6px"><textarea id="aa-oc-input" placeholder="发消息到该会话…（仅 OpenCode 会话支持）" style="flex:1;height:42px;resize:none;background:#16161a;color:#e8e8ea;border:1px solid #333;border-radius:8px;padding:6px;font:inherit"></textarea><button id="aa-oc-send" style="padding:0 14px;background:#2b6cb0;color:#fff;border:0;border-radius:8px;cursor:pointer">发送</button></div></div></div>';
    document.body.appendChild(panel);
    var listEl=panel.querySelector('#aa-oc-list');
    var msgEl=panel.querySelector('#aa-oc-msg');
    var filterEl=panel.querySelector('#aa-oc-filter');
    var inputEl=panel.querySelector('#aa-oc-input');
    var sess=[],current=null;
    function esc(s){return String(s==null?'':s).replace(/[&<>]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c]})}
    function profile(s){return s.profile||'?'}
    function renderList(){
      var f=(filterEl.value||'').toLowerCase();
      listEl.innerHTML='';
      var groups={};
      sess.filter(function(s){return !f||(s.agent_session_id||'').toLowerCase().indexOf(f)>=0||profile(s).toLowerCase().indexOf(f)>=0||s.id.indexOf(f)>=0}).forEach(function(s){
        var g=profile(s);(groups[g]=groups[g]||[]).push(s);
      });
      Object.keys(groups).forEach(function(g){
        var gh=document.createElement('div');gh.textContent=g+' · '+groups[g].length;
        gh.style.cssText='padding:6px 10px;color:#777;font-size:11px;position:sticky;top:0;background:#0d0d10;border-bottom:1px solid #1c1c20';listEl.appendChild(gh);
        groups[g].forEach(function(s){
          var d=document.createElement('div');
          d.textContent=(s.agent_session_id||s.id).slice(0,24)+(s.cwd?'  · '+s.cwd:'');
          d.title=s.id;
          d.style.cssText='padding:8px 10px;cursor:pointer;border-bottom:1px solid #1a1a1e;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'+(current&&current.id===s.id?';background:#232329;border-left:3px solid #6ea8fe;padding-left:7px':'');
          d.onclick=function(){openSession(s)};
          listEl.appendChild(d);
        });
      });
    }
    function openSession(s){
      current=s;renderList();
      msgEl.innerHTML='<div style="color:#666;text-align:center;margin-top:40%">加载消息…</div>';
      var isOC=(profile(s)==='opencode');
      var url=isOC?('/api/aa/messages?aa='+encodeURIComponent(s.id)):('/api/aa/messages?aa='+encodeURIComponent(s.id));
      // 统一读 AA 自己的 projection（适用所有 runtime）
      fetch(BASE+url).then(function(r){return r.json()}).then(function(d){
        if(!d.messages||!d.messages.length){msgEl.innerHTML='<div style="color:#666;text-align:center;margin-top:40%">(无消息)</div>';return}
        msgEl.innerHTML='';
        d.messages.forEach(function(m){
          var wrap=document.createElement('div');
          wrap.style.cssText='margin-bottom:14px;padding:10px 12px;border-radius:10px;max-width:90%;white-space:pre-wrap;word-break:break-word;'+(m.role==='user'?'background:#1d2a3a;margin-left:auto':'background:#1a1a1f;border:1px solid #2a2a30');
          var lab=document.createElement('div');lab.textContent=m.role==='user'?'你':profile(s).toUpperCase();lab.style.cssText='font-size:11px;color:#888;margin-bottom:4px';
          var t=document.createElement('div');t.textContent=m.text;
          wrap.appendChild(lab);wrap.appendChild(t);msgEl.appendChild(wrap);
        });
        msgEl.scrollTop=msgEl.scrollHeight;
      }).catch(function(e){msgEl.innerHTML='<div style="color:#c66">错误: '+esc(e.message)+'</div>'});
    }
    function load(){
      fetch(BASE+'/api/aa/sessions').then(function(r){return r.json()}).then(function(d){
        sess=d.sessions||[];panel.querySelector('#aa-oc-count').textContent=sess.length+' 个会话';renderList();
        // 自动检测当前 AA 会话 → 直接打开对应会话消息（适配 OpenCode/DSH/Claude 等）
        var m=location.hash.match(/session\/([^/?]+)/);
        if(m){
          var aa=m[1];var found=sess.find(function(s){return s.id===aa});
          if(found){openSession(found);return}
          // 兜底：用 binding 找
          fetch(BASE+'/api/binding?aa='+encodeURIComponent(aa)).then(function(r){return r.json()}).then(function(b){
            if(b.opencode_session){
              var f2=sess.find(function(s){return s.agent_session_id===b.opencode_session});
              if(f2)openSession(f2);
            }
          }).catch(function(){});
        }
      }).catch(function(e){panel.querySelector('#aa-oc-count').textContent='服务未启动: '+e.message});
    }
    function send(){
      if(!current){alert('请先选一个会话');return}
      if(profile(current)!=='opencode'){alert('发送仅支持 OpenCode 会话；其它 runtime 的会话为只读查看');return}
      var text=inputEl.value.trim();if(!text)return;
      var btn=panel.querySelector('#aa-oc-send');btn.disabled=true;
      fetch(BASE+'/api/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session:current.agent_session_id,text:text})}).then(function(r){return r.json()}).then(function(d){
        btn.disabled=false;
        if(d.error){alert('发送失败: '+d.error);return}
        inputEl.value='';openSession(current);
      }).catch(function(e){btn.disabled=false;alert('发送失败: '+e.message)});
    }
    panel.querySelector('#aa-oc-close').onclick=function(){panel.remove()};
    panel.querySelector('#aa-oc-filter').oninput=renderList;
    panel.querySelector('#aa-oc-send').onclick=send;
    inputEl.onkeydown=function(e){if(e.ctrlKey&&e.key==='Enter'){e.preventDefault();send()}};
    load();
  };
})();
