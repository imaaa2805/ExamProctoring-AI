from pathlib import Path
import sys
import time

import cv2

# ==========================================
# KONFIGURASI PROJECT
# ==========================================

BASE_DIR = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(BASE_DIR / "src"))
sys.path.insert(0, str(BASE_DIR / "attendance"))

from database import add_student, get_connection, initialize_database
from face_recognition import FaceRecognizer
from register_face import pilih_file_gambar, register_face_from_images


# ==========================================
# MEMILIH SESI UJIAN
# ==========================================

def pilih_sesi_ujian():
    with get_connection() as connection:
        exams = connection.execute(
            """
            SELECT exam_id, course_name, exam_date,
                   start_time, end_time
            FROM exams
            ORDER BY exam_date, start_time
            """
        ).fetchall()

    if not exams:
        print("Belum ada sesi ujian. Buat sesi ujian terlebih dahulu.")
        return None

    print("\n=== DAFTAR SESI UJIAN ===")

    for nomor, exam in enumerate(exams, start=1):
        print(
            f"{nomor}. {exam['course_name']} | "
            f"Tanggal: {exam['exam_date']} | "
            f"Waktu: {exam['start_time']} - {exam['end_time']} | "
            f"ID: {exam['exam_id']}"
        )

    pilihan = input("\nPilih nomor sesi ujian: ").strip()

    if not pilihan.isdigit():
        print("Pilihan harus berupa angka.")
        return None

    nomor = int(pilihan)

    if nomor < 1 or nomor > len(exams):
        print("Nomor sesi ujian tidak valid.")
        return None

    return exams[nomor - 1]


# ==========================================
# MEMERIKSA PESERTA UJIAN
# ==========================================

def cek_peserta(exam_id, nim):
    with get_connection() as connection:
        peserta = connection.execute(
            """
            SELECT s.nim, s.name
            FROM exam_participants ep
            JOIN students s ON s.nim = ep.nim
            WHERE ep.exam_id = ? AND ep.nim = ?
            """,
            (exam_id, nim)
        ).fetchone()

    return peserta


# ==========================================
# MENYIMPAN KEHADIRAN
# ==========================================

def catat_kehadiran(exam_id, nim):
    with get_connection() as connection:
        # Pastikan mahasiswa merupakan peserta ujian.
        peserta = connection.execute(
            """
            SELECT nim
            FROM exam_participants
            WHERE exam_id = ? AND nim = ?
            """,
            (exam_id, nim)
        ).fetchone()

        if peserta is None:
            return "BUKAN PESERTA"

        # Simpan hanya jika belum tercatat.
        cursor = connection.execute(
            """
            INSERT INTO attendance (exam_id, nim, status)
            VALUES (?, ?, 'HADIR')
            ON CONFLICT(exam_id, nim) DO NOTHING
            """,
            (exam_id, nim)
        )

        if cursor.rowcount == 1:
            return "BERHASIL"

        return "SUDAH HADIR"


# ==========================================
# PRESENSI MELALUI UPLOAD GAMBAR + NIM MANUAL
# ==========================================

def presensi_dari_gambar(exam):
    exam_id = exam["exam_id"]

    print("\n=== PRESENSI DARI FILE GAMBAR (NIM MANUAL) ===")
    print(f"Mata kuliah: {exam['course_name']}")
    print(f"Tanggal    : {exam['exam_date']}")

    with get_connection() as connection:
        students = connection.execute(
            """
            SELECT nim, name
            FROM students
            ORDER BY nim
            """
        ).fetchall()

    if students:
        print("\nDaftar mahasiswa terdaftar:")
        for idx, s in enumerate(students, start=1):
            print(f"{idx}. {s['name']} ({s['nim']})")

    raw_nim = input(
        "\nMasukkan NIM secara manual (atau ketik nomor urut di atas): "
    ).strip()

    if not raw_nim:
        print("NIM tidak boleh kosong.")
        return

    # Jika pengguna mengetik nomor urut pendek (1, 2, 3...)
    if raw_nim.isdigit() and 1 <= int(raw_nim) <= len(students):
        selected = students[int(raw_nim) - 1]
        nim = selected["nim"]
        nama = selected["name"]
    else:
        nim = raw_nim
        existing = next((s for s in students if s["nim"] == nim), None)
        if existing:
            nama = existing["name"]
        else:
            nama = input(
                f"NIM {nim} belum ada di database. Masukkan nama mahasiswa: "
            ).strip()
            if not nama:
                nama = f"Mahasiswa {nim}"
            add_student(nim, nama)

    # Pilih file gambar wajah
    print(f"\nPilih file gambar untuk {nama} ({nim})...")
    image_paths = pilih_file_gambar()

    if not image_paths:
        print("Tidak ada gambar yang dipilih. Presensi dibatalkan.")
        return

    # Simpan sampel wajah dari gambar ke dataset & latih model LBPH
    saved_count = register_face_from_images(
        nim,
        nama,
        image_paths=image_paths,
        auto_train=True
    )

    if saved_count == 0:
        print("Gagal memproses gambar wajah.")
        return

    # Pastikan mahasiswa terdaftar sebagai peserta di sesi ujian ini
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO exam_participants (exam_id, nim)
            VALUES (?, ?)
            ON CONFLICT(exam_id, nim) DO NOTHING
            """,
            (exam_id, nim)
        )

    status = catat_kehadiran(exam_id, nim)

    if status == "BERHASIL":
        print(
            f"\n[HADIR] {nama} ({nim}) berhasil masuk database "
            "& tercatat hadir melalui gambar!"
        )
    elif status == "SUDAH HADIR":
        print(
            f"\n[INFO] Data gambar {nama} ({nim}) berhasil disimpan "
            "(status kehadiran sudah tercatat sebelumnya)."
        )

    # Tampilkan pratinjau gambar pertama yang dipilih
    preview = cv2.imread(str(image_paths[0]))
    if preview is not None:
        cv2.putText(
            preview,
            f"HADIR: {nama} ({nim})",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )
        cv2.imshow("Presensi Gambar - Exam Proctoring AI", preview)
        print("Tekan tombol apa saja pada jendela gambar untuk menutup.")
        cv2.waitKey(0)
        cv2.destroyAllWindows()


# ==========================================
# MENJALANKAN PRESENSI KAMERA
# ==========================================

def mulai_presensi_kamera(exam):
    exam_id = exam["exam_id"]

    print("\n=== PRESENSI MAHASISWA (KAMERA) ===")
    print(f"Mata kuliah: {exam['course_name']}")
    print(f"Tanggal: {exam['exam_date']}")
    print(f"ID ujian: {exam_id}")

    # Pastikan ujian memiliki peserta.
    with get_connection() as connection:
        jumlah_peserta = connection.execute(
            """
            SELECT COUNT(*) AS jumlah
            FROM exam_participants
            WHERE exam_id = ?
            """,
            (exam_id,)
        ).fetchone()["jumlah"]

    if jumlah_peserta == 0:
        print("Sesi ujian ini belum memiliki peserta.")
        return

    recognizer = FaceRecognizer(threshold=70)

    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not camera.isOpened():
        print("Kamera laptop tidak bisa dibuka.")
        return

    # Menyimpan waktu pemrosesan terakhir per NIM
    # agar pesan tidak muncul terus-menerus.
    last_processed = {}

    print("\nKamera presensi aktif.")
    print("Tekan Q untuk menghentikan presensi.")

    try:
        while True:
            ret, frame = camera.read()

            if not ret:
                print("Gagal membaca gambar dari kamera.")
                break

            frame, results = recognizer.recognize_frame(frame)

            current_time = time.time()

            for result in results:
                nim = result["nim"]

                # Abaikan wajah yang tidak dikenali.
                if not nim:
                    continue

                # Beri jeda agar mahasiswa yang sama tidak
                # diproses berulang kali dalam waktu singkat.
                if current_time - last_processed.get(nim, 0) < 3:
                    continue

                last_processed[nim] = current_time

                peserta = cek_peserta(exam_id, nim)

                if peserta is None:
                    print(
                        f"[DITOLAK] NIM {nim} bukan peserta "
                        "sesi ujian ini."
                    )
                    continue

                status = catat_kehadiran(exam_id, nim)

                if status == "BERHASIL":
                    print(
                        f"[HADIR] {peserta['name']} "
                        f"({peserta['nim']}) berhasil presensi."
                    )

                elif status == "SUDAH HADIR":
                    print(
                        f"[INFO] {peserta['name']} "
                        "sudah tercatat hadir."
                    )

            cv2.imshow("Presensi - Exam Proctoring AI", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()

    print("\nProses presensi selesai.")


def mulai_presensi(exam):
    while True:
        print("\n=== PILIH METODE PRESENSI ===")
        print("1. Presensi menggunakan Kamera Live")
        print("2. Tambah Gambar + Input NIM Manual")
        print("3. Keluar")

        metode = input("Pilih metode (1-3): ").strip()

        if metode == "1":
            mulai_presensi_kamera(exam)
        elif metode == "2":
            presensi_dari_gambar(exam)
        elif metode == "3":
            break
        else:
            print("Pilihan tidak valid.")


# ==========================================
# PROGRAM UTAMA
# ==========================================

if __name__ == "__main__":
    initialize_database()

    exam = pilih_sesi_ujian()

    if exam is not None:
        mulai_presensi(exam)
