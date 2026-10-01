import os
import sqlite3
from datetime import date
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Pointage Étanchéité",
    page_icon="🏗️️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DB_PATH = os.path.join("/tmp", "chantier_fixe_v12.db")

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

LISTE_TACHES = [
    "PAX",
    "PARE-VAPEUR",
    "SOKLE PARE-VAPEUR",
    "ELASTOTEK",
    "ELASTOTEK GOURGE",
    "ELASTOTEK JOINTAGE",
    "ELASTOTEK LEVI",
    "ELASTOTEK NETTOYAGE",
    "Forme de pente",
    "GOURGE",
    "JOINT DE DILATATION",
    "MASTIC",
    "nettoyage",
    "PONSAGE",
    "BRICOL",
    "BRICOL ELASTOTEK",
    "BRICOL SILICONE",
    "BRICOL SOKLE",
    "BRICOL SOUS CARRELAGE",
    "BRICOL PARE-VAPEUR",
    "DIVERS",
]


def init_database():
  conn = sqlite3.connect(DB_PATH)
  c = conn.cursor()
  # Table ouvriers avec leur chantier d'affectation fixe par défaut
  c.execute("""
        CREATE TABLE IF NOT EXISTS workers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            chantier_fixe TEXT NOT NULL DEFAULT 'CAC-31-24'
        )
    """)
  c.execute("""
        CREATE TABLE IF NOT EXISTS pointages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_jour TEXT,
            chantier TEXT,
            worker_id INTEGER,
            statut TEXT,
            tache TEXT,
            quantite REAL,
            unite TEXT,
            observation TEXT,
            score REAL,
            FOREIGN KEY(worker_id) REFERENCES workers(id)
        )
    """)
  for w in EFFECTIF_GLOBAL:
    c.execute(
        "INSERT OR IGNORE INTO workers (nom, chantier_fixe) VALUES (?, ?)",
        (w, "CAC-31-24"),
    )
  conn.commit()
  conn.close()


init_database()


def get_workers_df():
  conn = sqlite3.connect(DB_PATH)
  df = pd.read_sql_query(
      "SELECT id, nom, chantier_fixe FROM workers ORDER BY nom ASC", conn
  )
  conn.close()
  return df


# --- APPLICATION ---
st.title("🏗️️ Suivi Chantier Étanchéité")
menu = st.radio(
    "Menu",
    [
        "⚡ Pointage Chantier",
        "⚙️ Équipes Fixes",
        "📊 Historique & Synthèse",
    ],
    horizontal=True,
)

# 1. POINTAGE RAPIDE DU CHANTIER
if menu == "⚡ Pointage Chantier":
  st.subheader("Pointage par Chantier")

  col_ch, col_dt = st.columns(2)
  with col_ch:
    chantier_choisi = st.selectbox("📍 Chantier", LISTE_CHANTIERS)
  with col_dt:
    date_choisie = st.date_input("📅 Date", value=date.today())

  df_w = get_workers_df()
  # Ouvriers fixes sur ce chantier
  fixes = df_w[df_w["chantier_fixe"] == chantier_choisi]

  st.markdown(
      f"#### 👷 Équipe fixe habituelle ({len(fixes)} ouvrier(s))"
  )

  if fixes.empty:
    st.warning(
        f"Aucun ouvrier n'est affecté en fixe sur {chantier_choisi}. Rendez-vous"
        " dans l'onglet '⚙️ Équipes Fixes' pour définir l'équipe."
    )
  else:
    with st.form("form_pointage_rapide", clear_on_submit=False):
      etats = {}
      for _, row in fixes.iterrows():
        c_nom, c_statut = st.columns([1.2, 2])
        with c_nom:
          st.write(f"**{row['nom']}**")
        with c_statut:
          etats[row["id"]] = st.selectbox(
              f"Statut {row['nom']}",
              [
                  "Présent (Journée)",
                  "1/2 journée",
                  "Absence Autorisée (Congé/Maladie)",
                  "Absence Non Autorisée (Ghayab)",
              ],
              key=f"st_{row['id']}",
              label_visibility="collapsed",
          )

      st.markdown("---")
      st.markdown("##### 🛠️ Travail réalisé sur le chantier")
      tache = st.selectbox("Tâche principale", LISTE_TACHES)

      est_bricol = "BRICOL" in tache.upper() or tache in [
          "DIVERS",
          "nettoyage",
          "PONSAGE",
      ]
      sans_metrage = st.checkbox(
          "🔨 Bricol / Travail sans métrage", value=est_bricol
      )

      if not sans_metrage:
        cm1, cm2 = st.columns(2)
        with cm1:
          qte = st.number_input(
              "Métrage par ouvrier présent",
              min_value=0.0,
              step=1.0,
              value=25.0,
          )
        with cm2:
          unite = st.selectbox("Unité", ["m²", "ml", "Unité"])
      else:
        qte = 1.0
        unite = "Sans métrage"

      obs = st.text_input(
        "📝 Remarque (terrasse, acrotère, finitions, etc.)",
        placeholder="Optionnel"
      )

      valider = st.form_submit_button(
          "💾 Valider le Pointage du Chantier",
          type="primary",
          use_container_width=True,
      )

      if valider:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        for w_id, st_val in etats.items():
          if "Présent" in st_val:
            pts = 80.0 if sans_metrage or qte >= 25 else 55.0
          elif "1/2" in st_val:
            pts = 40.0
          elif "Autorisée" in st_val:
            pts = None
          else:
            pts = 0.0

          c.execute(
              """
                    INSERT INTO pointages (date_jour, chantier, worker_id, statut, tache, quantite, unite, observation, score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
              (
                  str(date_choisie),
                  chantier_choisi,
                  w_id,
                  st_val,
                  tache,
                  qte if "Présent" in st_val else 0.0,
                  unite,
                  obs,
                  pts,
              ),
          )

        conn.commit()
        conn.close()
        st.success(f"Pointage validé avec succès pour {chantier_choisi} !")

# 2. DEFINITION DES EQUIPES FIXES
elif menu == "⚙️ Équipes Fixes":
  st.subheader("Affectation Fixe des Ouvriers")
  st.caption(
      "Définissez une bonne fois pour toutes sur quel chantier chaque ouvrier"
      " travaille en fixe."
  )

  df_w = get_workers_df()

  with st.form("form_maj_fixes"):
    nouvelles_affectations = {}
    for _, row in df_w.iterrows():
      c1, c2 = st.columns([1.5, 2])
      with c1:
        st.write(f"👷 **{row['nom']}**")
      with c2:
        idx = (
            LISTE_CHANTIERS.index(row["chantier_fixe"])
            if row["chantier_fixe"] in LISTE_CHANTIERS
            else 0
        )
        nouvelles_affectations[row["id"]] = st.selectbox(
            f"Chantier fixe de {row['nom']}",
            LISTE_CHANTIERS,
            index=idx,
            key=f"ch_fix_{row['id']}",
            label_visibility="collapsed",
        )

    btn_sauvegarder = st.form_submit_button(
        "💾 Sauvegarder les affectations fixes",
        type="primary",
        use_container_width=True,
    )

    if btn_sauvegarder:
      conn = sqlite3.connect(DB_PATH)
      c = conn.cursor()
      for w_id, ch_nom in nouvelles_affectations.items():
        c.execute(
            "UPDATE workers SET chantier_fixe = ? WHERE id = ?", (ch_nom, w_id)
        )
      conn.commit()
      conn.close()
      st.success("Affectations fixes enregistrées !")
      st.rerun()

# 3. HISTORIQUE & SYNTHESE
elif menu == "📊 Historique & Synthèse":
  st.subheader("Historique des Saisies")
  conn = sqlite3.connect(DB_PATH)
  query = """
        SELECT 
            p.date_jour AS Date,
            p.chantier AS Chantier,
            w.nom AS Ouvrier,
            p.statut AS Statut,
            p.tache AS Tâche,
            CASE 
                WHEN p.unite = 'Sans métrage' THEN 'Bricol'
                WHEN p.quantite > 0 THEN p.quantite || ' ' || p.unite 
                ELSE '-'
            END AS Production,
            COALESCE(p.observation, '-') AS Observation,
            CASE 
                WHEN p.score IS NULL THEN 'Justifié'
                ELSE CAST(p.score AS TEXT)
            END AS Score
        FROM pointages p
        JOIN workers w ON p.worker_id = w.id
        ORDER BY p.id DESC
    """
  df_hist = pd.read_sql_query(query, conn)
  conn.close()

  if df_hist.empty:
    st.info("Aucun pointage enregistré.")
  else:
    st.dataframe(df_hist, use_container_width=True, hide_index=True)
    csv = df_hist.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Exporter en Excel / CSV",
        data=csv,
        file_name="suivi_chantier_etancheite.csv",
        mime="text/csv",
        use_container_width=True,
    )
