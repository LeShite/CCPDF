"""
ccpdf_gui.py — Interfaz gráfica de CCpdf (CustomTkinter).

Estilo visual: Frutiger Aero + temas configurables en caliente.
Arquitectura de hilos:
  El hilo del motor SOLO deja mensajes en self.cola.
  _procesar_cola los consume en el hilo principal (Tkinter no es thread-safe).
"""
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from collections import namedtuple
from dataclasses import dataclass

from tkinter import filedialog, messagebox
import customtkinter as ctk


# ---------------------------------------------------------------------------
# RUTAS DEL PROYECTO
# ---------------------------------------------------------------------------
DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))
DIRECTORIO_PADRE  = os.path.dirname(DIRECTORIO_ACTUAL)

DIRECTORIO_MOTOR      = os.path.join(DIRECTORIO_PADRE, "Motores", "Extraccion")
DIRECTORIO_FUSION     = os.path.join(DIRECTORIO_PADRE, "Motores", "Fusion")
DIRECTORIO_DIVISION   = os.path.join(DIRECTORIO_PADRE, "Motores", "Division")
DIRECTORIO_COMPRESION = os.path.join(DIRECTORIO_PADRE, "Motores", "Compresion")
DIRECTORIO_VISOR      = os.path.join(DIRECTORIO_PADRE, "Motores", "Visualizacion")


def _preparar_path():
    for ruta in (DIRECTORIO_ACTUAL, DIRECTORIO_PADRE,
                 DIRECTORIO_MOTOR, DIRECTORIO_FUSION,
                 DIRECTORIO_DIVISION, DIRECTORIO_COMPRESION,
                 DIRECTORIO_VISOR):
        if ruta and os.path.isdir(ruta) and ruta not in sys.path:
            sys.path.insert(0, ruta)


_preparar_path()


def _ruta_recurso(relativa: str) -> str:
    """Resuelve rutas de recursos (logo, iconos) tanto en desarrollo como
    dentro del ejecutable empaquetado con PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = DIRECTORIO_PADRE
    return os.path.join(base, relativa)


# ---------------------------------------------------------------------------
# IMPORTS QUE DEPENDEN DE LAS RUTAS
# ---------------------------------------------------------------------------
import config as cfg_prefs
from dialogo_confirmar import mostrar_dialogo_confirmacion
from visor_pdf import VisorPDF


def _importar_extraccion():
    intentos = (
        "from pdf_motor import (cortar_hasta_palabra, clasificar_por_lista, "
        "limpiar_claves, leer_claves_txt, ErrorMotor)",
        "from Motores.Extraccion.pdf_motor import "
        "(cortar_hasta_palabra, clasificar_por_lista, limpiar_claves, "
        "leer_claves_txt, ErrorMotor)",
    )
    errores = []
    for sentencia in intentos:
        try:
            ns = {}
            exec(sentencia, ns)
            return (ns["cortar_hasta_palabra"], ns["clasificar_por_lista"],
                    ns["limpiar_claves"], ns["leer_claves_txt"], ns["ErrorMotor"])
        except ImportError as e:
            errores.append(f"  • {sentencia.split(' import ')[0]}  →  {e}")
    raise ImportError(
        "No se pudo importar el motor de extracción. Intentos:\n" + "\n".join(errores)
    )


def _importar_fusion():
    intentos = (
        "from pdf_fusionador import (fusionar_pdfs, listar_pdfs_carpeta, "
        "ordenar_natural, ErrorFusion, ResumenFusion)",
        "from Motores.Fusion.pdf_fusionador import "
        "(fusionar_pdfs, listar_pdfs_carpeta, ordenar_natural, ErrorFusion, ResumenFusion)",
    )
    errores = []
    for sentencia in intentos:
        try:
            ns = {}
            exec(sentencia, ns)
            return (ns["fusionar_pdfs"], ns["listar_pdfs_carpeta"],
                    ns["ordenar_natural"], ns["ErrorFusion"], ns["ResumenFusion"])
        except ImportError as e:
            errores.append(f"  • {sentencia.split(' import ')[0]}  →  {e}")
    raise ImportError(
        "No se pudo importar el motor de fusión. Intentos:\n" + "\n".join(errores)
    )


def _importar_divisor():
    intentos = (
        "from pdf_divisor import (dividir_por_unidad, leer_unidades_txt, "
        "ErrorDivisor, ResumenDivision)",
        "from Motores.Division.pdf_divisor import "
        "(dividir_por_unidad, leer_unidades_txt, ErrorDivisor, ResumenDivision)",
    )
    errores = []
    for sentencia in intentos:
        try:
            ns = {}
            exec(sentencia, ns)
            return (ns["dividir_por_unidad"], ns["leer_unidades_txt"],
                    ns["ErrorDivisor"], ns["ResumenDivision"])
        except ImportError as e:
            errores.append(f"  • {sentencia.split(' import ')[0]}  →  {e}")
    raise ImportError(
        "No se pudo importar el motor de división. Intentos:\n" + "\n".join(errores)
    )


def _importar_compresor():
    intentos = (
        "from pdf_compresor import (comprimir_pdfs, ErrorCompresion, "
        "ResumenCompresion, info_motor, NIVELES)",
        "from Motores.Compresion.pdf_compresor import "
        "(comprimir_pdfs, ErrorCompresion, ResumenCompresion, info_motor, NIVELES)",
    )
    errores = []
    for sentencia in intentos:
        try:
            ns = {}
            exec(sentencia, ns)
            return (ns["comprimir_pdfs"], ns["ErrorCompresion"],
                    ns["ResumenCompresion"], ns["info_motor"], ns["NIVELES"])
        except ImportError as e:
            errores.append(f"  • {sentencia.split(' import ')[0]}  →  {e}")
    raise ImportError(
        "No se pudo importar el motor de compresión. Intentos:\n" + "\n".join(errores)
    )


def _importar_visor():
    intentos = (
        "from visor_pdf_motor import (DocumentoPDF, abrir_pdf, ErrorVisor, "
        "InfoDocumento, ZOOM_MIN, ZOOM_MAX, ZOOM_DEFAULT)",
        "from Motores.Visualizacion.visor_pdf_motor import "
        "(DocumentoPDF, abrir_pdf, ErrorVisor, InfoDocumento, "
        "ZOOM_MIN, ZOOM_MAX, ZOOM_DEFAULT)",
    )
    errores = []
    for sentencia in intentos:
        try:
            ns = {}
            exec(sentencia, ns)
            return (ns["DocumentoPDF"], ns["abrir_pdf"], ns["ErrorVisor"],
                    ns["InfoDocumento"], ns["ZOOM_MIN"], ns["ZOOM_MAX"],
                    ns["ZOOM_DEFAULT"])
        except ImportError as e:
            errores.append(f"  • {sentencia.split(' import ')[0]}  →  {e}")
    raise ImportError(
        "No se pudo importar el motor de visor. Intentos:\n" + "\n".join(errores)
    )


(cortar_hasta_palabra, clasificar_por_lista,
 limpiar_claves, leer_claves_txt, ErrorMotor) = _importar_extraccion()

(fusionar_pdfs, listar_pdfs_carpeta,
 ordenar_natural, ErrorFusion, ResumenFusion) = _importar_fusion()

(dividir_por_unidad, leer_unidades_txt,
 ErrorDivisor, ResumenDivision) = _importar_divisor()

(comprimir_pdfs, ErrorCompresion,
 ResumenCompresion, info_motor, NIVELES_COMPRESION) = _importar_compresor()

(DocumentoPDF, abrir_pdf, ErrorVisor,
 InfoDocumento, ZOOM_MIN, ZOOM_MAX, ZOOM_DEFAULT) = _importar_visor()


# ---------------------------------------------------------------------------
# TEMA — carga desde preferencias y se puede cambiar en caliente
# ---------------------------------------------------------------------------
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

APP_NOMBRE  = "CCpdf"
APP_VERSION = "v0.8.1"

_PREFS = cfg_prefs.cargar()
_IDIOMA_ACTIVO = _PREFS["idioma"]
_TEMA_ACTIVO   = _PREFS["tema"]


def T(clave: str, defecto: str = "") -> str:
    """Traduce una clave al idioma activo."""
    return cfg_prefs.idioma(_IDIOMA_ACTIVO).get(clave, defecto or clave)


_t = cfg_prefs.tema(_TEMA_ACTIVO)

COLOR_FONDO          = _t["fondo"]
COLOR_SIDEBAR        = _t["sidebar"]
COLOR_TARJETA        = _t["tarjeta"]
COLOR_TARJETA_HOVER  = _t["tarjeta_hover"]
COLOR_ACTIVO         = _t["activo"]
COLOR_HOVER_SIDEBAR  = _t["hover_sidebar"]
COLOR_BORDER         = _t["border"]
COLOR_BORDER_SUAVE   = _t["border_suave"]

COLOR_ACENTO         = _t["acento"]
COLOR_ACENTO_HOVER   = _t["acento_hover"]
COLOR_ACENTO_SUAVE   = _t["acento_suave"]
COLOR_AQUA           = _t["aqua"]
COLOR_LIMA           = _t["lima"]

COLOR_TEXTO          = _t["texto"]
COLOR_TEXTO_SUAVE    = _t["texto_suave"]
COLOR_TEXTO_TENUE    = _t["texto_tenue"]
COLOR_TEXTO_BLANCO   = _t["texto_blanco"]

COLOR_OK             = _t["ok"]
COLOR_OK_HOVER       = _t["ok_hover"]
COLOR_STOP           = _t["stop"]
COLOR_STOP_HOVER     = _t["stop_hover"]

COLOR_EXTRAER        = _t["color_extraer"]
COLOR_FUSIONAR       = _t["color_fusionar"]
COLOR_DIVIDIR        = _t["color_dividir"]
COLOR_COMPRIMIR      = _t["color_comprimir"]
COLOR_VISOR          = _t["color_visor"]
COLOR_FIRMAR         = _t["color_firmar"]

APP_SUBTITULO        = T("app_subtitulo", "Suite local de PDF")

MAX_LINEAS_LOG = 2000
MAX_MENSAJES_POR_TICK = 200
INTERVALO_COLA_MS = 80
NOMBRE_FUSIONADO_DEFECTO = "fusionado.pdf"


def _aplicar_paleta(tema_dict: dict):
    """Actualiza las variables globales de color en caliente."""
    global COLOR_FONDO, COLOR_SIDEBAR, COLOR_TARJETA, COLOR_TARJETA_HOVER
    global COLOR_ACTIVO, COLOR_HOVER_SIDEBAR, COLOR_BORDER, COLOR_BORDER_SUAVE
    global COLOR_ACENTO, COLOR_ACENTO_HOVER, COLOR_ACENTO_SUAVE
    global COLOR_AQUA, COLOR_LIMA
    global COLOR_TEXTO, COLOR_TEXTO_SUAVE, COLOR_TEXTO_TENUE, COLOR_TEXTO_BLANCO
    global COLOR_OK, COLOR_OK_HOVER, COLOR_STOP, COLOR_STOP_HOVER
    global COLOR_EXTRAER, COLOR_FUSIONAR, COLOR_DIVIDIR, COLOR_COMPRIMIR
    global COLOR_VISOR, COLOR_FIRMAR

    COLOR_FONDO         = tema_dict["fondo"]
    COLOR_SIDEBAR       = tema_dict["sidebar"]
    COLOR_TARJETA       = tema_dict["tarjeta"]
    COLOR_TARJETA_HOVER = tema_dict["tarjeta_hover"]
    COLOR_ACTIVO        = tema_dict["activo"]
    COLOR_HOVER_SIDEBAR = tema_dict["hover_sidebar"]
    COLOR_BORDER        = tema_dict["border"]
    COLOR_BORDER_SUAVE  = tema_dict["border_suave"]
    COLOR_ACENTO        = tema_dict["acento"]
    COLOR_ACENTO_HOVER  = tema_dict["acento_hover"]
    COLOR_ACENTO_SUAVE  = tema_dict["acento_suave"]
    COLOR_AQUA          = tema_dict["aqua"]
    COLOR_LIMA          = tema_dict["lima"]
    COLOR_TEXTO         = tema_dict["texto"]
    COLOR_TEXTO_SUAVE   = tema_dict["texto_suave"]
    COLOR_TEXTO_TENUE   = tema_dict["texto_tenue"]
    COLOR_TEXTO_BLANCO  = tema_dict["texto_blanco"]
    COLOR_OK            = tema_dict["ok"]
    COLOR_OK_HOVER      = tema_dict["ok_hover"]
    COLOR_STOP          = tema_dict["stop"]
    COLOR_STOP_HOVER    = tema_dict["stop_hover"]
    COLOR_EXTRAER       = tema_dict["color_extraer"]
    COLOR_FUSIONAR      = tema_dict["color_fusionar"]
    COLOR_DIVIDIR       = tema_dict["color_dividir"]
    COLOR_COMPRIMIR     = tema_dict["color_comprimir"]
    COLOR_VISOR         = tema_dict["color_visor"]
    COLOR_FIRMAR        = tema_dict["color_firmar"]


def _aplicar_idioma(codigo: str):
    global _IDIOMA_ACTIVO
    _IDIOMA_ACTIVO = codigo


# ---------------------------------------------------------------------------
# MODELO DE MÓDULOS
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Modulo:
    clave: str
    emoji: str
    titulo: str
    descripcion: str
    color: str = COLOR_ACENTO
    subtitulo: str = ""

    @property
    def etiqueta(self) -> str:
        return f"{self.emoji}   {self.titulo}"


def _construir_modulos():
    return (
        Modulo("inicio",     "🏠", T("mod_inicio"),     T("mod_inicio_desc")),
        Modulo("extractor",  "📁", T("mod_extractor"),  T("mod_extractor_desc"),
               color=COLOR_EXTRAER, subtitulo=T("mod_extractor_sub")),
        Modulo("fusionador", "🧩", T("mod_fusionador"), T("mod_fusionador_desc"),
               color=COLOR_FUSIONAR, subtitulo=T("mod_fusionador_sub")),
        Modulo("divisor",    "✂️", T("mod_divisor"),    T("mod_divisor_desc"),
               color=COLOR_DIVIDIR, subtitulo=T("mod_divisor_sub")),
        Modulo("compresor",  "🗜️", T("mod_compresor"),  T("mod_compresor_desc"),
               color=COLOR_COMPRIMIR, subtitulo=T("mod_compresor_sub")),
        Modulo("visor",      "👁️", T("mod_visor"),      T("mod_visor_desc"),
               color=COLOR_VISOR, subtitulo=T("mod_visor_sub")),
        Modulo("firmar",     "✍️", T("mod_firmar"),     T("mod_firmar_desc"),
               color=COLOR_FIRMAR, subtitulo=T("mod_firmar_sub")),
    )


MODULOS = _construir_modulos()
MODULO_POR_CLAVE = {m.clave: m for m in MODULOS}


# ---------------------------------------------------------------------------
# MENSAJES DE LA COLA
# ---------------------------------------------------------------------------
MsgProgreso = namedtuple("MsgProgreso", "actual total archivo")
MsgLog      = namedtuple("MsgLog", "texto")
MsgFin      = namedtuple("MsgFin", "resumen error")
MsgPregunta = namedtuple("MsgPregunta", "valor unidad paginas indice total respuesta listo")


# ---------------------------------------------------------------------------
# UTILIDADES
# ---------------------------------------------------------------------------
def abrir_carpeta(ruta: str) -> None:
    if not ruta or not os.path.isdir(ruta):
        return
    try:
        if sys.platform.startswith("win"):
            os.startfile(ruta)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", ruta],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(["xdg-open", ruta],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        messagebox.showwarning("No se pudo abrir la carpeta", str(e))


def _attr(obj, nombre, default=""):
    return getattr(obj, nombre, default)


def _oscurecer(hex_color: str, factor: float) -> str:
    try:
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        r = max(0, int(r * (1 - factor)))
        g = max(0, int(g * (1 - factor)))
        b = max(0, int(b * (1 - factor)))
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return hex_color


# ---------------------------------------------------------------------------
# WIDGET: PANEL DE PROGRESO
# ---------------------------------------------------------------------------
class PanelProgreso(ctk.CTkFrame):
    def __init__(self, master, altura_log: int = 130, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        fila = ctk.CTkFrame(self, fg_color="transparent")
        fila.pack(fill="x")
        self.lbl_progreso = ctk.CTkLabel(fila, text=T("listo", "Listo."),
                                         text_color=COLOR_TEXTO_SUAVE,
                                         font=ctk.CTkFont(size=12))
        self.lbl_progreso.pack(side="left")
        self.btn_stop = ctk.CTkButton(fila, text=T("detener", "⏹  Detener"),
                                      width=100, height=30,
                                      corner_radius=15, state="disabled",
                                      fg_color=COLOR_STOP, hover_color=COLOR_STOP_HOVER,
                                      text_color=COLOR_TEXTO_BLANCO,
                                      font=ctk.CTkFont(size=12, weight="bold"))
        self.btn_stop.pack(side="right")

        self.barra = ctk.CTkProgressBar(self, fg_color=COLOR_BORDER_SUAVE,
                                        progress_color=COLOR_ACENTO, height=12,
                                        corner_radius=6)
        self.barra.pack(fill="x", pady=(8, 10))
        self.barra.set(0)

        self.txt_log = ctk.CTkTextbox(self, height=altura_log,
                                      fg_color="#F8FCFF", text_color=COLOR_TEXTO_SUAVE,
                                      border_width=1, border_color=COLOR_BORDER,
                                      corner_radius=10,
                                      font=ctk.CTkFont(family="monospace", size=11))
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
        self.lbl_progreso.configure(text=T("listo", "Listo."))


# ---------------------------------------------------------------------------
# TARJETA DE MÓDULO
# ---------------------------------------------------------------------------
class TarjetaModulo(ctk.CTkFrame):
    def __init__(self, master, mod: Modulo, al_abrir):
        super().__init__(master, corner_radius=20, fg_color=COLOR_TARJETA,
                         border_width=2, border_color=COLOR_BORDER_SUAVE)
        self._mod = mod
        self._al_abrir = al_abrir

        cab = ctk.CTkFrame(self, height=6, corner_radius=3, fg_color=mod.color)
        cab.pack(fill="x", padx=16, pady=(16, 0))

        ctk.CTkLabel(self, text=mod.emoji, font=ctk.CTkFont(size=38)
                     ).pack(anchor="w", padx=20, pady=(14, 4))

        ctk.CTkLabel(self, text=mod.titulo,
                     font=ctk.CTkFont(size=17, weight="bold"),
                     text_color=COLOR_TEXTO, anchor="w"
                     ).pack(anchor="w", padx=20)

        ctk.CTkLabel(self, text=mod.descripcion,
                     text_color=COLOR_TEXTO_SUAVE,
                     font=ctk.CTkFont(size=12), wraplength=220,
                     justify="left", anchor="w"
                     ).pack(anchor="w", padx=20, pady=(6, 0))

        self._btn = ctk.CTkButton(self, text=T("abrir", "Abrir") + "  →", height=38,
                                  corner_radius=19,
                                  fg_color=mod.color,
                                  hover_color=_oscurecer(mod.color, 0.18),
                                  text_color=COLOR_TEXTO_BLANCO,
                                  font=ctk.CTkFont(size=13, weight="bold"),
                                  command=lambda: self._al_abrir(self._mod.clave))
        self._btn.pack(fill="x", padx=20, pady=(18, 20))

        for w in (self, *self.winfo_children()):
            w.bind("<Enter>", self._on_enter, add="+")
            w.bind("<Leave>", self._on_leave, add="+")

    def _on_enter(self, _e=None):
        self.configure(fg_color=COLOR_TARJETA_HOVER, border_color=self._mod.color)

    def _on_leave(self, event=None):
        try:
            x, y = self.winfo_pointerxy()
            under = self.winfo_containing(x, y)
            w = under
            while w is not None:
                if w == self:
                    return
                try:
                    w = w.master
                except Exception:
                    break
        except Exception:
            pass
        self.configure(fg_color=COLOR_TARJETA, border_color=COLOR_BORDER_SUAVE)


# ---------------------------------------------------------------------------
# APLICACIÓN
# ---------------------------------------------------------------------------
class CCPdfApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NOMBRE} — {APP_SUBTITULO}")
        self.geometry("1180x820")
        self.minsize(1000, 720)
        self.configure(fg_color=COLOR_FONDO)
        self._aplicar_icono_ventana()
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.botones_nav: dict[str, ctk.CTkButton] = {}
        self._indicadores: dict[str, ctk.CTkFrame] = {}
        self.vistas: dict[str, ctk.CTkFrame] = {}
        self.evento_cancelar = threading.Event()
        self.cola: queue.Queue = queue.Queue()
        self._procesando = False
        self._after_id = None
        self._panel_activo: PanelProgreso | None = None
        self._clave_actual = "inicio"

        self._lista_fusion: list[str] = []
        self._lista_compresion: list[str] = []

        self._crear_sidebar()
        self._crear_area_contenido()
        self.mostrar_vista("inicio")

        self.protocol("WM_DELETE_WINDOW", self._al_cerrar)
        self._procesar_cola()

    # ---------- ICONO DE VENTANA ----------
    def _aplicar_icono_ventana(self):
        """Pone el logo como icono de la barra de título y de la taskbar."""
        try:
            png = _ruta_recurso("Interfaz/assets/logo.png")
            ico = _ruta_recurso("Interfaz/assets/logo.ico")

            if sys.platform.startswith("win"):
                if os.path.isfile(ico):
                    self.iconbitmap(ico)
            else:
                if os.path.isfile(png):
                    from PIL import Image, ImageTk
                    img = Image.open(png).convert("RGBA")
                    fotos = [
                        ImageTk.PhotoImage(img.resize((n, n), Image.LANCZOS))
                        for n in (16, 32, 48, 64, 128, 256)
                    ]
                    self.iconphoto(True, *fotos)
                    self._iconos_ref = fotos
        except Exception as e:
            print(f"[AVISO] No se pudo aplicar el icono: {e}")

    # ---------- SIDEBAR ----------
    def _crear_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0,
                                    fg_color=COLOR_SIDEBAR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        header.grid(row=0, column=0, padx=22, pady=(30, 26), sticky="ew")

        logo_cargado = False
        try:
            from PIL import Image
            ruta_logo = _ruta_recurso("Interfaz/assets/logo.png")
            if os.path.isfile(ruta_logo):
                pil = Image.open(ruta_logo).convert("RGBA")
                pil = pil.resize((52, 52), Image.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=pil, dark_image=pil,
                                       size=(52, 52))
                lbl_logo = ctk.CTkLabel(header, image=ctk_img, text="")
                lbl_logo.pack(side="left")
                lbl_logo._ctk_img_ref = ctk_img
                logo_cargado = True
        except Exception as e:
            print(f"[AVISO] Logo no cargado en sidebar: {e}")

        if not logo_cargado:
            logo_marco = ctk.CTkFrame(header, width=56, height=56, corner_radius=28,
                                      fg_color=COLOR_TEXTO_BLANCO,
                                      border_width=3, border_color=COLOR_ACENTO)
            logo_marco.pack(side="left")
            logo_marco.pack_propagate(False)
            ctk.CTkLabel(logo_marco, text="CC",
                         font=ctk.CTkFont(size=22, weight="bold"),
                         text_color=COLOR_ACENTO).pack(expand=True)

        textos = ctk.CTkFrame(header, fg_color="transparent")
        textos.pack(side="left", padx=(14, 0))
        ctk.CTkLabel(textos, text=APP_NOMBRE,
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=COLOR_TEXTO, anchor="w").pack(anchor="w")
        ctk.CTkLabel(textos, text=APP_VERSION,
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLOR_ACENTO, anchor="w").pack(anchor="w")

        ctk.CTkFrame(self.sidebar, height=2, fg_color=COLOR_TEXTO_BLANCO
                     ).grid(row=1, column=0, padx=22, sticky="ew", pady=(0, 14))

        nav = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav.grid(row=2, column=0, sticky="ew")

        for mod in MODULOS:
            fila = ctk.CTkFrame(nav, fg_color="transparent", height=46)
            fila.pack(fill="x", padx=12, pady=2)
            fila.pack_propagate(False)

            indicador = ctk.CTkFrame(fila, width=4, corner_radius=2,
                                     fg_color=COLOR_ACENTO)
            indicador.pack(side="left", fill="y", pady=6)
            indicador.pack_forget()
            self._indicadores[mod.clave] = indicador

            btn = ctk.CTkButton(
                fila, text=mod.etiqueta, anchor="w", height=46, corner_radius=23,
                fg_color="transparent", hover_color=COLOR_HOVER_SIDEBAR,
                font=ctk.CTkFont(size=13),
                text_color=COLOR_TEXTO,
                command=lambda c=mod.clave: self.mostrar_vista(c),
            )
            btn.pack(side="left", fill="both", expand=True, padx=(6, 0))
            self.botones_nav[mod.clave] = btn

        self.sidebar.grid_rowconfigure(3, weight=1)

        pie = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        pie.grid(row=4, column=0, padx=16, pady=(0, 20), sticky="ew")

        self.btn_config = ctk.CTkButton(
            pie, text="⚙️    " + T("configuracion", "Configuración"),
            anchor="w", height=44, corner_radius=22,
            fg_color=COLOR_TARJETA, hover_color=COLOR_ACTIVO,
            text_color=COLOR_TEXTO,
            font=ctk.CTkFont(size=13, weight="bold"),
            border_width=2, border_color=COLOR_BORDER,
            command=self._abrir_config,
        )
        self.btn_config.pack(fill="x", pady=(0, 12))

        info = ctk.CTkFrame(pie, fg_color="transparent")
        info.pack(fill="x")
        ctk.CTkLabel(info, text=T("todo_local", "☁  Todo local, sin nube"),
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=COLOR_TEXTO_BLANCO, anchor="w").pack(anchor="w")
        ctk.CTkLabel(info, text=T("todo_local_sub", "Tus PDFs nunca salen de tu equipo"),
                     font=ctk.CTkFont(size=9),
                     text_color=COLOR_TEXTO, anchor="w").pack(anchor="w")

    # ---------- ÁREA DE CONTENIDO ----------
    def _crear_area_contenido(self):
        wrapper = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        wrapper.grid(row=0, column=1, sticky="nsew")
        wrapper.grid_columnconfigure(0, weight=1)
        wrapper.grid_rowconfigure(1, weight=1)

        cab = ctk.CTkFrame(wrapper, fg_color="transparent")
        cab.grid(row=0, column=0, sticky="ew", padx=36, pady=(30, 4))

        self.icono_titulo = ctk.CTkLabel(cab, text="", font=ctk.CTkFont(size=28))
        self.icono_titulo.pack(side="left", padx=(0, 14))

        textos_cab = ctk.CTkFrame(cab, fg_color="transparent")
        textos_cab.pack(side="left", fill="x", expand=True)

        self.titulo = ctk.CTkLabel(textos_cab, text="",
                                   font=ctk.CTkFont(size=24, weight="bold"),
                                   text_color=COLOR_TEXTO, anchor="w")
        self.titulo.pack(anchor="w")

        self.subtitulo = ctk.CTkLabel(textos_cab, text="",
                                      font=ctk.CTkFont(size=12),
                                      text_color=COLOR_TEXTO_SUAVE, anchor="w")
        self.subtitulo.pack(anchor="w")

        sep = ctk.CTkFrame(wrapper, height=2, fg_color=COLOR_ACENTO_SUAVE)
        sep.grid(row=0, column=0, sticky="ews", padx=36, pady=(94, 0))

        self.contenido = ctk.CTkFrame(wrapper, corner_radius=0, fg_color="transparent")
        self.contenido.grid(row=1, column=0, sticky="nsew", padx=36, pady=26)
        self.contenido.grid_columnconfigure(0, weight=1)
        self.contenido.grid_rowconfigure(0, weight=1)

        self.vistas["inicio"]     = self._vista_inicio()
        self.vistas["extractor"]  = self._vista_extractor()
        self.vistas["fusionador"] = self._vista_fusionador()
        self.vistas["divisor"]    = self._vista_divisor()
        self.vistas["compresor"]  = self._vista_compresor()
        self.vistas["visor"]      = self._vista_visor()
        self.vistas["firmar"]     = self._vista_placeholder(MODULO_POR_CLAVE["firmar"])

    # ---------- VISTA: INICIO ----------
    def _vista_inicio(self):
        frame = ctk.CTkFrame(self.contenido, fg_color="transparent")

        bienvenida = ctk.CTkFrame(frame, corner_radius=22, fg_color=COLOR_TARJETA,
                                  border_width=2, border_color=COLOR_BORDER_SUAVE)
        bienvenida.pack(fill="x", pady=(0, 24))

        ctk.CTkFrame(bienvenida, height=6, corner_radius=3,
                     fg_color=COLOR_ACENTO
                     ).pack(fill="x", padx=18, pady=(18, 0))

        ctk.CTkLabel(bienvenida, text=T("bienvenida_titulo", "Bienvenido a CCpdf  🌊"),
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=COLOR_TEXTO, anchor="w"
                     ).pack(anchor="w", padx=26, pady=(16, 4))
        ctk.CTkLabel(bienvenida,
                     text=T("bienvenida_texto",
                            "Herramientas locales para trabajar con PDFs sin subirlos a ningún servidor. "
                            "Elige un módulo para empezar."),
                     font=ctk.CTkFont(size=12), text_color=COLOR_TEXTO_SUAVE,
                     wraplength=780, justify="left", anchor="w"
                     ).pack(anchor="w", padx=26, pady=(0, 22))

        tarjetas = ctk.CTkFrame(frame, fg_color="transparent")
        tarjetas.pack(fill="both", expand=True)

        mods = [m for m in MODULOS if m.clave != "inicio"]
        columnas = 3
        for i in range(columnas):
            tarjetas.grid_columnconfigure(i, weight=1, uniform="tarjeta")

        for i, mod in enumerate(mods):
            fila, col = divmod(i, columnas)
            tarjeta = TarjetaModulo(tarjetas, mod, self.mostrar_vista)
            tarjeta.grid(row=fila, column=col, padx=8, pady=8, sticky="nsew")

        return frame

    def _vista_placeholder(self, mod: Modulo):
        frame = ctk.CTkFrame(self.contenido, corner_radius=22, fg_color=COLOR_TARJETA,
                             border_width=2, border_color=COLOR_BORDER_SUAVE)
        interior = ctk.CTkFrame(frame, fg_color="transparent")
        interior.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(interior, text=mod.emoji, font=ctk.CTkFont(size=56)
                     ).pack(pady=(0, 8))
        ctk.CTkLabel(interior, text=mod.titulo,
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=COLOR_TEXTO).pack()
        ctk.CTkLabel(interior, text=T("en_desarrollo", "En desarrollo"),
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=mod.color).pack(pady=(4, 0))
        return frame

    # ---------- VISTA: VISOR PDF ----------
    def _vista_visor(self):
        frame = ctk.CTkFrame(self.contenido, corner_radius=22, fg_color=COLOR_TARJETA,
                             border_width=2, border_color=COLOR_BORDER_SUAVE)
        self.visor = VisorPDF(frame)
        self.visor.pack(fill="both", expand=True, padx=12, pady=12)
        return frame

    # ---------- HELPERS COMUNES ----------
    def _campo(self, master, placeholder, height=40, **kw):
        return ctk.CTkEntry(
            master, placeholder_text=placeholder, height=height,
            corner_radius=20, border_color=COLOR_BORDER, fg_color="#FFFFFF",
            text_color=COLOR_TEXTO, placeholder_text_color=COLOR_TEXTO_TENUE,
            **kw)

    def _btn_azul(self, master, texto, comando, ancho=140):
        return ctk.CTkButton(
            master, text=texto, width=ancho, height=40, corner_radius=20,
            fg_color=COLOR_ACENTO, hover_color=COLOR_ACENTO_HOVER,
            text_color=COLOR_TEXTO_BLANCO,
            font=ctk.CTkFont(size=12, weight="bold"), command=comando)

    def _btn_verde(self, master, texto, comando):
        return ctk.CTkButton(
            master, text=texto, height=46, corner_radius=23,
            fg_color=COLOR_OK, hover_color=COLOR_OK_HOVER,
            text_color=COLOR_TEXTO_BLANCO,
            font=ctk.CTkFont(size=14, weight="bold"), command=comando)

    def _btn_rojo(self, master, texto, comando, ancho=100):
        return ctk.CTkButton(
            master, text=texto, width=ancho, height=40, corner_radius=20,
            fg_color=COLOR_STOP, hover_color=COLOR_STOP_HOVER,
            text_color=COLOR_TEXTO_BLANCO,
            font=ctk.CTkFont(size=12, weight="bold"), command=comando)

    def _btn_suave(self, master, texto, comando, ancho=120):
        return ctk.CTkButton(
            master, text=texto, width=ancho, height=40, corner_radius=20,
            fg_color=COLOR_BORDER_SUAVE, hover_color=COLOR_HOVER_SIDEBAR,
            text_color=COLOR_TEXTO,
            font=ctk.CTkFont(size=12, weight="bold"), command=comando)

    def _card(self, master):
        return ctk.CTkFrame(master, corner_radius=22, fg_color=COLOR_TARJETA,
                            border_width=2, border_color=COLOR_BORDER_SUAVE)

    def _checkbox(self, master, texto):
        return ctk.CTkCheckBox(
            master, text=texto, fg_color=COLOR_ACENTO,
            hover_color=COLOR_ACENTO_HOVER, text_color=COLOR_TEXTO,
            border_color=COLOR_ACENTO, checkmark_color=COLOR_TEXTO_BLANCO,
            font=ctk.CTkFont(size=12))

    # ---------- VISTA: EXTRACCIÓN AVANZADA ----------
    def _vista_extractor(self):
        frame = self._card(self.contenido)

        f_origen = ctk.CTkFrame(frame, fg_color="transparent")
        f_origen.pack(fill="x", padx=26, pady=(22, 8))
        self.entry_origen = self._campo(f_origen, "Directorio de PDFs origen")
        self.entry_origen.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._btn_azul(f_origen, T("explorar", "📂  Explorar"),
                       lambda: self._sel_carpeta(self.entry_origen)).pack(side="right")

        f_destino = ctk.CTkFrame(frame, fg_color="transparent")
        f_destino.pack(fill="x", padx=26, pady=8)
        self.entry_destino = self._campo(f_destino, "Directorio de salida (opcional)")
        self.entry_destino.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._btn_azul(f_destino, T("explorar", "📂  Explorar"),
                       lambda: self._sel_carpeta(self.entry_destino)).pack(side="right")

        self.panel_extractor = PanelProgreso(frame, altura_log=130)
        self.panel_extractor.pack(side="bottom", fill="x", padx=26, pady=(0, 22))
        self.panel_extractor.btn_stop.configure(command=self._detener)

        self.tabs = ctk.CTkTabview(
            frame, fg_color="transparent",
            segmented_button_selected_color=COLOR_ACENTO,
            segmented_button_selected_hover_color=COLOR_ACENTO_HOVER,
            segmented_button_unselected_color=COLOR_BORDER_SUAVE,
            segmented_button_unselected_hover_color=COLOR_HOVER_SIDEBAR,
            text_color=COLOR_TEXTO)
        self.tabs.pack(fill="both", expand=True, padx=26, pady=8)
        tab_firma = self.tabs.add("✂️  Corte hasta palabra")
        tab_lista = self.tabs.add("🗂️  Clasificador por lista")

        ctk.CTkLabel(tab_firma,
                     text="Crea un PDF desde la página 1 hasta la primera página que contenga el texto.",
                     text_color=COLOR_TEXTO_SUAVE,
                     font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(8, 0))
        self.entry_k1 = self._campo(tab_firma, "Texto donde detener el corte (requerido)")
        self.entry_k1.pack(fill="x", pady=(12, 6))
        self.entry_k2 = self._campo(tab_firma, "Segundo texto en la misma página (opcional)")
        self.entry_k2.pack(fill="x", pady=6)
        self.chk_fuzzy_1 = self._checkbox(tab_firma, "Tolerancia ortográfica (Fuzzy)")
        self.chk_fuzzy_1.select()
        self.chk_fuzzy_1.pack(anchor="w", pady=(12, 4))
        self.chk_palabra_1 = self._checkbox(tab_firma, "Solo palabra completa (desactiva la tolerancia)")
        self.chk_palabra_1.pack(anchor="w", pady=4)
        self.btn_run_1 = self._btn_verde(tab_firma, "▶   Ejecutar corte",
                                         lambda: self._iniciar_extraccion("firma"))
        self.btn_run_1.pack(fill="x", pady=14)

        f_top = ctk.CTkFrame(tab_lista, fg_color="transparent")
        f_top.pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(f_top,
                     text="Palabras a buscar (una por línea). Cada página que coincida se guarda aparte:",
                     text_color=COLOR_TEXTO_SUAVE,
                     font=ctk.CTkFont(size=12)).pack(side="left")
        self._btn_azul(f_top, T("cargar_txt", "📄  Cargar .txt"),
                       self._cargar_txt, ancho=150).pack(side="right")
        self.txt_lista = ctk.CTkTextbox(
            tab_lista, fg_color="#F8FCFF", height=100, corner_radius=10,
            border_width=1, border_color=COLOR_BORDER, text_color=COLOR_TEXTO,
            font=ctk.CTkFont(family="monospace", size=11))
        self.txt_lista.pack(fill="both", expand=True, pady=8)
        self.chk_fuzzy_2 = self._checkbox(tab_lista, "Tolerancia ortográfica (Fuzzy)")
        self.chk_fuzzy_2.pack(anchor="w", pady=(6, 4))
        self.chk_palabra_2 = self._checkbox(tab_lista, "Solo palabra completa (recomendado para folios y números)")
        self.chk_palabra_2.pack(anchor="w", pady=4)
        self.btn_run_2 = self._btn_verde(tab_lista, "▶   Ejecutar clasificación",
                                         lambda: self._iniciar_extraccion("lista"))
        self.btn_run_2.pack(fill="x", pady=8)

        return frame

    # ---------- VISTA: FUSIONADOR ----------
    def _vista_fusionador(self):
        frame = self._card(self.contenido)

        barra = ctk.CTkFrame(frame, fg_color="transparent")
        barra.pack(fill="x", padx=26, pady=(22, 8))

        self._btn_azul(barra, "➕  Añadir PDFs", self._fusion_add_pdfs,
                       ancho=150).pack(side="left", padx=(0, 6))
        self._btn_azul(barra, "📁  Añadir carpeta", self._fusion_add_carpeta,
                       ancho=170).pack(side="left", padx=6)
        ctk.CTkButton(barra, text="⬆", width=44, height=40, corner_radius=20,
                      fg_color=COLOR_BORDER_SUAVE, hover_color=COLOR_HOVER_SIDEBAR,
                      text_color=COLOR_TEXTO, font=ctk.CTkFont(size=14, weight="bold"),
                      command=lambda: self._fusion_mover(-1)).pack(side="left", padx=6)
        ctk.CTkButton(barra, text="⬇", width=44, height=40, corner_radius=20,
                      fg_color=COLOR_BORDER_SUAVE, hover_color=COLOR_HOVER_SIDEBAR,
                      text_color=COLOR_TEXTO, font=ctk.CTkFont(size=14, weight="bold"),
                      command=lambda: self._fusion_mover(+1)).pack(side="left", padx=(0, 6))
        self._btn_rojo(barra, "🗑  Quitar", self._fusion_quitar,
                       ancho=110).pack(side="left", padx=6)
        self._btn_suave(barra, "Limpiar lista", self._fusion_limpiar,
                        ancho=130).pack(side="right")

        self._fusion_listbox = tk.Listbox(
            frame, selectmode=tk.EXTENDED, activestyle="none",
            bg="#F8FCFF", fg=COLOR_TEXTO, selectbackground=COLOR_ACENTO,
            selectforeground=COLOR_TEXTO_BLANCO, highlightthickness=1,
            highlightbackground=COLOR_BORDER, highlightcolor=COLOR_ACENTO,
            borderwidth=0, relief="flat",
            font=("Segoe UI", 10), height=9,
        )
        self._fusion_listbox.pack(fill="both", expand=True, padx=26, pady=(8, 6))

        self.lbl_fusion_count = ctk.CTkLabel(frame, text="0 archivos en la lista.",
                                             text_color=COLOR_TEXTO_SUAVE,
                                             font=ctk.CTkFont(size=11))
        self.lbl_fusion_count.pack(anchor="w", padx=30)

        ctk.CTkLabel(frame, text="¿Dónde guardar el PDF fusionado?",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=COLOR_TEXTO).pack(anchor="w", padx=30, pady=(16, 4))

        f_salida = ctk.CTkFrame(frame, fg_color="transparent")
        f_salida.pack(fill="x", padx=26, pady=(0, 2))
        self.var_salida_fusion = tk.StringVar()
        self.entry_salida_fusion = ctk.CTkEntry(
            f_salida, textvariable=self.var_salida_fusion,
            placeholder_text="Deja vacío para guardar junto a los PDFs originales",
            height=40, corner_radius=20, border_color=COLOR_BORDER,
            fg_color="#FFFFFF", text_color=COLOR_TEXTO,
            placeholder_text_color=COLOR_TEXTO_TENUE)
        self.entry_salida_fusion.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._btn_azul(f_salida, T("elegir_destino", "📂  Elegir destino…"),
                       self._fusion_elegir_salida, ancho=190).pack(side="right")

        self.lbl_salida_info = ctk.CTkLabel(
            frame, text="Añade PDFs para ver la ruta de destino.",
            text_color=COLOR_TEXTO_SUAVE, anchor="w", justify="left",
            wraplength=820, font=ctk.CTkFont(size=11))
        self.lbl_salida_info.pack(fill="x", padx=30, pady=(6, 6))

        self.var_salida_fusion.trace_add(
            "write", lambda *_: self._fusion_actualizar_info_salida())

        opciones = ctk.CTkFrame(frame, fg_color="transparent")
        opciones.pack(fill="x", padx=26, pady=(8, 8))
        self.chk_marcadores = self._checkbox(opciones, "Añadir marcadores (uno por archivo)")
        self.chk_marcadores.select()
        self.chk_marcadores.pack(side="left")

        self.btn_run_fusion = self._btn_verde(frame, "🧩   Fusionar PDFs",
                                              self._iniciar_fusion)
        self.btn_run_fusion.pack(fill="x", padx=26, pady=(8, 14))

        self.panel_fusion = PanelProgreso(frame, altura_log=110)
        self.panel_fusion.pack(side="bottom", fill="x", padx=26, pady=(0, 22))
        self.panel_fusion.btn_stop.configure(command=self._detener)

        return frame

    # ---------- VISTA: DIVISOR ----------
    def _vista_divisor(self):
        frame = self._card(self.contenido)

        f_origen = ctk.CTkFrame(frame, fg_color="transparent")
        f_origen.pack(fill="x", padx=26, pady=(22, 8))
        self.entry_div_origen = self._campo(
            f_origen, "PDF grande a dividir por unidad médica")
        self.entry_div_origen.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._btn_azul(f_origen, T("elegir_pdf", "📂  Elegir PDF…"),
                       self._div_elegir_pdf, ancho=170).pack(side="right")

        f_destino = ctk.CTkFrame(frame, fg_color="transparent")
        f_destino.pack(fill="x", padx=26, pady=8)
        self.entry_div_destino = self._campo(
            f_destino, "Carpeta de salida (opcional, por defecto junto al PDF)")
        self.entry_div_destino.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._btn_azul(f_destino, T("explorar", "📂  Explorar"),
                       lambda: self._sel_carpeta(self.entry_div_destino)
                       ).pack(side="right")

        ctk.CTkLabel(frame, text="Lista de unidades (una por línea):",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=COLOR_TEXTO).pack(anchor="w", padx=30, pady=(16, 4))

        cab = ctk.CTkFrame(frame, fg_color="transparent")
        cab.pack(fill="x", padx=26)
        ctk.CTkLabel(cab, text="Cada unidad tendrá su propio PDF con sus páginas.",
                     text_color=COLOR_TEXTO_SUAVE, font=ctk.CTkFont(size=12)
                     ).pack(side="left")
        self._btn_azul(cab, T("cargar_txt", "📄  Cargar .txt"),
                       self._div_cargar_txt, ancho=150).pack(side="right")

        self.txt_unidades = ctk.CTkTextbox(
            frame, fg_color="#F8FCFF", height=190, corner_radius=10,
            border_width=1, border_color=COLOR_BORDER, text_color=COLOR_TEXTO,
            font=ctk.CTkFont(family="monospace", size=11))
        self.txt_unidades.pack(fill="both", expand=True, padx=26, pady=8)
        self.txt_unidades.bind("<KeyRelease>", lambda e: self._div_actualizar_count())

        self.lbl_div_count = ctk.CTkLabel(frame, text="0 unidades en la lista.",
                                          text_color=COLOR_TEXTO_SUAVE,
                                          font=ctk.CTkFont(size=11))
        self.lbl_div_count.pack(anchor="w", padx=30)

        self.btn_run_div = self._btn_verde(frame, "✂️   Dividir por unidad médica",
                                           self._iniciar_division)
        self.btn_run_div.pack(fill="x", padx=26, pady=(8, 14))

        self.panel_divisor = PanelProgreso(frame, altura_log=110)
        self.panel_divisor.pack(side="bottom", fill="x", padx=26, pady=(0, 22))
        self.panel_divisor.btn_stop.configure(command=self._detener)

        return frame

    # ---------- VISTA: COMPRESOR ----------
    def _vista_compresor(self):
        frame = self._card(self.contenido)

        barra = ctk.CTkFrame(frame, fg_color="transparent")
        barra.pack(fill="x", padx=26, pady=(22, 8))
        self._btn_azul(barra, "➕  Añadir PDFs", self._comp_add_pdfs,
                       ancho=150).pack(side="left", padx=(0, 6))
        self._btn_azul(barra, "📁  Añadir carpeta", self._comp_add_carpeta,
                       ancho=170).pack(side="left", padx=6)
        self._btn_rojo(barra, "🗑  Quitar", self._comp_quitar,
                       ancho=110).pack(side="left", padx=6)
        self._btn_suave(barra, "Limpiar lista", self._comp_limpiar,
                        ancho=130).pack(side="right")

        self._comp_listbox = tk.Listbox(
            frame, selectmode=tk.EXTENDED, activestyle="none",
            bg="#F8FCFF", fg=COLOR_TEXTO, selectbackground=COLOR_ACENTO,
            selectforeground=COLOR_TEXTO_BLANCO, highlightthickness=1,
            highlightbackground=COLOR_BORDER, highlightcolor=COLOR_ACENTO,
            borderwidth=0, relief="flat",
            font=("Segoe UI", 10), height=8,
        )
        self._comp_listbox.pack(fill="both", expand=True, padx=26, pady=(8, 6))

        self.lbl_comp_count = ctk.CTkLabel(frame, text="0 archivos en la lista.",
                                           text_color=COLOR_TEXTO_SUAVE,
                                           font=ctk.CTkFont(size=11))
        self.lbl_comp_count.pack(anchor="w", padx=30)

        ctk.CTkLabel(frame, text="Nivel de compresión:",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=COLOR_TEXTO).pack(anchor="w", padx=30, pady=(16, 4))

        self.seg_nivel_comp = ctk.CTkSegmentedButton(
            frame, values=["Ligera", "Media", "Fuerte"],
            selected_color=COLOR_ACENTO, selected_hover_color=COLOR_ACENTO_HOVER,
            unselected_color=COLOR_BORDER_SUAVE,
            unselected_hover_color=COLOR_HOVER_SIDEBAR,
            text_color=COLOR_TEXTO, font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda _v: self._comp_actualizar_descripcion())
        self.seg_nivel_comp.set("Media")
        self.seg_nivel_comp.pack(fill="x", padx=26, pady=(0, 2))

        self.lbl_comp_desc = ctk.CTkLabel(
            frame, text="", text_color=COLOR_TEXTO_SUAVE,
            anchor="w", justify="left", wraplength=820,
            font=ctk.CTkFont(size=11))
        self.lbl_comp_desc.pack(fill="x", padx=30, pady=(4, 12))

        ctk.CTkLabel(frame, text="Motor:",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=COLOR_TEXTO).pack(anchor="w", padx=30, pady=(0, 4))

        f_motor = ctk.CTkFrame(frame, fg_color="transparent")
        f_motor.pack(fill="x", padx=26)
        self.var_motor_comp = tk.StringVar(value="auto")
        for valor, etiqueta in (("auto", "Automático"),
                                ("ghostscript", "Ghostscript"),
                                ("interno", "Interno")):
            ctk.CTkRadioButton(f_motor, text=etiqueta, variable=self.var_motor_comp,
                               value=valor, fg_color=COLOR_ACENTO,
                               hover_color=COLOR_ACENTO_HOVER,
                               text_color=COLOR_TEXTO,
                               border_color=COLOR_ACENTO,
                               font=ctk.CTkFont(size=12)
                               ).pack(side="left", padx=(0, 18))

        self.lbl_comp_motor_info = ctk.CTkLabel(
            frame, text="", text_color=COLOR_TEXTO_SUAVE,
            anchor="w", justify="left", wraplength=820,
            font=ctk.CTkFont(size=11))
        self.lbl_comp_motor_info.pack(fill="x", padx=30, pady=(6, 10))

        self.var_omitir_ya = tk.BooleanVar(value=True)
        self.var_fallback_gs = tk.BooleanVar(value=True)
        opciones_comp = ctk.CTkFrame(frame, fg_color="transparent")
        opciones_comp.pack(fill="x", padx=26, pady=(0, 10))
        ctk.CTkCheckBox(opciones_comp,
                        text="Omitir archivos ya comprimidos (sufijo _comprimido)",
                        variable=self.var_omitir_ya,
                        fg_color=COLOR_ACENTO, hover_color=COLOR_ACENTO_HOVER,
                        text_color=COLOR_TEXTO, border_color=COLOR_ACENTO,
                        checkmark_color=COLOR_TEXTO_BLANCO,
                        font=ctk.CTkFont(size=12)
                        ).pack(side="left", padx=(0, 22))
        ctk.CTkCheckBox(opciones_comp,
                        text="Si Ghostscript falla, usar motor interno",
                        variable=self.var_fallback_gs,
                        fg_color=COLOR_ACENTO, hover_color=COLOR_ACENTO_HOVER,
                        text_color=COLOR_TEXTO, border_color=COLOR_ACENTO,
                        checkmark_color=COLOR_TEXTO_BLANCO,
                        font=ctk.CTkFont(size=12)
                        ).pack(side="left")

        f_destino = ctk.CTkFrame(frame, fg_color="transparent")
        f_destino.pack(fill="x", padx=26, pady=(0, 6))
        self.entry_comp_destino = self._campo(
            f_destino,
            "Carpeta de salida (opcional, por defecto: <carpeta>/PDFs_Comprimidos)")
        self.entry_comp_destino.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._btn_azul(f_destino, T("explorar", "📂  Explorar"),
                       lambda: self._sel_carpeta(self.entry_comp_destino)
                       ).pack(side="right")

        self.btn_run_comp = self._btn_verde(frame, "🗜️   Comprimir PDFs",
                                            self._iniciar_compresion)
        self.btn_run_comp.pack(fill="x", padx=26, pady=(8, 14))

        self.panel_compresor = PanelProgreso(frame, altura_log=110)
        self.panel_compresor.pack(side="bottom", fill="x", padx=26, pady=(0, 22))
        self.panel_compresor.btn_stop.configure(command=self._detener)

        self._comp_actualizar_descripcion()
        self._comp_actualizar_info_motor()
        return frame

    # ---------- HELPERS DE LA LISTA DE FUSIÓN ----------
    def _fusion_refrescar(self):
        self._fusion_listbox.delete(0, "end")
        for i, ruta in enumerate(self._lista_fusion, 1):
            self._fusion_listbox.insert("end", f"{i:>3}.   {os.path.basename(ruta)}")
        total = len(self._lista_fusion)
        self.lbl_fusion_count.configure(
            text=f"{total} archivo{'s' if total != 1 else ''} en la lista."
        )
        self._fusion_actualizar_info_salida()

    def _fusion_add_pdfs(self):
        rutas = filedialog.askopenfilenames(
            title="Selecciona los PDFs a fusionar",
            filetypes=[("PDF", "*.pdf"), ("Todos", "*.*")])
        if not rutas:
            return
        existentes = {os.path.realpath(p) for p in self._lista_fusion}
        añadidos = 0
        for r in rutas:
            if os.path.realpath(r) in existentes:
                continue
            self._lista_fusion.append(r)
            existentes.add(os.path.realpath(r))
            añadidos += 1
        self._fusion_refrescar()
        if añadidos:
            self.panel_fusion.escribir_log(f"Añadidos {añadidos} PDF(s).")

    def _fusion_add_carpeta(self):
        carpeta = filedialog.askdirectory(title="Carpeta con PDFs")
        if not carpeta:
            return
        try:
            pdfs = listar_pdfs_carpeta(carpeta)
        except ErrorFusion as e:
            messagebox.showwarning("Atención", str(e))
            return
        if not pdfs:
            messagebox.showinfo("Sin PDFs", "Esa carpeta no contiene archivos PDF.")
            return
        existentes = {os.path.realpath(p) for p in self._lista_fusion}
        añadidos = 0
        for r in pdfs:
            if os.path.realpath(r) in existentes:
                continue
            self._lista_fusion.append(r)
            existentes.add(os.path.realpath(r))
            añadidos += 1
        self._fusion_refrescar()
        self.panel_fusion.escribir_log(
            f"Añadidos {añadidos} PDF(s) desde {os.path.basename(carpeta)}.")

    def _fusion_mover(self, delta: int):
        sel = list(self._fusion_listbox.curselection())
        if not sel:
            return
        indices = sel if delta < 0 else list(reversed(sel))
        for i in indices:
            nuevo = i + delta
            if nuevo < 0 or nuevo >= len(self._lista_fusion):
                continue
            self._lista_fusion[i], self._lista_fusion[nuevo] = (
                self._lista_fusion[nuevo], self._lista_fusion[i])
        self._fusion_refrescar()
        for i in sel:
            nuevo = max(0, min(len(self._lista_fusion) - 1, i + delta))
            self._fusion_listbox.selection_set(nuevo)

    def _fusion_quitar(self):
        sel = list(self._fusion_listbox.curselection())
        if not sel:
            return
        for i in reversed(sel):
            del self._lista_fusion[i]
        self._fusion_refrescar()

    def _fusion_limpiar(self):
        if not self._lista_fusion:
            return
        self._lista_fusion.clear()
        self._fusion_refrescar()

    # ---------- HELPERS DE DESTINO ----------
    def _carpeta_base_fusion(self) -> str:
        if self._lista_fusion:
            return os.path.dirname(self._lista_fusion[0])
        return os.getcwd()

    def _resolver_salida_fusion(self) -> str:
        entrada = self.var_salida_fusion.get().strip()
        carpeta = self._carpeta_base_fusion()
        if not entrada:
            return os.path.join(carpeta, NOMBRE_FUSIONADO_DEFECTO)
        if not os.path.isabs(entrada):
            entrada = os.path.join(carpeta, entrada)
        if not entrada.lower().endswith(".pdf"):
            entrada += ".pdf"
        return entrada

    def _fusion_actualizar_info_salida(self):
        if not hasattr(self, "lbl_salida_info"):
            return
        if not self._lista_fusion:
            self.lbl_salida_info.configure(
                text="Añade PDFs para ver la ruta de destino.",
                text_color=COLOR_TEXTO_SUAVE)
            return
        ruta = self._resolver_salida_fusion()
        entrada = self.var_salida_fusion.get().strip()
        if entrada:
            self.lbl_salida_info.configure(
                text=f"📄  Se guardará en:  {ruta}",
                text_color=COLOR_TEXTO_SUAVE)
        else:
            self.lbl_salida_info.configure(
                text=f"📄  Sin ruta indicada → se guardará como:  {ruta}",
                text_color=COLOR_ACENTO)

    def _fusion_elegir_salida(self):
        ruta = filedialog.asksaveasfilename(
            title="Guardar PDF fusionado como…",
            initialdir=self._carpeta_base_fusion(),
            initialfile=NOMBRE_FUSIONADO_DEFECTO,
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")])
        if ruta:
            self.var_salida_fusion.set(ruta)

    # ---------- HELPERS DEL DIVISOR ----------
    def _div_elegir_pdf(self):
        ruta = filedialog.askopenfilename(
            title="PDF a dividir",
            filetypes=[("PDF", "*.pdf"), ("Todos", "*.*")])
        if ruta:
            self.entry_div_origen.delete(0, "end")
            self.entry_div_origen.insert(0, ruta)

    def _div_cargar_txt(self):
        ruta = filedialog.askopenfilename(
            title="Lista de unidades",
            filetypes=[("Texto", "*.txt"), ("Todos", "*.*")])
        if not ruta:
            return
        try:
            unidades = leer_unidades_txt(ruta)
        except ErrorDivisor as e:
            messagebox.showwarning("Atención", str(e))
            return
        self.txt_unidades.delete("1.0", "end")
        self.txt_unidades.insert("1.0", "\n".join(unidades))
        self._div_actualizar_count()
        self.panel_divisor.escribir_log(
            f"Cargadas {len(unidades)} unidades desde {os.path.basename(ruta)}.")

    def _div_actualizar_count(self):
        lineas = [l.strip() for l in self.txt_unidades.get("1.0", "end").splitlines()
                  if l.strip() and not l.strip().startswith("#")]
        self.lbl_div_count.configure(
            text=f"{len(lineas)} unidad{'es' if len(lineas) != 1 else ''} en la lista.")

    # ---------- HELPERS DEL COMPRESOR ----------
    def _comp_refrescar(self):
        self._comp_listbox.delete(0, "end")
        for i, ruta in enumerate(self._lista_compresion, 1):
            self._comp_listbox.insert("end", f"{i:>3}.   {os.path.basename(ruta)}")
        n = len(self._lista_compresion)
        self.lbl_comp_count.configure(text=f"{n} archivo{'s' if n != 1 else ''} en la lista.")

    def _comp_add_rutas(self, rutas):
        existentes = {os.path.realpath(p) for p in self._lista_compresion}
        añadidos = 0
        for r in rutas:
            if os.path.realpath(r) in existentes:
                continue
            self._lista_compresion.append(r)
            existentes.add(os.path.realpath(r))
            añadidos += 1
        self._comp_refrescar()
        if añadidos:
            self.panel_compresor.escribir_log(f"Añadidos {añadidos} PDF(s).")

    def _comp_add_pdfs(self):
        rutas = filedialog.askopenfilenames(
            title="Selecciona los PDFs a comprimir",
            filetypes=[("PDF", "*.pdf"), ("Todos", "*.*")])
        if rutas:
            self._comp_add_rutas(rutas)

    def _comp_add_carpeta(self):
        carpeta = filedialog.askdirectory(title="Carpeta con PDFs")
        if not carpeta:
            return
        try:
            pdfs = listar_pdfs_carpeta(carpeta)
        except ErrorFusion as e:
            messagebox.showwarning("Atención", str(e))
            return
        if not pdfs:
            messagebox.showinfo("Sin PDFs", "Esa carpeta no contiene archivos PDF.")
            return
        self._comp_add_rutas(pdfs)

    def _comp_quitar(self):
        sel = list(self._comp_listbox.curselection())
        if not sel:
            return
        for i in reversed(sel):
            del self._lista_compresion[i]
        self._comp_refrescar()

    def _comp_limpiar(self):
        if not self._lista_compresion:
            return
        self._lista_compresion.clear()
        self._comp_refrescar()

    def _comp_actualizar_descripcion(self):
        etiqueta = self.seg_nivel_comp.get()
        clave = etiqueta.lower()
        cfg = NIVELES_COMPRESION.get(clave, {})
        self.lbl_comp_desc.configure(text=cfg.get("descripcion", ""))

    def _comp_actualizar_info_motor(self):
        try:
            texto = info_motor()
            if "Ghostscript" not in texto and sys.platform.startswith("linux"):
                texto += "  ·  Para mejor compresión: sudo apt install ghostscript"
            self.lbl_comp_motor_info.configure(text=texto)
        except Exception:
            self.lbl_comp_motor_info.configure(text="Motor: no se pudo detectar.")

    # ---------- HELPERS GENERALES DE UI ----------
    def _sel_carpeta(self, widget: ctk.CTkEntry):
        folder = filedialog.askdirectory()
        if folder:
            widget.delete(0, "end")
            widget.insert(0, folder)

    def _cargar_txt(self):
        ruta = filedialog.askopenfilename(
            title="Selecciona el archivo de palabras",
            filetypes=[("Texto", "*.txt"), ("Todos", "*.*")])
        if not ruta:
            return
        try:
            claves = leer_claves_txt(ruta)
        except ErrorMotor as e:
            messagebox.showwarning("Atención", str(e))
            return
        self.txt_lista.delete("1.0", "end")
        self.txt_lista.insert("1.0", "\n".join(claves))
        self.panel_extractor.escribir_log(
            f"Cargadas {len(claves)} palabras desde {os.path.basename(ruta)}")

    def _set_ejecutando(self, ejecutando: bool, panel: PanelProgreso | None = None):
        self._procesando = ejecutando
        estado = "disabled" if ejecutando else "normal"
        self.btn_run_1.configure(state=estado)
        self.btn_run_2.configure(state=estado)
        self.btn_run_fusion.configure(state=estado)
        self.btn_run_div.configure(state=estado)
        self.btn_run_comp.configure(state=estado)
        self.panel_extractor.btn_stop.configure(state="normal" if ejecutando else "disabled")
        self.panel_fusion.btn_stop.configure(state="normal" if ejecutando else "disabled")
        self.panel_divisor.btn_stop.configure(state="normal" if ejecutando else "disabled")
        self.panel_compresor.btn_stop.configure(state="normal" if ejecutando else "disabled")
        for btn in self.botones_nav.values():
            btn.configure(state="disabled" if ejecutando else "normal")
        self._panel_activo = panel

    @staticmethod
    def _opciones(chk_fuzzy, chk_palabra):
        palabra = bool(chk_palabra.get())
        tolerar = bool(chk_fuzzy.get()) and not palabra
        return tolerar, palabra

    def _detener(self):
        self.evento_cancelar.set()
        if self._panel_activo is not None:
            self._panel_activo.btn_stop.configure(state="disabled")
            self._panel_activo.lbl_progreso.configure(
                text="Deteniendo al terminar el archivo actual...")

    # ---------- ARRANQUE: EXTRACCIÓN ----------
    def _iniciar_extraccion(self, modo: str):
        if self._procesando:
            return
        origen = self.entry_origen.get().strip()
        destino = self.entry_destino.get().strip()
        if not destino:
            destino = self._carpeta_defecto("extractor")
        if not origen or not os.path.isdir(origen):
            messagebox.showwarning("Atención", "Selecciona una carpeta de origen válida.")
            return
        if destino and os.path.abspath(destino) == os.path.abspath(origen):
            if not messagebox.askyesno(
                "Aviso",
                "El origen y el destino son la misma carpeta.\n"
                "Los archivos generados se guardarán junto a los originales.\n\n¿Continuar?"):
                return
        if modo == "firma":
            k1 = self.entry_k1.get().strip()
            if not k1:
                messagebox.showwarning("Atención", "Escribe el texto donde se detiene el corte.")
                return
            tolerar, palabra = self._opciones(self.chk_fuzzy_1, self.chk_palabra_1)
            funcion = cortar_hasta_palabra
            kwargs = dict(origen=origen, destino=destino, clave1=k1,
                          clave2=self.entry_k2.get().strip(),
                          tolerar=tolerar, palabra_completa=palabra)
        else:
            claves = limpiar_claves(self.txt_lista.get("1.0", "end").splitlines())
            if not claves:
                messagebox.showwarning("Atención", "La lista de palabras está vacía.")
                return
            tolerar, palabra = self._opciones(self.chk_fuzzy_2, self.chk_palabra_2)
            funcion = clasificar_por_lista
            kwargs = dict(origen=origen, destino=destino, claves=claves,
                          tolerar=tolerar, palabra_completa=palabra)
        self._lanzar(funcion, kwargs, self.panel_extractor)

    # ---------- ARRANQUE: FUSIÓN ----------
    def _iniciar_fusion(self):
        if self._procesando:
            return
        if len(self._lista_fusion) < 2:
            messagebox.showwarning("Atención", "Agrega al menos 2 PDFs para fusionar.")
            return
        entrada = self.var_salida_fusion.get().strip()
        if not entrada:
            ruta = filedialog.asksaveasfilename(
                title="Guardar PDF fusionado como…",
                initialdir=self._carpeta_base_fusion(),
                initialfile=NOMBRE_FUSIONADO_DEFECTO,
                defaultextension=".pdf",
                filetypes=[("PDF", "*.pdf")])
            if ruta:
                self.var_salida_fusion.set(ruta)
            else:
                self.var_salida_fusion.set(
                    os.path.join(self._carpeta_base_fusion(), NOMBRE_FUSIONADO_DEFECTO))
        carpeta_conf = self._carpeta_defecto("fusionador")
        if carpeta_conf and not self.var_salida_fusion.get().strip():
            self.var_salida_fusion.set(
                os.path.join(carpeta_conf, NOMBRE_FUSIONADO_DEFECTO))
        salida = self._resolver_salida_fusion()
        salida_real = os.path.realpath(salida)
        for ruta_in in self._lista_fusion:
            if os.path.realpath(ruta_in) == salida_real:
                messagebox.showwarning(
                    "Ruta no válida",
                    "El archivo de salida no puede ser uno de los PDFs que estás fusionando.")
                return
        marcadores = bool(self.chk_marcadores.get())
        archivos = list(self._lista_fusion)
        kwargs = dict(archivos=archivos, salida=salida, marcadores=marcadores)
        self.panel_fusion.escribir_log(f"Destino: {salida}")
        self._lanzar(fusionar_pdfs, kwargs, self.panel_fusion)

    # ---------- ARRANQUE: DIVISIÓN ----------
    def _iniciar_division(self):
        if self._procesando:
            return
        origen = self.entry_div_origen.get().strip()
        if not origen or not os.path.isfile(origen):
            messagebox.showwarning("Atención", "Selecciona un PDF válido para dividir.")
            return
        unidades = [l.strip() for l in self.txt_unidades.get("1.0", "end").splitlines()
                    if l.strip() and not l.strip().startswith("#")]
        if not unidades:
            messagebox.showwarning("Atención", "La lista de unidades está vacía.")
            return
        destino = self.entry_div_destino.get().strip()
        if not destino:
            carpeta_conf = self._carpeta_defecto("divisor")
            base = os.path.splitext(os.path.basename(origen))[0]
            if carpeta_conf:
                destino = os.path.join(carpeta_conf, f"{base}_unidades")
            else:
                destino = os.path.join(os.path.dirname(origen), f"{base}_unidades")
        kwargs = dict(origen=origen, destino=destino, unidades=unidades,
                      callback_confirmar=self._confirmar_desde_hilo)
        self.panel_divisor.escribir_log(f"Salida: {destino}")
        self._lanzar(dividir_por_unidad, kwargs, self.panel_divisor)

    # ---------- ARRANQUE: COMPRESIÓN ----------
    def _iniciar_compresion(self):
        if self._procesando:
            return
        if not self._lista_compresion:
            messagebox.showwarning("Atención", "Agrega al menos un PDF para comprimir.")
            return
        nivel = self.seg_nivel_comp.get().lower()
        motor = self.var_motor_comp.get()
        destino = self.entry_comp_destino.get().strip()
        if not destino:
            destino = self._carpeta_defecto("compresor")
        archivos = list(self._lista_compresion)
        kwargs = dict(
            archivos=archivos, destino=destino, nivel=nivel, motor=motor,
            omitir_ya_comprimidos=bool(self.var_omitir_ya.get()),
            fallback_si_gs_falla=bool(self.var_fallback_gs.get()))
        self._lanzar(comprimir_pdfs, kwargs, self.panel_compresor)

    # ---------- LANZADOR GENÉRICO ----------
    def _lanzar(self, funcion, kwargs, panel: PanelProgreso):
        self.evento_cancelar.clear()
        self._set_ejecutando(True, panel=panel)
        panel.reset()
        panel.limpiar_log()
        panel.lbl_progreso.configure(text=T("iniciando", "Iniciando..."))
        threading.Thread(target=self._hilo_motor, args=(funcion, kwargs),
                         daemon=True).start()

    # ---------- HILO DEL MOTOR ----------
    def _hilo_motor(self, funcion, kwargs):
        try:
            resumen = funcion(
                **kwargs,
                callback_progreso=lambda a, t, f: self.cola.put(MsgProgreso(a, t, f)),
                callback_log=lambda m: self.cola.put(MsgLog(m)),
                cancelar=self.evento_cancelar)
            self.cola.put(MsgFin(resumen, None))
        except (ErrorMotor, ErrorFusion, ErrorDivisor, ErrorCompresion) as e:
            self.cola.put(MsgFin(None, str(e)))
        except Exception as e:
            self.cola.put(MsgFin(None, f"Error inesperado: {e}"))

    # ---------- CONFIRMACIÓN ----------
    def _confirmar_desde_hilo(self, valor, unidad, paginas, indice, total):
        respuesta, listo = {"ok": False}, threading.Event()
        self.cola.put(MsgPregunta(valor, unidad, paginas, indice, total, respuesta, listo))
        while not listo.wait(0.2):
            if self.evento_cancelar.is_set():
                return False
        return respuesta["ok"]

    def _preguntar(self, msg):
        if self._panel_activo is not None:
            self._panel_activo.lbl_progreso.configure(
                text=f"Esperando tu confirmación ({msg.indice} de {msg.total})...")
        def responder(si):
            msg.respuesta["ok"] = si
            msg.listo.set()
        mostrar_dialogo_confirmacion(self, msg.valor, msg.unidad, msg.paginas,
                                     msg.indice, msg.total, responder)

    # ---------- BOMBEO DE LA COLA ----------
    def _procesar_cola(self):
        if not self.winfo_exists():
            return
        for _ in range(MAX_MENSAJES_POR_TICK):
            try:
                msg = self.cola.get_nowait()
            except queue.Empty:
                break
            panel = self._panel_activo
            if isinstance(msg, MsgProgreso) and panel is not None:
                panel.set_progreso(msg.actual, msg.total, msg.archivo)
            elif isinstance(msg, MsgLog) and panel is not None:
                panel.escribir_log(msg.texto)
            elif isinstance(msg, MsgFin):
                self._terminar(msg.resumen, msg.error)
            elif isinstance(msg, MsgPregunta):
                self._preguntar(msg)
        self._after_id = self.after(INTERVALO_COLA_MS, self._procesar_cola)

    # ---------- FIN DEL PROCESO ----------
    def _terminar(self, resumen, error):
        panel = self._panel_activo
        self._set_ejecutando(False)
        if error or resumen is None:
            if panel is not None:
                panel.lbl_progreso.configure(text="Error.")
            messagebox.showerror("Error", error or "Error desconocido.")
            return
        texto_resumen = resumen.a_texto() if hasattr(resumen, "a_texto") else str(resumen)
        if panel is not None:
            panel.escribir_log("\n" + "─" * 40 + "\n" + texto_resumen)
        cancelado = bool(_attr(resumen, "cancelado", False))
        if panel is not None:
            if cancelado:
                panel.lbl_progreso.configure(text="Cancelado por el usuario.")
            else:
                panel.barra.set(1)
                panel.lbl_progreso.configure(text="¡Listo!")
        carpeta = _attr(resumen, "carpeta_salida", "")
        if not carpeta:
            ruta = _attr(resumen, "ruta_salida", "")
            if ruta:
                carpeta = os.path.dirname(ruta)
        errores = _attr(resumen, "errores", [])
        sin_texto = _attr(resumen, "sin_texto", [])
        sin_paginas = _attr(resumen, "unidades_sin_paginas", [])
        omitidos = _attr(resumen, "omitidos", [])
        hay_avisos = bool(errores or sin_texto or sin_paginas or omitidos
                          or _attr(resumen, "paginas_huerfanas", 0)
                          or _attr(resumen, "sin_mejora", []))
        texto = texto_resumen
        if hay_avisos:
            texto += "\n\nRevisa el registro para más detalle."
        if carpeta and os.path.isdir(carpeta) and not cancelado:
            if messagebox.askyesno("Proceso finalizado",
                                   texto + "\n\n¿Abrir la carpeta de salida?"):
                abrir_carpeta(carpeta)
        elif hay_avisos:
            messagebox.showwarning("Proceso finalizado", texto)
        else:
            messagebox.showinfo("Proceso finalizado", texto)

    # ---------- CONFIGURACIÓN ----------
    def _abrir_config(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title(T("configuracion", "Configuración"))
        dlg.configure(fg_color=COLOR_FONDO)
        dlg.resizable(False, False)
        dlg.transient(self)
        ancho, alto = 640, 620
        try:
            x = self.winfo_rootx() + (self.winfo_width() - ancho) // 2
            y = self.winfo_rooty() + (self.winfo_height() - alto) // 2
            dlg.geometry(f"{ancho}x{alto}+{max(x, 0)}+{max(y, 0)}")
        except Exception:
            dlg.geometry(f"{ancho}x{alto}")

        cab = ctk.CTkFrame(dlg, corner_radius=0, fg_color=COLOR_ACENTO, height=70)
        cab.pack(fill="x")
        cab.pack_propagate(False)
        ctk.CTkLabel(cab, text="⚙️   " + T("configuracion", "Configuración"),
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=COLOR_TEXTO_BLANCO).pack(side="left", padx=26)

        tabs = ctk.CTkTabview(
            dlg, fg_color="transparent",
            segmented_button_selected_color=COLOR_ACENTO,
            segmented_button_selected_hover_color=COLOR_ACENTO_HOVER,
            segmented_button_unselected_color=COLOR_BORDER_SUAVE,
            segmented_button_unselected_hover_color=COLOR_HOVER_SIDEBAR,
            text_color=COLOR_TEXTO)
        tabs.pack(fill="both", expand=True, padx=20, pady=(12, 8))

        tab_apariencia = tabs.add("🎨  " + T("config_apariencia", "Apariencia"))
        tab_carpetas   = tabs.add("📁  " + T("config_carpetas", "Carpetas"))
        tab_actual     = tabs.add("🔄  " + T("config_actualizaciones", "Actualizaciones"))
        tab_acerca     = tabs.add("ℹ️  " + T("config_acerca", "Acerca de"))

        # ---- Pestaña 1: Apariencia ----
        ctk.CTkLabel(tab_apariencia,
                     text=T("config_info", "Los cambios se aplican al instante"),
                     font=ctk.CTkFont(size=11),
                     text_color=COLOR_TEXTO_SUAVE).pack(anchor="w", pady=(6, 18))

        ctk.CTkLabel(tab_apariencia, text=T("config_tema", "Tema"),
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=COLOR_TEXTO).pack(anchor="w", pady=(0, 6))

        nombres_temas = [cfg_prefs.etiqueta_tema(k, _IDIOMA_ACTIVO) for k in cfg_prefs.TEMAS]
        claves_temas = list(cfg_prefs.TEMAS.keys())
        var_tema = tk.StringVar(value=cfg_prefs.etiqueta_tema(_TEMA_ACTIVO, _IDIOMA_ACTIVO))
        menu_tema = ctk.CTkOptionMenu(
            tab_apariencia, values=nombres_temas, variable=var_tema,
            fg_color=COLOR_TARJETA, button_color=COLOR_ACENTO,
            button_hover_color=COLOR_ACENTO_HOVER, text_color=COLOR_TEXTO,
            dropdown_fg_color=COLOR_TARJETA, dropdown_hover_color=COLOR_ACTIVO,
            dropdown_text_color=COLOR_TEXTO,
            font=ctk.CTkFont(size=12), dropdown_font=ctk.CTkFont(size=12),
            corner_radius=10, height=40)
        menu_tema.pack(fill="x")

        def _sel_tema(nueva):
            idx = nombres_temas.index(nueva)
            self._cambiar_tema(claves_temas[idx])
            try: dlg.destroy()
            except Exception: pass
        menu_tema.configure(command=_sel_tema)

        ctk.CTkLabel(tab_apariencia, text=T("config_idioma", "Idioma"),
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=COLOR_TEXTO).pack(anchor="w", pady=(22, 6))

        nombres_idiomas = [cfg_prefs.IDIOMAS[k]["etiqueta"] for k in cfg_prefs.IDIOMAS]
        claves_idiomas = list(cfg_prefs.IDIOMAS.keys())
        var_idioma = tk.StringVar(value=cfg_prefs.idioma(_IDIOMA_ACTIVO)["etiqueta"])
        menu_idioma = ctk.CTkOptionMenu(
            tab_apariencia, values=nombres_idiomas, variable=var_idioma,
            fg_color=COLOR_TARJETA, button_color=COLOR_ACENTO,
            button_hover_color=COLOR_ACENTO_HOVER, text_color=COLOR_TEXTO,
            dropdown_fg_color=COLOR_TARJETA, dropdown_hover_color=COLOR_ACTIVO,
            dropdown_text_color=COLOR_TEXTO,
            font=ctk.CTkFont(size=12), dropdown_font=ctk.CTkFont(size=12),
            corner_radius=10, height=40)
        menu_idioma.pack(fill="x")

        def _sel_idioma(nueva):
            idx = nombres_idiomas.index(nueva)
            self._cambiar_idioma(claves_idiomas[idx])
            try: dlg.destroy()
            except Exception: pass
        menu_idioma.configure(command=_sel_idioma)

        # ---- Pestaña 2: Carpetas ----
        ctk.CTkLabel(tab_carpetas,
                     text="Carpeta de salida por defecto para cada módulo.\n"
                          "Si la dejas vacía, se usa la carpeta junto al PDF original.",
                     font=ctk.CTkFont(size=11), justify="left",
                     text_color=COLOR_TEXTO_SUAVE).pack(anchor="w", pady=(6, 14))

        scroll = ctk.CTkScrollableFrame(tab_carpetas, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        entradas_carpetas: dict = {}
        for clave, etiqueta in (
            ("extractor",  "Extracción Avanzada"),
            ("fusionador", "Fusionador"),
            ("divisor",    "Divisor por Unidad"),
            ("compresor",  "Compresor"),
        ):
            fila = ctk.CTkFrame(scroll, fg_color="transparent")
            fila.pack(fill="x", pady=(0, 14))

            ctk.CTkLabel(fila, text=etiqueta,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=COLOR_TEXTO).pack(anchor="w")

            sub = ctk.CTkFrame(fila, fg_color="transparent")
            sub.pack(fill="x", pady=(4, 0))

            var = tk.StringVar(value=(_PREFS.get("carpetas") or {}).get(clave, ""))
            entradas_carpetas[clave] = var

            ctk.CTkEntry(sub, textvariable=var, height=36, corner_radius=10,
                         border_color=COLOR_BORDER, fg_color="#FFFFFF",
                         text_color=COLOR_TEXTO, placeholder_text_color=COLOR_TEXTO_TENUE,
                         placeholder_text="(por defecto)").pack(
                side="left", fill="x", expand=True, padx=(0, 8))

            def _elegir(v=var):
                ruta = filedialog.askdirectory()
                if ruta:
                    v.set(ruta)

            ctk.CTkButton(sub, text="📂", width=44, height=36, corner_radius=10,
                          fg_color=COLOR_ACENTO, hover_color=COLOR_ACENTO_HOVER,
                          text_color=COLOR_TEXTO_BLANCO,
                          font=ctk.CTkFont(size=14),
                          command=_elegir).pack(side="right")

        def _guardar_carpetas():
            for k, var in entradas_carpetas.items():
                _PREFS.setdefault("carpetas", {})[k] = var.get().strip()
            cfg_prefs.guardar(_PREFS)
            messagebox.showinfo("Carpetas",
                                "Carpetas de salida guardadas.",
                                parent=dlg)

        ctk.CTkButton(tab_carpetas, text="💾   Guardar carpetas",
                      height=40, corner_radius=10,
                      fg_color=COLOR_OK, hover_color=COLOR_OK_HOVER,
                      text_color=COLOR_TEXTO_BLANCO,
                      font=ctk.CTkFont(size=12, weight="bold"),
                      command=_guardar_carpetas).pack(fill="x", pady=(8, 0))

        # ---- Pestaña 3: Actualizaciones ----
        ctk.CTkLabel(tab_actual, text="Versión instalada",
                     font=ctk.CTkFont(size=11),
                     text_color=COLOR_TEXTO_SUAVE).pack(anchor="w", pady=(6, 2))
        ctk.CTkLabel(tab_actual, text=APP_VERSION,
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=COLOR_TEXTO).pack(anchor="w", pady=(0, 20))

        lbl_estado_act = ctk.CTkLabel(
            tab_actual, text="Pulsa el botón para comprobar si hay novedades.",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXTO_SUAVE, wraplength=520, justify="left")
        lbl_estado_act.pack(anchor="w", pady=(0, 14))

        btn_buscar_act = ctk.CTkButton(
            tab_actual, text="🔍   Buscar actualizaciones",
            height=44, corner_radius=10,
            fg_color=COLOR_ACENTO, hover_color=COLOR_ACENTO_HOVER,
            text_color=COLOR_TEXTO_BLANCO,
            font=ctk.CTkFont(size=13, weight="bold"))

        def _buscar_actualizaciones():
            try:
                from actualizador import comprobar
            except ImportError:
                messagebox.showwarning(
                    "Actualizaciones",
                    "Falta el archivo actualizador.py en la carpeta Interfaz.",
                    parent=dlg)
                return

            btn_buscar_act.configure(state="disabled", text="Buscando…")
            lbl_estado_act.configure(text="Consultando GitHub…",
                                     text_color=COLOR_TEXTO_SUAVE)

            def tarea():
                info = comprobar(APP_VERSION)
                self.after(0, lambda: _mostrar(info))

            def _mostrar(info):
                btn_buscar_act.configure(state="normal",
                                         text="🔍   Buscar actualizaciones")
                if info.error:
                    lbl_estado_act.configure(text=f"⚠  {info.error}",
                                             text_color=COLOR_STOP)
                    return
                if info.hay_nueva:
                    lbl_estado_act.configure(
                        text=f"✨  Hay versión nueva: {info.version_remota}\n"
                             f"Tienes la {info.version_actual}.",
                        text_color=COLOR_OK)
                    if messagebox.askyesno(
                        "Actualización disponible",
                        f"Versión nueva: {info.version_remota}\n"
                        f"Tienes: {info.version_actual}\n\n"
                        f"¿Abrir la página de descarga?",
                        parent=dlg):
                        import webbrowser
                        webbrowser.open(info.url_descarga)
                else:
                    lbl_estado_act.configure(
                        text=f"✓  Estás en la última versión ({info.version_actual}).",
                        text_color=COLOR_OK)

            import threading
            threading.Thread(target=tarea, daemon=True).start()

        btn_buscar_act.configure(command=_buscar_actualizaciones)
        btn_buscar_act.pack(fill="x")

        # ---- Pestaña 4: Acerca de ----
        try:
            from PIL import Image
            ruta_logo = _ruta_recurso("Interfaz/assets/logo.png")
            if os.path.isfile(ruta_logo):
                pil = Image.open(ruta_logo).convert("RGBA").resize((80, 80), Image.LANCZOS)
                img = ctk.CTkImage(light_image=pil, dark_image=pil, size=(80, 80))
                lbl_img = ctk.CTkLabel(tab_acerca, image=img, text="")
                lbl_img._img_ref = img
                lbl_img.pack(pady=(6, 8))
        except Exception:
            pass

        ctk.CTkLabel(tab_acerca, text=APP_NOMBRE,
                     font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=COLOR_TEXTO).pack()
        ctk.CTkLabel(tab_acerca, text=f"Versión {APP_VERSION}",
                     font=ctk.CTkFont(size=12),
                     text_color=COLOR_TEXTO_SUAVE).pack(pady=(2, 2))
        ctk.CTkLabel(tab_acerca,
                     text="Suite local de gestión de PDF · Open source",
                     font=ctk.CTkFont(size=11),
                     text_color=COLOR_TEXTO_SUAVE).pack(pady=(2, 2))
        ctk.CTkLabel(tab_acerca,
                     text="Desarrollado por Kodesoft",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLOR_ACENTO).pack(pady=(0, 18))

        info_box = ctk.CTkFrame(tab_acerca, corner_radius=12,
                                fg_color=COLOR_TARJETA,
                                border_width=1, border_color=COLOR_BORDER)
        info_box.pack(fill="x", pady=(0, 14))

        def _fila_info(k, v):
            f = ctk.CTkFrame(info_box, fg_color="transparent")
            f.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(f, text=k, width=110, anchor="w",
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=COLOR_TEXTO_SUAVE).pack(side="left")
            ctk.CTkLabel(f, text=v, anchor="w",
                         font=ctk.CTkFont(size=11),
                         text_color=COLOR_TEXTO).pack(side="left")

        _fila_info("Desarrollado por", "Kodesoft")
        _fila_info("Licencia",         "MIT (open source)")
        _fila_info("Plataforma",       "Windows / Linux / macOS")
        _fila_info("Repositorio",      "github.com/tu-usuario/CCpdf")
        _fila_info("Versión",          "Desarrollo")

        LICENCIA_TEXTO = """\
        CCpdf — Suite local de gestión de PDF
        Copyright (c) 2026 Kodesoft

        Licencia MIT (open source)

        Por la presente se otorga permiso, de forma gratuita, a cualquier
        persona que obtenga una copia de este software y de los archivos de
        documentación asociados (el "Software"), para utilizar el Software
        sin restricción, incluidos, entre otros, los derechos de uso, copia,
        modificación, fusión, publicación, distribución, sublicencia y/o
        venta de copias del Software, y para permitir a las personas a las
        que se les proporcione el Software que lo hagan, con sujeción a las
        siguientes condiciones:

        El aviso de copyright anterior y este aviso de permiso se incluirán
        en todas las copias o partes sustanciales del Software.

        EL SOFTWARE SE PROPORCIONA "TAL CUAL", SIN GARANTÍA DE NINGÚN TIPO,
        EXPRESA O IMPLÍCITA, INCLUYENDO PERO NO LIMITADO A LAS GARANTÍAS
        DE COMERCIABILIDAD, IDONEIDAD PARA UN PROPÓSITO PARTICULAR Y NO
        INFRACCIÓN. EN NINGÚN CASO LOS AUTORES O TITULARES DEL COPYRIGHT
        SERÁN RESPONSABLES DE NINGUNA RECLAMACIÓN, DAÑOS U OTRAS
        RESPONSABILIDADES, YA SEA EN UNA ACCIÓN DE CONTRATO, AGRAVIO O DE
        OTRO MODO, QUE SURJA DE O EN CONEXIÓN CON EL SOFTWARE O EL USO U
        OTRAS ACCIONES EN EL SOFTWARE.

        ---

        CCpdf se distribuye como versión de desarrollo open source bajo
        el sello de Kodesoft. Puedes consultar el código fuente, reportar
        problemas y contribuir en el repositorio oficial del proyecto.
        """

        def _ver_licencia():
            dlg_lic = ctk.CTkToplevel(dlg)
            dlg_lic.title("Licencia")
            dlg_lic.geometry("620x460")
            dlg_lic.configure(fg_color=COLOR_FONDO)
            dlg_lic.transient(dlg)
            txt = ctk.CTkTextbox(dlg_lic, fg_color="#F8FCFF",
                                 border_width=1, border_color=COLOR_BORDER,
                                 corner_radius=10,
                                 font=ctk.CTkFont(family="monospace", size=11),
                                 text_color=COLOR_TEXTO)
            txt.pack(fill="both", expand=True, padx=20, pady=20)
            txt.insert("1.0", LICENCIA_TEXTO)
            txt.configure(state="disabled")
            dlg_lic.after(200, lambda: (dlg_lic.lift(), dlg_lic.grab_set()))

        ctk.CTkButton(tab_acerca, text="📄   Ver licencia completa",
                      height=40, corner_radius=10,
                      fg_color=COLOR_ACENTO, hover_color=COLOR_ACENTO_HOVER,
                      text_color=COLOR_TEXTO_BLANCO,
                      font=ctk.CTkFont(size=12, weight="bold"),
                      command=_ver_licencia).pack(fill="x", pady=(0, 8))

        ctk.CTkButton(dlg, text=T("config_cerrar", "Cerrar"),
                      height=44, corner_radius=22,
                      fg_color=COLOR_ACENTO, hover_color=COLOR_ACENTO_HOVER,
                      text_color=COLOR_TEXTO_BLANCO,
                      font=ctk.CTkFont(size=13, weight="bold"),
                      command=dlg.destroy).pack(pady=(8, 16))

        dlg.after(200, lambda: (dlg.lift(), dlg.grab_set()))

    # ---------- HELPERS DE CARPETAS ----------
    def _carpeta_defecto(self, modulo: str) -> str:
        """Carpeta predeterminada del módulo, o '' si no hay."""
        try:
            return (_PREFS.get("carpetas") or {}).get(modulo, "").strip()
        except Exception:
            return ""

    # ---------- CAMBIO DE TEMA / IDIOMA ----------
    def _cambiar_tema(self, nombre_tema: str):
        global _TEMA_ACTIVO
        if nombre_tema not in cfg_prefs.TEMAS:
            return
        _TEMA_ACTIVO = nombre_tema
        _PREFS["tema"] = nombre_tema
        cfg_prefs.guardar(_PREFS)
        _aplicar_paleta(cfg_prefs.tema(nombre_tema))
        self._reconstruir_ui()

    def _cambiar_idioma(self, codigo: str):
        global APP_SUBTITULO, MODULOS, MODULO_POR_CLAVE
        if codigo not in cfg_prefs.IDIOMAS:
            return
        _PREFS["idioma"] = codigo
        cfg_prefs.guardar(_PREFS)
        _aplicar_idioma(codigo)
        APP_SUBTITULO = T("app_subtitulo", "Suite local de PDF")
        MODULOS = _construir_modulos()
        MODULO_POR_CLAVE = {m.clave: m for m in MODULOS}
        self._reconstruir_ui()

    def _reconstruir_ui(self):
        """Reconstruye toda la interfaz con el tema/idioma actuales."""
        clave_actual = self._clave_actual
        if hasattr(self, "visor"):
            try:
                self.visor.cerrar()
            except Exception:
                pass
        for w in self.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass
        self.botones_nav = {}
        self._indicadores = {}
        self.vistas = {}
        self._panel_activo = None
        self.configure(fg_color=COLOR_FONDO)
        self.title(f"{APP_NOMBRE} — {APP_SUBTITULO}")
        self._crear_sidebar()
        self._crear_area_contenido()
        self.mostrar_vista(clave_actual)
        self.update_idletasks()

    # ---------- CIERRE ----------
    def _al_cerrar(self):
        if self._procesando:
            if not messagebox.askyesno(
                "Salir",
                "Hay un proceso en curso. ¿Cancelarlo y salir igualmente?"):
                return
            self.evento_cancelar.set()
        if hasattr(self, "visor"):
            try:
                self.visor.cerrar()
            except Exception:
                pass
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        self.destroy()

    # ---------- NAVEGACIÓN ----------
    def mostrar_vista(self, clave: str):
        if clave not in self.vistas:
            return
        for v in self.vistas.values():
            v.grid_forget()
        for c, btn in self.botones_nav.items():
            activo = (c == clave)
            btn.configure(
                fg_color=COLOR_ACTIVO if activo else "transparent",
                text_color=COLOR_ACENTO if activo else COLOR_TEXTO,
                font=ctk.CTkFont(size=13, weight="bold" if activo else "normal"),
                hover_color=COLOR_ACTIVO if activo else COLOR_HOVER_SIDEBAR,
            )
            ind = self._indicadores.get(c)
            if ind is not None:
                if activo:
                    ind.pack(side="left", fill="y", pady=6, before=btn)
                else:
                    ind.pack_forget()
        mod = MODULO_POR_CLAVE[clave]
        self.icono_titulo.configure(text=mod.emoji)
        self.titulo.configure(text=mod.titulo)
        self.subtitulo.configure(text=mod.subtitulo or mod.descripcion)
        self.vistas[clave].grid(row=0, column=0, sticky="nsew")
        self._clave_actual = clave


if __name__ == "__main__":
    CCPdfApp().mainloop()