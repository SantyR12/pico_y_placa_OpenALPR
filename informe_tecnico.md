# Reporte de Proyecto Final
## Sistema de Detección de Placas Vehiculares y Clasificación de Pico y Placa — Pasto, Colombia

**Materia:** Inteligencia Artificial  
**Institución:** Universidad  
**Integrantes:** Santiago Ramos · Paulo [Apellido]  
**Fecha de entrega:** Mayo 2026  

---

## 1. Resumen

Este proyecto implementa un sistema de escritorio en Python que combina visión computacional e inteligencia artificial para detectar placas vehiculares en tiempo real y determinar si un vehículo tiene restricción de circulación según las reglas de Pico y Placa de la ciudad de Pasto, Nariño. El sistema utiliza una red neuronal de tipo CRNN para el reconocimiento óptico de caracteres en las placas, y un modelo de lenguaje basado en arquitectura Transformer para ofrecer un asistente conversacional especializado en las reglas de movilidad de la ciudad. Todo corre localmente sin depender de conexión a internet para las funciones principales.

---

## 2. Introducción

El Pico y Placa es una medida de restricción vehicular adoptada por varias ciudades colombianas para reducir la congestión en horas pico. En Pasto, la medida funciona de lunes a viernes en el horario de 7:30 AM a 7:00 PM, limitando la circulación de vehículos según el último dígito de su placa. Los dígitos están agrupados en pares (0-1, 2-3, 4-5, 6-7, 8-9) y cada par rota diariamente dentro de un ciclo semanal que se repite cada cinco semanas.

El problema que aborda este proyecto es doble. Por un lado, muchos conductores no recuerdan qué par corresponde a cada día, especialmente cuando el ciclo cambia semana a semana. Por otro, verificar manualmente si una placa está restringida implica conocer la tabla de rotación, el día de la semana y si es festivo o no. Este proceso, aunque sencillo, es propenso al error humano.

La solución propuesta automatiza completamente esa verificación: el sistema lee la placa con una cámara, calcula si hay restricción y muestra el resultado en segundos. Adicionalmente, un asistente de IA permite resolver dudas sobre las reglas sin tener que buscar en fuentes externas.

### 2.1 Objetivos

**Objetivo general**
Desarrollar un sistema funcional de visión computacional que detecte placas vehiculares y verifique en tiempo real si el vehículo tiene restricción de Pico y Placa en Pasto, integrando modelos de inteligencia artificial para la detección y para la asistencia conversacional.

**Objetivos específicos**
- Implementar un módulo de reconocimiento óptico de caracteres (OCR) sobre frames de video usando redes neuronales
- Codificar la lógica de restricción de Pico y Placa de Pasto con soporte para festivos y rotación semanal
- Integrar un modelo de lenguaje local (LLM) que responda preguntas sobre el sistema de pico y placa
- Construir una interfaz gráfica que integre todas las funciones de forma intuitiva

---

## 3. Marco Teórico

### 3.1 Visión computacional y OCR

El reconocimiento óptico de caracteres (OCR) es el proceso de extraer texto a partir de una imagen. En el contexto de placas vehiculares, el reto principal es que las condiciones de captura varían significativamente: distintos ángulos, niveles de luz, distancias y calidad de cámara. Los enfoques clásicos basados en segmentación de caracteres funcionan bien en condiciones controladas, pero fallan frecuentemente en escenarios reales.

Las redes neuronales profundas han demostrado ser mucho más robustas para esta tarea. En particular, la arquitectura CRNN combina lo mejor de dos tipos de redes: la capacidad de las CNN para procesar imágenes y la capacidad de las RNN para modelar secuencias de longitud variable.

### 3.2 Redes Neuronales Convolucionales (CNN)

Una red convolucional aplica filtros aprendibles sobre la imagen de entrada para detectar características visuales a distintos niveles de abstracción. Las primeras capas detectan bordes y texturas simples; las capas más profundas reconocen patrones complejos como formas de letras o dígitos. El resultado final es un mapa de características que condensa la información visual relevante de la imagen en una representación compacta.

### 3.3 Arquitectura CRNN — Red Neuronal Recurrente Convolucional

La CRNN (Convolutional Recurrent Neural Network) es la arquitectura que usa EasyOCR internamente. Su funcionamiento se divide en tres etapas:

**Etapa 1 — Extracción de características (CNN)**
La imagen de la placa pasa por una red convolucional (ResNet o VGG como backbone) que genera un mapa de características. Este mapa no es una clasificación de toda la imagen, sino una representación de la información visual organizada espacialmente.

**Etapa 2 — Modelado de secuencia (LSTM bidireccional)**
El mapa de características se divide en columnas y se interpreta como una secuencia de vectores de izquierda a derecha. Esa secuencia entra a una red LSTM bidireccional: una capa procesa la secuencia de izquierda a derecha y otra de derecha a izquierda. Los resultados se combinan, lo que permite al modelo entender el contexto de cada carácter en relación con sus vecinos en ambas direcciones.

**Etapa 3 — Decodificación con CTC**
La salida del LSTM es una distribución de probabilidad sobre los posibles caracteres para cada posición temporal. CTC (Connectionist Temporal Classification) es el algoritmo que convierte esa secuencia de distribuciones en el texto final, manejando automáticamente los caracteres repetidos y los espacios vacíos. La ventaja de CTC es que no necesita que cada carácter esté alineado con una posición exacta en la imagen durante el entrenamiento.

```
[Imagen de placa]
      │
      ▼
  CNN (backbone)
  extrae features
      │
      ▼
  Secuencia de vectores
  (columnas del feature map)
      │
      ▼
  LSTM Bidireccional
  → → → → → → →
  ← ← ← ← ← ← ←
      │
      ▼
  CTC Decoder
      │
      ▼
  "EBM187"
```

### 3.4 Transformers y Modelos de Lenguaje Grande (LLM)

El Transformer es una arquitectura de red neuronal propuesta en 2017 que transformó el campo del procesamiento de lenguaje natural. A diferencia de las redes recurrentes, no procesa las palabras en orden secuencial: en cambio, usa un mecanismo llamado **self-attention** que permite que cada token de la secuencia preste atención a todos los demás tokens simultáneamente. Esto lo hace mucho más eficiente de entrenar en paralelo y capaz de capturar relaciones de largo alcance en el texto.

Los modelos de lenguaje grande (LLM) como Llama 3.2 y Gemini 2.5 Flash siguen la variante **decoder-only** del Transformer. En lugar de tener un encoder que procesa la entrada y un decoder que genera la salida (como en los modelos de traducción), tienen un único stack de capas que procesa el prompt completo y genera la respuesta de forma autoregresiva: predice el siguiente token, lo agrega al contexto, predice el siguiente, y así sucesivamente hasta completar la respuesta.

```
[Prompt del usuario + contexto del día]
            │
            ▼
    Embedding de tokens
            │
            ▼
  ┌─────────────────────────┐
  │  Bloque Transformer     │  × N capas
  │  ┌─────────────────┐    │
  │  │ Multi-Head      │    │
  │  │ Self-Attention  │    │  cada token atiende a todos los anteriores
  │  └────────┬────────┘    │
  │           │             │
  │  ┌────────▼────────┐    │
  │  │ Feed-Forward    │    │
  │  │ Network         │    │
  │  └────────┬────────┘    │
  │           │             │
  │  ┌────────▼────────┐    │
  │  │ Layer Norm      │    │
  │  └─────────────────┘    │
  └─────────────────────────┘
            │
            ▼
    Capa softmax → siguiente token
            │
            ▼  (autoregresivo)
    "Sí, el vehículo puede circular hoy..."
```

---

## 4. Metodología y Desarrollo

### 4.1 Arquitectura del sistema

El sistema se desarrolló en Python y está compuesto por seis módulos con responsabilidades bien separadas:

```
[Fuente de video: Webcam / Imagen / Video]
          │
          ▼  OpenCV captura el frame como np.ndarray
    detector.py
    ├── Preprocesamiento: CLAHE + Unsharp Mask
    ├── EasyOCR (CRNN) → lectura de placa
    └── OpenALPR (Windows) → alternativa más precisa
          │
          ▼  texto de la placa: "EBM187"
    pico_y_placa.py
    ├── Extrae último dígito
    ├── Verifica fin de semana y festivos
    ├── Verifica horario (7:30–19:00)
    └── Compara dígito con par restringido del día
          │
          ▼  {restringido: True/False, motivo, dígito, par_hoy}
    gui.py
    ├── Dibuja bbox verde/rojo sobre el frame
    ├── Actualiza panel de resultado en tiempo real
    ├── Registra en historial con cooldown de 5 segundos
    └── Si restringido → genera ticket de multa
          │
    [Chat del usuario]
          │
          ▼
    assistant.py
    ├── Ollama · llama3.2:3b (motor local, sin internet)
    └── Gemini 2.5 Flash (respaldo si Ollama no disponible)
```

### 4.2 Módulo de detección — `detector.py`

Este módulo gestiona el reconocimiento de placas. Al iniciarse intenta cargar OpenALPR (disponible solo en Windows con las DLLs incluidas en el repositorio). Si no está disponible, activa EasyOCR automáticamente como motor principal.

Antes de pasar el frame al OCR se aplica un pipeline de preprocesamiento:

1. **Conversión a escala de grises** — elimina la información de color que no aporta al reconocimiento de texto
2. **CLAHE** (Contrast Limited Adaptive Histogram Equalization) — normaliza el contraste localmente, mejorando la legibilidad en zonas oscuras o sobreexpuestas
3. **Unsharp mask** — acentúa los bordes de los caracteres aplicando un desenfoque suavizado y combinándolo con la imagen original con peso negativo

Los resultados del OCR se filtran con la expresión regular `[A-Z]{3}\d{3}`, que corresponde al formato estándar de placas colombianas. Solo se acepta como válido un resultado que coincida exactamente con ese patrón.

### 4.3 Módulo de verificación — `pico_y_placa.py`

Implementa las reglas oficiales del decreto de Pico y Placa de Pasto. La verificación sigue un orden de prioridad:

1. Si es sábado o domingo → sin restricción
2. Si la fecha está en la lista de festivos → sin restricción
3. Si la hora actual está fuera del rango 7:30–19:00 → sin restricción
4. Si el último dígito de la placa está en el par restringido del día → restricción activa

El cálculo del par restringido se basa en una referencia fija verificada contra el decreto real: el lunes 4 de mayo de 2026 correspondía al par 8-9. A partir de ahí, la rotación sigue este patrón:

```python
REFERENCIA  = date(2026, 5, 4)
BASE_DIGITO = 8

semanas      = (lunes_de_la_fecha - REFERENCIA).days // 7
digito_lunes = (BASE_DIGITO + semanas * 2) % 10
dia_offset   = fecha.weekday()          # lunes=0, viernes=4
digito       = (digito_lunes + dia_offset * 2) % 10
par          = [digito, (digito + 1) % 10]
```

El módulo `holidays.py` contiene los 34 festivos oficiales de Colombia para 2025 y 2026, calculados aplicando la Ley Emiliani (traslado al lunes siguiente cuando el festivo no cae en lunes). Se almacenan como un `set` de objetos `date` para que la búsqueda sea O(1).

### 4.4 Asistente conversacional — `assistant.py`

El asistente usa dos motores en cascada. El motor principal es **Llama 3.2 (3B parámetros)** corriendo localmente mediante Ollama, lo que permite usarlo sin internet y sin API key. El motor de respaldo es **Gemini 2.5 Flash** de Google, que se activa automáticamente si Ollama no está disponible.

Ambos motores comparten el mismo system prompt, que limita al asistente a responder únicamente sobre Pico y Placa en Pasto. Con cada mensaje del usuario se inyecta un bloque de contexto dinámico que incluye el día, la fecha, el par restringido del momento y si es festivo. Cuando hay una placa detectada activa en la pantalla, también se inyecta el resultado ya calculado de la verificación — de esta forma el modelo solo tiene que explicar el resultado, no calcularlo, lo que reduce los errores de razonamiento del modelo de 3B parámetros.

### 4.5 Interfaz gráfica — `gui.py`

La interfaz fue construida con Tkinter, la librería gráfica incluida en la instalación estándar de Python. Tiene una ventana de 1020×800 píxeles dividida en tres zonas:

- **Panel de video (izquierda):** muestra el frame actual con el bounding box de la placa superpuesto en verde o rojo según el estado de restricción
- **Panel de resultado (derecha):** muestra la placa detectada, el estado, el último dígito, el par del día, el motor OCR usado y el porcentaje de confianza
- **Panel inferior con pestañas:** chat con el asistente, historial de detecciones exportable a CSV, y registro de multas generadas

El loop de video corre en un hilo separado para no bloquear la interfaz. Las consultas al asistente también se hacen en hilos separados para que el chat no congele la pantalla mientras el modelo genera la respuesta.

---

## 5. Resultados

### 5.1 Detección de placas

El sistema detecta correctamente placas en imágenes con buena iluminación y ángulo frontal. En condiciones de baja luz o desenfoque leve, el pipeline de preprocesamiento (CLAHE + unsharp mask) mejora la legibilidad antes de pasar al OCR. EasyOCR reporta valores de confianza entre el 75% y el 95% en condiciones normales de captura.

Las principales limitaciones observadas son:
- Placas capturadas desde ángulos muy oblicuos (más de 30°) reducen la precisión
- Distancias superiores a 3 metros con webcam de baja resolución dificultan la lectura
- El tiempo de carga inicial de EasyOCR es de 10–15 segundos la primera vez que se activa en una sesión

### 5.2 Verificación de pico y placa

La lógica de verificación es completamente determinista. Una vez que el OCR entrega el texto de la placa, el resultado de la verificación es inmediato y siempre correcto. Se probaron múltiples fechas, horarios y placas para confirmar que la rotación semanal coincide con el decreto real de Pasto. Los festivos 2025–2026 están hardcodeados siguiendo la Ley Emiliani, eliminando la dependencia de APIs externas.

### 5.3 Asistente conversacional

Con Llama 3.2 (3B) corriendo localmente, el tiempo de respuesta promedio es de 3–8 segundos dependiendo del hardware. Las respuestas son correctas cuando el contexto le entrega el resultado de la verificación ya calculado. Para preguntas generales sobre horarios, festivos y funcionamiento del sistema, el modelo responde de forma coherente y en español.

Gemini 2.5 Flash como respaldo ofrece respuestas más fluidas y rápidas (~1–2 segundos), pero requiere conexión a internet y una API key válida.

---

## 6. Conclusiones

El proyecto demostró que es posible construir un sistema funcional de visión computacional e inteligencia artificial con herramientas de código abierto y modelos que corren en hardware convencional sin necesidad de GPU.

La combinación de una red neuronal CRNN para la tarea de reconocimiento de texto y un modelo Transformer para la asistencia conversacional cubre los dos tipos de IA pedidos por el enunciado: redes neuronales para detección/clasificación, y Transformers para la generación de respuestas en lenguaje natural.

El mayor aprendizaje técnico del proyecto fue entender la diferencia entre los dos tipos de modelos y sus aplicaciones: la CRNN es una herramienta especializada que toma una imagen y entrega texto, mientras que el Transformer es un modelo de propósito general que entiende y genera lenguaje. Usarlos juntos en un mismo sistema dejó claro que la IA no es una sola tecnología sino un ecosistema de herramientas que se complementan.

Como trabajo futuro se podría incorporar un detector de región de placa basado en YOLO para mejorar la precisión del OCR en condiciones difíciles, entrenar EasyOCR específicamente con placas colombianas, y extender el sistema a otras ciudades con reglas de pico y placa distintas.

---

## 7. Referencias

- Shi, B., Bai, X., & Yao, C. (2016). *An End-to-End Trainable Neural Network for Image-Based Sequence Recognition and Its Application to Scene Text Recognition*. IEEE Transactions on Pattern Analysis and Machine Intelligence.
- Vaswani, A., et al. (2017). *Attention Is All You Need*. Advances in Neural Information Processing Systems.
- JaidedAI. (2024). *EasyOCR: Ready-to-use OCR with 80+ languages*. GitHub.
- Meta AI. (2024). *Llama 3.2: Lightweight, multilingual models*. Meta Research.
- Alcaldía de Pasto. Decreto de Pico y Placa vigente — San Juan de Pasto, Nariño, Colombia.
- Ley 51 de 1983 (Ley Emiliani) — Traslado de festivos en Colombia.
