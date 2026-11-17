# -*- coding: utf-8 -*-
"""把 OpenCode 注册为 Agents Anywhere 的 ACP runtime。"""
import os, sys, io, shutil, glob, argparse

APPDATA = os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming"))
CONNECTOR_SRC = os.path.join(APPDATA, "Agents Anywhere", "connector", "connector-source")
MARK = "builtin_browser_placeholder"  # 仅检测用，不写入

DEFINITION = '''"""OpenCode ACP runtime (injected by aa-native-browser-tab)."""
from ...domain.agents import AcpAgentDefinition, Executable

OPENCODE = AcpAgentDefinition(
    runtime_type="opencode",
    display_name="OpenCode",
    description="在本机运行 opencode acp，沿用本机 OpenCode 的模型与登录配置。",
    executable=Executable(
        "opencode",
        candidates=(
            "~/.opencode/bin/opencode",
            "~/.local/bin/opencode",
        ),
    ),
    arguments=("acp",),
    check=("acp", "--help"),
    version=("--version",),
)
'''

def log(*a): print("[opencode-remote]", *a)

def find_runtime_dirs():
    dirs = []
    for d in glob.glob(os.path.join(CONNECTOR_SRC, "*")):
        rp = os.path.join(d, "connector", "runtimes")
        if os.path.isfile(os.path.join(rp, "providers.py")):
            dirs.append(rp)
    # also G drive packaged source
    g = r"G:\anywhere\Agents Anywhere\resources\connector\connector\runtimes"
    if os.path.isfile(os.path.join(g, "providers.py")):
        dirs.append(g)
    return dirs

def inject(runtimes_dir):
    prof = os.path.join(runtimes_dir, "acp", "profiles", "opencode")
    os.makedirs(prof, exist_ok=True)
    init = os.path.join(prof, "__init__.py")
    if not os.path.exists(init): io.open(init, "w", encoding="utf-8").write("")
    df = os.path.join(prof, "definition.py")
    io.open(df, "w", encoding="utf-8").write(DEFINITION)
    log("写入", df)

    pp = os.path.join(runtimes_dir, "providers.py")
    s = io.open(pp, encoding="utf-8").read()
    if "AcpAgentProvider(OPENCODE)" in s:
        log("已注册，跳过", pp); return
    # import
    anchor = "from connector.runtime_protocol import RuntimeProvider"
    if anchor in s and "profiles.opencode.definition import OPENCODE" not in s:
        s = s.replace(anchor,
            anchor + "\nfrom connector.runtimes.acp.profiles.opencode.definition import OPENCODE\n"
            "from connector.runtimes.acp.provider import AcpAgentProvider", 1)
    # register: append to default_runtime_providers return tuple
    if "return (" in s:
        # insert into tuple-returning form
        s = s.replace("        DshProvider(),", "        DshProvider(),\n        AcpAgentProvider(OPENCODE),", 1)
        if "AcpAgentProvider(OPENCODE)" not in s:
            s = s.replace("    return (CodexProvider(), ClaudeProvider(), DshProvider(),",
                          "    return (CodexProvider(), ClaudeProvider(), DshProvider(), AcpAgentProvider(OPENCODE),", 1)
    else:
        s = s.replace("return CodexProvider(), ClaudeProvider(), DshProvider()",
                      "return CodexProvider(), ClaudeProvider(), DshProvider(), AcpAgentProvider(OPENCODE)", 1)
    io.open(pp, "w", encoding="utf-8").write(s)
    log("注册 OpenCode:", pp)

def status():
    dirs = find_runtime_dirs()
    log("找到 Connector 源码目录:", len(dirs))
    for d in dirs:
        reg = os.path.isfile(os.path.join(d, "acp", "profiles", "opencode", "definition.py"))
        log(" ", d, "->", "已注入" if reg else "未注入")

def revert():
    for d in find_runtime_dirs():
        prof = os.path.join(d, "acp", "profiles", "opencode")
        if os.path.isdir(prof):
            shutil.rmtree(prof, ignore_errors=True)
        pp = os.path.join(d, "providers.py")
        if os.path.isfile(pp):
            s = io.open(pp, encoding="utf-8").read()
            s = s.replace("from connector.runtimes.acp.profiles.opencode.definition import OPENCODE\n", "")
            s = s.replace("from connector.runtimes.acp.provider import AcpAgentProvider\n", "")
            s = s.replace("        AcpAgentProvider(OPENCODE),\n", "")
            s = s.replace(", AcpAgentProvider(OPENCODE)", "")
            io.open(pp, "w", encoding="utf-8").write(s)
        log("已清理", d)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--revert", action="store_true")
    args = ap.parse_args()
    if args.status: status()
    elif args.revert: revert()
    else:
        dirs = find_runtime_dirs()
        if not dirs: log("未找到 Connector 源码目录，请确认 AA 已安装"); sys.exit(1)
        for d in dirs: inject(d)
        log("完成，请重新打开 Agents Anywhere。")
