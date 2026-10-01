import os
import sqlite3
from datetime import date
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Suivi Chantier Étanchéité",
    page_icon="🏗️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DB_PATH = os.path.join("/tmp", "chantier_tracker_v7.db")

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
            observation TEXT,
            qualite_dechet TEXT,
            score REAL,
            FOREIGN KEY(worker_id) REFERENCES workers(id)
        )
    """)
  c.execute("""
        CREATE TABLE IF NOT EXISTS consommation_soir (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_jour TEXT,
            chantier TEXT,
            rouleaux_pax REAL,
            primaire REAL,
            gaz REAL,
            elastotek REAL,
            remarque TEXT
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
          "Observation",
          "Qualite",
          "Score",
      ],
  )


def get_consommations():
  init_database()
  conn = sqlite3.connect(DB_PATH)
  c = conn.cursor()
  c.execute("""
        SELECT 
            date_jour AS Date,
            chantier AS Chantier,
            rouleaux_pax AS [Rouleaux PAX],
            primaire AS [Primaire (L/Fût)],
            gaz AS [Gaz (Btl)],
            elastotek AS [Élastotek (Kg/Seau)],
            COALESCE(remarque, '-') AS Remarque
        FROM consommation_soir
        ORDER BY id DESC
    """)
  rows = c.fetchall()
  conn.close()
  return pd.DataFrame(
      rows,
      columns=[
          "Date",
          "Chantier",
          "Rouleaux PAX",
          "Primaire (L/Fût)",
          "Gaz (Btl)",
          "Élastotek (Kg/Seau)",
          "Remarque",
      ],
  )


# --- INTERFACE ---
st.title("🏗️ Suivi Chantier & Étanchéité")
onglet = st.radio(
    "Menu",
    [
        "Saisie Ouvrier",
        "Bilan Matériaux (Soir)",
        "Tableau de Bord",
    ],
    horizontal=True,
)

# 1. SAISIE JOURNALIÈRE DES OUVRIERS
if onglet == "Saisie Ouvrier":
  st.subheader("Pointage & Rendement Ouvrier")
  df_w = get_workers()
  ouvriers_dict = dict(zip(df_w["nom"], df_w["id"]))

  with st.form("form_saisie_ouvrier", clear_on_submit=True):
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

      qualite = st.select_slider(
          "Qualité / Propreté / Chutes",
          options=[
              "Élevé (Mauvais)",
              "Moyen (Acceptable)",
              "Faible (Très bien)",
          ],
          value="Faible (Très bien)",
      )

    observation = st.text_input(
        "📝 Remarque / Observation",
        placeholder="Ex: travail en acrotère, retard, etc.",
    )

    btn_valider = st.form_submit_button("Enregistrer la saisie ouvrier")

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
                (date_jour, chantier, worker_id, statut, corps_etat, quantite, unite, observation, qualite_dechet, score)
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
              observation,
              qualite,
              score,
          ),
      )
      conn.commit()
      conn.close()
      st.success(f"Enregistré pour {nom_ouvrier} sur {chantier} !")

# 2. BILAN CONSOMMATION DU SOIR (PAR CHANTIER)
elif onglet == "Bilan Matériaux (Soir)":
  st.subheader("📦 Consommation Journalière du Soir")
  st.caption(
      "Enregistrez ici les quantités totales utilisées sur le chantier durant"
      " la journée."
  )

  with st.form("form_conso_soir", clear_on_submit=True):
    col_c1, col_c2 = st.columns(2)
    with col_c1:
      c_chantier = st.selectbox("📍 Chantier", LISTE_CHANTIERS)
    with col_c2:
      c_date = st.date_input("📅 Date de consommation", value=date.today())

    st.markdown("---")
    m1, m2 = st.columns(2)
    with m1:
      conso_pax = st.number_input(
          "Rouleaux PAX / Bitume posés", min_value=0.0, step=0.5, value=0.0
      )
      conso_prim = st.number_input(
          "Primaire / Vernis (L ou Fûts)", min_value=0.0, step=0.5, value=0.0
      )
    with m2:
      conso_gaz = st.number_input(
          "Gaz brûlé (Bouteilles)", min_value=0.0, step=0.25, value=0.0
      )
      conso_elasto = st.number_input(
          "Élastotek consommé (Kg/Seaux)", min_value=0.0, step=0.5, value=0.0
      )

    c_remarque = st.text_input(
        "📝 Remarque stock (ex: stock restant faible, réapprovisionnement"
        " nécessaire)"
    )

    btn_conso = st.form_submit_button("Enregistrer le bilan matière du soir")
    if btn_conso:
      conn = sqlite3.connect(DB_PATH)
      c = conn.cursor()
      c.execute(
          """
                INSERT INTO consommation_soir 
                (date_jour, chantier, rouleaux_pax, primaire, gaz, elastotek, remarque)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
          (
              str(c_date),
              c_chantier,
              conso_pax,
              conso_prim,
              conso_gaz,
              conso_elasto,
              c_remarque,
          ),
      )
      conn.commit()
      conn.close()
      st.success(
          f"Bilan matériaux enregistré pour {c_chantier} le {str(c_date)} !"
      )

# 3. TABLEAU DE BORD GLOBAL
elif onglet == "Tableau de Bord":
  st.subheader("Synthèse Globale du Chantier")
  df_r = get_rapports()
  df_c = get_consommations()

  filtre_chantier = st.selectbox(
      "Filtrer par Chantier", ["Tous"] + LISTE_CHANTIERS
  )

  df_affiche_r = df_r.copy()
  df_affiche_c = df_c.copy()

  if filtre_chantier != "Tous":
    if not df_affiche_r.empty:
      df_affiche_r = df_affiche_r[df_affiche_r["Chantier"] == filtre_chantier]
    if not df_affiche_c.empty:
      df_affiche_c = df_affiche_c[df_affiche_c["Chantier"] == filtre_chantier]

  # Cartes des consommations enregistrées le soir
  st.markdown("#### 📦 Matériaux consommés (Bilan du soir)")
  if not df_affiche_c.empty:
    k1, k2, k3, k4 = st.columns(4)
    with k1:
      st.metric(
          label="Rouleaux PAX",
          value=f"{round(df_affiche_c['Rouleaux PAX'].sum(), 1)} U",
      )
    with k2:
      st.metric(
          label="Primaire",
          value=f"{round(df_affiche_c['Primaire (L/Fût)'].sum(), 1)}",
      )
    with k3:
      st.metric(
          label="Gaz", value=f"{round(df_affiche_c['Gaz (Btl)'].sum(), 1)} Btl"
      )
    with k4:
      st.metric(
          label="Élastotek",
          value=f"{round(df_affiche_c['Élastotek (Kg/Seau)'].sum(), 1)}",
      )
  else:
    st.info("Aucun bilan matière du soir enregistré pour cette sélection.")

  st.markdown("---")
  st.markdown("#### 👷 Suivi des Ouvriers & Rendements")
  if not df_affiche_r.empty:
    st.dataframe(df_affiche_r, use_container_width=True, hide_index=True)
  else:
    st.info("Aucune saisie ouvrier enregistrée pour cette sélection.")
