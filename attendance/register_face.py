from datetime import datetime
from pathlib import Path
import sys

import cv2

BASE_DIR = Path(__file__).resolve().parents[1]
DATASET_DIR = BASE_DIR / "datasets" / "faces"

sys.path.insert(0, str(BASE_DIR / "src"))
sys.path.insert(0, str(BASE_DIR / "attendance"))

from database import add_student, initialize_database
from train_lbph import train_lbph


def pilih_file_gambar():
    """
    Membuka jendela dialog pemilihan file gambar (bisa lebih dari 1 file).
    Jika dialog tidak tersedia/dibatalkan, pengguna bisa mengetik path manual.
    """
    selected_files = []

    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        file_paths = filedialog.askopenfilenames(
            title="Pilih Foto Wajah Mahasiswa (bisa pilih lebih dari 1)",
            filetypes=[
                ("File Gambar", "*.jpg *.jpeg *.png *.webp *.bmp"),
                ("Semua File", "*.*")
            ]
        )
        root.destroy()

        if file_paths:
            selected_files = [Path(p) for p in file_paths]
    except Exception:
        pass

    if not selected_files:
        print(
            "\nMasukkan path file gambar atau folder berisi gambar "
            "(pisahkan dengan koma jika lebih dari satu):"
        )
        raw_input = input("Path gambar/folder: ").strip()
        if not raw_input:
            return []

        for part in raw_input.split(","):
            cleaned = part.strip().strip('"').strip("'")
            if not cleaned:
                continue
            path = Path(cleaned)
            if not path.is_absolute():
                path = BASE_DIR / path

            if path.is_dir():
                for child in sorted(path.iterdir()):
                    if child.suffix.lower() in {
                        ".jpg", ".jpeg", ".png", ".webp", ".bmp"
                    }:
                        selected_files.append(child)
            elif path.is_file():
                selected_files.append(path)
            else:
                print(f"[PERINGATAN] File tidak ditemukan: {path}")

    return selected_files


def simpan_potongan_wajah(gray_face, save_dir, student_id, buat_variasi=True):
    """
    Menyimpan gambar wajah grayscale berukuran 200x200 ke folder dataset.
    Jika buat_variasi=True, membuat beberapa variasi (flip & kecerahan)
    agar pelatihan LBPH tetap akurat meskipun hanya dari 1 foto.
    """
    face_resized = cv2.resize(gray_face, (200, 200))
    variasi_list = [face_resized]

    if buat_variasi:
        # 1. Flip horizontal
        variasi_list.append(cv2.flip(face_resized, 1))
        # 2. Sedikit lebih terang
        variasi_list.append(
            cv2.convertScaleAbs(face_resized, alpha=1.1, beta=10)
        )
        # 3. Sedikit lebih gelap
        variasi_list.append(
            cv2.convertScaleAbs(face_resized, alpha=0.9, beta=-10)
        )
        # 4. Equalize histogram
        variasi_list.append(cv2.equalizeHist(face_resized))

    jumlah_tersimpan = 0
    for idx, img in enumerate(variasi_list, start=1):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{student_id}_{timestamp}_{idx}.jpg"
        cv2.imwrite(str(save_dir / filename), img)
        jumlah_tersimpan += 1

    return jumlah_tersimpan


def register_face_from_images(
    student_id,
    student_name,
    image_paths=None,
    auto_train=True
):
    """
    Mendaftarkan wajah mahasiswa dari file gambar (tanpa harus buka kamera)
    dan menyimpan data mahasiswa ke database.
    """
    student_id = str(student_id).strip()
    student_name = student_name.strip()

    if not student_id or not student_name:
        print("NIM dan nama mahasiswa wajib diisi.")
        return 0

    initialize_database()
    add_student(student_id, student_name)

    if image_paths is None:
        print(
            "\nSilakan pilih file gambar wajah untuk "
            f"{student_name} ({student_id})..."
        )
        image_paths = pilih_file_gambar()

    if not image_paths:
        print("Tidak ada file gambar yang dipilih.")
        return 0

    save_dir = DATASET_DIR / student_id
    save_dir.mkdir(parents=True, exist_ok=True)

    cascade_path = (
        cv2.data.haarcascades
        + "haarcascade_frontalface_default.xml"
    )
    face_cascade = cv2.CascadeClassifier(cascade_path)

    total_saved = 0
    buat_variasi = len(image_paths) < 5

    for img_path in image_paths:
        img_path = Path(img_path)
        image = cv2.imread(str(img_path))

        if image is None:
            print(f"[GAGAL] Tidak bisa membaca gambar: {img_path}")
            continue

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=4,
            minSize=(60, 60)
        )

        if len(faces) > 0:
            # Ambil wajah dengan ukuran kotak terbesar pada foto
            x, y, w, h = max(faces, key=lambda rect: rect[2] * rect[3])
            face_crop = gray[y:y + h, x:x + w]
            count = simpan_potongan_wajah(
                face_crop, save_dir, student_id, buat_variasi=buat_variasi
            )
            total_saved += count
            print(
                f"[BERHASIL] Wajah terdeteksi dari '{img_path.name}' "
                f"({count} sampel disimpan)."
            )
        else:
            # Jika foto sudah berupa close-up wajah sehingga Haar Cascade
            # tidak mendeteksi batas luar, simpan langsung ukuran 200x200.
            count = simpan_potongan_wajah(
                gray, save_dir, student_id, buat_variasi=buat_variasi
            )
            total_saved += count
            print(
                f"[INFO] Menyimpan gambar langsung dari '{img_path.name}' "
                f"({count} sampel disimpan)."
            )

    print(f"\nTotal sampel tersimpan: {total_saved}")
    print(f"Folder data: {save_dir}")

    if total_saved > 0 and auto_train:
        print("\nMelatih ulang model LBPH secara otomatis...")
        train_lbph()

    return total_saved


def register_face(student_id, student_name, samples=20, auto_train=True):
    """
    Mengambil sampel wajah mahasiswa dari kamera laptop,
    menyimpan data mahasiswa ke database, dan melatih ulang LBPH.
    """

    student_id = str(student_id).strip()
    student_name = student_name.strip()

    if not student_id or not student_name:
        print("ID dan nama mahasiswa wajib diisi.")
        return

    # Pastikan database siap dan simpan data mahasiswa ke tabel students.
    initialize_database()
    add_student(student_id, student_name)

    # Gunakan ID sebagai nama folder agar aman dari
    # karakter khusus pada nama mahasiswa.
    save_dir = DATASET_DIR / student_id
    save_dir.mkdir(parents=True, exist_ok=True)

    cascade_path = (
        cv2.data.haarcascades
        + "haarcascade_frontalface_default.xml"
    )
    face_cascade = cv2.CascadeClassifier(cascade_path)

    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not camera.isOpened():
        print("Kamera tidak bisa dibuka.")
        return

    saved = 0

    print(f"Pendaftaran wajah: {student_name} ({student_id})")
    print("Posisikan wajah di depan kamera.")
    print("Tekan Q untuk membatalkan.")

    try:
        while saved < samples:
            ret, frame = camera.read()

            if not ret:
                print("Gagal membaca kamera.")
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(100, 100)
            )

            for (x, y, w, h) in faces:
                cv2.rectangle(
                    frame, (x, y), (x + w, y + h),
                    (0, 255, 0), 2
                )

                cv2.putText(
                    frame,
                    "Face detected",
                    (x, max(y - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )

                # Simpan grayscale wajah, bukan seluruh frame.
                face = gray[y:y + h, x:x + w]
                face = cv2.resize(face, (200, 200))

                filename = (
                    f"{student_id}_"
                    f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
                )

                cv2.imwrite(str(save_dir / filename), face)
                saved += 1

                # Ambil satu sampel per frame.
                break

            cv2.putText(
                frame,
                f"Samples: {saved}/{samples}",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2
            )

            cv2.imshow("Register Student Face", frame)

            if cv2.waitKey(200) & 0xFF == ord("q"):
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()

    print(f"Sampel tersimpan: {saved}")
    print(f"Folder data: {save_dir}")

    if saved > 0 and auto_train:
        print("\nMelatih ulang model LBPH secara otomatis...")
        train_lbph()


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        student_id = sys.argv[1]
        student_name = sys.argv[2]
    else:
        student_id = input("Masukkan NIM/ID mahasiswa: ").strip()
        student_name = input("Masukkan nama mahasiswa  : ").strip()

    print("\nPilih metode pendaftaran wajah:")
    print("1. Ambil sampel wajah dari Kamera")
    print("2. Tambah dari File Gambar (Upload foto)")
    metode = input("Pilih metode (1/2): ").strip()

    if metode == "2":
        register_face_from_images(student_id, student_name, auto_train=True)
    else:
        register_face(student_id, student_name, samples=10, auto_train=True)
