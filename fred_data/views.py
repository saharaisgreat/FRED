"""Views for the FRED Macro Dashboard."""

import logging
from urllib.parse import unquote

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .fred_config import CATEGORIES, FRED_SERIES, SERIES_BY_CATEGORY
from .fred_service import fetch_series_observations, get_dashboard_summary

logger = logging.getLogger(__name__)


def index(request):
    api_key_set = bool(getattr(settings, "FRED_API_KEY", ""))
    context = {
        "categories": CATEGORIES,
        "series_by_category": SERIES_BY_CATEGORY,
        "api_key_set": api_key_set,
        "total_series": len(FRED_SERIES),
    }
    return render(request, "fred_data/dashboard.html", context)


def charts(request):
    """Charts page — YoY line graphs for all series."""
    import json
    context = {
        "categories": json.dumps(CATEGORIES),
        "series_by_category": SERIES_BY_CATEGORY,
    }
    return render(request, "fred_data/charts.html", context)


@require_GET
def api_summary(request):
    force_refresh = request.GET.get("refresh", "false").lower() == "true"
    try:
        summary = get_dashboard_summary(use_cache=not force_refresh)
        by_category = {}
        for sid, data in summary.items():
            cat = data["category"]
            by_category.setdefault(cat, []).append({"series_id": sid, **data})
        return JsonResponse({
            "status": "ok",
            "data": summary,
            "by_category": by_category,
            "categories": CATEGORIES,
        })
    except Exception as e:
        logger.error("Error in api_summary: %s", e)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@require_GET
def api_series(request, series_id):
    series_id = series_id.upper()
    if series_id not in FRED_SERIES:
        return JsonResponse({"status": "error", "message": f"Unknown series: {series_id}"}, status=404)
    force_refresh = request.GET.get("refresh", "false").lower() == "true"
    data = fetch_series_observations(series_id, use_cache=not force_refresh)
    if not data:
        return JsonResponse({"status": "error", "message": "Failed to fetch data from FRED."}, status=502)
    return JsonResponse({"status": "ok", "data": data})


@require_GET
def api_category(request, category):
    category = unquote(category)
    if category not in CATEGORIES:
        return JsonResponse({"status": "error", "message": f"Unknown category: {category}"}, status=404)
    series_ids = [sid for sid, meta in FRED_SERIES.items() if meta["category"] == category]
    results = {}
    for sid in series_ids:
        data = fetch_series_observations(sid)
        if data:
            results[sid] = data
    return JsonResponse({"status": "ok", "category": category, "data": results})


@require_GET
def health(request):
    api_key_set = bool(getattr(settings, "FRED_API_KEY", ""))
    return JsonResponse({"status": "ok", "fred_api_key_configured": api_key_set, "series_count": len(FRED_SERIES)})