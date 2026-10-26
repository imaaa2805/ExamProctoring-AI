from pathlib import Path
import cv2


class FaceDetector:
    """
    Mendeteksi wajah menggunakan Haar Cascade OpenCV.
    """

    def __init__(self):
        # Mengambil model deteksi wajah bawaan OpenCV.
        cascade_path = (
            cv2.data.haarcascades
            + "haarcascade_frontalface_default.xml"
        )

        self.face_cascade = cv2.CascadeClassifier(
            cascade_path
        )

        if self.face_cascade.empty():
            raise RuntimeError(
                "Model Haar Cascade gagal dimuat."
            )

        print("Face Detector berhasil dimuat!")

    def detect(self, image_path, show=True):
        """
        Mendeteksi wajah dari gambar.

        Mengembalikan daftar koordinat wajah.
        """

        image_path = Path(image_path)

        if not image_path.is_absolute():
            base_dir = Path(__file__).resolve().parents[1]
            image_path = base_dir / image_path

        if not image_path.exists():
            raise FileNotFoundError(
                f"Gambar tidak ditemukan: {image_path}"
            )

        image = cv2.imread(str(image_path))

        if image is None:
            raise ValueError(
                f"Gambar tidak bisa dibaca: {image_path}"
            )

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        detected_faces = []

        for index, (x, y, w, h) in enumerate(
            faces,
            start=1
        ):
            detected_faces.append({
                "face_id": index,
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h)
            })

            cv2.rectangle(
                image,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                2
            )

            cv2.putText(
                image,
                f"Face {index}",
                (x, max(y - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

        print(f"Jumlah wajah terdeteksi: {len(faces)}")

        if show:
            cv2.imshow("Face Detection", image)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        return detected_faces


if __name__ == "__main__":
    detector = FaceDetector()

    image_path = "datasets/yolo/687313529p.webp"

    faces = detector.detect(
        image_path=image_path,
        show=True
    )

    print("\nHasil deteksi wajah:")

    for face in faces:
        print(face)