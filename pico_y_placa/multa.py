"""
Generador de ticket de multa por infracción de Pico y Placa — Pasto, Colombia.
"""

import random
import tkinter as tk
from tkinter import ttk
from datetime import datetime

NOMBRES = [
    "Carlos Andres Muñoz Lopez",
    "Maria Fernanda Castillo Rios",
    "Andres Felipe Torres Gomez",
    "Laura Milena Pacheco Vargas",
    "Juan Sebastian Rojas Mora",
    "Ana Maria Guerrero Pinto",
    "Diego Alejandro Salcedo Ruiz",
    "Paola Andrea Narvaez Cordoba",
    "Luis Eduardo Benavides Enriquez",
    "Sandra Patricia Moncayo Coral",
]

VALOR_MULTA = 633_200
INFRACCION  = "Circulación en horario de Pico y Placa"
AUTORIDAD   = "Secretaría de Tránsito y Transporte — Pasto, Nariño"

BG_MAIN  = "#1e1e2e"
BG_PANEL = "#2a2a3e"
FG_WHITE = "#ffffff"
FG_GRAY  = "#aaaacc"
FG_RED   = "#ff6b6b"
FG_GOLD  = "#ffd700"


def _formato_pesos(valor: int) -> str:
    return "$ {:,}".format(valor).replace(",", ".")


def mostrar_multa(root: tk.Tk, placa: str, fecha_hora: datetime,
                  on_generada=None):
    """Abre una ventana modal con el ticket de multa.

    on_generada -- callback opcional: on_generada(nombre, placa, fecha_hora)
    """
    nombre = random.choice(NOMBRES)
    if on_generada:
        on_generada(nombre, placa, fecha_hora)
    folio  = "PPP-{}-{}".format(
        fecha_hora.strftime("%Y%m%d"), random.randint(1000, 9999)
    )

    ventana = tk.Toplevel(root)
    ventana.title("Ticket de Multa — Pico y Placa")
    ventana.geometry("480x530")
    ventana.configure(bg=BG_MAIN)
    ventana.resizable(False, False)
    ventana.grab_set()

    # ── Encabezado rojo ───────────────────────────────────────────────────────
    tk.Label(
        ventana, text="INFRACCION DE TRANSITO",
        bg="#c0392b", fg=FG_WHITE,
        font=("Arial", 13, "bold"), pady=10
    ).pack(fill=tk.X)

    tk.Label(
        ventana, text=AUTORIDAD,
        bg=BG_MAIN, fg=FG_GRAY, font=("Arial", 9)
    ).pack(pady=(6, 0))

    tk.Label(
        ventana, text="Folio N.  {}".format(folio),
        bg=BG_MAIN, fg=FG_GOLD, font=("Arial", 9, "bold")
    ).pack()

    ttk.Separator(ventana, orient="horizontal").pack(fill=tk.X, padx=20, pady=8)

    # ── Datos del infractor ───────────────────────────────────────────────────
    frame = tk.Frame(ventana, bg=BG_PANEL, padx=20, pady=14)
    frame.pack(fill=tk.X, padx=20)

    campos = [
        ("Infractor",   nombre),
        ("Placa",       placa),
        ("Fecha",       fecha_hora.strftime("%d/%m/%Y")),
        ("Hora",        fecha_hora.strftime("%H:%M:%S")),
        ("Infraccion",  INFRACCION),
    ]
    for etiqueta, valor in campos:
        fila = tk.Frame(frame, bg=BG_PANEL)
        fila.pack(fill=tk.X, pady=3)
        tk.Label(
            fila, text="{}:".format(etiqueta),
            bg=BG_PANEL, fg=FG_GRAY,
            font=("Arial", 10), width=13, anchor=tk.W
        ).pack(side=tk.LEFT)
        tk.Label(
            fila, text=valor,
            bg=BG_PANEL, fg=FG_WHITE,
            font=("Arial", 10, "bold"), anchor=tk.W
        ).pack(side=tk.LEFT)

    # ── Valor de la multa ─────────────────────────────────────────────────────
    ttk.Separator(ventana, orient="horizontal").pack(fill=tk.X, padx=20, pady=8)

    tk.Label(
        ventana, text="VALOR DE LA MULTA",
        bg=BG_MAIN, fg=FG_GRAY, font=("Arial", 10)
    ).pack()

    tk.Label(
        ventana, text=_formato_pesos(VALOR_MULTA),
        bg=BG_MAIN, fg=FG_RED,
        font=("Arial", 26, "bold")
    ).pack(pady=4)

    tk.Label(
        ventana,
        text="Art. 77 - Ley 769/2002  |  Decreto Municipal Pico y Placa",
        bg=BG_MAIN, fg="#555577", font=("Arial", 8)
    ).pack()

    ttk.Separator(ventana, orient="horizontal").pack(fill=tk.X, padx=20, pady=10)

    # ── Botón cerrar ──────────────────────────────────────────────────────────
    tk.Button(
        ventana, text="Cerrar",
        bg="#4a90d9", fg=FG_WHITE,
        font=("Arial", 11, "bold"), bd=0,
        padx=30, pady=8, cursor="hand2",
        command=ventana.destroy
    ).pack(pady=(0, 16))
