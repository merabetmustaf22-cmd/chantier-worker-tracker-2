import os
import io
import glob
import sqlite3
from datetime import date, datetime
import pandas as pd
from PIL import Image
import streamlit as st

# Moteur Excel sécurisé
try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    OPENPYXL_DISPO = True
except ImportError:
    OPENPYXL_DISPO = False

st.set_page_config(
    page_title="Suivi Chantier & Étanchéité",
    page_icon="🏗️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Injection CSS Mobile Tactile
st.markdown("""
<style>
    @media (max-width: 768px) {
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            padding-left: 0.6rem !important;
            padding-right: 0.6rem !important;
        }
        h1 { font-size: 1.4rem !important; }
        h2 { font-size: 1.2rem !important; }
        h3 { font-size: 1.1rem !important; }
        .stButton>button {
            height: 48px !important;
            font-size: 15px !important;
            font-weight: 600 !important;
            border-radius: 10px !important;
            margin-top: 4px !important;
            margin-bottom: 4px !important;
        }
    }
    .worker-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

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

def generer_classeur_par_chantier_separe(df_mois, mois_label):
    if not OPENPYXL_DISPO:
        return None

    wb = openpyxl.Workbook()
    ws_sum = wb.active
    ws_sum.title = "Synthèse Générale"
    ws_sum.views.sheetView[0].showGridLines = True

    BLEU_TITRE = "0F2537"
    BLEU_HEADER = "1E3A5F"
    BLEU_TOTAL = "E2E8F0"
    GRIS_ZEBRA = "F8FAFC"
    BORDURE_COLOR = "CBD5E1"

    thin_border = Border(
        left=Side(style='thin', color=BORDURE_COLOR),
        right=Side(style='thin', color=BORDURE_COLOR),
        top=Side(style='thin', color=BORDURE_COLOR),
        bottom=Side(style='thin', color=BORDURE_COLOR)
    )

    ws_sum.merge_cells("A1:F1")
    ws_sum["A1"] = f"RÉCAPITULATIF DE TOUS LES CHANTIERS — {mois_label.upper()}"
    ws_sum["A1"].font = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    ws_sum["A1"].fill = PatternFill(start_color=BLEU_TITRE, end_color=BLEU_TITRE, fill_type="solid")
    ws_sum["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws_sum.row_dimensions[1].height = 36

    headers_sum = ["Chantier", "Ouvriers Déployés", "Total Jours Payés", "Production Étanchéité (m²)", "Total Lignes Saisies", "Dernier Conducteur"]
    ws_sum.append([])
    ws_sum.append(headers_sum)
    ws_sum.row_dimensions[3].height = 26

    for c_i in range(1, len(headers_sum) + 1):
        c = ws_sum.cell(row=3, column=c_i)
        c.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        c.fill = PatternFill(start_color=BLEU_HEADER, end_color=BLEU_HEADER, fill_type="solid")
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = thin_border

    chantiers_group = df_mois.groupby("Chantier")
    row_sum_idx = 4
    tot_glob_ouv = 0
    tot_glob_j = 0.0
    tot_glob_m2 = 0.0

    for ch_nom, ch_df in chantiers_group:
        nb_ouv = ch_df["Ouvrier"].nunique()
        p_cnt = sum(1 for v in ch_df["Statut"] if "Présent" in str(v))
        d_cnt = sum(1 for v in ch_df["Statut"] if "1/2" in str(v))
        j_payes_ch = p_cnt + (d_cnt * 0.5)
        m2_ch = ch_df[(ch_df["Unite"] == "m²") & (ch_df["Quantite"] > 0)]["Quantite"].sum()
        cond_dernier = ch_df["Conducteur"].iloc[-1] if not ch_df.empty else "-"

        vals_sum = [ch_nom, nb_ouv, j_payes_ch, round(m2_ch, 1), len(ch_df), cond_dernier]
        ws_sum.append(vals_sum)
        ws_sum.row_dimensions[row_sum_idx].height = 20

        is_even = (row_sum_idx % 2 == 0)
        fill_c = PatternFill(start_color=GRIS_ZEBRA if is_even else "FFFFFF", end_color=GRIS_ZEBRA if is_even else "FFFFFF", fill_type="solid")

        for c_i in range(1, len(headers_sum) + 1):
            c = ws_sum.cell(row=row_sum_idx, column=c_i)
            c.font = Font(name="Calibri", size=9)
            c.border = thin_border
            c.fill = fill_c
            if c_i in [2, 3, 4, 5]:
                c.alignment = Alignment(horizontal="center", vertical="center")
            else:
                c.alignment = Alignment(horizontal="left", vertical="center")

        tot_glob_ouv += nb_ouv
        tot_glob_j += j_payes_ch
        tot_glob_m2 += m2_ch
        row_sum_idx += 1

    ws_sum.append(["TOTAL GÉNÉRAL", tot_glob_ouv, tot_glob_j, round(tot_glob_m2, 1), len(df_mois), "-"])
    ws_sum.row_dimensions[row_sum_idx].height = 24
    for c_i in range(1, len(headers_sum) + 1):
        c = ws_sum.cell(row=row_sum_idx, column=c_i)
        c.font = Font(name="Calibri", size=10, bold=True, color="000000")
        c.fill = PatternFill(start_color=BLEU_TOTAL, end_color=BLEU_TOTAL, fill_type="solid")
        c.border = thin_border
        if c_i in [2, 3, 4, 5]:
            c.alignment = Alignment(horizontal="center", vertical="center")

    for col in ws_sum.columns:
        if col[0].row < 3:
            continue
        max_len = max(len(str(c.value or '')) for c in col)
        ws_sum.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 4, 15)

    for ch_nom, ch_df in chantiers_group:
        safe_title = ch_nom.replace("/", "-").replace("\\", "-").replace("?", "").replace("*", "")[:28]
        ws_ch = wb.create_sheet(title=safe_title)
        ws_ch.views.sheetView[0].showGridLines = True

        ws_ch.merge_cells("A1:I1")
        ws_ch["A1"] = f"CHANTIER : {ch_nom.upper()} — BILAN MENSUEL ({mois_label.upper()})"
        ws_ch["A1"].font = Font(name="Calibri", size=12, bold=True, color="FFFFFF")
        ws_ch["A1"].fill = PatternFill(start_color=BLEU_TITRE, end_color=BLEU_TITRE, fill_type="solid")
        ws_ch["A1"].alignment = Alignment(horizontal="center", vertical="center")
        ws_ch.row_dimensions[1].height = 36

        ch_ouvriers_cnt = ch_df["Ouvrier"].nunique()
        ch_p_cnt = sum(1 for v in ch_df["Statut"] if "Présent" in str(v))
        ch_d_cnt = sum(1 for v in ch_df["Statut"] if "1/2" in str(v))
        ch_j_payes = ch_p_cnt + (ch_d_cnt * 0.5)
        ch_m2 = ch_df[(ch_df["Unite"] == "m²") & (ch_df["Quantite"] > 0)]["Quantite"].sum()

        ws_ch.merge_cells("A2:C2")
        ws_ch["A2"] = f"Effectif actif : {ch_ouvriers_cnt} ouvriers | Total Jours Payés : {ch_j_payes} j"
        ws_ch["A2"].font = Font(name="Calibri", size=9, bold=True, color="1E3A5F")

        ws_ch.merge_cells("D2:I2")
        ws_ch["D2"] = f"Production totale étanchéité : {round(ch_m2, 1)} m² | Saisies : {len(ch_df)}"
        ws_ch["D2"].font = Font(name="Calibri", size=9, italic=True, color="555555")
        ws_ch["D2"].alignment = Alignment(horizontal="right")
        ws_ch.row_dimensions[2].height = 20

        headers_ch = ["Date", "Conducteur", "Ouvrier", "Statut", "Tâche / Corps d'état", "Production", "Qualité", "Observation", "Score"]
        ws_ch.append([])
        ws_ch.append(headers_ch)
        ws_ch.row_dimensions[4].height = 24

        for c_i in range(1, len(headers_ch) + 1):
            c = ws_ch.cell(row=4, column=c_i)
            c.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
            c.fill = PatternFill(start_color=BLEU_HEADER, end_color=BLEU_HEADER, fill_type="solid")
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = thin_border

        row_ch_idx = 5
        for _, r in ch_df.iterrows():
            prod_val = "Bricol" if r["Unite"] == "Sans métrage" else (f"{r['Quantite']} {r['Unite']}" if r["Quantite"] > 0 else "-")
            vals_ch = [r["Date"], r["Conducteur"], r["Ouvrier"], r["Statut"], r["Tâche"], prod_val, r["Qualité"], r["Observation"], r["Score"]]
            ws_ch.append(vals_ch)
            ws_ch.row_dimensions[row_ch_idx].height = 20

            is_even = (row_ch_idx % 2 == 0)
            fill_c = PatternFill(start_color=GRIS_ZEBRA if is_even else "FFFFFF", end_color=GRIS_ZEBRA if is_even else "FFFFFF", fill_type="solid")

            for c_i in range(1, len(headers_ch) + 1):
                c = ws_ch.cell(row=row_ch_idx, column=c_i)
                c.font = Font(name="Calibri", size=9)
                c.border = thin_border
                c.fill = fill_c
                if c_i in [1, 4, 7, 9]:
                    c.alignment = Alignment(horizontal="center", vertical="center")
                elif c_i == 6:
                    c.alignment = Alignment(horizontal="right", vertical="center")
                else:
                    c.alignment = Alignment(horizontal="left", vertical="center")
            row_ch_idx += 1

        for col in ws_ch.columns:
            if col[0].row < 4:
                continue
            max_len = max(len(str(c.value or '')) for c in col)
            ws_ch.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 4, 13)

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


# Notifications
if "sync_notif" not in st.session_state:
    st.session_state["sync_notif"] = None

if st.session_state["sync_notif"]:
    st.success(st.session_state["sync_notif"])

st.title("🏗️ Suivi Chantier & Étanchéité")

dict_conducteurs = get_conducteurs_dict()
nom_c1 = dict_conducteurs.get("c1", "Conducteur 1")
nom_c2 = dict_conducteurs.get("c2", "Conducteur 2")

menu_general = st.radio(
    "Espace de travail",
    [f"👷 Espace {nom_c1}", f"👷 Espace {nom_c2}", "🔐 Espace Admin (Direction)"],
    horizontal=False
)

def interface_saisie_conducteur(conducteur_id_tag, default_nom):
    photo_cond = get_photo_path(conducteur_id_tag)
    
    col_h1, col_h2 = st.columns([1, 4])
    with col_h1:
        if photo_cond:
            st.image(photo_cond, width=65)
        else:
            st.markdown("<div style='font-size:40px;text-align:center;'>👷</div>", unsafe_allow_html=True)
    with col_h2:
        st.subheader(f"Pointage — {default_nom}")

    date_choisie = st.date_input("📅 Date", value=date.today(), key=f"date_{conducteur_id_tag}")
    chantiers_autorises = get_chantiers_conducteur(conducteur_id_tag)

    if not chantiers_autorises:
        st.warning(f"⚠️ Aucun chantier attribué à {default_nom}.\n\nDemandez à l'Admin de vous affecter vos chantiers.")
        return

    chantier_choisi = st.selectbox("📍 Chantier", chantiers_autorises, key=f"ch_sel_{conducteur_id_tag}")
    date_str = str(date_choisie)
    deja_fait = est_deja_valide(date_str, chantier_choisi)

    if deja_fait:
        st.info(f"🟢 **Pointage déjà enregistré pour {chantier_choisi} le {date_str}.**")

    df_w = get_workers_df()
    equipe_active = df_w[df_w["chantier_fixe"] == chantier_choisi]

    st.markdown(f"**Équipe active :** `{len(equipe_active)}` ouvrier(s)")

    if equipe_active.empty:
        st.warning(f"⚠️ Aucun ouvrier sur {chantier_choisi}.")
    else:
        donnees_ouvriers = {}
        toutes_les_taches = get_all_taches()

        for _, row in equipe_active.iterrows():
            w_id = row['id']
            w_nom = row['nom']
            photo_p = get_photo_path(w_nom)

            st.markdown(f"<div class='worker-card'>", unsafe_allow_html=True)
            col_av, col_tx = st.columns([1, 4])
            with col_av:
                if photo_p:
                    st.image(photo_p, width=55)
                else:
                    st.markdown("<div style='font-size:32px;text-align:center;'>👷</div>", unsafe_allow_html=True)
            with col_tx:
                st.markdown(f"**{w_nom}**")

            st_val = st.selectbox("Statut :", [
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
                tache_val = st.selectbox("Tâche / Activité :", toutes_les_taches, key=f"tch_{conducteur_id_tag}_{w_id}")
                est_bricol_defaut = ("BRICOL" in tache_val.upper()) or (tache_val in ["DIVERS", "nettoyage", "PONSAGE"])
                type_travail = st.selectbox("Type travail :", ["Métrage (m² / ml)", "Bricol / Sans métrage"], index=1 if est_bricol_defaut else 0, key=f"typ_{conducteur_id_tag}_{w_id}")

                if type_travail == "Métrage (m² / ml)":
                    col_q, col_ap = st.columns(2)
                    with col_q:
                        qte_val = st.number_input("Production :", min_value=0.0, step=1.0, value=25.0, key=f"qte_{conducteur_id_tag}_{w_id}")
                        unite_val = "m²"
                    with col_ap:
                        apprec_val = st.selectbox("Qualité :", ["🟢 Conforme / Soigné", "🟡 Moyen / Acceptable", "🔴 Non conforme / À reprendre"], key=f"app_{conducteur_id_tag}_{w_id}")
                    obs_val = st.text_input("Observation libre :", placeholder="Ex: terrasse sud, relevés...", key=f"obs_{conducteur_id_tag}_{w_id}")
                else:
                    unite_val = "Sans métrage"
                    qte_val = 1.0
                    apprec_val = st.selectbox("Qualité :", ["🟢 Conforme / Soigné", "🟡 Moyen / Acceptable", "🔴 Non conforme / À reprendre"], key=f"app_br_{conducteur_id_tag}_{w_id}")
                    obs_val = st.text_input("Détail du bricolage :", placeholder="Ex: regard, solin...", key=f"obs_br_{conducteur_id_tag}_{w_id}")
            else:
                obs_val = st.text_input("Motif absence :", placeholder="Ex: congé, maladie...", key=f"obs_abs_{conducteur_id_tag}_{w_id}")

            st.markdown("</div>", unsafe_allow_html=True)

            donnees_ouvriers[w_id] = {
                "statut": st_val,
                "tache": tache_val,
                "quantite": qte_val,
                "unite": unite_val,
                "appreciation": apprec_val,
                "observation": obs_val
            }

        label_bouton = "🔄 Mettre à jour la journée" if deja_fait else "💾 Valider la journée de l'équipe"

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
            st.session_state["sync_notif"] = f"✅ Journée validée par {default_nom} à {heure_validation} pour {chantier_choisi} !"
            st.rerun()

# ==============================================================================
# ESPACES CONDUCTEURS
# ==============================================================================
if menu_general == f"👷 Espace {nom_c1}":
    interface_saisie_conducteur("c1", nom_c1)

elif menu_general == f"👷 Espace {nom_c2}":
    interface_saisie_conducteur("c2", nom_c2)

# ==============================================================================
# ESPACE ADMIN (TITRES SIMPLES & PROPRES)
# ==============================================================================
elif menu_general == "🔐 Espace Admin (Direction)":
    st.subheader("Accès Sécurisé - Administration")

    if "admin_logged_in" not in st.session_state:
        st.session_state["admin_logged_in"] = False

    if not st.session_state["admin_logged_in"]:
        mdp = st.text_input("Mot de passe Admin", type="password", placeholder="Entrez le mot de passe...")
        if st.button("Connexion", type="primary", use_container_width=True):
            if mdp == ADMIN_PASSWORD:
                st.session_state["admin_logged_in"] = True
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")
    else:
        if st.button("🚪 Déconnexion", use_container_width=True):
            st.session_state["admin_logged_in"] = False
            st.session_state["admin_active_module"] = None
            st.rerun()

        conn = get_db_connection()
        total_p = conn.cursor().execute("SELECT COUNT(*) FROM pointages").fetchone()[0]
        conn.close()
        st.info(f"📊 Registre : **{total_p} pointages enregistrés**")

        if "admin_active_module" not in st.session_state:
            st.session_state["admin_active_module"] = None

        # ----------------------------------------------------------------------
        # TITRES COURTS, SIMPLES ET SANS PARENTHÈSES
        # ----------------------------------------------------------------------
        MODULES_ADMIN = [
            # 1. Actions Quotidiennes (Priorités)
            ("mod_rapport", "📊 Bilan Mensuel & Rapports"),
            ("mod_corriger", "✏️ Corriger un Pointage"),
            ("mod_transfert", "🔄 Transférer un Ouvrier"),
            
            # 2. Configurations & Éditions de Base
            ("mod_equipes", "⚡ Équipes par Chantier"),
            ("mod_chantiers_cond", "👷 Affecter les Chantiers"),
            ("mod_profils", "👥 Profils & Photos"),
            ("mod_chantiers_taches", "🏗️ Chantiers & Tâches"),
        ]

        if st.session_state["admin_active_module"] is None:
            st.markdown("### 🎛 Menu Administrateur")
            
            st.markdown("##### ⚡ Actions Quotidiennes")
            for tag, titre in MODULES_ADMIN[:3]:
                if st.button(titre, key=f"btn_case_{tag}", use_container_width=True):
                    st.session_state["admin_active_module"] = tag
                    st.rerun()

            st.markdown("##### ⚙️ Configurations & Éditions")
            for tag, titre in MODULES_ADMIN[3:]:
                if st.button(titre, key=f"btn_case_{tag}", use_container_width=True):
                    st.session_state["admin_active_module"] = tag
                    st.rerun()

        else:
            mod_actuel = st.session_state["admin_active_module"]

            if st.button("⬅️ Retour au Menu Admin", type="secondary", use_container_width=True):
                st.session_state["admin_active_module"] = None
                st.rerun()

            st.markdown("---")

            # 1. BILAN MENSUEL ET RAPPORTS
            if mod_actuel == "mod_rapport":
                st.markdown("### 📊 Bilan Mensuel & Rapports")

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
                    ORDER BY p.chantier ASC, p.date_jour DESC, p.id DESC
                """
                df_all = pd.read_sql_query(query_admin, conn)
                conn.close()

                if df_all.empty:
                    st.warning("⚠️ Aucune donnée enregistrée.")
                else:
                    df_all["Mois_Annee"] = df_all["Date"].str.slice(0, 7)
                    mois_dispos = sorted(df_all["Mois_Annee"].unique().tolist(), reverse=True)

                    c_m1, c_m2 = st.columns([1, 2])
                    with c_m1:
                        mois_choisi = st.selectbox("📅 Mois :", mois_dispos)
                    with c_m2:
                        filtre_ch = st.selectbox("📍 Chantier :", ["Tous les chantiers"] + sorted(df_all["Chantier"].unique().tolist()))

                    df_mois_actuel = df_all[df_all["Mois_Annee"] == mois_choisi].copy()
                    if filtre_ch != "Tous les chantiers":
                        df_mois_actuel = df_mois_actuel[df_mois_actuel["Chantier"] == filtre_ch]

                    total_ouv_actifs = df_mois_actuel["Ouvrier"].nunique()
                    p_c = sum(1 for v in df_mois_actuel["Statut"] if "Présent" in str(v))
                    d_c = sum(1 for v in df_mois_actuel["Statut"] if "1/2" in str(v))
                    j_payes = p_c + (d_c * 0.5)
                    m2_tot = df_mois_actuel[(df_mois_actuel["Unite"] == "m²") & (df_mois_actuel["Quantite"] > 0)]["Quantite"].sum()

                    k1, k2 = st.columns(2)
                    k1.metric("Ouvriers Actifs", f"{total_ouv_actifs}")
                    k2.metric("Jours Payés", f"{j_payes} j")

                    k3, k4 = st.columns(2)
                    k3.metric("Absences", f"{sum(1 for v in df_mois_actuel['Statut'] if 'Absence' in str(v))}")
                    k4.metric("Production (m²)", f"{m2_tot:.1f} m²")

                    st.markdown("---")
                    st.markdown("#### 1. Synthèse par Chantier")
                    ch_synth = []
                    for ch_name, grp in df_mois_actuel.groupby("Chantier"):
                        p_cnt = sum(1 for v in grp["Statut"] if "Présent" in str(v))
                        d_cnt = sum(1 for v in grp["Statut"] if "1/2" in str(v))
                        a_cnt = sum(1 for v in grp["Statut"] if "Absence" in str(v))
                        j_val = p_cnt + (d_cnt * 0.5)
                        m2_val = grp[(grp["Unite"] == "m²") & (grp["Quantite"] > 0)]["Quantite"].sum()

                        ch_synth.append({
                            "Chantier": ch_name,
                            "Effectif": grp["Ouvrier"].nunique(),
                            "Présents (J)": p_cnt,
                            "1/2 J": d_cnt,
                            "Absences": a_cnt,
                            "Jours Payés": f"{j_val} j",
                            "Métré (m²)": f"{m2_val:.1f} m²"
                        })

                    df_ch_synth = pd.DataFrame(ch_synth)
                    st.dataframe(df_ch_synth, use_container_width=True, hide_index=True)

                    st.markdown("---")
                    st.markdown("#### 2. Registre Détaillé des Pointages")
                    df_vue_detail = df_mois_actuel.copy()
                    df_vue_detail["Production"] = df_vue_detail.apply(
                        lambda r: "Bricol" if r["Unite"] == "Sans métrage" else (f"{r['Quantite']} {r['Unite']}" if r["Quantite"] > 0 else "-"),
                        axis=1
                    )
                    cols_finales = ["Chantier", "Date", "Conducteur", "Ouvrier", "Statut", "Tâche", "Production", "Qualité", "Score"]
                    st.dataframe(df_vue_detail[cols_finales], use_container_width=True, hide_index=True)

                    st.markdown("#### 📥 Téléchargements")
                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        if OPENPYXL_DISPO:
                            excel_separe = generer_classeur_par_chantier_separe(df_mois_actuel, mois_choisi)
                            st.download_button(
                                f"📗 Télécharger Excel (.xlsx) par Chantier",
                                data=excel_separe,
                                file_name=f"bilan_chantiers_{mois_choisi}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                        else:
                            st.caption("💡 Le CSV ci-contre s'ouvre parfaitement dans Excel.")
                    with col_dl2:
                        csv_propre = df_vue_detail[cols_finales].to_csv(index=False, sep=";", encoding="utf-8-sig")
                        st.download_button(
                            f"📥 Télécharger CSV ({mois_choisi})",
                            data=csv_propre.encode("utf-8-sig"),
                            file_name=f"registre_{mois_choisi}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )

            # 2. CORRIGER UN POINTAGE
            elif mod_actuel == "mod_corriger":
                st.markdown("### ✏️ Corriger un Pointage")
                
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
                        COALESCE(p.observation, '-') AS [Observation]
                    FROM pointages p
                    LEFT JOIN workers w ON p.worker_id = w.id
                    ORDER BY p.date_jour DESC, p.id DESC
                """
                df_pts = pd.read_sql_query(query_admin, conn)
                conn.close()

                if df_pts.empty:
                    st.info("Aucun pointage à corriger pour le moment.")
                else:
                    df_pts["label"] = df_pts.apply(
                        lambda r: f"ID #{r['ID']} | {r['Date']} | {r['Chantier']} | {r['Ouvrier']}",
                        axis=1
                    )
                    ligne_choisie = st.selectbox("Sélectionner la ligne :", df_pts["label"].tolist(), key="sel_pt_correction_prio")
                    row_sel = df_pts[df_pts["label"] == ligne_choisie].iloc[0]
                    pt_id = int(row_sel["ID"])

                    st.info(f"**{row_sel['Ouvrier']}** — {row_sel['Chantier']} ({row_sel['Date']})")

                    statuts_possibles = ["Présent (Journée)", "1/2 journée", "Absence Autorisée (Congé/Maladie)", "Absence Non Autorisée (Injustifiée)"]
                    idx_st = statuts_possibles.index(row_sel["Statut"]) if row_sel["Statut"] in statuts_possibles else 0
                    mod_statut = st.selectbox("Statut :", statuts_possibles, index=idx_st, key=f"mod_st_{pt_id}")
                    
                    toutes_les_taches_dispos = get_all_taches()
                    idx_tch = toutes_les_taches_dispos.index(row_sel["Tâche"]) if row_sel["Tâche"] in toutes_les_taches_dispos else 0
                    mod_tache = st.selectbox("Tâche :", toutes_les_taches_dispos, index=idx_tch, key=f"mod_tch_{pt_id}")

                    type_activite_mod = st.selectbox("Type :", ["Métrage (m² / ml)", "Bricol / Sans métrage"], index=1 if row_sel["Unite"] == "Sans métrage" else 0, key=f"mod_typ_{pt_id}")
                    if type_activite_mod == "Métrage (m² / ml)":
                        mod_qte = st.number_input("Quantité :", min_value=0.0, step=1.0, value=float(row_sel["Quantite"]), key=f"mod_qte_{pt_id}")
                        mod_unite = "m²"
                    else:
                        mod_qte = 1.0
                        mod_unite = "Sans métrage"

                    qualites_possibles = ["🟢 Conforme / Soigné", "🟡 Moyen / Acceptable", "🔴 Non conforme / À reprendre"]
                    idx_qual = qualites_possibles.index(row_sel["Qualité"]) if row_sel["Qualité"] in qualites_possibles else 0
                    mod_apprec = st.selectbox("Qualité :", qualites_possibles, index=idx_qual, key=f"mod_qual_{pt_id}")

                    mod_obs = st.text_input("Observation :", value=str(row_sel["Observation"]) if row_sel["Observation"] != "-" else "", key=f"mod_obs_{pt_id}")

                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        if st.button("💾 Enregistrer Correction", type="primary", use_container_width=True):
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
                            st.session_state["sync_notif"] = f"✅ Pointage #{pt_id} rectifié !"
                            st.rerun()

                    with col_b2:
                        if st.button("🗑️ Supprimer Pointage", type="secondary", use_container_width=True):
                            conn = get_db_connection()
                            c = conn.cursor()
                            c.execute("DELETE FROM pointages WHERE id = ?", (pt_id,))
                            conn.commit()
                            conn.close()
                            st.session_state["sync_notif"] = f"🗑️ Pointage #{pt_id} supprimé."
                            st.rerun()

            # 3. TRANSFÉRER UN OUVRIER
            elif mod_actuel == "mod_transfert":
                st.markdown("### 🔄 Transférer un Ouvrier")
                df_w_tr = get_workers_df()
                ouv_sel = st.selectbox("Ouvrier à transférer :", df_w_tr["nom"].tolist(), key="tr_o_prio")
                infos = df_w_tr[df_w_tr["nom"] == ouv_sel].iloc[0]
                st.info(f"Chantier actuel : **{infos['chantier_fixe']}**")
                dest_ch = st.selectbox("Vers chantier :", [c for c in get_all_chantiers() if c != infos["chantier_fixe"]], key="dest_ch_prio")

                if st.button("Confirmer le Transfert", type="primary", use_container_width=True):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("UPDATE workers SET chantier_fixe = ? WHERE id = ?", (dest_ch, int(infos["id"])))
                    conn.commit()
                    conn.close()
                    st.session_state["sync_notif"] = f"🔄 {ouv_sel} transféré vers {dest_ch} !"
                    st.rerun()

            # 4. ÉQUIPES PAR CHANTIER
            elif mod_actuel == "mod_equipes":
                st.markdown("### ⚡ Équipes par Chantier")
                ch_cible = st.selectbox("Chantier :", [c for c in get_all_chantiers() if c != "EN ATTENTE / DEPOT"], key="ch_eq_cfg")
                df_w_eq = get_workers_df()
                actuels = df_w_eq[df_w_eq["chantier_fixe"] == ch_cible]["nom"].tolist()
                nouv_eq = st.multiselect("Ouvriers affectés :", options=df_w_eq["nom"].tolist(), default=actuels, key=f"ms_eq_{ch_cible}_cfg")

                if st.button(f"💾 Verrouiller l'Équipe", type="primary", use_container_width=True):
                    conn = get_db_connection()
                    c = conn.cursor()
                    for nom in actuels:
                        if nom not in nouv_eq:
                            c.execute("UPDATE workers SET chantier_fixe = 'EN ATTENTE / DEPOT' WHERE nom = ?", (nom,))
                    for nom in nouv_eq:
                        c.execute("UPDATE workers SET chantier_fixe = ? WHERE nom = ?", (ch_cible, nom))
                    conn.commit()
                    conn.close()
                    st.session_state["sync_notif"] = f"🔄 Équipe de {ch_cible} verrouillée ({len(nouv_eq)} ouvriers) !"
                    st.rerun()

            # 5. AFFECTER LES CHANTIERS
            elif mod_actuel == "mod_chantiers_cond":
                st.markdown("### 👷 Affecter les Chantiers")
                ch_dispos = [c for c in get_all_chantiers() if c != "EN ATTENTE / DEPOT"]
                
                st.markdown(f"**{nom_c1}**")
                act_c1 = get_chantiers_conducteur("c1")
                nouv_c1 = st.multiselect("Chantiers c1 :", options=ch_dispos, default=act_c1, key="ms_c1_cfg")

                st.markdown(f"**{nom_c2}**")
                act_c2 = get_chantiers_conducteur("c2")
                nouv_c2 = st.multiselect("Chantiers c2 :", options=ch_dispos, default=act_c2, key="ms_c2_cfg")

                if st.button("💾 Sauvegarder les Affectations", type="primary", use_container_width=True):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("DELETE FROM conducteur_chantiers WHERE conducteur_tag = 'c1'")
                    for ch in nouv_c1:
                        c.execute("INSERT INTO conducteur_chantiers (conducteur_tag, chantier) VALUES ('c1', ?)", (ch,))
                    c.execute("DELETE FROM conducteur_chantiers WHERE conducteur_tag = 'c2'")
                    for ch in nouv_c2:
                        c.execute("INSERT INTO conducteur_chantiers (conducteur_tag, chantier) VALUES ('c2', ?)", (ch,))
                    conn.commit()
                    conn.close()
                    st.session_state["sync_notif"] = "🔄 Affectations sauvegardées !"
                    st.rerun()

            # 6. PROFILS & PHOTOS
            elif mod_actuel == "mod_profils":
                st.markdown("### 👥 Profils & Photos")
                tab_cond, tab_ouv = st.tabs(["👷 Conducteurs", "👷 Ouvriers"])

                with tab_cond:
                    c_tag = st.radio("Conducteur :", ["c1", "c2"], format_func=lambda x: f"Conducteur 1 ({nom_c1})" if x == 'c1' else f"Conducteur 2 ({nom_c2})")
                    n_act = nom_c1 if c_tag == 'c1' else nom_c2
                    ph_c = get_photo_path(c_tag)
                    if ph_c:
                        st.image(ph_c, width=120)
                    n_nom_c = st.text_input("Nom affiché :", value=n_act, key=f"in_nc_{c_tag}_cfg")
                    n_ph_c = st.file_uploader("Photo profil :", type=["jpg", "jpeg", "png"], key=f"up_pc_{c_tag}_cfg")
                    if st.button("💾 Enregistrer Profil Conducteur", type="primary", use_container_width=True):
                        n_propre = n_nom_c.strip() or ("Conducteur 1" if c_tag == 'c1' else "Conducteur 2")
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute("UPDATE conducteurs_meta SET nom_affiche = ? WHERE tag = ?", (n_propre, c_tag))
                        conn.commit()
                        conn.close()

                        if n_ph_c is not None:
                            ext = n_ph_c.name.split(".")[-1].lower()
                            nom_f = f"{c_tag}.{ext}"
                            for o_ext in [".jpg", ".jpeg", ".png"]:
                                old_path = os.path.join(PHOTOS_DIR, f"{c_tag}{o_ext}")
                                if os.path.exists(old_path):
                                    os.remove(old_path)
                            Image.open(n_ph_c).save(os.path.join(PHOTOS_DIR, nom_f))

                        st.session_state["sync_notif"] = f"✅ Conducteur {n_propre} mis à jour !"
                        st.rerun()

                with tab_ouv:
                    df_w_m = get_workers_df()
                    sub_ed, sub_ad, sub_dl = st.tabs(["✏️ Modifier", "➕ Ajouter", "🗑️ Supprimer"])
                    with sub_ed:
                        o_sel = st.selectbox("Sélectionner l'ouvrier :", df_w_m["nom"].tolist(), key="sel_ouv_cfg")
                        ph_o = get_photo_path(o_sel)
                        if ph_o:
                            st.image(ph_o, width=120)
                        n_nom_o = st.text_input("Nom complet :", value=o_sel, key=f"in_no_{o_sel}_cfg")
                        n_ph_o = st.file_uploader("Photo profil ouvrier :", type=["jpg", "jpeg", "png"], key=f"up_po_{o_sel}_cfg")

                        if st.button("💾 Enregistrer Modifications", type="primary", use_container_width=True):
                            nom_p = n_nom_o.strip()
                            conn = get_db_connection()
                            c = conn.cursor()
                            if nom_p and nom_p != o_sel:
                                try:
                                    c.execute("UPDATE workers SET nom = ? WHERE nom = ?", (nom_p, o_sel))
                                    conn.commit()
                                    o_cl = o_sel.replace(" ", "_")
                                    n_cl = nom_p.replace(" ", "_")
                                    for ext in [".jpg", ".jpeg", ".png"]:
                                        if os.path.exists(os.path.join(PHOTOS_DIR, f"{o_cl}{ext}")):
                                            os.rename(os.path.join(PHOTOS_DIR, f"{o_cl}{ext}"), os.path.join(PHOTOS_DIR, f"{n_cl}{ext}"))
                                    nom_ref = nom_p
                                except sqlite3.IntegrityError:
                                    conn.close()
                                    st.error("Ce nom existe déjà.")
                                    st.stop()
                            else:
                                nom_ref = o_sel

                            if n_ph_o is not None:
                                ext = n_ph_o.name.split(".")[-1].lower()
                                nom_f = f"{nom_ref.replace(' ', '_')}.{ext}"
                                Image.open(n_ph_o).save(os.path.join(PHOTOS_DIR, nom_f))

                            conn.close()
                            st.session_state["sync_notif"] = f"✅ Profil {nom_ref} mis à jour !"
                            st.rerun()

                    with sub_ad:
                        nom_nouv = st.text_input("Nom et prénom :", key="in_add_w_nom_cfg")
                        ch_init = st.selectbox("Chantier initial :", get_all_chantiers(), key="in_add_w_ch_cfg")
                        ph_nouv = st.file_uploader("Photo profil :", type=["jpg", "jpeg", "png"], key="in_add_w_ph_cfg")
                        if st.button("➕ Ajouter l'Ouvrier", type="primary", use_container_width=True):
                            n_net = nom_nouv.strip()
                            if n_net:
                                conn = get_db_connection()
                                c = conn.cursor()
                                try:
                                    c.execute("INSERT INTO workers (nom, chantier_fixe) VALUES (?, ?)", (n_net, ch_init))
                                    conn.commit()
                                    conn.close()
                                    if ph_nouv is not None:
                                        ext = ph_nouv.name.split(".")[-1].lower()
                                        Image.open(ph_nouv).save(os.path.join(PHOTOS_DIR, f"{n_net.replace(' ', '_')}.{ext}"))
                                    st.session_state["sync_notif"] = f"✅ {n_net} ajouté !"
                                    st.rerun()
                                except sqlite3.IntegrityError:
                                    conn.close()
                                    st.error("Cet ouvrier existe déjà.")

                    with sub_dl:
                        ouv_del_s = st.selectbox("Ouvrier à supprimer :", df_w_m["nom"].tolist(), key="sel_del_ouv_cfg")
                        if st.button(f"❌ Supprimer Définitivement", type="secondary", use_container_width=True):
                            conn = get_db_connection()
                            c = conn.cursor()
                            c.execute("DELETE FROM workers WHERE nom = ?", (ouv_del_s,))
                            conn.commit()
                            conn.close()
                            st.session_state["sync_notif"] = f"🗑️ {ouv_del_s} supprimé de la base."
                            st.rerun()

            # 7. CHANTIERS & TÂCHES
            elif mod_actuel == "mod_chantiers_taches":
                st.markdown("### 🏗️ Chantiers & Tâches")
                tab_ch, tab_tch = st.tabs(["📍 Chantiers", "🔨 Tâches"])

                with tab_ch:
                    liste_ch = get_all_chantiers()
                    nouveau_ch = st.text_input("Nouveau chantier :", key="in_add_ch_cfg")
                    if st.button("➕ Ajouter Chantier", type="primary", use_container_width=True):
                        n_c = nouveau_ch.strip()
                        if n_c:
                            conn = get_db_connection()
                            c = conn.cursor()
                            try:
                                c.execute("INSERT INTO chantiers_ref (nom) VALUES (?)", (n_c,))
                                conn.commit()
                                conn.close()
                                st.session_state["sync_notif"] = f"✅ Chantier {n_c} ajouté !"
                                st.rerun()
                            except sqlite3.IntegrityError:
                                conn.close()
                                st.error("Ce chantier existe déjà.")

                    st.markdown("---")
                    ch_a_renom = st.selectbox("Chantier à renommer :", liste_ch, key="sel_mod_ch_cfg")
                    ch_new_n = st.text_input("Nouveau libellé :", value=ch_a_renom, key="in_renom_ch_cfg")
                    if st.button("💾 Renommer Chantier", use_container_width=True):
                        n_cl = ch_new_n.strip()
                        if n_cl and n_cl != ch_a_renom:
                            conn = get_db_connection()
                            c = conn.cursor()
                            try:
                                c.execute("UPDATE chantiers_ref SET nom = ? WHERE nom = ?", (n_cl, ch_a_renom))
                                c.execute("UPDATE workers SET chantier_fixe = ? WHERE chantier_fixe = ?", (n_cl, ch_a_renom))
                                c.execute("UPDATE conducteur_chantiers SET chantier = ? WHERE chantier = ?", (n_cl, ch_a_renom))
                                c.execute("UPDATE pointages SET chantier = ? WHERE chantier = ?", (n_cl, ch_a_renom))
                                conn.commit()
                                conn.close()
                                st.session_state["sync_notif"] = f"✅ Chantier renommé vers {n_cl} !"
                                st.rerun()
                            except sqlite3.IntegrityError:
                                conn.close()
                                st.error("Ce nom existe déjà.")

                with tab_tch:
                    liste_tch = get_all_taches()
                    nouvelle_t = st.text_input("Nouvelle tâche :", key="in_add_tch_cfg")
                    if st.button("➕ Ajouter Tâche", type="primary", use_container_width=True):
                        n_t = nouvelle_t.strip()
                        if n_t:
                            conn = get_db_connection()
                            c = conn.cursor()
                            try:
                                c.execute("INSERT INTO taches_ref (nom) VALUES (?)", (n_t,))
                                conn.commit()
                                conn.close()
                                st.session_state["sync_notif"] = f"✅ Tâche {n_t} ajoutée !"
                                st.rerun()
                            except sqlite3.IntegrityError:
                                conn.close()
                                st.error("Cette tâche existe déjà.")
