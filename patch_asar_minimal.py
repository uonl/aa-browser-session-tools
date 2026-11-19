# -*- coding: utf-8 -*-
"""在原版 asar 的编译 chunk 上做最小手术，加入原生「浏览器」工具 tab。

不改任何其它前端代码 —— WebSocket / 登录 / API 全部保持原版行为。

用法：
  python patch_asar_minimal.py [--asar 路径]
"""
import sys, os, io, shutil, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from asar_packer import Asar

DEFAULT_ASAR = r"G:\anywhere\Agents Anywhere\resources\app.asar"
CHUNK = "renderer/out/_next/static/chunks/0axsoae8j5mxk.js"
I18N  = "renderer/out/_next/static/chunks/233tc332t4hy3.js"
MD    = "renderer/out/_next/static/chunks/31airuwdveg0l.js"
MAIN  = "dist/electron/main.js"
PRELOAD = "dist/electron/preload.js"
BAK_SUFFIX = ".bak_before_minimal_browser"

# 浏览器面板组件（插入到模块作用域内，复用 bundle 里的 T=React / A=jsx-runtime / VR=Globe）
BROWSER_PANEL = r'''function wBrowserPanel(W){var H=T.createElement,V=T.useState("about:blank"),Q=V[0],Y=V[1],K=T.useState(function(){try{return JSON.parse(localStorage.getItem("aa-browser-recent")||"[]")}catch(e){return[]}}),R=K[0],G=K[1],SS=T.useState(""),SV=SS[0],SY=SS[1];function nav(u){if(!u)return;var v=String(u).trim();if(/^[a-z][a-z0-9+.-]*:\/\//i.test(v)||/^file:/i.test(v)){}else if(v.indexOf(".")>0){v="https://"+v}else{v="https://www.bing.com/search?q="+encodeURIComponent(v)};Y(v);G(function(x){var y=[v].concat(x.filter(function(s){return s!==v})).slice(0,8);try{localStorage.setItem("aa-browser-recent",JSON.stringify(y))}catch(e){}return y})}T.useEffect(function(){function h(e){if(e.key==="aa-browser-goto"&&e.newValue){nav(e.newValue);try{localStorage.removeItem("aa-browser-goto")}catch(a){}}}window.addEventListener("storage",h);try{var g=localStorage.getItem("aa-browser-goto");if(g){nav(g);localStorage.removeItem("aa-browser-goto")}}catch(a){}return function(){window.removeEventListener("storage",h)}},[]);if(!W)return null;var L=(function(){try{return /[\u4e00-\u9fff]/.test((document.body&&document.body.innerText||"").slice(0,6000))}catch(e){return true}})();function X(){var p=document.querySelector('[role=tabpanel]:not([aria-hidden="true"])');if(p){var lab=p.getAttribute('aria-labelledby');var tab=lab?document.getElementById(lab):null;if(tab){var bs=tab.parentElement.querySelectorAll('button');if(bs.length>1)bs[bs.length-1].click()}}}return H("div",{className:"flex h-full min-h-0 flex-col bg-background text-foreground"},H("div",{className:"flex h-11 shrink-0 items-center gap-1 border-b border-border px-2"},H("button",{className:"rounded px-2 py-1 text-xs text-muted-foreground hover:bg-secondary",onClick:function(){var f=document.getElementById("aa-browser-frame");if(f)f.contentWindow.history.back()}},L?"\u540e\u9000":"Back"),H("button",{className:"rounded px-2 py-1 text-xs text-muted-foreground hover:bg-secondary",onClick:function(){var f=document.getElementById("aa-browser-frame");if(f)f.contentWindow.history.forward()}},L?"\u524d\u8fdb":"Forward"),H("button",{className:"rounded px-2 py-1 text-xs text-muted-foreground hover:bg-secondary",onClick:function(){var f=document.getElementById("aa-browser-frame");if(f)f.src=f.src}},L?"\u5237\u65b0":"Reload"),H("input",{value:!Q||Q==="about:blank"?"":Q,onChange:function(e){var v=e.target.value;Y(v);clearTimeout(window.__aaSearchTimer);window.__aaSearchTimer=setTimeout(function(){nav(v)},800)},onKeyDown:function(e){if(e.key==="Enter"){clearTimeout(window.__aaSearchTimer);nav(e.target.value)}},placeholder:"Search or enter a URL",className:"h-8 min-w-0 flex-1 rounded-full border border-border bg-secondary/40 px-3 text-xs outline-none"}),H("button",{className:"rounded px-2 py-1 text-xs text-muted-foreground hover:bg-secondary",onClick:X},L?"\u5173\u95ed":"Close")),!Q||Q==="about:blank"?H("div",{className:"flex-1 overflow-auto"},H("div",{className:"flex flex-col items-center px-6 pt-14 pb-8"},H("div",{className:"mb-5 text-xl font-semibold text-foreground"},L?"\u641c\u7d22":"Search"),H("div",{className:"flex w-full max-w-xl items-center gap-2"},H("input",{value:SV,onChange:function(e){SY(e.target.value)},onKeyDown:function(e){if(e.key==="Enter"&&SV.trim())nav(SV)},placeholder:"Search or enter a URL",className:"h-11 flex-1 rounded-full border border-border bg-secondary/40 px-5 text-sm outline-none placeholder:text-muted-foreground focus:border-ring"}),H("button",{onClick:function(){if(SV.trim())nav(SV)},className:"h-11 rounded-full bg-primary px-6 text-sm font-medium text-primary-foreground hover:opacity-90"},L?"\u641c\u7d22":"Search"))),H("div",{className:"px-6 pb-6"},H("h3",{className:"mb-4 text-sm font-semibold text-muted-foreground"},"Recent"),R.length===0?H("p",{className:"text-xs text-muted-foreground"},L?"\u6682\u65e0\u8bb0\u5f55":"No recent history"):H("div",{className:"flex flex-col gap-1"},R.map(function(u,i){return H("button",{key:i,onClick:function(){nav(u)},className:"rounded-lg px-3 py-2 text-left text-sm hover:bg-secondary"},u)})))):H("iframe",{id:"aa-browser-frame",src:Q,title:"browser",className:"h-full w-full border-0 bg-white",sandbox:"allow-same-origin allow-scripts allow-forms allow-modals allow-popups",onLoad:function(){var f=document.getElementById("aa-browser-frame");try{var d=f&&f.contentDocument;if(d&&d.location&&d.location.protocol!=="about:"){d.addEventListener("click",function(ev){var a=ev.target&&ev.target.closest&&ev.target.closest("a");if(a&&a.href&&/^https?:/i.test(a.href)){ev.preventDefault();ev.stopPropagation();window.__aaOpenInBrowser(a.href)}},true)}}catch(e){}}}))}'''

def patch(asar_path, build=False):
    a = Asar(asar_path)
    ui = a.read(CHUNK).decode('utf-8', 'replace')
    i18n = a.read(I18N).decode('utf-8', 'replace')

    # --- 1. TOOL_META: add browser (Globe icon = VR) ---
    old = 'files:{icon:xC.File,labelKey:"files",descriptionKey:"filesDescription"}}'
    assert old in ui, 'TOOL_META tail not found'
    # w$ 与 w_ 处于同一条 let 声明链，wGlobe 也用逗号并入，不能用 var/分号
    globe_def = 'wGlobe=(0,ae.default)("globe",[["circle",{cx:"12",cy:"12",r:"10",key:"1mglay"}],["path",{d:"M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20",key:"13o1zl"}],["path",{d:"M2 12h20",key:"9i4pu4"}]]),'
    assert 'w_={review:' in ui, 'TOOL_META head not found'
    ui = ui.replace('w_={review:', globe_def + 'w_={review:', 1)
    ui = ui.replace(old,
        'files:{icon:xC.File,labelKey:"files",descriptionKey:"filesDescription"},browser:{icon:wGlobe,labelKey:"browser",descriptionKey:"browserDescription"}}', 1)

    # --- 2. TOOL_KINDS ---
    old = 'wL=["review","terminal","files"]'
    assert old in ui, 'TOOL_KINDS not found'
    ui = ui.replace(old, 'wL=["review","terminal","files","browser"]', 1)

    # --- 3. content-area render branch (insert browser before the final :null) ---
    # 原版片段: ...onPinTab:t.pinTab}):null]})})]}
    old = 'onPinTab:t.pinTab}):null]},null===i?u.id:`files-workspace:${i}`)})})]}),document.body)}'
    assert old in ui, 'render tail not found'
    new = 'onPinTab:t.pinTab}):null,"browser"===u.kind?(0,A.jsx)(wBrowserPanel,{active:p}):null]},null===i?u.id:`files-workspace:${i}`)})})]}),document.body)}'
    ui = ui.replace(old, new, 1)

    # --- 4. insert BrowserPanel component before function wG( ---
    old = 'function wG({triggerRef:e,onOpenTool:t})'
    assert old in ui, 'wG anchor not found'
    ui = ui.replace(old, BROWSER_PANEL + '\n' + old, 1)

    # --- 4b. 在 wF hook 里注册全局函数，直接调用 openTool("browser") ---
    anchor_wf = ';return T.useMemo(()=>({...p,toggleSidebar:g'
    assert anchor_wf in ui, 'wF return anchor not found'
    ui = ui.replace(anchor_wf,
        ';window.__aaOpenBrowserTab=function(){m({type:"open-tool",tab:pI(hV("browser"),"browser")})};return T.useMemo(()=>({...p,toggleSidebar:g', 1)
    print('global __aaOpenBrowserTab registered')

    # --- 4c. 让原生 openTool("browser")(+ 菜单/卡片点击)也用唯一 id，避免多个浏览器标签页同 id 一起被关 ---
    old_w = 'if("terminal"!==t)return void m({type:"open-tool",tab:pI(t,t)})'
    assert old_w in ui, 'openTool pI(t,t) anchor not found'
    new_w = 'if("terminal"!==t)return void m({type:"open-tool",tab:pI("browser"===t?hV("browser"):t,t)})'
    ui = ui.replace(old_w, new_w, 1)
    print('openTool uses unique id for browser')


    # --- 5. i18n: add browser labels to BOTH zh-CN and en translation objects ---
    import re
    pat = re.compile(r'("filesDescription"\s*:\s*"((?:[^"\\]|\\.)*)")')
    def repl(m):
        # 中文区的值是 UTF-8 中文（含非 ASCII），英文区是纯 ASCII
        val = m.group(2)
        is_zh = any(ord(c) > 127 for c in val) or '\\u' in val
        if is_zh:
            add = ',"browser":"\\u6d4f\\u89c8\\u5668","browserDescription":"\\u5728\\u4fa7\\u680f\\u6d4f\\u89c8\\u7f51\\u9875 / \\u672c\\u5730 HTML"'
        else:
            add = ',"browser":"Browser","browserDescription":"Browse web pages / local HTML in the sidebar"'
        return m.group(1) + add
    i18n, n = pat.subn(repl, i18n)
    print('i18n patched', n, 'filesDescription entries')

    # --- 6. markdown 链接拦截：对话里的 http(s) 链接在浏览器 tab 打开 ---
    md = a.read(MD).decode('utf-8', 'replace')
    old_a = 'return(0,t.jsx)("a",{href:e,target:"_blank",rel:"noreferrer",...a,children:r})'
    if old_a in md:
        new_a = 'return(0,t.jsx)("a",{href:e,target:"_blank",rel:"noreferrer",...a,onClick:function(ev){if(/^https?:\\/\\//i.test(e)&&window.__aaOpenInBrowser){ev.preventDefault();window.__aaOpenInBrowser(e)}else if(a.onClick)a.onClick(ev)},children:r})'
        md = md.replace(old_a, new_a, 1)
        print('markdown link interceptor added')
    else:
        print('WARN: markdown link anchor not found')

    # --- 6b. <code> 里的 URL 也能点击（如 http://127.0.0.1:8779/） ---
    old_code = 'className:(0,m.cn)(e,"rounded-md bg-secondary px-1.5 py-0.5 text-secondary-foreground"),...a,children:r'
    if old_code in md:
        new_code = 'className:(0,m.cn)(e,"rounded-md bg-secondary px-1.5 py-0.5 text-secondary-foreground cursor-pointer"),...a,onClick:function(ev){var s=typeof r==="string"?r:"";if(/^https?:\\/\\//i.test(s)&&window.__aaOpenInBrowser){ev.preventDefault();ev.stopPropagation();window.__aaOpenInBrowser(s)}else if(a.onClick)a.onClick(ev)},children:r'
        md = md.replace(old_code, new_code, 1)
        print('code URL interceptor added')
    else:
        print('WARN: code anchor not found')

    # --- 6c. 文件路径 span role=button 加 cursor-pointer ---
    old_span = 'className:"inline-flex max-w-full items-baseline gap-0.5 rounded-none bg-transparent p-0 align-baseline text-[1em] text-inherit underline underline-offset-2 hover:text-foreground"'
    if old_span in md:
        new_span = 'className:"inline-flex max-w-full cursor-pointer items-baseline gap-0.5 rounded-none bg-transparent p-0 align-baseline text-[1em] text-inherit underline underline-offset-2 hover:text-foreground"'
        md = md.replace(old_span, new_span, 1)
        print('file-path cursor-pointer added')
    else:
        print('WARN: file-path span anchor not found')

    old_span2 = 'className:"inline-flex max-w-full items-baseline gap-0.5 align-baseline text-left underline underline-offset-2 hover:text-foreground"'
    if old_span2 in md:
        new_span2 = 'className:"inline-flex max-w-full cursor-pointer items-baseline gap-0.5 align-baseline text-left underline underline-offset-2 hover:text-foreground"'
        md = md.replace(old_span2, new_span2, 1)
        print('file-path span2 cursor-pointer added')


    # --- 7. 注册 __aaOpenInBrowser 全局函数 ---
    open_fn = 'window.__aaOpenInBrowser=function(u){try{localStorage.setItem("aa-browser-goto",u)}catch(e){}if(typeof window.__aaOpenBrowserTab==="function"){window.__aaOpenBrowserTab();return}var bs=document.querySelectorAll(\'button\');for(var i=0;i<bs.length;i++){var al=bs[i].getAttribute(\'aria-label\')||\'\';if(al.indexOf(\'\u6253\u5f00\u5de5\u5177\u4fa7\u680f\')>=0){bs[i].click();setTimeout(function(){if(window.__aaOpenBrowserTab)window.__aaOpenBrowserTab()},500);return}}};'
    capture_js = 'document.addEventListener("click",function(ev){var a=ev.target&&ev.target.closest&&ev.target.closest("a");if(a&&a.href&&/^https?:/i.test(a.href)&&window.__aaOpenInBrowser){ev.preventDefault();ev.stopPropagation();window.__aaOpenInBrowser(a.href)}},true);'
    # 主进程把 iframe 里的 target=_blank / window.open 重定向到这里，转进内置浏览器 tab
    ipc_listen = 'if(window.desktopWorkbench&&window.desktopWorkbench.browser&&window.desktopWorkbench.browser.onOpen){try{window.desktopWorkbench.browser.onOpen(function(u){window.__aaOpenInBrowser&&window.__aaOpenInBrowser(u)})}catch(e){}}'
    oc_panel_js = '(function(){\n  var BASE=\'http://127.0.0.1:8891\';\n  window.__aaOCPanel=function(){\n    var old=document.getElementById(\'aa-oc-panel\');\n    if(old){old.remove();return}\n    var panel=document.createElement(\'div\');\n    panel.id=\'aa-oc-panel\';\n    panel.style.cssText=\'position:fixed;top:56px;right:16px;width:560px;height:72vh;z-index:100000;background:#0d0d10;border:1px solid #2a2a32;border-radius:12px;display:flex;flex-direction:column;box-shadow:0 12px 40px rgba(0,0,0,.6);font:13px/1.5 -apple-system,"Segoe UI",sans-serif;color:#e8e8ea\';\n    panel.innerHTML=\'<div style="padding:12px 14px;border-bottom:1px solid #26262b;display:flex;align-items:center;gap:8px"><b style="font-size:15px">会话记录</b><span id="aa-oc-count" style="color:#888;font-size:11px">加载中…</span><input id="aa-oc-filter" placeholder="筛选…" style="margin-left:auto;background:#16161a;color:#e8e8ea;border:1px solid #333;border-radius:6px;padding:5px 8px;width:130px;font:inherit"><button id="aa-oc-close" style="background:transparent;color:#aaa;border:0;cursor:pointer;font-size:18px">×</button></div>\'+\n      \'<div style="display:flex;flex:1;min-height:0"><div id="aa-oc-list" style="width:220px;border-right:1px solid #26262b;overflow:auto;flex-shrink:0"></div><div style="flex:1;display:flex;flex-direction:column;min-width:0"><div id="aa-oc-msg" style="flex:1;overflow:auto;padding:12px"><div style="color:#666;text-align:center;margin-top:40%">← 选一个会话</div></div><div style="border-top:1px solid #26262b;padding:8px;display:flex;gap:6px"><textarea id="aa-oc-input" placeholder="发消息到该会话…（仅 OpenCode 会话支持）" style="flex:1;height:42px;resize:none;background:#16161a;color:#e8e8ea;border:1px solid #333;border-radius:8px;padding:6px;font:inherit"></textarea><button id="aa-oc-send" style="padding:0 14px;background:#2b6cb0;color:#fff;border:0;border-radius:8px;cursor:pointer">发送</button></div></div></div>\';\n    document.body.appendChild(panel);\n    var listEl=panel.querySelector(\'#aa-oc-list\');\n    var msgEl=panel.querySelector(\'#aa-oc-msg\');\n    var filterEl=panel.querySelector(\'#aa-oc-filter\');\n    var inputEl=panel.querySelector(\'#aa-oc-input\');\n    var sess=[],current=null;\n    function esc(s){return String(s==null?\'\':s).replace(/[&<>]/g,function(c){return {\'&\':\'&amp;\',\'<\':\'&lt;\',\'>\':\'&gt;\'}[c]})}\n    function profile(s){return s.profile||\'?\'}\n    function renderList(){\n      var f=(filterEl.value||\'\').toLowerCase();\n      listEl.innerHTML=\'\';\n      var groups={};\n      sess.filter(function(s){return !f||(s.agent_session_id||\'\').toLowerCase().indexOf(f)>=0||profile(s).toLowerCase().indexOf(f)>=0||s.id.indexOf(f)>=0}).forEach(function(s){\n        var g=profile(s);(groups[g]=groups[g]||[]).push(s);\n      });\n      Object.keys(groups).forEach(function(g){\n        var gh=document.createElement(\'div\');gh.textContent=g+\' · \'+groups[g].length;\n        gh.style.cssText=\'padding:6px 10px;color:#777;font-size:11px;position:sticky;top:0;background:#0d0d10;border-bottom:1px solid #1c1c20\';listEl.appendChild(gh);\n        groups[g].forEach(function(s){\n          var d=document.createElement(\'div\');\n          d.textContent=(s.agent_session_id||s.id).slice(0,24)+(s.cwd?\'  · \'+s.cwd:\'\');\n          d.title=s.id;\n          d.style.cssText=\'padding:8px 10px;cursor:pointer;border-bottom:1px solid #1a1a1e;white-space:nowrap;overflow:hidden;text-overflow:ellipsis\'+(current&&current.id===s.id?\';background:#232329;border-left:3px solid #6ea8fe;padding-left:7px\':\'\');\n          d.onclick=function(){openSession(s)};\n          listEl.appendChild(d);\n        });\n      });\n    }\n    function openSession(s){\n      current=s;renderList();\n      msgEl.innerHTML=\'<div style="color:#666;text-align:center;margin-top:40%">加载消息…</div>\';\n      var isOC=(profile(s)===\'opencode\');\n      var url=isOC?(\'/api/aa/messages?aa=\'+encodeURIComponent(s.id)):(\'/api/aa/messages?aa=\'+encodeURIComponent(s.id));\n      // 统一读 AA 自己的 projection（适用所有 runtime）\n      fetch(BASE+url).then(function(r){return r.json()}).then(function(d){\n        if(!d.messages||!d.messages.length){msgEl.innerHTML=\'<div style="color:#666;text-align:center;margin-top:40%">(无消息)</div>\';return}\n        msgEl.innerHTML=\'\';\n        d.messages.forEach(function(m){\n          var wrap=document.createElement(\'div\');\n          wrap.style.cssText=\'margin-bottom:14px;padding:10px 12px;border-radius:10px;max-width:90%;white-space:pre-wrap;word-break:break-word;\'+(m.role===\'user\'?\'background:#1d2a3a;margin-left:auto\':\'background:#1a1a1f;border:1px solid #2a2a30\');\n          var lab=document.createElement(\'div\');lab.textContent=m.role===\'user\'?\'你\':profile(s).toUpperCase();lab.style.cssText=\'font-size:11px;color:#888;margin-bottom:4px\';\n          var t=document.createElement(\'div\');t.textContent=m.text;\n          wrap.appendChild(lab);wrap.appendChild(t);msgEl.appendChild(wrap);\n        });\n        msgEl.scrollTop=msgEl.scrollHeight;\n      }).catch(function(e){msgEl.innerHTML=\'<div style="color:#c66">错误: \'+esc(e.message)+\'</div>\'});\n    }\n    function load(){\n      fetch(BASE+\'/api/aa/sessions\').then(function(r){return r.json()}).then(function(d){\n        sess=d.sessions||[];panel.querySelector(\'#aa-oc-count\').textContent=sess.length+\' 个会话\';renderList();\n        // 自动检测当前 AA 会话 → 直接打开对应会话消息（适配 OpenCode/DSH/Claude 等）\n        var m=location.hash.match(/session\\/([^/?]+)/);\n        if(m){\n          var aa=m[1];var found=sess.find(function(s){return s.id===aa});\n          if(found){openSession(found);return}\n          // 兜底：用 binding 找\n          fetch(BASE+\'/api/binding?aa=\'+encodeURIComponent(aa)).then(function(r){return r.json()}).then(function(b){\n            if(b.opencode_session){\n              var f2=sess.find(function(s){return s.agent_session_id===b.opencode_session});\n              if(f2)openSession(f2);\n            }\n          }).catch(function(){});\n        }\n      }).catch(function(e){panel.querySelector(\'#aa-oc-count\').textContent=\'服务未启动: \'+e.message});\n    }\n    function send(){\n      if(!current){alert(\'请先选一个会话\');return}\n      if(profile(current)!==\'opencode\'){alert(\'发送仅支持 OpenCode 会话；其它 runtime 的会话为只读查看\');return}\n      var text=inputEl.value.trim();if(!text)return;\n      var btn=panel.querySelector(\'#aa-oc-send\');btn.disabled=true;\n      fetch(BASE+\'/api/send\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},body:JSON.stringify({session:current.agent_session_id,text:text})}).then(function(r){return r.json()}).then(function(d){\n        btn.disabled=false;\n        if(d.error){alert(\'发送失败: \'+d.error);return}\n        inputEl.value=\'\';openSession(current);\n      }).catch(function(e){btn.disabled=false;alert(\'发送失败: \'+e.message)});\n    }\n    panel.querySelector(\'#aa-oc-close\').onclick=function(){panel.remove()};\n    panel.querySelector(\'#aa-oc-filter\').oninput=renderList;\n    panel.querySelector(\'#aa-oc-send\').onclick=send;\n    inputEl.onkeydown=function(e){if(e.ctrlKey&&e.key===\'Enter\'){e.preventDefault();send()}};\n    load();\n  };\n})();\n'
    ui = ui.replace('function wBrowserPanel', capture_js + open_fn + ipc_listen + oc_panel_js + 'function wBrowserPanel', 1)
    # 8b. 会话输入框工具栏加「🌐 会话」原生按钮，打开 OpenCode 会话面板
    old_tb = 'className:"flex items-center gap-1 px-3 pb-2 pt-1.5",children:[(0,A.jsx)(hL,{attachments:e6,onAttach:e8'
    new_tb = 'className:"flex items-center gap-1 px-3 pb-2 pt-1.5",children:[(0,A.jsx)("button",{type:"button",title:"OpenCode 会话",onClick:function(){window.__aaOCPanel&&window.__aaOCPanel()},style:{background:"transparent",border:"1px solid #333",borderRadius:8,padding:"4px 8px",cursor:"pointer",color:"#e8e8ea",fontSize:12},children:"🌐 会话"}),(0,A.jsx)(hL,{attachments:e6,onAttach:e8'
    if old_tb in ui:
        ui = ui.replace(old_tb, new_tb, 1)
        print('OpenCode 会话按钮已注入工具栏')
    else:
        print('工具栏锚点未找到（AA 版本可能变化）')
    # 已有会话的工具栏（pb-3 pt-2 那处）
    old_tb2 = 'className:"flex items-center gap-1 px-3 pb-3 pt-2",children:[(0,A.jsx)(hL,{attachments:eL,onAttach:eH'
    new_tb2 = 'className:"flex items-center gap-1 px-3 pb-3 pt-2",children:[(0,A.jsx)("button",{type:"button",title:"OpenCode 会话",onClick:function(){window.__aaOCPanel&&window.__aaOCPanel()},style:{background:"transparent",border:"1px solid #333",borderRadius:8,padding:"4px 8px",cursor:"pointer",color:"#e8e8ea",fontSize:12},children:"🌐 会话"}),(0,A.jsx)(hL,{attachments:eL,onAttach:eH'
    if old_tb2 in ui:
        ui = ui.replace(old_tb2, new_tb2, 1)
        print('OpenCode 会话按钮已注入已有会话工具栏')
    else:
        print('已有会话工具栏锚点未找到')


    # --- 8. 主进程：把外链弹窗从 shell.openExternal 改为主发 IPC 给渲染层 ---
    mainjs = a.read(MAIN).decode('utf-8', 'replace')
    old_ext = '''        void electron_1.shell.openExternal(url);
        return { action: "deny" };
    });
    window.webContents.on("will-navigate", (event, url) => {'''
    new_ext = '''        if (/^https?:\\/\\//i.test(url)) {
            try { window.webContents.send("aa:open-in-browser", url); } catch (_) {}
            return { action: "deny" };
        }
        void electron_1.shell.openExternal(url);
        return { action: "deny" };
    });
    window.webContents.on("will-navigate", (event, url) => {'''
    assert old_ext in mainjs, 'main.js setWindowOpenHandler fallback not found'
    mainjs = mainjs.replace(old_ext, new_ext, 1)
    print('main.js: popup -> aa:open-in-browser IPC')

    # --- 9. preload：暴露 browser.onOpen 给渲染层订阅 ---
    preload = a.read(PRELOAD).decode('utf-8', 'replace')
    old_tail = '''    device: {
        createAndConnect: (input) => api("/device/create", { method: "POST", body: JSON.stringify(input) }),'''
    new_tail = '''    browser: {
        onOpen: (callback) => subscribe("aa:open-in-browser", callback),
    },
    device: {
        createAndConnect: (input) => api("/device/create", { method: "POST", body: JSON.stringify(input) }),'''
    assert old_tail in preload, 'preload.js device anchor not found'
    preload = preload.replace(old_tail, new_tail, 1)
    print('preload.js: browser.onOpen exposed')

    replacements = {CHUNK: ui.encode('utf-8'), I18N: i18n.encode('utf-8'), MD: md.encode('utf-8'), MAIN: mainjs.encode('utf-8'), PRELOAD: preload.encode('utf-8')}
    out = asar_path + '.patched'
    a.replace_and_write(replacements, out)
    print('WROTE', out, os.path.getsize(out))
    if build:
        if not os.path.exists(asar_path + BAK_SUFFIX):
            shutil.copy2(asar_path, asar_path + BAK_SUFFIX)
            print('backup ->', asar_path + BAK_SUFFIX)
        shutil.copy2(out, asar_path)
        print('APPLIED. Restart Agents Anywhere.')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--asar', default=DEFAULT_ASAR)
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    patch(args.asar, args.apply)
