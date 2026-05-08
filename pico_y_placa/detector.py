"""
Módulo de detección y reconocimiento de placas vehiculares.

Motor principal : OpenALPR (bindings Python del repo clonado)
Motor fallback  : EasyOCR + OpenCV (pure Python, sin DLL)

Al importar este módulo se intenta inicializar OpenALPR automáticamente.
Si la DLL no está disponible, se usa EasyOCR sin configuración adicional.
"""

import os
import sys
import re
import cv2
import numpy as np

# ── Paths base ───────────────────────────────────────────────────────────────
_BASE          = os.path.dirname(os.path.abspath(__file__))
_REPO_BINDINGS = os.path.join(_BASE, '..', 'openalpr', 'src', 'bindings', 'python')
_BIN_DIR       = os.path.join(_BASE, '..', 'openalpr_bin', 'openalpr_64')

# Agregar bindings del repo al path de Python
sys.path.insert(0, os.path.abspath(_REPO_BINDINGS))

# ── Registrar carpeta de DLLs en Windows ────────────────────────────────────
# Python 3.8+ ignora PATH para DLLs — hay que usar os.add_dll_directory()
_BIN_DIR_ABS = os.path.abspath(_BIN_DIR)
os.environ["PATH"] = _BIN_DIR_ABS + os.pathsep + os.environ.get("PATH", "")
if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(_BIN_DIR_ABS)

# Pre-cargar dependencias en orden para que ctypes las resuelva
import ctypes
for _dll in ["liblept170.dll", "opencv_world300.dll", "openalpr.dll", "libopenalprpy.dll"]:
    _dll_path = os.path.join(_BIN_DIR_ABS, _dll)
    if os.path.exists(_dll_path):
        try:
            ctypes.WinDLL(_dll_path)
        except Exception as _e:
            print(f"[detector] Advertencia al precargar {_dll}: {_e}")

# ── Inicialización de OpenALPR ────────────────────────────────────────────────
_OPENALPR_OK   = False
_alpr_instance = None


def _init_openalpr():
    global _OPENALPR_OK, _alpr_instance
    try:
        from openalpr import Alpr

        # ── Parche: bug en el repo — __del__ falla si __init__ no completó ──
        # Cuando la DLL no existe, Alpr.__init__ lanza OSError antes de
        # asignar self.loaded=True; el GC llama __del__ y explota.
        _orig_del = Alpr.__del__
        def _safe_del(self):
            try:
                _orig_del(self)
            except AttributeError:
                pass
        Alpr.__del__ = _safe_del
        # ────────────────────────────────────────────────────────────────────

        # Usar config y runtime_data del ZIP (tienen los modelos OCR compilados)
        _config  = os.path.abspath(os.path.join(_BIN_DIR, 'openalpr.conf'))
        _runtime = os.path.abspath(os.path.join(_BIN_DIR, 'runtime_data'))

        _alpr_instance = Alpr("us", _config, _runtime)
        if _alpr_instance.is_loaded():
            _alpr_instance.set_top_n(5)
            _OPENALPR_OK = True
            print("[detector] Motor activo: OpenALPR")
        else:
            print("[detector] OpenALPR cargó pero no está listo, usando EasyOCR")
    except Exception as e:
        print(f"[detector] OpenALPR no disponible ({e})\n"
              f"[detector] Motor activo: EasyOCR (fallback)")
        _OPENALPR_OK = False


_init_openalpr()


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
        reader     = _get_easyocr_reader()
        gris       = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        resultados = reader.readtext(gris)

        for (bbox_pts, texto, confianza) in resultados:
            limpio = _limpiar_placa(texto)
            # Aceptar solo patrón colombiano exacto
            if re.match(r'^[A-Z]{3}\d{3}$', limpio):
                xs   = [int(p[0]) for p in bbox_pts]
                ys   = [int(p[1]) for p in bbox_pts]
                bbox = (min(xs), min(ys),
                        max(xs) - min(xs), max(ys) - min(ys))
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
        return _detectar_openalpr(frame)
    return _detectar_easyocr(frame)
