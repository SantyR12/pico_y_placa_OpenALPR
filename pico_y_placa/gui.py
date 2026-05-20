"""
Interfaz gráfica principal — Tkinter.

Paneles:
  - Izquierdo : video en tiempo real con bbox sobre la placa
  - Derecho   : placa detectada + resultado pico y placa
  - Inferior  : tabs → Chat (Gemini) | Historial de detecciones
"""

import csv
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
from datetime import datetime

import cv2
import numpy as np
from PIL import Image, ImageTk

from detector import detectar_placa
from pico_y_placa import verificar, obtener_par_restringido
from holidays import FESTIVOS
from assistant import preguntar, reiniciar_chat
from multa import mostrar_multa

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
BTN_TEAL   = "#2a9d8f"

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

VIDEO_W      = 640
VIDEO_H      = 400
COOLDOWN_SEG = 5   # segundos antes de volver a registrar la misma placa


class PicoPlacaApp:
    def __init__(self, root: tk.Tk):
        self.root      = root
        self.cap       = None
        self.running   = False
        self._ultimo   = {}
        self._historial: list[dict] = []
        self._multas:    list[dict] = []
        self._cooldown: dict[str, datetime] = {}

        self.root.title("Pico y Placa — Pasto, Colombia")
        self.root.geometry("1020x800")
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

        # ── Panel inferior con tabs ───────────────────────────────────────────
        self._construir_tabs()

    # ── Tabs inferiores ───────────────────────────────────────────────────────
    def _construir_tabs(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Dark.TNotebook",
                        background=BG_MAIN, borderwidth=0)
        style.configure("Dark.TNotebook.Tab",
                        background=BG_PANEL, foreground=FG_GRAY,
                        padding=[12, 5], font=("Arial", 10, "bold"))
        style.map("Dark.TNotebook.Tab",
                  background=[("selected", BTN_BLUE)],
                  foreground=[("selected", FG_WHITE)])

        nb = ttk.Notebook(self.root, style="Dark.TNotebook")
        nb.pack(fill=tk.BOTH, padx=10, pady=(0, 8), expand=True)

        tab_chat = tk.Frame(nb, bg=BG_PANEL)
        nb.add(tab_chat, text="💬  Chat Gemini")
        self._construir_chat(tab_chat)

        tab_hist = tk.Frame(nb, bg=BG_PANEL)
        nb.add(tab_hist, text="📋  Historial")
        self._construir_historial(tab_hist)

        tab_multas = tk.Frame(nb, bg=BG_PANEL)
        nb.add(tab_multas, text="📄  Multas")
        self._construir_multas(tab_multas)

    # ── Tab Chat ──────────────────────────────────────────────────────────────
    def _construir_chat(self, parent):
        tk.Label(
            parent, text="💬  Asistente Pico y Placa (Gemini)",
            bg=BG_PANEL, fg=FG_GRAY, font=("Arial", 10, "bold")
        ).pack(anchor=tk.W, padx=10, pady=(8, 2))

        self.txt_chat = scrolledtext.ScrolledText(
            parent, height=6,
            bg=BG_DARK, fg=FG_WHITE,
            font=("Arial", 10), state=tk.DISABLED,
            wrap=tk.WORD, insertbackground=FG_WHITE
        )
        self.txt_chat.pack(fill=tk.X, padx=10, pady=(0, 4))

        fila_inp = tk.Frame(parent, bg=BG_PANEL)
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

    # ── Tab Historial ─────────────────────────────────────────────────────────
    def _construir_historial(self, parent):
        # Barra superior: contador + botones
        barra = tk.Frame(parent, bg=BG_PANEL)
        barra.pack(fill=tk.X, padx=10, pady=(8, 4))

        self.lbl_conteo = tk.Label(
            barra, text="0 vehículos detectados",
            bg=BG_PANEL, fg=FG_GRAY, font=("Arial", 10, "bold")
        )
        self.lbl_conteo.pack(side=tk.LEFT)

        tk.Button(
            barra, text="🗑  Limpiar", bg=BTN_RED, fg=FG_WHITE,
            font=("Arial", 9, "bold"), bd=0, padx=10, pady=3,
            cursor="hand2", command=self._limpiar_historial
        ).pack(side=tk.RIGHT, padx=(4, 0))

        tk.Button(
            barra, text="💾  Exportar CSV", bg=BTN_TEAL, fg=FG_WHITE,
            font=("Arial", 9, "bold"), bd=0, padx=10, pady=3,
            cursor="hand2", command=self._exportar_csv
        ).pack(side=tk.RIGHT, padx=(4, 0))

        # Tabla (Treeview)
        style = ttk.Style()
        style.configure("Dark.Treeview",
                        background=BG_DARK, foreground=FG_WHITE,
                        fieldbackground=BG_DARK, rowheight=22,
                        font=("Arial", 10))
        style.configure("Dark.Treeview.Heading",
                        background=BG_PANEL, foreground=FG_YELLOW,
                        font=("Arial", 9, "bold"))
        style.map("Dark.Treeview",
                  background=[("selected", BTN_BLUE)],
                  foreground=[("selected", FG_WHITE)])

        frame_tree = tk.Frame(parent, bg=BG_DARK)
        frame_tree.pack(fill=tk.BOTH, padx=10, pady=(0, 8), expand=True)

        cols = ("hora", "placa", "estado", "digito", "motor", "confianza")
        self.tree = ttk.Treeview(
            frame_tree, columns=cols, show="headings",
            style="Dark.Treeview", height=6
        )

        encabezados = {
            "hora"      : ("Hora",       90),
            "placa"     : ("Placa",      90),
            "estado"    : ("Estado",    145),
            "digito"    : ("Dígito",     65),
            "motor"     : ("Motor",     100),
            "confianza" : ("Confianza",  85),
        }
        for col, (texto, ancho) in encabezados.items():
            self.tree.heading(col, text=texto)
            self.tree.column(col, width=ancho, anchor=tk.CENTER)

        scroll_y = ttk.Scrollbar(frame_tree, orient=tk.VERTICAL,
                                 command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        # Tags de color por fila
        self.tree.tag_configure("libre",       foreground=FG_GREEN)
        self.tree.tag_configure("restringido", foreground=FG_RED)

    # ── Tab Multas ────────────────────────────────────────────────────────────
    def _construir_multas(self, parent):
        barra = tk.Frame(parent, bg=BG_PANEL)
        barra.pack(fill=tk.X, padx=10, pady=(8, 4))

        self.lbl_conteo_multas = tk.Label(
            barra, text="0 multas generadas",
            bg=BG_PANEL, fg=FG_GRAY, font=("Arial", 10, "bold")
        )
        self.lbl_conteo_multas.pack(side=tk.LEFT)

        tk.Button(
            barra, text="🗑  Limpiar", bg=BTN_RED, fg=FG_WHITE,
            font=("Arial", 9, "bold"), bd=0, padx=10, pady=3,
            cursor="hand2", command=self._limpiar_multas
        ).pack(side=tk.RIGHT, padx=(4, 0))

        tk.Button(
            barra, text="💾  Exportar CSV", bg=BTN_TEAL, fg=FG_WHITE,
            font=("Arial", 9, "bold"), bd=0, padx=10, pady=3,
            cursor="hand2", command=self._exportar_multas_csv
        ).pack(side=tk.RIGHT, padx=(4, 0))

        frame_tree = tk.Frame(parent, bg=BG_DARK)
        frame_tree.pack(fill=tk.BOTH, padx=10, pady=(0, 8), expand=True)

        cols = ("hora", "nombre", "placa", "monto")
        self.tree_multas = ttk.Treeview(
            frame_tree, columns=cols, show="headings",
            style="Dark.Treeview", height=6
        )

        encabezados = {
            "hora"   : ("Hora",      90),
            "nombre" : ("Infractor", 230),
            "placa"  : ("Placa",     100),
            "monto"  : ("Monto",     110),
        }
        for col, (texto, ancho) in encabezados.items():
            self.tree_multas.heading(col, text=texto)
            self.tree_multas.column(col, width=ancho, anchor=tk.CENTER)

        scroll_y = ttk.Scrollbar(frame_tree, orient=tk.VERTICAL,
                                 command=self.tree_multas.yview)
        self.tree_multas.configure(yscrollcommand=scroll_y.set)
        self.tree_multas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_multas.tag_configure("multa", foreground=FG_RED)

    def _agregar_multa_tabla(self, nombre: str, placa: str, fecha_hora: datetime):
        monto_txt = "$ {:,}".format(633_200).replace(",", ".")
        fila = {
            "hora"  : fecha_hora.strftime("%H:%M:%S"),
            "nombre": nombre,
            "placa" : placa,
            "monto" : monto_txt,
        }
        self._multas.append(fila)
        self.tree_multas.insert(
            "", 0,
            values=(fila["hora"], fila["nombre"], fila["placa"], fila["monto"]),
            tags=("multa",)
        )
        total  = len(self._multas)
        sufijo = "s" if total != 1 else ""
        self.lbl_conteo_multas.config(text=f"{total} multa{sufijo} generada{sufijo}")

    def _limpiar_multas(self):
        self._multas.clear()
        for item in self.tree_multas.get_children():
            self.tree_multas.delete(item)
        self.lbl_conteo_multas.config(text="0 multas generadas")

    def _exportar_multas_csv(self):
        if not self._multas:
            self._agregar_chat("Sistema", "No hay multas para exportar.", FG_YELLOW)
            return
        path = filedialog.asksaveasfilename(
            title="Guardar multas",
            defaultextension=".csv",
            initialfile=f"multas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")]
        )
        if not path:
            return
        campos = ["hora", "nombre", "placa", "monto"]
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(self._multas)
        self._agregar_chat("Sistema", f"Multas exportadas → {path}", FG_GREEN)

    # ── Reloj ─────────────────────────────────────────────────────────────────
    def _actualizar_reloj(self):
        ahora = datetime.now()
        dia   = DIAS[ahora.weekday()]
        self.lbl_reloj.config(
            text=f"{dia} {ahora.strftime('%d/%m/%Y  %H:%M:%S')}"
        )
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

    # ── Registrar detección en historial ─────────────────────────────────────
    def _registrar_deteccion(self, resultado: dict, verificacion: dict):
        placa = resultado["placa"]
        ahora = datetime.now()

        # Anti-spam: ignorar si la misma placa se vio hace menos de COOLDOWN_SEG s
        ultimo = self._cooldown.get(placa)
        if ultimo and (ahora - ultimo).total_seconds() < COOLDOWN_SEG:
            return

        self._cooldown[placa] = ahora

        estado_txt = "❌ RESTRICCIÓN" if verificacion["restringido"] else "✅ PUEDE CIRCULAR"
        tag        = "restringido"    if verificacion["restringido"] else "libre"

        fila = {
            "hora"       : ahora.strftime("%H:%M:%S"),
            "placa"      : placa,
            "estado"     : estado_txt,
            "digito"     : str(verificacion["digito"]),
            "motor"      : resultado["motor"],
            "confianza"  : f"{resultado['confianza']}%",
            "restringido": verificacion["restringido"],
        }
        self._historial.append(fila)

        # Insertar al inicio (más reciente arriba)
        self.tree.insert(
            "", 0,
            values=(fila["hora"], fila["placa"], fila["estado"],
                    fila["digito"], fila["motor"], fila["confianza"]),
            tags=(tag,)
        )

        total = len(self._historial)
        sufijo = "s" if total != 1 else ""
        self.lbl_conteo.config(
            text=f"{total} vehículo{sufijo} detectado{sufijo}"
        )

        if verificacion["restringido"]:
            self.root.after(
                0, mostrar_multa, self.root, placa, ahora,
                self._agregar_multa_tabla
            )

    # ── Exportar CSV ──────────────────────────────────────────────────────────
    def _exportar_csv(self):
        if not self._historial:
            self._agregar_chat("Sistema", "No hay detecciones para exportar.", FG_YELLOW)
            return

        path = filedialog.asksaveasfilename(
            title="Guardar historial",
            defaultextension=".csv",
            initialfile=f"pico_placa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")]
        )
        if not path:
            return

        campos = ["hora", "placa", "estado", "digito", "motor", "confianza"]
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(self._historial)

        self._agregar_chat("Sistema", f"Historial exportado → {path}", FG_GREEN)

    # ── Limpiar historial ─────────────────────────────────────────────────────
    def _limpiar_historial(self):
        self._historial.clear()
        self._cooldown.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.lbl_conteo.config(text="0 vehículos detectados")

    # ── Procesar frame ────────────────────────────────────────────────────────
    def _procesar_frame(self, frame: np.ndarray):
        resultado = detectar_placa(frame)

        if resultado:
            x, y, w, h  = resultado["bbox"]
            fecha_hora   = datetime.now()
            verificacion = verificar(resultado["placa"], fecha_hora)
            self._ultimo = verificacion

            color = (0, 0, 220) if verificacion["restringido"] else (0, 200, 80)
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 3)
            cv2.putText(
                frame, resultado["placa"],
                (x, max(y - 12, 20)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2
            )

            self.lbl_placa.config(text=resultado["placa"])

            if verificacion["restringido"]:
                self.lbl_estado.config(text="❌  RESTRICCIÓN ACTIVA", fg=FG_RED)
            else:
                self.lbl_estado.config(text="✅  PUEDE CIRCULAR", fg=FG_GREEN)

            par = verificacion["par_hoy"]
            dia = DIAS[fecha_hora.weekday()]
            detalle = (
                f"Último dígito : {verificacion['digito']}\n"
                f"Par restringido: {f'{par[0]}-{par[1]}' if par else 'N/A'}\n"
                f"Día            : {dia} {fecha_hora.strftime('%d/%m/%Y')}\n"
                f"Horario        : 7:30 AM – 7:00 PM\n"
                f"Motor OCR      : {resultado['motor']}\n"
                f"Confianza      : {resultado['confianza']}%"
            )
            self.lbl_detalle.config(text=detalle)

            # Registrar en historial (con cooldown anti-spam)
            self._registrar_deteccion(resultado, verificacion)

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
                self._limpiar_panel()
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
            "par_hoy"   : f"{par[0]}-{par[1]}" if par and len(par) > 1 else "Sin restricción",
            "es_festivo": ahora.date() in FESTIVOS,
        }
        # Si hay una placa detectada activa, agregarla al contexto
        if self._ultimo:
            contexto["placa_detectada"] = self.lbl_placa.cget("text")
            contexto["digito"]          = self._ultimo.get("digito")
            contexto["restringido"]     = self._ultimo.get("restringido")
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
