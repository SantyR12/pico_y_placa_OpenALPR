"""
Módulo de reglas de Pico y Placa para la ciudad de Pasto, Colombia.

Reglas:
- Horario de restricción: 7:30 AM – 7:00 PM
- Días: Lunes a Viernes (sin restricción sábados, domingos y festivos)
- Criterio: último dígito de la placa vehicular
- Pares rotan semanalmente: 0-1, 2-3, 4-5, 6-7, 8-9

Rotación semanal confirmada:
  Semana del 4 may 2026 → Lun:8-9 | Mar:0-1 | Mié:2-3 | Jue:4-5 | Vie:6-7
  Cada semana el par del lunes avanza +2 (ciclo de 5 semanas).
"""

from datetime import date, datetime, time, timedelta
from holidays import FESTIVOS

# ── Constantes ────────────────────────────────────────────────────────────────
REFERENCIA   = date(2026, 5, 4)   # Lunes de referencia (dígito base = 8)
BASE_DIGITO  = 8
HORA_INICIO  = time(7, 30)
HORA_FIN     = time(19, 0)


# ── Lógica de rotación ────────────────────────────────────────────────────────
def obtener_par_restringido(fecha: date) -> list[int]:
    """
    Calcula el par de dígitos restringidos para una fecha dada.

    Retorna lista de dos enteros, ej: [6, 7]
    Retorna [] si es fin de semana o festivo.
    """
    if fecha.weekday() >= 5 or fecha in FESTIVOS:
        return []

    lunes        = fecha - timedelta(days=fecha.weekday())
    semanas      = (lunes - REFERENCIA).days // 7
    digito_lunes = (BASE_DIGITO + semanas * 2) % 10
    dia_offset   = fecha.weekday()                        # lunes=0 … viernes=4
    digito       = (digito_lunes + dia_offset * 2) % 10
    return [digito, (digito + 1) % 10]


# ── Verificación principal ────────────────────────────────────────────────────
def verificar(placa: str, fecha_hora: datetime) -> dict:
    """
    Verifica si una placa tiene restricción de pico y placa.

    Parámetros:
        placa      -- texto de la placa, ej: 'EBM187' o 'EBM-187'
        fecha_hora -- datetime con la fecha y hora a evaluar

    Retorna dict con:
        restringido  bool   -- True si tiene restricción activa
        motivo       str    -- mensaje explicativo
        digito       int    -- último dígito de la placa (-1 si inválida)
        par_hoy      list   -- par restringido hoy, ej [6, 7]
        es_festivo   bool
        en_horario   bool
    """
    placa_limpia = placa.upper().replace("-", "").replace(" ", "")

    # Validar que tenga al menos un dígito al final
    digitos = [c for c in placa_limpia if c.isdigit()]
    if not digitos:
        return {
            "restringido": False,
            "motivo"     : "Placa sin dígitos válidos",
            "digito"     : -1,
            "par_hoy"    : [],
            "es_festivo" : False,
            "en_horario" : False,
        }

    digito     = int(placa_limpia[-1])
    fecha      = fecha_hora.date()
    hora_actual = fecha_hora.time()
    dia_semana = fecha.weekday()   # 0=lunes … 6=domingo

    # ── 1. Fin de semana ──────────────────────────────────────────────────────
    if dia_semana >= 5:
        return {
            "restringido": False,
            "motivo"     : "Fin de semana — sin restricción",
            "digito"     : digito,
            "par_hoy"    : [],
            "es_festivo" : False,
            "en_horario" : False,
        }

    # ── 2. Festivo ────────────────────────────────────────────────────────────
    es_festivo = fecha in FESTIVOS
    if es_festivo:
        return {
            "restringido": False,
            "motivo"     : "Festivo — sin restricción",
            "digito"     : digito,
            "par_hoy"    : [],
            "es_festivo" : True,
            "en_horario" : False,
        }

    # ── 3. Fuera de horario ───────────────────────────────────────────────────
    en_horario = HORA_INICIO <= hora_actual <= HORA_FIN
    par_hoy    = obtener_par_restringido(fecha)

    if not en_horario:
        return {
            "restringido": False,
            "motivo"     : "Fuera de horario (7:30 AM – 7:00 PM)",
            "digito"     : digito,
            "par_hoy"    : par_hoy,
            "es_festivo" : False,
            "en_horario" : False,
        }

    # ── 4. Verificar dígito ───────────────────────────────────────────────────
    restringido = digito in par_hoy
    return {
        "restringido": restringido,
        "motivo"     : "RESTRICCIÓN ACTIVA" if restringido else "PUEDE CIRCULAR",
        "digito"     : digito,
        "par_hoy"    : par_hoy,
        "es_festivo" : False,
        "en_horario" : True,
    }
