from pathlib import Path
import sys

import cv2

# ==========================================
# KONFIGURASI PROJECT
# ==========================================

BASE_DIR = Path(__file__).resolve().parents[1]

DATASET_DIR = BASE_DIR / "datasets" / "faces"
MODEL_PATH = BASE_DIR / "models" / "lbph_model.yml"
LABELS_PATH = BASE_DIR / "models" / "lbph_labels.txt"

# Agar modul database dan pelatihan bisa digunakan.
sys.path.insert(0, str(BASE_DIR / "src"))
sys.path.insert(0, str(BASE_DIR / "attendance"))

from database import get_connection, initialize_database
from train_lbph import ensure_student_in_db, train_lbph


# ==========================================
# MEMBACA DATA MAHASISWA
# ==========================================

def load_students():
    initialize_database()
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT nim, name FROM students"
        ).fetchall()

    return {
        str(row["nim"]): row["name"]
        for row in rows
    }


def is_model_outdated():
    """
    Memeriksa apakah model LBPH belum ada atau belum
    memuat seluruh folder sampel wajah terbaru di datasets/faces.
    """
    if not MODEL_PATH.exists() or MODEL_PATH.stat().st_size == 0:
        return True

    if not LABELS_PATH.exists():
        return True

    if not DATASET_DIR.exists():
        return False

    # Baca NIM yang sudah ada di lbph_labels.txt
    labeled_nims = set()
    for line in LABELS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(",", 1)
        if len(parts) == 2:
            labeled_nims.add(parts[1].strip())

    model_mtime = MODEL_PATH.stat().st_mtime

    dataset_nims = set()
    for folder in DATASET_DIR.iterdir():
        if not folder.is_dir():
            continue
        images = [
            p for p in folder.iterdir()
            if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
        ]
        if images:
            dataset_nims.add(folder.name)
            # Jika ada foto wajah yang lebih baru dari model
            if any(img.stat().st_mtime > model_mtime for img in images):
                return True

    # Jika daftar folder NIM di dataset berbeda dengan label model
    if dataset_nims and dataset_nims != labeled_nims:
        return True

    return False


# ==========================================
# PENGENALAN WAJAH LBPH
# ==========================================

class FaceRecognizer:

    def __init__(self, threshold=70):
        if not hasattr(cv2, "face"):
            raise RuntimeError(
                "Modul LBPH tidak tersedia. "
                "Pastikan opencv-contrib-python sudah terpasang."
            )

        # Jika ada mahasiswa baru di datasets/faces yang belum dilatih,
        # latih ulang model secara otomatis.
        if is_model_outdated():
            print(
                "\n[INFO] Dataset wajah baru terdeteksi atau model belum sinkron. "
                "Melatih ulang model LBPH..."
            )
            train_lbph()

        if not MODEL_PATH.exists() or MODEL_PATH.stat().st_size == 0:
            raise FileNotFoundError(
                f"Model LBPH tidak ditemukan: {MODEL_PATH}"
            )

        if not LABELS_PATH.exists():
            raise FileNotFoundError(
                f"File label tidak ditemukan: {LABELS_PATH}"
            )

        # Muat model LBPH.
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.recognizer.read(str(MODEL_PATH))

        self.threshold = threshold

        # Baca pemetaan label LBPH -> NIM.
        self.label_to_nim = {}

        with LABELS_PATH.open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()

                if not line:
                    continue

                parts = line.split(",", 1)

                if len(parts) != 2:
                    raise ValueError(
                        f"Format label tidak valid: {line}"
                    )

                label = int(parts[0].strip())
                nim = parts[1].strip()

                if label in self.label_to_nim:
                    raise ValueError(
                        f"Label duplikat ditemukan: {label}"
                    )

                self.label_to_nim[label] = nim
                ensure_student_in_db(nim)

        # Baca nama dan NIM dari database.
        self.students = load_students()

        # Detektor wajah Haar Cascade.
        cascade_path = (
            cv2.data.haarcascades
            + "haarcascade_frontalface_default.xml"
        )

        self.face_cascade = cv2.CascadeClassifier(cascade_path)

        if self.face_cascade.empty():
            raise RuntimeError(
                "Model deteksi wajah gagal dimuat."
            )

        print("Face Recognizer berhasil dimuat!")
        print(f"Jumlah mahasiswa di database: {len(self.students)}")
        print(f"Jumlah label LBPH: {len(self.label_to_nim)}")
        print(f"Threshold LBPH: {self.threshold}")
        print("Tekan Q pada jendela kamera untuk keluar.")

    # ==========================================
    # MENGENALI WAJAH DALAM FRAME
    # ==========================================

    def recognize_frame(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80)
        )

        results = []

        for (x, y, w, h) in faces:
            # Potong area wajah.
            face = gray[y:y + h, x:x + w]

            # Samakan ukuran dan normalisasi kontras dengan sampel pelatihan.
            face = cv2.resize(face, (200, 200))
            face = cv2.equalizeHist(face)

            # Prediksi label dan jarak LBPH.
            label, distance = self.recognizer.predict(face)

            nim = self.label_to_nim.get(label)
            name = self.students.get(nim) if nim else None

            # Hanya kenali jika label cocok dan distance di bawah threshold.
            known = (
                nim is not None
                and distance <= self.threshold
            )

            if known:
                display_name = name or f"Mahasiswa ({nim})"
                text = f"{display_name} | {nim}"
                color = (0, 255, 0)
                status = "Dikenali"
            else:
                display_name = None
                text = "Tidak dikenal"
                color = (0, 0, 255)
                status = "Tidak dikenal"

            # Gambar kotak wajah.
            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                color,
                2
            )

            # Tampilkan identitas dan nilai distance.
            cv2.putText(
                frame,
                text,
                (x, max(y - 30, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2
            )

            distance_text = f"Distance: {distance:.2f}"

            cv2.putText(
                frame,
                distance_text,
                (x, y + h + 22),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1
            )

            results.append({
                "nim": nim if known else None,
                "nama": display_name if known else None,
                "status": status,
                "predicted_label": int(label),
                "distance": round(float(distance), 2)
            })

        return frame, results


# ==========================================
# MENJALANKAN KAMERA
# ==========================================

if __name__ == "__main__":
    recognizer = FaceRecognizer(threshold=70)

    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not camera.isOpened():
        raise RuntimeError(
            "Kamera laptop tidak bisa dibuka."
        )

    print("Pengenalan wajah berjalan.")

    try:
        while True:
            ret, frame = camera.read()

            if not ret:
                print("Gagal membaca frame kamera.")
                break

            frame, results = recognizer.recognize_frame(frame)

            cv2.imshow(
                "Face Recognition - Exam Proctoring AI",
                frame
            )

            # Tampilkan hasil prediksi di terminal.
            for result in results:
                print(
                    f"Status: {result['status']} | "
                    f"NIM: {result['nim']} | "
                    f"Nama: {result['nama']} | "
                    f"Label: {result['predicted_label']} | "
                    f"Distance: {result['distance']}"
                )

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()
