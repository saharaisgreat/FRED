from django.apps import AppConfig

class FredDataConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fred_data'
    verbose_name = 'FRED Macro Data'
