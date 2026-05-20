import csv
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime

from pico_y_placa import verificar, obtener_par_restringido
from holidays import FESTIVOS
from multa import mostrar_multa

BG_MAIN   = "#1e1e2e"
BG_PANEL  = "#2a2a3e"
BG_DARK   = "#12121e"
FG_WHITE  = "#ffffff"
FG_GRAY   = "#aaaacc"
FG_GREEN  = "#6bff9e"
FG_RED    = "#ff6b6b"
FG_YELLOW = "#ffd700"
BTN_BLUE  = "#4a90d9"
BTN_RED   = "#c0392b"
BTN_TEAL  = "#2a9d8f"

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
COOLDOWN_SEG = 5


class PicoPlacaApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self._historial: list[dict] = []
        self._multas: list[dict] = []
        self._cooldown: dict[str, datetime] = {}

        self.root.title("Pico y Placa — Pasto, Colombia")
        self.root.geometry("560x640")
        self.root.configure(bg=BG_MAIN)
        self.root.resizable(False, False)

        self._construir_ui()
        self._actualizar_reloj()

    def _construir_ui(self):
        tk.Label(
            self.root, text="Pico y Placa — Pasto, Colombia",
            bg=BG_MAIN, fg=FG_YELLOW, font=("Arial", 14, "bold")
        ).pack(pady=(12, 0))

        self.lbl_reloj = tk.Label(self.root, text="", bg=BG_MAIN, fg=FG_GRAY, font=("Arial", 10))
        self.lbl_reloj.pack()

        pnl = tk.Frame(self.root, bg=BG_PANEL)
        pnl.pack(fill=tk.X, padx=14, pady=(12, 0))

        tk.Label(pnl, text="Par restringido hoy:",
                 bg=BG_PANEL, fg=FG_GRAY, font=("Arial", 10)).pack(pady=(14, 0))
        self.lbl_par_actual = tk.Label(
            pnl, text="", bg=BG_PANEL, fg=FG_YELLOW, font=("Arial", 22, "bold")
        )
        self.lbl_par_actual.pack(pady=(2, 12))

        tk.Label(pnl, text="─" * 52, bg=BG_PANEL, fg="#444466").pack()

        tk.Label(pnl, text="Ingresar placa:", bg=BG_PANEL, fg=FG_GRAY, font=("Arial", 10)).pack(pady=(12, 4))

        fila = tk.Frame(pnl, bg=BG_PANEL)
        fila.pack(pady=(0, 8))

        self.ent_placa = tk.Entry(
            fila, bg=BG_DARK, fg=FG_WHITE,
            font=("Courier", 16, "bold"), insertbackground=FG_WHITE,
            bd=0, highlightthickness=1, highlightbackground="#555577",
            width=11, justify=tk.CENTER
        )
        self.ent_placa.pack(side=tk.LEFT, padx=(0, 8), ipady=6)
        self.ent_placa.bind("<Return>", lambda _: self._verificar_placa())

        tk.Button(
            fila, text="Verificar", bg=BTN_BLUE, fg=FG_WHITE,
            font=("Arial", 11, "bold"), bd=0, padx=16, pady=6,
            cursor="hand2", command=self._verificar_placa
        ).pack(side=tk.LEFT)

        self.lbl_placa = tk.Label(
            pnl, text="---", bg=BG_PANEL, fg=FG_WHITE, font=("Courier", 28, "bold")
        )
        self.lbl_placa.pack(pady=(12, 4))

        self.lbl_estado = tk.Label(
            pnl, text="Ingresa una placa para verificar",
            bg=BG_PANEL, fg=FG_GRAY, font=("Arial", 13, "bold"), wraplength=420
        )
        self.lbl_estado.pack(pady=4)

        self.lbl_detalle = tk.Label(
            pnl, text="", bg=BG_PANEL, fg=FG_GRAY,
            font=("Arial", 10), wraplength=420, justify=tk.LEFT
        )
        self.lbl_detalle.pack(pady=(4, 16), padx=14, anchor=tk.W)

        self._construir_tabs()

    def _construir_tabs(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Dark.TNotebook", background=BG_MAIN, borderwidth=0)
        style.configure("Dark.TNotebook.Tab",
                        background=BG_PANEL, foreground=FG_GRAY,
                        padding=[12, 5], font=("Arial", 10, "bold"))
        style.map("Dark.TNotebook.Tab",
                  background=[("selected", BTN_BLUE)],
                  foreground=[("selected", FG_WHITE)])

        nb = ttk.Notebook(self.root, style="Dark.TNotebook")
        nb.pack(fill=tk.BOTH, padx=14, pady=(8, 8), expand=True)

        tab_hist = tk.Frame(nb, bg=BG_PANEL)
        nb.add(tab_hist, text="Historial")
        self._construir_historial(tab_hist)

        tab_multas = tk.Frame(nb, bg=BG_PANEL)
        nb.add(tab_multas, text="Multas")
        self._construir_multas(tab_multas)

    def _construir_historial(self, parent):
        barra = tk.Frame(parent, bg=BG_PANEL)
        barra.pack(fill=tk.X, padx=10, pady=(8, 4))

        self.lbl_conteo = tk.Label(
            barra, text="0 vehículos verificados",
            bg=BG_PANEL, fg=FG_GRAY, font=("Arial", 10, "bold")
        )
        self.lbl_conteo.pack(side=tk.LEFT)

        tk.Button(
            barra, text="Limpiar", bg=BTN_RED, fg=FG_WHITE,
            font=("Arial", 9, "bold"), bd=0, padx=10, pady=3,
            cursor="hand2", command=self._limpiar_historial
        ).pack(side=tk.RIGHT, padx=(4, 0))

        tk.Button(
            barra, text="Exportar CSV", bg=BTN_TEAL, fg=FG_WHITE,
            font=("Arial", 9, "bold"), bd=0, padx=10, pady=3,
            cursor="hand2", command=self._exportar_csv
        ).pack(side=tk.RIGHT, padx=(4, 0))

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

        cols = ("hora", "placa", "estado", "digito")
        self.tree = ttk.Treeview(
            frame_tree, columns=cols, show="headings",
            style="Dark.Treeview", height=6
        )

        encabezados = {
            "hora"  : ("Hora",    90),
            "placa" : ("Placa",   90),
            "estado": ("Estado", 160),
            "digito": ("Dígito",  70),
        }
        for col, (texto, ancho) in encabezados.items():
            self.tree.heading(col, text=texto)
            self.tree.column(col, width=ancho, anchor=tk.CENTER)

        scroll_y = ttk.Scrollbar(frame_tree, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.tag_configure("libre",       foreground=FG_GREEN)
        self.tree.tag_configure("restringido", foreground=FG_RED)

    def _construir_multas(self, parent):
        barra = tk.Frame(parent, bg=BG_PANEL)
        barra.pack(fill=tk.X, padx=10, pady=(8, 4))

        self.lbl_conteo_multas = tk.Label(
            barra, text="0 multas generadas",
            bg=BG_PANEL, fg=FG_GRAY, font=("Arial", 10, "bold")
        )
        self.lbl_conteo_multas.pack(side=tk.LEFT)

        tk.Button(
            barra, text="Limpiar", bg=BTN_RED, fg=FG_WHITE,
            font=("Arial", 9, "bold"), bd=0, padx=10, pady=3,
            cursor="hand2", command=self._limpiar_multas
        ).pack(side=tk.RIGHT, padx=(4, 0))

        tk.Button(
            barra, text="Exportar CSV", bg=BTN_TEAL, fg=FG_WHITE,
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
            "hora"  : ("Hora",      90),
            "nombre": ("Infractor", 200),
            "placa" : ("Placa",    100),
            "monto" : ("Monto",    110),
        }
        for col, (texto, ancho) in encabezados.items():
            self.tree_multas.heading(col, text=texto)
            self.tree_multas.column(col, width=ancho, anchor=tk.CENTER)

        scroll_y = ttk.Scrollbar(frame_tree, orient=tk.VERTICAL, command=self.tree_multas.yview)
        self.tree_multas.configure(yscrollcommand=scroll_y.set)
        self.tree_multas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_multas.tag_configure("multa", foreground=FG_RED)

    def _actualizar_reloj(self):
        ahora = datetime.now()
        dia = DIAS[ahora.weekday()]
        self.lbl_reloj.config(text=f"{dia} {ahora.strftime('%d/%m/%Y  %H:%M:%S')}")
        par = obtener_par_restringido(ahora.date())
        if par:
            self.lbl_par_actual.config(text=f"{par[0]}  –  {par[1]}")
        else:
            self.lbl_par_actual.config(text="Sin restricción")
        self.root.after(1000, self._actualizar_reloj)

    def _verificar_placa(self):
        placa = self.ent_placa.get().strip().upper()
        if not placa:
            return

        fecha_hora = datetime.now()
        verificacion = verificar(placa, fecha_hora)

        self.lbl_placa.config(text=placa)

        if verificacion["restringido"]:
            self.lbl_estado.config(text="RESTRICCION ACTIVA", fg=FG_RED)
        else:
            self.lbl_estado.config(text="PUEDE CIRCULAR", fg=FG_GREEN)

        par = verificacion["par_hoy"]
        dia = DIAS[fecha_hora.weekday()]
        self.lbl_detalle.config(text=(
            f"Ultimo digito  : {verificacion['digito']}\n"
            f"Par restringido: {f'{par[0]}-{par[1]}' if par else 'N/A'}\n"
            f"Dia            : {dia} {fecha_hora.strftime('%d/%m/%Y')}\n"
            f"Horario        : 7:30 AM - 7:00 PM"
        ))

        self._registrar(placa, verificacion, fecha_hora)

    def _registrar(self, placa: str, verificacion: dict, fecha_hora: datetime):
        ultimo = self._cooldown.get(placa)
        if ultimo and (fecha_hora - ultimo).total_seconds() < COOLDOWN_SEG:
            return
        self._cooldown[placa] = fecha_hora

        estado_txt = "RESTRICCION" if verificacion["restringido"] else "PUEDE CIRCULAR"
        tag        = "restringido" if verificacion["restringido"] else "libre"

        fila = {
            "hora"  : fecha_hora.strftime("%H:%M:%S"),
            "placa" : placa,
            "estado": estado_txt,
            "digito": str(verificacion["digito"]),
        }
        self._historial.append(fila)

        self.tree.insert(
            "", 0,
            values=(fila["hora"], fila["placa"], fila["estado"], fila["digito"]),
            tags=(tag,)
        )
        total = len(self._historial)
        s = "s" if total != 1 else ""
        self.lbl_conteo.config(text=f"{total} vehículo{s} verificado{s}")

        if verificacion["restringido"]:
            self.root.after(0, mostrar_multa, self.root, placa, fecha_hora, self._agregar_multa_tabla)

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
        total = len(self._multas)
        s = "s" if total != 1 else ""
        self.lbl_conteo_multas.config(text=f"{total} multa{s} generada{s}")

    def _limpiar_historial(self):
        self._historial.clear()
        self._cooldown.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.lbl_conteo.config(text="0 vehículos verificados")

    def _limpiar_multas(self):
        self._multas.clear()
        for item in self.tree_multas.get_children():
            self.tree_multas.delete(item)
        self.lbl_conteo_multas.config(text="0 multas generadas")

    def _exportar_csv(self):
        if not self._historial:
            messagebox.showinfo("Exportar", "No hay detecciones para exportar.")
            return
        path = filedialog.asksaveasfilename(
            title="Guardar historial",
            defaultextension=".csv",
            initialfile=f"pico_placa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")]
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["hora", "placa", "estado", "digito"])
            writer.writeheader()
            writer.writerows(self._historial)

    def _exportar_multas_csv(self):
        if not self._multas:
            messagebox.showinfo("Exportar", "No hay multas para exportar.")
            return
        path = filedialog.asksaveasfilename(
            title="Guardar multas",
            defaultextension=".csv",
            initialfile=f"multas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")]
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["hora", "nombre", "placa", "monto"])
            writer.writeheader()
            writer.writerows(self._multas)

    def cerrar(self):
        self.root.destroy()
