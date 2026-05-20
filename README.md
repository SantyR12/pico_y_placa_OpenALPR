# Pico y Placa — Pasto, Colombia

Sistema de escritorio que detecta placas vehiculares en tiempo real y determina automáticamente si un vehículo tiene restricción de circulación según las reglas de Pico y Placa vigentes en la ciudad de San Juan de Pasto, Nariño. Incluye un asistente conversacional con inteligencia artificial que responde preguntas sobre el sistema de restricción.

Proyecto final del curso de Inteligencia Artificial — Universidad.

---

## ¿Qué hace?

Cuando el sistema detecta una placa en la cámara o en una imagen, extrae el último dígito y lo compara con el par restringido para ese día según la rotación semanal de Pasto. El resultado aparece en pantalla en tiempo real: verde si el vehículo puede circular, rojo si tiene restricción activa. Si la placa está restringida, genera automáticamente un ticket de multa de muestra.

Además, en cualquier momento se puede abrir el chat para hacerle preguntas al asistente — cosas como "¿cuál es el horario?", "¿mañana hay restricción para placas terminadas en 5?" o "¿el primero de mayo hay pico y placa?". El asistente responde usando el contexto del día actual.

---

## Modelos de inteligencia artificial

El proyecto combina dos tipos distintos de modelos de IA:

**EasyOCR — Red neuronal CRNN**
Se encarga de leer el texto de la placa vehicular. Internamente usa una arquitectura CRNN (Convolutional Recurrent Neural Network): una red convolucional (CNN) extrae las características visuales de la imagen, y una red recurrente bidireccional (LSTM) interpreta esa información como una secuencia de caracteres. El entrenamiento usa CTC loss, lo que permite reconocer texto sin necesitar segmentar cada letra por separado.

**Llama 3.2 / Gemini 2.5 Flash — Transformer**
El asistente conversacional usa un modelo de lenguaje grande con arquitectura Transformer decoder-only. Funciona de forma autoregresiva: genera la respuesta token por token, prestando atención al historial completo de la conversación mediante mecanismos de self-attention. El motor principal es Llama 3.2 corriendo localmente con Ollama (sin internet ni API key). Si Ollama no está disponible, el sistema cae automáticamente a Gemini Flash como respaldo.

**OpenALPR** (solo Windows)
En Windows también está disponible OpenALPR, un motor especializado en reconocimiento de matrículas vehiculares que combina visión computacional clásica con OCR basado en Tesseract.

---

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Captura y procesamiento de imagen | OpenCV |
| OCR de placas | EasyOCR (CRNN) + OpenALPR (Windows) |
| Asistente conversacional | Ollama · llama3.2:3b (local) / Gemini 2.5 Flash (fallback) |
| Interfaz gráfica | Tkinter |
| Renderizado de frames | Pillow |
| Lenguaje | Python 3.10+ |

---

## Instalación

### Requisitos
- Python 3.10 o superior
- [Ollama](https://ollama.com) instalado en el sistema (para el asistente local)
- En Windows: ejecutar `openalpr_bin/openalpr_64/vc_redist.x64.exe` antes de correr el sistema

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/SantyR12/pico_y_placa_OpenALPR.git
cd pico_y_placa_OpenALPR

# 2. Instalar dependencias Python
cd pico_y_placa
pip install -r requirements.txt

# 3. Descargar el modelo de lenguaje local (solo primera vez)
ollama pull llama3.2:3b

# 4. Ejecutar
python main.py
```

> La primera vez que se usa EasyOCR descarga el modelo automáticamente (~100 MB). El sistema funciona sin internet después de eso.

---

## Uso

Al abrir la aplicación se tienen tres botones de fuente:

- **Webcam** — activa la cámara en tiempo real, detectando placas frame a frame
- **Imagen** — carga una foto desde el computador y procesa ese frame
- **Video** — carga un archivo de video y lo procesa completo

La placa detectada aparece resaltada en el video con un recuadro **verde** si puede circular o **rojo** si tiene restricción activa. En el panel derecho se muestra el número de placa, el estado, el último dígito, el par restringido del día y la confianza del OCR.

En la parte inferior hay tres pestañas: el chat con el asistente, el historial de detecciones con opción de exportar a CSV, y el registro de multas generadas.

---

## Reglas de Pico y Placa en Pasto

- **Horario:** 7:30 AM a 7:00 PM
- **Días:** lunes a viernes (sábados, domingos y festivos sin restricción)
- **Criterio:** último dígito de la placa
- **Rotación:** los pares (0-1, 2-3, 4-5, 6-7, 8-9) rotan cada semana en un ciclo de 5 semanas

| Semana | Lun | Mar | Mié | Jue | Vie |
|---|---|---|---|---|---|
| 4 mayo 2026 | 8-9 | 0-1 | 2-3 | 4-5 | 6-7 |
| 11 mayo | 0-1 | 2-3 | 4-5 | 6-7 | 8-9 |
| 18 mayo | 2-3 | 4-5 | 6-7 | 8-9 | 0-1 |
| 25 mayo | 4-5 | 6-7 | 8-9 | 0-1 | 2-3 |
| 1 junio | 6-7 | 8-9 | 0-1 | 2-3 | 4-5 |

---

## Estructura del proyecto

```
pico_y_placa_OpenALPR/
├── pico_y_placa/
│   ├── main.py           # Punto de entrada
│   ├── gui.py            # Interfaz Tkinter
│   ├── detector.py       # OCR de placas (EasyOCR + OpenALPR)
│   ├── pico_y_placa.py   # Lógica de restricción y rotación semanal
│   ├── assistant.py      # Asistente conversacional (Ollama / Gemini)
│   ├── holidays.py       # Festivos Colombia 2025–2026
│   ├── multa.py          # Generador de ticket de multa
│   └── requirements.txt
├── openalpr/             # Bindings Python de OpenALPR
├── openalpr_bin/         # Binarios Windows (DLLs)
├── analisis_tecnico_placas.ipynb    # Notebook explicativo con diagramas de arquitectura
└── SETUP.md              # Guía de instalación detallada
```

---

## Notebook de demostración

El archivo `analisis_tecnico_placas.ipynb` contiene una explicación completa del sistema con código ejecutable: diagramas de las arquitecturas de IA, comparación del pipeline de preprocesamiento de imagen, pruebas de los módulos de detección y verificación, y ejemplos del asistente conversacional. Es el punto de entrada recomendado para entender cómo funciona el proyecto por dentro.

```bash
jupyter notebook analisis_tecnico_placas.ipynb
```

---

## Solución de problemas

| Problema | Causa probable | Solución |
|---|---|---|
| `Motor activo: EasyOCR` en Windows | Falta el runtime de Visual C++ | Instalar `vc_redist.x64.exe` del paso de instalación |
| El chat no responde | Ollama no está corriendo | Ejecutar `ollama serve` en otra terminal |
| EasyOCR tarda al iniciar | Primera ejecución | Esperar, descarga el modelo (~100 MB) una sola vez |
| `No se detectó ninguna webcam` | Sin cámara disponible | Usar los botones Imagen o Video |
