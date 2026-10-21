import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Analyse_intelligente_des_comportements_clients.settings')

application = get_wsgi_application()
