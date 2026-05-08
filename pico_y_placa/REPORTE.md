# Reporte de Código Generado — Sistema Pico y Placa Pasto

**Fecha de generación:** 2026-05-08  
**Proyecto:** Detección de Placas Vehiculares y Clasificación de Pico y Placa  
**Ciudad:** San Juan de Pasto, Nariño, Colombia

---

## Resumen

Sistema de escritorio en Python que detecta placas vehiculares en tiempo real
(webcam, video o imagen estática), verifica si el vehículo tiene restricción
de Pico y Placa según las reglas de Pasto, y ofrece un asistente conversacional
con Gemini para responder preguntas sobre el tema.

---

## Archivos Generados

| Archivo | Líneas | Responsabilidad |
|---|---|---|
| `holidays.py` | ~60 | Festivos oficiales Colombia 2025–2026 |
| `pico_y_placa.py` | ~110 | Reglas de restricción + rotación semanal |
| `detector.py` | ~130 | OpenALPR + fallback EasyOCR |
| `assistant.py` | ~80 | Asistente Gemini Flash |
| `gui.py` | ~280 | Interfaz Tkinter (3 paneles) |
| `main.py` | ~15 | Entry point |
| `requirements.txt` | ~10 | Dependencias pip |

---

## Instrucciones de Instalación

### 1. Instalar dependencias

```bash
cd "C:\Pico y placa\pico_y_placa"
pip install -r requirements.txt
```

> **Nota sobre OpenALPR:** Si `pip install openalpr` falla (error de DLL),
> el sistema automáticamente usa **EasyOCR** como motor alternativo.
> EasyOCR no requiere ningún binario externo.

### 2. Configurar API Key de Gemini

1. Ir a https://aistudio.google.com/app/apikey
2. Crear una API Key gratuita
3. Abrir `assistant.py` y reemplazar:

```python
GEMINI_API_KEY = "TU_API_KEY_AQUI"
# por ejemplo:
GEMINI_API_KEY = "AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXX"
```

### 3. Ejecutar

```bash
python main.py
```

---

## Descripción de Módulos

### `holidays.py`
Lista de festivos oficiales de Colombia para 2025 y 2026, basada en la
**Ley Emiliani (Ley 51 de 1983)**. Los festivos que no caen en lunes se
trasladan al siguiente lunes. Se exporta como un `set` de objetos `date`
para búsqueda O(1).

---

### `pico_y_placa.py`

**Reglas de Pasto:**
- Horario: 7:30 AM – 7:00 PM
- Días: Lunes a Viernes (sin sábados, domingos ni festivos)
- Criterio: **último dígito** de la placa
- Pares: 0-1 / 2-3 / 4-5 / 6-7 / 8-9

**Rotación semanal:**

Los pares rotan cada semana. Dentro de cada semana, cada día avanza 2
dígitos respecto al día anterior. Semana a semana, el lunes también avanza 2.

Fecha de referencia: **Lunes 4 de mayo 2026 → dígito base = 8**

| Semana | Lun | Mar | Mié | Jue | Vie |
|--------|-----|-----|-----|-----|-----|
| 4 mayo | 8-9 | 0-1 | 2-3 | 4-5 | 6-7 |
| 11 mayo| 0-1 | 2-3 | 4-5 | 6-7 | 8-9 |
| 18 mayo| 2-3 | 4-5 | 6-7 | 8-9 | 0-1 |
| 25 mayo| 4-5 | 6-7 | 8-9 | 0-1 | 2-3 |
| 1 jun  | 6-7 | 8-9 | 0-1 | 2-3 | 4-5 |

Ciclo completo: **5 semanas**.

**Fórmula:**
```python
semanas      = (lunes_semana - referencia).days // 7
digito_lunes = (8 + semanas * 2) % 10
digito_dia   = (digito_lunes + dia_semana * 2) % 10
par          = [digito_dia, (digito_dia + 1) % 10]
```

**Función principal:**
```python
verificar(placa: str, fecha_hora: datetime) -> dict
# Retorna: restringido, motivo, digito, par_hoy, es_festivo, en_horario
```

---

### `detector.py`

Detecta placas vehiculares en frames de OpenCV usando dos motores:

**Motor 1 — OpenALPR (principal)**
- Usa los Python bindings del repo clonado (`openalpr/src/bindings/python/`)
- Requiere `libopenalprpy.dll` instalada en el sistema
- Si está disponible, se inicializa automáticamente al importar el módulo
- Retorna placa, confianza y bounding box

**Motor 2 — EasyOCR (fallback)**
- Se activa si OpenALPR no está disponible
- Pure Python, instalable con `pip install easyocr`
- Filtra resultados por patrón colombiano `[A-Z]{3}\d{3}`
- El reader se carga lazy (solo cuando se necesita)

**Función pública:**
```python
detectar_placa(frame: np.ndarray) -> dict | None
# Retorna: placa, confianza, bbox, motor
```

---

### `assistant.py`

Asistente conversacional usando **Google Gemini 1.5 Flash**.

- System prompt especializado en Pico y Placa de Pasto
- Rechaza preguntas fuera del dominio con mensaje amable
- Contexto dinámico inyectado: día, fecha, par restringido, festivo
- Mantiene historial de conversación en la sesión
- Función `reiniciar_chat()` para limpiar el historial

**Función pública:**
```python
preguntar(mensaje: str, contexto: dict) -> str
```

---

### `gui.py`

Interfaz Tkinter con tres zonas:

**Panel izquierdo — Video (640×400)**
- Muestra el frame actual de la fuente seleccionada
- Dibuja bounding box sobre la placa detectada
  - 🟢 Verde: puede circular
  - 🔴 Rojo: restricción activa
- Texto de la placa superpuesto sobre el bbox

**Panel derecho — Resultado**
- Placa detectada en fuente grande
- Estado: ✅ PUEDE CIRCULAR / ❌ RESTRICCIÓN ACTIVA
- Detalles: dígito, par, día, horario, motor OCR, confianza
- Par restringido del día (se actualiza cada segundo)

**Panel inferior — Chat**
- ScrolledText con historial de conversación
- Campo de entrada con soporte Enter para enviar
- Respuestas de Gemini en hilo separado (no bloquea la UI)
- Botón "Nuevo chat" para reiniciar la sesión

**Controles:**
- 📷 Webcam: `cv2.VideoCapture(0)`
- 🖼 Imagen: `filedialog` → procesa un solo frame
- 🎬 Video: `filedialog` → reproduce frame a frame
- ⏹ Detener: libera la fuente actual

---

### `main.py`

Entry point. Crea la ventana Tkinter, instancia `PicoPlacaApp` y arranca
el loop de eventos. Conecta el evento de cierre de ventana con `app.cerrar()`
para liberar recursos de OpenCV correctamente.

---

## Flujo de Datos

```
[Fuente: Webcam / Imagen / Video]
          ↓  (OpenCV captura frame)
    detector.py
    ├── OpenALPR.recognize_ndarray(frame)   ← motor principal
    └── EasyOCR.readtext(frame)             ← fallback
          ↓  texto placa ej: "EBM187"
    pico_y_placa.py → verificar()
    ├── ¿fin de semana?   → sin restricción
    ├── ¿festivo?         → sin restricción
    ├── ¿fuera horario?   → sin restricción
    └── dígito in par_hoy → ✅ / ❌
          ↓  resultado
    gui.py → bbox + color + panel resultado
          ↓
    [Chat] → assistant.py → Gemini Flash API → respuesta
```

---

## Tecnologías Utilizadas

| Tecnología | Versión recomendada | Uso |
|---|---|---|
| Python | 3.10+ | Lenguaje base |
| OpenCV | 4.x | Captura video/imagen |
| OpenALPR | 2.3.x | Detección y OCR de placas |
| EasyOCR | 1.7+ | OCR fallback pure Python |
| Google Generative AI | 0.5+ | Asistente Gemini |
| Pillow | 10.x | Renderizado en Tkinter |
| Tkinter | stdlib | Interfaz gráfica |

---

## Posibles Errores y Soluciones

| Error | Causa | Solución |
|---|---|---|
| `OSError: Unable to locate the OpenALPR library` | DLL no instalada | Normal — el sistema usa EasyOCR automáticamente |
| `GEMINI_API_KEY inválida` | Key no configurada | Editar `assistant.py` con la key real |
| `No module named 'easyocr'` | No instalado | `pip install easyocr` |
| `No se detectó ninguna webcam` | Cámara no disponible | Usar fuente Imagen o Video |
| EasyOCR tarda al iniciar | Descarga del modelo | Solo ocurre la primera vez |
