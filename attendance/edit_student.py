import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

from database import get_connection


def tampilkan_mahasiswa():
    conn = get_connection()

    try:
        data = conn.execute(
            "SELECT nim, name FROM students ORDER BY name"
        ).fetchall()

        print("\n===== DAFTAR MAHASISWA =====")

        if not data:
            print("Belum ada data mahasiswa.")
            return

        for mahasiswa in data:
            print(f"NIM: {mahasiswa['nim']} | Nama: {mahasiswa['name']}")

    finally:
        conn.close()


def edit_mahasiswa():
    tampilkan_mahasiswa()

    nim_lama = input("\nMasukkan NIM yang ingin diedit: ").strip()

    conn = get_connection()

    try:
        mahasiswa = conn.execute(
            "SELECT nim, name FROM students WHERE nim = ?",
            (nim_lama,)
        ).fetchone()

        if mahasiswa is None:
            print("\nMahasiswa tidak ditemukan!")
            return

        print("\nData saat ini:")
        print(f"NIM  : {mahasiswa['nim']}")
        print(f"Nama : {mahasiswa['name']}")

        nim_baru = input(
            "\nMasukkan NIM baru (Enter jika tetap): "
        ).strip()

        nama_baru = input(
            "Masukkan nama baru (Enter jika tetap): "
        ).strip()

        # Pertahankan data lama jika input kosong
        nim_baru = nim_baru or mahasiswa["nim"]
        nama_baru = nama_baru or mahasiswa["name"]

        if nim_baru != mahasiswa["nim"]:
            nim_terpakai = conn.execute(
                "SELECT nim FROM students WHERE nim = ?",
                (nim_baru,)
            ).fetchone()

            if nim_terpakai:
                print("\nGagal! NIM tersebut sudah digunakan.")
                return

        if (
            nim_baru == mahasiswa["nim"]
            and nama_baru == mahasiswa["name"]
        ):
            print("\nTidak ada perubahan data.")
            return

        konfirmasi = input(
            f"\nSimpan perubahan menjadi NIM {nim_baru}, "
            f"nama {nama_baru}? (y/n): "
        ).strip().lower()

        if konfirmasi != "y":
            print("\nPerubahan dibatalkan.")
            return

        conn.execute("PRAGMA defer_foreign_keys = ON")

        conn.execute(
            """
            UPDATE students
            SET nim = ?, name = ?
            WHERE nim = ?
            """,
            (nim_baru, nama_baru, mahasiswa["nim"])
        )

        conn.commit()

        print("\nData mahasiswa berhasil diperbarui!")
        print(f"NIM  : {nim_baru}")
        print(f"Nama : {nama_baru}")

        print(
            "\nCatatan: folder sampel wajah dan file label model "
            "belum diubah. Jika NIM berubah, keduanya perlu "
            "disinkronkan sebelum pengenalan wajah digunakan lagi."
        )

    except sqlite3.IntegrityError as error:
        conn.rollback()
        print(f"\nPerubahan gagal karena kendala database: {error}")

    finally:
        conn.close()


if __name__ == "__main__":
    edit_mahasiswa()
