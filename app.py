import os
import sqlite3
from datetime import date
import pandas as pd
import streamlit as st

# Configuration mobile
st.set_page_config(
    page_title="Suivi Chantier & Étanchéité",
    page_icon="🏗️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DB_PATH = os.path.join("/tmp", "chantier_tracker.db")

# Vos 14 Chantiers réels
LISTE_CHANTIERS = [
    "CAC-31-24",
    "CMA-09-23",
    "ECOLE SBA",
    "GROUPEMENT GENDARMERIE",
    "HOB-342-08-24",
    "HTA ZONE SBA",
    "IZM-31-24(CES)",
    "LBU-31-23",
    "LCP-31-24",
    "MARAVAL",
    "VILLA CITE EL RIAD ORAN",
    "VILLA Hasnaoui MAKAM",
    "VILLA Hasnaoui Outhman",
    "ESC-16-24",
]

# Vos Corps d'état & Tâches réelles
LISTE_CORPS_ETAT = [
    "CONGÉ",
    "MALADIE",
    "RECUPERATION",
    "1/2 journée",
    "Absence autorisée",
    "PAX",
    "PARE-VAPEUR",
    "SOKLE PARE-VAPEUR",
    "ELASTOTEK",
    "ELASTOTEK GOURGE",
    "ELASTOTEK JOINTAGE",
    "ELASTOTEK LEVI",
    "ELASTOTEK NETTOYAGE",
    "ELASTOTEK Ponçage",
    "ELASTOTEK RESERVE",
    "ELASTOTEK SAUPOUDRAGE",
    "Forme de pente",
    "GOURGE",
    "JOINT DE DILATATION",
    "MASTIC",
    "nettoyage",
    "PONSAGE",
    "décapage",
    "BACHE A EAU",
    "PISCINE",
    "SOUS CARRELAGE",
    "TEST EAU",
    "coupe-feu",
    "Couvre-joint",
    "DALLE Cheminée",
    "regard",
    "Traitement de l'ascenseur",
    "BRICOL",
    "BRICOL ELASTOTEK",
    "BRICOL SILICONE",
    "BRICOL SOKLE",
    "BRICOL SOUS CARRELAGE",
    "BRICOL PARE-VAPEUR",
    "BRICOL Cheminée",
    "DIVERS",
]

# Votre effectif de 23 ouvriers
EFFECTIF_GLOBAL = [
    "ADDA Abbess",
    "MEKHACHEF DJAMEL",
    "MESTEFAOUI AHMED",
    "ARGOUB HALIM",
    "FEHIM CHIBANI AZZOUZ",
    "TAIBI REDA",
    "ABED OMAR",
    "ZEGHDAN ABDELKADER",
    "BAGHDADI ALI",
    "BOUKHELIF KAMEL",
    "MOKHTARI Omar",
    "GHEZINI Habib",
    "BERACHEMI AHMED",
    "ARAR AISSA",
    "MOKHTARI Djelloul",
    "HAFDI Rachid",
    "BENHAMMADI Mohamed",
    "MOUISSI WALID",
    "BENSEMICHA MEROUANE",
    "TOUATI Zouaoui",
    "GHRIBI MOHAMED",
    "MESSAOUDI ABDELKRIM",
    "TAHAR BOUZIAN YOUCEF",
]


def get_connection():
  conn = sqlite3.connect(DB_PATH)
  c = conn.cursor()
  c.execute("""
        CREATE TABLE IF NOT EXISTS workers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            fonction TEXT NOT NULL
        )
    """)
  c.execute("""
        CREATE TABLE IF NOT EXISTS rapports_journaliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_jour TEXT,
            chantier TEXT,
            worker_id INTEGER,
            statut TEXT,
            corps_etat TEXT,
            quantite REAL,
            unite TEXT,
            qualite_dechet TEXT,
            hse_conforme INTEGER,
            score REAL,
            FOREIGN KEY(worker_id) REFERENCES workers(id)
        )
    """)
  conn.commit()

  for w in EFFECTIF_GLOBAL:
    c.execute(
        "INSERT OR IGNORE INTO workers (nom, fonction) VALUES (?, ?)",
        (w, "Applicateur Étanchéité"),
    )
  conn.commit()
  return conn


def get_workers():
  conn = get_connection()
  c = conn.cursor()
  c.execute("SELECT id, nom FROM workers ORDER BY nom ASC")
  rows = c.fetchall()
  conn.close()
  return pd.DataFrame(rows, columns=["id", "nom"])


def get_rapports():
  conn = get_connection()
  c = conn.cursor()
  c.execute("""
        SELECT 
            r.date_jour AS Date,
            r.chantier AS Chantier,
            w.nom AS Ouvrier,
            r.statut AS Statut,
            r.corps_etat AS [Corps d'État],
            r.quantite || ' ' || r.unite AS Production,
            r.qualite_dechet AS Qualite,
            r.score AS Score
        FROM rapports_journaliers r
        JOIN workers w ON r.worker_id = w.id
        ORDER BY r.id DESC
    """)
  rows = c.fetchall()
  conn.close()
  return pd.DataFrame(
      rows,
      columns=[
          "Date",
          "Chantier",
          "Ouvrier",
          "Statut",
          "Corps d'État",
          "Production",
          "Qualite",
          "Score",
      ],
  )


# --- INTERFACE ---
st.title("🏗️ Suivi Chantier Étanchéité")
onglet = st.radio(
    "Menu", ["Saisie Chantier", "Tableau de Bord"], horizontal=True
)

# 1. SAISIE DU CHANTIER
if onglet == "Saisie Chantier":
  st.subheader("Rapport Journalier de Pose")
  df_w = get_workers()
  ouvriers_dict = dict(zip(df_w["nom"], df_w["id"]))

  with st.form("form_saisie", clear_on_submit=True):
    col_a, col_b = st.columns(2)
    with col_a:
      chantier = st.selectbox("📍 Chantier", LISTE_CHANTIERS)
    with col_b:
      date_jour = st.date_input("📅 Date", value=date.today())

    st.markdown("---")
    nom_ouvrier = st.selectbox(
        "👷 Ouvrier", list(ouvriers_dict.keys())
    )

    statut = st.radio(
        "Statut de la journée",
        ["Présent (Travail)", "1/2 journée", "Absent / Congé / Maladie"],
        horizontal=True,
    )

    corps_etat = st.selectbox("🛠️ Corps d'état / Tâche", LISTE_CORPS_ETAT)

    quantite = 0.0
    unite = "m²"
    qualite = "Faible (Très bien)"
    hse = True

    if statut != "Absent / Congé / Maladie":
      c1, c2 = st.columns(2)
      with c1:
        quantite = st.number_input(
            "Production réalisée", min_value=0.0, step=0.5, value=25.0
        )
      with c2:
        unite = st.selectbox("Unité", ["m²", "ml", "Unité", "Fût", "Bricol"])

      qualite = st.select_slider(
          "Qualité / Déchets & Chutes",
          options=[
              "Élevé (Mauvais)",
              "Moyen (Acceptable)",
              "Faible (Très bien)",
          ],
          value="Faible (Très bien)",
      )
      hse = st.checkbox("Respect HSE & EPI obligatoires", value=True)

    btn_valider = st.form_submit_button("Enregistrer la saisie")

    if btn_valider:
      # Calcul automatique du score
      if statut == "Absent / Congé / Maladie":
        score = 0.0
      else:
        score = 30.0 if statut == "Présent (Travail)" else 15.0
        if quantite >= 40:
          score += 40
        elif quantite >= 25:
          score += 30
        elif quantite > 0:
          score += 15

        if qualite == "Faible (Très bien)":
          score += 15
        elif qualite == "Moyen (Acceptable)":
          score += 10

        if hse:
          score += 15
        score = min(score, 100.0)

      conn = get_connection()
      c = conn.cursor()
      c.execute(
          """
                INSERT INTO rapports_journaliers 
                (date_jour, chantier, worker_id, statut, corps_etat, quantite, unite, qualite_dechet, hse_conforme, score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
          (
              str(date_jour),
              chantier,
              ouvriers_dict[nom_ouvrier],
              statut,
              corps_etat,
              quantite,
              unite,
              qualite,
              int(hse),
              score,
          ),
      )
      conn.commit()
      conn.close()
      st.success(
          f"Enregistré pour {nom_ouvrier} sur {chantier} (Score: {score}/100) !"
      )

# 2. TABLEAU DE BORD
elif onglet == "Tableau de Bord":
  st.subheader("Synthèse de l'Activité")
  df_r = get_rapports()

  if df_r.empty:
    st.info("Aucune saisie effectuée pour le moment.")
  else:
    # Filtres rapides
    col_f1, col_f2 = st.columns(2)
    with col_f1:
      filtre_chantier = st.selectbox(
          "Filtrer par Chantier", ["Tous"] + LISTE_CHANTIERS
      )
    with col_f2:
      filtre_ouvrier = st.selectbox(
          "Filtrer par Ouvrier", ["Tous"] + list(EFFECTIF_GLOBAL)
      )

    df_affiche = df_r.copy()
    if filtre_chantier != "Tous":
      df_affiche = df_affiche[df_affiche["Chantier"] == filtre_chantier]
    if filtre_ouvrier != "Tous":
      df_affiche = df_affiche[df_affiche["Ouvrier"] == filtre_ouvrier]

    st.dataframe(df_affiche, use_container_width=True, hide_index=True)

    csv = df_affiche.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Exporter cette sélection (CSV)",
        data=csv,
        file_name="rapport_chantiers_etancheite.csv",
        mime="text/csv",
        use_container_width=True,
    )
