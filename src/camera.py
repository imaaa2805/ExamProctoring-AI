import cv2


def open_camera():
    # Membuka kamera laptop default
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not camera.isOpened():
        print("ERROR: Kamera laptop tidak bisa dibuka.")
        return

    print("Kamera berhasil dibuka!")
    print("Tekan Q untuk menutup kamera.")

    while True:
        ret, frame = camera.read()

        if not ret:
            print("Gagal membaca gambar dari kamera.")
            break

        cv2.imshow("Exam Proctoring AI - Camera Test", frame)

        # Tekan Q untuk keluar
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    open_camera()