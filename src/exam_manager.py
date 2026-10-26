from database import get_connection, initialize_database


def create_exam():
    print("\n=== BUAT SESI UJIAN ===")

    course_name = input("Nama mata kuliah: ").strip()
    exam_date = input("Tanggal ujian (YYYY-MM-DD): ").strip()
    start_time = input("Waktu mulai (HH:MM): ").strip()
    end_time = input("Waktu selesai (HH:MM): ").strip()

    if not course_name or not exam_date:
        print("Nama mata kuliah dan tanggal wajib diisi.")
        return

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO exams (
                course_name, exam_date, start_time, end_time
            )
            VALUES (?, ?, ?, ?)
            """,
            (course_name, exam_date, start_time, end_time)
        )

        exam_id = cursor.lastrowid

    print("\nSesi ujian berhasil dibuat!")
    print(f"ID ujian: {exam_id}")
    print(f"Mata kuliah: {course_name}")
    print(f"Tanggal: {exam_date}")


def list_exams():
    with get_connection() as connection:
        exams = connection.execute(
            """
            SELECT exam_id, course_name, exam_date, start_time, end_time
            FROM exams
            ORDER BY exam_date, start_time
            """
        ).fetchall()

    print("\n=== DAFTAR SESI UJIAN ===")

    if not exams:
        print("Belum ada sesi ujian.")
        return

    for exam in exams:
        print(
            f"ID: {exam['exam_id']} | "
            f"Mata kuliah: {exam['course_name']} | "
            f"Tanggal: {exam['exam_date']} | "
            f"Waktu: {exam['start_time']} - {exam['end_time']}"
        )


if __name__ == "__main__":
    initialize_database()

    while True:
        print("\n=== MENU PENGELOLAAN UJIAN ===")
        print("1. Buat sesi ujian")
        print("2. Lihat sesi ujian")
        print("3. Keluar")

        pilihan = input("Pilih menu: ").strip()

        if pilihan == "1":
            create_exam()
        elif pilihan == "2":
            list_exams()
        elif pilihan == "3":
            print("Program selesai.")
            break
        else:
            print("Pilihan tidak valid.")

