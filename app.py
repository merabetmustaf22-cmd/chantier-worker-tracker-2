import os
import sqlite3
from datetime import date
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Suivi Chantier & Évaluation",
    page_icon="🏗️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DB_PATH = os.path.join("/tmp", "chantier_eval_v14.db")

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
            tache TEXT,
            quantite REAL,
            unite TEXT,
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


# --- INTERFACE ---
st.title("🏗️ Suivi Chantier Étanchéité")
menu = st.radio(
    "Menu",
    [
        "⚡ Saisie Chantier",
        "⚙️ Équipes Fixes",
        "📊 Historique & Synthèse",
    ],
    horizontal=True,
)

# 1. SAISIE DU CHANTIER
if menu == "⚡ Saisie Chantier":
  st.subheader("Pointage, Tâches & Évaluation")

  col_ch, col_dt = st.columns(2)
  with col_ch:
    chantier_choisi = st.selectbox("📍 Chantier", LISTE_CHANTIERS)
  with col_dt:
    date_choisie = st.date_input("📅 Date", value=date.today())

  df_w = get_workers_df()
  fixes = df_w[df_w["chantier_fixe"] == chantier_choisi]

  st.markdown(f"#### 👷 Équipe affectée ({len(fixes)} ouvriers)")

  if fixes.empty:
    st.warning(
        f"Makach ouvriers rattachés l {chantier_choisi}. Roh l l'onglet '⚙️"
        " Équipes Fixes'."
    )
  else:
    with st.form("form_pointage_individuel", clear_on_submit=False):
      donnees_ouvriers = {}

      for _, row in fixes.iterrows():
        w_id = row["id"]
        w_nom = row["nom"]

        st.markdown(f"**👷 {w_nom}**")
        c_st, c_tch, c_rend = st.columns([1.2, 1.4, 1.4])

        with c_st:
          st_val = st.selectbox(
              f"Statut {w_nom}",
              [
                  "Présent (Journée)",
                  "1/2 journée",
                  "Absence Autorisée (Congé/Maladie)",
                  "Absence Non Autorisée (Ghayab)",
              ],
              key=f"st_{w_id}",
              label_visibility="collapsed",
          )

        with c_tch:
          tache_val = st.selectbox(
              f"Tâche {w_nom}",
              LISTE_TACHES,
              key=f"tch_{w_id}",
              label_visibility="collapsed",
          )

        with c_rend:
          type_travail = st.selectbox(
              f"Type {w_nom}",
              ["Métrage (m² / ml)", "Bricol / Sans métrage"],
              key=f"type_{w_id}",
              label_visibility="collapsed",
          )

        qte_val = 0.0
        unite_val = "m²"
        obs_val = ""
        apprec_val = "-"

        if "Présent" in st_val or "1/2" in st_val:
          sub_c1, sub_c2, sub_c3 = st.columns([1.5, 1.5, 2])
          with sub_c1:
            if type_travail == "Métrage (m² / ml)":
              qte_val = st.number_input(
                  f"Métrage ({w_nom})",
                  min_value=0.0,
                  step=1.0,
                  value=25.0,
                  key=f"qte_{w_id}",
              )
            else:
              unite_val = "Sans métrage"
              qte_val = 1.0
          with sub_c2:
            apprec_val = st.selectbox(
                f"Khdmtou ({w_nom})",
                [
                    "🟢 Mlih bzzaf",
                    "🟡 Moyen",
                    "🔴 Na9es (3ayan)",
                ],
                key=f"app_{w_id}",
            )
          with sub_c3:
            obs_val = st.text_input(
                f"Remarque ({w_nom})",
                placeholder="Ex: terrasse, finitions, regard...",
                key=f"obs_{w_id}",
            )

        st.markdown("<hr style='margin:6px 0;'>", unsafe_allow_html=True)

        donnees_ouvriers[w_id] = {
            "statut": st_val,
            "tache": (
                tache_val if ("Présent" in st_val or "1/2" in st_val) else "-"
            ),
            "quantite": qte_val,
            "unite": unite_val,
            "appreciation": apprec_val,
            "observation": obs_val,
        }

      btn_valider = st.form_submit_button(
          "💾 Valider la journée de l'équipe",
          type="primary",
          use_container_width=True,
      )

      if btn_valider:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        for w_id, d in donnees_ouvriers.items():
          st_val = d["statut"]
          qte = d["quantite"]
          unite = d["unite"]
          app = d["appreciation"]

          # Calcul score souple
          if "Présent" in st_val:
            base_p = 40.0
            pts_prod = (
                40.0
                if (unite == "Sans métrage" or qte >= 30)
                else (30.0 if qte >= 20 else 15.0)
            )
            pts_app = (
                20.0
                if "Mlih" in app
                else (10.0 if "Moyen" in app else (0.0 if "Na9es" in app else 10.0))
            )
            score = min(base_p + pts_prod + pts_app, 100.0)
          elif "1/2" in st_val:
            score = 35.0
          elif "Autorisée" in st_val:
            score = None
          else:
            score = 0.0

          c.execute(
              """
                    INSERT INTO pointages (date_jour, chantier, worker_id, statut, tache, quantite, unite, appreciation, observation, score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
              (
                  str(date_choisie),
                  chantier_choisi,
                  w_id,
                  st_val,
                  d["tache"],
                  qte,
                  unite,
                  app,
                  d["observation"],
                  score,
              ),
          )

        conn.commit()
        conn.close()
        st.success(f"Journée validée pour {chantier_choisi} !")

# 2. DEFINITION DES EQUIPES FIXES
elif menu == "⚙️ Équipes Fixes":
  st.subheader("Affectation Fixe des Ouvriers")
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
            f"Chantier de {row['nom']}",
            LISTE_CHANTIERS,
            index=idx,
            key=f"ch_fix_{row['id']}",
            label_visibility="collapsed",
        )

    btn_sauvegarder = st.form_submit_button(
        "💾 Sauvegarder les affectations",
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
      st.success("Affectations enregistrées !")
      st.rerun()

# 3. HISTORIQUE & SYNTHESE
elif menu == "📊 Historique & Synthèse":
  st.subheader("Historique des Saisies & Évaluation")
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
            COALESCE(p.appreciation, '-') AS [Avis Khdma],
            COALESCE(p.observation, '-') AS Remarque,
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
    st.info("Aucune donnée enregistrée.")
  else:
    st.dataframe(df_hist, use_container_width=True, hide_index=True)
    csv = df_hist.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Exporter (CSV)",
        data=csv,
        file_name="suivi_chantier_etancheite.csv",
        mime="text/csv",
        use_container_width=True,
    )
