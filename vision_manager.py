# core/vision_manager.py
import cv2
import time
import threading

try:
    from pyzbar import pyzbar
    _HAS_PYZBAR = True
except Exception:
    _HAS_PYZBAR = False

class VisionManager:
    """
    Simple webcam utilities for:
      - Face detection (Haar cascade)
      - QR/Barcode scanning (OpenCV QRCodeDetector, fallback: pyzbar)
    Windows: close the window with 'q'. Press 's' to save a snapshot.
    """

    def __init__(self):
        # Load OpenCV's built-in frontal face cascade
        self._cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._face_cascade = cv2.CascadeClassifier(self._cascade_path)
        self._qr = cv2.QRCodeDetector()
        self._lock = threading.Lock()

    # ------------- helpers -------------
    def _open_cam(self, index=0):
        cam = cv2.VideoCapture(index, cv2.CAP_DSHOW)  # CAP_DSHOW avoids long open delay on Windows
        if not cam.isOpened():
            # Try default backend fallback
            cam.release()
            cam = cv2.VideoCapture(index)
        if not cam.isOpened():
            raise RuntimeError("Could not open webcam. Is it in use by another app?")
        return cam

    def _put_text(self, frame, text, org=(10, 30)):
        cv2.putText(frame, text, org, cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)

    def _snapshot(self, frame, prefix="snap"):
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = f"{prefix}_{ts}.png"
        cv2.imwrite(path, frame)
        return path

    # ------------- public -------------
    def detect_faces(self, cam_index=0):
        """
        Live face detection. Draws rectangles around faces.
        Controls:
          - 'q' to quit
          - 's' to save snapshot
        """
        with self._lock:
            cam = self._open_cam(cam_index)
        try:
            while True:
                ok, frame = cam.read()
                if not ok:
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self._face_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
                )

                # draw boxes
                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                self._put_text(frame, f"Faces: {len(faces)}  |  q = quit, s = snapshot")
                cv2.imshow("Jarvis - Face Detection", frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                if key == ord('s'):
                    path = self._snapshot(frame, prefix="face")
                    print(f"[Vision] Snapshot saved: {path}")

        finally:
            cam.release()
            cv2.destroyAllWindows()

    def detect_qr(self, cam_index=0):
        """
        Live QR / Barcode scan.
        Uses OpenCV QRCodeDetector first; if nothing found, falls back to pyzbar (if available).
        Controls:
          - 'q' to quit
          - 's' to save snapshot
        """
        with self._lock:
            cam = self._open_cam(cam_index)
        try:
            last_text = None
            last_shown_time = 0
            while True:
                ok, frame = cam.read()
                if not ok:
                    break

                # 1) Try OpenCV QR detector
                data_list = []
                boxes_list = []

                try:
                    # OpenCV >= 4.7 has detectAndDecodeMulti; older has detectAndDecode
                    if hasattr(self._qr, "detectAndDecodeMulti"):
                        data, points, _ = self._qr.detectAndDecodeMulti(frame)
                        if data and points is not None:
                            for s, pts in zip(data, points):
                                if s:
                                    data_list.append(s)
                                    boxes_list.append(pts)
                    else:
                        s, pts = self._qr.detectAndDecode(frame)
                        if s:
                            data_list.append(s)
                            if pts is not None:
                                boxes_list.append(pts)
                except Exception:
                    pass

                # 2) Fallback to pyzbar if needed
                if not data_list and _HAS_PYZBAR:
                    try:
                        decoded = pyzbar.decode(frame)
                        for obj in decoded:
                            s = obj.data.decode("utf-8", errors="ignore")
                            if s:
                                data_list.append(s)
                                # Build a 4-point box for consistency
                                pts = obj.polygon
                                if len(pts) >= 4:
                                    boxes_list.append([(p.x, p.y) for p in pts[:4]])
                    except Exception:
                        pass

                # Draw boxes
                for pts in boxes_list:
                    pts = pts if isinstance(pts, (list, tuple)) else []
                    pts = [(int(x), int(y)) for (x, y) in pts]
                    for i in range(len(pts)):
                        cv2.line(frame, pts[i], pts[(i + 1) % len(pts)], (255, 0, 0), 2)

                # Show latest decoded text briefly
                if data_list:
                    text = "; ".join(data_list)
                    last_text = text
                    last_shown_time = time.time()

                if last_text and time.time() - last_shown_time < 2.0:
                    self._put_text(frame, f"QR: {last_text}")
                else:
                    self._put_text(frame, "q = quit, s = snapshot")

                cv2.imshow("Jarvis - QR / Barcode Scanner", frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                if key == ord('s'):
                    path = self._snapshot(frame, prefix="qr")
                    print(f"[Vision] Snapshot saved: {path}")
                # Print decoded texts to console (useful if TaskManager just calls this)
                if data_list:
                    print("[Vision] Decoded:", " | ".join(data_list))

        finally:
            cam.release()
            cv2.destroyAllWindows()
