# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas"]
# ///
"""把 data/ 的三個 CSV 整理成網頁直接載入的 docs/data.js（window.DATA）。

用法：uv run work/build_data.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
rd = lambda name: pd.read_csv(ROOT / "data" / name, encoding="utf-8-sig", dtype=str, keep_default_na=False)

enr = rd("enrollment.csv")
enr["count"] = enr["count"].astype(int)
enr = (enr.groupby(["semester", "college", "dept", "degree", "gender"], as_index=False)["count"].sum()
          .sort_values(["semester", "college", "dept", "degree", "gender"]))

lv = rd("leave.csv")
lv[["new_leave", "on_leave_end"]] = lv[["new_leave", "on_leave_end"]].astype(int)
lv = (lv.groupby(["semester", "college", "dept", "degree", "gender", "reason"], as_index=False)
        [["new_leave", "on_leave_end"]].sum()
        .sort_values(["semester", "college", "dept", "degree", "gender", "reason"]))

mp = rd("dept_mapping.csv")
depts = [dict(dept=r.dept, college=r.college,
              aliases=[a.strip() for a in r.aliases.split(";") if a.strip()])
         for r in mp.itertuples()]

data = {
    "semesters": sorted(enr["semester"].unique()),
    "enrollment": {"columns": list(enr.columns), "rows": enr.values.tolist()},
    "leave": {"columns": list(lv.columns), "rows": lv.values.tolist()},
    "depts": depts,
}
out = ROOT / "docs" / "data.js"
out.write_text("window.DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=int) + ";\n",
               encoding="utf-8")

# 核對
n114 = int(enr.loc[enr.semester == "114-1", "count"].sum())
assert n114 == 10035, n114
assert enr["count"].sum() == int(rd("enrollment.csv")["count"].astype(int).sum())
assert lv["new_leave"].sum() == int(rd("leave.csv")["new_leave"].astype(int).sum())
print(f"114-1 在學人數合計 {n114}（OK）")
print(f"在學 {len(enr)} 列、休學 {len(lv)} 列、系所 {len(depts)} 個（{sum(bool(d['aliases']) for d in depts)} 個有舊名稱）")
print(f"{out}  {out.stat().st_size/1024:.1f} KB")
