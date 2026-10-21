from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("clients/", views.liste_clients, name="clients"),
    path("analyse/", views.analyse, name="analyse"),
    path("uml/", views.documentation_uml, name="uml"),
    path("clients/export-csv/", views.export_clients_csv, name="export_clients_csv"),
    path("powerbi/", views.analyses_bi, name="powerbi"),
    path("ia/", views.analyses_ia, name="ia"),
]
