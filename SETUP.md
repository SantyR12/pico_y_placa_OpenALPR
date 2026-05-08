# Guía de Instalación — Sistema Pico y Placa Pasto

**Repositorio:** https://github.com/SantyR12/pico_y_placa_OpenALPR

---

## Requisitos previos

- **Python 3.10 o superior** → https://www.python.org/downloads/
  - Durante la instalación activa la casilla **"Add Python to PATH"**
- **Git** → https://git-scm.com/downloads

---

## Paso 1 — Clonar el repositorio

Abre una terminal (CMD o PowerShell) y ejecuta:

```bash
git clone https://github.com/SantyR12/pico_y_placa_OpenALPR.git
cd pico_y_placa_OpenALPR
```

---

## Paso 2 — Instalar Visual C++ Runtime

Los binarios de OpenALPR ya vienen incluidos en el repo. Solo instala el runtime:

1. Abre la carpeta `openalpr_bin\openalpr_64\`
2. Haz **doble clic** en `vc_redist.x64.exe`
3. Dale a **Instalar**

> Si aparece "ya está instalada otra versión", cierra y continúa al siguiente paso.

---

## Paso 3 — Instalar dependencias Python

Desde la terminal, entra a la carpeta `pico_y_placa\`:

```bash
cd pico_y_placa
pip install -r requirements.txt
```

> La primera vez puede tardar varios minutos porque descarga los modelos de EasyOCR (~100 MB).

---

## Paso 4 — Configurar API Key de Gemini

1. Ve a https://aistudio.google.com/app/apikey
2. Crea una cuenta gratuita y genera una API Key
3. Abre el archivo `pico_y_placa/assistant.py` con cualquier editor de texto
4. Reemplaza esta línea:

```python
GEMINI_API_KEY = "TU_API_KEY_AQUI"
```

Por tu key real:

```python
GEMINI_API_KEY = "AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXX"
```

---

## Paso 5 — Ejecutar el sistema

```bash
python main.py
```

En la terminal deberías ver:

```
[detector] Motor activo: OpenALPR
```

> Si ves `Motor activo: EasyOCR (fallback)` revisa que el Paso 2 esté completo.

---

## Uso del sistema

| Botón | Función |
|-------|---------|
| 📷 Webcam | Activa la cámara en tiempo real |
| 🖼 Imagen | Carga una foto desde el computador |
| 🎬 Video | Carga un archivo de video |
| ⏹ Detener | Para la fuente actual |

- La placa detectada se resalta en **verde** si puede circular o **rojo** si tiene restricción
- El chat inferior responde preguntas sobre pico y placa de Pasto

---

## Estructura del proyecto

```
pico_y_placa_OpenALPR/
├── openalpr/                  ← Submódulo: bindings Python de OpenALPR
│   └── src/bindings/python/
├── openalpr_bin/              ← Binarios Windows (DLLs incluidas en el repo)
│   └── openalpr_64/
│       ├── libopenalprpy.dll
│       ├── openalpr.dll
│       ├── openalpr.conf
│       ├── runtime_data/
│       └── vc_redist.x64.exe
├── pico_y_placa/              ← Submódulo: código del proyecto
│   ├── main.py
│   ├── gui.py
│   ├── detector.py
│   ├── pico_y_placa.py
│   ├── assistant.py
│   ├── holidays.py
│   └── requirements.txt
└── SETUP.md
```

---

## Solución de problemas

| Problema | Solución |
|----------|----------|
| `Motor activo: EasyOCR` en lugar de OpenALPR | Instala `vc_redist.x64.exe` del Paso 2 |
| El chat no responde | Verifica tu API Key de Gemini en `assistant.py` |
| `No module named 'cv2'` | Ejecuta `pip install opencv-python` |
| `No se detectó ninguna webcam` | Usa el botón Imagen o Video en su lugar |
| EasyOCR tarda al iniciar | Solo ocurre la primera vez, descarga el modelo (~100 MB) |
