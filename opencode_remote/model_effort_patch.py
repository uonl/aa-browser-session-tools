# -*- coding: utf-8 -*-
"""按 OpenCode 原生 variants 决定哪些模型显示「思考程度」子菜单。

OpenCode 的 /api/model 给每个模型返回 variants（reasoning effort 档位）；
variants 为空的模型没有思考程度。AA 的 ACP 数据没有暴露这个信息，导致
所有模型都被显示 effort 子菜单。本模块：

1. 运行时查询 `opencode api --standalone GET /api/model`，导出无 effort 模型 ID；
2. 写入 Connector 的 acp/profiles/opencode/no_effort_models.py；
3. patch acp/domain/catalogs.py 的 model_catalog()，无 effort 模型的 reasoning_items
   设为空 —— AA 前端就不显示 effort 子菜单。

由 apply_opencode.py 在注入时调用；也可单独运行：`python model_effort_patch.py`
"""
import os, sys, glob, json, subprocess

# 离线兜底：当前已知无 effort 的模型（查询失败时使用）
DEFAULT_NO_EFFORT_MODELS = {
    "opencode/big-pickle",
    "opencode/iceman-free",
    "opencode/longcat-2.5-free",
    "opencode/mimo-v2.6-flash-free",
    "opencode/nemotron-3.5-lightning-free",
    "ollama/dafeiyu:latest",
    "ollama/deepseek-r1:7b",
}

OLD_EXPR = '''            reasoning_items=tuple(
                RuntimeReasoningItem(
                    id=effort["value"],
                    title=effort["name"],
                    selection_id=selection_id(value["value"], effort["value"]),
                )
                for effort in efforts
            ),'''
NEW_EXPR = '''            reasoning_items=(
                () if (runtime == "opencode" and value.get("value") in _no_effort_models())
                else tuple(
                    RuntimeReasoningItem(
                        id=effort["value"],
                        title=effort["name"],
                        selection_id=selection_id(value["value"], effort["value"]),
                    )
                    for effort in efforts
                )
            ),  # opencode patch: per-model effort support'''
HELPER = '''

def _no_effort_models():
    try:
        from ..profiles.opencode.no_effort_models import NO_EFFORT_MODELS
        return NO_EFFORT_MODELS
    except Exception:
        return set()
'''
MARKER = 'opencode patch: per-model effort support'


def find_cli():
    cands = []
    for base in (
        os.path.join(os.environ.get("APPDATA", ""), "ai.opencode.desktop", "cli"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "ai.opencode.desktop", "resources"),
    ):
        cands += glob.glob(os.path.join(base, "*", "opencode-cli.exe"))
        direct = os.path.join(base, "opencode-cli.exe")
        if os.path.isfile(direct):
            cands.append(direct)
    import re
    def ver_key(p):
        m = re.search(r"(\d+)\.(\d+)\.(\d+)", p)
        return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)
    cands.sort(key=ver_key, reverse=True)
    return cands[0] if cands else None


def build_no_effort_models():
    cli = find_cli()
    if not cli:
        return set(DEFAULT_NO_EFFORT_MODELS)
    try:
        out = subprocess.run(
            [cli, "api", "--standalone", "GET", "/api/model"],
            capture_output=True, timeout=60,
        )
        raw = out.stdout.decode("utf-8", "replace").strip()
        i = raw.find('{"location"')
        if i < 0:
            return set(DEFAULT_NO_EFFORT_MODELS)
        data = json.loads(raw[i:])
        found = set()
        for m in data.get("data", []):
            if not (m.get("variants") or []):
                found.add(m.get("providerID", "") + "/" + m.get("modelID", ""))
        # ollama 旧 provider 在本机 server 视图里可能缺失，用兜底补齐
        found |= {x for x in DEFAULT_NO_EFFORT_MODELS if x.startswith("ollama/")}
        return found or set(DEFAULT_NO_EFFORT_MODELS)
    except Exception:
        return set(DEFAULT_NO_EFFORT_MODELS)


def find_runtime_bases():
    bases = []
    root = os.path.join(os.environ.get("APPDATA", ""), "Agents Anywhere", "connector", "connector-source")
    for d in glob.glob(os.path.join(root, "*")):
        rp = os.path.join(d, "connector", "runtimes")
        if os.path.isfile(os.path.join(rp, "acp", "domain", "catalogs.py")):
            bases.append(rp)
    g = r"G:\anywhere\Agents Anywhere\resources\connector\connector\runtimes"
    if os.path.isfile(os.path.join(g, "acp", "domain", "catalogs.py")):
        bases.append(g)
    return bases


def apply(log=print):
    no_effort = build_no_effort_models()
    log("无思考程度模型:", len(no_effort))
    for base in find_runtime_bases():
        # write no_effort_models.py
        nm_dir = os.path.join(base, "acp", "profiles", "opencode")
        os.makedirs(nm_dir, exist_ok=True)
        with open(os.path.join(nm_dir, "no_effort_models.py"), "w", encoding="utf-8") as f:
            f.write("NO_EFFORT_MODELS = set()\n")
            for m in sorted(no_effort):
                f.write("NO_EFFORT_MODELS.add(%r)\n" % m)
        # patch catalogs.py
        cat = os.path.join(base, "acp", "domain", "catalogs.py")
        t = open(cat, encoding="utf-8").read()
        if MARKER in t:
            continue
        if OLD_EXPR in t:
            t = t.replace(OLD_EXPR, NEW_EXPR, 1)
            if "def _no_effort_models()" not in t:
                t += HELPER
            open(cat, "w", encoding="utf-8").write(t)
            log("per-model effort patch:", cat)
        else:
            log("anchor 未找到:", cat)


if __name__ == "__main__":
    apply()
