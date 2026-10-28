# 📂 Sample data

Three **made-up** XML sitemaps for a fictional CRM market, plus a snapshot "from a month earlier":

| File | Site | Rhythm built in |
|---|---|---|
| `brightcrm_sitemap.xml` | brightcrm.io | Updates in batches once a quarter |
| `pipelinehq_sitemap.xml` | pipelinehq.com | Updates every month |
| `salesdeck_sitemap.xml` | salesdeck.io | Hardly touches its content |
| `snapshot_2026-09-15.csv` | all three | An older snapshot, for `--compare` |

The sites, URLs and dates are fictional. `--as-of 2026-10-15` keeps the sample output the same on every run.

```bash
content-velocity-tracker examples/brightcrm_sitemap.xml examples/pipelinehq_sitemap.xml examples/salesdeck_sitemap.xml --as-of 2026-10-15 --compare examples/snapshot_2026-09-15.csv
```
