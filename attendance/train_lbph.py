from pathlib import Path
import sys

import cv2
import numpy as np


BASE_DIR = Path(__file__).resolve().parents[1]
DATASET_DIR = BASE_DIR / "datasets" / "faces"
MODEL_PATH = BASE_DIR / "models" / "lbph_model.yml"
LABELS_PATH = BASE_DIR / "models" / "lbph_labels.txt"

sys.path.insert(0, str(BASE_DIR / "src"))

from database import (
    add_student,
    get_connection,
    initialize_database,
    sync_face_labels,
)


def ensure_student_in_db(nim):
    """
    Memastikan NIM yang memiliki folder sampel wajah
    sudah terdaftar di tabel students pada database.
    """
    with get_connection() as connection:
        row = connection.execute(
            "SELECT nim, name FROM students WHERE nim = ?",
            (nim,)
        ).fetchone()

    if row is not None:
        return row["name"]

    print(
        f"\n[INFO] NIM {nim} memiliki sampel wajah di folder dataset, "
        f"tetapi belum terdaftar di database."
    )
    nama = input(
        f"Masukkan nama mahasiswa untuk NIM {nim} "
        f"(Enter untuk memakai 'Mahasiswa {nim}'): "
    ).strip()

    if not nama:
        nama = f"Mahasiswa {nim}"

    add_student(nim, nama)
    return nama


def train_lbph():
    if not hasattr(cv2, "face"):
        raise RuntimeError(
            "LBPH tidak tersedia. Instal opencv-contrib-python."
        )

    if not DATASET_DIR.exists():
        raise FileNotFoundError(
            f"Folder tidak ditemukan: {DATASET_DIR}"
        )

    initialize_database()

    face_images = []
    labels = []
    label_to_student = {}
    student_names = {}
    next_label = 1

    student_folders = sorted(
        folder for folder in DATASET_DIR.iterdir()
        if folder.is_dir()
    )

    if not student_folders:
        raise ValueError(
            "Belum ada folder mahasiswa di datasets/faces."
        )

    print("\n=== PEMERIKSAAN DATA WAJAH ===")

    for student_folder in student_folders:
        student_id = student_folder.name

        image_files = sorted(
            path for path in student_folder.iterdir()
            if path.suffix.lower() in {".jpg", ".jpeg", ".png"}
        )

        print(
            f"NIM: {student_id} | "
            f"Jumlah file gambar: {len(image_files)}"
        )

        valid_images = []

        for image_path in image_files:
            image = cv2.imread(
                str(image_path),
                cv2.IMREAD_GRAYSCALE
            )

            if image is None:
                print(
                    f"  [GAGAL] Tidak bisa membaca: "
                    f"{image_path.name}"
                )
                continue

            image = cv2.resize(image, (200, 200))
            image = cv2.equalizeHist(image)
            valid_images.append(image)

        if not valid_images:
            print(
                f"  [PERINGATAN] Tidak ada sampel valid "
                f"untuk NIM {student_id}."
            )
            continue

        student_name = ensure_student_in_db(student_id)
        student_names[student_id] = student_name

        label = next_label
        next_label += 1

        label_to_student[label] = student_id

        for image in valid_images:
            face_images.append(image)
            labels.append(label)

        print(
            f"  Label {label} ditetapkan untuk "
            f"NIM {student_id} ({student_name}) | "
            f"Sampel valid: {len(valid_images)}"
        )

    if not face_images:
        raise ValueError(
            "Tidak ada sampel wajah valid untuk pelatihan."
        )

    # Latih model menggunakan seluruh sampel valid.
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(
        face_images,
        np.array(labels, dtype=np.int32)
    )

    # Simpan model.
    MODEL_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    recognizer.write(str(MODEL_PATH))

    # Simpan pemetaan label -> NIM.
    with LABELS_PATH.open("w", encoding="utf-8") as file:
        for label, student_id in label_to_student.items():
            file.write(f"{label},{student_id}\n")

    # Sinkronkan label ke tabel students di database.
    sync_face_labels()

    print("\n=== PELATIHAN LBPH SELESAI ===")
    print(f"Jumlah sampel valid: {len(face_images)}")
    print(f"Jumlah mahasiswa   : {len(label_to_student)}")
    print(f"Model              : {MODEL_PATH}")
    print(f"Pemetaan label     : {LABELS_PATH}")

    print("\n=== PEMETAAN LABEL ===")

    for label, student_id in label_to_student.items():
        nama = student_names.get(student_id, "-")
        print(f"Label {label} -> NIM {student_id} ({nama})")

    print("\nPelatihan selesai. Periksa pemetaan di atas.")


if __name__ == "__main__":
    train_lbph()
