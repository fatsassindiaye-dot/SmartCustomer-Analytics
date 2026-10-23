import csv
import json
import numpy as np
from sklearn.cluster import KMeans
from django.http import HttpResponse
from django.db.models import Avg, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from .models import Customer

def liste_clients(request):
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "delete":
            customer = get_object_or_404(Customer, pk=request.POST.get("client_id"))
            customer.delete()
            return redirect("clients")

        if action in {"create", "update"}:
            customer = (
                get_object_or_404(Customer, pk=request.POST.get("edit_id"))
                if action == "update"
                else Customer()
            )
            customer.name = request.POST.get("name", "").strip()
            customer.email = request.POST.get("email", "").strip() or None
            customer.telephone = request.POST.get("telephone", "").strip() or None
            customer.total_achats = float(request.POST.get("total_achats") or 0)
            customer.nombre_visites = int(request.POST.get("nombre_visites") or 0)
            customer.pages_visitees = int(request.POST.get("pages_visitees") or 0)
            customer.temps_navigation = float(request.POST.get("temps_navigation") or 0)
            customer.produits_consultes = int(request.POST.get("produits_consultes") or 0)
            customer.save()
            return redirect("clients")

    q = request.GET.get("q", "").strip()
    categorie = request.GET.get("categorie", "Toutes")
    clients = Customer.objects.all().order_by("-created_at")

    if q:
        clients = clients.filter(
            Q(name__icontains=q) | Q(email__icontains=q) | Q(client_id__icontains=q)
        )

    clients = list(clients)
    if categorie != "Toutes":
        clients = [client for client in clients if client.categorie() == categorie]

    edit_client = None
    edit_id = request.GET.get("edit")
    if edit_id:
        edit_client = get_object_or_404(Customer, pk=edit_id)

    all_clients = list(Customer.objects.all())
    total_clients = len(all_clients)
    score_moyen = (
        round(sum(client.calculer_score() for client in all_clients) / total_clients, 2)
        if total_clients
        else 0
    )
    categories = ["Toutes", "VIP", "Fidèle", "Potentiel", "Nouveau"]
    category_counts = {
        "VIP": 0,
        "Fidèle": 0,
        "Potentiel": 0,
        "Nouveau": 0,
    }
    for client in all_clients:
        category_counts[client.categorie()] += 1

    chart_data = [
        {
            "label": label,
            "count": count,
            "percentage": (count * 100 / total_clients) if total_clients else 0,
        }
        for label, count in category_counts.items()
    ]

    stats = {
        "total_clients": total_clients,
        "vip_count": category_counts["VIP"],
        "total_achats": Customer.objects.aggregate(total=Sum("total_achats"))["total"] or 0,
        "score_moyen": score_moyen,
    }

    return render(
        request,
        "principal/clients.html",
        {
            "clients": clients,
            "stats": stats,
            "chart_data": chart_data,
            "categories": categories,
            "q": q,
            "categorie": categorie,
            "edit_client": edit_client,
        },
    )


def fiche_client(request, pk):
    """Vue détaillée d'un client avec fiche complète, score, probabilité et recommandations."""
    client = get_object_or_404(Customer, pk=pk)
    all_clients = list(Customer.objects.all())
    total_clients = len(all_clients)

    # Rang du client selon le score
    scores_sorted = sorted([c.calculer_score() for c in all_clients], reverse=True)
    score_client  = client.calculer_score()
    rang = scores_sorted.index(score_client) + 1 if score_client in scores_sorted else total_clients

    # Score max et percentile
    score_max   = max(scores_sorted) if scores_sorted else 1
    percentile  = round((1 - rang / total_clients) * 100) if total_clients > 1 else 100

    # Catégorie et couleur
    cat   = client.categorie()
    color = client.categorie_color()

    # Recommandation personnalisée
    if cat == "VIP":
        recommandation = (
            "Client ambassadeur. Proposez des invitations VIP, un gestionnaire de compte dédié "
            "et des offres exclusives pour renforcer la relation."
        )
        icone_reco = "fa-star"
        color_reco = "#059669"
    elif cat == "Fidèle":
        recommandation = (
            "Client fidèle à fort potentiel. Une réduction personnalisée de 10–15 % "
            "ou un programme de fidélité accélèrerait sa montée en VIP."
        )
        icone_reco = "fa-heart"
        color_reco = "#0ea5e9"
    elif cat == "Potentiel":
        recommandation = (
            "Client intéressé mais pas encore converti. Déclenchez une campagne email ciblée "
            "sur les produits qu'il a consultés pour l'inciter à l'achat."
        )
        icone_reco = "fa-bolt"
        color_reco = "#f59e0b"
    else:
        recommandation = (
            "Nouveau client ou inactif. Envoyez un code promo de bienvenue et inscrivez-le "
            "à la newsletter pour susciter son engagement."
        )
        icone_reco = "fa-envelope"
        color_reco = "#6c757d"

    # Détails des métriques pour la jauge radar
    metrics = [
        {"label": "Achats",   "value": min(100, round(client.total_achats / 1000)),  "color": "#6366f1"},
        {"label": "Visites",  "value": min(100, client.nombre_visites * 5),           "color": "#0ea5e9"},
        {"label": "Pages",    "value": min(100, client.pages_visitees * 3),           "color": "#f59e0b"},
        {"label": "Produits", "value": min(100, client.produits_consultes * 8),       "color": "#10b981"},
        {"label": "Temps",    "value": min(100, int(client.temps_navigation * 2)),    "color": "#ec4899"},
    ]

    return render(request, "principal/fiche_client.html", {
        "client":        client,
        "score":         score_client,
        "score_max":     score_max,
        "rang":          rang,
        "percentile":    percentile,
        "total_clients": total_clients,
        "cat":           cat,
        "color":         color,
        "probabilite":   client.probabilite_achat(),
        "recommandation": recommandation,
        "icone_reco":    icone_reco,
        "color_reco":    color_reco,
        "metrics":       metrics,
        "metrics_json":  __import__('json').dumps([{"label": m["label"], "value": m["value"]} for m in metrics]),
    })


def analyse(request):
    clients = Customer.objects.all().order_by("-created_at")
    stats = {
        "total_visites": clients.aggregate(total=Sum("nombre_visites"))["total"] or 0,
        "total_pages": clients.aggregate(total=Sum("pages_visitees"))["total"] or 0,
        "temps_moyen": round(clients.aggregate(avg=Avg("temps_navigation"))["avg"] or 0, 2),
        "total_produits": clients.aggregate(total=Sum("produits_consultes"))["total"] or 0,
        "total_achats": clients.aggregate(total=Sum("total_achats"))["total"] or 0,
    }

    return render(
        request,
        "analyse.html",
        {
            "clients": clients,
            "stats": stats,
        },
    )


def dashboard(request):
    import json as _json
    from datetime import datetime, timedelta
    from django.utils import timezone

    clients = list(Customer.objects.all().order_by('created_at'))
    total_clients = len(clients)

    categories = [
        {"label": "VIP",       "color": "#198754"},
        {"label": "Fidèle",    "color": "#0dcaf0"},
        {"label": "Potentiel", "color": "#fd7e14"},
        {"label": "Nouveau",   "color": "#6c757d"},
    ]
    category_counts = {cat["label"]: 0 for cat in categories}
    for client in clients:
        category_counts[client.categorie()] += 1

    total_achats   = sum(c.total_achats for c in clients)
    score_moyen    = round(sum(c.calculer_score() for c in clients) / total_clients, 2) if total_clients else 0

    # ── Nouveaux KPIs ──────────────────────────────────────────────────
    # Clients actifs : ont au moins 1 visite
    clients_actifs = sum(1 for c in clients if c.nombre_visites > 0)

    # Nouveaux clients : ajoutés dans les 30 derniers jours
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    nouveaux_clients = sum(1 for c in clients if c.created_at and c.created_at >= thirty_days_ago)

    # Taux de conversion : clients ayant effectué au moins un achat / total
    clients_avec_achat = sum(1 for c in clients if c.total_achats > 0)
    taux_conversion = round((clients_avec_achat / total_clients * 100), 1) if total_clients else 0

    # Chiffre d'affaires mensuel (30 derniers jours)
    ca_mensuel = sum(c.total_achats for c in clients if c.created_at and c.created_at >= thirty_days_ago)

    # Clients à risque : catégorie "Nouveau" avec 0 achat (inactifs)
    clients_a_risque = sum(1 for c in clients if c.categorie() == "Nouveau" and c.total_achats == 0)

    # Taux de fidélisation : (VIP + Fidèle) / total
    fideles_total = category_counts["VIP"] + category_counts["Fidèle"]
    taux_fidelisation = round((fideles_total / total_clients * 100), 1) if total_clients else 0

    # ── Chart data (donut + barres) ────────────────────────────────────
    chart_data = []
    gradient_parts = []
    start = 0
    category_scores = {cat["label"]: [] for cat in categories}
    for client in clients:
        category_scores[client.categorie()].append(client.calculer_score())

    for cat in categories:
        count      = category_counts[cat["label"]]
        percentage = round((count * 100 / total_clients), 2) if total_clients else 0
        end        = start + percentage
        chart_data.append({"label": cat["label"], "count": count,
                            "percentage": percentage, "color": cat["color"]})
        if count:
            gradient_parts.append(f"{cat['color']} {start}% {end}%")
        start = end

    pie_style = ", ".join(gradient_parts) if gradient_parts else "#dee2e6 0% 100%"
    category_avg_scores = [
        round(sum(category_scores[cat["label"]]) / len(category_scores[cat["label"]]), 1)
        if category_scores[cat["label"]] else 0
        for cat in categories
    ]

    # ── Évolution cumulée des ventes (par client, trié par date) ───────
    sorted_by_date = sorted(clients, key=lambda c: c.created_at or now)
    evolution_labels  = [c.name for c in sorted_by_date]
    evolution_values  = []
    cumul = 0
    for c in sorted_by_date:
        cumul += c.total_achats
        evolution_values.append(round(cumul, 0))

    # ── Évolution du nombre de visites (par client) ────────────────────
    visites_labels = [c.name for c in sorted_by_date]
    visites_values = [c.nombre_visites for c in sorted_by_date]

    # ── Produits les plus consultés (Top 5 clients / produits_consultes) ─
    top_produits = sorted(clients, key=lambda c: c.produits_consultes, reverse=True)[:6]
    produits_labels = [c.name for c in top_produits]
    produits_values = [c.produits_consultes for c in top_produits]

    # ── Comparaison mensuelle simulée sur 6 mois ──────────────────────
    # On simule des tranches de 5 jours par mois à partir des dates réelles
    mois_labels = ["Mois -5", "Mois -4", "Mois -3", "Mois -2", "Mois -1", "Ce mois"]
    mois_achats   = [0] * 6
    mois_visites  = [0] * 6
    for c in clients:
        if c.created_at:
            diff = (now - c.created_at).days
            idx = min(5, max(0, 5 - diff // 30))
            mois_achats[idx]  += c.total_achats
            mois_visites[idx] += c.nombre_visites

    # ── Top VIP & Récents ─────────────────────────────────────────────
    top_vip        = sorted(clients, key=lambda c: c.calculer_score(), reverse=True)[:5]
    recent_clients = sorted(clients, key=lambda c: c.created_at or now, reverse=True)[:5]

    return render(request, "principal/dashboard.html", {
        "stats": {
            "total_clients":    total_clients,
            "total_achats":     total_achats,
            "score_moyen":      score_moyen,
            "vip_count":        category_counts["VIP"],
            # Nouveaux KPIs
            "clients_actifs":   clients_actifs,
            "nouveaux_clients": nouveaux_clients,
            "taux_conversion":  taux_conversion,
            "ca_mensuel":       round(ca_mensuel, 0),
            "clients_a_risque": clients_a_risque,
            "taux_fidelisation": taux_fidelisation,
        },
        "chart_data":           chart_data,
        "pie_style":            pie_style,
        "top_vip":              top_vip,
        "recent_clients":       recent_clients,
        "category_avg_scores":  _json.dumps(category_avg_scores),
        # Nouveaux graphiques
        "evolution_labels":     _json.dumps(evolution_labels),
        "evolution_values":     _json.dumps(evolution_values),
        "visites_labels":       _json.dumps(visites_labels),
        "visites_values":       _json.dumps(visites_values),
        "produits_labels":      _json.dumps(produits_labels),
        "produits_values":      _json.dumps(produits_values),
        "mois_labels":          _json.dumps(mois_labels),
        "mois_achats":          _json.dumps([round(v,0) for v in mois_achats]),
        "mois_visites":         _json.dumps(mois_visites),
        "category_labels":      _json.dumps([cat["label"] for cat in categories]),
        "category_colors":      _json.dumps([cat["color"] for cat in categories]),
    })
from django.shortcuts import render
from .models import Customer

def ancien_dashboard_inutilise(request):
    clients = Customer.objects.all()

    vip = 0
    fidele = 0
    potentiel = 0
    nouveau = 0

    for c in clients:
        cat = c.categorie()
        if cat == "VIP":
            vip += 1
        elif cat == "Fidèle":
            fidele += 1
        elif cat == "Potentiel":
            potentiel += 1
        else:
            nouveau += 1

    return render(request, "dashboard.html", {
        "vip": vip,
        "fidele": fidele,
        "potentiel": potentiel,
        "nouveau": nouveau
    })


def documentation_uml(request):
    return render(request, "principal/uml.html")


def export_clients_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="analyse_clients.csv"'

    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'Nom', 
        'Email', 
        'Total des Achats (FCFA)', 
        'Nombre de Visites', 
        'Pages Visitées', 
        'Temps de Navigation (min)', 
        'Produits Consultés', 
        'Score Comportemental', 
        'Catégorie',
        'Date d\'Ajout'
    ])

    clients = Customer.objects.all().order_by('-created_at')
    for client in clients:
        writer.writerow([
            client.name,
            client.email or 'N/A',
            client.total_achats,
            client.nombre_visites,
            client.pages_visitees,
            client.temps_navigation,
            client.produits_consultes,
            client.calculer_score(),
            client.categorie(),
            client.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    return response


import json

def analyses_bi(request):
    clients = list(Customer.objects.all())
    clients_data = []
    for c in clients:
        clients_data.append({
            'name': c.name,
            'email': c.email or '',
            'total_achats': c.total_achats,
            'nombre_visites': c.nombre_visites,
            'pages_visitees': c.pages_visitees,
            'temps_navigation': c.temps_navigation,
            'produits_consultes': c.produits_consultes,
            'score': c.calculer_score(),
            'categorie': c.categorie()
        })
    return render(request, "principal/powerbi.html", {
        "clients_json": json.dumps(clients_data)
    })


def analyses_ia(request):
    clients = list(Customer.objects.all())
    count = len(clients)

    if count >= 3:
        # Extraction des caractéristiques : total_achats et nombre_visites
        X = np.array([[c.total_achats, c.nombre_visites] for c in clients])

        # Standardisation des données (K-Means y est sensible)
        X_mean = X.mean(axis=0)
        X_std = X.std(axis=0)
        X_std[X_std == 0] = 1.0
        X_scaled = (X - X_mean) / X_std

        # Entraînement de K-Means (K=3)
        kmeans = KMeans(n_clusters=3, random_state=42, n_init='auto')
        kmeans.fit(X_scaled)
        labels = kmeans.labels_

        # Calcul des centres de gravité (centroids) sur l'échelle d'origine
        centers_scaled = kmeans.cluster_centers_
        centers_original = (centers_scaled * X_std) + X_mean

        # Tri cohérent des clusters par niveau d'achat moyen (0: Bas, 1: Moyen, 2: Haut)
        sorted_indices = np.argsort(centers_original[:, 0])
        map_cluster = {old_id: new_id for new_id, old_id in enumerate(sorted_indices)}

        # Regroupement des clients par cluster trié
        clusters_data = {0: [], 1: [], 2: []}
        for i, c in enumerate(clients):
            sorted_label = map_cluster[labels[i]]
            clusters_data[sorted_label].append(c)

        # Préparation des données pour JSON Chart.js
        clients_json = []
        for i, c in enumerate(clients):
            clients_json.append({
                'name': c.name,
                'total_achats': float(c.total_achats),
                'nombre_visites': int(c.nombre_visites),
                'cluster': int(map_cluster[labels[i]])
            })

        # Centres de gravité triés
        centers_json = [
            {'x': float(centers_original[sorted_indices[k]][0]), 'y': float(centers_original[sorted_indices[k]][1])}
            for k in range(3)
        ]

        # Statistiques des groupes
        colors = ['#6366f1', '#f59e0b', '#10b981'] # Indigo, Orange, Vert émeraude
        meanings = [
            "Faible volume d'achat, visites irrégulières (Clients Occasionnels / Inactifs)",
            "Panier d'achat moyen, visites régulières (Clients Potentiels à fidéliser)",
            "Volume d'achat très élevé, visites fréquentes (Clients VIP / Ambassadeurs)"
        ]
        titles = [
            "Segment Économique / Nouveau",
            "Segment Régulier / Fidélité intermédiaire",
            "Segment Premium / VIP"
        ]

        cluster_stats = []
        for k in range(3):
            c_list = clusters_data[k]
            c_count = len(c_list)
            c_avg_achat = round(sum(c.total_achats for c in c_list) / c_count, 2) if c_count else 0
            c_avg_visites = round(sum(c.nombre_visites for c in c_list) / c_count, 2) if c_count else 0

            cluster_stats.append({
                'id': k,
                'title': titles[k],
                'count': c_count,
                'avg_achat': c_avg_achat,
                'avg_visites': c_avg_visites,
                'color': colors[k],
                'meaning': meanings[k]
            })

        context = {
            "has_data": True,
            "clients_data": clients_json,
            "centers_data": centers_json,
            "cluster_stats": cluster_stats
        }
    else:
        context = {
            "has_data": False,
            "client_count": count
        }

    return render(request, "principal/ia.html", context)



