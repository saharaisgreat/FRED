"""
Management command: fetch all FRED series and print a summary table.

Usage:
    python manage.py fetch_fred
    python manage.py fetch_fred --series GDPC1 UNRATE FEDFUNDS
    python manage.py fetch_fred --no-cache
"""

from django.core.management.base import BaseCommand, CommandError

from fred_data.fred_config import FRED_SERIES, CATEGORIES
from fred_data.fred_service import fetch_series_observations, get_dashboard_summary


class Command(BaseCommand):
    help = "Fetch macroeconomic data from FRED and display a summary table"

    def add_arguments(self, parser):
        parser.add_argument(
            "--series",
            nargs="+",
            metavar="SERIES_ID",
            help="Fetch only these series (default: all)",
        )
        parser.add_argument(
            "--no-cache",
            action="store_true",
            help="Bypass cache and fetch fresh data from FRED",
        )
        parser.add_argument(
            "--category",
            choices=CATEGORIES,
            help="Filter by category",
        )

    def handle(self, *args, **options):
        use_cache = not options["no_cache"]
        series_filter = [s.upper() for s in (options["series"] or [])]
        cat_filter = options.get("category")

        # Determine which series to fetch
        if series_filter:
            invalid = [s for s in series_filter if s not in FRED_SERIES]
            if invalid:
                raise CommandError(f"Unknown series IDs: {', '.join(invalid)}")
            target_ids = series_filter
        elif cat_filter:
            target_ids = [sid for sid, m in FRED_SERIES.items() if m["category"] == cat_filter]
        else:
            target_ids = list(FRED_SERIES.keys())

        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'='*72}\n  US Macro Dashboard — FRED Data Fetch\n{'='*72}"
            )
        )
        self.stdout.write(
            f"  Fetching {len(target_ids)} series | cache={'ON' if use_cache else 'OFF'}\n"
        )

        results = []
        for sid in target_ids:
            data = fetch_series_observations(sid, use_cache=use_cache)
            if not data:
                self.stdout.write(self.style.WARNING(f"  ✗ {sid}: failed"))
                continue

            latest = data.get("latest") or {}
            meta = data["meta"]
            yoy = latest.get("yoy_pct")
            yoy_str = f"{yoy:+.2f}%" if yoy is not None else "N/A"
            val_str = f"{latest.get('value', 'N/A')}"

            self.stdout.write(
                f"  ✓ {sid:<20} {meta.get('name',''):<35} "
                f"Latest: {val_str:<12} YoY: {yoy_str}"
            )
            results.append((sid, data))

        # Print category summary
        self.stdout.write(f"\n{'─'*72}")
        self.stdout.write(f"  {len(results)}/{len(target_ids)} series fetched successfully.")
        self.stdout.write(
            "\n  Run 'python manage.py runserver' and open http://127.0.0.1:8000 "
            "to see the live dashboard.\n"
        )
