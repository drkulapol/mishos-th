#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
สร้าง dashboard "กำกับผลงานการชดเชยรายกองทุน ทั้งประเทศ" (index.html ไฟล์เดียว)
ใช้หน้าตาและโค้ดเดียวกับ mishos-rh1 (template_th.html) + ข้อมูลจาก nhso_th_<ปีงบ>_rXX.json

    python build_th.py --fy 2570 --out index.html --yearnav "<a ...>"   # ปีงบ 2570
    python build_th.py --fy 2569 --out 2569.html                       # ปีงบ 2569
    (หรือใช้ build_all.py สร้างทั้งสองปีพร้อมลิงก์เลือกปี)
    python build_th.py --src D:/nhso --out index.html
ต้องมี: data.xlsx, nhso_th_<ปีงบ>_r*.json, template_th.html, labels_rh1.json
"""
import argparse, glob, json, re
from collections import Counter, defaultdict
from pathlib import Path
import pandas as pd

HERE = Path(__file__).parent
TH_M = ["ม.ค.","ก.พ.","มี.ค.","เม.ย.","พ.ค.","มิ.ย.","ก.ค.","ส.ค.","ก.ย.","ต.ค.","พ.ย.","ธ.ค."]
FOCUS_DEFAULT = "11183"


def num(x):
    try: return float(str(x).replace(",", ""))
    except (TypeError, ValueError): return 0.0


def month_name(k):
    y, m = k.split("-")
    return f"{TH_M[int(m)-1]} {y[-2:]}"


def load_hosp(path):
    df = pd.read_excel(path, dtype={"รหัส": str})
    code = "รหัส" if "รหัส" in df.columns else df.columns[3]
    col = lambda *pre: next((c for c in df.columns if any(str(c).startswith(p) for p in pre)), None)
    beds, pop, lvl = col("เตียง", "จำนวนเตียง"), col("POP UC", "ปชช UC"), col("ระดับขีดความสามารถ", "ระดับ")
    out = []
    for d in df.to_dict("records"):
        out.append({"c": str(d[code]).strip().replace(".0", "").zfill(5),
                    "n": re.sub(r"^รพ\.\s+", "รพ.", str(d["หน่วยบริการ"]).strip()),
                    "p": str(d["จังหวัด"]).strip(), "t": str(d["ประเภท"]).strip(), "l": str(d[lvl]).strip(),
                    "b": int(num(d[beds])) if beds else 0, "u": int(num(d[pop])) if pop else 0,
                    "g": str(d["กลุ่มระดับบริการ"]).strip(), "r": str(int(d["เขต"])), "_gi": int(d["ID"])})
    return out, pop or ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=".")
    ap.add_argument("--out", default="index.html")
    ap.add_argument("--fy", type=int, default=2569)
    ap.add_argument("--glob", default=None, help="รูปแบบชื่อไฟล์ข้อมูล (ค่าเริ่มต้น nhso_th_<fy>_r*.json)")
    ap.add_argument("--yearnav", default="", help="HTML ลิงก์เลือกปีงบ")
    ap.add_argument("--hospitals", default="data.xlsx", help="ไฟล์รายชื่อ รพ./กลุ่ม/ประชากร UC")
    a = ap.parse_args()
    src = Path(a.src)
    tpl = (HERE / "template_th.html").read_text(encoding="utf-8")
    LAB = json.loads((HERE / "labels_rh1.json").read_text(encoding="utf-8"))

    hosp, pop_col = load_hosp(src / a.hospitals)
    raw, regions, fetched = {}, set(), []
    for f in sorted(glob.glob(str(src / (a.glob or f"nhso_th_{a.fy}_r*.json")))):
        d = json.load(open(f, encoding="utf-8"))
        regions.add(int(d.get("region", 0))); fetched.append(d.get("fetched_at", ""))
        raw.update(d["data"])
    H = [h for h in hosp if h["c"] in raw]
    HI = {h["c"]: i for i, h in enumerate(H)}
    print(f"เขตที่มีข้อมูล {sorted(regions)} · รพ. {len(H)}/{len(hosp)}")

    def lab(ds, kind, k, fallback):
        return LAB.get(ds, {}).get(kind, {}).get(k) or fallback

    S = {}
    # ---------- L1 budget
    def build_std(ds, name, keyfn, flat, parts, all_label, ordered=False):
        keys, mains, recs = {}, {}, defaultdict(lambda: None)
        kname, mname = defaultdict(Counter), defaultdict(Counter)
        for hc, rec in raw.items():
            if hc not in HI: continue
            for row in rec.get(name) or []:
                kid, mid, kn, mn, vals = keyfn(row)
                kname[kid][kn] += 1; mname[mid][mn] += 1; keys.setdefault(kid, mid)
                cur = recs[(HI[hc], kid)]
                recs[(HI[hc], kid)] = vals if cur is None else [x + y for x, y in zip(cur, vals)]
        kl = sorted(keys) if ordered else sorted(keys, key=lambda k: (keys[k], k))
        kix = {k: i for i, k in enumerate(kl)}
        mids = list(dict.fromkeys(keys[k] for k in kl))
        S[ds] = {
            "keys": [{"id": k, "m": keys[k], "name": lab(ds, "keys", k, kname[k].most_common(1)[0][0])} for k in kl],
            "mains": [{"id": m, "name": lab(ds, "mains", m, mname[m].most_common(1)[0][0])} for m in mids],
            "flat": flat, "ordered": ordered, "parts": parts, "allLabel": all_label,
            "recs": [[h, kix[k]] + [round(v, 2) for v in vals] for (h, k), vals in sorted(recs.items(), key=lambda x: (x[0][0], kix[x[0][1]]))],
        }

    blank = lambda s, d: (str(s).strip() or d)
    build_std("L1", "L1_budget", lambda r: (f'{r.get("M_FUND_CD")}|{r.get("S_FUND_CD")}', str(r.get("M_FUND_CD")),
              blank(r.get("S_FUND_DESC"), "(ไม่ระบุกองทุน/ปรับปรุงบัญชี)"), blank(r.get("M_FUND_DESC"), "(ไม่ระบุกองทุน/ปรับปรุงบัญชี)"),
              [num(r.get("BUDGET"))]), False, ["—"], "รวมทุกกองทุน")
    build_std("L2", "L2_statementuc", lambda r: (f'{r.get("FUND_AF")}|{r.get("SUB_FUND")}', r.get("FUND_AF"),
              r.get("DESCRIPTION") or r.get("SUB_FUND"), f'{r.get("FUND_AF")} · {r.get("DESCRIPTION") or r.get("SUB_FUND")}',
              [num(r.get("ACT_AMT"))]), False, ["—"], "รวมทุกกองทุน")
    build_std("L3", "L3_instrument", lambda r: ((r.get("CODE") or "(ไม่ระบุรหัส)"),) * 4 + ([num(r.get("SUM_AMT")), num(r.get("SUM_AMT_OP")), num(r.get("SUM_AMT_IP"))],),
              True, ["รวม (ผู้ป่วยนอก + ใน)", "ผู้ป่วยนอก (OP)", "ผู้ป่วยใน (IP)"], "รวมทุกรายการ")
    build_std("L4", "L4_ckd_2203", lambda r: (r.get("SUB_FUND"), str(r.get("SUB_FUND")).split("-")[0],
              f'{r.get("SUB_FUND")} · {r.get("DETAIL")}', str(r.get("SUB_FUND")).split("-")[0], [num(r.get("ACT_AMT"))]),
              False, ["—"], "รวมทุกรายการ")
    for ds, nm in (("L5", "L5_moph_2205"), ("L6", "L6_ktp_2263")):
        build_std(ds, nm, lambda r: (r.get("SUB_FUND"), r.get("SUB_FUND"), f'{r.get("SUB_FUND")} · {r.get("DETAIL")}',
                  f'{r.get("SUB_FUND")} · {r.get("DETAIL")}', [num(r.get("ACT_AMT"))]), True, ["—"], "รวมทุกรายการ")
    for ds, nm in (("L7", "L7_csmbs"), ("L8", "L8_lgo")):
        build_std(ds, nm, lambda r: (r.get("MONTH_SEND"), r.get("MONTH_SEND"), month_name(r.get("MONTH_SEND")), month_name(r.get("MONTH_SEND")),
                  [num(r.get("ACT_AMT_OP")) + num(r.get("ACT_AMT_IP")), num(r.get("ACT_AMT_OP")), num(r.get("ACT_AMT_IP")),
                   num(r.get("NUMPT_OP")), num(r.get("NUMPT_IP"))]),
                  True, ["รวม (ผู้ป่วยนอก + ใน)", "ผู้ป่วยนอก (OP)", "ผู้ป่วยใน (IP)"], "รวมทุกเดือน", ordered=True)

    months = [k["id"] for k in S["L7"]["keys"]] or [k["id"] for k in S["L8"]["keys"]]
    gorder = [g for g, _ in sorted({h["g"]: h["_gi"] for h in hosp}.items(), key=lambda x: -x[1])]
    fidx = HI.get(FOCUS_DEFAULT)
    for h in H: h.pop("_gi", None)
    m = re.search(r"(\d+)\s*เม\.ย\.\s*(\d{2,4})", pop_col)
    pop_date = f"{m.group(1)} เม.ย. {m.group(2) if len(m.group(2)) == 4 else '25' + m.group(2)}" if m else pop_col
    last = max(fetched) if fetched else ""
    th_date = f"{int(last[8:10])} {TH_M[int(last[5:7])-1]} {int(last[:4])+543}" if last else "-"
    if len(last) >= 16: th_date += f" {last[11:16]} น."
    reg_txt = "ครบ 12 เขตสุขภาพ" if len(regions) == 12 else "เขตสุขภาพที่ " + ", ".join(map(str, sorted(regions)))
    D = {"H": H, "S": S, "GORDER": gorder, "RORDER": [str(i) for i in range(1, 13)],
         "DEF": {"g": H[fidx]["g"] if fidx is not None else "all", "focus": fidx},
         "META": {"sub": f"{len(H)} หน่วยบริการ · {reg_txt} · {len({h['p'] for h in H})} จังหวัด · ปีงบประมาณ {a.fy} · เทียบผลงานภายในกลุ่ม รพ. ที่เลือก",
                  "asof": f"ข้อมูลจาก NHSO-MIS for Hospital · ประชากร UC ณ {pop_date} · ปรับปรุงข้อมูลล่าสุด {th_date}",
                  "pop": pop_date, "fy": a.fy, "months": f"{month_name(months[0])} – {month_name(months[-1])}" if months else ""}}
    html = tpl.replace("/*__DATA__*/null", json.dumps(D, ensure_ascii=False, separators=(",", ":"))).replace("<!--YEARNAV-->", a.yearnav)
    Path(a.out).write_text(html, encoding="utf-8")
    print(f"สร้าง {a.out} ({len(html)/1e6:.2f} MB)")


if __name__ == "__main__":
    main()
