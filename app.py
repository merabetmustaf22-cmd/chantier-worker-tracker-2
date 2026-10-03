import os
import io
import glob
import sqlite3
from datetime import date, datetime
import pandas as pd
from PIL import Image
import streamlit as st

# Moteur de style Excel
try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    OPENPYXL_DISPO = True
except ImportError:
    OPENPYXL_DISPO = False

st.set_page_config(
    page_title="Suivi de Chantier & Étanchéité",
    page_icon="🏗️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

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

# ==============================================================================
# GÉNÉRATEUR EXCEL MENSUEL MULTI-FEUILLES (AVEC TOTAUX AUTOMATIQUES)
# ==============================================================================
def generer_classeur_mensuel_complet(df_mois, mois_label):
    if not OPENPYXL_DISPO:
        return None

    wb = openpyxl.Workbook()
    
    # Couleurs du thème
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

    # -------------------------------------------------------------
    # FEUILLE 1 : SYNTHÈSE MENSUELLE OUVRIERS (PAIE & RH)
    # -------------------------------------------------------------
    ws1 = wb.active
    ws1.title = "Synthèse Mensuelle RH"
    ws1.views.sheetView[0].showGridLines = True

    ws1.merge_cells("A1:H1")
    ws1["A1"] = f"BILAN MENSUEL DES POINTAGES & EFFECTIFS — {mois_label.upper()}"
    ws1["A1"].font = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    ws1["A1"].fill = PatternFill(start_color=BLEU_TITRE, end_color=BLEU_TITRE, fill_type="solid")
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[1].height = 36

    headers_rh = [
        "Nom Ouvrier", "Dernier Chantier", "Jours Présents (1.0)", "1/2 Journées (0.5)", 
        "Absences", "Total Jours Payés", "Taux Présence", "Score Moyen"
    ]
    ws1.append([])
    ws1.append(headers_rh)
    ws1.row_dimensions[3].height = 26

    for col_i in range(1, len(headers_rh) + 1):
        cell = ws1.cell(row=3, column=col_i)
        cell.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color=BLEU_HEADER, end_color=BLEU_HEADER, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    # Calcul des totaux par ouvrier
    ouvriers_group = df_mois.groupby("Ouvrier")
    row_cur = 4
    total_pres_sum = 0
    total_demi_sum = 0
    total_abs_sum = 0
    total_paye_sum = 0.0

    for nom_ouv, grp in ouvriers_group:
        p_count = sum(1 for v in grp["Statut"] if "Présent" in str(v))
        d_count = sum(1 for v in grp["Statut"] if "1/2" in str(v))
        a_count = sum(1 for v in grp["Statut"] if "Absence" in str(v))
        j_payes = p_count + (d_count * 0.5)
        
        total_presents_possible = p_count + d_count + a_count
        taux_pres = f"{(j_payes / total_presents_possible * 100):.1f}%" if total_presents_possible > 0 else "0%"
        
        scores_valides = pd.to_numeric(grp["Score"], errors='coerce').dropna()
        score_moy = f"{scores_valides.mean():.1f}" if not scores_valides.empty else "-"
        dernier_ch = grp["Chantier"].iloc[-1] if not grp.empty else "-"

        vals = [nom_ouv, dernier_ch, p_count, d_count, a_count, j_payes, taux_pres, score_moy]
        ws1.append(vals)
        ws1.row_dimensions[row_cur].height = 20

        is_even = (row_cur % 2 == 0)
        fill_c = PatternFill(start_color=GRIS_ZEBRA if is_even else "FFFFFF", end_color=GRIS_ZEBRA if is_even else "FFFFFF", fill_type="solid")

        for c_i in range(1, len(headers_rh) + 1):
            c = ws1.cell(row=row_cur, column=c_i)
            c.font = Font(name="Calibri", size=9)
            c.border = thin_border
            c.fill = fill_c
            if c_i in [3, 4, 5, 6, 7, 8]:
                c.alignment = Alignment(horizontal="center", vertical="center")
            else:
                c.alignment = Alignment(horizontal="left", vertical="center")

        total_pres_sum += p_count
        total_demi_sum += d_count
        total_abs_sum += a_count
        total_paye_sum += j_payes
        row_cur += 1

    # Ligne TOTAL GÉNÉRAL
    ws1.append(["TOTAL GÉNÉRAL", "-", total_pres_sum, total_demi_sum, total_abs_sum, total_paye_sum, "-", "-"])
    ws1.row_dimensions[row_cur].height = 24
    for c_i in range(1, len(headers_rh) + 1):
        c = ws1.cell(row=row_cur, column=c_i)
        c.font = Font(name="Calibri", size=10, bold=True, color="000000")
        c.fill = PatternFill(start_color=BLEU_TOTAL, end_color=BLEU_TOTAL, fill_type="solid")
        c.border = thin_border
        if c_i in [3, 4, 5, 6, 7, 8]:
            c.alignment = Alignment(horizontal="center", vertical="center")
        else:
            c.alignment = Alignment(horizontal="left", vertical="center")

    for col in ws1.columns:
        if col[0].row < 3:
            continue
        max_len = max(len(str(c.value or '')) for c in col)
        ws1.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 4, 14)

    # -------------------------------------------------------------
    # FEUILLE 2 : SYNTHÈSE PRODUCTION & MÉTRÉS DU MOIS
    # -------------------------------------------------------------
    ws2 = wb.create_sheet(title="Production & Métrés")
    ws2.views.sheetView[0].showGridLines = True

    ws2.merge_cells("A1:E1")
    ws2["A1"] = f"TOTAL MÉTRÉS & PRODUCTION PAR TÂCHE — {mois_label.upper()}"
    ws2["A1"].font = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    ws2["A1"].fill = PatternFill(start_color=BLEU_TITRE, end_color=BLEU_TITRE, fill_type="solid")
    ws2["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws2.row_dimensions[1].height = 36

    headers_prod = ["Chantier", "Corps d'état / Tâche", "Quantité Totale", "Unité", "Nombre Interventions"]
    ws2.append([])
    ws2.append(headers_prod)
    ws2.row_dimensions[3].height = 26

    for col_i in range(1, len(headers_prod) + 1):
        cell = ws2.cell(row=3, column=col_i)
        cell.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color=BLEU_HEADER, end_color=BLEU_HEADER, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    # Filtrer les tâches actives
    df_travaux = df_mois[df_mois["Tâche"] != "-"].copy()
    df_travaux["Quantite_Num"] = pd.to_numeric(df_travaux["Quantite"], errors='coerce').fillna(0)
    
    prod_group = df_travaux.groupby(["Chantier", "Tâche", "Unite"]).agg(
        Total_Qte=("Quantite_Num", "sum"),
        Nb_Fois=("ID", "count")
    ).reset_index()

    row_cur2 = 4
    total_qte_m2 = 0.0

    for _, r in prod_group.iterrows():
        unite_lbl = r["Unite"]
        qte_val = r["Total_Qte"] if unite_lbl != "Sans métrage" else "-"
        if unite_lbl == "m²":
            total_qte_m2 += r["Total_Qte"]

        vals2 = [r["Chantier"], r["Tâche"], qte_val, unite_lbl, r["Nb_Fois"]]
        ws2.append(vals2)
        ws2.row_dimensions[row_cur2].height = 20

        is_even = (row_cur2 % 2 == 0)
        fill_c = PatternFill(start_color=GRIS_ZEBRA if is_even else "FFFFFF", end_color=GRIS_ZEBRA if is_even else "FFFFFF", fill_type="solid")

        for c_i in range(1, len(headers_prod) + 1):
            c = ws2.cell(row=row_cur2, column=c_i)
            c.font = Font(name="Calibri", size=9)
            c.border = thin_border
            c.fill = fill_c
            if c_i in [3, 4, 5]:
                c.alignment = Alignment(horizontal="center", vertical="center")
            else:
                c.alignment = Alignment(horizontal="left", vertical="center")
        row_cur2 += 1

    # Total m² en bas
    ws2.append(["TOTAL GÉNÉRAL MÉTRÉS (m²)", "-", round(total_qte_m2, 1), "m²", len(df_travaux)])
    ws2.row_dimensions[row_cur2].height = 24
    for c_i in range(1, len(headers_prod) + 1):
        c = ws2.cell(row=row_cur2, column=c_i)
        c.font = Font(name="Calibri", size=10, bold=True, color="000000")
        c.fill = PatternFill(start_color=BLEU_TOTAL, end_color=BLEU_TOTAL, fill_type="solid")
        c.border = thin_border
        if c_i in [3, 4, 5]:
            c.alignment = Alignment(horizontal="center", vertical="center")

    for col in ws2.columns:
        if col[0].row < 3:
            continue
        max_len = max(len(str(c.value or '')) for c in col)
        ws2.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 4, 15)

    # -------------------------------------------------------------
    # FEUILLE 3 : DÉTAIL JOURNALIER (REGISTRE COMPLET)
    # -------------------------------------------------------------
    ws3 = wb.create_sheet(title="Détail Journalier")
    ws3.views.sheetView[0].showGridLines = True

    ws3.merge_cells("A1:J1")
    ws3["A1"] = f"HISTORIQUE DÉTAILLÉ DES SAISIES — {mois_label.upper()}"
    ws3["A1"].font = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    ws3["A1"].fill = PatternFill(start_color=BLEU_TITRE, end_color=BLEU_TITRE, fill_type="solid")
    ws3["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws3.row_dimensions[1].height = 36

    headers_det = ["Date", "Chantier", "Conducteur", "Ouvrier", "Statut", "Tâche", "Production", "Qualité", "Observation", "Score"]
    ws3.append([])
    ws3.append(headers_det)
    ws3.row_dimensions[3].height = 26

    for col_i in range(1, len(headers_det) + 1):
        cell = ws3.cell(row=3, column=col_i)
        cell.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color=BLEU_HEADER, end_color=BLEU_HEADER, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    row_cur3 = 4
    for _, r in df_mois.iterrows():
        prod_val = "Bricol" if r["Unite"] == "Sans métrage" else (f"{r['Quantite']} {r['Unite']}" if r["Quantite"] > 0 else "-")
        vals3 = [r["Date"], r["Chantier"], r["Conducteur"], r["Ouvrier"], r["Statut"], r["Tâche"], prod_val, r["Qualité"], r["Observation"], r["Score"]]
        ws3.append(vals3)
        ws3.row_dimensions[row_cur3].height = 20

        is_even = (row_cur3 % 2 == 0)
        fill_c = PatternFill(start_color=GRIS_ZEBRA if is_even else "FFFFFF", end_color=GRIS_ZEBRA if is_even else "FFFFFF", fill_type="solid")

        for c_i in range(1, len(headers_det) + 1):
            c = ws3.cell(row=row_cur3, column=c_i)
            c.font = Font(name="Calibri", size=9)
            c.border = thin_border
            c.fill = fill_c
            if c_i in [1, 5, 8, 10]:
                c.alignment = Alignment(horizontal="center", vertical="center")
            elif c_i == 7:
                c.alignment = Alignment(horizontal="right", vertical="center")
            else:
                c.alignment = Alignment(horizontal="left", vertical="center")
        row_cur3 += 1

    for col in ws3.columns:
        if col[0].row < 3:
            continue
        max_len = max(len(str(c.value or '')) for c in col)
        ws3.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 4, 12)

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


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
# ESPACES CONDUCTEURS
# ==============================================================================
if menu_general == f"👷 Espace {nom_c1}":
    interface_saisie_conducteur("c1", nom_c1)

elif menu_general == f"👷 Espace {nom_c2}":
    interface_saisie_conducteur("c2", nom_c2)

# ==============================================================================
# ESPACE ADMIN
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
            ("mod_rapport", "📊 Registre & Bilan Mensuel", "Synthèse RH, métrés totaux et export Excel multi-feuilles"),
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

            # 1. MODULE BILAN MENSUEL & EXPORT MULTI-FEUILLES
            if mod_actuel == "mod_rapport":
                st.markdown("### 📊 Registre Officiel & Synthèse Mensuelle")
                
                tab_mois, tab_corr = st.tabs(["📅 Bilan Mensuel & Export Excel", "✏️ Corriger une Saisie"])

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
                df_all = pd.read_sql_query(query_admin, conn)
                conn.close()

                with tab_mois:
                    if df_all.empty:
                        st.warning("⚠️ Aucune donnée enregistrée dans le registre.")
                    else:
                        # Extraction des mois disponibles (format YYYY-MM)
                        df_all["Mois_Annee"] = df_all["Date"].str.slice(0, 7)
                        mois_disponibles = sorted(df_all["Mois_Annee"].unique().tolist(), reverse=True)
                        
                        col_m1, col_m2 = st.columns(2)
                        with col_m1:
                            mois_choisi = st.selectbox("📅 Sélectionner le Mois :", mois_disponibles)
                        with col_m2:
                            filtre_ch_m = st.selectbox("📍 Filtrer par Chantier :", ["Tous les chantiers"] + sorted(df_all["Chantier"].unique().tolist()))

                        # Filtrage du mois
                        df_mois_actuel = df_all[df_all["Mois_Annee"] == mois_choisi].copy()
                        if filtre_ch_m != "Tous les chantiers":
                            df_mois_actuel = df_mois_actuel[df_mois_actuel["Chantier"] == filtre_ch_m]

                        st.markdown(f"#### 📌 Synthèse de **{mois_choisi}** ({len(df_mois_actuel)} pointages enregistrés)")

                        # Calculs des KPIs du mois
                        total_ouv_actifs = df_mois_actuel["Ouvrier"].nunique()
                        total_j_pres = sum(1 for v in df_mois_actuel["Statut"] if "Présent" in str(v))
                        total_j_demi = sum(1 for v in df_mois_actuel["Statut"] if "1/2" in str(v))
                        total_j_payes = total_j_pres + (total_j_demi * 0.5)

                        # Somme des m²
                        df_m2 = df_mois_actuel[(df_mois_actuel["Unite"] == "m²") & (df_mois_actuel["Quantite"] > 0)]
                        total_m2_prod = df_m2["Quantite"].sum()

                        k1, k2, k3, k4 = st.columns(4)
                        k1.metric("Ouvriers Actifs", f"{total_ouv_actifs}")
                        k2.metric("Total Jours Payés", f"{total_j_payes} j")
                        k3.metric("Absences Déclarées", f"{sum(1 for v in df_mois_actuel['Statut'] if 'Absence' in str(v))}")
                        k4.metric("Production Étanchéité", f"{total_m2_prod:.1f} m²")

                        st.markdown("---")
                        st.markdown("#### 📥 Téléchargement du Bilan Mensuel")
                        st.caption("Le classeur contient 3 feuilles distinctes : **1. Synthèse RH & Jours Payés**, **2. Métrés Totaux par Tâche**, **3. Détail Journalier**.")

                        if OPENPYXL_DISPO:
                            excel_mensuel = generer_classeur_mensuel_complet(df_mois_actuel, f"Mois {mois_choisi}")
                            st.download_button(
                                f"📗 Télécharger le Bilan Complet de {mois_choisi} (.xlsx)",
                                data=excel_mensuel,
                                file_name=f"bilan_mensuel_chantier_{mois_choisi}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                        else:
                            csv_propre = df_mois_actuel.to_csv(index=False, sep=";", encoding="utf-8-sig")
                            st.download_button(
                                f"📥 Télécharger l'export CSV de {mois_choisi}",
                                data=csv_propre.encode("utf-8-sig"),
                                file_name=f"bilan_{mois_choisi}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )

                        st.markdown("##### Aperçu des Lignes du Mois :")
                        df_apercu = df_mois_actuel[["Date", "Chantier", "Conducteur", "Ouvrier", "Statut", "Tâche", "Quantite", "Unite", "Qualité", "Score"]].copy()
                        st.dataframe(df_apercu, use_container_width=True, hide_index=True)

                with tab_corr:
                    st.markdown("##### Rectifier ou supprimer une saisie erronée")
                    if df_all.empty:
                        st.info("Aucun pointage à corriger pour le moment.")
                    else:
                        df_all["label"] = df_all.apply(
                            lambda r: f"ID #{r['ID']} | {r['Date']} | {r['Chantier']} | {r['Ouvrier']} ({r['Conducteur']})",
                            axis=1
                        )
                        ligne_choisie = st.selectbox("Sélectionner l'enregistrement à corriger :", df_all["label"].tolist(), key="sel_pt_correction")
                        row_sel = df_all[df_all["label"] == ligne_choisie].iloc[0]
                        pt_id = int(row_sel["ID"])

                        st.info(f"Pointage de **{row_sel['Ouvrier']}** sur **{row_sel['Chantier']}** le **{row_sel['Date']}**")

                        col_c1, col_c2 = st.columns(2)
                        with col_c1:
                            statuts_possibles = ["Présent (Journée)", "1/2 journée", "Absence Autorisée (Congé/Maladie)", "Absence Non Autorisée (Injustifiée)"]
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
                            photo_nouvel_ouvrier = st.file_uploader("Photo (Optionnel) :", type=["jpg", "jpeg", "png"], key="upload_new_worker_photo_tab")

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
