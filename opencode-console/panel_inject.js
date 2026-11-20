(function(){
  var LOCAL='http://127.0.0.1:8891';
  window.__aaOCPanel=function(){
    var old=document.getElementById('aa-oc-panel');
    if(old){old.remove();return}
    var panel=document.createElement('div');
    panel.id='aa-oc-panel';
    panel.style.cssText='position:fixed;top:56px;right:16px;width:580px;height:74vh;z-index:100000;background:#0d0d10;border:1px solid #2a2a32;border-radius:12px;display:flex;flex-direction:column;box-shadow:0 12px 40px rgba(0,0,0,.6);font:13px/1.5 -apple-system,"Segoe UI",sans-serif;color:#e8e8ea';
    panel.innerHTML='<div style="padding:12px 14px;border-bottom:1px solid #26262b;display:flex;align-items:center;gap:8px;flex-wrap:wrap"><b style="font-size:15px">会话记录</b>'+
      '<div id="aa-oc-tabs" style="display:flex;gap:4px;margin-left:6px"><button data-src="oc" style="padding:3px 10px;border-radius:6px;border:1px solid #3a6ea5;background:#1d3a5f;color:#cfe4ff;cursor:pointer;font-size:12px">OpenCode</button><button data-src="aa" style="padding:3px 10px;border-radius:6px;border:1px solid #333;background:transparent;color:#aaa;cursor:pointer;font-size:12px">AA 会话</button></div>'+
      '<span id="aa-oc-count" style="color:#888;font-size:11px">加载中…</span><input id="aa-oc-filter" placeholder="筛选…" style="margin-left:auto;background:#16161a;color:#e8e8ea;border:1px solid #333;border-radius:6px;padding:5px 8px;width:120px;font:inherit"><button id="aa-oc-close" style="background:transparent;color:#aaa;border:0;cursor:pointer;font-size:18px">×</button></div>'+
      '<div style="display:flex;flex:1;min-height:0"><div id="aa-oc-list" style="width:240px;border-right:1px solid #26262b;overflow:auto;flex-shrink:0"></div><div style="flex:1;display:flex;flex-direction:column;min-width:0"><div id="aa-oc-msg" style="flex:1;overflow:auto;padding:12px"><div style="color:#666;text-align:center;margin-top:40%">← 选一个会话</div></div><div style="border-top:1px solid #26262b;padding:8px;display:flex;gap:6px"><textarea id="aa-oc-input" placeholder="发消息…（仅 OpenCode 支持）" style="flex:1;height:42px;resize:none;background:#16161a;color:#e8e8ea;border:1px solid #333;border-radius:8px;padding:6px;font:inherit"></textarea><button id="aa-oc-send" style="padding:0 14px;background:#2b6cb0;color:#fff;border:0;border-radius:8px;cursor:pointer">发送</button></div></div></div>';
    document.body.appendChild(panel);
    var listEl=panel.querySelector('#aa-oc-list'),msgEl=panel.querySelector('#aa-oc-msg'),filterEl=panel.querySelector('#aa-oc-filter'),inputEl=panel.querySelector('#aa-oc-input');
    var sess=[],current=null,token='',source='oc'; // 'oc' = OpenCode原生, 'aa' = AA会话
    try{token=(JSON.parse(localStorage.getItem('aa.session.v1')||'{}').accessToken)||''}catch(e){}
    function api(path){return fetch(path,{headers:{Authorization:'Bearer '+token}}).then(function(r){return r.json()})}
    function esc(s){return String(s==null?'':s).replace(/[&<>]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c]})}
    function rtName(s){return (source==='oc'?'OpenCode':(s.runtimeName||s.runtimeTypeDisplayName||s.runtime||'?'));}
    function renderList(){
      var f=(filterEl.value||'').toLowerCase();
      listEl.innerHTML='';
      var groups={};
      sess.filter(function(s){return !f||(s.title||'').toLowerCase().indexOf(f)>=0||(s.id||'').indexOf(f)>=0}).forEach(function(s){
        var g=rtName(s);(groups[g]=groups[g]||[]).push(s);
      });
      Object.keys(groups).forEach(function(g){
        var gh=document.createElement('div');gh.textContent=g+' · '+groups[g].length;
        gh.style.cssText='padding:6px 10px;color:#777;font-size:11px;position:sticky;top:0;background:#0d0d10;border-bottom:1px solid #1c1c20';listEl.appendChild(gh);
        groups[g].forEach(function(s){
          var d=document.createElement('div');
          d.textContent=s.title||(s.id||'').slice(0,24)||'(无标题)';d.title=s.id;
          d.style.cssText='padding:8px 10px;cursor:pointer;border-bottom:1px solid #1a1a1e;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'+(current&&current.id===s.id?';background:#232329;border-left:3px solid #6ea8fe;padding-left:7px':'');
          d.onclick=function(){openSession(s)};listEl.appendChild(d);
        });
      });
    }
    function openSession(s){
      current=s;renderList();
      msgEl.innerHTML='<div style="color:#666;text-align:center;margin-top:40%">加载消息…</div>';
      var p = source==='oc'
        ? fetch(LOCAL+'/api/messages/'+encodeURIComponent(s.id)).then(function(r){return r.json()}).then(function(d){return d.messages||[]})
        : api('/api/v2/sessions/'+encodeURIComponent(s.id)+'/snapshot?limit=200').then(function(d){return (d.timeline&&d.timeline.items)||[]});
      p.then(function(items){
        if(!items.length){msgEl.innerHTML='<div style="color:#666;text-align:center;margin-top:40%">(无消息)</div>';return}
        msgEl.innerHTML='';
        items.forEach(function(x){
          var role,text,isReason=false,isTool=false;
          if(source==='oc'){ role=x.role==='user'?'user':'assistant'; text=x.text||''; }
          else { var kind=x.content&&x.content.kind; role=x.role==='user'?'user':'assistant'; text=(x.content&&x.content.text)||''; isReason=(kind==='reasoning'); isTool=(x.type==='tool'); if(!text&&!isTool)return; }
          if(!String(text).trim()&&!isTool)return;
          var wrap=document.createElement('div');
          wrap.style.cssText='margin-bottom:12px;padding:9px 12px;border-radius:10px;max-width:92%;white-space:pre-wrap;word-break:break-word;'+(role==='user'?'background:#1d2a3a;margin-left:auto':(isReason?'background:#16161a;border:1px dashed #333;color:#999':'background:#1a1a1f;border:1px solid #2a2a30'));
          var lab=document.createElement('div');lab.textContent=(role==='user'?'你':(isReason?'思考':rtName(s).toUpperCase()))+(isTool?' · 工具':'');lab.style.cssText='font-size:11px;color:#888;margin-bottom:4px';
          var t=document.createElement('div');t.textContent=String(text||(isTool?'[工具调用]':''));wrap.appendChild(lab);wrap.appendChild(t);msgEl.appendChild(wrap);
        });
        msgEl.scrollTop=msgEl.scrollHeight;
      }).catch(function(e){msgEl.innerHTML='<div style="color:#c66">错误: '+esc(e.message)+'</div>'});
    }
    function load(){
      current=null;msgEl.innerHTML='<div style="color:#666;text-align:center;margin-top:40%">← 选一个会话</div>';
      var p = source==='oc'
        ? fetch(LOCAL+'/api/sessions').then(function(r){return r.json()}).then(function(d){return d.sessions||[]})
        : api('/api/v2/sessions/list').then(function(d){return d.sessions||d.data||[]});
      p.then(function(arr){
        sess=arr;panel.querySelector('#aa-oc-count').textContent=sess.length+' 个会话';renderList();
        // 自动检测当前会话
        var m=location.hash.match(/session\/([^/?]+)/);
        if(m){
          var found=sess.find(function(s){return s.id===m[1]||s.externalSessionId===m[1]});
          if(found)openSession(found);
        }
      }).catch(function(e){panel.querySelector('#aa-oc-count').textContent='加载失败: '+esc(e.message)});
    }
    function send(){
      if(!current){alert('请先选一个会话');return}
      var rt=(current.runtime||'').toLowerCase();
      if(source==='aa'&&rt!=='opencode'){alert('发消息暂只支持 OpenCode；当前是 '+(current.runtimeName||rt)+'，可只读查看');return}
      var text=inputEl.value.trim();if(!text)return;
      var btn=panel.querySelector('#aa-oc-send');btn.disabled=true;
      var sid = source==='oc' ? current.id : (current.externalSessionId||current.id);
      fetch(LOCAL+'/api/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session:sid,text:text})}).then(function(r){return r.json()}).then(function(d){
        btn.disabled=false;
        if(d.error){alert('发送失败: '+d.error);return}
        inputEl.value='';openSession(current);
      }).catch(function(e){btn.disabled=false;alert('发送失败: '+e.message)});
    }
    // tab switching
    panel.querySelectorAll('#aa-oc-tabs button').forEach(function(b){
      b.onclick=function(){
        source=b.getAttribute('data-src');
        panel.querySelectorAll('#aa-oc-tabs button').forEach(function(x){
          var on=x===b;
          x.style.background=on?(source==='oc'?'#1d3a5f':'#3a2f1f'):'transparent';
          x.style.color=on?(source==='oc'?'#cfe4ff':'#ffe0a0'):'#aaa';
        });
        load();
      };
    });
    panel.querySelector('#aa-oc-close').onclick=function(){panel.remove()};
    panel.querySelector('#aa-oc-filter').oninput=renderList;
    panel.querySelector('#aa-oc-send').onclick=send;
    inputEl.onkeydown=function(e){if(e.ctrlKey&&e.key==='Enter'){e.preventDefault();send()}};
    load();
  };
})();
