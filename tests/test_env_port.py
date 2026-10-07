import os, sys, importlib, subprocess

def run(mod, env_name):
    code = (
        "import os,importlib,sys;"
        f"os.environ['{env_name}']='abc';"
        f"m=importlib.import_module('{mod}');print(m.PORT)"
    )
    env = dict(os.environ); env["PYTHONDONTWRITEBYTECODE"]="1"
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=60)
    assert r.returncode == 0, r.stderr
    return int(r.stdout.strip())

def test_muse_bridge_garbage_port_falls_back():
    assert run("muse_bridge", "MUSE_BRIDGE_PORT") == 11471

def test_codex_bridge_garbage_port_falls_back():
    assert run("codex_bridge", "CODEX_BRIDGE_PORT") == 11472

def test_muse_bridge_blank_port_falls_back():
    assert run_blank("muse_bridge", "MUSE_BRIDGE_PORT") == 11471

def run_blank(mod, env_name):
    code = f"import os,importlib;os.environ['{env_name}']='  ';import {mod};print({mod}.PORT)"
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return int(r.stdout.strip())
