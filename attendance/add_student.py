from pathlib import Path
import sys

# Lokasi utama project
BASE_DIR = Path(__file__).resolve().parents[1]

# Impor fungsi database dan registrasi wajah
sys.path.insert(0, str(BASE_DIR / "src"))
sys.path.insert(0, str(BASE_DIR / "attendance"))

from database import add_student, get_connection, initialize_database
from register_face import register_face, register_face_from_images


def main():
    print("=" * 40)
    print("     TAMBAH DATA MAHASISWA")
    print("       EXAM PROCTORING AI")
    print("=" * 40)

    initialize_database()

    # Input data mahasiswa secara manual
    if len(sys.argv) >= 3:
        nim = sys.argv[1].strip()
        nama = sys.argv[2].strip()
    else:
        nim = input("Masukkan NIM mahasiswa : ").strip()
        nama = input("Masukkan nama mahasiswa: ").strip()

    if not nim or not nama:
        print("\nNIM dan nama tidak boleh kosong!")
        return

    # Cek apakah NIM sudah terdaftar
    with get_connection() as connection:
        existing = connection.execute(
            "SELECT nim, name FROM students WHERE nim = ?",
            (nim,)
        ).fetchone()

    if existing:
        print(
            f"\nNIM {nim} sudah terdaftar atas nama "
            f"{existing['name']}."
        )
        perbarui = input(
            "Apakah ingin memperbarui nama / menambah sampel wajah? (y/n): "
        ).strip().lower()
        if perbarui != "y":
            return

    # Simpan mahasiswa ke database
    add_student(nim, nama)

    print("\nData mahasiswa berhasil disimpan ke database!")
    print(f"NIM  : {nim}")
    print(f"Nama : {nama}")

    # Pilihan metode penambahan sampel wajah
    print("\nPilih cara menambahkan sampel wajah:")
    print("1. Ambil wajah menggunakan Kamera")
    print("2. Tambah dari File Gambar (Pilih foto dari komputer)")
    print("3. Lewati (simpan NIM & nama saja)")

    pilihan = input("Pilih (1/2/3): ").strip()

    if pilihan == "1":
        print("\nKamera akan dibuka. Ikuti petunjuk di layar.")
        register_face(nim, nama, samples=10, auto_train=True)
    elif pilihan == "2":
        register_face_from_images(nim, nama, auto_train=True)
    else:
        print("\nPengambilan sampel wajah dilewati.")

    print("\nSelesai.")


if __name__ == "__main__":
    main()
