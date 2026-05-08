"""
Entry point del sistema Pico y Placa — Pasto, Colombia.

Uso:
    python main.py
"""

import tkinter as tk
from gui import PicoPlacaApp


def main():
    root = tk.Tk()
    app  = PicoPlacaApp(root)
    root.protocol("WM_DELETE_WINDOW", app.cerrar)
    root.mainloop()


if __name__ == "__main__":
    main()
