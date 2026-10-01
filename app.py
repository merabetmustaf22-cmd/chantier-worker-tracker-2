import os
import io
import glob
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

# Base de données permanente
DB_PATH = "chantier_master.db"
PHOTOS_DIR = "photos"
os.makedirs(PHOTOS_DIR, exist_ok=True)

ADMIN_PASSWORD = "admin"

LISTE_CHANTIERS_INIT = [
    "CAC-31-24", "CMA-09-23", "ECOLE SBA", "GROUPEMENT GENDARMERIE",
    "HOB-342-08-24", "HTA ZONE SBA", "IZM-31-24(CES)", "LBU-31-23",
    "LCP-31-24", "MARAVAL", "VILLA CITE EL RIAD ORAN",
    "VILLA Hasnaoui MAKAM", "VILLA Hasnaoui Outhman", "ESC-16-24",
    "EN ATTENTE / DEPOT"
]

LISTE_TACHES_INIT = [
    "PAX", "PARE-VAPEUR", "SOKLE PARE-VAPEUR", "ELASTOTEK",
    "ELASTOTEK GOURGE", "ELASTOTEK JOINTAGE", "ELASTOTEK LEVI",
    "ELASTOTEK NETTOYAGE", "Forme de pente", "GOURGE",
    "JOINT DE DILATATION", "MASTIC", "nettoyage", "PONSAGE",
    "décapage", "BACHE A EAU", "PISCINE", "SOUS CARRELAGE",
    "TEST EAU", "coupe-feu", "Couvre-joint", "DALLE Cheminée",
    "regard", "Traitement de l'ascenseur", "BRICOL", "BRICOL ELASTOTEK",
    "BRICOL SILICONE", "BRICOL SOKLE", "BRICOL SOUS CARRELAGE",
    "BRICOL PARE-VAPEUR", "DIVERS"
]

EFFECTIF_GLOBAL_INIT = [
    "ADDA Abbess", "MEKHACHEF DJAMEL", "MESTEFAOUI AHMED", "ARGOUB HALIM",
    "FEHIM CHIBANI AZZOUZ", "TAIBI REDA", "ABED OMAR", "ZEGHDAN ABDELKADER",
    "BAGHDADI ALI", "BOUKHELIF KAMEL", "MOKHTARI Omar", "GHEZINI Habib",
    "BERACHEMI AHMED", "ARAR AISSA", "MOKHTARI Djelloul", "HAFDI Rachid",
    "BENHAMMADI Mohamed", "MOUISSI WALID", "BENSEMICHA MEROUANE",
    "TOUATI Zouaoui", "GHRIBI MOHAMED", "MESSAOUDI ABDELKRIM",
    "TAHAR BOUZIAN YOUCEF"
]

def get_db_connection():
    return sqlite3.connect(DB_PATH, timeout=15)

def init_database():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS chantiers_ref (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS taches_ref (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE
        )
    """)
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
            UNIQUE(date_jour, chantier, worker_id)
        )
    """)

    for ch in LISTE_CHANTIERS_INIT:
        c.execute("INSERT OR IGNORE INTO chantiers_ref (nom) VALUES (?)", (ch,))
    for tch in LISTE_TACHES_INIT:
        c.execute("INSERT OR IGNORE INTO taches_ref (nom) VALUES (?)", (tch,))
    for w in EFFECTIF_GLOBAL_INIT:
        c.execute("INSERT OR IGNORE INTO workers (nom, chantier_fixe) VALUES (?, ?)", (w, 'CAC-31-24'))

    c.execute("INSERT OR IGNORE INTO conducteurs_meta (tag, nom_affiche) VALUES ('c1', 'Conducteur 1')")
    c.execute("INSERT OR IGNORE INTO conducteurs_meta (tag, nom_affiche) VALUES ('c2', 'Conducteur 2')")
    
    conn.commit()
    conn.close()
    
    recuperer_anciennes_donnees()

def recuperer_anciennes_donnees():
    anciennes_bases = glob.glob("chantier_*.db")
    for old_db in anciennes_bases:
        if old_db == DB_PATH:
            continue
        try:
            conn_old = sqlite3.connect(old_db)
            c_old = conn_old.cursor()
            c_old.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pointages'")
            if c_old.fetchone():
                c_old.execute("""
                    SELECT date_jour, chantier, COALESCE(conducteur, 'Conducteur'), worker_id, statut, tache, quantite, unite, appreciation, observation, score 
                    FROM pointages
                """)
                lignes = c_old.fetchall()
                if lignes:
                    conn_new = get_db_connection()
                    c_new = conn_new.cursor()
                    for r in lignes:
                        c_new.execute("""
                            INSERT OR IGNORE INTO pointages (date_jour, chantier, conducteur, worker_id, statut, tache, quantite, unite, appreciation, observation, score)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, r)
                    conn_new.commit()
                    conn_new.close()
            conn_old.close()
        except Exception:
            pass

init_database()

def get_all_chantiers():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT nom FROM chantiers_ref ORDER BY nom ASC")
    res = [row[0] for row in c.fetchall()]
    conn.close()
    return res

def get_all_taches():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT nom FROM taches_ref ORDER BY nom ASC")
    res = [row[0] for row in c.fetchall()]
    conn.close()
    return res

def get_conducteurs_dict():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT tag, nom_affiche FROM conducteurs_meta")
    res = {row[0]: row[1] for row in c.fetchall()}
    conn.close()
    return res

def get_workers_df():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT id, nom, chantier_fixe FROM workers ORDER BY nom ASC", conn)
    conn.close()
    return df

def get_chantiers_conducteur(conducteur_tag):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT chantier FROM conducteur_chantiers WHERE conducteur_tag = ? ORDER BY chantier ASC", (conducteur_tag,))
    lignes = c.fetchall()
    conn.close()
    return [r[0] for r in lignes]

def est_deja_valide(date_str, chantier):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM pointages WHERE date_jour = ? AND chantier = ?", (date_str, chantier))
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

# --- NOTIFICATIONS STREAMLIT ---
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
    horizontal=True
)

def interface_saisie_conducteur(conducteur_id_tag, default_nom):
    photo_cond = get_photo_path(conducteur_id_tag)
    col_h1, col_h2 = st.columns([1, 4])
    with col_h1:
        if photo_cond:
            st.image(photo_cond, width=70)
        else:
            st.markdown("<div style='font-size:45px;line-height:70px;text-align:center;'>👷</div>", unsafe_allow_html=True)
    with col_h2:
        st.subheader(f"Pointage Journalier — {default_nom}")

    date_choisie = st.date_input("📅 Date de saisie", value=date.today(), key=f"date_{conducteur_id_tag}")

    chantiers_autorises = get_chantiers_conducteur(conducteur_id_tag)

    if not chantiers_autorises:
        st.warning(f"⚠️ Aucun chantier n'est actuellement attribué à {default_nom}.\n\nL'administrateur doit vous affecter vos chantiers dans l'Espace Admin.")
        return

    chantier_choisi = st.selectbox("📍 Sélectionner le Chantier", chantiers_autorises, key=f"ch_sel_{conducteur_id_tag}")

    date_str = str(date_choisie)
    deja_fait = est_deja_valide(date_str, chantier_choisi)

    if deja_fait:
        st.info(f"🟢 **Pointage déjà enregistré pour {chantier_choisi} le {date_str}.** Une nouvelle validation mettra à jour la saisie sans doublon.")

    df_w = get_workers_df()
    equipe_active = df_w[df_w["chantier_fixe"] == chantier_choisi]

    st.markdown(f"#### 👷 Équipe présente sur **{chantier_choisi}** : `{len(equipe_active)}` ouvrier(s)")

    if equipe_active.empty:
        st.warning(f"⚠️ Aucun ouvrier n'est actuellement rattaché à {chantier_choisi}.\n\nL'administrateur doit affecter l'équipe dans l'Espace Admin.")
    else:
        donnees_ouvriers = {}
        toutes_les_taches = get_all_taches()

        for _, row in equipe_active.iterrows():
            w_id = row['id']
            w_nom = row['nom']
            photo_p = get_photo_path(w_nom)

            col_av, col_tx = st.columns([1, 4])
            with col_av:
                if photo_p:
                    st.image(photo_p, width=65)
                else:
                    st.markdown("<div style='font-size:40px;line-height:65px;text-align:center;'>👷</div>", unsafe_allow_html=True)
            with col_tx:
                st.markdown(f"### {w_nom}")

            st_val = st.selectbox("Statut de présence", [
                "Présent (Journée)",
                "1/2 journée",
                "Absence Autorisée (Congé/Maladie)",
                "Absence Non Autorisée (Injustifiée)"
            ], key=f"st_{conducteur_id_tag}_{w_id}")

            tache_val = "-"
            qte_val = 0.0
            unite_val = "-"
            apprec_val = "-"
            obs_val = ""

            if "Présent" in st_val or "1/2" in st_val:
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    tache_val = st.selectbox("Tâche / Corps d'état", toutes_les_taches, key=f"tch_{conducteur_id_tag}_{w_id}")
                with col_t2:
                    est_bricol_defaut = ("BRICOL" in tache_val.upper()) or (tache_val in ["DIVERS", "nettoyage", "PONSAGE"])
                    type_travail = st.selectbox("Type d'activité", ["Métrage (m² / ml)", "Bricol / Sans métrage"], index=1 if est_bricol_defaut else 0, key=f"typ_{conducteur_id_tag}_{w_id}")

                if type_travail == "Métrage (m² / ml)":
                    col_r1, col_r2, col_r3 = st.columns([1.5, 1.5, 2])
                    with col_r1:
                        qte_val = st.number_input("Production réalisée", min_value=0.0, step=1.0, value=25.0, key=f"qte_{conducteur_id_tag}_{w_id}")
                        unite_val = "m²"
                    with col_r2:
                        apprec_val = st.selectbox("Qualité d'exécution", ["🟢 Conforme / Soigné", "🟡 Moyen / Acceptable", "🔴 Non conforme / À reprendre"], key=f"app_{conducteur_id_tag}_{w_id}")
                    with col_r3:
                        obs_val = st.text_input("Observation libre", placeholder="Ex: terrasse sud, relevés...", key=f"obs_{conducteur_id_tag}_{w_id}")
                else:
                    unite_val = "Sans métrage"
                    qte_val = 1.0
                    col_b1, col_b2 = st.columns([1.5, 2.5])
                    with col_b1:
                        apprec_val = st.selectbox("Qualité d'exécution", ["🟢 Conforme / Soigné", "🟡 Moyen / Acceptable", "🔴 Non conforme / À reprendre"], key=f"app_br_{conducteur_id_tag}_{w_id}")
                    with col_b2:
                        obs_val = st.text_input("Détail du bricolage", placeholder="Ex: traitement regard, solin...", key=f"obs_br_{conducteur_id_tag}_{w_id}")
            else:
                obs_val = st.text_input("Motif de l'absence", placeholder="Ex: congé, maladie, arrêt...", key=f"obs_abs_{conducteur_id_tag}_{w_id}")

            st.markdown("---")

            donnees_ouvriers[w_id] = {
                "statut": st_val,
                "tache": tache_val,
                "quantite": qte_val,
                "unite": unite_val,
                "appreciation": apprec_val,
                "observation": obs_val
            }

        label_bouton = "🔄 Mettre à jour la saisie (Déjà validée)" if deja_fait else "💾 Valider la journée de l'équipe"

        if st.button(label_bouton, type="primary", use_container_width=True, key=f"btn_val_{conducteur_id_tag}"):
            conn = get_db_connection()
            c = conn.cursor()

            for w_id, d in donnees_ouvriers.items():
                st_val = d["statut"]
                qte = d["quantite"]
                unite = d["unite"]
                app = d["appreciation"]

                if "Présent" in st_val:
                    base_p = 40.0
                    pts_prod = 40.0 if (unite == "Sans métrage" or qte >= 30) else (30.0 if qte >= 20 else 15.0)
                    pts_app = 20.0 if "Conforme" in app else (10.0 if "Moyen" in app else (0.0 if "Non conforme" in app else 10.0))
                    score = min(base_p + pts_prod + pts_app, 100.0)
                elif "1/2" in st_val:
                    score = 35.0
                elif "Autorisée" in st_val:
                    score = None
                else:
                    score = 0.0

                c.execute("""
                    INSERT OR REPLACE INTO pointages (date_jour, chantier, conducteur, worker_id, statut, tache, quantite, unite, appreciation, observation, score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (date_str, chantier_choisi, default_nom, w_id, st_val, d['tache'], qte, unite, app, d['observation'], score))

            conn.commit()
            conn.close()

            heure_validation = datetime.now().strftime("%H:%M:%S")
            st.session_state["sync_notif"] = f"✅ Journée enregistrée par {default_nom} à {heure_validation} pour {chantier_choisi} !"
            st.rerun()

# ==============================================================================
# 1. ESPACES CONDUCTEURS
# ==============================================================================
if menu_general == f"👷 Espace {nom_c1}":
    interface_saisie_conducteur("c1", nom_c1)

elif menu_general == f"👷 Espace {nom_c2}":
    interface_saisie_conducteur("c2", nom_c2)

# ==============================================================================
# 2. ESPACE ADMIN
# ==============================================================================
elif menu_general == "🔐 Espace Admin (Direction)":
    st.subheader("Accès Sécurisé - Administration")

    if "admin_logged_in" not in st.session_state:
        st.session_state["admin_logged_in"] = False

    if not st.session_state["admin_logged_in"]:
        col_p1, col_p2 = st.columns([2, 1])
        with col_p1:
            mdp = st.text_input("Code d'accès administrateur", type="password", placeholder="Entrez le mot de passe...")
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
        col_dec, col_stat = st.columns([1, 2])
        with col_dec:
            if st.button("🚪 Déconnexion Admin", use_container_width=True):
                st.session_state["admin_logged_in"] = False
                st.session_state["admin_active_module"] = None
                st.rerun()

        conn = get_db_connection()
        total_p = conn.cursor().execute("SELECT COUNT(*) FROM pointages").fetchone()[0]
        conn.close()
        with col_stat:
            st.info(f"📊 Registre Master : **{total_p} pointage(s) enregistrés au total**")

        if "admin_active_module" not in st.session_state:
            st.session_state["admin_active_module"] = None

        MODULES_ADMIN = [
            ("mod_rapport", "📊 Registre & Rapports", "Consulter, corriger ou exporter les rapports de saisie"),
            ("mod_chantiers_taches", "🏗️ Chantiers & Corps d'état", "Ajouter, modifier ou supprimer des chantiers et tâches"),
            ("mod_profils", "👥 Profils & Photos", "Gérer les noms et photos des Conducteurs et Ouvriers"),
            ("mod_chantiers_cond", "👷 Chantiers / Conducteurs", "Attribuer les chantiers sous la responsabilité de chacun"),
            ("mod_equipes", "⚡ Équipes par Chantier", "Composer et verrouiller l'équipe affectée à un projet"),
            ("mod_transfert", "🔄 Transfert d'Ouvrier", "Déplacer un ouvrier vers un autre chantier de façon unique"),
        ]

        if st.session_state["admin_active_module"] is None:
            st.markdown("### 🎛 Panneau de Contrôle Administrateur")
            st.caption("Cliquez sur une case pour ouvrir le module :")

            for i in range(0, len(MODULES_ADMIN), 2):
                col_c1, col_c2 = st.columns(2)
                
                tag1, titre1, desc1 = MODULES_ADMIN[i]
                with col_c1:
                    st.markdown(f"""
                    <div style="border:1px solid #ddd; border-radius:10px; padding:12px; margin-bottom:8px; background-color:#fafafa;">
                        <h4 style="margin:0 0 6px 0;">{titre1}</h4>
                        <p style="margin:0; font-size:13px; color:#555;">{desc1}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"Ouvrir {titre1}", key=f"btn_case_{tag1}", use_container_width=True):
                        st.session_state["admin_active_module"] = tag1
                        st.rerun()

                if i + 1 < len(MODULES_ADMIN):
                    tag2, titre2, desc2 = MODULES_ADMIN[i+1]
                    with col_c2:
                        st.markdown(f"""
                        <div style="border:1px solid #ddd; border-radius:10px; padding:12px; margin-bottom:8px; background-color:#fafafa;">
                            <h4 style="margin:0 0 6px 0;">{titre2}</h4>
                            <p style="margin:0; font-size:13px; color:#555;">{desc2}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"Ouvrir {titre2}", key=f"btn_case_{tag2}", use_container_width=True):
                            st.session_state["admin_active_module"] = tag2
                            st.rerun()

        else:
            mod_actuel = st.session_state["admin_active_module"]

            if st.button("⬅️ Retour au tableau des cases", type="secondary"):
                st.session_state["admin_active_module"] = None
                st.rerun()

            st.markdown("---")

            # 1. MODULE REGISTRE & RAPPORTS AVEC EXPORT EXCEL PARFAIT
            if mod_actuel == "mod_rapport":
                st.markdown("### 📊 Registre & Gestion des Saisies Conducteurs")
                
                tab_reg, tab_corr = st.tabs(["📋 Registre & Consultation", "✏️️ Corriger un Pointage (Admin)"])

                conn = get_db_connection()
                query_admin = """
                    SELECT 
                        p.id AS ID,
                        p.date_jour AS [Date],
                        p.chantier AS [Chantier],
                        COALESCE(p.conducteur, 'Non spécifié') AS [Conducteur],
                        COALESCE(w.nom, 'Ouvrier #' || p.worker_id) AS [Ouvrier],
                        p.statut AS [Statut],
                        p.tache AS [Tâche],
                        p.quantite AS [Quantite],
                        p.unite AS [Unite],
                        COALESCE(p.appreciation, '-') AS [Qualité],
                        COALESCE(p.observation, '-') AS [Observation],
                        p.score AS [Score]
                    FROM pointages p
                    LEFT JOIN workers w ON p.worker_id = w.id
                    ORDER BY p.date_jour DESC, p.id DESC
                """
                df_all_pointages = pd.read_sql_query(query_admin, conn)
                conn.close()

                with tab_reg:
                    if df_all_pointages.empty:
                        st.warning("⚠️ Aucune saisie n'a encore été effectuée ou validée dans le registre.")
                    else:
                        c_f1, c_f2 = st.columns(2)
                        with c_f1:
                            conds_trouves = sorted(df_all_pointages["Conducteur"].dropna().unique().tolist())
                            filtre_cond = st.selectbox("Filtrer par Conducteur :", ["Tous les conducteurs"] + conds_trouves)
                        with c_f2:
                            ch_trouves = sorted(df_all_pointages["Chantier"].dropna().unique().tolist())
                            filtre_ch = st.selectbox("Filtrer par Chantier :", ["Tous les chantiers"] + ch_trouves)

                        df_filtre = df_all_pointages.copy()
                        if filtre_cond != "Tous les conducteurs":
                            df_filtre = df_filtre[df_filtre["Conducteur"] == filtre_cond]
                        if filtre_ch != "Tous les chantiers":
                            df_filtre = df_filtre[df_filtre["Chantier"] == filtre_ch]

                        df_affichage = df_filtre.copy()
                        df_affichage["Production"] = df_affichage.apply(
                            lambda r: "Bricol" if r["Unite"] == "Sans métrage" else (f"{r['Quantite']} {r['Unite']}" if r["Quantite"] > 0 else "-"),
                            axis=1
                        )
                        colonnes_vues = ["Date", "Chantier", "Conducteur", "Ouvrier", "Statut", "Tâche", "Production", "Qualité", "Observation", "Score"]
                        
                        st.markdown(f"**Nombre d'enregistrements :** `{len(df_affichage)}` ligne(s)")
                        st.dataframe(df_affichage[colonnes_vues], use_container_width=True, hide_index=True)

                        # EXPORT ULTRA COMPATIBLE EXCEL (Point-virgule et UTF-8 BOM)
                        csv_propre = df_affichage[colonnes_vues].to_csv(index=False, sep=";", encoding="utf-8-sig")

                        col_dl1, col_dl2 = st.columns(2)
                        with col_dl1:
                            st.download_button(
                                "📥 Télécharger CSV (Excel Français)",
                                data=csv_propre.encode("utf-8-sig"),
                                file_name=f"rapport_pointage_{date.today()}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        with col_dl2:
                            try:
                                buffer = io.BytesIO()
                                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                                    df_affichage[colonnes_vues].to_excel(writer, index=False, sheet_name="Pointages")
                                st.download_button(
                                    "📗 Télécharger Fichier Excel (.xlsx)",
                                    data=buffer.getvalue(),
                                    file_name=f"rapport_pointage_{date.today()}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True
                                )
                            except Exception:
                                st.caption("💡 Pour activer l'export natif .xlsx : installez `openpyxl` (`pip install openpyxl`).")

                with tab_corr:
                    st.markdown("##### Rectifier ou supprimer une saisie erronée")
                    if df_all_pointages.empty:
                        st.info("Aucun pointage à corriger pour le moment.")
                    else:
                        df_all_pointages["label"] = df_all_pointages.apply(
                            lambda r: f"ID #{r['ID']} | {r['Date']} | {r['Chantier']} | {r['Ouvrier']} ({r['Conducteur']})",
                            axis=1
                        )
                        
                        ligne_choisie = st.selectbox(
                            "Sélectionner l'enregistrement à corriger :",
                            df_all_pointages["label"].tolist(),
                            key="sel_pt_correction"
                        )
                        
                        row_sel = df_all_pointages[df_all_pointages["label"] == ligne_choisie].iloc[0]
                        pt_id = int(row_sel["ID"])

                        st.info(f"Pointage de **{row_sel['Ouvrier']}** sur **{row_sel['Chantier']}** le **{row_sel['Date']}**")

                        col_c1, col_c2 = st.columns(2)
                        with col_c1:
                            statuts_possibles = [
                                "Présent (Journée)",
                                "1/2 journée",
                                "Absence Autorisée (Congé/Maladie)",
                                "Absence Non Autorisée (Injustifiée)"
                            ]
                            idx_st = statuts_possibles.index(row_sel["Statut"]) if row_sel["Statut"] in statuts_possibles else 0
                            mod_statut = st.selectbox("Statut :", statuts_possibles, index=idx_st, key=f"mod_st_{pt_id}")
                            
                            toutes_les_taches_dispos = get_all_taches()
                            idx_tch = toutes_les_taches_dispos.index(row_sel["Tâche"]) if row_sel["Tâche"] in toutes_les_taches_dispos else 0
                            mod_tache = st.selectbox("Tâche / Corps d'état :", toutes_les_taches_dispos, index=idx_tch, key=f"mod_tch_{pt_id}")

                        with col_c2:
                            type_activite_mod = st.selectbox("Type :", ["Métrage (m² / ml)", "Bricol / Sans métrage"], index=1 if row_sel["Unite"] == "Sans métrage" else 0, key=f"mod_typ_{pt_id}")
                            
                            if type_activite_mod == "Métrage (m² / ml)":
                                mod_qte = st.number_input("Production :", min_value=0.0, step=1.0, value=float(row_sel["Quantite"]), key=f"mod_qte_{pt_id}")
                                mod_unite = "m²"
                            else:
                                mod_qte = 1.0
                                mod_unite = "Sans métrage"

                            qualites_possibles = ["🟢 Conforme / Soigné", "🟡 Moyen / Acceptable", "🔴 Non conforme / À reprendre"]
                            idx_qual = qualites_possibles.index(row_sel["Qualité"]) if row_sel["Qualité"] in qualites_possibles else 0
                            mod_apprec = st.selectbox("Qualité :", qualites_possibles, index=idx_qual, key=f"mod_qual_{pt_id}")

                        mod_obs = st.text_input("Observation :", value=str(row_sel["Observation"]) if row_sel["Observation"] != "-" else "", key=f"mod_obs_{pt_id}")

                        col_btn_mod, col_btn_del = st.columns([2, 1])
                        
                        with col_btn_mod:
                            if st.button("💾 Sauvegarder la correction", type="primary", use_container_width=True):
                                if "Présent" in mod_statut:
                                    base_p = 40.0
                                    pts_prod = 40.0 if (mod_unite == "Sans métrage" or mod_qte >= 30) else (30.0 if mod_qte >= 20 else 15.0)
                                    pts_app = 20.0 if "Conforme" in mod_apprec else (10.0 if "Moyen" in mod_apprec else (0.0 if "Non conforme" in mod_apprec else 10.0))
                                    score_corr = min(base_p + pts_prod + pts_app, 100.0)
                                elif "1/2" in mod_statut:
                                    score_corr = 35.0
                                elif "Autorisée" in mod_statut:
                                    score_corr = None
                                else:
                                    score_corr = 0.0

                                conn = get_db_connection()
                                c = conn.cursor()
                                c.execute("""
                                    UPDATE pointages 
                                    SET statut = ?, tache = ?, quantite = ?, unite = ?, appreciation = ?, observation = ?, score = ?
                                    WHERE id = ?
                                """, (mod_statut, mod_tache, mod_qte, mod_unite, mod_apprec, mod_obs, score_corr, pt_id))
                                conn.commit()
                                conn.close()
                                st.session_state["sync_notif"] = f"✅ Pointage #{pt_id} rectifié avec succès !"
                                st.rerun()

                        with col_btn_del:
                            if st.button("🗑️ Supprimer ce pointage", type="secondary", use_container_width=True):
                                conn = get_db_connection()
                                c = conn.cursor()
                                c.execute("DELETE FROM pointages WHERE id = ?", (pt_id,))
                                conn.commit()
                                conn.close()
                                st.session_state["sync_notif"] = f"🗑️ Pointage #{pt_id} supprimé du registre."
                                st.rerun()

            # 2. MODULE CHANTIERS & CORPS D'ÉTAT
            elif mod_actuel == "mod_chantiers_taches":
                st.markdown("### 🏗️ Gestion des Chantiers & Corps d'état (Tâches)")
                tab_ch, tab_tch = st.tabs(["📍 Gestion des Chantiers", "🔨 Gestion des Corps d'état (Tâches)"])

                with tab_ch:
                    liste_actuelle_ch = get_all_chantiers()
                    sub_ch1, sub_ch2, sub_ch3 = st.tabs(["➕ Nouveau Chantier", "✏️ Modifier un Chantier", "🗑 Supprimer"])

                    with sub_ch1:
                        nouveau_chantier_nom = st.text_input("Nom du nouveau chantier :", key="in_add_ch")
                        if st.button("➕ Ajouter le chantier", type="primary"):
                            nom_c_clean = nouveau_chantier_nom.strip()
                            if nom_c_clean:
                                conn = get_db_connection()
                                c = conn.cursor()
                                try:
                                    c.execute("INSERT INTO chantiers_ref (nom) VALUES (?)", (nom_c_clean,))
                                    conn.commit()
                                    conn.close()
                                    st.session_state["sync_notif"] = f"✅ Chantier {nom_c_clean} ajouté avec succès !"
                                    st.rerun()
                                except sqlite3.IntegrityError:
                                    conn.close()
                                    st.error("Ce chantier existe déjà.")

                    with sub_ch2:
                        ch_a_modifier = st.selectbox("Sélectionner le chantier à renommer :", liste_actuelle_ch, key="sel_mod_ch")
                        ch_nouveau_nom = st.text_input("Nouveau nom :", value=ch_a_modifier, key="in_renom_ch")
                        if st.button("💾 Enregistrer la modification du nom"):
                            nom_n_clean = ch_nouveau_nom.strip()
                            if nom_n_clean and nom_n_clean != ch_a_modifier:
                                conn = get_db_connection()
                                c = conn.cursor()
                                try:
                                    c.execute("UPDATE chantiers_ref SET nom = ? WHERE nom = ?", (nom_n_clean, ch_a_modifier))
                                    c.execute("UPDATE workers SET chantier_fixe = ? WHERE chantier_fixe = ?", (nom_n_clean, ch_a_modifier))
                                    c.execute("UPDATE conducteur_chantiers SET chantier = ? WHERE chantier = ?", (nom_n_clean, ch_a_modifier))
                                    c.execute("UPDATE pointages SET chantier = ? WHERE chantier = ?", (nom_n_clean, ch_a_modifier))
                                    conn.commit()
                                    conn.close()
                                    st.session_state["sync_notif"] = f"✅ Chantier renommé vers {nom_n_clean} !"
                                    st.rerun()
                                except sqlite3.IntegrityError:
                                    conn.close()
                                    st.error("Ce nom de chantier existe déjà.")

                    with sub_ch3:
                        ch_a_suppr = st.selectbox("Sélectionner le chantier à retirer :", [c for c in liste_actuelle_ch if c != "EN ATTENTE / DEPOT"], key="sel_del_ch")
                        if st.button(f"❌ Supprimer définitivement {ch_a_suppr}", type="secondary"):
                            conn = get_db_connection()
                            c = conn.cursor()
                            c.execute("DELETE FROM chantiers_ref WHERE nom = ?", (ch_a_suppr,))
                            c.execute("UPDATE workers SET chantier_fixe = 'EN ATTENTE / DEPOT' WHERE chantier_fixe = ?", (ch_a_suppr,))
                            c.execute("DELETE FROM conducteur_chantiers WHERE chantier = ?", (ch_a_suppr,))
                            conn.commit()
                            conn.close()
                            st.session_state["sync_notif"] = f"🗑️ Chantier {ch_a_suppr} supprimé."
                            st.rerun()

                with tab_tch:
                    liste_actuelle_tch = get_all_taches()
                    sub_t1, sub_t2, sub_t3 = st.tabs(["➕ Nouveau Corps d'état", "✏️ Modifier", "🗑️ Supprimer"])

                    with sub_t1:
                        nouvelle_tache_nom = st.text_input("Nom de la nouvelle tâche :", key="in_add_tch")
                        if st.button("➕ Ajouter la tâche", type="primary"):
                            nom_t_clean = nouvelle_tache_nom.strip()
                            if nom_t_clean:
                                conn = get_db_connection()
                                c = conn.cursor()
                                try:
                                    c.execute("INSERT INTO taches_ref (nom) VALUES (?)", (nom_t_clean,))
                                    conn.commit()
                                    conn.close()
                                    st.session_state["sync_notif"] = f"✅ Corps d'état {nom_t_clean} ajouté avec succès !"
                                    st.rerun()
                                except sqlite3.IntegrityError:
                                    conn.close()
                                    st.error("Cette tâche existe déjà.")

                    with sub_t2:
                        tch_a_modifier = st.selectbox("Sélectionner la tâche à renommer :", liste_actuelle_tch, key="sel_mod_tch")
                        tch_nouveau_nom = st.text_input("Nouveau libellé :", value=tch_a_modifier, key="in_renom_tch")
                        if st.button("💾 Enregistrer la modification de la tâche"):
                            nom_nt_clean = tch_nouveau_nom.strip()
                            if nom_nt_clean and nom_nt_clean != tch_a_modifier:
                                conn = get_db_connection()
                                c = conn.cursor()
                                try:
                                    c.execute("UPDATE taches_ref SET nom = ? WHERE nom = ?", (nom_nt_clean, tch_a_modifier))
                                    c.execute("UPDATE pointages SET tache = ? WHERE tache = ?", (nom_nt_clean, tch_a_modifier))
                                    conn.commit()
                                    conn.close()
                                    st.session_state["sync_notif"] = f"✅ Tâche renommée vers {nom_nt_clean} !"
                                    st.rerun()
                                except sqlite3.IntegrityError:
                                    conn.close()
                                    st.error("Ce nom de tâche existe déjà.")

                    with sub_t3:
                        tch_a_suppr = st.selectbox("Sélectionner la tâche à retirer :", liste_actuelle_tch, key="sel_del_tch")
                        if st.button(f"❌ Supprimer {tch_a_suppr}", type="secondary", key="btn_del_tch"):
                            conn = get_db_connection()
                            c = conn.cursor()
                            c.execute("DELETE FROM taches_ref WHERE nom = ?", (tch_a_suppr,))
                            conn.commit()
                            conn.close()
                            st.session_state["sync_notif"] = f"🗑️ Corps d'état {tch_a_suppr} supprimé."
                            st.rerun()

            # 3. MODULE PROFILS & PHOTOS
            elif mod_actuel == "mod_profils":
                st.markdown("### 👥 Gestion des Profils & Photos (Conducteurs & Ouvriers)")
                tab_conducteurs, tab_ouvriers = st.tabs(["👷 Profils Conducteurs", "👷 Profils Ouvriers"])

                with tab_conducteurs:
                    cond_choisi_tag = st.radio("Conducteur à modifier :", ["c1", "c2"], format_func=lambda x: f"Conducteur 1 ({nom_c1})" if x == 'c1' else f"Conducteur 2 ({nom_c2})", horizontal=True)
                    nom_actuel = nom_c1 if cond_choisi_tag == 'c1' else nom_c2
                    photo_actuelle_cond = get_photo_path(cond_choisi_tag)

                    col_cp, col_ci = st.columns([1, 2])
                    with col_cp:
                        if photo_actuelle_cond:
                            st.image(photo_actuelle_cond, caption=f"Photo : {nom_actuel}", width=140)
                        else:
                            st.info("Aucune photo.")

                    with col_ci:
                        nouveau_nom_c = st.text_input("Nom affiché :", value=nom_actuel, key=f"input_nom_cond_{cond_choisi_tag}")
                        nouvelle_photo_c = st.file_uploader("Photo du conducteur :", type=["jpg", "jpeg", "png"], key=f"upload_photo_cond_{cond_choisi_tag}")

                        if st.button("💾 Enregistrer le profil conducteur", type="primary", key=f"btn_save_cond_{cond_choisi_tag}"):
                            nom_net = nouveau_nom_c.strip() or ("Conducteur 1" if cond_choisi_tag == 'c1' else "Conducteur 2")
                            conn = get_db_connection()
                            c = conn.cursor()
                            c.execute("UPDATE conducteurs_meta SET nom_affiche = ? WHERE tag = ?", (nom_net, cond_choisi_tag))
                            conn.commit()
                            conn.close()

                            if nouvelle_photo_c is not None:
                                ext = nouvelle_photo_c.name.split(".")[-1].lower()
                                nom_f = f"{cond_choisi_tag}.{ext}"
                                for old_ext in [".jpg", ".jpeg", ".png"]:
                                    ancien_f = os.path.join(PHOTOS_DIR, f"{cond_choisi_tag}{old_ext}")
                                    if os.path.exists(ancien_f):
                                        os.remove(ancien_f)
                                chemin_save = os.path.join(PHOTOS_DIR, nom_f)
                                img = Image.open(nouvelle_photo_c)
                                img.save(chemin_save)

                            st.session_state["sync_notif"] = f"✅ Profil mis à jour pour {nom_net} !"
                            st.rerun()

                with tab_ouvriers:
                    df_w_admin = get_workers_df()
                    subtab_edit, subtab_add, subtab_del = st.tabs(["✏️ Modifier un ouvrier", "➕ Ajouter un ouvrier", "🗑️ Supprimer"])

                    with subtab_edit:
                        ouvrier_sel = st.selectbox("Ouvrier à modifier :", df_w_admin["nom"].tolist(), key="sel_ouvrier_tab_unifie")
                        photo_actuelle_ouv = get_photo_path(ouvrier_sel)

                        col_op, col_oi = st.columns([1, 2])
                        with col_op:
                            if photo_actuelle_ouv:
                                st.image(photo_actuelle_ouv, caption=f"Photo : {ouvrier_sel}", width=140)
                            else:
                                st.info("Aucune photo.")

                        with col_oi:
                            nouveau_nom_ouv = st.text_input("Nom complet :", value=ouvrier_sel, key=f"edit_nom_w_{ouvrier_sel}")
                            nouvelle_photo_ouv = st.file_uploader("Photo de l'ouvrier :", type=["jpg", "jpeg", "png"], key=f"upload_photo_w_{ouvrier_sel}")

                            if st.button("💾 Enregistrer les modifications", type="primary", key=f"btn_save_w_{ouvrier_sel}"):
                                nom_propre = nouveau_nom_ouv.strip()
                                conn = get_db_connection()
                                c = conn.cursor()

                                if nom_propre and nom_propre != ouvrier_sel:
                                    try:
                                        c.execute("UPDATE workers SET nom = ? WHERE nom = ?", (nom_propre, ouvrier_sel))
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
                                st.session_state["sync_notif"] = f"✅ Profil mis à jour pour {nom_ref} !"
                                st.rerun()

                    with subtab_add:
                        col_add1, col_add2 = st.columns(2)
                        with col_add1:
                            nom_nouveau = st.text_input("Nom et prénom :", key="in_new_worker_nom_tab")
                            chantiers_options = get_all_chantiers()
                            chantier_init = st.selectbox("Chantier initial :", chantiers_options, key="sel_new_worker_ch_tab")
                        with col_add2:
                            photo_nouvel_ouvrier = st.file_uploader("Photo (Optionnel) :", type=["jpg", "jpeg", "png"], key=upload_new_worker_photo_tab)

                        if st.button("➕ Ajouter l'ouvrier", type="primary", key="btn_add_worker_tab"):
                            nom_nettoye = nom_nouveau.strip()
                            if nom_nettoye:
                                conn = get_db_connection()
                                c = conn.cursor()
                                try:
                                    c.execute("INSERT INTO workers (nom, chantier_fixe) VALUES (?, ?)", (nom_nettoye, chantier_init))
                                    conn.commit()
                                    conn.close()

                                    if photo_nouvel_ouvrier is not None:
                                        ext = photo_nouvel_ouvrier.name.split(".")[-1].lower()
                                        nom_fichier = f"{nom_nettoye.replace(' ', '_')}.{ext}"
                                        chemin = os.path.join(PHOTOS_DIR, nom_fichier)
                                        img = Image.open(photo_nouvel_ouvrier)
                                        img.save(chemin)

                                    st.session_state["sync_notif"] = f"✅ {nom_nettoye} a été ajouté avec succès !"
                                    st.rerun()
                                except sqlite3.IntegrityError:
                                    conn.close()
                                    st.error("Cet ouvrier est déjà enregistré.")

                    with subtab_del:
                        ouvrier_a_del = st.selectbox("Ouvrier à supprimer :", df_w_admin["nom"].tolist(), key="sel_ouvrier_suppression_tab")
                        if st.button(f"❌ Supprimer définitivement {ouvrier_a_del}", type="secondary", key="btn_del_worker_tab"):
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

                            st.session_state["sync_notif"] = f"🗑️ {ouvrier_a_del} supprimé de la base."
                            st.rerun()

            # 4. MODULE CHANTIERS / CONDUCTEURS
            elif mod_actuel == "mod_chantiers_cond":
                st.markdown("### 🏗️ Attribution des Chantiers aux Conducteurs")
                chantiers_disponibles = [c for c in get_all_chantiers() if c != "EN ATTENTE / DEPOT"]

                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    st.markdown(f"##### 👷 {nom_c1}")
                    actuels_c1 = get_chantiers_conducteur("c1")
                    nouveaux_c1 = st.multiselect("Chantiers sous sa responsabilité :", options=chantiers_disponibles, default=actuels_c1, key="ms_admin_assign_c1")

                with col_c2:
                    st.markdown(f"##### 👷 {nom_c2}")
                    actuels_c2 = get_chantiers_conducteur("c2")
                    nouveaux_c2 = st.multiselect("Chantiers sous sa responsabilité :", options=chantiers_disponibles, default=actuels_c2, key="ms_admin_assign_c2")

                if st.button("💾 Sauvegarder les attributions", type="primary", use_container_width=True):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("DELETE FROM conducteur_chantiers WHERE conducteur_tag = 'c1'")
                    for ch in nouveaux_c1:
                        c.execute("INSERT INTO conducteur_chantiers (conducteur_tag, chantier) VALUES ('c1', ?)", (ch,))

                    c.execute("DELETE FROM conducteur_chantiers WHERE conducteur_tag = 'c2'")
                    for ch in nouveaux_c2:
                        c.execute("INSERT INTO conducteur_chantiers (conducteur_tag, chantier) VALUES ('c2', ?)", (ch,))

                    conn.commit()
                    conn.close()
                    st.session_state["sync_notif"] = f"🔄 Attributions mises à jour !"
                    st.rerun()

            # 5. MODULE EQUIPES PAR CHANTIER
            elif mod_actuel == "mod_equipes":
                st.markdown("### ⚡ Définir l'équipe autorisée sur un chantier")
                chantiers_dispos = [c for c in get_all_chantiers() if c != "EN ATTENTE / DEPOT"]
                ch_cible = st.selectbox("Chantier à configurer :", chantiers_dispos, key="adm_ch_cible")

                df_w_admin = get_workers_df()
                tous_les_noms = df_w_admin["nom"].tolist()
                actuels = df_w_admin[df_w_admin["chantier_fixe"] == ch_cible]["nom"].tolist()

                nouveaux_membres = st.multiselect(f"Ouvriers travaillant sur {ch_cible} :", options=tous_les_noms, default=actuels, key=f"ms_adm_{ch_cible}")

                if st.button(f"💾 Verrouiller l'équipe de {ch_cible}", type="primary", use_container_width=True):
                    conn = get_db_connection()
                    c = conn.cursor()
                    for nom in actuels:
                        if nom not in nouveaux_membres:
                            c.execute("UPDATE workers SET chantier_fixe = 'EN ATTENTE / DEPOT' WHERE nom = ?", (nom,))

                    for nom in nouveaux_membres:
                        c.execute("UPDATE workers SET chantier_fixe = ? WHERE nom = ?", (ch_cible, nom))

                    conn.commit()
                    conn.close()
                    st.session_state["sync_notif"] = f"🔄 Équipe verrouillée pour {ch_cible} ({len(nouveaux_membres)} ouvriers) !"
                    st.rerun()

            # 6. MODULE TRANSFERT
            elif mod_actuel == "mod_transfert":
                st.markdown("### 🔄 Transférer un ouvrier vers un autre chantier")
                df_w_admin = get_workers_df()

                ouvrier_sel = st.selectbox("Sélectionner l'ouvrier à déplacer :", df_w_admin["nom"].tolist(), key="ouv_transf_sel")
                infos_o = df_w_admin[df_w_admin["nom"] == ouvrier_sel].iloc[0]
                ancien_ch = infos_o["chantier_fixe"]
                ouv_id = int(infos_o["id"])

                st.info(f"Chantier actuel : **{ancien_ch}**")

                chantiers_tous = get_all_chantiers()
                dest_ch = st.selectbox("Nouveau chantier de destination :", [c for c in chantiers_tous if c != ancien_ch], key="dest_ch_sel")

                if st.button(f"Confirmer le transfert vers {dest_ch}", type="primary", use_container_width=True):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("UPDATE workers SET chantier_fixe = ? WHERE id = ?", (dest_ch, ouv_id))
                    conn.commit()
                    conn.close()
                    st.session_state["sync_notif"] = f"🔄 Transfert effectué : {ouvrier_sel} ➔ {dest_ch}"
                    st.rerun()
