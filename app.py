import os
import sqlite3
from datetime import date
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Suivi de Chantier & Étanchéité",
    page_icon="🏗️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DB_PATH = os.path.join("/tmp", "chantier_equipe_globale_v17.db")

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
            tache_globale TEXT,
            metrage_global REAL,
            unite_globale TEXT,
            appreciation TEXT,
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
st.title("🏗️ Suivi de Chantier & Étanchéité")
menu = st.radio(
    "Navigation",
    [
        "⚡ Saisie Chantier",
        "⚙️ Affectations Fixes",
        "📊 Historique & Synthèse",
    ],
    horizontal=True,
)

# 1. SAISIE DU CHANTIER
if menu == "⚡ Saisie Chantier":
  st.subheader("Pointage de l'Équipe & Production Globale")

  col_ch, col_dt = st.columns(2)
  with col_ch:
    chantier_choisi = st.selectbox("📍 Chantier", LISTE_CHANTIERS)
  with col_dt:
    date_choisie = st.date_input("📅 Date", value=date.today())

  df_w = get_workers_df()
  fixes = df_w[df_w["chantier_fixe"] == chantier_choisi]

  if fixes.empty:
    st.warning(
        f"Aucun ouvrier rattaché au chantier {chantier_choisi}. Rendez-vous"
        " dans l'onglet '⚙️ Affectations Fixes'."
    )
  else:
    with st.form("form_pointage_global", clear_on_submit=False):
      st.markdown("#### 📦 Production globale du chantier")

      c_tch, c_typ = st.columns(2)
      with c_tch:
        tache_globale = st.selectbox("Tâche réalisée", LISTE_TACHES)
      with c_typ:
        type_travail = st.selectbox(
            "Type d'activité", ["Métrage global", "Bricol / Sans métrage"]
        )

      metrage_total = 0.0
      unite_globale = "m²"

      if type_travail == "Métrage global":
        cq1, cq2 = st.columns(2)
        with cq1:
          metrage_total = st.number_input(
              "Métrage total réalisé par l'équipe",
              min_value=0.0,
              step=5.0,
              value=100.0,
          )
        with cq2:
          unite_globale = st.selectbox("Unité", ["m²", "ml", "Unité"])
      else:
        unite_globale = "Sans métrage"
        metrage_total = 1.0

      obs_chantier = st.text_input(
          "📝 Observation globale du chantier",
          placeholder="Ex: terrasse sud, détails techniques, intempéries...",
      )

      st.markdown("---")
      st.markdown(f"#### 👷 Pointage individuel ({len(fixes)} ouvriers)")

      donnees_ouvriers = {}
      for _, row in fixes.iterrows():
        w_id = row["id"]
        w_nom = row["nom"]

        c_nom, c_st, c_app = st.columns([1.5, 1.5, 1.5])
        with c_nom:
          st.write(f"👷 **{w_nom}**")
        with c_st:
          st_val = st.selectbox(
              "Statut",
              [
                  "Présent (Journée)",
                  "1/2 journée",
                  "Absence Autorisée (Congé/Maladie)",
                  "Absence Non Autorisée (Injustifiée)",
              ],
              key=f"st_{w_id}",
              label_visibility="collapsed",
          )
        with c_app:
          if "Présent" in st_val or "1/2" in st_val:
            app_val = st.selectbox(
                "Qualité d'exécution",
                [
                    "🟢 Conforme / Soigné",
                    "🟡 Moyen / Acceptable",
                    "🔴 Non conforme / À reprendre",
                ],
                key=f"app_{w_id}",
                label_visibility="collapsed",
            )
          else:
            app_val = "-"
            st.caption("Absent")

        donnees_ouvriers[w_id] = {
            "statut": st_val,
            "appreciation": app_val,
        }

      btn_valider = st.form_submit_button(
          "💾 Valider la journée du chantier",
          type="primary",
          use_container_width=True,
      )

      if btn_valider:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        for w_id, d in donnees_ouvriers.items():
          st_val = d["statut"]
          app = d["appreciation"]

          if "Présent" in st_val:
            base_p = 40.0
            pts_prod = 40.0
            pts_app = (
                20.0
                if "Conforme" in app
                else (
                    10.0
                    if "Moyen" in app
                    else (0.0 if "Non conforme" in app else 10.0)
                )
            )
            score = min(base_p + pts_prod + pts_app, 100.0)
          elif "1/2" in st_val:
            score = 40.0
          elif "Autorisée" in st_val:
            score = None
          else:
            score = 0.0

          c.execute(
              """
                    INSERT INTO pointages (date_jour, chantier, worker_id, statut, tache_globale, metrage_global, unite_globale, appreciation, observation, score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
              (
                  str(date_choisie),
                  chantier_choisi,
                  w_id,
                  st_val,
                  tache_globale,
                  metrage_total,
                  unite_globale,
                  app,
                  obs_chantier,
                  score,
              ),
          )

        conn.commit()
        conn.close()
        st.success(
            f"Journée validée pour {chantier_choisi} avec {metrage_total}"
            f" {unite_globale} !"
        )

# 2. DEFINITION DES EQUIPES FIXES
elif menu == "⚙️ Affectations Fixes":
  st.subheader("Affectation Fixe des Ouvriers par Chantier")
  st.caption(
      "Définissez l'affectation standard de chaque ouvrier afin d'afficher"
      " automatiquement l'équipe correspondante lors de la saisie."
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
            "Chantier fixe",
            LISTE_CHANTIERS,
            index=idx,
            key=f"ch_fix_{row['id']}",
            label_visibility="collapsed",
        )

    btn_sauvegarder = st.form_submit_button(
        "💾 Enregistrer les affectations",
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
      st.success("Affectations fixes enregistrées avec succès !")
      st.rerun()

# 3. HISTORIQUE & SYNTHESE
elif menu == "📊 Historique & Synthèse":
  st.subheader("Historique des Saisies & Évaluations")
  conn = sqlite3.connect(DB_PATH)
  query = """
        SELECT 
            p.date_jour AS Date,
            p.chantier AS Chantier,
            w.nom AS Ouvrier,
            p.statut AS Statut,
            p.tache_globale AS Tâche,
            CASE 
                WHEN p.unite_globale = 'Sans métrage' THEN 'Bricol'
                WHEN p.metrage_global > 0 THEN p.metrage_global || ' ' || p.unite_globale 
                ELSE '-'
            END AS [Production Chantier],
            COALESCE(p.appreciation, '-') AS [Qualité / Appréciation],
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
    st.info("Aucune donnée enregistrée pour le moment.")
  else:
    st.dataframe(df_hist, use_container_width=True, hide_index=True)
    csv = df_hist.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Exporter les données (CSV)",
        data=csv,
        file_name="suivi_chantier_etancheite.csv",
        mime="text/csv",
        use_container_width=True,
    )
      
