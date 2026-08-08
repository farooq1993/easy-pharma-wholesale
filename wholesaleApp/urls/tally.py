from django.urls import path
from wholesaleApp.views.tally_views import (
    tally_dashboard,
    tally_export_csv
)

urlpatterns = [
    path('tally/dashboard/', tally_dashboard, name='tally_dashboard'),
    path('tally/export/csv/', tally_export_csv, name='tally_export_csv'),
]
