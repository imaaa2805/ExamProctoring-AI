from pathlib import Path
from datetime import datetime
from ultralytics import YOLO


# ==================================================
# KONFIGURASI
# ==================================================

BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = BASE_DIR / "models" / "yolo11n.pt"

# Objek yang relevan untuk pengawasan ujian.
TARGET_OBJECTS = {
    "person",
    "cell phone",
    "backpack",
    "handbag",
    "suitcase",
}


# ==================================================
# OBJECT DETECTOR
# ==================================================

class ObjectDetector:
    def __init__(self, confidence=0.40):
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model YOLO tidak ditemukan: {MODEL_PATH}"
            )

        if MODEL_PATH.stat().st_size == 0:
            raise ValueError(
                f"File model YOLO kosong: {MODEL_PATH}"
            )

        self.model = YOLO(str(MODEL_PATH))
        self.confidence = confidence

        print("YOLO berhasil dimuat!")
        print(f"Model: {MODEL_PATH}")

    def detect(self, image_path, show=False):
        """
        Mendeteksi objek pada gambar.

        Return:
            list[dict]: daftar objek yang terdeteksi.
        """

        image_path = Path(image_path)

        if not image_path.is_absolute():
            image_path = BASE_DIR / image_path

        if not image_path.exists():
            raise FileNotFoundError(
                f"Gambar tidak ditemukan: {image_path}"
            )

        results = self.model.predict(
            source=str(image_path),
            conf=self.confidence,
            verbose=False,
        )

        detected_objects = []

        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                object_name = self.model.names[class_id]
                confidence = float(box.conf[0])

                # Abaikan objek yang tidak relevan untuk
                # daftar target pengawasan ujian.
                if object_name not in TARGET_OBJECTS:
                    continue

                x1, y1, x2, y2 = map(
                    int, box.xyxy[0].tolist()
                )

                detected_objects.append({
                    "object": object_name,
                    "confidence": round(confidence, 3),
                    "bbox": {
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                    },
                    "timestamp": datetime.now().isoformat(
                        timespec="seconds"
                    ),
                    "source": str(image_path),
                })

            if show:
                result.show()

        return detected_objects

    def print_results(self, detected_objects):
        """Menampilkan hasil deteksi di terminal."""

        if not detected_objects:
            print("Tidak ada objek target yang terdeteksi.")
            return

        print("\n=== HASIL DETEKSI PENGAWASAN ===")

        for item in detected_objects:
            print(
                f"Objek: {item['object']} | "
                f"Confidence: {item['confidence']:.1%} | "
                f"Posisi: {item['bbox']}"
            )


# ==================================================
# PENGUJIAN MANDIRI
# ==================================================

if __name__ == "__main__":
    detector = ObjectDetector(confidence=0.40)

    image_path = "datasets/yolo/687313529p.webp"

    detections = detector.detect(
        image_path=image_path,
        show=True,
    )

    detector.print_results(detections)