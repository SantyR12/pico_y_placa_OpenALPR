"""
Módulo del asistente conversacional.

Usa Google Gemini (nuevo SDK google-genai) para responder preguntas
sobre el Pico y Placa de Pasto, Colombia.
Rechaza amablemente preguntas fuera del dominio.
"""

from google import genai
from google.genai.types import GenerateContentConfig

# ── API Key ───────────────────────────────────────────────────────────────────
# Reemplaza este valor con tu API Key de Google AI Studio:
# https://aistudio.google.com/app/apikey
GEMINI_API_KEY = "AIzaSyDHD_iLBMyjCQUQXQMkSJvJC4tBvyTelXY"
GEMINI_MODEL   = "gemini-2.5-flash"

# ── System prompt ─────────────────────────────────────────────────────────────
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

Responde siempre en español, de forma clara y concisa.
""".strip()

# ── Cliente y sesión de chat (inicialización lazy) ────────────────────────────
_client       = None
_chat_session = None


def _get_chat() -> object:
    """Inicializa el cliente y la sesión de chat la primera vez que se necesita."""
    global _client, _chat_session
    if _chat_session is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
        _chat_session = _client.chats.create(
            model=GEMINI_MODEL,
            config=GenerateContentConfig(system_instruction=_SYSTEM_PROMPT),
        )
    return _chat_session


# ── API pública ───────────────────────────────────────────────────────────────
def preguntar(mensaje: str, contexto: dict) -> str:
    """
    Envía un mensaje al asistente Gemini con contexto de fecha/hora actual.

    Parámetros:
        mensaje  -- texto del usuario
        contexto -- dict con claves:
                    'dia'        str   ej: 'Viernes'
                    'fecha'      str   ej: '08/05/2026'
                    'par_hoy'    str   ej: '6-7'
                    'es_festivo' bool

    Retorna la respuesta del asistente como string.
    """
    festivo_txt = "Hoy es festivo, no hay restricción." \
                  if contexto.get("es_festivo") else "Hoy no es festivo."

    contexto_str = (
        f"\n[Contexto del sistema — {contexto.get('dia', '')}, "
        f"{contexto.get('fecha', '')}: "
        f"par restringido hoy = {contexto.get('par_hoy', 'N/A')}. "
        f"{festivo_txt}]"
    )

    try:
        chat     = _get_chat()
        respuesta = chat.send_message(mensaje + contexto_str)
        return respuesta.text.strip()
    except Exception as e:
        return (
            f"No pude conectarme con el asistente.\n"
            f"Error: {e}\n\n"
            f"Verifica que tu API Key de Gemini sea válida en assistant.py."
        )


def reiniciar_chat():
    """Limpia el historial de conversación iniciando una nueva sesión."""
    global _chat_session
    _chat_session = None
