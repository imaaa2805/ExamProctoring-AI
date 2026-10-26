import cv2

CAMERA_URL = "http://192.168.56.1"


def main():
    print("Menguji koneksi kamera ESP32-CAM...")

    camera = cv2.VideoCapture(CAMERA_URL)

    if not camera.isOpened():
        print("Kamera belum berhasil dibuka.")
        print("Alamat tersebut mungkin hanya halaman konfigurasi.")
        return

    success, frame = camera.read()

    if success:
        cv2.imshow("ESP32-CAM", frame)
        print("Frame kamera berhasil diterima.")
        cv2.waitKey(0)
    else:
        print("Belum berhasil menerima gambar kamera.")

    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()