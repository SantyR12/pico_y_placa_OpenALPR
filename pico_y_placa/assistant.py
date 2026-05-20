"""
Módulo del asistente conversacional.

Motor principal : Ollama (local, sin API key) — llama3.2:3b
Motor fallback  : Google Gemini Flash (requiere GEMINI_API_KEY)

El motor local arranca automáticamente si Ollama está corriendo.
Si falla, cae a Gemini. Si ambos fallan, devuelve mensaje de error.
"""

# ── Configuración ─────────────────────────────────────────────────────────────
import os

OLLAMA_MODEL   = "llama3.2:3b"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL   = "gemini-2.5-flash"

# ── System prompt (compartido por ambos motores) ──────────────────────────────
_SYSTEM_PROMPT = """
Eres un asistente experto en el sistema de Pico y Placa de la ciudad de
Pasto, Nariño, Colombia.

Tu rol es EXCLUSIVAMENTE responder preguntas relacionadas con:
- Restricciones vehiculares de Pico y Placa en Pasto
- Horarios de restricción (7:30 AM a 7:00 PM)
- Días con restricción (lunes a viernes, sin sábados, domingos ni festivos)
- Cómo funciona la rotación semanal de pares de dígitos
- Festivos colombianos y su efecto en la restricción
- Qué dígito de la placa determina la restricción (el último)

Si alguien pregunta algo que NO esté relacionado con el tránsito, pico y placa
o movilidad en Pasto, responde amablemente:
"Solo puedo ayudarte con preguntas sobre el Pico y Placa de Pasto.
¿Tienes alguna duda sobre las restricciones vehiculares?"

Reglas técnicas del Pico y Placa en Pasto:
- El último dígito de la placa determina la restricción
- Los pares son: 0-1, 2-3, 4-5, 6-7, 8-9
- Los pares rotan cada semana (ciclo de 5 semanas)
- Horario: 7:30 AM a 7:00 PM
- Días hábiles únicamente (lunes a viernes, sin festivos)

Responde siempre en español, de forma clara y concisa. Máximo 3 oraciones.
""".strip()

# ── Estado interno ────────────────────────────────────────────────────────────
_historial: list[dict] = []   # para Ollama (chat con memoria)
_gemini_chat = None           # sesión Gemini (lazy)
_motor_activo = None          # "ollama" | "gemini" | None


def _construir_mensaje(mensaje: str, contexto: dict) -> str:
    festivo_txt = "Hoy es festivo, no hay restricción." \
                  if contexto.get("es_festivo") else "Hoy no es festivo."

    ctx = (
        f"\n[Contexto del sistema — {contexto.get('dia', '')}, "
        f"{contexto.get('fecha', '')}: "
        f"par restringido hoy = {contexto.get('par_hoy', 'N/A')}. "
        f"{festivo_txt}"
    )

    # Si hay una placa detectada activa, inyectar el resultado ya calculado
    # para que el modelo explique en lugar de calcular (evita errores de razonamiento)
    placa  = contexto.get("placa_detectada")
    digito = contexto.get("digito")
    if placa and digito is not None:
        estado = "TIENE RESTRICCIÓN ACTIVA y NO puede circular" \
                 if contexto.get("restringido") else "PUEDE circular sin restricción"
        ctx += (
            f" Placa detectada actualmente: {placa} "
            f"(último dígito: {digito}). "
            f"Esta placa {estado} hoy."
        )

    ctx += "]"
    return mensaje + ctx


# ── Motor 1: Ollama (local) ───────────────────────────────────────────────────
def _preguntar_ollama(mensaje_con_ctx: str) -> str:
    import ollama

    _historial.append({"role": "user", "content": mensaje_con_ctx})
    respuesta = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "system", "content": _SYSTEM_PROMPT}] + _historial,
    )
    texto = respuesta.message.content.strip()
    _historial.append({"role": "assistant", "content": texto})
    return texto


# ── Motor 2: Gemini (fallback) ────────────────────────────────────────────────
def _get_gemini_chat():
    global _gemini_chat
    if _gemini_chat is None:
        from google import genai
        from google.genai.types import GenerateContentConfig
        client = genai.Client(api_key=GEMINI_API_KEY)
        _gemini_chat = client.chats.create(
            model=GEMINI_MODEL,
            config=GenerateContentConfig(system_instruction=_SYSTEM_PROMPT),
        )
    return _gemini_chat


def _preguntar_gemini(mensaje_con_ctx: str) -> str:
    chat = _get_gemini_chat()
    return chat.send_message(mensaje_con_ctx).text.strip()


# ── API pública ───────────────────────────────────────────────────────────────
def preguntar(mensaje: str, contexto: dict) -> str:
    """
    Envía un mensaje al asistente con contexto de fecha/hora actual.

    Intenta Ollama primero (local, sin API key).
    Si falla, usa Gemini como respaldo.
    """
    global _motor_activo
    msg = _construir_mensaje(mensaje, contexto)

    # ── Intento 1: Ollama ─────────────────────────────────────────────────────
    try:
        respuesta = _preguntar_ollama(msg)
        if _motor_activo != "ollama":
            _motor_activo = "ollama"
            print("[asistente] Motor activo: Ollama (local)")
        return respuesta
    except Exception as e_ollama:
        print(f"[asistente] Ollama no disponible ({e_ollama}), usando Gemini…")
        # Limpiar historial de ollama para no contaminar el siguiente intento
        if _historial:
            _historial.pop()

    # ── Intento 2: Gemini ─────────────────────────────────────────────────────
    try:
        respuesta = _preguntar_gemini(msg)
        if _motor_activo != "gemini":
            _motor_activo = "gemini"
            print("[asistente] Motor activo: Gemini Flash")
        return respuesta
    except Exception as e_gemini:
        return (
            "No pude conectarme con ningún motor de IA.\n"
            f"• Ollama: asegúrate de que el servicio esté corriendo (`ollama serve`).\n"
            f"• Gemini: verifica la API Key en assistant.py.\n"
            f"Error Gemini: {e_gemini}"
        )


def reiniciar_chat():
    """Limpia el historial de conversación de ambos motores."""
    global _historial, _gemini_chat
    _historial.clear()
    _gemini_chat = None
