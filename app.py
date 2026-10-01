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

DB_PATH = os.path.join("/tmp", "chantier_tracker_v11.db")

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
            r.corps_etat AS [Corps d'État / Tâche],
            CASE 
                WHEN r.statut LIKE '%Absence autorisée%' THEN 'Excusé'
                WHEN r.statut LIKE '%Injustifiée%' THEN 'Non justifié'
                WHEN r.unite = 'Sans métrage' THEN 'Bricol / Jour'
                WHEN r.quantite > 0 THEN r.quantite || ' ' || r.unite 
                ELSE '-'
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
          "Corps d'État / Tâche",
          "Production",
          "Observation",
          "Qualite",
          "Score",
      ],
  )


# --- APPLICATION ---
st.title("🏗️️ Suivi Chantier Étanchéité")
onglet = st.radio(
    "Menu",
    [
        "📍 Affectation & Chantier",
        "🚫 Absences du Jour",
        "📊 Tableau de Bord",
    ],
    horizontal=True,
)

# 1. POINTAGE PAR CHANTIER (ÉQUIPE RÉELLE SUR CE CHANTIER)
if onglet == "📍 Affectation & Chantier":
  st.subheader("Pointage par Chantier")
  st.caption(
      "Choisissez le chantier et sélectionnez uniquement les ouvriers qui y"
      " travaillent aujourd'hui."
  )

  df_w = get_workers()
  ouvriers_dict = dict(zip(df_w["nom"], df_w["id"]))

  col1, col2 = st.columns(2)
  with col1:
    chantier_sel = st.selectbox("📍 Chantier", LISTE_CHANTIERS)
  with col2:
    date_sel = st.date_input("📅 Date", value=date.today())

  st.markdown("---")

  # Sélection des ouvriers affectés à ce chantier spécifique
  equipe_chantier = st.multiselect(
      f"👷 Équipe affectée à {chantier_sel}",
      options=EFFECTIF_GLOBAL,
      placeholder="Sélectionnez les membres de l'équipe sur ce site...",
  )

  if equipe_chantier:
    st.markdown("##### Détails de l'équipe sélectionnée")
    type_journee = st.radio(
        "Temps de travail de l'équipe",
        ["Journée complète (Présent)", "1/2 journée"],
        horizontal=True,
    )
    tache_commune = st.selectbox("🛠️ Tâche principale", LISTE_CORPS_ETAT)

    avec_metrage = st.checkbox(
        "Saisir un métrage d'équipe",
        value=("BRICOL" not in tache_commune.upper()),
    )
    quantite_indiv = 0.0
    unite = "m²"

    if avec_metrage:
      c1, c2 = st.columns(2)
      with c1:
        quantite_indiv = st.number_input(
            "Métrage par ouvrier (ou total divisé)",
            min_value=0.0,
            step=1.0,
            value=25.0,
        )
      with c2:
        unite = st.selectbox("Unité", ["m²", "ml", "Unité"])
    else:
      unite = "Sans métrage"
      quantite_indiv = 1.0

    qualite = st.select_slider(
        "Finition / Qualité / Déchets",
        options=["Élevé (Mauvais)", "Moyen (Acceptable)", "Faible (Très bien)"],
        value="Faible (Très bien)",
    )
    obs = st.text_input(
        "📝 Remarque (zone de travail, localisation terrasse, etc.)"
    )

    if st.button(
        f"💾 Valider l'équipe ({len(equipe_chantier)} ouvriers) sur"
        f" {chantier_sel}",
        type="primary",
        use_container_width=True,
    ):
      conn = sqlite3.connect(DB_PATH)
      c = conn.cursor()

      base_p = 40.0 if "complète" in type_journee else 20.0
      if unite == "Sans métrage":
        pts_prod = 40.0 if "complète" in type_journee else 20.0
      else:
        if quantite_indiv >= 40:
          pts_prod = 40.0
        elif quantite_indiv >= 25:
          pts_prod = 30.0
        elif quantite_indiv > 0:
          pts_prod = 15.0
        else:
          pts_prod = 0.0

      pts_qual = (
          20.0
          if qualite == "Faible (Très bien)"
          else (10.0 if qualite == "Moyen (Acceptable)" else 0.0)
      )
      score = min(base_p + pts_prod + pts_qual, 100.0)
      statut_val = (
          "Présent (Travail)" if "complète" in type_journee else "1/2 journée"
      )

      for ouv in equipe_chantier:
        w_id = ouvriers_dict[ouv]
        c.execute(
            """
                    INSERT INTO rapports_journaliers 
                    (date_jour, chantier, worker_id, statut, corps_etat, quantite, unite, observation, qualite_dechet, score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
            (
                str(date_sel),
                chantier_sel,
                w_id,
                statut_val,
                tache_commune,
                quantite_indiv,
                unite,
                obs,
                qualite,
                score,
            ),
        )

      conn.commit()
      conn.close()
      st.success(
          f"Enregistré pour {len(equipe_chantier)} ouvriers sur {chantier_sel} !"
      )
  else:
    st.info("Veuillez choisir les ouvriers présents sur ce chantier.")

# 2. ENREGISTREMENT DES ABSENCES (HORS CHANTIER)
elif onglet == "🚫 Absences du Jour":
  st.subheader("Enregistrement des Absences")
  st.caption("Pointer les ouvriers qui n'ont pas travaillé aujourd'hui.")

  df_w = get_workers()
  ouvriers_dict = dict(zip(df_w["nom"], df_w["id"]))

  date_abs = st.date_input("📅 Date de l'absence", value=date.today())

  absents_auto = st.multiselect(
      "🟢 Absences Autorisées (Congé, Maladie, Récupération)",
      options=EFFECTIF_GLOBAL,
  )
  motif_auto = st.selectbox(
      "Motif justifié", ["CONGÉ", "MALADIE", "RECUPERATION", "Absence autorisée"]
  )

  st.write("")
  absents_injust = st.multiselect(
      "🔴 Absences Injustifiées (Ghayab non autorisé)",
      options=[w for w in EFFECTIF_GLOBAL if w not in absents_auto],
  )

  obs_abs = st.text_input("📝 Observation / Détail absence")

  if st.button(
      "💾 Enregistrer les absences", type="primary", use_container_width=True
  ):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    count = 0
    # Autorisées
    for ouv in absents_auto:
      w_id = ouvriers_dict[ouv]
      c.execute(
          """
                INSERT INTO rapports_journaliers 
                (date_jour, chantier, worker_id, statut, corps_etat, quantite, unite, observation, qualite_dechet, score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
          (
              str(date_abs),
              "HORS CHANTIER",
              w_id,
              "Absence autorisée / Justifiée",
              motif_auto,
              0.0,
              "-",
              obs_abs,
              "-",
              None,
          ),
      )
      count += 1

    # Injustifiées
    for ouv in absents_injust:
      w_id = ouvriers_dict[ouv]
      c.execute(
          """
                INSERT INTO rapports_journaliers 
                (date_jour, chantier, worker_id, statut, corps_etat, quantite, unite, observation, qualite_dechet, score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
          (
              str(date_abs),
              "HORS CHANTIER",
              w_id,
              "Absence non autorisée (Injustifiée)",
              "Absence injustifiée",
              0.0,
              "-",
              obs_abs,
              "-",
              0.0,
          ),
      )
      count += 1

    conn.commit()
    conn.close()
    st.success(f"{count} absence(s) enregistrée(s) pour le {str(date_abs)} !")

# 3. TABLEAU DE BORD
elif onglet == "📊 Tableau de Bord":
  st.subheader("Synthèse de l'Activité")
  df_r = get_rapports()

  if df_r.empty:
    st.info("Aucune saisie enregistrée pour le moment.")
  else:
    col_f1, col_f2 = st.columns(2)
    with col_f1:
      filtre_chantier = st.selectbox(
          "Filtrer par Chantier", ["Tous", "HORS CHANTIER"] + LISTE_CHANTIERS
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
        "📥 Exporter les données (CSV)",
        data=csv,
        file_name="rapport_chantiers_etancheite.csv",
        mime="text/csv",
        use_container_width=True,
    )
