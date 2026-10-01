from datetime import date
import sqlite3
import pandas as pd
import streamlit as st

# Configuration responsive adaptée aux smartphones
st.set_page_config(
    page_title="Suivi Chantier & Ouvriers",
    page_icon="🏗️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- BASE DE DONNÉES SQLITE ---
conn = sqlite3.connect("chantier_tracker.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS workers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
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


# --- CALCUL DU SCORE (0 à 100) ---
def calculer_score(presence, quantite, qualite, hse):
  if not presence:
    return 0.0

  score = 30.0  # Présence validée (30 pts)

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

  # Respect HSE / EPI (max 15 pts)
  if hse:
    score += 15.0

  return min(score, 100.0)


# --- INTERFACE UTILISATEUR ---
st.title("🏗️ Suivi Chantier")
onglet = st.radio(
    "Navigation",
    ["Saisie du Jour", "Tableau de Bord", "Gestion Ouvriers"],
    horizontal=True,
)

# 1. GESTION DES OUVRIERS
if onglet == "Gestion Ouvriers":
  st.subheader("Ajouter un ouvrier")
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
    if btn_ajouter and nom:
      cursor.execute(
          "INSERT INTO workers (nom, fonction) VALUES (?, ?)", (nom, fonction)
      )
      conn.commit()
      st.success(f"Ouvrier {nom} ajouté avec succès !")

  st.divider()
  st.subheader("Liste de l'équipe")
  df_workers = pd.read_sql_query(
      "SELECT id, nom, fonction FROM workers", conn
  )
  st.dataframe(df_workers, use_container_width=True, hide_index=True)

# 2. SAISIE JOURNALIÈRE
elif onglet == "Saisie du Jour":
  st.subheader("Pointage & Rendement")
  df_workers = pd.read_sql_query("SELECT id, nom FROM workers", conn)

  if df_workers.empty:
    st.warning(
        "Veuillez d'abord ajouter des ouvriers dans l'onglet 'Gestion"
        " Ouvriers'."
    )
  else:
    ouvriers_dict = dict(zip(df_workers["nom"], df_workers["id"]))
    with st.form("form_perf", clear_on_submit=True):
      nom_select = st.selectbox("Sélectionner l'ouvrier", list(ouvriers_dict.keys()))
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
          options=[
              "Élevé (Mauvais)",
              "Moyen (Acceptable)",
              "Faible (Très bien)",
          ],
          value="Faible (Très bien)",
      )
      hse = st.checkbox("Port complet des EPI (Casque, gants, etc.)", value=True)

      btn_save = st.form_submit_button("Valider la journée")
      if btn_save:
        score_final = calculer_score(presence, quantite, qualite, hse)
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
                score_final,
            ),
        )
        conn.commit()
        st.success(f"Enregistré ! Score attribué : {score_final} / 100")

# 3. TABLEAU DE BORD
elif onglet == "Tableau de Bord":
  st.subheader("Performances de l'équipe")
  query = """
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
  """
  df_result = pd.read_sql_query(query, conn)

  if df_result.empty:
    st.info("Aucune donnée enregistrée pour le moment.")
  else:
    col1, col2 = st.columns(2)
    with col1:
      st.metric(
          label="Score Moyen Équipe",
          value=f"{round(df_result['Score'].mean(), 1)} / 100",
      )
    with col2:
      st.metric(label="Total Saisies", value=len(df_result))

    st.dataframe(df_result, use_container_width=True, hide_index=True)

    # Export Excel / CSV pour les rapports
    csv = df_result.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Exporter les données (CSV)",
        data=csv,
        file_name="suivi_rendement_ouvriers.csv",
        mime="text/csv",
        use_container_width=True,
    )
