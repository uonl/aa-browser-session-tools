# -*- coding: utf-8 -*-
"""把 OpenCode 注册为 Agents Anywhere 的 ACP runtime。

OpenCode Desktop 把 CLI 放在 %APPDATA%/ai.opencode.desktop/cli/<版本>-x64/opencode-cli.exe，
版本号会随升级变化。本脚本在注入时动态探测所有已安装版本，按版本号从新到旧写入 candidates，
避免写死路径导致升级后找不到 CLI。
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
    # 去重并保持顺序
    seen = set()
    found = [x for x in found if not (x in seen or seen.add(x))]

    def ver_key(path):
        m = re.search(r"(\d+)\.(\d+)\.(\d+)", path)
        return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)

    found.sort(key=ver_key, reverse=True)
    return found


def make_definition():
    cands = _desktop_cli_candidates() + [
        "~/.opencode/bin/opencode",
        "~/.local/bin/opencode",
        "opencode",
    ]
    lines = "\n".join('            "%s",' % c.replace('"', '\\"') for c in cands)
    return '''"""OpenCode ACP runtime (injected by aa-native-browser-tab)."""
from ...domain.agents import AcpAgentDefinition, Executable

# opencode-cli.exe ships with the OpenCode desktop app and is not on PATH.
# Candidates are generated at inject time (sorted newest-first by version).
OPENCODE = AcpAgentDefinition(
    runtime_type="opencode",
    display_name="OpenCode",
    description="在本机运行 opencode acp，沿用本机 OpenCode 的模型与登录配置。",
    executable=Executable(
        "opencode",
        candidates=(
%s
        ),
    ),
    arguments=("acp",),
    check=("acp", "--help"),
    version=("--version",),
)
''' % lines


def find_runtime_dirs():
    dirs = []
    for d in glob.glob(os.path.join(CONNECTOR_SRC, "*")):
        rp = os.path.join(d, "connector", "runtimes")
        if os.path.isfile(os.path.join(rp, "providers.py")):
            dirs.append(rp)
    # G drive packaged source
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
    io.open(df, "w", encoding="utf-8").write(make_definition())
    log("写入", df)

    pp = os.path.join(runtimes_dir, "providers.py")
    s = io.open(pp, encoding="utf-8").read()
    if "AcpAgentProvider(OPENCODE)" in s:
        log("已注册，跳过", pp)
        return
    # import
    anchor = "from connector.runtime_protocol import RuntimeProvider"
    if anchor in s and "profiles.opencode.definition import OPENCODE" not in s:
        s = s.replace(
            anchor,
            anchor
            + "\nfrom connector.runtimes.acp.profiles.opencode.definition import OPENCODE\n"
            + "from connector.runtimes.acp.provider import AcpAgentProvider",
            1,
        )
    # register into default_runtime_providers
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


def status():
    dirs = find_runtime_dirs()
    log("找到 Connector 源码目录:", len(dirs))
    for d in dirs:
        df = os.path.join(d, "acp", "profiles", "opencode", "definition.py")
        reg = os.path.isfile(df)
        ver = ""
        if reg:
            t = io.open(df, encoding="utf-8").read()
            m = re.search(r"cli/(\d+\.\d+\.\d+)-x64", t)
            ver = " CLI=" + (m.group(1) if m else "?")
        log(" ", d, "->", ("已注入" + ver) if reg else "未注入")
    log("探测到的 CLI:", _desktop_cli_candidates()[:4])


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
    if args.status:
        status()
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
