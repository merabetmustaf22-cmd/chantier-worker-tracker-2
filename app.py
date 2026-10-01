import os
import sqlite3
from datetime import date, datetime
import pandas as pd
from PIL import Image
import streamlit as st

st.set_page_config(
    page_title="Suivi de Chantier & Étanchéité",
    page_icon="🏗️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DB_PATH = "chantier_roles_v39.db"
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
    "EN ATTENTE / DEPOT",
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

EFFECTIF_GLOBAL_INIT = [
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


def get_db_connection():
  return sqlite3.connect(DB_PATH, timeout=10)


def init_database():
  conn = get_db_connection()
  c = conn.cursor()
  c.execute("""
        CREATE TABLE IF NOT EXISTS workers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            chantier_fixe TEXT NOT NULL DEFAULT 'CAC-31-24'
        )
    """)
  c.execute("""
        CREATE TABLE IF NOT EXISTS conducteurs_meta (
            tag TEXT PRIMARY KEY,
            nom_affiche TEXT NOT NULL
        )
    """)
  c.execute("""
        CREATE TABLE IF NOT EXISTS conducteur_chantiers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conducteur_tag TEXT NOT NULL,
            chantier TEXT NOT NULL,
            UNIQUE(conducteur_tag, chantier)
        )
    """)
  c.execute("""
        CREATE TABLE IF NOT EXISTS pointages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_jour TEXT NOT NULL,
            chantier TEXT NOT NULL,
            conducteur TEXT NOT NULL DEFAULT 'Conducteur',
            worker_id INTEGER NOT NULL,
            statut TEXT,
            tache TEXT,
            quantite REAL,
            unite TEXT,
            appreciation TEXT,
            observation TEXT,
            score REAL,
            UNIQUE(date_jour, chantier, worker_id),
            FOREIGN KEY(worker_id) REFERENCES workers(id)
        )
    """)
  c.execute(
      "INSERT OR IGNORE INTO conducteurs_meta (tag, nom_affiche) VALUES ('c1',"
      " 'Conducteur 1')"
  )
  c.execute(
      "INSERT OR IGNORE INTO conducteurs_meta (tag, nom_affiche) VALUES ('c2',"
      " 'Conducteur 2')"
  )

  for w in EFFECTIF_GLOBAL_INIT:
    c.execute(
        "INSERT OR IGNORE INTO workers (nom, chantier_fixe) VALUES (?, ?)",
        (w, "CAC-31-24"),
    )
  conn.commit()
  conn.close()


init_database()


def get_conducteurs_dict():
  conn = get_db_connection()
  c = conn.cursor()
  c.execute("SELECT tag, nom_affiche FROM conducteurs_meta")
  res = {row[0]: row[1] for row in c.fetchall()}
  conn.close()
  return res


def get_workers_df():
  conn = get_db_connection()
  df = pd.read_sql_query(
      "SELECT id, nom, chantier_fixe FROM workers ORDER BY nom ASC", conn
  )
  conn.close()
  return df


def get_chantiers_conducteur(conducteur_tag):
  conn = get_db_connection()
  c = conn.cursor()
  c.execute(
      "SELECT chantier FROM conducteur_chantiers WHERE conducteur_tag = ?"
      " ORDER BY chantier ASC",
      (conducteur_tag,),
  )
  lignes = c.fetchall()
  conn.close()
  return [r[0] for r in lignes]


def est_deja_valide(date_str, chantier):
  conn = get_db_connection()
  c = conn.cursor()
  c.execute(
      "SELECT COUNT(*) FROM pointages WHERE date_jour = ? AND chantier = ?",
      (date_str, chantier),
  )
  count = c.fetchone()[0]
  conn.close()
  return count > 0


def get_photo_path(identifiant):
  nom_clean = identifiant.replace(" ", "_")
  for ext in [".jpg", ".jpeg", ".png"]:
    p = os.path.join(PHOTOS_DIR, f"{nom_clean}{ext}")
    if os.path.exists(p):
      return p
  return None


# --- GESTION DES NOTIFICATIONS ---
if "sync_notif" not in st.session_state:
  st.session_state["sync_notif"] = None

if st.session_state["sync_notif"]:
  st.success(st.session_state["sync_notif"])

st.title("🏗️ Suivi de Chantier & Étanchéité")

dict_conducteurs = get_conducteurs_dict()
nom_c1 = dict_conducteurs.get("c1", "Conducteur 1")
nom_c2 = dict_conducteurs.get("c2", "Conducteur 2")

menu_general = st.radio(
    "Espace de travail",
    [f"👷 Espace {nom_c1}", f"👷 Espace {nom_c2}", "🔐 Espace Admin (Direction)"],
    horizontal=True,
)


def interface_saisie_conducteur(conducteur_id_tag, default_nom):
  photo_cond = get_photo_path(conducteur_id_tag)
  col_h1, col_h2 = st.columns([1, 4])
  with col_h1:
    if photo_cond:
      st.image(photo_cond, width=70)
    else:
      st.markdown(
          "<div"
          " style='font-size:45px;line-height:70px;text-align:center;'>👷</div>",
          unsafe_allow_html=True,
      )
  with col_h2:
    st.subheader(f"Pointage Journalier — {default_nom}")

  date_choisie = st.date_input(
      "📅 Date de saisie", value=date.today(), key=f"date_{conducteur_id_tag}"
  )

  chantiers_autorises = get_chantiers_conducteur(conducteur_id_tag)

  if not chantiers_autorises:
    st.warning(
        f"⚠️ Aucun chantier n'est actuellement attribué à {default_nom}.\n\n"
        "L'administrateur doit vous affecter vos chantiers dans l'Espace Admin."
    )
    return

  chantier_choisi = st.selectbox(
      "📍 Sélectionner le Chantier",
      chantiers_autorises,
      key=f"ch_sel_{conducteur_id_tag}",
  )

  date_str = str(date_choisie)
  deja_fait = est_deja_valide(date_str, chantier_choisi)

  if deja_fait:
    st.info(
        f"🟢 **Pointage déjà enregistré pour {chantier_choisi} le {date_str}.**"
        " Une nouvelle validation mettra à jour la saisie sans doublon."
    )

  df_w = get_workers_df()
  equipe_active = df_w[df_w["chantier_fixe"] == chantier_choisi]

  st.markdown(
      f"#### 👷 Équipe présente sur **{chantier_choisi}** :"
      f" `{len(equipe_active)}` ouvrier(s)"
  )

  if equipe_active.empty:
    st.warning(
        f"⚠️ Aucun ouvrier n'est actuellement rattaché à {chantier_choisi}.\n\n"
        "L'administrateur doit affecter l'équipe dans l'Espace Admin."
    )
  else:
    donnees_ouvriers = {}

    for _, row in equipe_active.iterrows():
      w_id = row["id"]
      w_nom = row["nom"]
      photo_p = get_photo_path(w_nom)

      col_av, col_tx = st.columns([1, 4])
      with col_av:
        if photo_p:
          st.image(photo_p, width=65)
        else:
          st.markdown(
              "<div"
              " style='font-size:40px;line-height:65px;text-align:center;'>👷</div>",
              unsafe_allow_html=True,
          )
      with col_tx:
        st.markdown(f"### {w_nom}")

      st_val = st.selectbox(
          "Statut de présence",
          [
              "Présent (Journée)",
              "1/2 journée",
              "Absence Autorisée (Congé/Maladie)",
              "Absence Non Autorisée (Injustifiée)",
          ],
          key=f"st_{conducteur_id_tag}_{w_id}",
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
              "Tâche effectuée",
              LISTE_TACHES,
              key=f"tch_{conducteur_id_tag}_{w_id}",
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
              key=f"typ_{conducteur_id_tag}_{w_id}",
          )

        if type_travail == "Métrage (m² / ml)":
          col_r1, col_r2, col_r3 = st.columns([1.5, 1.5, 2])
          with col_r1:
            qte_val = st.number_input(
                "Production réalisée",
                min_value=0.0,
                step=1.0,
                value=25.0,
                key=f"qte_{conducteur_id_tag}_{w_id}",
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
                key=f"app_{conducteur_id_tag}_{w_id}",
            )
          with col_r3:
            obs_val = st.text_input(
                "Observation libre",
                placeholder="Ex: terrasse sud, relevés...",
                key=f"obs_{conducteur_id_tag}_{w_id}",
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
                key=f"app_br_{conducteur_id_tag}_{w_id}",
            )
          with col_b2:
            obs_val = st.text_input(
                "Détail du bricolage",
                placeholder="Ex: traitement regard, solin...",
                key=f"obs_br_{conducteur_id_tag}_{w_id}",
            )
      else:
        obs_val = st.text_input(
            "Motif de l'absence",
            placeholder="Ex: congé, maladie, arrêt...",
            key=f"obs_abs_{conducteur_id_tag}_{w_id}",
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

    label_bouton = (
        "🔄 Mettre à jour la saisie (Déjà validée)"
        if deja_fait
        else "💾 Valider la journée de l'équipe"
    )

    if st.button(
        label_bouton,
        type="primary",
        use_container_width=True,
        key=f"btn_val_{conducteur_id_tag}",
    ):
      conn = get_db_connection()
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
                INSERT OR REPLACE INTO pointages (date_jour, chantier, conducteur, worker_id, statut, tache, quantite, unite, appreciation, observation, score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date_str,
                chantier_choisi,
                default_nom,
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

      heure_validation = datetime.now().strftime("%H:%M:%S")
      st.session_state["sync_notif"] = (
          f"✅ Journée enregistrée par {default_nom} à {heure_validation} pour"
          f" {chantier_choisi} !"
      )
      st.rerun()


# ==============================================================================
# 1. ESPACES CONDUCTEURS
# ==============================================================================
if menu_general == f"👷 Espace {nom_c1}":
  interface_saisie_conducteur("c1", nom_c1)

elif menu_general == f"👷 Espace {nom_c2}":
  interface_saisie_conducteur("c2", nom_c2)

# ==============================================================================
# 2. ESPACE ADMIN (GESTION CENTRALISÉE CONDUCTEURS ET OUVRIERS)
# ==============================================================================
elif menu_general == "🔐 Espace Admin (Direction)":
  st.subheader("Accès Sécurisé - Administration")

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
            "👥 Profils & Photos (Conducteurs & Ouvriers)",
            "🏗️ Affecter les Chantiers aux Conducteurs",
            "⚡ Fixer l'équipe d'un Chantier",
            "🔄 Transférer un ouvrier individuel",
            "📋 Vue générale des équipes",
            "📊 Registre & Rapport des Pointages",
        ],
    )

    st.markdown("---")

    # MODULE UNIFIÉ : CONDUCTEURS ET OUVRIERS REGROUPÉS ENSEMBLE
    if (
        sous_menu_admin
        == "👥 Profils & Photos (Conducteurs & Ouvriers)"
    ):
      st.markdown(
          "#### Gestion Complète des Profils & Photos (Conducteurs & Ouvriers)"
      )
      st.caption(
          "Modifiez les noms, téléversez les photos ou ajoutez de nouvelles"
          " personnes en un seul endroit."
      )

      tab_conducteurs, tab_ouvriers = st.tabs(
          ["👷 Profils des Conducteurs", "👷 Profils des Ouvriers"]
      )

      # --- ONGLET 1 : LES CONDUCTEURS (NOM + PHOTO) ---
      with tab_conducteurs:
        cond_choisi_tag = st.radio(
            "Sélectionner le conducteur à modifier :",
            ["c1", "c2"],
            format_func=lambda x: f"Conducteur 1 ({nom_c1})"
            if x == "c1"
            else f"Conducteur 2 ({nom_c2})",
            horizontal=True,
            key="radio_sel_cond_tab",
        )

        nom_actuel = nom_c1 if cond_choisi_tag == "c1" else nom_c2
        photo_actuelle_cond = get_photo_path(cond_choisi_tag)

        col_cp, col_ci = st.columns([1, 2])
        with col_cp:
          if photo_actuelle_cond:
            st.image(
                photo_actuelle_cond,
                caption=f"Photo : {nom_actuel}",
                width=140,
            )
          else:
            st.info("Aucune photo enregistrée.")

        with col_ci:
          nouveau_nom_c = st.text_input(
              "Nom affiché du conducteur :",
              value=nom_actuel,
              key=f"input_nom_cond_{cond_choisi_tag}",
          )
          nouvelle_photo_c = st.file_uploader(
              "Photo du conducteur (Galerie ou Fichier)",
              type=["jpg", "jpeg", "png"],
              key=f"upload_photo_cond_{cond_choisi_tag}",
          )

          if st.button(
              "💾 Enregistrer le profil conducteur",
              type="primary",
              key=f"btn_save_cond_{cond_choisi_tag}",
          ):
            nom_net = nouveau_nom_c.strip() or (
                "Conducteur 1" if cond_choisi_tag == "c1" else "Conducteur 2"
            )
            conn = get_db_connection()
            c = conn.cursor()
            c.execute(
                "UPDATE conducteurs_meta SET nom_affiche = ? WHERE tag = ?",
                (nom_net, cond_choisi_tag),
            )
            conn.commit()
            conn.close()

            if nouvelle_photo_c is not None:
              ext = nouvelle_photo_c.name.split(".")[-1].lower()
              nom_f = f"{cond_choisi_tag}.{ext}"
              for old_ext in [".jpg", ".jpeg", ".png"]:
                ancien_f = os.path.join(
                    PHOTOS_DIR, f"{cond_choisi_tag}{old_ext}"
                )
                if os.path.exists(ancien_f):
                  os.remove(ancien_f)
              chemin_save = os.path.join(PHOTOS_DIR, nom_f)
              img = Image.open(nouvelle_photo_c)
              img.save(chemin_save)

            st.session_state["sync_notif"] = (
                f"✅ Profil et photo mis à jour pour {nom_net} !"
            )
            st.rerun()

      # --- ONGLET 2 : LES OUVRIERS (NOM + PHOTO + AJOUT + SUPPRESSION) ---
      with tab_ouvriers:
        df_w_admin = get_workers_df()
        subtab_edit, subtab_add, subtab_del = st.tabs([
            "✏️ Modifier un ouvrier (Nom + Photo)",
            "➕ Ajouter un nouvel ouvrier (avec photo)",
            "🗑️ Supprimer un ouvrier",
        ])

        with subtab_edit:
          ouvrier_sel = st.selectbox(
              "Sélectionner l'ouvrier à modifier :",
              df_w_admin["nom"].tolist(),
              key="sel_ouvrier_tab_unifie",
          )
          photo_actuelle_ouv = get_photo_path(ouvrier_sel)

          col_op, col_oi = st.columns([1, 2])
          with col_op:
            if photo_actuelle_ouv:
              st.image(
                  photo_actuelle_ouv,
                  caption=f"Photo : {ouvrier_sel}",
                  width=140,
              )
            else:
              st.info("Aucune photo.")

          with col_oi:
            nouveau_nom_ouv = st.text_input(
                "Nom complet de l'ouvrier :",
                value=ouvrier_sel,
                key=f"edit_nom_w_{ouvrier_sel}",
            )
            nouvelle_photo_ouv = st.file_uploader(
                "Photo de l'ouvrier (Galerie ou Fichier)",
                type=["jpg", "jpeg", "png"],
                key=f"upload_photo_w_{ouvrier_sel}",
            )

            if st.button(
                "💾 Enregistrer les modifications ouvrier",
                type="primary",
                key=f"btn_save_w_{ouvrier_sel}",
            ):
              nom_propre = nouveau_nom_ouv.strip()
              conn = get_db_connection()
              c = conn.cursor()

              if nom_propre and nom_propre != ouvrier_sel:
                try:
                  c.execute(
                      "UPDATE workers SET nom = ? WHERE nom = ?",
                      (nom_propre, ouvrier_sel),
                  )
                  conn.commit()

                  old_clean = ouvrier_sel.replace(" ", "_")
                  new_clean = nom_propre.replace(" ", "_")
                  for ext in [".jpg", ".jpeg", ".png"]:
                    old_f = os.path.join(PHOTOS_DIR, f"{old_clean}{ext}")
                    new_f = os.path.join(PHOTOS_DIR, f"{new_clean}{ext}")
                    if os.path.exists(old_f):
                      os.rename(old_f, new_f)
                  nom_ref = nom_propre
                except sqlite3.IntegrityError:
                  st.error("Ce nom d'ouvrier existe déjà.")
                  conn.close()
                  st.stop()
              else:
                nom_ref = ouvrier_sel

              if nouvelle_photo_ouv is not None:
                ext = nouvelle_photo_ouv.name.split(".")[-1].lower()
                nom_fichier_photo = f"{nom_ref.replace(' ', '_')}.{ext}"
                chemin_sauvegarder = os.path.join(PHOTOS_DIR, nom_fichier_photo)
                img = Image.open(nouvelle_photo_ouv)
                img.save(chemin_sauvegarder)

              conn.close()
              st.session_state["sync_notif"] = (
                  f"✅ Profil et photo mis à jour pour l'ouvrier {nom_ref} !"
              )
              st.rerun()

        with subtab_add:
          st.markdown("##### Ajouter un nouvel ouvrier")
          col_add1, col_add2 = st.columns(2)
          with col_add1:
            nom_nouveau = st.text_input(
                "Nom et prénom :",
                placeholder="Ex: BENKADDOUR Karim",
                key="in_new_worker_nom_tab",
            )
            chantier_init = st.selectbox(
                "Chantier initial :",
                LISTE_CHANTIERS,
                key="sel_new_worker_ch_tab",
            )
          with col_add2:
            photo_nouvel_ouvrier = st.file_uploader(
                "Photo de profil (Optionnel) :",
                type=["jpg", "jpeg", "png"],
                key="upload_new_worker_photo_tab",
            )

          if st.button(
              "➕ Ajouter l'ouvrier avec son profil",
              type="primary",
              key="btn_add_worker_tab",
          ):
            nom_nettoye = nom_nouveau.strip()
            if nom_nettoye:
              conn = get_db_connection()
              c = conn.cursor()
              try:
                c.execute(
                    "INSERT INTO workers (nom, chantier_fixe) VALUES (?, ?)",
                    (nom_nettoye, chantier_init),
                )
                conn.commit()
                conn.close()

                if photo_nouvel_ouvrier is not None:
                  ext = photo_nouvel_ouvrier.name.split(".")[-1].lower()
                  nom_fichier = f"{nom_nettoye.replace(' ', '_')}.{ext}"
                  chemin = os.path.join(PHOTOS_DIR, nom_fichier)
                  img = Image.open(photo_nouvel_ouvrier)
                  img.save(chemin)

                st.session_state["sync_notif"] = (
                    f"✅ {nom_nettoye} a été ajouté avec succès !"
                )
                st.rerun()
              except sqlite3.IntegrityError:
                conn.close()
                st.error("Cet ouvrier est déjà enregistré.")

        with subtab_del:
          st.markdown("##### Retirer un ouvrier")
          ouvrier_a_del = st.selectbox(
              "Sélectionner l'ouvrier à supprimer :",
              df_w_admin["nom"].tolist(),
              key="sel_ouvrier_suppression_tab",
          )
          if st.button(
              f"❌ Supprimer définitivement {ouvrier_a_del}",
              type="secondary",
              key="btn_del_worker_tab",
          ):
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("DELETE FROM workers WHERE nom = ?", (ouvrier_a_del,))
            conn.commit()
            conn.close()

            clean_nom = ouvrier_a_del.replace(" ", "_")
            for ext in [".jpg", ".jpeg", ".png"]:
              p_to_del = os.path.join(PHOTOS_DIR, f"{clean_nom}{ext}")
              if os.path.exists(p_to_del):
                os.remove(p_to_del)

            st.session_state["sync_notif"] = (
                f"🗑️ {ouvrier_a_del} a été supprimé de la base."
            )
            st.rerun()

    # MODULE 2 : ATTRIBUTION DES CHANTIERS
    elif sous_menu_admin == "🏗️ Affecter les Chantiers aux Conducteurs":
      st.markdown("#### Attribution des chantiers sous responsabilité")
      chantiers_disponibles = [
          c for c in LISTE_CHANTIERS if c != "EN ATTENTE / DEPOT"
      ]

      col_c1, col_c2 = st.columns(2)
      with col_c1:
        st.markdown(f"##### 👷 {nom_c1}")
        actuels_c1 = get_chantiers_conducteur("c1")
        nouveaux_c1 = st.multiselect(
            "Chantiers assignés :",
            options=chantiers_disponibles,
            default=actuels_c1,
            key="ms_admin_assign_c1",
        )

      with col_c2:
        st.markdown(f"##### 👷 {nom_c2}")
        actuels_c2 = get_chantiers_conducteur("c2")
        nouveaux_c2 = st.multiselect(
            "Chantiers assignés :",
            options=chantiers_disponibles,
            default=actuels_c2,
            key="ms_admin_assign_c2",
        )

      if st.button(
          "💾 Sauvegarder les attributions",
          type="primary",
          use_container_width=True,
      ):
        conn = get_db_connection()
        c = conn.cursor()

        c.execute(
            "DELETE FROM conducteur_chantiers WHERE conducteur_tag = 'c1'"
        )
        for ch in nouveaux_c1:
          c.execute(
              "INSERT INTO conducteur_chantiers (conducteur_tag, chantier)"
              " VALUES ('c1', ?)",
              (ch,),
          )

        c.execute(
            "DELETE FROM conducteur_chantiers WHERE conducteur_tag = 'c2'"
        )
        for ch in nouveaux_c2:
          c.execute(
              "INSERT INTO conducteur_chantiers (conducteur_tag, chantier)"
              " VALUES ('c2', ?)",
              (ch,),
          )

        conn.commit()
        conn.close()

        heure_sync = datetime.now().strftime("%H:%M:%S")
        st.session_state["sync_notif"] = (
            f"🔄 Attribution mise à jour à {heure_sync} : {nom_c1}"
            f" ({len(nouveaux_c1)} chantier(s)), {nom_c2}"
            f" ({len(nouveaux_c2)} chantier(s))."
        )
        st.rerun()

    # MODULE 3 : FIXER L'ÉQUIPE DU CHANTIER
    elif sous_menu_admin == "⚡ Fixer l'équipe d'un Chantier":
      st.markdown("#### Définir l'équipe autorisée sur un chantier")
      ch_cible = st.selectbox(
          "Chantier à configurer",
          [c for c in LISTE_CHANTIERS if c != "EN ATTENTE / DEPOT"],
          key="adm_ch_cible",
      )

      df_w_admin = get_workers_df()
      tous_les_noms = df_w_admin["nom"].tolist()
      actuels = df_w_admin[df_w_admin["chantier_fixe"] == ch_cible][
          "nom"
      ].tolist()

      nouveaux_membres = st.multiselect(
          f"Ouvriers rattachés à {ch_cible} :",
          options=tous_les_noms,
          default=actuels,
          key=f"ms_adm_{ch_cible}",
      )

      if st.button(
          f"💾 Verrouiller l'équipe de {ch_cible}",
          type="primary",
          use_container_width=True,
      ):
        conn = get_db_connection()
        c = conn.cursor()

        for nom in actuels:
          if nom not in nouveaux_membres:
            c.execute(
                "UPDATE workers SET chantier_fixe = 'EN ATTENTE / DEPOT' WHERE"
                " nom = ?",
                (nom,),
            )

        for nom in nouveaux_membres:
          c.execute(
              "UPDATE workers SET chantier_fixe = ? WHERE nom = ?",
              (ch_cible, nom),
          )

        conn.commit()
        conn.close()

        heure_sync = datetime.now().strftime("%H:%M:%S")
        st.session_state["sync_notif"] = (
            f"🔄 Équipe verrouillée à {heure_sync} : {len(nouveaux_membres)}"
            f" ouvriers fixés sur {ch_cible}."
        )
        st.rerun()

    # MODULE 4 : TRANSFERT INDIVIDUEL
    elif sous_menu_admin == "🔄 Transférer un ouvrier individuel":
      st.markdown("#### Déplacer un ouvrier vers un autre chantier")
      df_w_admin = get_workers_df()

      ouvrier_sel = st.selectbox(
          "Sélectionner l'ouvrier",
          df_w_admin["nom"].tolist(),
          key="ouv_transf_sel",
      )
      infos_o = df_w_admin[df_w_admin["nom"] == ouvrier_sel].iloc[0]
      ancien_ch = infos_o["chantier_fixe"]
      ouv_id = int(infos_o["id"])

      st.info(f"Chantier actuel : **{ancien_ch}**")

      dest_ch = st.selectbox(
          "Nouveau chantier",
          [c for c in LISTE_CHANTIERS if c != ancien_ch],
          key="dest_ch_sel",
      )

      if st.button(
          f"Confirmer le transfert vers {dest_ch}",
          type="primary",
          use_container_width=True,
      ):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            "UPDATE workers SET chantier_fixe = ? WHERE id = ?",
            (dest_ch, ouv_id),
        )
        conn.commit()
        conn.close()

        st.session_state["sync_notif"] = (
            f"🔄 Transfert effectué : {ouvrier_sel} ➔ {dest_ch}"
        )
        st.rerun()

    # MODULE 5 : VUE GÉNÉRALE
    elif sous_menu_admin == "📋 Vue générale des équipes":
      st.markdown("#### Répartition actuelle des ouvriers")
      df_w_admin = get_workers_df()

      filtre = st.selectbox(
          "Filtrer par Chantier", ["Tous les chantiers"] + LISTE_CHANTIERS
      )
      if filtre != "Tous les chantiers":
        df_show = df_w_admin[df_w_admin["chantier_fixe"] == filtre]
      else:
        df_show = df_w_admin

      st.dataframe(
          df_show[["nom", "chantier_fixe"]].rename(
              columns={"nom": "Ouvrier", "chantier_fixe": "Chantier Fixé"}
          ),
          use_container_width=True,
          hide_index=True,
      )

    # MODULE 6 : REGISTRE
    elif (
        sous_menu_admin == "📊 Registre & Rapport des Pointages"
    ):
      st.markdown("#### Registre des Pointages & Responsables de Saisie")
      conn = get_db_connection()
      query = """
            SELECT 
                p.date_jour AS [Date],
                p.chantier AS [Chantier],
                p.conducteur AS [Conducteur],
                w.nom AS [Ouvrier],
                p.statut AS [Statut],
                p.tache AS [Tâche],
                CASE 
                    WHEN p.unite = 'Sans métrage' THEN 'Bricol'
                    WHEN p.quantite > 0 THEN p.quantite || ' ' || p.unite 
                    ELSE '-'
                END AS [Production],
                COALESCE(p.appreciation, '-') AS [Qualité],
                COALESCE(p.observation, '-') AS [Observation],
                CASE 
                    WHEN p.score IS NULL THEN 'Justifié'
                    ELSE CAST(p.score AS TEXT)
                END AS [Score]
            FROM pointages p
            JOIN workers w ON p.worker_id = w.id
            ORDER BY p.date_jour DESC, p.chantier ASC, w.nom ASC
        """
      df_hist = pd.read_sql_query(query, conn)
      conn.close()

      if df_hist.empty:
        st.info("Aucune saisie enregistrée dans la base de données.")
      else:
        c_f1, c_f2 = st.columns(2)
        with c_f1:
          conducteurs_trouves = sorted(
              df_hist["Conducteur"].dropna().unique().tolist()
          )
          filtre_cond = st.selectbox(
              "Filtrer par Conducteur :",
              ["Tous les conducteurs"] + conducteurs_trouves,
          )
        with c_f2:
          chantiers_trouves = sorted(
              df_hist["Chantier"].dropna().unique().tolist()
          )
          filtre_ch = st.selectbox(
              "Filtrer par Chantier :",
              ["Tous les chantiers"] + chantiers_trouves,
          )

        df_filtre = df_hist.copy()
        if filtre_cond != "Tous les conducteurs":
          df_filtre = df_filtre[df_filtre["Conducteur"] == filtre_cond]
        if filtre_ch != "Tous les chantiers":
          df_filtre = df_filtre[df_filtre["Chantier"] == filtre_ch]

        st.markdown(
            f"**Total enregistrements affichés :** `{len(df_filtre)}` ligne(s)"
        )
        st.dataframe(df_filtre, use_container_width=True, hide_index=True)

        csv = df_filtre.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Télécharger ce rapport (CSV Excel)",
            data=csv,
            file_name=f"rapport_pointage_{date.today()}.csv",
            mime="text/csv",
            use_container_width=True,
        )
