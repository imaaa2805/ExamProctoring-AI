from database import get_connection, initialize_database


def pilih_sesi_ujian(exams):
    """
    Menampilkan daftar sesi ujian dengan nomor urut (1, 2, 3, ...)
    dan mengembalikan data ujian yang dipilih.
    """
    print("\nDaftar sesi ujian:")
    for idx, exam in enumerate(exams, start=1):
        print(
            f"{idx}. {exam['course_name']} | "
            f"Tanggal: {exam['exam_date']} "
            f"(ID Ujian: {exam['exam_id']})"
        )

    pilihan = input(
        f"\nPilih nomor sesi ujian (1-{len(exams)}): "
    ).strip()

    if not pilihan.isdigit():
        print("Pilihan harus berupa angka.")
        return None

    nomor = int(pilihan)

    # Prioritaskan berdasarkan nomor urut tampilan (1, 2, 3, ...)
    if 1 <= nomor <= len(exams):
        return exams[nomor - 1]

    # Cadangan jika pengguna mengetik exam_id secara langsung
    for exam in exams:
        if exam["exam_id"] == nomor:
            return exam

    print("Nomor sesi ujian tidak valid.")
    return None


def add_participant():
    print("\n=== TAMBAH PESERTA UJIAN ===")

    with get_connection() as connection:
        exams = connection.execute(
            """
            SELECT exam_id, course_name, exam_date
            FROM exams
            ORDER BY exam_date, exam_id
            """
        ).fetchall()

        students = connection.execute(
            """
            SELECT nim, name
            FROM students
            ORDER BY nim
            """
        ).fetchall()

    if not exams:
        print("Belum ada sesi ujian. Buat sesi ujian terlebih dahulu.")
        return

    if not students:
        print("Belum ada mahasiswa di database.")
        return

    selected_exam = pilih_sesi_ujian(exams)
    if selected_exam is None:
        return

    exam_id = selected_exam["exam_id"]

    # Cek mahasiswa yang sudah terdaftar di sesi ujian ini
    with get_connection() as connection:
        existing_rows = connection.execute(
            """
            SELECT nim FROM exam_participants
            WHERE exam_id = ?
            """,
            (exam_id,)
        ).fetchall()
    registered_nims = {row["nim"] for row in existing_rows}

    print(
        f"\nDaftar mahasiswa untuk ujian "
        f"'{selected_exam['course_name']}':"
    )
    for idx, student in enumerate(students, start=1):
        status = (
            " [Sudah Terdaftar]"
            if student["nim"] in registered_nims
            else ""
        )
        print(
            f"{idx}. {student['name']} ({student['nim']}){status}"
        )
    print("0. Tambahkan SEMUA mahasiswa di atas")

    pilihan_input = input(
        f"\nPilih nomor mahasiswa (contoh: 1 atau 1,2,3 atau 0 untuk semua): "
    ).strip()

    if not pilihan_input:
        print("Tidak ada pilihan yang dimasukkan.")
        return

    # Pisahkan input jika memilih lebih dari satu (misal: "1,2,3" atau "1 2")
    tokens = [
        token.strip()
        for token in pilihan_input.replace(",", " ").split()
        if token.strip()
    ]

    selected_students = []

    if "0" in tokens or pilihan_input.lower() == "semua":
        selected_students = list(students)
    else:
        for token in tokens:
            if token.isdigit():
                nomor = int(token)
                if 1 <= nomor <= len(students):
                    student = students[nomor - 1]
                    if student not in selected_students:
                        selected_students.append(student)
                else:
                    # Cek apabila pengguna mengetik NIM lengkap
                    matched = next(
                        (s for s in students if s["nim"] == token),
                        None
                    )
                    if matched and matched not in selected_students:
                        selected_students.append(matched)
                    else:
                        print(f"Nomor pilihan '{token}' tidak valid.")
            else:
                print(f"Input '{token}' tidak valid.")

    if not selected_students:
        print("Tidak ada mahasiswa valid yang dipilih.")
        return

    berhasil = 0
    sudah_ada = 0

    with get_connection() as connection:
        for student in selected_students:
            nim = student["nim"]
            nama = student["name"]
            try:
                connection.execute(
                    """
                    INSERT INTO exam_participants (exam_id, nim)
                    VALUES (?, ?)
                    """,
                    (exam_id, nim)
                )
                print(f"[BERHASIL] {nama} ({nim}) ditambahkan.")
                berhasil += 1
            except Exception as error:
                if "UNIQUE constraint failed" in str(error):
                    print(
                        f"[INFO] {nama} ({nim}) sudah terdaftar sebelumnya."
                    )
                    sudah_ada += 1
                else:
                    raise

    print(
        f"\nSelesai: {berhasil} mahasiswa ditambahkan"
        + (f", {sudah_ada} sudah terdaftar." if sudah_ada else ".")
    )


def list_participants():
    print("\n=== DAFTAR PESERTA UJIAN ===")

    with get_connection() as connection:
        exams = connection.execute(
            """
            SELECT exam_id, course_name, exam_date
            FROM exams
            ORDER BY exam_date, exam_id
            """
        ).fetchall()

    if not exams:
        print("Belum ada sesi ujian.")
        return

    selected_exam = pilih_sesi_ujian(exams)
    if selected_exam is None:
        return

    exam_id = selected_exam["exam_id"]

    with get_connection() as connection:
        participants = connection.execute(
            """
            SELECT s.nim, s.name
            FROM exam_participants ep
            JOIN students s ON s.nim = ep.nim
            WHERE ep.exam_id = ?
            ORDER BY s.nim
            """,
            (exam_id,)
        ).fetchall()

    print(
        f"\nPeserta pada ujian '{selected_exam['course_name']}' "
        f"({selected_exam['exam_date']}):"
    )

    if not participants:
        print("Belum ada peserta.")
        return

    for idx, student in enumerate(participants, start=1):
        print(f"{idx}. {student['name']} ({student['nim']})")


if __name__ == "__main__":
    initialize_database()

    while True:
        print("\n=== MENU PESERTA UJIAN ===")
        print("1. Tambah mahasiswa ke sesi ujian")
        print("2. Lihat peserta sesi ujian")
        print("3. Keluar")

        choice = input("Pilih menu (1-3): ").strip()

        if choice == "1":
            add_participant()
        elif choice == "2":
            list_participants()
        elif choice == "3":
            break
        else:
            print("Pilihan tidak valid.")
