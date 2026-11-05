#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""สร้างทั้งสองปีงบ: index.html = ปีงบ 2570 (ค่าเริ่มต้น), 2569.html = ปีงบ 2569 พร้อมแถบเลือกปีงบ"""
import subprocess, sys
YEARS = [(2570, "index.html"), (2569, "2569.html")]
def nav(cur):
    return "\n".join(f'  <a href="{f}" data-fy="{y}"' + (' aria-current="page"' if y == cur else "") + f'>ปีงบประมาณ {y}</a>' for y, f in YEARS)
for y, f in YEARS:
    subprocess.run([sys.executable, "build_th.py", "--fy", str(y), "--out", f, "--yearnav", nav(y)] + sys.argv[1:], check=True)
