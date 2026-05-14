from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="dashboard"),
    path("charts/", views.charts, name="charts"),
    path("api/summary/", views.api_summary, name="api_summary"),
    path("api/series/<str:series_id>/", views.api_series, name="api_series"),
    path("api/category/<str:category>/", views.api_category, name="api_category"),
    path("api/health/", views.health, name="health"),
]