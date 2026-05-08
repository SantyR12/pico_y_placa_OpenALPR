# Diseño: Sistema de Detección de Placas y Pico y Placa — Pasto, Colombia

**Fecha:** 2026-05-08  
**Estado:** Aprobado  
**Ciudad:** San Juan de Pasto, Nariño, Colombia

---

## 1. Resumen del Proyecto

Sistema de escritorio en Python que detecta placas vehiculares desde webcam, video o imagen estática, verifica si el vehículo tiene restricción de circulación según las reglas de Pico y Placa de Pasto, y ofrece un asistente conversacional basado en Gemini que responde preguntas relacionadas con el sistema.

---

## 2. Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Detección y OCR de placas | OpenALPR (Python bindings del repo clonado) |
| Fallback OCR | EasyOCR + OpenCV |
| Captura de video/imagen | OpenCV (`cv2`) |
| Interfaz gráfica | Tkinter |
| Asistente conversacional | Google Gemini Flash API (`google-generativeai`) |
| Festivos Colombia | Lista hardcodeada 2025–2026 |
| Lenguaje | Python 3.10+ |

---

## 3. Arquitectura General

```
[Webcam / Imagen / Video]
        ↓ (OpenCV captura frame)
  detector.py  ←── OpenALPR bindings (repo) → fallback EasyOCR
        ↓texto placa (ej: "EBM187")
  pico_placa.py  →  ✅ PUEDE CIRCULAR / ❌ RESTRICCIÓN ACTIVA
        ↓resultado
     gui.py  ←── muestra frame + resultado
        ↓
  [Panel Chat] ↔ assistant.py ↔ Gemini Flash API
```

---

## 4. Estructura de Archivos

```
C:\Pico y placa\
├── openalpr\                        # Repo clonado (no modificar)
│   ├── src\bindings\python\openalpr\openalpr.py
│   └── runtime_data\
└── pico_y_placa\                    # Código del proyecto
    ├── main.py                      # Entry point
    ├── gui.py                       # Tkinter app (3 paneles)
    ├── detector.py                  # OpenALPR + fallback EasyOCR
    ├── pico_placa.py                # Reglas de restricción Pasto
    ├── assistant.py                 # Gemini API chat
    ├── holidays.py                  # Festivos Colombia 2025–2026
    └── requirements.txt
```

---

## 5. Módulo `detector.py`

Intenta usar OpenALPR primero; si el DLL no está disponible, cae a EasyOCR.

```python
# Interfaz pública
def detectar_placa(frame: np.ndarray) -> dict:
    """
    Recibe un frame de OpenCV.
    Retorna: {
        "placa": "EBM187",        # texto reconocido
        "confianza": 88.9,        # porcentaje
        "bbox": (x, y, w, h),    # región de la placa en el frame
        "motor": "openalpr"       # o "easyocr"
    }
    Retorna None si no se detecta placa.
    """
```

**OpenALPR** se inicializa con:
- `country = "us"` (mejor soporte de caracteres alfanuméricos)
- `config` = `openalpr/config/openalpr.conf.defaults`
- `runtime_data` = `openalpr/runtime_data/`

---

## 6. Módulo `pico_placa.py`

### Reglas de Pasto

- **Horario:** 7:30 AM – 7:00 PM
- **Días hábiles:** Lunes a Viernes (excluye sábados, domingos y festivos)
- **Criterio:** Último dígito de la placa (ej. `EBM-187` → dígito `7`)
- **Pares:** `0-1`, `2-3`, `4-5`, `6-7`, `8-9`

### Rotación Semanal

Los pares rotan cada semana. Fecha de referencia: **Lunes 4 de mayo 2026 → dígito base = 8**.

| Semana | Lun | Mar | Mié | Jue | Vie |
|--------|-----|-----|-----|-----|-----|
| May 4  | 8-9 | 0-1 | 2-3 | 4-5 | 6-7 |
| May 11 | 0-1 | 2-3 | 4-5 | 6-7 | 8-9 |
| May 18 | 2-3 | 4-5 | 6-7 | 8-9 | 0-1 |
| May 25 | 4-5 | 6-7 | 8-9 | 0-1 | 2-3 |
| Jun 1  | 6-7 | 8-9 | 0-1 | 2-3 | 4-5 |

Ciclo completo: **5 semanas**. Cálculo:

```python
REFERENCIA = date(2026, 5, 4)   # Lunes, dígito base 8
BASE_DIGITO = 8

def obtener_par_restringido(fecha: date) -> list[int]:
    lunes = fecha - timedelta(days=fecha.weekday())
    semanas = (lunes - REFERENCIA).days // 7
    digito_lunes = (BASE_DIGITO + semanas * 2) % 10
    dia_offset = fecha.weekday()            # lunes=0, viernes=4
    digito = (digito_lunes + dia_offset * 2) % 10
    return [digito, digito + 1]
```

### Interfaz pública

```python
def verificar(placa: str, fecha_hora: datetime) -> dict:
    """
    Retorna: {
        "restringido": bool,
        "motivo": str,          # "RESTRICCIÓN ACTIVA" / "PUEDE CIRCULAR"
        "digito": int,          # último dígito de la placa
        "par_hoy": [int, int],  # par restringido hoy
        "es_festivo": bool,
        "en_horario": bool
    }
    """
```

---

## 7. Módulo `holidays.py`

Lista hardcodeada de festivos oficiales de Colombia 2025–2026 (Ley Emiliani incluida). No depende de API externa.

```python
FESTIVOS = [
    date(2025, 1, 1),   # Año Nuevo
    date(2025, 1, 6),   # Reyes Magos
    # ... todos los festivos 2025–2026
]
```

---

## 8. Módulo `assistant.py`

**Modelo:** `gemini-1.5-flash` (gratuito, rápido)

**System prompt:**
```
Eres un asistente experto en el sistema de Pico y Placa de la ciudad 
de Pasto, Colombia. Solo responde preguntas relacionadas con 
restricciones vehiculares, horarios, días hábiles y festivos de Pasto.
Si el usuario pregunta algo que no tenga relación con el tránsito o 
pico y placa de Pasto, responde amablemente que solo puedes ayudar 
con ese tema.
```

**Contexto dinámico** inyectado con cada mensaje:
```
Hoy es {día}, {fecha}. El par restringido hoy es {X-Y} de 7:30am a 
7:00pm. {'Es festivo.' if festivo else 'No es festivo.'}
```

**Interfaz pública:**
```python
def preguntar(mensaje: str, contexto_fecha: dict) -> str:
    """Retorna la respuesta de Gemini como string."""
```

---

## 9. Módulo `gui.py`

### Layout

```
┌─────────────────────────────────────────────────────────┐
│              Pico y Placa — Pasto                       │
├────────────────────────┬────────────────────────────────┤
│                        │  PLACA DETECTADA               │
│   [VIDEO / IMAGEN]     │  ┌──────────────┐              │
│                        │  │  EBM - 187   │              │
│   Frame con placa      │  └──────────────┘              │
│   resaltada en verde   │                                │
│   o rojo               │  ❌ RESTRICCIÓN ACTIVA         │
│                        │  Dígito: 7 | Par: 6-7          │
│                        │  Hoy: Viernes 8 mayo           │
│                        │  Horario: 7:30am - 7:00pm      │
├────────────────────────┴────────────────────────────────┤
│       [Webcam]    [Imagen]    [Video]                   │
├─────────────────────────────────────────────────────────┤
│  Asistente Pico y Placa                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │  [historial de chat]                            │   │
│  └─────────────────────────────────────────────────┘   │
│  [Escribe tu pregunta...              ] [Enviar]        │
└─────────────────────────────────────────────────────────┘
```

### Comportamiento
- Placa resaltada en **verde** si puede circular, **rojo** si está restringida
- Panel de resultado actualiza en tiempo real durante webcam/video
- Chat disponible en todo momento, independiente de la detección
- Botón Webcam arranca `cv2.VideoCapture(0)`
- Botón Imagen abre `filedialog.askopenfilename()`
- Botón Video abre `filedialog.askopenfilename()` con filtro de video

---

## 10. `requirements.txt`

```
opencv-python
openalpr
easyocr
google-generativeai
pillow
```

---

## 11. Flujo de Datos Completo

```
1. Usuario selecciona fuente (webcam / imagen / video)
2. OpenCV captura frame como numpy array
3. detector.py procesa el frame:
   a. Intenta OpenALPR → si falla, usa EasyOCR
   b. Retorna placa + bbox + confianza
4. pico_placa.py recibe el texto de la placa:
   a. Extrae último dígito
   b. Obtiene par restringido para fecha/hora actual
   c. Verifica día hábil y horario
   d. Retorna resultado con motivo
5. gui.py:
   a. Dibuja bbox sobre el frame (verde/rojo)
   b. Muestra texto de placa y resultado en panel derecho
6. Usuario puede escribir en el chat en cualquier momento:
   a. assistant.py envía mensaje + contexto a Gemini
   b. Respuesta se muestra en historial del chat
```

---

## 12. Decisiones de Diseño

| Decisión | Razón |
|---|---|
| OpenALPR como motor principal | El repo clonado ya provee los bindings Python |
| EasyOCR como fallback | Instalación pure-Python en Windows sin compilar C++ |
| Tkinter para GUI | Incluido en Python stdlib, sin dependencias extra |
| Gemini Flash | Gratuito, rápido, API key fácil de obtener |
| Festivos hardcodeados | Sin dependencia de API externa, más confiable |
| Ciclo de 5 semanas calculado | Basado en referencia real confirmada (Lunes 4 mayo 2026 = 8-9) |
