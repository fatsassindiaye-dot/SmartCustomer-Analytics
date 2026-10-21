import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Analyse_intelligente_des_comportements_clients.settings')

import django
django.setup()

from main.models import Customer

updates = {
    'RealCheck': 'Khady',
    'Test': 'Brahima'
}

for old_name, new_name in updates.items():
    for obj in Customer.objects.filter(name=old_name):
        obj.name = new_name
        obj.save()
        print(f'updated {obj.id}: {old_name} -> {new_name}')

print('Current names:', [c.name for c in Customer.objects.order_by('id')[:12]])

