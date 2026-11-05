#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""แปลงข้อมูลแบบย่อจาก browser ({hcode:{ds:[[...]]}}) -> nhso_th_<fy>_rXX.json (รูปแบบเดิม)"""
import json, sys
import pandas as pd
COLS = {"L1_budget":["M_FUND_CD","M_FUND_DESC","S_FUND_CD","S_FUND_DESC","BUDGET"],
        "L2_statementuc":["FUND_AF","SUB_FUND","DESCRIPTION","ACT_AMT"],
        "L3_instrument":["CODE","SUM_AMT","SUM_AMT_OP","SUM_AMT_IP"],
        "L4_ckd_2203":["SUB_FUND","DETAIL","ACT_AMT"], "L5_moph_2205":["SUB_FUND","DETAIL","ACT_AMT"],
        "L6_ktp_2263":["SUB_FUND","DETAIL","ACT_AMT"],
        "L7_csmbs":["MONTH_SEND","ACT_AMT_OP","ACT_AMT_IP","NUMPT_OP","NUMPT_IP"],
        "L8_lgo":["MONTH_SEND","ACT_AMT_OP","ACT_AMT_IP","NUMPT_OP","NUMPT_IP"]}
src, fy, fetched, hosp = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
data = json.load(open(src, encoding="utf-8"))
df = pd.read_excel(hosp, dtype={"รหัส": str})
reg = {str(c).strip().replace(".0","").zfill(5): int(r) for c, r in zip(df["รหัส"], df["เขต"])}
errs = json.load(open(sys.argv[5])) if len(sys.argv) > 5 else []
out = {}
for h, rec in data.items():
    r = reg.get(h)
    if r is None: continue
    out.setdefault(r, {})[h] = {ds: [dict(zip(COLS[ds], row)) for row in rows] for ds, rows in rec.items()}
for r, d in sorted(out.items()):
    e = [x for x in errs if x[0] == fy and reg.get(x[1]) == r]
    json.dump({"fiscal_year": int(fy), "region": r, "fetched_at": fetched, "errors": e, "data": d},
              open(f"nhso_th_{fy}_r{r:02d}.json", "w", encoding="utf-8"), ensure_ascii=False)
    print(fy, r, len(d), "errors", len(e))
