#!/usr/bin/env python3
"""Re-add the Meta Muse provider into PI-Desktop's pi.sqlite database.

PI-Desktop stores its providers in ~/.pi-desktop/pi.sqlite. An app update can
wipe that table. This script re-inserts the "Meta Muse" provider that points at
the local bridge (http://127.0.0.1:11471/v1). It is idempotent: safe to run
more than once.

Usage (close PI-Desktop first):
  python3 restore_muse_provider.py [path_to_pi.sqlite]

Defaults to ~/.pi-desktop/pi.sqlite on every OS.
"""
import json
import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


def main():
    if len(sys.argv) > 1:
        db = sys.argv[1]
    else:
        home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
        db = os.path.join(home, ".pi-desktop", "pi.sqlite")
    if not os.path.exists(db):
        print(f"ERROR: database not found: {db}")
        return 1
    prov = load("provider_row.json")
    models = load("models_rows.json")
    now = int(time.time() * 1000)
    prov["updated_at"] = now
    conn = sqlite3.connect(db)
    try:
        c = conn.cursor()
        cols = list(prov.keys())
        c.execute(
            f"INSERT OR REPLACE INTO providers ({','.join(cols)}) "
            f"VALUES ({','.join('?' * len(cols))})",
            [prov[k] for k in cols])
        c.execute("DELETE FROM models WHERE provider_id='meta-muse-bridge-1'")
        for m in models:
            m = dict(m)
            m["updated_at"] = now
            mc = list(m.keys())
            c.execute(
                f"INSERT INTO models ({','.join(mc)}) "
                f"VALUES ({','.join('?' * len(mc))})",
                [m[k] for k in mc])
        conn.commit()
        ok_p = c.execute(
            "select count(*) from providers "
            "where id='meta-muse-bridge-1'").fetchone()[0]
        ok_m = c.execute(
            "select count(*) from models "
            "where provider_id='meta-muse-bridge-1'").fetchone()[0]
        print(f"DONE: providers={ok_p}, models={ok_m} in {db}")
        return 0 if (ok_p == 1 and ok_m == len(models)) else 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
