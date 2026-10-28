"""Command line entry point: `content-velocity-tracker SITEMAP [SITEMAP ...]`."""
from datetime import date
from pathlib import Path

import click
import requests

from . import __version__, core
from .benchmark import STATS
from .report import Report, write_excel


@click.command()
@click.argument("sitemaps", nargs=-1, required=True)
@click.option("--as-of", default=None, help="Date to measure ages from (YYYY-MM-DD). Default: today.")
@click.option("--compare", "previous", type=click.Path(exists=True), default=None,
              help="Snapshot CSV from an earlier run: list new, updated and removed URLs.")
@click.option("--snapshot", "snapshot_path", default=None,
              help="Save this run's URLs + lastmod to a CSV for the next --compare.")
@click.option("-o", "--output", default="content_velocity", show_default=True,
              help="Report name; writes <name>.html and <name>.xlsx")
@click.version_option(__version__)
def main(sitemaps, as_of, previous, snapshot_path, output):
    """Read the XML SITEMAPS (URLs or files, one per site, indexes are followed) and show how often each site
    publishes and updates content.

    Built by Meer Hamza - linkedin.com/in/meerhamza-seo
    """
    day = date.fromisoformat(as_of) if as_of else date.today()
    session = requests.Session()
    session.headers["User-Agent"] = core.USER_AGENT
    df = core.add_age(core.load(sitemaps, session), day)
    if df.empty:
        raise click.ClickException("no URLs found in the sitemaps")
    summ = core.site_summary(df, day)
    months = core.monthly(df, day)
    secs = core.sections(df)

    report = Report(title="Content velocity report", subtitle=f"{', '.join(summ['site'])} · ages as of {day}",
                    tool="content-velocity-tracker")
    fastest = summ.sort_values("updated_90d_pct", ascending=False).iloc[0]
    report.add_cards([
        ("Sites", len(summ)),
        ("URLs in sitemaps", len(df)),
        ("Updated in last 90 days", int((df["days_since_update"] <= core.QUARTER_DAYS).sum()), "good"),
        ("Stale (1 year+)", int((df["days_since_update"] > core.STALE_DAYS).sum()), "bad"),
        ("No lastmod", int(df["lastmod"].isna().sum()), "warn"),
        (f"Freshest site ({fastest['updated_90d_pct']}% updated in 90 days)", fastest["site"]),
    ])
    report.add_benchmark(STATS[0], how_used="Each site gets the survey's update tier from its lastmod dates: "
                         "monthly = changes in 10+ of the last 12 months, quarterly = changes in each of the last "
                         "four quarters. The tier's reported revenue growth is shown for context only.")
    report.add_benchmark(STATS[1], how_used="Fast-growing sites focused on updating, so the report counts "
                         "updates (lastmod) separately from new URLs (--compare) and flags pages untouched for a year.")
    report.add_table("Site summary", summ, sheet="Summary",
                     note="lastmod is what each site declares. Some CMSs set it on every deploy, so check a few URLs "
                          "before trusting a perfect score.")
    report.add_table("URLs updated per month", months, sheet="By month",
                     note="Count of URLs whose lastmod falls in each month (last 12 months).")
    report.add_table("Sections", secs, sheet="Sections", note="First folder of the URL path.")
    if previous:
        changes = core.compare(df, previous)
        report.add_table("Changes since the last snapshot", changes, sheet="Changes",
                         note=f"Compared with {Path(previous).name}.")
    stale = df[df["freshness"] == "stale (1y+)"].sort_values("days_since_update", ascending=False)
    report.add_table("Stale URLs (1 year+ without an update)", stale, sheet="Stale")
    report.add_table("All URLs", df.sort_values(["site", "days_since_update"]), sheet="All URLs")

    html_path = report.save_html(Path(output).with_suffix(".html"))
    xlsx_path = write_excel(report.sheets, Path(output).with_suffix(".xlsx"))
    if snapshot_path:
        core.snapshot(df).to_csv(snapshot_path, index=False)
        click.echo(f"Snapshot: {snapshot_path}")
    click.secho(f"Report: {html_path}\nData:   {xlsx_path}", fg="green", bold=True)
    click.echo(summ[["site", "urls", "updated_90d_pct", "stale_1y_pct", "update_tier"]].to_string(index=False))


if __name__ == "__main__":
    main()
