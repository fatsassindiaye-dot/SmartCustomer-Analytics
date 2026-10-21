from django.db import models
import math


class Customer(models.Model):
    # Identifiant lisible généré automatiquement (CL001, CL002, ...)
    client_id = models.CharField(max_length=10, unique=True, blank=True, null=True)

    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, null=True, blank=True)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    total_achats = models.FloatField(default=0)
    nombre_visites = models.IntegerField(default=0)
    pages_visitees = models.IntegerField(default=0)
    temps_navigation = models.FloatField(default=0)
    produits_consultes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """Génère automatiquement un client_id de type CL001 à la création."""
        if not self.client_id:
            super().save(*args, **kwargs)
            self.client_id = f"CL{self.pk:03d}"
            Customer.objects.filter(pk=self.pk).update(client_id=self.client_id)
        else:
            super().save(*args, **kwargs)

    def calculer_score(self):
        score = (
            (self.total_achats / 10000) * 40
            + self.nombre_visites * 10
            + self.pages_visitees * 5
            + self.produits_consultes * 3
            + self.temps_navigation * 2
        )
        return int(score)

    def probabilite_achat(self):
        """Probabilité d'achat estimée (%) via une sigmoïde sur le score."""
        score = self.calculer_score()
        # Sigmoïde centrée sur 50 (score moyen) — plage réaliste 10%–97%
        prob = 1 / (1 + math.exp(-(score - 50) / 20))
        return round(prob * 100, 1)

    def categorie(self):
        score = self.calculer_score()
        if score >= 80:
            return "VIP"
        if score >= 50:
            return "Fidèle"
        if score >= 20:
            return "Potentiel"
        return "Nouveau"

    def categorie_color(self):
        mapping = {
            "VIP":       "#059669",
            "Fidèle":    "#0ea5e9",
            "Potentiel": "#f59e0b",
            "Nouveau":   "#6c757d",
        }
        return mapping.get(self.categorie(), "#6c757d")

    def __str__(self):
        return f"{self.client_id or ''} — {self.name}"
