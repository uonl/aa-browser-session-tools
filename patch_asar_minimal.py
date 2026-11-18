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
BAK_SUFFIX = ".bak_before_minimal_browser"

# 浏览器面板组件（插入到模块作用域内，复用 bundle 里的 T=React / A=jsx-runtime / VR=Globe）
BROWSER_PANEL = r'''function wBrowserPanel(W){var H=T.createElement,V=T.useState("about:blank"),Q=V[0],Y=V[1],K=T.useState(function(){try{return JSON.parse(localStorage.getItem("aa-browser-recent")||"[]")}catch(e){return[]}}),R=K[0],G=K[1];function nav(u){if(!u)return;var v=String(u).trim();if(!/^[a-z][a-z0-9+.-]*:\/\//i.test(v)&&!/^file:/i.test(v))v="https://"+v;Y(v);G(function(x){var y=[v].concat(x.filter(function(s){return s!==v})).slice(0,8);try{localStorage.setItem("aa-browser-recent",JSON.stringify(y))}catch(e){}return y})}T.useEffect(function(){function h(e){if(e.key==="aa-browser-goto"&&e.newValue){nav(e.newValue);try{localStorage.removeItem("aa-browser-goto")}catch(a){}}}window.addEventListener("storage",h);try{var g=localStorage.getItem("aa-browser-goto");if(g){nav(g);localStorage.removeItem("aa-browser-goto")}}catch(a){}return function(){window.removeEventListener("storage",h)}},[]);if(!W)return null;var L=(function(){try{return /[\u4e00-\u9fff]/.test((document.body&&document.body.innerText||"").slice(0,6000))}catch(e){return true}})();function X(){var p=document.querySelector('[role=tabpanel]:not([aria-hidden="true"])');if(p){var lab=p.getAttribute('aria-labelledby');var tab=lab?document.getElementById(lab):null;if(tab){var bs=tab.parentElement.querySelectorAll('button');if(bs.length>1)bs[bs.length-1].click()}}}return H("div",{className:"flex h-full min-h-0 flex-col bg-background text-foreground"},H("div",{className:"flex h-11 shrink-0 items-center gap-1 border-b border-border px-2"},H("button",{className:"rounded px-2 py-1 text-xs text-muted-foreground hover:bg-secondary",onClick:function(){var f=document.getElementById("aa-browser-frame");if(f)f.contentWindow.history.back()}},L?"\u540e\u9000":"Back"),H("button",{className:"rounded px-2 py-1 text-xs text-muted-foreground hover:bg-secondary",onClick:function(){var f=document.getElementById("aa-browser-frame");if(f)f.contentWindow.history.forward()}},L?"\u524d\u8fdb":"Forward"),H("button",{className:"rounded px-2 py-1 text-xs text-muted-foreground hover:bg-secondary",onClick:function(){var f=document.getElementById("aa-browser-frame");if(f)f.src=f.src}},L?"\u5237\u65b0":"Reload"),H("input",{value:Q==="about:blank"?"":Q,onChange:function(e){Y(e.target.value)},onKeyDown:function(e){if(e.key==="Enter")nav(e.target.value)},placeholder:"Search or enter a URL",className:"h-8 min-w-0 flex-1 rounded-full border border-border bg-secondary/40 px-3 text-xs outline-none"}),H("button",{className:"rounded px-2 py-1 text-xs text-muted-foreground hover:bg-secondary",onClick:X},L?"\u5173\u95ed":"Close")),Q==="about:blank"?H("div",{className:"flex-1 overflow-auto p-6"},H("h3",{className:"mb-4 text-sm font-semibold text-muted-foreground"},"Recent"),R.length===0?H("p",{className:"text-xs text-muted-foreground"},L?"\u5728\u4e0a\u65b9\u8f93\u5165\u7f51\u5740\u5f00\u59cb\u6d4f\u89c8\u3002":"Enter a URL above to start browsing."):H("div",{className:"flex flex-col gap-1"},R.map(function(u,i){return H("button",{key:i,onClick:function(){nav(u)},className:"rounded-lg px-3 py-2 text-left text-sm hover:bg-secondary"},u)}))):H("iframe",{id:"aa-browser-frame",src:Q,title:"browser",className:"h-full w-full border-0 bg-white"}))}'''

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
        new_a = 'return(0,t.jsx)("a",{href:e,target:"_blank",rel:"noreferrer",onClick:function(ev){if(/^https?:\\/\\//i.test(e)&&window.__aaOpenInBrowser){ev.preventDefault();window.__aaOpenInBrowser(e)}},...a,children:r})'
        md = md.replace(old_a, new_a, 1)
        print('markdown link interceptor added')
    else:
        print('WARN: markdown link anchor not found')
    # --- 7. 注册 __aaOpenInBrowser 全局函数 ---
    open_fn = 'window.__aaOpenInBrowser=function(u){try{localStorage.setItem("aa-browser-goto",u)}catch(e){}var all=document.querySelectorAll(\'div,button\');for(var i=0;i<all.length;i++){var el=all[i];var t=(el.textContent||\'\').trim();if(t.indexOf(\'\\u6d4f\\u89c8\\u5668\')>=0&&t.indexOf(\'\\u5728\\u4fa7\\u680f\')>=0&&el.getBoundingClientRect().width>0){var card=el;for(var k=0;k<6&&card;k++){if(card.tagName===\'BUTTON\'){card.click();return}card=card.parentElement}var c=el.parentElement&&el.parentElement.querySelector(\'button\');if(c){c.click();return}}}};'
    ui = ui.replace('function wBrowserPanel', open_fn + 'function wBrowserPanel', 1)

    replacements = {CHUNK: ui.encode('utf-8'), I18N: i18n.encode('utf-8'), MD: md.encode('utf-8')}
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
