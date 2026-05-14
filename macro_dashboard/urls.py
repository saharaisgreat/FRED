from django.urls import path, include

urlpatterns = [
    path('', include('fred_data.urls')),
]
