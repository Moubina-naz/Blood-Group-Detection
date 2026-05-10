"""
Blood Group Identification System - CORE LOGIC MODULE
======================================================
Contains ALL core scientific/processing logic and backend services.

Sections:
  1. Agglutination detection algorithm  (UNCHANGED)
  2. Blood typing orchestrator          (UNCHANGED)
  3. Fingerprint quality thread         (UNCHANGED)
  4. Compatibility & text helpers       (UNCHANGED)
  5. SQLite database management         (NEW)
  6. Fingerprint biometric matching     (NEW)
  7. PDF report generation              (NEW)
  8. Email sending                      (NEW)
"""

import cv2
import numpy as np
import os
import sqlite3
import pickle
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal
import warnings
warnings.filterwarnings('ignore')

# Optional imports — features degrade gracefully if missing
try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False

# ==============================================================================
# DATABASE PATH
# ==============================================================================
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       'blood_group_system.db')

# ==============================================================================
# BLOOD TYPE LOOKUP TABLE
# ==============================================================================

BLOOD_TYPE_TABLE = {
    (True,  True,  True):  "AB+",
    (True,  True,  False): "AB-",
    (True,  False, True):  "A+",
    (True,  False, False): "A-",
    (False, True,  True):  "B+",
    (False, True,  False): "B-",
    (False, False, True):  "O+",
    (False, False, False): "O-",
}


# ==============================================================================
# 1. ENHANCED IMAGE PROCESSING FOR AGGLUTINATION DETECTION  (UNCHANGED)
# ==============================================================================

def enhanced_agglutination_detection(image_path):
    """
    Agglutination detection — distinguishes clumped from smooth blood smears
    by analysing the INTERIOR texture of the blood spot.

    How it works
    -------------
    1.  Isolate the blood-spot region (ROI) via HSV colour masking.
    2.  Within the ROI, detect dark-red granular clusters using adaptive
        thresholding on the red channel.
    3.  Score based on:
          F1 — Number of internal fragments           [0-30 pts]
          F2 — Fragment area ratio inside the ROI      [0-25 pts]
          F3 — Pixel-intensity standard deviation (ROI)[0-20 pts]
          F4 — Laplacian texture roughness (ROI)       [0-15 pts]
          F5 — Edge density inside the ROI             [0-10 pts]
        Total possible = 100.   Threshold > 40 -> POSITIVE.

    Positive (clumped) = many scattered red dots/clumps on lighter serum.
    Negative (smooth)  = uniform, homogeneous red wash with no granules.

    Returns
    -------
    score       : float   - 0-100
    is_positive : bool    - True if clumping detected
    explanation : str     - human-readable per-feature breakdown
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not load image: {image_path}")

    img = cv2.resize(img, (400, 400))

    # Step 1: Isolate the blood-spot ROI
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask_lo   = cv2.inRange(hsv, (0,   30, 50), (15,  255, 255))
    mask_hi   = cv2.inRange(hsv, (160, 30, 50), (180, 255, 255))
    mask_pink = cv2.inRange(hsv, (0, 15, 80), (20, 255, 255))
    roi_mask  = mask_lo | mask_hi | mask_pink

    kernel   = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    roi_mask = cv2.morphologyEx(roi_mask, cv2.MORPH_CLOSE, kernel)
    roi_mask = cv2.morphologyEx(roi_mask, cv2.MORPH_OPEN,  kernel)

    roi_pixels   = int(np.sum(roi_mask > 0))
    total_pixels = roi_mask.size

    if roi_pixels < total_pixels * 0.02:
        return 0.0, False, "No blood spot detected in the image."

    # Step 2: Detect internal granules
    red_ch   = img[:, :, 2].astype(np.float64)
    gray     = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    roi_red  = red_ch.copy();  roi_red[roi_mask == 0] = 0
    roi_gray = gray.copy();    roi_gray[roi_mask == 0] = 0

    roi_gray_u8 = roi_gray.astype(np.uint8)
    adaptive = cv2.adaptiveThreshold(
        roi_gray_u8, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV,
        blockSize=21, C=8
    )
    adaptive = adaptive & roi_mask

    small_kernel = np.ones((3, 3), np.uint8)
    adaptive = cv2.morphologyEx(adaptive, cv2.MORPH_OPEN, small_kernel)

    contours, _ = cv2.findContours(adaptive, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)

    MIN_FRAG_AREA = 15
    frag_areas = [cv2.contourArea(c) for c in contours
                  if cv2.contourArea(c) >= MIN_FRAG_AREA]
    num_fragments   = len(frag_areas)
    total_frag_area = sum(frag_areas)
    frag_area_ratio = total_frag_area / max(roi_pixels, 1)

    # Step 3: Intensity statistics inside ROI
    roi_vals       = gray[roi_mask > 0].astype(np.float64)
    intensity_std  = float(np.std(roi_vals))  if len(roi_vals) > 0 else 0.0
    intensity_mean = float(np.mean(roi_vals)) if len(roi_vals) > 0 else 0.0

    # Step 4: Laplacian texture roughness
    blurred_roi = cv2.GaussianBlur(roi_gray_u8, (5, 5), 0)
    lap      = cv2.Laplacian(blurred_roi, cv2.CV_64F)
    lap_vals = lap[roi_mask > 0]
    lap_var  = float(np.var(lap_vals)) if len(lap_vals) > 0 else 0.0

    # Step 5: Edge density inside ROI
    edges = cv2.Canny(blurred_roi, 40, 120) & roi_mask
    edge_density = float(np.sum(edges > 0)) / max(roi_pixels, 1)

    # Scoring
    f1 = 30.0 * min(num_fragments / 20.0, 1.0)
    f2 = 25.0 * min(frag_area_ratio / 0.12, 1.0)
    f3 = 20.0 * min(intensity_std / 40.0, 1.0)
    f4 = 15.0 * min(lap_var / 500.0, 1.0)
    f5 = 10.0 * min(edge_density / 0.08, 1.0)

    score = max(0.0, min(f1 + f2 + f3 + f4 + f5, 100.0))
    is_positive = score > 40.0

    explanation = (
        f"[F1] Internal fragments    : {num_fragments}"
        f"  -> {f1:.1f}/30 pts\n"
        f"[F2] Fragment area ratio   : {frag_area_ratio*100:.1f}%"
        f"  -> {f2:.1f}/25 pts\n"
        f"[F3] Intensity std-dev     : {intensity_std:.1f}"
        f"  -> {f3:.1f}/20 pts\n"
        f"[F4] Texture roughness     : {lap_var:.0f}"
        f"  -> {f4:.1f}/15 pts\n"
        f"[F5] Edge density (ROI)    : {edge_density*100:.1f}%"
        f"  -> {f5:.1f}/10 pts\n"
        f"Blood-spot ROI coverage    : {roi_pixels/total_pixels*100:.1f}%\n"
        f"Mean intensity (ROI)       : {intensity_mean:.1f}\n"
        f"---------------------------------------------\n"
        f"FINAL SCORE : {score:.1f}/100"
        f"  ->  {'POSITIVE (clumping detected)' if is_positive else 'NEGATIVE (smooth / no clumping)'}"
    )
    return score, is_positive, explanation


def compute_clump_score_relative(image_path, reference_scores=None):
    """Enhanced version with both absolute and relative scoring."""
    abs_score, is_positive, explanation = enhanced_agglutination_detection(image_path)
    if reference_scores is not None and len(reference_scores) > 0:
        ref_min = min(reference_scores)
        ref_max = max(reference_scores)
        ref_range = max(ref_max - ref_min, 1e-6)
        rel_score = (abs_score - ref_min) / ref_range
        is_positive = rel_score > 0.4
    return abs_score, is_positive, explanation


# ==============================================================================
# 2. BLOOD TYPING ORCHESTRATOR  (UNCHANGED)
# ==============================================================================

def analyze_blood_sample(anti_a_path, anti_b_path, anti_d_path):
    """Run enhanced agglutination detection on all three test images."""
    print("\n" + "=" * 60)
    print("ENHANCED BLOOD TYPING ANALYSIS")
    print("=" * 60)

    score_a, is_pos_a, exp_a = enhanced_agglutination_detection(anti_a_path)
    score_b, is_pos_b, exp_b = enhanced_agglutination_detection(anti_b_path)
    score_d, is_pos_d, exp_d = enhanced_agglutination_detection(anti_d_path)

    for tag, sc, pos, exp in [("ANTI-A", score_a, is_pos_a, exp_a),
                               ("ANTI-B", score_b, is_pos_b, exp_b),
                               ("ANTI-D (Rh)", score_d, is_pos_d, exp_d)]:
        print(f"\n{tag} TEST:")
        print(f"  Score: {sc:.1f}/100")
        print(f"  Result: {'POSITIVE' if pos else 'NEGATIVE'}")
        print(f"  Details: {exp}")

    blood_type = BLOOD_TYPE_TABLE.get((is_pos_a, is_pos_b, is_pos_d), "Unknown")
    print(f"\n{'=' * 60}\nFINAL BLOOD TYPE: {blood_type}\n{'=' * 60}")

    return {
        'blood_type': blood_type,
        'results': {
            'A': {'score': score_a, 'positive': is_pos_a, 'explanation': exp_a},
            'B': {'score': score_b, 'positive': is_pos_b, 'explanation': exp_b},
            'D': {'score': score_d, 'positive': is_pos_d, 'explanation': exp_d},
        }
    }


# ==============================================================================
# 3. FINGERPRINT PROCESSING WORKER  (UNCHANGED)
# ==============================================================================

class FingerprintThread(QThread):
    """Background worker for fingerprint quality analysis."""
    progress = pyqtSignal(int)
    result   = pyqtSignal(str)

    def __init__(self, fingerprint_path):
        super().__init__()
        self.fingerprint_path = fingerprint_path

    def run(self):
        try:
            self.progress.emit(10)
            img = cv2.imread(self.fingerprint_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                self.result.emit("ERROR: Invalid fingerprint image")
                return

            img = cv2.resize(img, (300, 300))
            self.progress.emit(30)

            img_std = np.std(img)
            if img_std < 20:
                self.result.emit("WARNING: Low quality fingerprint")
                return

            _, binary = cv2.threshold(img, 0, 255,
                                      cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            kernel = np.ones((3, 3), np.uint8)
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            ridges = cv2.erode(binary, kernel, iterations=1)
            self.progress.emit(60)

            minutiae_count = np.sum(ridges == 255) // 80
            if minutiae_count > 25:
                quality, status = "Excellent", "VERIFIED"
            elif minutiae_count > 15:
                quality, status = "Good", "VERIFIED"
            elif minutiae_count > 8:
                quality, status = "Fair", "VERIFIED"
            else:
                quality, status = "Poor", "REJECTED"

            self.progress.emit(90)
            result_text = (
                f"FINGERPRINT ANALYSIS:\n{'=' * 40}\n"
                f"Status: {status}\nQuality: {quality}\n"
                f"Features Detected: {minutiae_count}\n"
                f"Contrast Score: {img_std:.1f}\n{'=' * 40}\n"
                f"Patient identity has been registered."
            )
            self.progress.emit(100)
            self.result.emit(result_text)
        except Exception as e:
            self.result.emit(f"ERROR: {str(e)}")


# ==============================================================================
# 4. COMPATIBILITY & REPORT TEXT HELPERS  (UNCHANGED)
# ==============================================================================

COMPATIBILITY_MAP = {
    "A+":  {"can_donate_to": "A+, AB+",         "can_receive_from": "A+, A-, O+, O-",  "frequency": "~34%", "note": "Common blood type"},
    "A-":  {"can_donate_to": "A+, A-, AB+, AB-", "can_receive_from": "A-, O-",           "frequency": "~6%",  "note": "Rare blood type"},
    "B+":  {"can_donate_to": "B+, AB+",          "can_receive_from": "B+, B-, O+, O-",  "frequency": "~9%",  "note": "Common in Asia"},
    "B-":  {"can_donate_to": "B+, B-, AB+, AB-", "can_receive_from": "B-, O-",           "frequency": "~2%",  "note": "Very rare"},
    "AB+": {"can_donate_to": "AB+",              "can_receive_from": "All blood types",  "frequency": "~3%",  "note": "Universal recipient"},
    "AB-": {"can_donate_to": "AB+, AB-",         "can_receive_from": "AB-, A-, B-, O-",  "frequency": "~1%",  "note": "Rarest blood type"},
    "O+":  {"can_donate_to": "O+, A+, B+, AB+", "can_receive_from": "O+, O-",           "frequency": "~38%", "note": "Most common blood type"},
    "O-":  {"can_donate_to": "All blood types",  "can_receive_from": "O-",               "frequency": "~7%",  "note": "Universal donor"},
}


def generate_compatibility_info(blood_type):
    """Formatted compatibility string for a blood type."""
    info = COMPATIBILITY_MAP.get(blood_type, {
        "can_donate_to": "Unknown", "can_receive_from": "Unknown",
        "frequency": "Unknown", "note": "Unknown blood type",
    })
    return (
        f"BLOOD COMPATIBILITY FOR {blood_type}\n{'=' * 40}\n"
        f"Can donate to: {info['can_donate_to']}\n"
        f"Can receive from: {info['can_receive_from']}\n"
        f"Population frequency: {info['frequency']}\n"
        f"Special notes: {info['note']}\n\n"
        f"IMPORTANT:\n"
        f"  * Always verify with a qualified technician\n"
        f"  * Cross-matching required before transfusion\n"
        f"  * Rh factor is critical in pregnancy (HDN risk)"
    )


def generate_result_details(results, blood_type):
    """Formatted per-test scores and interpretation."""
    ra, rb, rd = results['A'], results['B'], results['D']
    return (
        f"DETAILED ANALYSIS RESULTS\n{'=' * 40}\n"
        f"Anti-A Test:\n"
        f"  Score: {ra['score']:.1f}/100\n"
        f"  Result: {'POSITIVE (Clumping)' if ra['positive'] else 'NEGATIVE (Smooth)'}\n"
        f"  Interpretation: {'A antigen PRESENT' if ra['positive'] else 'No A antigen'}\n\n"
        f"Anti-B Test:\n"
        f"  Score: {rb['score']:.1f}/100\n"
        f"  Result: {'POSITIVE (Clumping)' if rb['positive'] else 'NEGATIVE (Smooth)'}\n"
        f"  Interpretation: {'B antigen PRESENT' if rb['positive'] else 'No B antigen'}\n\n"
        f"Anti-D (Rh) Test:\n"
        f"  Score: {rd['score']:.1f}/100\n"
        f"  Result: {'POSITIVE (Clumping)' if rd['positive'] else 'NEGATIVE (Smooth)'}\n"
        f"  Interpretation: {'Rh+ (Rh factor PRESENT)' if rd['positive'] else 'Rh- (No Rh factor)'}\n\n"
        f"FINAL DETERMINATION:\n{'=' * 40}\n"
        f"Blood Type: {blood_type}\n"
        f"Confidence: High (multi-feature ROI analysis)\n"
        f"Method: Enhanced agglutination detection v2.0"
    )


def generate_visualization_text(results):
    """ASCII bar-chart string for quick score overview."""
    ra, rb, rd = results['A'], results['B'], results['D']

    def _bar(score, label):
        bars   = "█" * int(score / 5)
        spaces = " " * (20 - len(bars))
        return f"{label:10} [{bars}{spaces}] {score:5.1f}/100"

    pos_a = "POSITIVE" if ra['positive'] else "NEGATIVE"
    pos_b = "POSITIVE" if rb['positive'] else "NEGATIVE"
    pos_d = "POSITIVE" if rd['positive'] else "NEGATIVE"

    return (
        f"TEST SCORE VISUALIZATION\n{'=' * 40}\n\n"
        f"{_bar(ra['score'], 'Anti-A')}  {pos_a}\n"
        f"{_bar(rb['score'], 'Anti-B')}  {pos_b}\n"
        f"{_bar(rd['score'], 'Anti-D')}  {pos_d}\n\n"
        f"{'=' * 40}\n"
        f"THRESHOLD: score > 40 = POSITIVE agglutination\n"
        f"Primary discriminators: fragment count & area ratio"
    )


def generate_full_report(analysis_results, patient_info=None):
    """Full text report string. Accepts optional patient_info dict."""
    res = analysis_results['results']
    pi  = patient_info or {}
    name   = pi.get('name', '-')
    age    = pi.get('age', '-')
    gender = pi.get('gender', '-')
    pid    = pi.get('id', '-')

    return (
        f"{'=' * 60}\n"
        f"BLOOD GROUP IDENTIFICATION REPORT\n"
        f"{'=' * 60}\n\n"
        f"PATIENT INFORMATION\n{'-' * 40}\n"
        f"Patient Name : {name}\n"
        f"Patient ID   : {pid}\n"
        f"Age / Gender : {age} / {gender}\n"
        f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"System       : Enhanced Agglutination Detection v2.0\n\n"
        f"TEST RESULTS\n{'-' * 40}\n"
        f"Anti-A Test: {'POSITIVE' if res['A']['positive'] else 'NEGATIVE'}  "
        f"(Score: {res['A']['score']:.1f}/100)\n"
        f"Anti-B Test: {'POSITIVE' if res['B']['positive'] else 'NEGATIVE'}  "
        f"(Score: {res['B']['score']:.1f}/100)\n"
        f"Anti-D Test: {'POSITIVE' if res['D']['positive'] else 'NEGATIVE'}  "
        f"(Score: {res['D']['score']:.1f}/100)\n\n"
        f"FINAL DETERMINATION\n{'-' * 40}\n"
        f"Blood Type : {analysis_results['blood_type']}\n"
        f"Confidence : High (multi-feature analysis)\n\n"
        f"CLINICAL NOTES\n{'-' * 40}\n"
        f"* This report is for educational/demonstration purposes\n"
        f"* Always confirm with standard serological testing\n"
        f"* Consult healthcare professional for medical decisions\n"
        f"{'=' * 60}"
    )


# ==============================================================================
# 5. SQLite DATABASE MANAGEMENT  (NEW)
# ==============================================================================

def _get_conn():
    """Return a new connection to the local SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Create tables if they do not exist."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            name                TEXT    NOT NULL,
            age                 INTEGER,
            gender              TEXT,
            phone               TEXT,
            doctor_email        TEXT,
            fingerprint_desc    BLOB,
            created_at          TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS blood_results (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id      INTEGER NOT NULL,
            blood_type      TEXT,
            score_a         REAL,
            score_b         REAL,
            score_d         REAL,
            positive_a      INTEGER,
            positive_b      INTEGER,
            positive_d      INTEGER,
            analysis_date   TEXT DEFAULT (datetime('now','localtime')),
            report_path     TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS email_config (
            id              INTEGER PRIMARY KEY CHECK (id = 1),
            sender_email    TEXT,
            sender_password TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_patient(name, age, gender, phone, doctor_email,
                 fingerprint_desc=None):
    """Insert a new patient and return the patient_id."""
    conn = _get_conn()
    c = conn.cursor()
    desc_blob = pickle.dumps(fingerprint_desc) if fingerprint_desc is not None else None
    c.execute(
        "INSERT INTO patients (name,age,gender,phone,doctor_email,fingerprint_desc)"
        " VALUES (?,?,?,?,?,?)",
        (name, age, gender, phone, doctor_email, desc_blob)
    )
    conn.commit()
    pid = c.lastrowid
    conn.close()
    return pid


def save_blood_result(patient_id, blood_type, results, report_path=None):
    """Save blood analysis results linked to a patient."""
    ra, rb, rd = results['A'], results['B'], results['D']
    conn = _get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO blood_results "
        "(patient_id,blood_type,score_a,score_b,score_d,"
        " positive_a,positive_b,positive_d,report_path)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        (patient_id, blood_type,
         ra['score'], rb['score'], rd['score'],
         int(ra['positive']), int(rb['positive']), int(rd['positive']),
         report_path)
    )
    conn.commit()
    conn.close()


def get_all_history():
    """Return list of dicts: patient + latest blood result."""
    conn = _get_conn()
    rows = conn.execute("""
        SELECT p.id, p.name, p.age, p.gender, p.phone, p.doctor_email,
               b.blood_type, b.score_a, b.score_b, b.score_d,
               b.positive_a, b.positive_b, b.positive_d,
               b.analysis_date, b.report_path
        FROM   blood_results b
        JOIN   patients p ON p.id = b.patient_id
        ORDER BY b.analysis_date DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_history(query):
    """Search history by patient name (case-insensitive)."""
    conn = _get_conn()
    rows = conn.execute("""
        SELECT p.id, p.name, p.age, p.gender, p.phone, p.doctor_email,
               b.blood_type, b.score_a, b.score_b, b.score_d,
               b.analysis_date
        FROM   blood_results b
        JOIN   patients p ON p.id = b.patient_id
        WHERE  p.name LIKE ?
        ORDER BY b.analysis_date DESC
    """, (f"%{query}%",)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_blood_type_stats():
    """Return dict of blood_type -> count from all results."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT blood_type, COUNT(*) as cnt FROM blood_results GROUP BY blood_type"
    ).fetchall()
    conn.close()
    return {r['blood_type']: r['cnt'] for r in rows}


# ==============================================================================
# 6. FINGERPRINT BIOMETRIC MATCHING  (NEW)
# ==============================================================================

def extract_fingerprint_features(image_path):
    """Extract ORB keypoints & descriptors from a fingerprint image.
    Returns (keypoints_list, descriptors_ndarray) or (None, None)."""
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None, None
    img = cv2.resize(img, (300, 300))
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    img = clahe.apply(img)
    orb = cv2.ORB_create(nfeatures=500)
    kp, desc = orb.detectAndCompute(img, None)
    if desc is None:
        return None, None
    # Convert keypoints to serialisable list
    kp_data = [(p.pt, p.size, p.angle, p.response, p.octave) for p in kp]
    return kp_data, desc


def match_fingerprints(desc1, desc2):
    """Compare two ORB descriptor arrays. Returns match count (int)."""
    if desc1 is None or desc2 is None:
        return 0
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    try:
        matches = bf.knnMatch(desc1, desc2, k=2)
    except cv2.error:
        return 0
    good = 0
    for m_pair in matches:
        if len(m_pair) == 2:
            m, n = m_pair
            if m.distance < 0.75 * n.distance:
                good += 1
    return good


def find_matching_patient(image_path, threshold=12):
    """Try to match a fingerprint against all stored patients.
    Returns (patient_dict, match_count) or (None, 0)."""
    _, new_desc = extract_fingerprint_features(image_path)
    if new_desc is None:
        return None, 0

    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, name, age, gender, phone, doctor_email, fingerprint_desc "
        "FROM patients WHERE fingerprint_desc IS NOT NULL"
    ).fetchall()
    conn.close()

    best_patient = None
    best_count   = 0

    for row in rows:
        stored_desc = pickle.loads(row['fingerprint_desc'])
        if not isinstance(stored_desc, np.ndarray):
            continue
        count = match_fingerprints(new_desc, stored_desc)
        if count > best_count:
            best_count   = count
            best_patient = dict(row)

    if best_count >= threshold and best_patient is not None:
        best_patient.pop('fingerprint_desc', None)
        return best_patient, best_count
    return None, best_count


# ==============================================================================
# 7. PDF REPORT GENERATION  (NEW)
# ==============================================================================

def generate_pdf_report(patient_info, analysis_results, output_path):
    """Generate a professional PDF report using fpdf2.
    Returns True on success, raises if fpdf2 is missing."""
    if not HAS_FPDF:
        raise ImportError("fpdf2 is required for PDF reports. "
                          "Install with: pip install fpdf2")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    bt  = analysis_results['blood_type']
    res = analysis_results['results']
    pi  = patient_info or {}

    # Header
    pdf.set_fill_color(20, 60, 120)
    pdf.rect(0, 0, 210, 38, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_y(8)
    pdf.cell(0, 10, 'Blood Group Identification Report', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 7, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
             align='C', new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(45)
    pdf.set_text_color(0, 0, 0)

    # Patient info
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_fill_color(230, 240, 255)
    pdf.cell(0, 10, '  Patient Information', fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 11)
    pdf.ln(3)
    for label, val in [("Name", pi.get('name', '-')),
                       ("Age", pi.get('age', '-')),
                       ("Gender", pi.get('gender', '-')),
                       ("Phone", pi.get('phone', '-')),
                       ("Doctor Email", pi.get('doctor_email', '-'))]:
        pdf.cell(50, 7, f'  {label}:', new_x="RIGHT")
        pdf.cell(0, 7, str(val), new_x="LMARGIN", new_y="NEXT")

    # Blood type result
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_fill_color(200, 255, 200)
    pdf.cell(0, 10, '  Blood Type Result', fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font('Helvetica', 'B', 28)
    pdf.set_text_color(200, 30, 30)
    pdf.cell(0, 18, bt, align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)

    # Test scores table
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_fill_color(255, 240, 220)
    pdf.cell(0, 10, '  Test Scores', fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_fill_color(60, 60, 100)
    pdf.set_text_color(255, 255, 255)
    for header, w in [("Test", 50), ("Score", 40), ("Result", 45), ("Interpretation", 55)]:
        pdf.cell(w, 8, header, border=1, fill=True, align='C')
    pdf.ln()
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Helvetica', '', 10)

    for label, key, antigen in [("Anti-A", "A", "A antigen"),
                                 ("Anti-B", "B", "B antigen"),
                                 ("Anti-D (Rh)", "D", "Rh factor")]:
        r = res[key]
        result_str = "POSITIVE" if r['positive'] else "NEGATIVE"
        interp = f"{antigen} PRESENT" if r['positive'] else f"No {antigen}"
        pdf.cell(50, 7, f"  {label}", border=1)
        pdf.cell(40, 7, f"{r['score']:.1f}/100", border=1, align='C')
        pdf.cell(45, 7, result_str, border=1, align='C')
        pdf.cell(55, 7, interp, border=1, align='C')
        pdf.ln()

    # Compatibility
    info = COMPATIBILITY_MAP.get(bt, {})
    if info:
        pdf.ln(5)
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_fill_color(220, 230, 255)
        pdf.cell(0, 10, '  Blood Compatibility', fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        pdf.set_font('Helvetica', '', 11)
        pdf.cell(0, 7, f"  Can donate to    : {info.get('can_donate_to', '-')}",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 7, f"  Can receive from : {info.get('can_receive_from', '-')}",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 7, f"  Population freq  : {info.get('frequency', '-')}",
                 new_x="LMARGIN", new_y="NEXT")

    # Disclaimer
    pdf.ln(8)
    pdf.set_font('Helvetica', 'I', 9)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 5,
                   "Disclaimer: This report is generated by an automated system "
                   "for educational and demonstration purposes only. Results must "
                   "be verified by a qualified medical professional before any "
                   "clinical decision is made.")

    pdf.output(output_path)
    return True


# ==============================================================================
# 8. EMAIL SENDING  (NEW)
# ==============================================================================

def save_email_config(sender_email, sender_password):
    """Store SMTP sender credentials in the local database."""
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO email_config (id, sender_email, sender_password) "
        "VALUES (1, ?, ?)", (sender_email, sender_password)
    )
    conn.commit()
    conn.close()


def get_email_config():
    """Retrieve stored sender email + password. Returns dict or None."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM email_config WHERE id = 1").fetchone()
    conn.close()
    return dict(row) if row else None


def send_email_report(to_email, pdf_path, patient_name, blood_type):
    """Send a PDF report as an email attachment via Gmail SMTP.
    Returns True on success, raises on failure."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.base import MIMEBase
    from email.mime.text import MIMEText
    from email import encoders

    config = get_email_config()
    if not config:
        raise ValueError("Email credentials not configured. "
                         "Please set up sender email first.")

    sender   = config['sender_email']
    password = config['sender_password']

    msg = MIMEMultipart()
    msg['From']    = sender
    msg['To']      = to_email
    msg['Subject'] = f"Blood Group Report - {patient_name} ({blood_type})"

    body = (
        f"Dear Doctor,\n\n"
        f"Please find attached the blood group identification report for "
        f"patient {patient_name}.\n\n"
        f"Blood Group Determined: {blood_type}\n\n"
        f"This report was generated by the Enhanced Blood Group "
        f"Identification System.\n\n"
        f"Best regards,\nBlood Group Identification System"
    )
    msg.attach(MIMEText(body, 'plain'))

    with open(pdf_path, 'rb') as f:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition',
                        f'attachment; filename="{os.path.basename(pdf_path)}"')
        msg.attach(part)

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(sender, password)
    server.sendmail(sender, to_email, msg.as_string())
    server.quit()
    return True


# ==============================================================================
# AUTO-INITIALISE DATABASE ON IMPORT
# ==============================================================================
init_database()
