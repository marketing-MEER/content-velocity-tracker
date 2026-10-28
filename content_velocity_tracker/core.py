"""Publishing and update rhythm of competitor sites, read from their XML sitemaps.

Each sitemap's <lastmod> dates are grouped by month and by site section, and every
site gets an update tier (monthly, quarterly, occasional, rarely or never) that
matches the tiers in NP Digital's content-update survey. Saved snapshots can be
compared run to run to see new, updated and removed URLs.
"""
import gzip
import io
import re
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib import robotparser
from urllib.parse import urlparse

import pandas as pd
import requests

USER_AGENT = "content-velocity-tracker/1.0 (+https://github.com/marketing-MEER/content-velocity-tracker)"
DELAY = 0.5          # seconds between requests to the same site
MAX_SITEMAPS = 200   # child sitemaps followed per input, a safety cap

# Update tiers and the revenue growth each tier reported in the NP Digital survey
# (1,000 respondents, August 2026): monthly 21%, quarterly 17%, rarely or never 7%.
# Source: https://neilpatel.com/marketing-stats/how-often-team-updates-existing-content/
TIER_GROWTH = {"monthly": "21%", "quarterly": "17%", "occasional": "no survey tier", "rarely or never": "7%"}
TIER_ORDER = list(TIER_GROWTH)

# "Refresh pages that already rank" (updating-vs-creating-content): pages untouched for
# a year are flagged as stale; 90 days is the quarterly review cadence the survey recommends.
STALE_DAYS = 365
QUARTER_DAYS = 90


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _read(source: str, session: requests.Session | None) -> bytes:
    if re.match(r"https?://", source):
        if session is None:
            raise ValueError("network source needs a session")
        if not robots_allows(source, session):
            raise PermissionError(f"robots.txt disallows {source}")
        resp = session.get(source, timeout=20)
        resp.raise_for_status()
        time.sleep(DELAY)
        data = resp.content
    else:
        data = Path(source).read_bytes()
    if data[:2] == b"\x1f\x8b":
        data = gzip.GzipFile(fileobj=io.BytesIO(data)).read()
    return data


_robots_cache: dict[str, robotparser.RobotFileParser | None] = {}


def robots_allows(url: str, session: requests.Session) -> bool:
    parts = urlparse(url)
    root = f"{parts.scheme}://{parts.netloc}"
    if root not in _robots_cache:
        parser = robotparser.RobotFileParser()
        try:
            resp = session.get(root + "/robots.txt", timeout=10)
            parser.parse(resp.text.splitlines() if resp.status_code == 200 else [])
        except requests.RequestException:
            parser.parse([])
        _robots_cache[root] = parser
    return _robots_cache[root].can_fetch(USER_AGENT, url)


def parse_lastmod(text: str | None) -> date | None:
    if not text:
        return None
    text = text.strip()
    for fmt, size in (("%Y-%m-%d", 10), ("%Y-%m", 7), ("%Y", 4)):
        try:
            return datetime.strptime(text[:size], fmt).date()
        except ValueError:
            continue
    return None


def read_sitemap(source: str, session: requests.Session | None = None) -> list[tuple[str, date | None]]:
    """All (url, lastmod) pairs of a sitemap or sitemap index, following child sitemaps."""
    queue, seen, rows = [source], set(), []
    while queue and len(seen) < MAX_SITEMAPS:
        current = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        root = ET.fromstring(_read(current, session))
        kind = _local(root.tag)
        for item in root:
            fields = {_local(child.tag): (child.text or "").strip() for child in item}
            loc = fields.get("loc")
            if not loc:
                continue
            if kind == "sitemapindex":
                queue.append(loc)
            else:
                rows.append((loc, parse_lastmod(fields.get("lastmod"))))
    return rows


def site_of(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def section_of(url: str) -> str:
    path = urlparse(url).path.strip("/")
    first = path.split("/", 1)[0] if path else ""
    if not first:
        return "/ (home)"
    if "/" not in path:
        return "/ (root pages)"
    return f"/{first}/"


def load(sources, session: requests.Session | None = None) -> pd.DataFrame:
    frames = []
    for source in sources:
        pairs = read_sitemap(str(source), session)
        df = pd.DataFrame(pairs, columns=["url", "lastmod"])
        frames.append(df)
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["url", "lastmod"])
    df = df.drop_duplicates("url")
    df["site"] = df["url"].map(site_of)
    df["section"] = df["url"].map(section_of)
    return df[["site", "section", "url", "lastmod"]].reset_index(drop=True)


def add_age(df: pd.DataFrame, as_of: date) -> pd.DataFrame:
    df = df.copy()
    df["days_since_update"] = df["lastmod"].map(lambda d: (as_of - d).days if d else None)
    df["freshness"] = df["days_since_update"].map(freshness)
    return df


def freshness(days) -> str:
    if days is None or pd.isna(days):
        return "no lastmod"
    if days < 0:
        return "future date"
    if days <= 30:
        return "last 30 days"
    if days <= QUARTER_DAYS:
        return "31-90 days"
    if days <= STALE_DAYS:
        return "91-365 days"
    return "stale (1y+)"


def month_keys(as_of: date, months: int = 12) -> list[str]:
    keys, y, m = [], as_of.year, as_of.month
    for _ in range(months):
        keys.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return keys[::-1]


def update_tier(dates, as_of: date) -> str:
    """Tier from the last 12 months of lastmod dates.

    monthly = changes in 10+ of the last 12 months; quarterly = changes in each of the
    last four 3-month blocks; occasional = some change in the last year; else rarely or never.
    """
    months = set(month_keys(as_of))
    active = {f"{d.year:04d}-{d.month:02d}" for d in dates if d} & months
    if len(active) >= 10:
        return "monthly"
    blocks = [as_of - timedelta(days=91 * i) for i in range(5)]
    if all(any(blocks[i + 1] < d <= blocks[i] for d in dates if d) for i in range(4)):
        return "quarterly"
    if active:
        return "occasional"
    return "rarely or never"


def site_summary(df: pd.DataFrame, as_of: date) -> pd.DataFrame:
    rows = []
    for site, g in df.groupby("site", sort=False):
        dated = g["lastmod"].dropna()
        days = g["days_since_update"].dropna()
        tier = update_tier(list(dated), as_of)
        n = len(g)
        rows.append({
            "site": site,
            "urls": n,
            "with_lastmod_pct": round(len(dated) / n * 100, 1) if n else 0,
            "updated_30d": int((days <= 30).sum()),
            "updated_90d": int((days <= QUARTER_DAYS).sum()),
            "updated_90d_pct": round((days <= QUARTER_DAYS).sum() / n * 100, 1) if n else 0,
            "stale_1y_pct": round((days > STALE_DAYS).sum() / n * 100, 1) if n else 0,
            "median_days_since_update": int(days.median()) if len(days) else None,
            "active_months_of_12": len({f"{d.year:04d}-{d.month:02d}" for d in dated} & set(month_keys(as_of))),
            "update_tier": tier,
            "np_tier_revenue_growth": TIER_GROWTH[tier],
        })
    cols = ["site", "urls", "with_lastmod_pct", "updated_30d", "updated_90d", "updated_90d_pct", "stale_1y_pct",
            "median_days_since_update", "active_months_of_12", "update_tier", "np_tier_revenue_growth"]
    return pd.DataFrame(rows, columns=cols)


def monthly(df: pd.DataFrame, as_of: date) -> pd.DataFrame:
    """URLs per site whose lastmod falls in each of the last 12 months."""
    keys = month_keys(as_of)
    dated = df.dropna(subset=["lastmod"]).copy()
    dated["month"] = dated["lastmod"].map(lambda d: f"{d.year:04d}-{d.month:02d}")
    sites = list(dict.fromkeys(df["site"]))
    table = dated.groupby(["month", "site"]).size().unstack(fill_value=0)
    table = table.reindex(index=keys, columns=sites, fill_value=0)
    return table.reset_index().rename(columns={"index": "month"})


def sections(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (site, section), g in df.groupby(["site", "section"], sort=False):
        days = g["days_since_update"].dropna()
        rows.append({"site": site, "section": section, "urls": len(g),
                     "updated_90d": int((days <= QUARTER_DAYS).sum()),
                     "stale_1y": int((days > STALE_DAYS).sum()),
                     "median_days_since_update": int(days.median()) if len(days) else None})
    out = pd.DataFrame(rows, columns=["site", "section", "urls", "updated_90d", "stale_1y",
                                      "median_days_since_update"])
    return out.sort_values(["site", "urls"], ascending=[True, False]).reset_index(drop=True)


def compare(current: pd.DataFrame, previous_csv) -> pd.DataFrame:
    """New, updated and removed URLs against a snapshot saved by an earlier run."""
    old = pd.read_csv(previous_csv, dtype=str).fillna("")
    old_map = dict(zip(old["url"], old["lastmod"]))
    now_map = {u: (d.isoformat() if d else "") for u, d in zip(current["url"], current["lastmod"])}
    site_map = dict(zip(current["url"], current["site"]))
    rows = []
    for url, lm in now_map.items():
        if url not in old_map:
            rows.append({"site": site_map[url], "change": "new", "url": url, "old_lastmod": "", "lastmod": lm})
        elif lm and lm != old_map[url]:
            rows.append({"site": site_map[url], "change": "updated", "url": url,
                         "old_lastmod": old_map[url], "lastmod": lm})
    old_sites = dict(zip(old["url"], old["site"])) if "site" in old else {}
    for url, lm in old_map.items():
        if url not in now_map:
            rows.append({"site": old_sites.get(url, site_of(url)), "change": "removed", "url": url,
                         "old_lastmod": lm, "lastmod": ""})
    out = pd.DataFrame(rows, columns=["site", "change", "url", "old_lastmod", "lastmod"])
    return out.sort_values(["site", "change", "url"]).reset_index(drop=True)


def snapshot(df: pd.DataFrame) -> pd.DataFrame:
    out = df[["site", "url", "lastmod"]].copy()
    out["lastmod"] = out["lastmod"].map(lambda d: d.isoformat() if d else "")
    return out
