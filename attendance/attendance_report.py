from pathlib import Path
import sys

# ==========================================
# KONFIGURASI PROJECT
# ==========================================

BASE_DIR = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(BASE_DIR / "src"))

from database import get_connection, initialize_database


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
        print("\nBelum ada sesi ujian.")
        return None

    print("\n========== DAFTAR SESI UJIAN ==========")

    for nomor, exam in enumerate(exams, start=1):
        print(
            f"{nomor}. {exam['course_name']} | "
            f"Tanggal: {exam['exam_date']} | "
            f"Waktu: {exam['start_time']} - "
            f"{exam['end_time']} | "
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
# MEMBUAT REKAP KEHADIRAN
# ==========================================

def tampilkan_rekap(exam):
    exam_id = exam["exam_id"]

    with get_connection() as connection:
        participants = connection.execute(
            """
            SELECT
                s.nim,
                s.name,
                a.attendance_time,
                a.status
            FROM exam_participants ep
            JOIN students s
                ON s.nim = ep.nim
            LEFT JOIN attendance a
                ON a.exam_id = ep.exam_id
                AND a.nim = ep.nim
            WHERE ep.exam_id = ?
            ORDER BY s.nim
            """,
            (exam_id,)
        ).fetchall()

    print("\n")
    print("=" * 78)
    print("                 REKAP KEHADIRAN MAHASISWA")
    print("=" * 78)
    print(f"Mata Kuliah : {exam['course_name']}")
    print(f"Tanggal     : {exam['exam_date']}")
    print(f"ID Ujian    : {exam_id}")
    print(f"Waktu Ujian : {exam['start_time']} - {exam['end_time']}")
    print("-" * 78)

    if not participants:
        print("Belum ada mahasiswa yang terdaftar sebagai peserta ujian.")
        print("=" * 78)
        return

    print(
        f"{'NO':<4}"
        f"{'NIM':<18}"
        f"{'NAMA':<28}"
        f"{'STATUS':<15}"
        f"WAKTU PRESENSI"
    )
    print("-" * 100)

    total_peserta = len(participants)
    jumlah_hadir = 0

    for nomor, student in enumerate(participants, start=1):
        if student["attendance_time"] is not None:
            status = student["status"]
            waktu = student["attendance_time"]

            if status == "HADIR":
                jumlah_hadir += 1
        else:
            status = "BELUM HADIR"
            waktu = "-"

        print(
            f"{nomor:<4}"
            f"{student['nim']:<18}"
            f"{student['name'][:26]:<28}"
            f"{status:<15}"
            f"{waktu}"
        )

    belum_hadir = total_peserta - jumlah_hadir
    persentase = (jumlah_hadir / total_peserta) * 100

    print("-" * 100)
    print(f"Total Peserta : {total_peserta}")
    print(f"Hadir         : {jumlah_hadir}")
    print(f"Belum Hadir   : {belum_hadir}")
    print(f"Persentase    : {persentase:.2f}%")
    print("=" * 100)


# ==========================================
# PROGRAM UTAMA
# ==========================================

if __name__ == "__main__":
    initialize_database()

    while True:
        exam = pilih_sesi_ujian()

        if exam is not None:
            tampilkan_rekap(exam)

        ulang = input(
            "\nLihat rekap sesi ujian lain? (y/n): "
        ).strip().lower()

        if ulang != "y":
            print("Program rekap kehadiran selesai.")
            break

