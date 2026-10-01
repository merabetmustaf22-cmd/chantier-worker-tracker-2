import sqlite3
from datetime import date
import pandas as pd
import streamlit as st

# Configuration de la page
st.set_page_config(
    page_title="Système de Scoring Ouvriers", page_icon="👷", layout="wide"
)

# Connexion à la base de données SQLite
conn = sqlite3.connect("chantier_tracker.db", check_same_thread=False)
c = conn.cursor()

# Création des tables nécessaires
c.execute("""
CREATE TABLE IF NOT EXISTS workers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom_prenom TEXT NOT NULL,
    poste TEXT NOT NULL,
    actif INTEGER DEFAULT 1
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS daily_attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id INTEGER,
    date TEXT,
    statut TEXT,
    heures_sup REAL DEFAULT 0
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS daily_productivity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id INTEGER,
    date TEXT,
    qte_realisee REAL,
    qte_cible REAL
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS penalties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id INTEGER,
    date TEXT,
    type_incident TEXT,
    points_retires INTEGER,
    remarque TEXT
)
""")
conn.commit()

# Données d'exemple initiales
c.execute("SELECT COUNT(*) FROM workers")
if c.fetchone()[0] == 0:
    workers_init = [
        ("Mohamed Benali", "Applicateur"),
        ("Karim Mansouri", "Chef d'équipe"),
        ("Youcef Belkacem", "Manoeuvre"),
        ("Ahmed Zitouni", "Applicateur"),
    ]
    c.executemany(
        "INSERT INTO workers (nom_prenom, poste) VALUES (?, ?)", workers_init
    )
    conn.commit()

# Menu latéral
st.sidebar.title("👷 Suivi de Chantier")
menu = st.sidebar.radio(
    "Menu Principal",
    [
        "📊 Dashboard Responsable (Score & Primes)",
        "🕒 Pointage de Présence",
        "📐 Saisie de Rendement",
        "⚠️️ Enregistrement des Pénalités",
    ],
)

# Récupération des ouvriers actifs
df_workers = pd.read_sql_query(
    "SELECT id, nom_prenom, poste FROM workers WHERE actif = 1", conn
)
workers_dict = dict(zip(df_workers["id"], df_workers["nom_prenom"]))

# ==========================================
# 1. Dashboard Responsable
# ==========================================
if menu == "📊 Dashboard Responsable (Score & Primes)":
    st.title("📊 Évaluation des Ouvriers et Calcul du Score")
    st.write(
        "Tableau de bord pour le calcul automatique des scores et le classement des ouvriers."
    )

    scores = []
    for _, w in df_workers.iterrows():
        w_id = w["id"]
        score_base = 100

        # Données de présence
        df_att = pd.read_sql_query(
            f"SELECT statut, heures_sup FROM daily_attendance WHERE worker_id = {w_id}",
            conn,
        )
        retards = len(df_att[df_att["statut"] == "Retard"])
        absences = len(df_att[df_att["statut"] == "Absent"])
        heures_sup = df_att["heures_sup"].sum() if not df_att.empty else 0

        # Données de rendement
        df_prod = pd.read_sql_query(
            f"SELECT qte_realisee, qte_cible FROM daily_productivity WHERE worker_id = {w_id}",
            conn,
        )
        total_realise = (
            df_prod["qte_realisee"].sum() if not df_prod.empty else 0
        )
        total_cible = df_prod["qte_cible"].sum() if not df_prod.empty else 0

        bonus_prod = 0
        rendement_pct = 100.0
        if total_cible > 0:
            rendement_pct = round((total_realise / total_cible) * 100, 1)
            if rendement_pct > 100:
                bonus_prod = int((rendement_pct - 100) / 10) * 2

        # Données des pénalités
        df_pen = pd.read_sql_query(
            f"SELECT points_retires FROM penalties WHERE worker_id = {w_id}",
            conn,
        )
        total_penalties = (
            df_pen["points_retires"].sum() if not df_pen.empty else 0
        )

        # Calcul final
        final_score = (
            score_base
            + (heures_sup * 1)
            + bonus_prod
            - (retards * 2)
            - (absences * 10)
            - total_penalties
        )

        if final_score >= 95:
            categorie = "⭐ Catégorie A+ (Prime max / Promotion)"
        elif final_score >= 80:
            categorie = "✅ Catégorie A (Prime standard)"
        elif final_score >= 60:
            categorie = "⚠️ Catégorie B (Moyen / Pas de prime)"
        else:
            categorie = "❌ Catégorie C (Faible / Recadrage requis)"

        scores.append({
            "Nom & Prénom": w["nom_prenom"],
            "Poste": w["poste"],
            "Rendement (%)": f"{rendement_pct}%",
            "Heures Sup": heures_sup,
            "Retards": retards,
            "Absences": absences,
            "Score Final": max(0, final_score),
            "Statut Suggéré": categorie,
        })

    df_result = pd.DataFrame(scores).sort_values(
        by="Score Final", ascending=False
    )
    st.dataframe(df_result, use_container_width=True)

# ==========================================
# 2. Pointage de Présence
# ==========================================
elif menu == "🕒 Pointage de Présence":
    st.subheader("🕒 Saisie du Pointage")
    jour = st.date_input("Date", date.today())

    with st.form("form_pointage"):
        selected_worker = st.selectbox(
            "Ouvrier",
            options=list(workers_dict.keys()),
            format_func=lambda x: workers_dict[x],
        )
        statut = st.radio(
            "Statut", ["Présent", "Retard", "Absent"], horizontal=True
        )
        h_sup = st.number_input(
            "Heures supplémentaires", min_value=0.0, max_value=8.0, step=0.5
        )

        if st.form_submit_button("Enregistrer"):
            c.execute(
                "INSERT INTO daily_attendance (worker_id, date, statut, heures_sup) VALUES (?, ?, ?, ?)",
                (selected_worker, str(jour), statut, h_sup),
            )
            conn.commit()
            st.success("Pointage enregistré !")

# ==========================================
# 3. Saisie de Rendement
# ==========================================
elif menu == "📐 Saisie de Rendement":
    st.subheader("📐 Saisie du Rendement Quotidien")
    jour = st.date_input("Date", date.today())

    with st.form("form_prod"):
        selected_worker = st.selectbox(
            "Ouvrier",
            options=list(workers_dict.keys()),
            format_func=lambda x: workers_dict[x],
        )
        col1, col2 = st.columns(2)
        with col1:
            qte_realisee = st.number_input(
                "Quantité réalisée (ex: m²)", min_value=0.0, step=5.0
            )
        with col2:
            qte_cible = st.number_input(
                "Objectif cible (ex: m²)", min_value=1.0, value=80.0, step=5.0
            )

        if st.form_submit_button("Enregistrer"):
            c.execute(
                "INSERT INTO daily_productivity (worker_id, date, qte_realisee, qte_cible) VALUES (?, ?, ?, ?)",
                (selected_worker, str(jour), qte_realisee, qte_cible),
            )
            conn.commit()
            st.success("Rendement enregistré !")

# ==========================================
# 4. Enregistrement des Pénalités
# ==========================================
elif menu == "⚠️ Enregistrement des Pénalités":
    st.subheader("⚠️ Signalement des Fautes et Infractions")
    jour = st.date_input("Date", date.today())

    with st.form("form_penalties"):
        selected_worker = st.selectbox(
            "Ouvrier",
            options=list(workers_dict.keys()),
            format_func=lambda x: workers_dict[x],
        )
        type_incident = st.selectbox("Type d'infraction", [
            "Manque d'équipement de sécurité (Casque, gilet...)",
            "Malfaçon nécessitant reprise",
            "Gaspillage de matière première",
            "Départ avant l'heure sans autorisation",
        ])
        pts = st.slider("Points à retirer", min_value=1, max_value=20, value=5)
        remarque = st.text_area("Remarque / Détails")

        if st.form_submit_button("Appliquer la sanction"):
            c.execute(
                "INSERT INTO penalties (worker_id, date, type_incident, points_retires, remarque) VALUES (?, ?, ?, ?, ?)",
                (selected_worker, str(jour), type_incident, pts, remarque),
            )
            conn.commit()
            st.warning(f"{pts} points retirés avec succès.")
