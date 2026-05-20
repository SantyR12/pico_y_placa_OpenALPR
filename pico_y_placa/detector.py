"""
Módulo de detección y reconocimiento de placas vehiculares.

Motor principal : OpenALPR
  - Linux  : librería del sistema (/usr/share/openalpr/) instalada via AUR
  - Windows : binarios bundled en openalpr_bin/openalpr_64/
Motor fallback  : EasyOCR + OpenCV (pure Python, sin dependencias nativas)

Al importar este módulo se intenta inicializar OpenALPR automáticamente.
Si no está disponible en el sistema, se usa EasyOCR sin configuración adicional.
"""

import os
import sys
import re
import platform
import cv2
import numpy as np

# ── Paths base ───────────────────────────────────────────────────────────────
_BASE          = os.path.dirname(os.path.abspath(__file__))
_REPO_BINDINGS = os.path.join(_BASE, '..', 'openalpr', 'src', 'bindings', 'python')

# Agregar bindings del repo al path de Python (compatibles con Linux y Windows)
sys.path.insert(0, os.path.abspath(_REPO_BINDINGS))

# ── Rutas de OpenALPR según sistema operativo ────────────────────────────────
_IS_WINDOWS = platform.system().lower() == "windows"

if _IS_WINDOWS:
    # Windows: usar binarios bundled en el proyecto
    _BIN_DIR = os.path.abspath(os.path.join(_BASE, '..', 'openalpr_bin', 'openalpr_64'))
    _CONFIG  = os.path.join(_BIN_DIR, 'openalpr.conf')
    _RUNTIME = os.path.join(_BIN_DIR, 'runtime_data')

    # Python 3.8+ ignora PATH para DLLs — hay que usar os.add_dll_directory()
    os.environ["PATH"] = _BIN_DIR + os.pathsep + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(_BIN_DIR)

    import ctypes
    for _dll in ["liblept170.dll", "opencv_world300.dll", "openalpr.dll", "libopenalprpy.dll"]:
        _dll_path = os.path.join(_BIN_DIR, _dll)
        if os.path.exists(_dll_path):
            try:
                ctypes.WinDLL(_dll_path)
            except Exception as _e:
                print(f"[detector] Advertencia al precargar {_dll}: {_e}")
else:
    # Linux: usar instalación del sistema (via AUR: yay -S openalpr)
    _CONFIG  = "/etc/openalpr/openalpr.conf"
    _RUNTIME = "/usr/share/openalpr/runtime_data"

# ── Inicialización de OpenALPR ────────────────────────────────────────────────
_OPENALPR_OK   = False
_alpr_instance = None


def _init_openalpr():
    global _OPENALPR_OK, _alpr_instance
    try:
        from openalpr import Alpr

        # Parche: bug en el repo — __del__ falla si __init__ no completó.
        # Alpr.__init__ lanza OSError antes de asignar self.loaded=True;
        # el GC llama __del__ y explota con AttributeError.
        _orig_del = Alpr.__del__
        def _safe_del(self):
            try:
                _orig_del(self)
            except AttributeError:
                pass
        Alpr.__del__ = _safe_del

        if not os.path.exists(_CONFIG) or not os.path.exists(_RUNTIME):
            raise FileNotFoundError(
                f"OpenALPR no instalado. Config: {_CONFIG} | Runtime: {_RUNTIME}\n"
                f"  Linux  → yay -S openalpr\n"
                f"  Windows → ejecutar vc_redist.x64.exe del directorio openalpr_bin"
            )

        _alpr_instance = Alpr("us", _CONFIG, _RUNTIME)
        if _alpr_instance.is_loaded():
            _alpr_instance.set_top_n(5)
            _OPENALPR_OK = True
            so = "Windows (bundled)" if _IS_WINDOWS else "Linux (sistema)"
            print(f"[detector] Motor activo: OpenALPR — {so}")
        else:
            print("[detector] OpenALPR cargó pero no está listo, usando EasyOCR")
    except Exception as e:
        print(f"[detector] OpenALPR no disponible ({e})\n"
              f"[detector] Motor activo: EasyOCR (fallback)")
        _OPENALPR_OK = False


_init_openalpr()


# ── Detección de región de placa ──────────────────────────────────────────────
# Tier 1 (siempre disponible): Haar cascade bundled con OpenCV
# Tier 2 (opcional):           YOLOv8 — colocar modelo en models/plate_detector.pt

_YOLO_OK      = False
_yolo_model   = None
_CASCADE_OK   = False
_cascade      = None

_YOLO_LOCAL = os.path.abspath(
    os.path.join(_BASE, '..', 'models', 'plate_detector.pt')
)


def _init_region_detector():
    global _YOLO_OK, _yolo_model, _CASCADE_OK, _cascade

    # ── Tier 2: YOLO (solo si existe el .pt local) ────────────────────────────
    if os.path.exists(_YOLO_LOCAL):
        try:
            from ultralytics import YOLO
            _yolo_model = YOLO(_YOLO_LOCAL)
            _YOLO_OK = True
            print("[detector] YOLOv8 activo — predetección de placas habilitada")
        except Exception as e:
            print(f"[detector] YOLOv8 falló ({e})")

    # ── Tier 1: Haar cascade (bundled con OpenCV, sin descarga) ───────────────
    if not _YOLO_OK:
        try:
            cascade_path = cv2.data.haarcascades + "haarcascade_russian_plate_number.xml"
            _cascade = cv2.CascadeClassifier(cascade_path)
            if not _cascade.empty():
                _CASCADE_OK = True
                print("[detector] Cascade de placas activo — predetección habilitada")
        except Exception as e:
            print(f"[detector] Cascade no disponible ({e})")

    if not _YOLO_OK and not _CASCADE_OK:
        print("[detector] Sin predetección — EasyOCR usará frame completo")


_init_region_detector()


def _detectar_region(frame: np.ndarray) -> tuple | None:
    """
    Localiza la región de la placa.
    Usa YOLOv8 si está disponible (models/plate_detector.pt), si no usa
    el Haar cascade bundled con OpenCV.
    Retorna (x, y, w, h) o None si no detecta nada.
    """
    # ── Tier 2: YOLO ──────────────────────────────────────────────────────────
    if _YOLO_OK:
        try:
            resultados = _yolo_model(frame, verbose=False)[0]
            if len(resultados.boxes):
                mejor = resultados.boxes[resultados.boxes.conf.argmax()]
                x1, y1, x2, y2 = map(int, mejor.xyxy[0])
                return (x1, y1, x2 - x1, y2 - y1)
        except Exception as e:
            print(f"[detector] Error YOLO: {e}")

    # ── Tier 1: Haar cascade ──────────────────────────────────────────────────
    if _CASCADE_OK:
        try:
            gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            placas = _cascade.detectMultiScale(
                gris, scaleFactor=1.1, minNeighbors=4,
                minSize=(60, 20), maxSize=(400, 120),
            )
            if len(placas):
                # Tomar la detección más ancha (más probable que sea la placa)
                idx = placas[:, 2].argmax()
                return tuple(placas[idx])
        except Exception as e:
            print(f"[detector] Error cascade: {e}")

    return None


def _preprocesar(region: np.ndarray) -> np.ndarray:
    """
    Normaliza y mejora una región de placa para el OCR:
    escala fija → escala de grises → CLAHE → filtro bilateral → unsharp mask.
    """
    h, w = region.shape[:2]
    if h == 0 or w == 0:
        return region
    nuevo_w = max(1, int(w * (80 / h)))
    region  = cv2.resize(region, (nuevo_w, 80), interpolation=cv2.INTER_LANCZOS4)
    gris    = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    clahe   = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
    gris    = clahe.apply(gris)
    gris    = cv2.bilateralFilter(gris, 9, 75, 75)
    blur    = cv2.GaussianBlur(gris, (0, 0), 3)
    gris    = cv2.addWeighted(gris, 1.5, blur, -0.5, 0)
    return gris


# ── Utilidades ────────────────────────────────────────────────────────────────
def _limpiar_placa(texto: str) -> str:
    """
    Normaliza el texto OCR y extrae el patrón de placa colombiana (AAA000).
    Si no coincide exactamente, retorna el texto limpio sin guiones ni espacios.
    """
    texto = texto.upper().replace(" ", "").replace("-", "").replace(".", "")
    match = re.search(r'[A-Z]{3}\d{3}', texto)
    return match.group() if match else texto


# ── Motor OpenALPR ────────────────────────────────────────────────────────────
def _detectar_openalpr(frame: np.ndarray) -> dict | None:
    try:
        # recognize_array recibe bytes JPEG — compatible con DLL v2.3.0
        success, buffer = cv2.imencode('.jpg', frame)
        if not success:
            return None
        jpeg_bytes = buffer.tobytes()

        results = _alpr_instance.recognize_array(jpeg_bytes)
        if not results.get('results'):
            return None

        mejor     = results['results'][0]
        candidato = mejor['candidates'][0]
        coords    = mejor['coordinates']

        xs   = [c['x'] for c in coords]
        ys   = [c['y'] for c in coords]
        bbox = (int(min(xs)), int(min(ys)),
                int(max(xs) - min(xs)), int(max(ys) - min(ys)))

        return {
            "placa"    : _limpiar_placa(candidato['plate']),
            "confianza": round(candidato['confidence'], 1),
            "bbox"     : bbox,
            "motor"    : "OpenALPR",
        }
    except Exception as e:
        print(f"[detector] Error OpenALPR: {e}")
        return None


# ── Motor EasyOCR (fallback) ──────────────────────────────────────────────────
_easyocr_reader = None


def _get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        import easyocr
        print("[detector] Cargando modelo EasyOCR (puede tardar unos segundos)…")
        _easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        print("[detector] EasyOCR listo.")
    return _easyocr_reader


def _detectar_easyocr(frame: np.ndarray) -> dict | None:
    try:
        reader = _get_easyocr_reader()

        # Preprocesamiento sobre frame completo: mejora contraste y nitidez
        # sin recortar, para no depender de un detector de región impreciso
        gris  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gris  = clahe.apply(gris)
        blur  = cv2.GaussianBlur(gris, (0, 0), 3)
        gris  = cv2.addWeighted(gris, 1.5, blur, -0.5, 0)

        resultados = reader.readtext(gris)

        for (bbox_pts, texto, confianza) in resultados:
            limpio = _limpiar_placa(texto)
            if re.match(r'^[A-Z]{3}\d{3}$', limpio):
                xs   = [int(p[0]) for p in bbox_pts]
                ys   = [int(p[1]) for p in bbox_pts]
                bbox = (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
                return {
                    "placa"    : limpio,
                    "confianza": round(confianza * 100, 1),
                    "bbox"     : bbox,
                    "motor"    : "EasyOCR",
                }
    except Exception as e:
        print(f"[detector] Error EasyOCR: {e}")
    return None


# ── API pública ───────────────────────────────────────────────────────────────
def detectar_placa(frame: np.ndarray) -> dict | None:
    """
    Detecta y reconoce una placa vehicular en un frame de OpenCV.

    Parámetros:
        frame -- numpy array BGR (salida de cv2.VideoCapture o cv2.imread)

    Retorna dict con:
        placa      str    -- texto de la placa, ej: 'EBM187'
        confianza  float  -- porcentaje de confianza (0-100)
        bbox       tuple  -- (x, y, w, h) región de la placa en el frame
        motor      str    -- 'OpenALPR' o 'EasyOCR'

    Retorna None si no se detecta ninguna placa.
    """
    if _OPENALPR_OK:
        resultado = _detectar_openalpr(frame)
        if resultado:
            return resultado
    return _detectar_easyocr(frame)
