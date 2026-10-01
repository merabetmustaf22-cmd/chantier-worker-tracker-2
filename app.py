import os
import sqlite3
from datetime import date
import pandas as pd
import streamlit as st

# Configuration responsive adaptée aux smartphones
st.set_page_config(
    page_title="Suivi Chantier",
    page_icon="🏗️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DB_PATH = os.path.join("/tmp", "chantier_tracker.db")

# Liste de votre effectif global
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
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS workers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            fonction TEXT NOT NULL
        )
    """)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS performances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_id INTEGER,
            date_jour TEXT,
            presence INTEGER,
            quantite REAL,
            unite TEXT,
            qualite_dechet TEXT,
            hse_conforme INTEGER,
            score REAL,
            FOREIGN KEY(worker_id) REFERENCES workers(id)
        )
    """)
  conn.commit()

  # Insertion automatique de l'effectif s'il n'est pas déjà présent
  for ouvrier in EFFECTIF_GLOBAL:
    cursor.execute(
        """
            INSERT OR IGNORE INTO workers (nom, fonction) 
            VALUES (?, ?)
        """,
        (ouvrier, "Applicateur / Équipe Chantier"),
    )
  conn.commit()
  return conn


def get_workers():
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute("SELECT id, nom, fonction FROM workers ORDER BY nom ASC")
  rows = cursor.fetchall()
  conn.close()
  return pd.DataFrame(rows, columns=["id", "nom", "fonction"])


def get_performances():
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute("""
        SELECT 
            p.date_jour AS Date,
            w.nom AS Ouvrier,
            w.fonction AS Fonction,
            p.quantite || ' ' || p.unite AS Rendement,
            p.qualite_dechet AS Qualite,
            p.score AS Score
        FROM performances p
        JOIN workers w ON p.worker_id = w.id
        ORDER BY p.id DESC
    """)
  rows = cursor.fetchall()
  conn.close()
  return pd.DataFrame(
      rows,
      columns=["Date", "Ouvrier", "Fonction", "Rendement", "Qualite", "Score"],
  )


# --- CALCUL DU SCORE (0 à 100) ---
def calculer_score(presence, quantite, qualite, hse):
  if not presence:
    return 0.0

  score = 30.0  # Présence (30 pts)

  # Productivité (max 40 pts)
  if quantite >= 40.0:
    score += 40.0
  elif quantite >= 25.0:
    score += 30.0
  elif quantite > 0.0:
    score += 15.0

  # Qualité / Déchets (max 15 pts)
  if qualite == "Faible (Très bien)":
    score += 15.0
  elif qualite == "Moyen (Acceptable)":
    score += 10.0
  else:
    score += 0.0

  # Respect HSE (max 15 pts)
  if hse:
    score += 15.0

  return min(score, 100.0)


# --- INTERFACE ---
st.title("🏗️ Suivi Chantier")
onglet = st.radio(
    "Navigation",
    ["Saisie du Jour", "Tableau de Bord", "Gestion Ouvriers"],
    horizontal=True,
)

# 1. SAISIE DU JOUR (Par défaut en premier)
if onglet == "Saisie du Jour":
  st.subheader("Pointage & Rendement")
  df_w = get_workers()

  ouvriers_dict = dict(zip(df_w["nom"], df_w["id"]))
  with st.form("form_perf", clear_on_submit=True):
    nom_select = st.selectbox(
        "Sélectionner l'ouvrier", list(ouvriers_dict.keys())
    )
    date_saisie = st.date_input("Date", value=date.today())
    presence = st.toggle("Présent sur chantier", value=True)

    col1, col2 = st.columns(2)
    with col1:
      quantite = st.number_input(
          "Production réalisée", min_value=0.0, step=1.0, value=25.0
      )
    with col2:
      unite = st.selectbox("Unité", ["m²", "ml", "Unité"])

    qualite = st.select_slider(
        "Niveau de chutes / déchets",
        options=["Élevé (Mauvais)", "Moyen (Acceptable)", "Faible (Très bien)"],
        value="Faible (Très bien)",
    )
    hse = st.checkbox("Port complet des EPI (Casque, gants, etc.)", value=True)

    btn_save = st.form_submit_button("Valider la journée")
    if btn_save:
      score_calc = calculer_score(presence, quantite, qualite, hse)
      conn = get_connection()
      cursor = conn.cursor()
      cursor.execute(
          """
                INSERT INTO performances (worker_id, date_jour, presence, quantite, unite, qualite_dechet, hse_conforme, score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
          (
              ouvriers_dict[nom_select],
              str(date_saisie),
              int(presence),
              quantite,
              unite,
              qualite,
              int(hse),
              score_calc,
          ),
      )
      conn.commit()
      conn.close()
      st.success(f"Enregistré ! Score attribué : {score_calc} / 100")

# 2. TABLEAU DE BORD
elif onglet == "Tableau de Bord":
  st.subheader("Performances de l'équipe")
  df_p = get_performances()

  if df_p.empty:
    st.info("Aucune saisie enregistrée pour le moment.")
  else:
    col1, col2 = st.columns(2)
    with col1:
      st.metric(
          label="Score Moyen Équipe",
          value=f"{round(df_p['Score'].mean(), 1)} / 100",
      )
    with col2:
      st.metric(label="Total Saisies", value=len(df_p))

    st.dataframe(df_p, use_container_width=True, hide_index=True)

    csv = df_p.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Exporter les données (CSV)",
        data=csv,
        file_name="suivi_rendement_ouvriers.csv",
        mime="text/csv",
        use_container_width=True,
    )

# 3. GESTION DES OUVRIERS
elif onglet == "Gestion Ouvriers":
  st.subheader("Effectif du Chantier")
  df_w = get_workers()
  st.dataframe(
      df_w[["nom", "fonction"]], use_container_width=True, hide_index=True
  )

  st.divider()
  st.subheader("Ajouter un nouvel ouvrier")
  with st.form("form_worker", clear_on_submit=True):
    nom = st.text_input("Nom & Prénom")
    fonction = st.selectbox(
        "Fonction / Spécialité",
        [
            "Applicateur Étanchéité",
            "Manoeuvre",
            "Chef d'équipe",
            "Maçon",
            "Ferrailleur",
        ],
    )
    btn_ajouter = st.form_submit_button("Enregistrer")
    if btn_ajouter and nom.strip():
      conn = get_connection()
      cursor = conn.cursor()
      cursor.execute(
          "INSERT OR IGNORE INTO workers (nom, fonction) VALUES (?, ?)",
          (nom.strip(), fonction),
      )
      conn.commit()
      conn.close()
      st.success(f"Ouvrier {nom} ajouté !")
      st.rerun()
