"""
Festivos oficiales de Colombia 2025-2026.
Basado en la Ley Emiliani (Ley 51 de 1983): los festivos que no caen
en lunes se trasladan al siguiente lunes.
"""

from datetime import date

FESTIVOS = {
    # ── 2025 ──────────────────────────────────────────────
    date(2025, 1,  1),   # Año Nuevo
    date(2025, 1,  6),   # Reyes Magos (ya es lunes)
    date(2025, 3, 24),   # San José (19 mar mié → lunes 24)
    date(2025, 4, 17),   # Jueves Santo
    date(2025, 4, 18),   # Viernes Santo
    date(2025, 5,  1),   # Día del Trabajo
    date(2025, 6,  2),   # Ascensión del Señor (Pascua+39, trasladado)
    date(2025, 6, 23),   # Corpus Christi (Pascua+60, trasladado)
    date(2025, 6, 30),   # Sagrado Corazón + San Pedro y San Pablo
    date(2025, 7, 20),   # Independencia de Colombia
    date(2025, 8,  7),   # Batalla de Boyacá
    date(2025, 8, 18),   # Asunción de la Virgen (15 ago vie → lunes 18)
    date(2025, 10,13),   # Día de la Raza (12 oct dom → lunes 13)
    date(2025, 11, 3),   # Todos los Santos (1 nov sáb → lunes 3)
    date(2025, 11,17),   # Independencia de Cartagena (11 nov mar → lunes 17)
    date(2025, 12, 8),   # Inmaculada Concepción
    date(2025, 12,25),   # Navidad

    # ── 2026 ──────────────────────────────────────────────
    date(2026, 1,  1),   # Año Nuevo
    date(2026, 1, 12),   # Reyes Magos (6 ene mar → lunes 12)
    date(2026, 3, 23),   # San José (19 mar jue → lunes 23)
    date(2026, 4,  2),   # Jueves Santo
    date(2026, 4,  3),   # Viernes Santo
    date(2026, 5,  1),   # Día del Trabajo
    date(2026, 5, 18),   # Ascensión del Señor (trasladado)
    date(2026, 6,  8),   # Corpus Christi (trasladado)
    date(2026, 6, 15),   # Sagrado Corazón (trasladado)
    date(2026, 6, 29),   # San Pedro y San Pablo (ya es lunes)
    date(2026, 7, 20),   # Independencia de Colombia
    date(2026, 8,  7),   # Batalla de Boyacá
    date(2026, 8, 17),   # Asunción de la Virgen (15 ago sáb → lunes 17)
    date(2026, 10,12),   # Día de la Raza (ya es lunes)
    date(2026, 11, 2),   # Todos los Santos (1 nov dom → lunes 2)
    date(2026, 11,16),   # Independencia de Cartagena (11 nov mié → lunes 16)
    date(2026, 12, 8),   # Inmaculada Concepción
    date(2026, 12,25),   # Navidad
}
