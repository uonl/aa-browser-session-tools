# -*- coding: utf-8 -*-
"""一键给 Agents Anywhere 2.2.0 注入原生浏览器 tab。

用法：
  python apply.py            # 安装（自动备份）
  python apply.py --revert   # 从备份恢复

流程：下载 v2.2.0 源码 -> patch -> yarn build(静态导出) -> 写回 app.asar
"""
import os, sys, io, json, shutil, tarfile, subprocess, urllib.request, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "_work")
ASAR = r"G:\anywhere\Agents Anywhere\resources\app.asar"
BAK = ASAR + ".bak_before_native_browser"
SRC_URL = "https://codeload.github.com/anywhere-labs/Agents-Anywhere/tar.gz/refs/tags/v2.2.0"
NODE_URL = "https://nodejs.org/dist/v22.16.0/node-v22.16.0-win-x64.zip"
NODE_DIR = os.path.join(WORK, "node22")
NODE_BIN = os.path.join(NODE_DIR, "node-v22.16.0-win-x64")

def log(*a): print("[aa-native-browser]", *a)

def run(cmd, cwd=None, env_extra=None):
    env = dict(os.environ)
    env["PATH"] = NODE_BIN + os.pathsep + env.get("PATH", "")
    if env_extra: env.update(env_extra)
    log("RUN", " ".join(cmd))
    r = subprocess.run(cmd, cwd=cwd, env=env, shell=True)
    if r.returncode != 0:
        raise RuntimeError("命令失败: " + " ".join(cmd))

def ensure_node():
    if os.path.isfile(os.path.join(NODE_BIN, "node.exe")):
        log("Node 已就绪:", NODE_BIN)
        return
    log("下载 Node 22 ...")
    os.makedirs(NODE_DIR, exist_ok=True)
    zpath = os.path.join(NODE_DIR, "node22.zip")
    urllib.request.urlretrieve(NODE_URL, zpath)
    with __import__("zipfile").ZipFile(zpath) as z:
        z.extractall(NODE_DIR)
    log("Node 就绪")

def ensure_source():
    web = os.path.join(WORK, "Agents-Anywhere-2.2.0", "web-next")
    if os.path.isdir(web):
        log("源码已就绪:", web)
        return web
    log("下载 v2.2.0 源码 ...")
    os.makedirs(WORK, exist_ok=True)
    tgz = os.path.join(WORK, "src.tar.gz")
    urllib.request.urlretrieve(SRC_URL, tgz)
    with tarfile.open(tgz, "r:gz") as tf:
        tf.extractall(WORK)
    return web

def apply_changes():
    ensure_node()
    web = ensure_source()
    # patch
    sys.path.insert(0, HERE)
    from patch_webnext import patch
    patch(web)
    # install + build (static export)
    corepack = os.path.join(NODE_BIN, "corepack.cmd")
    run([corepack, "yarn", "install"], cwd=web)
    run([corepack, "yarn", "build"], cwd=web, env_extra={"NEXT_OUTPUT": "export"})
    out = os.path.join(web, "out")
    if not os.path.isdir(out):
        raise RuntimeError("构建未产生 out/ 目录")
    log("构建完成，开始写回 asar ...")
    # write asar
    sys.path.insert(0, HERE)
    from asar_packer import Asar
    if not os.path.exists(ASAR):
        raise RuntimeError("找不到 " + ASAR)
    if not os.path.exists(BAK):
        shutil.copy2(ASAR, BAK)
        log("已备份原版:", BAK)
    a = Asar(ASAR)
    new_out = {}
    for dp, _, fs in os.walk(out):
        for f in fs:
            full = os.path.join(dp, f)
            rel = os.path.relpath(full, out).replace("\\", "/")
            new_out["renderer/out/" + rel] = open(full, "rb").read()
    # keep existing electron IPC files if present
    existing = []
    def walk(n, p=""):
        for k, v in (n.get("files") or {}).items():
            pp = (p + "/" + k).lstrip("/")
            if "files" in v: walk(v, pp)
            elif "offset" in v: existing.append(pp)
    walk(a.header, "")
    repl = dict(new_out)
    for keep in ["dist/electron/main.js", "dist/electron/preload.js",
                 "dist/electron/builtin-browser.js", "dist/electron/browser-preload.js"]:
        if keep in existing:
            repl[keep] = a.read(keep)
    tmp = os.path.join(WORK, "app_patched.asar")
    a.replace_and_write(repl, tmp, remove_prefixes=["renderer/out/"])
    shutil.copy2(tmp, ASAR)
    log("完成！请重新打开 Agents Anywhere。")

def revert():
    if not os.path.exists(BAK):
        log("没有备份，无法恢复"); return
    shutil.copy2(BAK, ASAR)
    log("已从备份恢复:", BAK)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--revert", action="store_true")
    args = ap.parse_args()
    if args.revert: revert()
    else: apply_changes()
