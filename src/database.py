import sqlite3
from pathlib import Path


# ==========================================
# KONFIGURASI DATABASE
# ==========================================

BASE_DIR = Path(__file__).resolve().parents[1]
DATABASE_DIR = BASE_DIR / "databases"
DATABASE_PATH = DATABASE_DIR / "exam_proctoring.db"
LABELS_PATH = BASE_DIR / "models" / "lbph_labels.txt"


# ==========================================
# KONEKSI DATABASE
# ==========================================

def get_connection():
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


# ==========================================
# MEMBUAT TABEL
# ==========================================

def initialize_database():
    with get_connection() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS students (
                nim TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                face_label INTEGER UNIQUE
            );

            CREATE TABLE IF NOT EXISTS exams (
                exam_id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_name TEXT NOT NULL,
                exam_date TEXT NOT NULL,
                start_time TEXT,
                end_time TEXT
            );

            CREATE TABLE IF NOT EXISTS exam_participants (
                exam_id INTEGER NOT NULL,
                nim TEXT NOT NULL,
                PRIMARY KEY (exam_id, nim),
                FOREIGN KEY (exam_id)
                    REFERENCES exams(exam_id),
                FOREIGN KEY (nim)
                    REFERENCES students(nim)
            );

            CREATE TABLE IF NOT EXISTS attendance (
                attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_id INTEGER NOT NULL,
                nim TEXT NOT NULL,
                attendance_time TEXT NOT NULL
                    DEFAULT (datetime('now', 'localtime')),
                status TEXT NOT NULL DEFAULT 'HADIR',
                UNIQUE (exam_id, nim),
                FOREIGN KEY (exam_id, nim)
                    REFERENCES exam_participants(exam_id, nim)
            );
        """)

    print("Database berhasil disiapkan!")
    print(f"Lokasi: {DATABASE_PATH}")


# ==========================================
# MENDAFTARKAN MAHASISWA
# ==========================================

def add_student(nim, name):
    nim = str(nim).strip()
    name = name.strip()

    if not nim or not name:
        raise ValueError("NIM dan nama wajib diisi.")

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO students (nim, name)
            VALUES (?, ?)
            ON CONFLICT(nim)
            DO UPDATE SET name = excluded.name
            """,
            (nim, name)
        )

    print(f"Mahasiswa tersimpan: {nim} - {name}")


# ==========================================
# MENAMPILKAN MAHASISWA
# ==========================================

def list_students():
    with get_connection() as connection:
        students = connection.execute(
            """
            SELECT nim, name, face_label
            FROM students
            ORDER BY nim
            """
        ).fetchall()

    for student in students:
        print(
            f"NIM: {student['nim']} | "
            f"Nama: {student['name']} | "
            f"Label wajah: {student['face_label']}"
        )


# ==========================================
# SINKRONISASI LABEL LBPH
# ==========================================

def sync_face_labels():
    if not LABELS_PATH.exists():
        raise FileNotFoundError(
            f"File label LBPH tidak ditemukan: {LABELS_PATH}"
        )

    mappings = []

    for line in LABELS_PATH.read_text(
        encoding="utf-8"
    ).splitlines():

        if not line.strip():
            continue

        parts = line.split(",", 1)

        if len(parts) != 2:
            raise ValueError(
                f"Format label tidak valid: {line}"
            )

        label = int(parts[0].strip())
        nim = parts[1].strip()

        mappings.append((label, nim))

    labels = [label for label, _ in mappings]
    nims = [nim for _, nim in mappings]

    if len(labels) != len(set(labels)):
        raise ValueError("Ada label LBPH yang duplikat.")

    if len(nims) != len(set(nims)):
        raise ValueError("Ada NIM duplikat pada file label.")

    with get_connection() as connection:

        # Pastikan semua NIM dalam file label terdaftar.
        for label, nim in mappings:
            student = connection.execute(
                "SELECT nim FROM students WHERE nim = ?",
                (nim,)
            ).fetchone()

            if student is None:
                raise ValueError(
                    f"NIM {nim} pada file label belum "
                    "terdaftar di database. "
                    "Daftarkan mahasiswa terlebih dahulu."
                )

        # Kosongkan label lama agar tidak terjadi bentrok.
        connection.execute(
            "UPDATE students SET face_label = NULL"
        )

        # Terapkan pemetaan label yang terbaru.
        for label, nim in mappings:
            connection.execute(
                """
                UPDATE students
                SET face_label = ?
                WHERE nim = ?
                """,
                (label, nim)
            )

    print(
        f"Sinkronisasi selesai: {len(mappings)} "
        "label wajah berhasil diperbarui."
    )


# ==========================================
# PROGRAM UTAMA
# ==========================================

