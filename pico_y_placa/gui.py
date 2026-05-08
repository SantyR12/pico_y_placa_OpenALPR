"""
Interfaz gráfica principal — Tkinter.

Paneles:
  - Izquierdo : video en tiempo real con bbox sobre la placa
  - Derecho   : placa detectada + resultado pico y placa
  - Inferior  : chat con asistente Gemini
"""

import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext
from datetime import datetime

import cv2
import numpy as np
from PIL import Image, ImageTk

from detector import detectar_placa
from pico_y_placa import verificar, obtener_par_restringido
from holidays import FESTIVOS
from assistant import preguntar, reiniciar_chat

# ── Paleta de colores ─────────────────────────────────────────────────────────
BG_MAIN    = "#1e1e2e"
BG_PANEL   = "#2a2a3e"
BG_DARK    = "#12121e"
FG_WHITE   = "#ffffff"
FG_GRAY    = "#aaaacc"
FG_GREEN   = "#6bff9e"
FG_RED     = "#ff6b6b"
FG_YELLOW  = "#ffd700"
BTN_BLUE   = "#4a90d9"
BTN_GREEN  = "#3a9e6f"
BTN_ORANGE = "#d4813a"
BTN_RED    = "#c0392b"
BTN_PURPLE = "#7c5cbf"

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

VIDEO_W = 640
VIDEO_H = 400


class PicoPlacaApp:
    def __init__(self, root: tk.Tk):
        self.root     = root
        self.cap      = None
        self.running  = False
        self._ultimo  = {}

        self.root.title("Pico y Placa — Pasto, Colombia")
        self.root.geometry("1020x730")
        self.root.configure(bg=BG_MAIN)
        self.root.resizable(False, False)

        self._construir_ui()
        self._actualizar_reloj()

    # ── Construcción de la UI ─────────────────────────────────────────────────
    def _construir_ui(self):
        # ── Título ────────────────────────────────────────────────────────────
        tk.Label(
            self.root, text="🚗  Pico y Placa — Pasto, Colombia",
            bg=BG_MAIN, fg=FG_YELLOW, font=("Arial", 14, "bold")
        ).pack(pady=(8, 0))

        self.lbl_reloj = tk.Label(
            self.root, text="", bg=BG_MAIN, fg=FG_GRAY, font=("Arial", 10)
        )
        self.lbl_reloj.pack()

        # ── Fila superior: video + resultado ─────────────────────────────────
        fila_sup = tk.Frame(self.root, bg=BG_MAIN)
        fila_sup.pack(fill=tk.X, padx=10, pady=(5, 0))

        # Panel video
        self.lbl_video = tk.Label(
            fila_sup, bg=BG_DARK,
            width=VIDEO_W, height=VIDEO_H
        )
        self.lbl_video.pack(side=tk.LEFT)
        self._mostrar_placeholder()

        # Panel resultado
        pnl = tk.Frame(fila_sup, bg=BG_PANEL, width=340)
        pnl.pack(side=tk.LEFT, fill=tk.Y, padx=(8, 0))
        pnl.pack_propagate(False)

        tk.Label(pnl, text="PLACA DETECTADA",
                 bg=BG_PANEL, fg=FG_GRAY,
                 font=("Arial", 9, "bold")).pack(pady=(18, 4))

        self.lbl_placa = tk.Label(
            pnl, text="---",
            bg=BG_PANEL, fg=FG_WHITE,
            font=("Courier", 26, "bold")
        )
        self.lbl_placa.pack(pady=4)

        self.lbl_estado = tk.Label(
            pnl, text="Esperando detección…",
            bg=BG_PANEL, fg=FG_GRAY,
            font=("Arial", 12, "bold"), wraplength=300
        )
        self.lbl_estado.pack(pady=8)

        self.lbl_detalle = tk.Label(
            pnl, text="",
            bg=BG_PANEL, fg=FG_GRAY,
            font=("Arial", 10), wraplength=300, justify=tk.LEFT
        )
        self.lbl_detalle.pack(pady=4, padx=12, anchor=tk.W)

        tk.Label(pnl, text="─" * 34, bg=BG_PANEL, fg="#444466").pack(pady=8)

        # Info par actual
        tk.Label(pnl, text="Par restringido hoy:",
                 bg=BG_PANEL, fg=FG_GRAY, font=("Arial", 9)).pack()
        self.lbl_par_actual = tk.Label(
            pnl, text="",
            bg=BG_PANEL, fg=FG_YELLOW, font=("Arial", 16, "bold")
        )
        self.lbl_par_actual.pack(pady=2)

        tk.Button(
            pnl, text="🔄 Nuevo chat", bg=BTN_PURPLE, fg=FG_WHITE,
            font=("Arial", 9, "bold"), bd=0, padx=10, pady=4,
            cursor="hand2", command=self._reiniciar_chat
        ).pack(pady=(16, 4))

        # ── Botones fuente ────────────────────────────────────────────────────
        fila_btn = tk.Frame(self.root, bg=BG_MAIN)
        fila_btn.pack(fill=tk.X, padx=10, pady=6)

        _btn = dict(font=("Arial", 11, "bold"), padx=18, pady=7,
                    bd=0, cursor="hand2", fg=FG_WHITE)

        tk.Button(fila_btn, text="📷 Webcam",  bg=BTN_BLUE,
                  command=self.iniciar_webcam,  **_btn).pack(side=tk.LEFT, padx=4)
        tk.Button(fila_btn, text="🖼  Imagen",  bg=BTN_GREEN,
                  command=self.cargar_imagen,   **_btn).pack(side=tk.LEFT, padx=4)
        tk.Button(fila_btn, text="🎬 Video",   bg=BTN_ORANGE,
                  command=self.cargar_video,    **_btn).pack(side=tk.LEFT, padx=4)
        tk.Button(fila_btn, text="⏹  Detener", bg=BTN_RED,
                  command=self.detener,         **_btn).pack(side=tk.LEFT, padx=4)

        # ── Panel chat ────────────────────────────────────────────────────────
        pnl_chat = tk.Frame(self.root, bg=BG_PANEL)
        pnl_chat.pack(fill=tk.BOTH, padx=10, pady=(0, 8))

        tk.Label(
            pnl_chat, text="💬  Asistente Pico y Placa (Gemini)",
            bg=BG_PANEL, fg=FG_GRAY, font=("Arial", 10, "bold")
        ).pack(anchor=tk.W, padx=10, pady=(8, 2))

        self.txt_chat = scrolledtext.ScrolledText(
            pnl_chat, height=7,
            bg=BG_DARK, fg=FG_WHITE,
            font=("Arial", 10), state=tk.DISABLED,
            wrap=tk.WORD, insertbackground=FG_WHITE
        )
        self.txt_chat.pack(fill=tk.X, padx=10, pady=(0, 4))

        fila_inp = tk.Frame(pnl_chat, bg=BG_PANEL)
        fila_inp.pack(fill=tk.X, padx=10, pady=(0, 8))

        self.ent_chat = tk.Entry(
            fila_inp, bg=BG_DARK, fg=FG_WHITE,
            font=("Arial", 11), insertbackground=FG_WHITE, bd=0,
            highlightthickness=1, highlightbackground="#555577"
        )
        self.ent_chat.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6), ipady=5)
        self.ent_chat.bind("<Return>", lambda _: self.enviar_mensaje())

        tk.Button(
            fila_inp, text="Enviar", bg=BTN_BLUE, fg=FG_WHITE,
            font=("Arial", 10, "bold"), bd=0, padx=14, pady=5,
            cursor="hand2", command=self.enviar_mensaje
        ).pack(side=tk.RIGHT)

        self._agregar_chat(
            "Asistente",
            "¡Hola! Soy tu asistente de Pico y Placa en Pasto. "
            "Puedo ayudarte a saber si tu vehículo puede circular hoy. "
            "¿En qué te puedo ayudar?",
            FG_GREEN
        )

    # ── Reloj ─────────────────────────────────────────────────────────────────
    def _actualizar_reloj(self):
        ahora = datetime.now()
        dia   = DIAS[ahora.weekday()]
        self.lbl_reloj.config(
            text=f"{dia} {ahora.strftime('%d/%m/%Y  %H:%M:%S')}"
        )
        # Actualizar par restringido
        par = obtener_par_restringido(ahora.date())
        if par:
            self.lbl_par_actual.config(text=f"{par[0]}  –  {par[1]}")
        else:
            self.lbl_par_actual.config(text="Sin restricción")

        self.root.after(1000, self._actualizar_reloj)

    # ── Placeholder ───────────────────────────────────────────────────────────
    def _mostrar_placeholder(self):
        img = np.zeros((VIDEO_H, VIDEO_W, 3), dtype=np.uint8)
        cv2.putText(img, "Sin señal", (VIDEO_W // 2 - 80, VIDEO_H // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (80, 80, 120), 2)
        self._render_frame(img)

    # ── Renderizar frame ──────────────────────────────────────────────────────
    def _render_frame(self, frame: np.ndarray):
        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img   = Image.fromarray(rgb).resize((VIDEO_W, VIDEO_H), Image.LANCZOS)
        imgtk = ImageTk.PhotoImage(image=img)
        self.lbl_video.imgtk = imgtk
        self.lbl_video.config(image=imgtk)

    # ── Limpiar panel resultado ───────────────────────────────────────────────
    def _limpiar_panel(self):
        self.lbl_placa.config(text="---")
        self.lbl_estado.config(text="Sin placa detectada", fg=FG_GRAY)
        self.lbl_detalle.config(text="")
        self._ultimo = {}

    # ── Procesar frame ────────────────────────────────────────────────────────
    def _procesar_frame(self, frame: np.ndarray):
        resultado = detectar_placa(frame)

        if resultado:
            x, y, w, h    = resultado["bbox"]
            fecha_hora     = datetime.now()
            verificacion   = verificar(resultado["placa"], fecha_hora)
            self._ultimo   = verificacion

            color = (0, 0, 220) if verificacion["restringido"] else (0, 200, 80)
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 3)
            cv2.putText(
                frame, resultado["placa"],
                (x, max(y - 12, 20)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2
            )

            # Actualizar panel resultado
            self.lbl_placa.config(text=resultado["placa"])

            if verificacion["restringido"]:
                self.lbl_estado.config(text="❌  RESTRICCIÓN ACTIVA", fg=FG_RED)
            else:
                self.lbl_estado.config(text="✅  PUEDE CIRCULAR", fg=FG_GREEN)

            par = verificacion["par_hoy"]
            dia = DIAS[fecha_hora.weekday()]
            detalle = (
                f"Último dígito : {verificacion['digito']}\n"
                f"Par restringido: {par[0]}-{par[1] if par else 'N/A'}\n"
                f"Día            : {dia} {fecha_hora.strftime('%d/%m/%Y')}\n"
                f"Horario        : 7:30 AM – 7:00 PM\n"
                f"Motor OCR      : {resultado['motor']}\n"
                f"Confianza      : {resultado['confianza']}%"
            )
            self.lbl_detalle.config(text=detalle)

        self._render_frame(frame)

    # ── Loop de video ─────────────────────────────────────────────────────────
    def _loop_video(self):
        while self.running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break
            self.root.after(0, self._procesar_frame, frame)
            cv2.waitKey(30)
        self.running = False

    # ── Controles de fuente ───────────────────────────────────────────────────
    def iniciar_webcam(self):
        self.detener()
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self._agregar_chat("Sistema", "No se detectó ninguna webcam.", FG_RED)
            return
        self.running = True
        threading.Thread(target=self._loop_video, daemon=True).start()

    def cargar_imagen(self):
        self.detener()
        path = filedialog.askopenfilename(
            title="Seleccionar imagen",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.bmp *.webp")]
        )
        if path:
            frame = cv2.imread(path)
            if frame is not None:
                self._limpiar_panel()   # resetear panel antes de cada imagen nueva
                self._procesar_frame(frame)
            else:
                self._agregar_chat("Sistema", "No se pudo leer la imagen.", FG_RED)

    def cargar_video(self):
        self.detener()
        path = filedialog.askopenfilename(
            title="Seleccionar video",
            filetypes=[("Videos", "*.mp4 *.avi *.mov *.mkv *.wmv")]
        )
        if path:
            self.cap = cv2.VideoCapture(path)
            self.running = True
            threading.Thread(target=self._loop_video, daemon=True).start()

    def detener(self):
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self._mostrar_placeholder()

    # ── Chat ──────────────────────────────────────────────────────────────────
    def enviar_mensaje(self):
        mensaje = self.ent_chat.get().strip()
        if not mensaje:
            return
        self.ent_chat.delete(0, tk.END)
        self._agregar_chat("Tú", mensaje, "#a0c4ff")

        ahora = datetime.now()
        par   = obtener_par_restringido(ahora.date())
        contexto = {
            "dia"       : DIAS[ahora.weekday()],
            "fecha"     : ahora.strftime("%d/%m/%Y"),
            "par_hoy"   : f"{par[0]}-{par[1]}" if par else "Sin restricción",
            "es_festivo": ahora.date() in FESTIVOS,
        }
        threading.Thread(
            target=self._responder_gemini,
            args=(mensaje, contexto),
            daemon=True
        ).start()

    def _responder_gemini(self, mensaje: str, contexto: dict):
        respuesta = preguntar(mensaje, contexto)
        self.root.after(0, self._agregar_chat, "Asistente", respuesta, FG_GREEN)

    def _agregar_chat(self, remitente: str, texto: str, color: str):
        self.txt_chat.config(state=tk.NORMAL)
        self.txt_chat.insert(tk.END, f"{remitente}: {texto}\n\n")
        self.txt_chat.config(state=tk.DISABLED)
        self.txt_chat.see(tk.END)

    def _reiniciar_chat(self):
        reiniciar_chat()
        self.txt_chat.config(state=tk.NORMAL)
        self.txt_chat.delete("1.0", tk.END)
        self.txt_chat.config(state=tk.DISABLED)
        self._agregar_chat("Sistema", "Chat reiniciado.", FG_YELLOW)

    # ── Cierre ────────────────────────────────────────────────────────────────
    def cerrar(self):
        self.detener()
        self.root.destroy()
