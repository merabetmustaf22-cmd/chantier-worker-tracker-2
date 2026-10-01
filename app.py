import os
import sqlite3
from datetime import date
import pandas as pd
from PIL import Image
import streamlit as st

st.set_page_config(
    page_title="Suivi de Chantier & Étanchéité",
    page_icon="🏗️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DB_PATH = os.path.join("/tmp", "chantier_photos_v24.db")
PHOTOS_DIR = "photos"
os.makedirs(PHOTOS_DIR, exist_ok=True)

ADMIN_PASSWORD = "admin"

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


def get_photo_path(nom_ouvrier):
  nom_clean = nom_ouvrier.replace(" ", "_")
  for ext in [".jpg", ".jpeg", ".png"]:
    p = os.path.join(PHOTOS_DIR, f"{nom_clean}{ext}")
    if os.path.exists(p):
      return p
  return None


# --- STRUCTURE PRINCIPALE ---
st.title("🏗️ Suivi de Chantier & Étanchéité")

menu_general = st.radio(
    "Navigation",
    ["⚡ Saisie du Jour (Chantier)", "🔐 Panneau d'Administration"],
    horizontal=True,
)

# ==============================================================================
# 1. ESPACE TERRAIN : SAISIE DU JOUR
# ==============================================================================
if menu_general == "⚡ Saisie du Jour (Chantier)":
  st.subheader("Pointage & Rendement Journalier")

  col_ch, col_dt = st.columns(2)
  with col_ch:
    chantier_choisi = st.selectbox("📍 Chantier", LISTE_CHANTIERS)
  with col_dt:
    date_choisie = st.date_input("📅 Date", value=date.today())

  df_w = get_workers_df()
  fixes = df_w[df_w["chantier_fixe"] == chantier_choisi]

  # Module de renfort ponctuel : ajouter un ouvrier d'un autre chantier pour la journée
  ouvriers_autres = df_w[df_w["chantier_fixe"] != chantier_choisi][
      "nom"
  ].tolist()
  with st.expander("🔄 Ajouter un renfort venu d'un autre chantier pour aujourd'hui"):
    ouvriers_renforts = st.multiselect(
        "Sélectionner l'ouvrier à intégrer temporairement sur ce site",
        options=ouvriers_autres,
        placeholder="Choisir un ouvrier en renfort...",
    )

  # Liste combinée : Équipe fixe + Renforts sélectionnés
  df_renforts = df_w[df_w["nom"].isin(ouvriers_renforts)]
  equipe_active = pd.concat([fixes, df_renforts]).drop_duplicates(subset=["id"])

  st.markdown(
      f"#### 👷 Équipe présente sur le site ({len(equipe_active)} ouvrier(s))"
  )

  if equipe_active.empty:
    st.warning(
        f"Aucun ouvrier rattaché au chantier {chantier_choisi}. Ajoutez un"
        " renfort ci-dessus ou configurez l'équipe dans le Panneau Admin."
    )
  else:
    donnees_ouvriers = {}

    for _, row in equipe_active.iterrows():
      w_id = row["id"]
      w_nom = row["nom"]
      photo_p = get_photo_path(w_nom)
      est_renfort = row["chantier_fixe"] != chantier_choisi

      col_av, col_tx = st.columns([1, 4])
      with col_av:
        if photo_p:
          st.image(photo_p, width=65)
        else:
          st.markdown(
              "<div"
              " style='font-size:42px;line-height:65px;text-align:center;'>👷</div>",
              unsafe_allow_html=True,
          )
      with col_tx:
        tag_renfort = " *(Renfort temporaire)*" if est_renfort else ""
        st.markdown(f"### {w_nom}{tag_renfort}")

      st_val = st.selectbox(
          "Statut de présence",
          [
              "Présent (Journée)",
              "1/2 journée",
              "Absence Autorisée (Congé/Maladie)",
              "Absence Non Autorisée (Injustifiée)",
          ],
          key=f"st_{w_id}",
      )

      tache_val = "-"
      qte_val = 0.0
      unite_val = "-"
      apprec_val = "-"
      obs_val = ""

      if "Présent" in st_val or "1/2" in st_val:
        col_t1, col_t2 = st.columns(2)
        with col_t1:
          tache_val = st.selectbox(
              "Tâche effectuée", LISTE_TACHES, key=f"tch_{w_id}"
          )
        with col_t2:
          est_bricol_defaut = "BRICOL" in tache_val.upper() or tache_val in [
              "DIVERS",
              "nettoyage",
              "PONSAGE",
          ]
          type_travail = st.selectbox(
              "Type d'activité",
              ["Métrage (m² / ml)", "Bricol / Sans métrage"],
              index=1 if est_bricol_defaut else 0,
              key=f"typ_{w_id}",
          )

        if type_travail == "Métrage (m² / ml)":
          col_r1, col_r2, col_r3 = st.columns([1.5, 1.5, 2])
          with col_r1:
            qte_val = st.number_input(
                "Production réalisée",
                min_value=0.0,
                step=1.0,
                value=25.0,
                key=f"qte_{w_id}",
            )
            unite_val = "m²"
          with col_r2:
            apprec_val = st.selectbox(
                "Qualité d'exécution",
                [
                    "🟢 Conforme / Soigné",
                    "🟡 Moyen / Acceptable",
                    "🔴 Non conforme / À reprendre",
                ],
                key=f"app_{w_id}",
            )
          with col_r3:
            obs_val = st.text_input(
                "Observation libre",
                placeholder="Ex: terrasse sud, relevés...",
                key=f"obs_{w_id}",
            )
        else:
          unite_val = "Sans métrage"
          qte_val = 1.0
          col_b1, col_b2 = st.columns([1.5, 2.5])
          with col_b1:
            apprec_val = st.selectbox(
                "Qualité d'exécution",
                [
                    "🟢 Conforme / Soigné",
                    "🟡 Moyen / Acceptable",
                    "🔴 Non conforme / À reprendre",
                ],
                key=f"app_br_{w_id}",
            )
          with col_b2:
            obs_val = st.text_input(
                "Détail du bricolage",
                placeholder="Ex: étanchéité acrotère, regard, finitions...",
                key=f"obs_br_{w_id}",
            )
      else:
        obs_val = st.text_input(
            "Motif / Observation de l'absence",
            placeholder="Ex: congé, maladie, absence injustifiée...",
            key=f"obs_abs_{w_id}",
        )

      st.markdown("---")

      donnees_ouvriers[w_id] = {
          "statut": st_val,
          "tache": tache_val,
          "quantite": qte_val,
          "unite": unite_val,
          "appreciation": apprec_val,
          "observation": obs_val,
      }

    if st.button(
        "💾 Valider la journée de l'équipe",
        type="primary",
        use_container_width=True,
    ):
      conn = sqlite3.connect(DB_PATH)
      c = conn.cursor()

      for w_id, d in donnees_ouvriers.items():
        st_val = d["statut"]
        qte = d["quantite"]
        unite = d["unite"]
        app = d["appreciation"]

        if "Présent" in st_val:
          base_p = 40.0
          pts_prod = (
              40.0
              if (unite == "Sans métrage" or qte >= 30)
              else (30.0 if qte >= 20 else 15.0)
          )
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
      st.success(
          f"Pointage et rendements enregistrés avec succès pour"
          f" {chantier_choisi} !"
      )

# ==============================================================================
# 2. ESPACE ADMINISTRATION
# ==============================================================================
elif menu_general == "🔐 Panneau d'Administration":
  st.subheader("Accès Sécurisé Administration")

  if "admin_logged_in" not in st.session_state:
    st.session_state["admin_logged_in"] = False

  if not st.session_state["admin_logged_in"]:
    col_p1, col_p2 = st.columns([2, 1])
    with col_p1:
      mdp = st.text_input(
          "Code d'accès administrateur",
          type="password",
          placeholder="Entrez le mot de passe...",
      )
    with col_p2:
      st.write("")
      st.write("")
      if st.button("Connexion", type="primary", use_container_width=True):
        if mdp == ADMIN_PASSWORD:
          st.session_state["admin_logged_in"] = True
          st.rerun()
        else:
          st.error("Mot de passe incorrect.")
  else:
    st.sidebar.button(
        "Déconnexion Admin",
        on_click=lambda: st.session_state.update({"admin_logged_in": False}),
    )

    sous_menu_admin = st.selectbox(
        "Module Administrateur",
        [
            "⚙️ Modifier l'Affectation d'un Ouvrier",
            "📋 Vue d'ensemble de toutes les Affectations",
            "👤 Profils & Gestion des Photos",
            "📊 Historique des Saisies & Exportation",
        ],
    )

    st.markdown("---")

    # 1. MODIFICATION RAPIDE PAR OUVRIER UNIQUE
    if sous_menu_admin == "⚙️ Modifier l'Affectation d'un Ouvrier":
      st.markdown("#### Transfert ou Réaffectation d'un Ouvrier")
      df_w = get_workers_df()

      ouvrier_a_changer = st.selectbox(
          "Choisir l'ouvrier à transférer", df_w["nom"].tolist()
      )
      infos_actuelles = df_w[df_w["nom"] == ouvrier_a_changer].iloc[0]
      chantier_actuel = infos_actuelles["chantier_fixe"]
      ouvrier_id = infos_actuelles["id"]

      st.info(
          f"Chantier actuel de **{ouvrier_a_changer}** : **{chantier_actuel}**"
      )

      nouveau_chantier = st.selectbox(
          "Nouveau chantier d'affectation fixe",
          [c for c in LISTE_CHANTIERS if c != chantier_actuel],
      )

      if st.button(
          f"Confirmer le transfert vers {nouveau_chantier}",
          type="primary",
          use_container_width=True,
      ):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "UPDATE workers SET chantier_fixe = ? WHERE id = ?",
            (nouveau_chantier, ouvrier_id),
        )
        conn.commit()
        conn.close()
        st.success(
            f"{ouvrier_a_changer} est désormais affecté à {nouveau_chantier} !"
        )
        st.rerun()

    # 2. VUE D'ENSEMBLE ET MODIFICATION GLOBALE
    elif (
        sous_menu_admin == "📋 Vue d'ensemble de toutes les Affectations"
    ):
      st.markdown("#### Tableau Général des Affectations")
      df_w = get_workers_df()

      with st.form("form_maj_fixes_admin"):
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
                key=f"ch_fix_adm_{row['id']}",
                label_visibility="collapsed",
            )

        if st.form_submit_button(
            "💾 Sauvegarder toutes les affectations",
            type="primary",
            use_container_width=True,
        ):
          conn = sqlite3.connect(DB_PATH)
          c = conn.cursor()
          for w_id, ch_nom in nouvelles_affectations.items():
            c.execute(
                "UPDATE workers SET chantier_fixe = ? WHERE id = ?",
                (ch_nom, w_id),
            )
          conn.commit()
          conn.close()
          st.success("Toutes les affectations ont été mises à jour !")
          st.rerun()

    # 3. GESTION DES PHOTOS
    elif sous_menu_admin == "👤 Profils & Gestion des Photos":
      st.markdown("#### Gestion des Portraits des Ouvriers")
      ouvrier_photo = st.selectbox(
          "Sélectionner l'ouvrier", EFFECTIF_GLOBAL, key="sel_ouv_photo"
      )
      photo_actuelle = get_photo_path(ouvrier_photo)

      col_view, col_upload = st.columns([1, 2])
      with col_view:
        if photo_actuelle:
          st.image(photo_actuelle, caption="Photo actuelle", width=140)
        else:
          st.info("Aucune photo enregistrée.")

      with col_upload:
        fichier_photo = st.file_uploader(
            "Télécharger une photo (Galerie ou Fichier)",
            type=["jpg", "jpeg", "png"],
            key="upload_worker_photo_adm",
        )
        if fichier_photo is not None:
          image_obj = Image.open(fichier_photo)
          ext = fichier_photo.name.split(".")[-1].lower()
          nom_fichier = f"{ouvrier_photo.replace(' ', '_')}.{ext}"
          chemin_save = os.path.join(PHOTOS_DIR, nom_fichier)
          image_obj.save(chemin_save)
          st.success(f"Photo enregistrée pour {ouvrier_photo} !")
          st.rerun()

    # 4. HISTORIQUE & SYNTHESE
    elif (
        sous_menu_admin == "📊 Historique des Saisies & Exportation"
    ):
      st.markdown("#### Registre des Pointages & Rendements")
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
                END AS [Production],
                COALESCE(p.appreciation, '-') AS [Qualité],
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
        st.info("Aucune saisie enregistrée pour l'instant.")
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
