# 05 - Who's Around

**Question:** How much time do teens actually spend with adults outside their family, the
people who could become mentors, and does it differ by family income? This measures the
"access gap" from Project 02 (P1) in minutes per day rather than survey answers.

**Status:** complete (2026-11-14). All data public domain (BLS).

> **Exploratory.** Associations from diary data, not causal effects. Verify figures against
> the original sources before external use.

## Key findings

American Time Use Survey 2003-2023: **8,961 diary days from teens aged 15-17**, weighted.
Family income splits into thirds within each year. Gaps compare low- vs. high-income teens,
adjusted for age, sex, weekend and year.

1. **Lower-income teens spend less time with non-family adults outside the home:** 69 vs. 83
   minutes per day; adjusted gap **-13 minutes** (CI -22 to -4). **Outside school and work**
   (where the data are complete and mentoring would add time), it's 47 vs. 55 minutes, an
   adjusted gap of **-8 minutes a day** (CI -15 to -1), about **50 hours a year**.
2. **One hour a week of mentoring is about the size of that gap.** 8 minutes a day is roughly
   an hour a week, the typical dose of a community mentoring program. That's a concrete way
   to describe what a match adds.
3. **Family ties substitute for bridging ties.** Lower-income teens spend **more** time with
   extended-family adults (+9 minutes, CI +2 to +15), and less with parents at home (-20) and
   alone (-17). Their adult networks are more *bonding* (family) and less *bridging*
   (teachers, coaches, employers, neighbors), the distinction behind Projects 01-02.
4. **Screens fill the gap:** **+31 minutes a day** of TV, games and leisure computer use
   (CI +19 to +42).
5. **Where the adult time comes from:** higher-income teens get more of it through **sports**
   (15 vs. 10 minutes), **volunteering** (5 vs. 3) and paid work. Structured activities are
   the main settings where teens meet non-family adults, which matches Project 02's NSCH
   finding that activities explain about a third of the mentor gap.
6. **Possibly widening since 2020** (uncertain): outside school and work, low-income teens'
   time with non-family adults fell to about 28 minutes a day in 2020-23, against 52 for
   high-income teens. Samples per period are small and the intervals overlap, so this needs
   confirming with future years.

## Outputs

| File | What |
|---|---|
| `output/minutes_by_income.csv` | Daily minutes by income third: all days, school-year weekdays, weekends; with CIs |
| `output/income_gaps_adjusted.csv` | Adjusted low- and middle- vs. high-income differences |
| `output/nonfamily_adult_time_by_context.csv` | Minutes with non-family adults by activity (class, work, sports, religious, volunteering...) |
| `output/trends.csv` | Five periods, 2003-2023 |
| `output/time_with_adults.png` | Figure |

## Rebuild

```bash
python3 -I scripts/fetch_data.py .
python3 -I scripts/01_whos_around.py   # ~10 seconds
```

## Method

- **Sample:** ATUS respondents aged 15-17 (roster line 1), positive weight, known family income.
- **Weights:** `TUFNWGTP` (`TU20FWGT` for 2020), which already balance days of the week.
- **Who was present:** an activity counts toward a group if anyone from it was present.
  Non-family adults = codes 55-62 (coworkers, neighbors/acquaintances, other non-household
  adults, boss, customers...). Extended family = 51, 53. "Who" isn't collected for sleep,
  grooming and private activities, and is mostly blank during class, so in-class time with
  teachers is undercounted. Hence the headline "outside school and work" measure.
- **Income:** `HUFAMINC` (2003-2009) / `HEFAMINC` (2010-2023), ranked within year (midranks
  for ties).
- **Uncertainty:** robust standard errors with weights only; ATUS replicate weights would give
  somewhat wider intervals.

## Caveats

- One diary day per teen, so day-to-day variation is large; averages are reliable, individual
  days are not.
- "Other non-household adults" mixes teachers, coaches, mentors, clergy and strangers in
  public places; ATUS can't separate them.
- Teens aged 15-17 only; younger children are not interviewed.

## License, citation and data terms

- **Code:** MIT (see `LICENSE`). **Outputs:** CC BY 4.0, subject to the source terms below.
- **Cite this project as:** JonathanDoanePhD (2026). *Who's Around*. https://github.com/JonathanDoanePhD/whos-around
- **Data sources and terms** (from `data/sources.csv`; recorded versions and checksums in `data/sources.lock.csv`):

| Source | Terms |
|---|---|
| BLS American Time Use Survey 2003-2023 respondent file | U.S. government work (public domain) |
| ATUS 2003-2023 activity file | U.S. government work (public domain) |
| ATUS 2003-2023 who-was-present file | U.S. government work (public domain) |
| ATUS 2003-2023 CPS file (family income) | U.S. government work (public domain) |
| ATUS 2003-2023 household roster | U.S. government work (public domain) |

Built with AI assistance (Claude). Exploratory research: every statistic needs checking against its original source
before it appears in funder reports, grant applications or public material.

## Status and limitations

Published 2026-11-26 as exploratory research. The analysis is complete and reproducible, but these checks have **not yet been done**, so treat figures as provisional:

- Statistics in this README and in `output/` have not been independently checked against their original sources.
- bls.gov blocked downloads from the development environment on 2026-11-25; confirm the ATUS files still download for a clean rebuild.
