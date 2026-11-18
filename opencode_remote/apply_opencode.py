# -*- coding: utf-8 -*-
"""把 OpenCode 注册为 Agents Anywhere 的 ACP runtime。

注入的 definition.py 在每次被 Connector import 时会**动态探测**本机已安装的
opencode-cli.exe（按版本号从新到旧排序），因此 OpenCode Desktop 升级后无需重跑本脚本，
只要重启 AA（Connector 重新 import）就会自动使用新版本 CLI。
"""
import os, sys, io, shutil, glob, re, argparse

APPDATA = os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming"))
LOCALAPPDATA = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
CONNECTOR_SRC = os.path.join(APPDATA, "Agents Anywhere", "connector", "connector-source")


def log(*a):
    print("[opencode-remote]", *a)


def _desktop_cli_candidates():
    """探测 OpenCode Desktop 自带的 opencode-cli.exe，按版本号从新到旧排列。"""
    found = []
    bases = (
        os.path.join(APPDATA, "ai.opencode.desktop", "cli"),
        os.path.join(LOCALAPPDATA, "Programs", "ai.opencode.desktop", "resources"),
    )
    for base in bases:
        for exe in glob.glob(os.path.join(base, "*", "opencode-cli.exe")):
            found.append(exe.replace("\\", "/"))
        direct = os.path.join(base, "opencode-cli.exe")
        if os.path.isfile(direct):
            found.append(direct.replace("\\", "/"))
    seen = set()
    found = [x for x in found if not (x in seen or seen.add(x))]

    def ver_key(path):
        m = re.search(r"(\d+)\.(\d+)\.(\d+)", path)
        return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)

    found.sort(key=ver_key, reverse=True)
    return found


# 注入到 Connector 的 definition.py —— 运行时动态探测，OpenCode 升级自动适配
DEFINITION = '''"""OpenCode ACP runtime (injected by aa-native-browser-tab).

The executable candidates are resolved dynamically at import time, so upgrading
OpenCode Desktop is picked up automatically on the next Connector restart —
no need to re-run the injector.
"""
import os as _os, glob as _glob, re as _re
from ...domain.agents import AcpAgentDefinition, Executable


def _candidates():
    found = []
    for base in (
        _os.path.join(_os.environ.get("APPDATA", ""), "ai.opencode.desktop", "cli"),
        _os.path.join(_os.environ.get("LOCALAPPDATA", ""), "Programs", "ai.opencode.desktop", "resources"),
    ):
        for exe in _glob.glob(_os.path.join(base, "*", "opencode-cli.exe")):
            found.append(exe.replace("\\\\", "/"))
        direct = _os.path.join(base, "opencode-cli.exe")
        if _os.path.isfile(direct):
            found.append(direct.replace("\\\\", "/"))
    seen = set()
    found = [x for x in found if not (x in seen or seen.add(x))]

    def _key(p):
        m = _re.search(r"(\\d+)\\.(\\d+)\\.(\\d+)", p)
        return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)

    found.sort(key=_key, reverse=True)
    return tuple(found + [
        "~/.opencode/bin/opencode",
        "~/.local/bin/opencode",
        "opencode",
    ])


OPENCODE = AcpAgentDefinition(
    runtime_type="opencode",
    display_name="OpenCode",
    description="在本机运行 opencode acp，沿用本机 OpenCode 的模型与登录配置。",
    executable=Executable("opencode", candidates=_candidates()),
    arguments=("acp",),
    check=("acp", "--help"),
    version=("--version",),
)
'''


def find_runtime_dirs():
    dirs = []
    for d in glob.glob(os.path.join(CONNECTOR_SRC, "*")):
        rp = os.path.join(d, "connector", "runtimes")
        if os.path.isfile(os.path.join(rp, "providers.py")):
            dirs.append(rp)
    g = r"G:\anywhere\Agents Anywhere\resources\connector\connector\runtimes"
    if os.path.isfile(os.path.join(g, "providers.py")):
        dirs.append(g)
    return dirs


def inject(runtimes_dir):
    prof = os.path.join(runtimes_dir, "acp", "profiles", "opencode")
    os.makedirs(prof, exist_ok=True)
    init = os.path.join(prof, "__init__.py")
    if not os.path.exists(init):
        io.open(init, "w", encoding="utf-8").write("")
    df = os.path.join(prof, "definition.py")
    io.open(df, "w", encoding="utf-8").write(DEFINITION)
    log("写入", df)

    pp = os.path.join(runtimes_dir, "providers.py")
    s = io.open(pp, encoding="utf-8").read()
    if "AcpAgentProvider(OPENCODE)" in s:
        log("已注册，跳过", pp)
        return
    anchor = "from connector.runtime_protocol import RuntimeProvider"
    if anchor in s and "profiles.opencode.definition import OPENCODE" not in s:
        s = s.replace(
            anchor,
            anchor
            + "\nfrom connector.runtimes.acp.profiles.opencode.definition import OPENCODE\n"
            + "from connector.runtimes.acp.provider import AcpAgentProvider",
            1,
        )
    if "return (" in s:
        s = s.replace(
            "        DshProvider(),",
            "        DshProvider(),\n        AcpAgentProvider(OPENCODE),",
            1,
        )
        if "AcpAgentProvider(OPENCODE)" not in s:
            s = s.replace(
                "    return (CodexProvider(), ClaudeProvider(), DshProvider(),",
                "    return (CodexProvider(), ClaudeProvider(), DshProvider(), AcpAgentProvider(OPENCODE),",
                1,
            )
    else:
        s = s.replace(
            "return CodexProvider(), ClaudeProvider(), DshProvider()",
            "return CodexProvider(), ClaudeProvider(), DshProvider(), AcpAgentProvider(OPENCODE)",
            1,
        )
    io.open(pp, "w", encoding="utf-8").write(s)
    log("注册 OpenCode:", pp)


def _current_cli_desc():
    c = _desktop_cli_candidates()
    if not c:
        return "未探测到 opencode-cli.exe"
    m = re.search(r"(\d+\.\d+\.\d+)", c[0])
    return "%s (版本 %s)" % (c[0], m.group(1) if m else "?")


def status():
    dirs = find_runtime_dirs()
    log("找到 Connector 源码目录:", len(dirs))
    for d in dirs:
        df = os.path.join(d, "acp", "profiles", "opencode", "definition.py")
        reg = os.path.isfile(df)
        dynamic = False
        if reg:
            t = io.open(df, encoding="utf-8").read()
            dynamic = "def _candidates()" in t
        state = "已注入(动态探测)" if reg and dynamic else ("已注入(旧版固定路径)" if reg else "未注入")
        log(" ", d, "->", state)
    log("当前探测到的 CLI:", _current_cli_desc())


def check():
    """自动更新检测：确认所有源码目录都是动态探测版，并显示当前 CLI 版本。"""
    dirs = find_runtime_dirs()
    outdated = []
    missing = []
    for d in dirs:
        df = os.path.join(d, "acp", "profiles", "opencode", "definition.py")
        if not os.path.isfile(df):
            missing.append(d)
            continue
        t = io.open(df, encoding="utf-8").read()
        if "def _candidates()" not in t:
            outdated.append(d)
    log("当前 CLI:", _current_cli_desc())
    if missing:
        log("未注入目录:", len(missing))
        for d in missing:
            log("   ", d)
    if outdated:
        log("旧版固定路径(需重跑注入):", len(outdated))
        for d in outdated:
            log("   ", d)
    if not missing and not outdated:
        log("[OK] 全部为动态探测版 —— OpenCode 升级后重启 AA 即自动适配，无需重跑注入")
    else:
        log("请运行: python apply_opencode.py")


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
    ap.add_argument("--status", action="store_true", help="查看各源码目录注入状态")
    ap.add_argument("--check", action="store_true", help="自动更新检测")
    ap.add_argument("--revert", action="store_true")
    args = ap.parse_args()
    if args.status:
        status()
    elif args.check:
        check()
    elif args.revert:
        revert()
    else:
        dirs = find_runtime_dirs()
        if not dirs:
            log("未找到 Connector 源码目录，请确认 AA 已安装")
            sys.exit(1)
        for d in dirs:
            inject(d)
        log("完成，请重新打开 Agents Anywhere。")
