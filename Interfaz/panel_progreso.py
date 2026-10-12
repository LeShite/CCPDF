"""
panel_progreso.py — Widget reutilizable: barra + etiqueta + Detener + log.

Usado por todas las vistas (extractor, fusionador, divisor, compresor).
"""
import customtkinter as ctk

COLOR_FONDO       = "#0F1218"
COLOR_ACENTO      = "#3B82F6"
COLOR_ACTIVO      = "#232A38"
COLOR_TEXTO_SUAVE = "#8A94A6"
COLOR_STOP        = "#EF4444"
COLOR_STOP_HOVER  = "#DC2626"

MAX_LINEAS_LOG = 2000


class PanelProgreso(ctk.CTkFrame):
    def __init__(self, master, altura_log: int = 130, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        fila = ctk.CTkFrame(self, fg_color="transparent")
        fila.pack(fill="x")
        self.lbl_progreso = ctk.CTkLabel(fila, text="Listo.", text_color=COLOR_TEXTO_SUAVE)
        self.lbl_progreso.pack(side="left")
        self.btn_stop = ctk.CTkButton(fila, text="⏹ Detener", width=90, height=28,
                                      state="disabled",
                                      fg_color=COLOR_STOP, hover_color=COLOR_STOP_HOVER)
        self.btn_stop.pack(side="right")

        self.barra = ctk.CTkProgressBar(self, fg_color=COLOR_ACTIVO,
                                        progress_color=COLOR_ACENTO, height=12)
        self.barra.pack(fill="x", pady=(6, 8))
        self.barra.set(0)

        self.txt_log = ctk.CTkTextbox(self, height=altura_log,
                                      fg_color=COLOR_FONDO, text_color=COLOR_TEXTO_SUAVE)
        self.txt_log.pack(fill="x")

    def set_progreso(self, actual: int, total: int, archivo: str):
        self.barra.set(actual / total if total else 0)
        self.lbl_progreso.configure(text=f"Procesado {actual} de {total}: {archivo}")

    def escribir_log(self, mensaje: str):
        self.txt_log.insert("end", mensaje + "\n")
        try:
            total = int(self.txt_log.index("end-1c").split(".")[0])
        except Exception:
            total = 0
        if total > MAX_LINEAS_LOG:
            self.txt_log.delete("1.0", f"{total - MAX_LINEAS_LOG}.0")
        self.txt_log.see("end")

    def limpiar_log(self):
        self.txt_log.delete("1.0", "end")

    def reset(self):
        self.barra.set(0)
        self.lbl_progreso.configure(text="Listo.")
