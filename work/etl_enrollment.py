# /// script
# requires-python = ">=3.10"
# dependencies = ["xlrd"]
# ///
"""把 114-1 在學生人數統計表（.xls 第一個工作表）轉成整齊的 CSV。

用法：uv run work/etl_enrollment.py
"""
import csv
import glob
import re
import sys
from pathlib import Path

import xlrd

ROOT = Path(__file__).resolve().parent.parent
SRC = glob.glob(str(ROOT / "東華大學統計資料" / "在學人數統計表" / "114-1*.xls"))[0]
OUT = ROOT / "work" / "enrollment_114-1.csv"

# 欄位位置（0 起算）
C_PROGRAM, C_COLLEGE, C_DEPT, C_GROUP = 0, 1, 2, 3
C_FEMALE, C_MALE = 5, 6  # 「總計」底下的女、男

# 學制區段標題（col0）→ program_raw
PROGRAM_MARKERS = [("博士班", "博士班"), ("碩專班", "碩士在職專班"),
                   ("碩士班", "碩士班"), ("學士班", "學士班")]


def clean(v):
    return re.sub(r"\s+", " ", str(v)).strip() if v != "" else ""


def num(v):
    return 0 if v == "" else int(v)


def filled_grid(sheet):
    """回傳 text[r][c]，合併儲存格範圍內的空格以第一格的值填入。"""
    grid = [[clean(sheet.cell_value(r, c)) for c in range(sheet.ncols)] for r in range(sheet.nrows)]
    for rlo, rhi, clo, chi in sheet.merged_cells:
        top = grid[rlo][clo]
        for r in range(rlo, rhi):
            for c in range(clo, chi):
                grid[r][c] = top
    return grid


def main():
    # 這份 .xls 的字串是 Big5（cp950）編碼，xlrd 預設猜錯，必須指定
    wb = xlrd.open_workbook(SRC, encoding_override="cp950", formatting_info=True)
    sheet = wb.sheet_by_index(0)
    grid = filled_grid(sheet)

    rows, program, college, dept = [], None, "", ""
    totals = {}
    for r in range(sheet.nrows):
        c0 = grid[r][C_PROGRAM]
        if c0.startswith("備註"):
            break
        if "合計" in c0 or c0.startswith("總計"):
            # 合計列：記下區段小計供核對，並決定接下來的學制
            for marker, name in PROGRAM_MARKERS:
                if marker in c0:
                    program = name
                    totals[name] = num(sheet.cell_value(r, C_FEMALE)) + num(sheet.cell_value(r, C_MALE))
            continue
        if program is None or not isinstance(sheet.cell_value(r, C_FEMALE), float):
            continue
        # 學院、系所只寫在合併範圍第一格；合併展開後仍為空者沿用上一列
        college = grid[r][C_COLLEGE] or college
        if grid[r][C_DEPT]:
            dept = grid[r][C_DEPT]
        else:
            # 合併範圍少涵蓋一列（例如「應用物理博士班一般組」那一列落在合併範圍外）：
            # 該列實際屬於下一個有名稱的系所，往下取
            dept = next(grid[i][C_DEPT] for i in range(r + 1, sheet.nrows) if grid[i][C_DEPT])
            print(f"註：第 {r + 1} 列系所欄空白（合併範圍缺漏），歸入下一個系所「{dept}」")
        college_clean = re.sub(r"[（(].*?[)）]", "", college).strip()
        for gender, col in (("女", C_FEMALE), ("男", C_MALE)):
            rows.append(dict(college=college_clean, dept_raw=dept, program_raw=program,
                             gender=gender, count=num(sheet.cell_value(r, col))))

    # 同一系所、同一學制下的多個分組加總成一列
    agg = {}
    for x in rows:
        k = (x["college"], x["dept_raw"], x["program_raw"], x["gender"])
        agg[k] = agg.get(k, 0) + x["count"]
    out = [dict(college=k[0], dept_raw=k[1], program_raw=k[2], gender=k[3], count=v)
           for k, v in agg.items()]

    # 核對：各學制加總需等於報表的合計列
    for name, t in totals.items():
        s = sum(x["count"] for x in out if x["program_raw"] == name)
        print(f"{'OK ' if s == t else 'ERR'} {name}: 明細 {s} / 報表合計 {t}")

    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, ["college", "dept_raw", "program_raw", "gender", "count"])
        w.writeheader()
        w.writerows(out)
    print(f"{len(out)} 列 → {OUT}，總人數 {sum(x['count'] for x in out)}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
