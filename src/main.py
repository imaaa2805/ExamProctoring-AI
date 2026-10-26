import cv2
from ultralytics import YOLO
from pathlib import Path


# =====================================
# KONFIGURASI
# =====================================

BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = BASE_DIR / "models" / "yolo11n.pt"

CONFIDENCE = 0.40


# =====================================
# INISIALISASI MODEL
# =====================================

def main():
    print("Memuat model YOLO11...")

    model = YOLO(str(MODEL_PATH))

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades
        + "haarcascade_frontalface_default.xml"
    )

    if face_cascade.empty():
        print("ERROR: Model deteksi wajah gagal dimuat.")
        return

    print("YOLO11 dan Face Detector berhasil dimuat!")

    # Membuka kamera laptop
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not camera.isOpened():
        print("ERROR: Kamera laptop tidak bisa dibuka.")
        return

    print("Sistem berjalan. Tekan Q untuk keluar.")

    try:
        while True:
            ret, frame = camera.read()

            if not ret:
                print("Gagal membaca frame kamera.")
                break

            # =====================================
            # 1. DETEKSI ORANG MENGGUNAKAN YOLO11
            # =====================================

            results = model.predict(
                source=frame,
                conf=CONFIDENCE,
                classes=[0],  # Kelas person
                verbose=False
            )

            # Menggambar kotak hasil deteksi YOLO
            annotated_frame = results[0].plot()

            # =====================================
            # 2. DETEKSI WAJAH MENGGUNAKAN OPENCV
            # =====================================

            gray = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2GRAY
            )

            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(40, 40)
            )

            for (x, y, w, h) in faces:
                cv2.rectangle(
                    annotated_frame,
                    (x, y),
                    (x + w, y + h),
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    annotated_frame,
                    "Face detected",
                    (x, max(y - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )

            # =====================================
            # 3. INFORMASI LAYAR
            # =====================================

            person_count = len(results[0].boxes)

            cv2.putText(
                annotated_frame,
                f"People: {person_count}",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 0),
                2
            )

            cv2.putText(
                annotated_frame,
                f"Faces: {len(faces)}",
                (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 0),
                2
            )

            cv2.imshow(
                "Exam Proctoring AI - Live Detection",
                annotated_frame
            )

            # Tekan Q untuk keluar
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()