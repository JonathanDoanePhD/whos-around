"""Who's Around: how much time do teens spend with adults outside their family, by family income?

American Time Use Survey 2003-2023, respondents aged 15-17 (one diary day each).
"Who was present" is recorded for each activity except sleeping, grooming and private
activities. Time with a group counts if anyone in that group was present.

Groups (ATUS TUWHO_CODE):
  nonfamily adults  55 coworkers/clients, 56 neighbors/acquaintances, 58 other non-household
                    adults (teachers, coaches, mentors...), 59 boss, 60 people supervised,
                    61 coworkers, 62 customers
  extended-family adults  51 parents not in household, 53 other non-household family 18+
  household parent  24     alone  18, 19
Screen time: activity codes 120303-120308 (TV, games, leisure computer use).
Note: "who was present" is mostly left blank during class time (ATUS codes it -1), so time
with teachers in class is undercounted. The headline measure is therefore time with
non-family adults OUTSIDE school and work, which is fully recorded.

Income: family income category (HEFAMINC) ranked within each survey year among teen
respondents, split into thirds (low / middle / high). Weights: TUFNWGTP (TU20FWGT in 2020).
Standard errors: robust (weights only; ATUS replicate weights not used), so intervals are
somewhat narrow.

Run: python3 -I scripts/01_whos_around.py  ->  output/
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "atus"
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

NONFAM = {55, 56, 58, 59, 60, 61, 62}
EXTFAM = {51, 53}

# ---------------- Respondents ----------------
resp = pd.read_csv(RAW / "atusresp_0323.dat", usecols=["TUCASEID", "TUYEAR", "TUDIARYDAY", "TRHOLIDAY",
                                                        "TUFNWGTP", "TU20FWGT", "TESCHENR", "TESCHLVL"])
rost = pd.read_csv(RAW / "atusrost_0323.dat", usecols=["TUCASEID", "TULINENO", "TEAGE", "TESEX"])
rost = rost[rost.TULINENO == 1]
cps = pd.read_csv(RAW / "atuscps_0323.dat", usecols=["TUCASEID", "TULINENO", "HEFAMINC", "HUFAMINC"])
cps = cps[cps.TULINENO == 1]
# Family income is HUFAMINC before 2010 and HEFAMINC from 2010 (both 16 ordered categories)
cps["HEFAMINC"] = cps.HEFAMINC.where(cps.HEFAMINC > 0, cps.HUFAMINC)
r = resp.merge(rost, on="TUCASEID").merge(cps[["TUCASEID", "HEFAMINC"]], on="TUCASEID", how="left")
r = r[r.TEAGE.between(15, 17)].copy()
r["w"] = np.where(r.TUYEAR == 2020, r.TU20FWGT, r.TUFNWGTP)
r = r[(r.w > 0) & (r.HEFAMINC > 0)]
r["female"] = (r.TESEX == 2).astype(float)
r["weekend"] = r.TUDIARYDAY.isin([1, 7]) | (r.TRHOLIDAY == 1)
r["enrolled"] = r.TESCHENR == 1


def within_year_thirds(g):
    order = g.sort_values("HEFAMINC")
    cw = order.w.cumsum() - order.w / 2
    # midrank for ties so equal income categories share a percentile
    pr = (cw / order.w.sum()).groupby(order.HEFAMINC).transform("mean")
    return pd.cut(pr, [0, 1 / 3, 2 / 3, 1.0001], labels=["Low", "Middle", "High"]).reindex(g.index)


r["income"] = r.groupby("TUYEAR", group_keys=False).apply(within_year_thirds, include_groups=False)

# ---------------- Activities and who ----------------
act = pd.read_csv(RAW / "atusact_0323.dat", usecols=["TUCASEID", "TUACTIVITY_N", "TUACTDUR24", "TRCODEP"])
act = act[act.TUCASEID.isin(r.TUCASEID)]
who = pd.read_csv(RAW / "atuswho_0323.dat", usecols=["TUCASEID", "TUACTIVITY_N", "TUWHO_CODE"])
who = who[who.TUCASEID.isin(r.TUCASEID)]
flags = who.assign(nonfam=who.TUWHO_CODE.isin(NONFAM), extfam=who.TUWHO_CODE.isin(EXTFAM),
                   parent=who.TUWHO_CODE == 24, alone=who.TUWHO_CODE.isin([18, 19])) \
    .groupby(["TUCASEID", "TUACTIVITY_N"])[["nonfam", "extfam", "parent", "alone"]].max().reset_index()
a = act.merge(flags, on=["TUCASEID", "TUACTIVITY_N"], how="left").fillna({"nonfam": False, "extfam": False,
                                                                          "parent": False, "alone": False})
a["screen"] = a.TRCODEP.between(120303, 120308)
a["tier1"] = a.TRCODEP // 10000
a["tier2"] = a.TRCODEP // 100
CONTEXT = {  # where time with non-family adults happens
    "Class & school activities": lambda t2: t2 in (601, 603),
    "Paid work": lambda t2: t2 // 100 == 5,
    "Sports & exercise": lambda t2: t2 // 100 == 13,
    "Religious": lambda t2: t2 // 100 == 14,
    "Volunteering": lambda t2: t2 // 100 == 15,
    "Shopping & services": lambda t2: t2 // 100 in (7, 8, 9, 10),
}
a["context"] = "Other"
for name, fn in CONTEXT.items():
    a.loc[a.tier2.map(fn).astype(bool), "context"] = name

mins = pd.DataFrame({
    "nonfam_adults": a[a.nonfam].groupby("TUCASEID").TUACTDUR24.sum(),
    "extfam_adults": a[a.extfam].groupby("TUCASEID").TUACTDUR24.sum(),
    "with_parent": a[a.parent].groupby("TUCASEID").TUACTDUR24.sum(),
    "alone": a[a.alone].groupby("TUCASEID").TUACTDUR24.sum(),
    "screen": a[a.screen].groupby("TUCASEID").TUACTDUR24.sum(),
    "nonfam_outside_school_work": a[a.nonfam & ~a.context.isin(["Class & school activities", "Paid work"])].groupby("TUCASEID").TUACTDUR24.sum(),
})
r = r.merge(mins, left_on="TUCASEID", right_index=True, how="left")
MEAS = list(mins.columns)
r[MEAS] = r[MEAS].fillna(0)
r["any_nonfam"] = (r.nonfam_adults > 0).astype(float)
LAB = {"nonfam_adults": "With non-family adults outside the home", "extfam_adults": "With extended-family adults",
       "with_parent": "With a parent at home", "alone": "Alone", "screen": "Screens (TV, games, leisure computer)",
       "nonfam_outside_school_work": "With non-family adults, outside school and work",
       "any_nonfam": "Share of days with any time with non-family adults"}


def wmean_ci(x, w):
    m = np.average(x, weights=w)
    neff = w.sum() ** 2 / (w ** 2).sum()
    se = np.sqrt(np.average((x - m) ** 2, weights=w) / neff)
    return m, m - 1.96 * se, m + 1.96 * se, len(x)


# ---------------- 1. Daily minutes by income ----------------
rows = []
for day, sel in [("All days", r.index == r.index), ("School-year weekdays (enrolled)", r.enrolled & ~r.weekend & ~r.TUDIARYDAY.isna()),
                 ("Weekends & holidays", r.weekend)]:
    s = r[sel]
    for inc in ["Low", "Middle", "High"]:
        g = s[s.income == inc]
        for m in MEAS + ["any_nonfam"]:
            mu, lo, hi, n = wmean_ci(g[m], g.w)
            rows.append({"days": day, "income": inc, "measure": m, "label": LAB[m], "mean": mu, "low": lo, "high": hi, "n": n})
by_inc = pd.DataFrame(rows)
by_inc.to_csv(OUT / "minutes_by_income.csv", index=False, float_format="%.3f")

# ---------------- 2. Adjusted gap (low vs high income) ----------------
gap_rows = []
X0 = pd.concat([pd.get_dummies(r.income, prefix="inc", dtype=float).drop(columns="inc_High"),
                pd.get_dummies(r.TEAGE, prefix="age", drop_first=True, dtype=float), r[["female"]],
                r.weekend.astype(float).rename("weekend"), pd.get_dummies(r.TUYEAR, prefix="yr", drop_first=True, dtype=float)], axis=1)
for m in MEAS + ["any_nonfam"]:
    fit = sm.WLS(r[m], sm.add_constant(X0), weights=r.w).fit(cov_type="HC1")
    for k in ["inc_Low", "inc_Middle"]:
        gap_rows.append({"measure": m, "label": LAB[m], "term": k.replace("inc_", "") + " vs high income",
                         "diff_minutes": fit.params[k], "low": fit.conf_int().loc[k, 0], "high": fit.conf_int().loc[k, 1]})
gap = pd.DataFrame(gap_rows)
gap.to_csv(OUT / "income_gaps_adjusted.csv", index=False, float_format="%.3f")

# ---------------- 3. Where time with non-family adults happens ----------------
ctx = a[a.nonfam].merge(r[["TUCASEID", "income", "w"]], on="TUCASEID")
ctx_tot = ctx.groupby(["income", "context"], observed=True).apply(
    lambda g: (g.TUACTDUR24 * g.w).sum(), include_groups=False).rename("wmin").reset_index()
denom = r.groupby("income", observed=True).w.sum()
ctx_tot["minutes_per_day"] = ctx_tot.wmin / ctx_tot.income.map(denom).astype(float)
ctx_tot = ctx_tot.drop(columns="wmin")
ctx_tot.to_csv(OUT / "nonfamily_adult_time_by_context.csv", index=False, float_format="%.2f")

# ---------------- 4. Trends ----------------
r["period"] = pd.cut(r.TUYEAR, [2002, 2007, 2012, 2017, 2019, 2023],
                     labels=["2003-07", "2008-12", "2013-17", "2018-19", "2020-23"])
tr = []
for (p, inc), g in r.groupby(["period", "income"], observed=True):
    for m in ["nonfam_adults", "nonfam_outside_school_work", "alone", "screen"]:
        mu, lo, hi, n = wmean_ci(g[m], g.w)
        tr.append({"period": p, "income": inc, "measure": m, "label": LAB[m], "mean": mu, "low": lo, "high": hi, "n": n})
tr = pd.DataFrame(tr)
tr.to_csv(OUT / "trends.csv", index=False, float_format="%.3f")

# ---------------- Figures ----------------
SURFACE, TEXT, TEXT2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
INC_COL = {"Low": "#eb6834", "Middle": "#1baf7a", "High": "#2a78d6"}
fig, axes = plt.subplots(1, 2, figsize=(13, 5.6), dpi=100, gridspec_kw={"width_ratios": [1.15, 1]})
fig.patch.set_facecolor(SURFACE)
ax = axes[0]; ax.set_facecolor(SURFACE)
days = ["School-year weekdays (enrolled)", "Weekends & holidays"]
meas = ["nonfam_adults", "nonfam_outside_school_work"]
xs = np.arange(len(days) * len(meas))
labels = []
for j, (d_, m) in enumerate([(d_, m) for m in meas for d_ in days]):
    for k, inc in enumerate(["Low", "Middle", "High"]):
        row = by_inc[(by_inc.days == d_) & (by_inc.measure == m) & (by_inc.income == inc)].iloc[0]
        x = j + (k - 1) * 0.26
        ax.bar(x, row["mean"], width=0.24, color=INC_COL[inc], label=f"{inc} income" if j == 0 else None)
        ax.errorbar(x, row["mean"], yerr=[[row["mean"] - row.low], [row.high - row["mean"]]], color=TEXT2, lw=1.2, capsize=0)
    labels.append(("All settings" if m == "nonfam_adults" else "Outside school/work") + "\n" + ("school days" if "weekdays" in d_ else "weekends"))
ax.set_xticks(xs, labels, fontsize=9.5)
ax.set_ylabel("Minutes per day", color=TEXT2)
ax.set_title("Time with non-family adults outside the home", loc="left", color=TEXT, fontsize=12)
ax.legend(frameon=False, labelcolor=TEXT)
ax2 = axes[1]; ax2.set_facecolor(SURFACE)
periods = ["2003-07", "2008-12", "2013-17", "2018-19", "2020-23"]
for inc in ["Low", "High"]:
    s = tr[(tr.measure == "nonfam_outside_school_work") & (tr.income == inc)].set_index("period").reindex(periods)
    ax2.plot(range(5), s["mean"], color=INC_COL[inc], lw=2, marker="o", label=f"{inc} income")
    ax2.fill_between(range(5), s.low, s.high, color=INC_COL[inc], alpha=0.15, lw=0)
ax2.set_xticks(range(5), periods)
ax2.set_ylabel("Minutes per day", color=TEXT2)
ax2.set_title("Outside school & work, over time (wide intervals)", loc="left", color=TEXT, fontsize=12)
ax2.legend(frameon=False, labelcolor=TEXT)
for a_ in axes:
    a_.grid(axis="y", color=GRID, lw=0.6); a_.set_axisbelow(True)
    for s_ in ["top", "right"]:
        a_.spines[s_].set_visible(False)
    a_.tick_params(colors=TEXT2)
fig.text(0.02, 0.955, "Lower-income teens spend less time with adults outside their family, especially outside school",
         fontsize=13.5, weight="bold", color=TEXT)
fig.text(0.02, 0.012, f"American Time Use Survey 2003-2023, teens 15-17 (n = {len(r):,} diary days), weighted. Income = within-year thirds of family income. "
         "Exploratory - verify before external use.", fontsize=8.5, color=TEXT2)
fig.subplots_adjust(left=0.06, right=0.98, top=0.86, bottom=0.17, wspace=0.18)
fig.savefig(OUT / "time_with_adults.png", dpi=150, facecolor=SURFACE)

pd.set_option("display.width", 200)
print(f"Teen diary days: {len(r):,}; by income: {r.income.value_counts().to_dict()}")
pv = by_inc[by_inc.days == "All days"].pivot(index="label", columns="income", values="mean")[["Low", "Middle", "High"]]
print(pv.round(1).to_string())
print(by_inc[(by_inc.measure.isin(["nonfam_adults", "nonfam_outside_school_work"])) & (by_inc.days != "All days")]
      .pivot_table(index=["days", "label"], columns="income", values="mean")[["Low", "Middle", "High"]].round(1).to_string())
print(gap.round(1).to_string(index=False))
print(ctx_tot.pivot(index="context", columns="income", values="minutes_per_day")[["Low", "Middle", "High"]].round(1).to_string())
print(tr[tr.measure == "nonfam_outside_school_work"].pivot(index="period", columns="income", values="mean").round(1).to_string())
print(tr[tr.measure == "screen"].pivot(index="period", columns="income", values="mean").round(0).to_string())
