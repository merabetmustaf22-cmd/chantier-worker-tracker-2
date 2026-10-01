import os
import sqlite3
from datetime import date
import pandas as pd
import streamlit as st

# Configuration responsive mobile
st.set_page_config(
    page_title="Suivi Chantier & Matériaux",
    page_icon="🏗️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DB_PATH = os.path.join("/tmp", "chantier_tracker_v6.db")

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

LISTE_CORPS_ETAT = [
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
    "CONGÉ",
    "MALADIE",
    "RECUPERATION",
    "1/2 journée",
    "Absence autorisée",
]

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


def init_database():
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
            conso_rouleaux REAL,
            conso_primaire REAL,
            conso_gaz REAL,
            conso_elastotek REAL,
            observation TEXT,
            qualite_dechet TEXT,
            score REAL,
            FOREIGN KEY(worker_id) REFERENCES workers(id)
        )
    """)
  for w in EFFECTIF_GLOBAL:
    c.execute(
        "INSERT OR IGNORE INTO workers (nom, fonction) VALUES (?, ?)",
        (w, "Applicateur Étanchéité"),
    )
  conn.commit()
  conn.close()


init_database()


def get_workers():
  init_database()
  conn = sqlite3.connect(DB_PATH)
  c = conn.cursor()
  c.execute("SELECT id, nom FROM workers ORDER BY nom ASC")
  rows = c.fetchall()
  conn.close()
  return pd.DataFrame(rows, columns=["id", "nom"])


def get_rapports():
  init_database()
  conn = sqlite3.connect(DB_PATH)
  c = conn.cursor()
  c.execute("""
        SELECT 
            r.date_jour AS Date,
            r.chantier AS Chantier,
            w.nom AS Ouvrier,
            r.statut AS Statut,
            r.corps_etat AS [Corps d'État],
            CASE 
                WHEN r.statut LIKE '%Absence autorisée%' THEN 'Excusé'
                WHEN r.statut LIKE '%Injustifiée%' THEN 'Non justifié'
                WHEN r.unite = 'Sans métrage' THEN 'Bricol / Jour'
                ELSE r.quantite || ' ' || r.unite 
            END AS Production,
            r.conso_rouleaux AS [Rouleaux PAX],
            r.conso_primaire AS [Primaire (L/Fût)],
            r.conso_gaz AS [Gaz (Btl)],
            r.conso_elastotek AS [Élastotek (Kg/Seau)],
            COALESCE(r.observation, '-') AS Observation,
            r.qualite_dechet AS Qualite,
            CASE 
                WHEN r.score IS NULL THEN 'Justifié'
                ELSE CAST(r.score AS TEXT)
            END AS Score
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
          "Rouleaux PAX",
          "Primaire (L/Fût)",
          "Gaz (Btl)",
          "Élastotek (Kg/Seau)",
          "Observation",
          "Qualite",
          "Score",
      ],
  )


# --- INTERFACE ---
st.title("🏗️ Suivi Chantier & Matériaux")
onglet = st.radio(
    "Menu", ["Saisie Chantier", "Tableau de Bord"], horizontal=True
)

# 1. SAISIE DU CHANTIER
if onglet == "Saisie Chantier":
  st.subheader("Rapport Journalier & Consommation")
  df_w = get_workers()
  ouvriers_dict = dict(zip(df_w["nom"], df_w["id"]))

  with st.form("form_saisie", clear_on_submit=True):
    col_a, col_b = st.columns(2)
    with col_a:
      chantier = st.selectbox("📍 Chantier", LISTE_CHANTIERS)
    with col_b:
      date_jour = st.date_input("📅 Date", value=date.today())

    st.markdown("---")
    nom_ouvrier = st.selectbox("👷 Ouvrier", list(ouvriers_dict.keys()))

    statut = st.radio(
        "Statut de la journée",
        [
            "Présent (Travail)",
            "1/2 journée",
            "Absence autorisée / Justifiée",
            "Absence non autorisée (Injustifiée)",
        ],
        horizontal=False,
    )

    quantite = 0.0
    unite = "m²"
    qualite = "-"
    c_rouleaux = 0.0
    c_primaire = 0.0
    c_gaz = 0.0
    c_elastotek = 0.0

    if "Absence" in statut:
      corps_etat = st.selectbox(
          "Motif d'absence",
          [
              "Absence autorisée",
              "CONGÉ",
              "MALADIE",
              "RECUPERATION",
              "Absence injustifiée",
              "Autre",
          ],
      )
    else:
      corps_etat = st.selectbox("🛠️ Corps d'état / Tâche", LISTE_CORPS_ETAT)

      est_bricol_auto = "BRICOL" in corps_etat.upper() or corps_etat in [
          "DIVERS",
          "nettoyage",
          "PONSAGE",
          "décapage",
      ]
      sans_metrage = st.checkbox(
          "🔨 Sans métrage (Bricolage / Forfait jour)", value=est_bricol_auto
      )

      if not sans_metrage:
        c1, c2 = st.columns(2)
        with c1:
          quantite = st.number_input(
              "Production réalisée", min_value=0.0, step=0.5, value=25.0
          )
        with c2:
          unite = st.selectbox("Unité", ["m²", "ml", "Unité"])
      else:
        unite = "Sans métrage"
        quantite = 1.0

      st.markdown("##### 📦 Consommation des Matériaux")
      mc1, mc2 = st.columns(2)
      with mc1:
        c_rouleaux = st.number_input(
            "Rouleaux PAX / Bitume", min_value=0.0, step=0.5, value=0.0
        )
        c_primaire = st.number_input(
            "Primaire / Vernis (L ou Fûts)",
            min_value=0.0,
            step=0.5,
            value=0.0,
        )
      with mc2:
        c_gaz = st.number_input(
            "Gaz (Bouteilles)", min_value=0.0, step=0.25, value=0.0
        )
        c_elastotek = st.number_input(
            "Élastotek (Kg ou Seaux)", min_value=0.0, step=0.5, value=0.0
        )

      qualite = st.select_slider(
          "Qualité / Propreté / Gestion des chutes",
          options=[
              "Élevé (Mauvais)",
              "Moyen (Acceptable)",
              "Faible (Très bien)",
          ],
          value="Faible (Très bien)",
      )

    observation = st.text_input(
        "📝 Remarque / Observation / Stock restant",
        placeholder=(
            "Ex: recouvrement 10 cm respecté, manque chalumeau, etc."
        ),
    )

    btn_valider = st.form_submit_button("Enregistrer la saisie")

    if btn_valider:
      if statut == "Absence autorisée / Justifiée":
        score = None
      elif statut == "Absence non autorisée (Injustifiée)":
        score = 0.0
      else:
        base_presence = 40.0 if statut == "Présent (Travail)" else 20.0
        if unite == "Sans métrage":
          points_prod = 40.0 if statut == "Présent (Travail)" else 20.0
        else:
          if quantite >= 40:
            points_prod = 40.0
          elif quantite >= 25:
            points_prod = 30.0
          elif quantite > 0:
            points_prod = 15.0
          else:
            points_prod = 0.0

        points_qualite = (
            20.0
            if qualite == "Faible (Très bien)"
            else (10.0 if qualite == "Moyen (Acceptable)" else 0.0)
        )
        score = min(base_presence + points_prod + points_qualite, 100.0)

      conn = sqlite3.connect(DB_PATH)
      c = conn.cursor()
      c.execute(
          """
                INSERT INTO rapports_journaliers 
                (date_jour, chantier, worker_id, statut, corps_etat, quantite, unite, conso_rouleaux, conso_primaire, conso_gaz, conso_elastotek, observation, qualite_dechet, score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
          (
              str(date_jour),
              chantier,
              ouvriers_dict[nom_ouvrier],
              statut,
              corps_etat,
              quantite,
              unite,
              c_rouleaux,
              c_primaire,
              c_gaz,
              c_elastotek,
              observation,
              qualite,
              score,
          ),
      )
      conn.commit()
      conn.close()
      st.success(f"Enregistré pour {nom_ouvrier} sur {chantier} !")

# 2. TABLEAU DE BORD
elif onglet == "Tableau de Bord":
  st.subheader("Synthèse de l'Activité & Consommations")
  df_r = get_rapports()

  if df_r.empty:
    st.info("Aucune saisie enregistrée pour le moment.")
  else:
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

    # Synthèse des totaux consommés
    st.markdown("#### 📊 Cumul Matériaux de la sélection")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
      st.metric(
          label="Total Rouleaux",
          value=f"{round(df_affiche['Rouleaux PAX'].sum(), 1)} U",
      )
    with k2:
      st.metric(
          label="Total Primaire",
          value=f"{round(df_affiche['Primaire (L/Fût)'].sum(), 1)}",
      )
    with k3:
      st.metric(
          label="Total Gaz",
          value=f"{round(df_affiche['Gaz (Btl)'].sum(), 1)} Btl",
      )
    with k4:
      st.metric(
          label="Total Élastotek",
          value=f"{round(df_affiche['Élastotek (Kg/Seau)'].sum(), 1)}",
      )

    st.markdown("---")
    st.dataframe(df_affiche, use_container_width=True, hide_index=True)

    csv = df_affiche.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Exporter cette sélection (CSV)",
        data=csv,
        file_name="rapport_consommation_etancheite.csv",
        mime="text/csv",
        use_container_width=True,
    )
