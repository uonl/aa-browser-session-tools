# -*- coding: utf-8 -*-
"""给 Agents Anywhere web-next 源码加一个原生「浏览器」工具 tab。

用法：先解压 web-next 源码到某目录，然后：
  python patch_webnext.py <web-next根目录>
"""
import os, sys, io, json

def patch(root):
    # ---- 0. workspace-header.tsx : 加大 header 高度让按钮下移脱离窗口控制按钮反应区，并加大右侧间距 ----
    p = os.path.join(root, "src", "components", "workspace-header.tsx")
    if os.path.isfile(p):
        s = io.open(p, encoding="utf-8").read()
        # 已经打过补丁则跳过
        if 'h-20 shrink-0 overflow-hidden' not in s:
            s = s.replace('"pointer-events-none z-10 h-14 shrink-0 overflow-hidden"',
                          '"pointer-events-none z-10 h-20 shrink-0 overflow-hidden"', 1)
            s = s.replace('"pointer-events-auto relative flex h-14 items-center gap-3 px-3"',
                          '"pointer-events-auto relative flex h-20 items-center gap-3 pl-3 pr-[14px]"', 1)
            io.open(p, "w", encoding="utf-8").write(s)
            print("patched header height/padding", p)

    # ---- 1. session-tool-tabs.ts : add "browser" kind ----
    p = os.path.join(root, "src", "components", "session-tool-tabs.ts")
    s = io.open(p, encoding="utf-8").read()
    old = 'export type SessionToolKind = "review" | "terminal" | "files"'
    assert old in s, "SessionToolKind not found"
    s = s.replace(old, 'export type SessionToolKind = "review" | "terminal" | "files" | "browser"', 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("patched", p)

    # ---- 2. session-tool-sidebar.tsx ----
    p = os.path.join(root, "src", "components", "session-tool-sidebar.tsx")
    s = io.open(p, encoding="utf-8").read()
    # 2a import Globe
    s = s.replace("  File,\n  FileDiff,", "  File,\n  FileDiff,\n  Globe,", 1)
    # 2b TOOL_META entry
    old = '  files: { icon: File, labelKey: "files", descriptionKey: "filesDescription" },\n}'
    assert old in s, "TOOL_META tail not found"
    s = s.replace(old,
        '  files: { icon: File, labelKey: "files", descriptionKey: "filesDescription" },\n'
        '  browser: { icon: Globe, labelKey: "browser", descriptionKey: "browserDescription" },\n}', 1)
    # 2c TOOL_KINDS
    old = 'const TOOL_KINDS: SessionToolKind[] = ["review", "terminal", "files"]'
    assert old in s
    s = s.replace(old, 'const TOOL_KINDS: SessionToolKind[] = ["review", "terminal", "files", "browser"]', 1)
    # 2d labelKey/descriptionKey union types
    s = s.replace('labelKey: "review" | "terminal" | "files"',
                  'labelKey: "review" | "terminal" | "files" | "browser"', 1)
    s = s.replace('descriptionKey: "reviewDescription" | "terminalDescription" | "filesDescription"',
                  'descriptionKey: "reviewDescription" | "terminalDescription" | "filesDescription" | "browserDescription"', 1)
    # 2e content area: add browser tab rendering before the end of the mapped panels
    anchor = '''                ) : tab.kind === "files" ? (
                  <SessionFilesToolPanel'''
    assert anchor in s, "content anchor not found"
    browser_block = '''                ) : tab.kind === "browser" ? (
                  <BrowserPanel active={panelActive} />
                ) : tab.kind === "files" ? (
                  <SessionFilesToolPanel'''
    s = s.replace(anchor, browser_block, 1)
    # 2e2: browser is not a workspace panel id; exclude it from setPanelMode
    old = 'if (kind !== "review") setPanelMode(kind, "closed")'
    assert old in s, "handleOpenTool not found"
    s = s.replace(old, 'if (kind !== "review" && kind !== "browser") setPanelMode(kind, "closed")', 1)

    # 2e3: 侧栏右上角按钮组下移一点，避免贴着窗口标题栏控制按钮
    s = s.replace('ml-1 flex shrink-0 items-center gap-6',
                  'ml-1 flex shrink-0 items-center gap-0.5', 1)
    # 新建标签页 (+) 按钮也一起下移，和另外两个按钮对齐
    s = s.replace('className="shrink-0 rounded-lg"',
                  'className="shrink-0 rounded-lg"', 1)

    # 2f append BrowserPanel component at end of file
    browser_component = r'''

function BrowserPanel({ active }: { active: boolean }) {
  const [url, setUrl] = React.useState("about:blank")
  const [saved, setSaved] = React.useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem("aa-browser-recent") || "[]") } catch { return [] }
  })
  const commit = React.useCallback((value: string) => {
    let v = value.trim()
    if (!v) return
    if (!/^[a-z][a-z0-9+.-]*:\/\//i.test(v) && !/^file:/i.test(v)) v = "https://" + v
    setUrl(v)
    setSaved((prev) => {
      const next = [v, ...prev.filter((item) => item !== v)].slice(0, 8)
      try { localStorage.setItem("aa-browser-recent", JSON.stringify(next)) } catch {}
      return next
    })
  }, [])
  if (!active) return null
  const isBlank = url === "about:blank"
  return (
    <div className="flex h-full min-h-0 flex-col bg-background text-foreground">
      <div className="flex h-11 shrink-0 items-center gap-2 border-b border-border px-2">
        <button type="button" className="rounded-md px-2 py-1 text-muted-foreground hover:bg-secondary hover:text-foreground"
          onClick={() => { const f = window.document.getElementById("aa-browser-frame") as HTMLIFrameElement | null; try { f?.contentWindow?.history.back() } catch {} }} title="后退">&#8592;</button>
        <button type="button" className="rounded-md px-2 py-1 text-muted-foreground hover:bg-secondary hover:text-foreground"
          onClick={() => { const f = window.document.getElementById("aa-browser-frame") as HTMLIFrameElement | null; try { f?.contentWindow?.history.forward() } catch {} }} title="前进">&#8594;</button>
        <button type="button" className="rounded-md px-2 py-1 text-muted-foreground hover:bg-secondary hover:text-foreground"
          onClick={() => setUrl((u) => u + "#") } title="刷新">&#8635;</button>
        <form className="flex min-w-0 flex-1" onSubmit={(e) => { e.preventDefault(); commit(url) }}>
          <input value={url === "about:blank" ? "" : url} onChange={(e) => setUrl(e.target.value)}
            placeholder="Search or enter a URL"
            className="h-8 w-full rounded-full border border-border bg-secondary/40 px-3 text-xs outline-none placeholder:text-muted-foreground focus:border-ring" />
        </form>
      </div>
      <div className="relative min-h-0 flex-1">
        {isBlank ? (
          <div className="h-full overflow-auto p-6">
            <h3 className="mb-4 text-sm font-semibold text-muted-foreground">Recent</h3>
            <div className="flex flex-col gap-1">
              {saved.length === 0 ? <p className="text-xs text-muted-foreground">在上方输入网址开始浏览。</p> : null}
              {saved.map((item) => (
                <button key={item} type="button" onClick={() => commit(item)}
                  className="flex flex-col items-start gap-0.5 rounded-lg px-3 py-2 text-left hover:bg-secondary">
                  <span className="text-sm">{item.replace(/^https?:\/\//, "").slice(0, 48)}</span>
                  <span className="text-[11px] text-muted-foreground">{item}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <iframe id="aa-browser-frame" src={url} title="browser"
            className="h-full w-full border-0 bg-white"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups" />
        )}
      </div>
    </div>
  )
}
'''
    s = s.rstrip() + "\n" + browser_component
    io.open(p, "w", encoding="utf-8").write(s)
    print("patched", p)

    # ---- 3. i18n ----
    for name, browser, desc in [
        ("zh-CN.json", "浏览器", "在侧栏浏览网页 / 本地 HTML"),
        ("en.json", "Browser", "Browse web pages / local HTML in the sidebar"),
    ]:
        p = os.path.join(root, "messages", name)
        s = io.open(p, encoding="utf-8").read()
        anchor = '"filesDescription":'
        idx = s.find(anchor)
        assert idx >= 0, f"{name}: filesDescription not found"
        # insert after the filesDescription line
        eol = s.find("\n", idx)
        insert = f'\n        "browser": "{browser}",\n        "browserDescription": "{desc}",'
        s = s[:eol] + insert + s[eol:]
        io.open(p, "w", encoding="utf-8").write(s)
        print("patched", p)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python patch_webnext.py <web-next-root>")
        sys.exit(1)
    patch(sys.argv[1])
    print("DONE")

