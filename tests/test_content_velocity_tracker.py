import gzip
import tempfile
import threading
import unittest
from datetime import date
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from click.testing import CliRunner

from content_velocity_tracker import cli, core

EXAMPLES = Path(__file__).parent.parent / "examples"
AS_OF = date(2026, 10, 15)

SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.a.com/</loc><lastmod>2026-10-10T08:00:00+00:00</lastmod></url>
  <url><loc>https://www.a.com/blog/fresh</loc><lastmod>2026-09-20</lastmod></url>
  <url><loc>https://www.a.com/blog/old</loc><lastmod>2024-01-05</lastmod></url>
  <url><loc>https://www.a.com/pricing</loc></url>
</urlset>
"""


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class CoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "a.xml"
        self.path.write_text(SITEMAP, encoding="utf-8")
        self.df = core.add_age(core.load([self.path]), AS_OF)

    def tearDown(self):
        self.tmp.cleanup()

    def test_reads_urls_lastmod_and_site(self):
        self.assertEqual(len(self.df), 4)
        self.assertEqual(set(self.df["site"]), {"a.com"})
        row = self.df.set_index("url").loc["https://www.a.com/"]
        self.assertEqual(row["lastmod"], date(2026, 10, 10))
        self.assertEqual(row["section"], "/ (home)")

    def test_freshness_buckets(self):
        f = self.df.set_index("url")["freshness"]
        self.assertEqual(f["https://www.a.com/blog/fresh"], "last 30 days")
        self.assertEqual(f["https://www.a.com/blog/old"], "stale (1y+)")
        self.assertEqual(f["https://www.a.com/pricing"], "no lastmod")

    def test_gzip_sitemap(self):
        gz = Path(self.tmp.name) / "a.xml.gz"
        gz.write_bytes(gzip.compress(SITEMAP.encode()))
        self.assertEqual(len(core.read_sitemap(str(gz))), 4)

    def test_update_tiers(self):
        monthly = [date(2026, m, 1) for m in range(1, 11)]
        quarterly = [date(2026, 10, 1), date(2026, 7, 1), date(2026, 4, 1), date(2026, 1, 1)]
        self.assertEqual(core.update_tier(monthly, AS_OF), "monthly")
        self.assertEqual(core.update_tier(quarterly, AS_OF), "quarterly")
        self.assertEqual(core.update_tier([date(2026, 2, 1)], AS_OF), "occasional")
        self.assertEqual(core.update_tier([date(2023, 2, 1)], AS_OF), "rarely or never")

    def test_summary_and_months(self):
        summ = core.site_summary(self.df, AS_OF).iloc[0]
        self.assertEqual(summ["urls"], 4)
        self.assertEqual(summ["updated_90d"], 2)
        self.assertEqual(summ["np_tier_revenue_growth"], "no survey tier")
        months = core.monthly(self.df, AS_OF)
        self.assertEqual(len(months), 12)
        self.assertEqual(months.set_index("month").at["2026-10", "a.com"], 1)

    def test_compare_snapshot(self):
        old = Path(self.tmp.name) / "old.csv"
        old.write_text("site,url,lastmod\na.com,https://www.a.com/blog/fresh,2025-01-01\n"
                       "a.com,https://www.a.com/blog/old,2024-01-05\na.com,https://www.a.com/gone,2022-01-01\n",
                       encoding="utf-8")
        changes = core.compare(self.df, old).set_index("url")["change"]
        self.assertEqual(changes["https://www.a.com/blog/fresh"], "updated")
        self.assertEqual(changes["https://www.a.com/pricing"], "new")
        self.assertEqual(changes["https://www.a.com/gone"], "removed")
        self.assertNotIn("https://www.a.com/blog/old", changes.index)


class HttpTest(unittest.TestCase):
    def test_follows_sitemap_index_over_http(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = HTTPServer(("127.0.0.1", 0), partial(Quiet, directory=tmp))
            base = f"http://127.0.0.1:{server.server_port}"
            Path(tmp, "child.xml").write_text(SITEMAP, encoding="utf-8")
            Path(tmp, "index.xml").write_text(
                '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                f"<sitemap><loc>{base}/child.xml</loc></sitemap></sitemapindex>", encoding="utf-8")
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                import requests
                rows = core.read_sitemap(f"{base}/index.xml", requests.Session())
            finally:
                server.shutdown()
                server.server_close()
        self.assertEqual(len(rows), 4)


class CliTest(unittest.TestCase):
    def test_example_writes_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "velocity"
            snap = Path(tmp) / "snap.csv"
            args = [str(EXAMPLES / f) for f in ["brightcrm_sitemap.xml", "pipelinehq_sitemap.xml",
                                                 "salesdeck_sitemap.xml"]]
            args += ["--as-of", "2026-10-15", "--compare", str(EXAMPLES / "snapshot_2026-09-15.csv"),
                     "--snapshot", str(snap), "-o", str(out)]
            res = CliRunner().invoke(cli.main, args)
            self.assertEqual(res.exit_code, 0, res.output)
            html = out.with_suffix(".html").read_text(encoding="utf-8")
            self.assertIn("Content velocity report", html)
            self.assertIn("Changes since the last snapshot", html)
            self.assertTrue(out.with_suffix(".xlsx").exists())
            self.assertTrue(snap.exists())


if __name__ == "__main__":
    unittest.main()
