<div align="center">

# ⏱️ content-velocity-tracker

### See how often your competitors publish and update content, straight from their sitemaps.

[![tests](https://github.com/marketing-MEER/content-velocity-tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/marketing-MEER/content-velocity-tracker/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![No API keys](https://img.shields.io/badge/API%20keys-none%20needed-brightgreen)
[![Part of SEO Toolbox](https://img.shields.io/badge/part%20of-SEO%20Toolbox-orange)](https://github.com/marketing-MEER/seo-toolbox)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Meer%20Hamza-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/meerhamza-seo)

[🚀 Quick start](#quick-start) · [⚙️ How it works](#how-it-works) · [📄 Report](#report) · [❓ FAQ](#faq) · [👤 Author](#author)

</div>

---

## 💡 What it does

"How often does that competitor refresh their content?" is usually answered by opening their blog and guessing. Their XML sitemap already holds the answer: every URL with a `<lastmod>` date.

`content-velocity-tracker` reads the sitemaps of as many sites as you like and shows each site's update rhythm month by month, which sections they keep fresh, which pages they have left alone for a year and, run to run, which URLs are new, updated or removed.

- ✅ An **update tier** per site (monthly, quarterly, occasional, rarely or never) matched to published survey tiers
- ✅ Month-by-month update counts, a section breakdown and a stale-page list
- ✅ Save a snapshot today, run `--compare` next month: new, updated and removed URLs
- ✅ Free, MIT licensed, no API keys. Reads sitemap URLs (indexes and `.gz` included) or local files

## 📊 Why this matters

> **How Often Teams Update Existing Content and How It Affects Revenue** · NP Digital, August 2026 (1,000 people surveyed)
> - 85 percent of respondents rarely or never update existing content.
> - Rarely or never updaters report 7 percent revenue growth over the prior 12 months.
> - Monthly updaters account for only 0.7 percent of respondents but report 21 percent revenue growth, the highest growth rate in the dataset.
> - Quarterly updaters account for 4 percent of respondents and report 17 percent revenue growth.
>
> **Updating vs Creating Content for SEO Growth** · NP Digital, November 2024 (846 marketers)
> - 91.3% of sites with traffic loss focused on new content.
> - 58.5% of sites with 41%+ growth focused on updating content.
>
> Data: [update frequency and revenue](https://neilpatel.com/marketing-stats/how-often-team-updates-existing-content/) · [updating vs creating](https://neilpatel.com/marketing-stats/updating-vs-creating-content/)

**How content-velocity-tracker uses this:** the survey groups teams by how often they update content, and its advice is to *"establish a quarterly content review cadence as a realistic minimum."* So each site gets the same tiers from its own lastmod dates, and the tier's reported revenue growth is shown next to it as context (a survey figure, not a prediction for that site). Because the second stat shows growing sites lean on updates, updates (lastmod changes) are counted separately from new URLs, and pages untouched for over a year are listed so you can see where a competitor has gone quiet.

<a id="quick-start"></a>

## 🚀 Quick start

```bash
git clone https://github.com/marketing-MEER/content-velocity-tracker.git
cd content-velocity-tracker
pip install -e .
content-velocity-tracker examples/brightcrm_sitemap.xml examples/pipelinehq_sitemap.xml examples/salesdeck_sitemap.xml --as-of 2026-10-15
```

On real sites, pass sitemap URLs and save a snapshot for next time:

```bash
content-velocity-tracker https://competitor-a.com/sitemap.xml https://competitor-b.com/sitemap_index.xml --snapshot snap_oct.csv
# a month later
content-velocity-tracker https://competitor-a.com/sitemap.xml https://competitor-b.com/sitemap_index.xml --compare snap_oct.csv --snapshot snap_nov.csv
```

This writes **`content_velocity.html`** (a formatted report you can share or print to PDF) and **`content_velocity.xlsx`** (all data, one sheet per section).

> [!TIP]
> If the `content-velocity-tracker` command isn't found, use `python -m content_velocity_tracker`.

## 📥 Input

| Input | Notes |
|---|---|
| Sitemap URL | `https://site.com/sitemap.xml`; sitemap indexes and `.xml.gz` files are followed (up to 200 child sitemaps) |
| Local sitemap file | Same formats, saved to disk |
| Snapshot CSV (optional) | Written by `--snapshot` on an earlier run: `site`, `url`, `lastmod` |

Sites are grouped by domain, so one site can have several sitemaps.

<a id="how-it-works"></a>

## ⚙️ How it works

1. **Fetch politely**: own user agent, robots.txt checked, 0.5 s between requests. Only the sitemap files are downloaded, never the pages.
2. **Read** every `<loc>` and `<lastmod>`, following sitemap indexes.
3. **Age** each URL from `--as-of` (default today) and bucket it: last 30 days, 31-90 days, 91-365 days, stale (1y+), no lastmod.
4. **Update tier** per site from the last 12 months of lastmod dates:

| Tier | Rule | Survey revenue growth |
|---|---|---|
| **monthly** | Updates in 10 or more of the last 12 months | 21% |
| **quarterly** | At least one update in each of the last four quarters | 17% |
| **occasional** | Some update in the last year, but not every quarter | no survey tier |
| **rarely or never** | No update in the last year | 7% |

5. **Sections**: URLs grouped by first folder (`/blog/`, `/features/`, ...).
6. **Compare** (optional): new URLs, URLs whose lastmod changed, and URLs that left the sitemap.

### Options

| Option | Default | What it does |
|---|---|---|
| `--as-of` | today | Date to measure ages from (YYYY-MM-DD) |
| `--compare` | none | Snapshot CSV from an earlier run |
| `--snapshot` | none | Save this run's URLs and lastmod dates |
| `-o`, `--output` | `content_velocity` | Report name; writes `.html` and `.xlsx` |

<a id="report"></a>

## 📄 The report

| Section / Excel sheet | Shows |
|---|---|
| Summary cards | URLs, updated in 90 days, stale, missing lastmod, freshest site |
| Benchmark panels | The two Neil Patel stats behind the tiers |
| **Summary** | Per site: URLs, % with lastmod, updated in 30/90 days, % stale, median age, active months, tier |
| **By month** | URLs updated per month per site, last 12 months |
| **Sections** | Per site and folder: URLs, updated in 90 days, stale, median age |
| **Changes** | With `--compare`: new, updated and removed URLs |
| **Stale** | URLs with no update for over a year |
| **All URLs** | Everything, with age and freshness bucket |

<details>
<summary>📄 Example: real output from <code>examples/</code> (fictional CRM sites)</summary>

**Summary**

| site | urls | with lastmod pct | updated 30d | updated 90d | updated 90d pct | stale 1y pct | median days since update | active months of 12 | update tier | np tier revenue growth |
|---|---|---|---|---|---|---|---|---|---|---|
| brightcrm.io | 60 | 96.7 | 12 | 12 | 20 | 36.7 | 233 | 4 | quarterly | 17% |
| pipelinehq.com | 86 | 95.3 | 15 | 34 | 39.5 | 24.4 | 144 | 12 | monthly | 21% |
| salesdeck.io | 45 | 93.3 | 0 | 0 | 0 | 91.1 | 731 | 1 | occasional | no survey tier |

**Changes since the snapshot of 2026-09-15** (counts from the Changes sheet):

| site | new | removed | updated |
|---|---|---|---|
| brightcrm.io | 8 | 1 | 4 |
| pipelinehq.com | 8 | 1 | 7 |
| salesdeck.io | 0 | 1 | 0 |

**Sections of pipelinehq.com.** The blog carries the update work:

| site | section | urls | updated 90d | stale 1y | median days since update |
|---|---|---|---|---|---|
| pipelinehq.com | /blog/ | 70 | 29 | 20 | 116 |
| pipelinehq.com | /features/ | 12 | 3 | 1 | 155 |
| pipelinehq.com | / (root pages) | 3 | 1 | 0 | 183 |
| pipelinehq.com | / (home) | 1 | 1 | 0 | 4 |

</details>

## 🧰 More free SEO tools

This repo is one tool in the **[SEO Toolbox](https://github.com/marketing-MEER/seo-toolbox)**, a family of free, single-purpose SEO tools. Related:
- [content-gap-crawler](https://github.com/marketing-MEER/content-gap-crawler): topics your competitors cover and you don't
- [competitor-page-type-mix](https://github.com/marketing-MEER/competitor-page-type-mix): which page types bring competitors their traffic
- [seo-workhorse](https://github.com/marketing-MEER/seo-workhorse): audit, clustering, redirects and GSC quick wins in one CLI

<a id="faq"></a>

## ❓ FAQ

<details><summary><b>Can I trust lastmod?</b></summary>

Mostly, but check. Some CMSs stamp every URL with the deploy date, which makes a site look like it updates everything daily. If one month shows nearly all URLs updated at once, open a few of them and see whether anything really changed.
</details>

<details><summary><b>The site has no lastmod at all. Is the tool useless?</b></summary>

Not quite. The age columns stay empty, but `--snapshot` and `--compare` still show new and removed URLs between runs, which is the publishing side of velocity.
</details>

<details><summary><b>Does it crawl the competitor's pages?</b></summary>

No. It downloads only the sitemap files, checks robots.txt first, and waits 0.5 s between requests.
</details>

<details><summary><b>How often should I run it?</b></summary>

Monthly is enough for most markets. Keep each snapshot CSV so `--compare` can show the month's changes.
</details>

## 🧪 Tests

```bash
python -m unittest discover -s tests -t . -v
```

## 📄 License

[MIT](LICENSE). Free for personal and commercial use. Benchmark figures © their original publishers, quoted with a link to the source.

<a id="author"></a>

## 👤 Author

**Meer Hamza** · SEO Team Lead · Berlin 🇩🇪
10+ years in SEO, AEO and GEO. I build small tools that take the spreadsheet work out of SEO.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/meerhamza-seo)
[![Email](https://img.shields.io/badge/Email-meerhamza5%40gmail.com-D14836?logo=gmail&logoColor=white)](mailto:meerhamza5@gmail.com)

<div align="center">

**If this saved you time, a ⭐ helps other SEOs find it.**

</div>
