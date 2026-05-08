# Guía de Instalación — Sistema Pico y Placa Pasto

## Requisitos previos

- **Python 3.10 o superior** → https://www.python.org/downloads/
  - Durante la instalación activa la casilla **"Add Python to PATH"**
- **Git** → https://git-scm.com/downloads

---

## Paso 1 — Clonar el repositorio

Abre una terminal (CMD o PowerShell) y ejecuta:

```bash
git clone <URL_DEL_REPOSITORIO>
cd <nombre-de-la-carpeta>
```

---

## Paso 2 — Descargar OpenALPR para Windows

1. Descarga el archivo ZIP desde este enlace:

```
https://github.com/openalpr/openalpr/releases/download/v2.3.0/openalpr-2.3.0-win-64bit.zip
```

2. Extrae el ZIP dentro de la carpeta del proyecto de forma que quede así:

```
pico-y-placa/
├── openalpr/               ← repo clonado (ya está)
├── openalpr_bin/
│   └── openalpr_64/        ← contenido del ZIP aquí
│       ├── libopenalprpy.dll
│       ├── openalpr.dll
│       ├── openalpr.conf
│       ├── runtime_data/
│       └── ...
├── pico_y_placa/
└── ...
```

3. Entra a la carpeta `openalpr_bin\openalpr_64\` y **renombra** el archivo:

```
openalprpy.dll  →  libopenalprpy.dll
```

> Haz clic derecho → Cambiar nombre

---

## Paso 3 — Instalar Visual C++ Runtime

Dentro de `openalpr_bin\openalpr_64\` haz **doble clic** en:

```
vc_redist.x64.exe
```

Dale a **Instalar**. Si aparece el mensaje "ya está instalada otra versión", cierra y continúa.

---

## Paso 4 — Instalar dependencias Python

Desde la terminal, dentro de la carpeta `pico_y_placa\`:

```bash
cd pico_y_placa
pip install -r requirements.txt
```

> La primera vez puede tardar varios minutos porque descarga los modelos de EasyOCR (~100 MB).

---

## Paso 5 — Configurar API Key de Gemini

1. Ve a https://aistudio.google.com/app/apikey
2. Crea una cuenta gratuita y genera una API Key
3. Abre el archivo `pico_y_placa/assistant.py` con cualquier editor de texto
4. Reemplaza esta línea:

```python
GEMINI_API_KEY = "TU_API_KEY_AQUI"
```

Por tu key real, por ejemplo:

```python
GEMINI_API_KEY = "AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXX"
```

---

## Paso 6 — Ejecutar el sistema

```bash
python main.py
```

En la terminal deberías ver:

```
[detector] Motor activo: OpenALPR
```

Si ves `Motor activo: EasyOCR (fallback)`, revisa que el Paso 2 y 3 estén completos.

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

## Estructura de carpetas final

```
pico-y-placa/
├── openalpr/                  ← Repo OpenALPR (bindings Python)
│   ├── src/bindings/python/
│   └── runtime_data/
├── openalpr_bin/              ← Binarios Windows del ZIP
│   └── openalpr_64/
│       ├── libopenalprpy.dll
│       ├── openalpr.dll
│       ├── liblept170.dll
│       ├── opencv_world300.dll
│       ├── openalpr.conf
│       ├── runtime_data/
│       └── vc_redist.x64.exe
├── pico_y_placa/              ← Código del proyecto
│   ├── main.py
│   ├── gui.py
│   ├── detector.py
│   ├── pico_y_placa.py
│   ├── assistant.py
│   ├── holidays.py
│   └── requirements.txt
└── SETUP.md                   ← Esta guía
```

---

## Solución de problemas

| Problema | Solución |
|----------|----------|
| `Motor activo: EasyOCR` en lugar de OpenALPR | Verifica que `libopenalprpy.dll` esté en `openalpr_bin/openalpr_64/` |
| Error al instalar `openalpr` con pip | Normal, el sistema usa EasyOCR automáticamente |
| El chat no responde | Verifica tu API Key de Gemini en `assistant.py` |
| `No module named 'cv2'` | Ejecuta `pip install opencv-python` |
| `No se detectó ninguna webcam` | Usa el botón Imagen o Video en su lugar |
| EasyOCR tarda al iniciar | Solo ocurre la primera vez, está descargando el modelo |
