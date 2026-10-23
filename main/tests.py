from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Customer


@override_settings(SECURE_SSL_REDIRECT=False)
class ClientsViewTests(TestCase):
    def test_clients_page_displays_client_data(self):
        Customer.objects.create(
            name="Alice Dupont",
            email="alice@example.com",
            total_achats=150.50,
            nombre_visites=5,
        )

        response = self.client.get(reverse("clients"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gestion des Clients")
        self.assertContains(response, "Alice Dupont")
        self.assertContains(response, "alice@example.com")

    def test_create_client_redirects_and_refreshes_list(self):
        response = self.client.post(
            reverse("clients"),
            {
                "action": "create",
                "name": "Mamadou Ba",
                "email": "mamadou@example.com",
                "total_achats": "12000",
                "nombre_visites": "3",
                "pages_visitees": "4",
                "temps_navigation": "2.5",
                "produits_consultes": "2",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("clients"))
        self.assertContains(response, "Mamadou Ba")

    def test_uml_page_renders(self):
        response = self.client.get(reverse("uml"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Modèle de données")

    def test_ai_page_renders_without_clients(self):
        response = self.client.get(reverse("ia"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Analyse intelligente")

    def test_ai_page_renders_clustered_clients(self):
        for name, total_achats, nombre_visites in (
            ("Alice", 100, 1),
            ("Bob", 5000, 5),
            ("Charlie", 20000, 12),
        ):
            Customer.objects.create(
                name=name,
                total_achats=total_achats,
                nombre_visites=nombre_visites,
            )

        response = self.client.get(reverse("ia"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["has_data"])
        self.assertContains(response, 'id="cluster-clients-data"')
        self.assertContains(response, 'id="cluster-centers-data"')
