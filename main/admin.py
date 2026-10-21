from django.contrib import admin
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'email',
        'total_achats',
        'nombre_visites',
        'calculer_score',
        'categorie'
    )
