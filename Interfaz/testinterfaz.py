"""
prototipo_ui.py — Maqueta visual "empresarial" para CCpdf.

⚠️  Este archivo es SOLO un prototipo. No toca app.py ni los motores.
    Su único objetivo es mostrar una versión más limpia y profesional
    de la interfaz para que decidas si merece la pena implementarla.

Ejecuta:  python prototipo_ui.py
"""

import tkinter as tk
from dataclasses import dataclass
from typing import Callable

import customtkinter as ctk


# ═══════════════════════════════════════════════════════════════
#  TOKENS DE DISEÑO
# ═══════════════════════════════════════════════════════════════
class P:
    # Sidebar (oscura)
    SB_BG          = "#0F172A"
    SB_HOVER       = "#1E293B"
    SB_ACTIVE      = "#1E293B"
    SB_TEXT        = "#94A3B8"
    SB_TEXT_ACTIVE = "#F8FAFC"
    SB_SECTION     = "#64748B"
    SB_DIVIDER     = "#1E293B"

    # Superficie principal (clara)
    BG             = "#F8FAFC"
    CARD           = "#FFFFFF"
    CARD_ALT       = "#F1F5F9"
    BORDER         = "#E2E8F0"
    BORDER_STRONG  = "#CBD5E1"

    # Tipografía
    TXT            = "#0F172A"
    TXT_2          = "#475569"
    TXT_3          = "#94A3B8"
    TXT_INV        = "#FFFFFF"

    # Acento (índigo)
    ACCENT         = "#4F46E5"
    ACCENT_HOVER   = "#4338CA"
    ACCENT_SOFT    = "#EEF2FF"

    # Semánticos
    SUCCESS        = "#10B981"
    SUCCESS_SOFT   = "#ECFDF5"
    WARNING        = "#F59E0B"
    WARNING_SOFT   = "#FFFBEB"
    DANGER         = "#EF4444"
    DANGER_SOFT    = "#FEF2F2"
    INFO           = "#3B82F6"
    INFO_SOFT      = "#EFF6FF"

    R_CARD         = 12
    R_INPUT        = 8
    R_BTN          = 8


def F(size=12, weight="normal"):
    return ctk.CTkFont(family="Segoe UI", size=size, weight=weight)


def FM(size=11, weight="normal"):
    return ctk.CTkFont(family="Consolas", size=size, weight=weight)


# ═══════════════════════════════════════════════════════════════
#  COMPONENTES REUTILIZABLES
# ═══════════════════════════════════════════════════════════════
class Card(ctk.CTkFrame):
    """Tarjeta blanca con borde sutil."""
    def __init__(self, master, padding=20, **kw):
        super().__init__(master,
                         fg_color=P.CARD,
                         border_width=1,
                         border_color=P.BORDER,
                         corner_radius=P.R_CARD,
                         **kw)
        self._padding = padding


class StatCard(ctk.CTkFrame):
    """Tarjeta de KPI con etiqueta, valor y variación."""
    def __init__(self, master, etiqueta, valor, delta, color, icono="●"):
        super().__init__(master,
                         fg_color=P.CARD,
                         border_width=1,
                         border_color=P.BORDER,
                         corner_radius=P.R_CARD)
        self.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 0))

        ctk.CTkLabel(top, text=icono, font=F(16), text_color=color
                     ).pack(side="left")
        ctk.CTkLabel(top, text=etiqueta, font=F(11, "bold"),
                     text_color=P.TXT_3).pack(side="left", padx=(8, 0))

        ctk.CTkLabel(self, text=valor, font=F(26, "bold"),
                     text_color=P.TXT, anchor="w"
                     ).grid(row=1, column=0, sticky="ew", padx=18, pady=(6, 0))

        ctk.CTkLabel(self, text=delta, font=F(11),
                     text_color=color, anchor="w"
                     ).grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 16))


class NavItem(ctk.CTkFrame):
    """Elemento de la barra lateral con indicador activo."""
    def __init__(self, master, icono, texto, badge=None, comando=None):
        super().__init__(master, fg_color="transparent", height=38)
        self.pack_propagate(False)
        self._comando = comando
        self._activo = False

        # Barra lateral izquierda (indicador activo)
        self._barra = ctk.CTkFrame(self, width=3, corner_radius=2,
                                   fg_color=P.SB_ACTIVE)
        self._barra.pack(side="left", fill="y", pady=6, padx=(6, 0))
        self._barra.pack_forget()

        # Icono
        self._icono = ctk.CTkLabel(self, text=icono, font=F(14),
                                   text_color=P.SB_TEXT, width=20)
        self._icono.pack(side="left", padx=(12, 10))

        # Texto
        self._texto = ctk.CTkLabel(self, text=texto, font=F(12),
                                   text_color=P.SB_TEXT, anchor="w")
        self._texto.pack(side="left", fill="x", expand=True)

        # Badge opcional
        self._badge = None
        if badge:
            self._badge = ctk.CTkLabel(self, text=badge, font=F(9, "bold"),
                                       text_color=P.ACCENT,
                                       fg_color=P.ACCENT_SOFT,
                                       corner_radius=8,
                                       width=36, height=18)
            self._badge.pack(side="right", padx=(0, 12))

        # Hover
        for w in (self, self._icono, self._texto, self._barra):
            w.bind("<Enter>", self._on_enter, add="+")
            w.bind("<Leave>", self._on_leave, add="+")
            w.bind("<Button-1>", self._on_click, add="+")

    def _on_enter(self, _=None):
        if not self._activo:
            self.configure(fg_color=P.SB_HOVER)

    def _on_leave(self, _=None):
        if not self._activo:
            self.configure(fg_color="transparent")

    def _on_click(self, _=None):
        if self._comando:
            self._comando()

    def set_activo(self, activo: bool):
        self._activo = activo
        if activo:
            self.configure(fg_color=P.SB_ACTIVE)
            self._icono.configure(text_color=P.SB_TEXT_ACTIVE)
            self._texto.configure(text_color=P.SB_TEXT_ACTIVE,
                                  font=F(12, "bold"))
            self._barra.pack(side="left", fill="y", pady=6, padx=(6, 0))
        else:
            self.configure(fg_color="transparent")
            self._icono.configure(text_color=P.SB_TEXT)
            self._texto.configure(text_color=P.SB_TEXT, font=F(12))
            self._barra.pack_forget()


class SectionLabel(ctk.CTkLabel):
    def __init__(self, master, texto):
        super().__init__(master, text=texto.upper(), font=F(9, "bold"),
                         text_color=P.SB_SECTION, anchor="w")


class Btn(ctk.CTkButton):
    """Botón primario del sistema."""
    def __init__(self, master, texto, comando=None, icono="", tipo="primary",
                 ancho=120, height=36):
        colores = {
            "primary": (P.ACCENT, P.ACCENT_HOVER, P.TXT_INV),
            "secondary": (P.CARD, P.CARD_ALT, P.TXT),
            "ghost": (P.BG, P.CARD_ALT, P.TXT_2),
            "success": (P.SUCCESS, "#059669", P.TXT_INV),
            "danger":  (P.DANGER, "#DC2626", P.TXT_INV),
        }
        fg, hov, txt = colores.get(tipo, colores["primary"])
        etiqueta = f"{icono}  {texto}".strip()
        super().__init__(master, text=etiqueta, command=comando,
                         width=ancho, height=height,
                         corner_radius=P.R_BTN,
                         fg_color=fg, hover_color=hov,
                         text_color=txt,
                         border_width=1 if tipo == "secondary" else 0,
                         border_color=P.BORDER_STRONG if tipo == "secondary" else fg,
                         font=F(11, "bold"))


class InputField(ctk.CTkFrame):
    """Campo con etiqueta arriba y entrada debajo."""
    def __init__(self, master, etiqueta, placeholder="", ayuda="",
                 boton=None, **kw):
        super().__init__(master, fg_color="transparent", **kw)

        ctk.CTkLabel(self, text=etiqueta, font=F(11, "bold"),
                     text_color=P.TXT, anchor="w"
                     ).pack(anchor="w", pady=(0, 4))

        fila = ctk.CTkFrame(self, fg_color="transparent")
        fila.pack(fill="x")

        self.entry = ctk.CTkEntry(
            fila, placeholder_text=placeholder,
            height=38, corner_radius=P.R_INPUT,
            border_width=1, border_color=P.BORDER_STRONG,
            fg_color=P.CARD, text_color=P.TXT,
            placeholder_text_color=P.TXT_3,
            font=F(12))
        self.entry.pack(side="left", fill="x", expand=True)

        if boton:
            Btn(fila, boton[0], comando=boton[1], icono=boton[2],
                tipo="secondary", ancho=100, height=38
                ).pack(side="left", padx=(8, 0))

        if ayuda:
            ctk.CTkLabel(self, text=ayuda, font=F(10),
                         text_color=P.TXT_3, anchor="w"
                         ).pack(anchor="w", pady=(4, 0))


class SectionTitle(ctk.CTkFrame):
    """Título de sección con descripción opcional."""
    def __init__(self, master, titulo, descripcion=""):
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text=titulo, font=F(14, "bold"),
                     text_color=P.TXT, anchor="w"
                     ).pack(anchor="w")
        if descripcion:
            ctk.CTkLabel(self, text=descripcion, font=F(11),
                         text_color=P.TXT_2, anchor="w"
                         ).pack(anchor="w", pady=(2, 0))


class Badge(ctk.CTkLabel):
    def __init__(self, master, texto, color="info"):
        paleta = {
            "info":    (P.INFO_SOFT,    P.INFO),
            "success": (P.SUCCESS_SOFT, P.SUCCESS),
            "warning": (P.WARNING_SOFT, P.WARNING),
            "danger":  (P.DANGER_SOFT,  P.DANGER),
            "neutral": (P.CARD_ALT,     P.TXT_2),
        }
        fg, txt = paleta.get(color, paleta["neutral"])
        super().__init__(master, text=texto, font=F(10, "bold"),
                         text_color=txt, fg_color=fg,
                         corner_radius=10, padx=8, pady=2)


# ═══════════════════════════════════════════════════════════════
#  APLICACIÓN
# ═══════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class Modulo:
    clave: str
    emoji: str
    titulo: str
    descripcion: str
    color: str
    seccion: str


MODULOS = [
    Modulo("inicio",     "◆", "Dashboard",     "Vista general de la suite",              P.ACCENT,  "Principal"),
    Modulo("extractor",  "◈", "Extracción",    "Corta y clasifica lotes por palabra",    "#06B6D4", "Procesamiento"),
    Modulo("fusionador", "◇", "Fusionar",      "Une varios PDFs en uno solo",            "#10B981", "Procesamiento"),
    Modulo("divisor",    "◐", "Dividir",       "Separa un PDF por unidad",               "#F59E0B", "Procesamiento"),
    Modulo("compresor",  "◆", "Comprimir",     "Reduce el tamaño de tus PDFs",           "#3B82F6", "Procesamiento"),
    Modulo("visor",      "◉", "Visor",         "Explora cualquier PDF",                  "#EC4899", "Herramientas"),
]

MODULO_POR_CLAVE = {m.clave: m for m in MODULOS}


class PrototipoApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        self.title("CCpdf — Prototipo Enterprise")
        self.geometry("1280x820")
        self.minsize(1100, 720)
        self.configure(fg_color=P.BG)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._nav_items: dict[str, NavItem] = {}
        self._vistas: dict[str, ctk.CTkFrame] = {}
        self._clave_actual = "inicio"

        self._build_sidebar()
        self._build_topbar()
        self._build_content()
        self._show_view("inicio")

    # ─────────────────────────────────────────────
    #  SIDEBAR
    # ─────────────────────────────────────────────
    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=240, corner_radius=0,
                          fg_color=P.SB_BG)
        sb.grid(row=0, column=0, rowspan=2, sticky="nsew")
        sb.grid_propagate(False)
        self.sidebar = sb

        # Logo
        cab = ctk.CTkFrame(sb, fg_color="transparent", height=64)
        cab.pack(fill="x", padx=16, pady=(18, 8))
        cab.pack_propagate(False)

        logo = ctk.CTkFrame(cab, width=36, height=36,
                            corner_radius=10, fg_color=P.ACCENT)
        logo.pack(side="left")
        logo.pack_propagate(False)
        ctk.CTkLabel(logo, text="CC", font=F(14, "bold"),
                     text_color=P.TXT_INV).pack(expand=True)

        textos = ctk.CTkFrame(cab, fg_color="transparent")
        textos.pack(side="left", padx=(10, 0))
        ctk.CTkLabel(textos, text="CCpdf", font=F(15, "bold"),
                     text_color=P.TXT_INV, anchor="w").pack(anchor="w")
        ctk.CTkLabel(textos, text="Enterprise Edition", font=F(9),
                     text_color=P.SB_TEXT, anchor="w").pack(anchor="w")

        # Navegación agrupada por sección
        nav = ctk.CTkFrame(sb, fg_color="transparent")
        nav.pack(fill="x", padx=8, pady=(8, 0))

        seccion_actual = None
        for mod in MODULOS:
            if mod.seccion != seccion_actual:
                seccion_actual = mod.seccion
                SectionLabel(nav, seccion_actual).pack(
                    anchor="w", padx=14, pady=(14 if mod.clave != "inicio" else 0, 6))

            item = NavItem(nav, mod.emoji, mod.titulo,
                           comando=lambda c=mod.clave: self._show_view(c))
            item.pack(fill="x", padx=2, pady=1)
            self._nav_items[mod.clave] = item

        # Separador
        ctk.CTkFrame(sb, height=1, fg_color=P.SB_DIVIDER
                     ).pack(fill="x", padx=16, pady=(16, 0))

        # Sección inferior
        inferior = ctk.CTkFrame(sb, fg_color="transparent")
        inferior.pack(side="bottom", fill="x", padx=8, pady=12)

        for texto, icono in (("Configuración", "⚙"), ("Ayuda y soporte", "?")):
            it = NavItem(inferior, icono, texto)
            it.pack(fill="x", padx=2, pady=1)

        # Tarjeta de usuario
        user = ctk.CTkFrame(inferior, fg_color=P.SB_HOVER,
                            corner_radius=10)
        user.pack(fill="x", padx=4, pady=(10, 0))

        avatar = ctk.CTkFrame(user, width=32, height=32,
                              corner_radius=16, fg_color=P.ACCENT)
        avatar.pack(side="left", padx=10, pady=10)
        avatar.pack_propagate(False)
        ctk.CTkLabel(avatar, text="IK", font=F(11, "bold"),
                     text_color=P.TXT_INV).pack(expand=True)

        col = ctk.CTkFrame(user, fg_color="transparent")
        col.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(col, text="Iker", font=F(11, "bold"),
                     text_color=P.TXT_INV, anchor="w").pack(anchor="w")
        ctk.CTkLabel(col, text="Licencia Pro", font=F(9),
                     text_color=P.SB_TEXT, anchor="w").pack(anchor="w")

    # ─────────────────────────────────────────────
    #  TOPBAR
    # ─────────────────────────────────────────────
    def _build_topbar(self):
        top = ctk.CTkFrame(self, height=64, corner_radius=0,
                           fg_color=P.CARD,
                           border_width=0)
        top.grid(row=0, column=1, sticky="ew")
        top.grid_propagate(False)
        top.grid_columnconfigure(1, weight=1)
        self.topbar = top

        # Breadcrumb
        migas = ctk.CTkFrame(top, fg_color="transparent")
        migas.grid(row=0, column=0, sticky="w", padx=24, pady=18)

        self._bc_modulo = ctk.CTkLabel(migas, text="", font=F(13, "bold"),
                                       text_color=P.TXT)
        self._bc_modulo.pack(side="left")
        ctk.CTkLabel(migas, text="  /  ", font=F(13),
                     text_color=P.TXT_3).pack(side="left")
        ctk.CTkLabel(migas, text="CCpdf", font=F(13),
                     text_color=P.TXT_3).pack(side="left")

        # Buscador global
        buscador = ctk.CTkFrame(top, fg_color=P.BG, corner_radius=8,
                                border_width=1, border_color=P.BORDER,
                                width=320, height=36)
        buscador.grid(row=0, column=2, sticky="e", padx=(0, 16), pady=14)
        buscador.grid_propagate(False)

        ctk.CTkLabel(buscador, text="🔍", font=F(12),
                     text_color=P.TXT_3).pack(side="left", padx=(10, 6))
        ctk.CTkEntry(buscador, placeholder_text="Buscar archivos, acciones…",
                     border_width=0, fg_color="transparent",
                     text_color=P.TXT, placeholder_text_color=P.TXT_3,
                     font=F(11)).pack(side="left", fill="both", expand=True,
                                       padx=(0, 8))

        # Acciones derecha
        acc = ctk.CTkFrame(top, fg_color="transparent")
        acc.grid(row=0, column=3, sticky="e", padx=24)

        notif = ctk.CTkFrame(acc, width=36, height=36, corner_radius=8,
                             fg_color=P.BG, border_width=1,
                             border_color=P.BORDER)
        notif.pack(side="left", padx=(0, 8))
        notif.pack_propagate(False)
        ctk.CTkLabel(notif, text="🔔", font=F(13)).pack(expand=True)

        # Separador vertical
        ctk.CTkFrame(acc, width=1, height=24, fg_color=P.BORDER
                     ).pack(side="left", padx=8)

        Btn(acc, "Nuevo", icono="+", tipo="primary",
            ancho=100, height=36, comando=lambda: None).pack(side="left")

        # Línea inferior de separación
        ctk.CTkFrame(self, height=1, fg_color=P.BORDER
                     ).grid(row=0, column=1, sticky="ews")

    # ─────────────────────────────────────────────
    #  CONTENIDO
    # ─────────────────────────────────────────────
    def _build_content(self):
        wrap = ctk.CTkFrame(self, corner_radius=0, fg_color=P.BG)
        wrap.grid(row=1, column=1, sticky="nsew")
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(0, weight=1)
        self.content = wrap

        self._vistas["inicio"]     = self._view_dashboard()
        self._vistas["extractor"]  = self._view_modulo("extractor")
        self._vistas["fusionador"] = self._view_modulo("fusionador")
        self._vistas["divisor"]    = self._view_modulo("divisor")
        self._vistas["compresor"]  = self._view_modulo("compresor")
        self._vistas["visor"]      = self._view_modulo("visor")

    # ─── DASHBOARD ───
    def _view_dashboard(self):
        # Scrollable para que todo quepa
        scroll = ctk.CTkScrollableFrame(self.content, fg_color="transparent",
                                        corner_radius=0)
        scroll.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        interior = ctk.CTkFrame(scroll, fg_color="transparent")
        interior.pack(fill="both", expand=True, padx=36, pady=(28, 28))

        # Saludo
        ctk.CTkLabel(interior, text="Buenos días, Iker",
                     font=F(24, "bold"), text_color=P.TXT, anchor="w"
                     ).pack(anchor="w")
        ctk.CTkLabel(interior,
                     text="Martes, 9 de octubre de 2026  ·  Última sesión hace 2 horas",
                     font=F(12), text_color=P.TXT_2, anchor="w"
                     ).pack(anchor="w", pady=(4, 22))

        # KPIs
        stats = ctk.CTkFrame(interior, fg_color="transparent")
        stats.pack(fill="x")
        for i in range(4):
            stats.grid_columnconfigure(i, weight=1, uniform="stat")

        kpis = [
            ("Procesados hoy",   "42",   "+12% vs. ayer",     P.ACCENT,  "◆"),
            ("Esta semana",      "318",  "+8% vs. semana pas.", P.SUCCESS, "◈"),
            ("Espacio ahorrado", "1.2 GB", "compresión aplicada", P.INFO, "◇"),
            ("En cola",          "3",    "esperando proceso",  P.WARNING, "◐"),
        ]
        for i, (etq, val, delta, col, ico) in enumerate(kpis):
            StatCard(stats, etq, val, delta, col, ico).grid(
                row=0, column=i, padx=(0 if i == 0 else 6, 0), sticky="nsew")

        # Sección: acciones rápidas
        ctk.CTkLabel(interior, text="Acciones rápidas",
                     font=F(15, "bold"), text_color=P.TXT, anchor="w"
                     ).pack(anchor="w", pady=(28, 4))
        ctk.CTkLabel(interior,
                     text="Los flujos de trabajo más habituales, a un clic.",
                     font=F(11), text_color=P.TXT_2, anchor="w"
                     ).pack(anchor="w", pady=(0, 14))

        grid = ctk.CTkFrame(interior, fg_color="transparent")
        grid.pack(fill="x")
        for i in range(4):
            grid.grid_columnconfigure(i, weight=1, uniform="accion")

        acciones = [
            ("Extracción",  "Corta y clasifica lotes", "#06B6D4", "◈", "extractor"),
            ("Fusionar",    "Une varios en uno",       "#10B981", "◇", "fusionador"),
            ("Dividir",     "Separa por unidad",       "#F59E0B", "◐", "divisor"),
            ("Comprimir",   "Reduce el tamaño",        "#3B82F6", "◆", "compresor"),
        ]
        for i, (titulo, desc, col, ico, clave) in enumerate(acciones):
            tarjeta = self._accion_card(grid, titulo, desc, col, ico,
                                        lambda c=clave: self._show_view(c))
            tarjeta.grid(row=0, column=i, padx=(0 if i == 0 else 6, 0),
                         sticky="nsew")

        # Sección: actividad reciente
        ctk.CTkLabel(interior, text="Actividad reciente",
                     font=F(15, "bold"), text_color=P.TXT, anchor="w"
                     ).pack(anchor="w", pady=(28, 4))

        actividad = Card(interior, padding=0)
        actividad.pack(fill="x", pady=(14, 0))

        eventos = [
            ("✓", P.SUCCESS, "Extracción completada",
             "Lote_Octubre · 24 archivos · 3.2 s", "hace 12 min"),
            ("✓", P.SUCCESS, "Fusión completada",
             "expedientes_2026.pdf · 8 documentos", "hace 1 h"),
            ("!", P.WARNING, "Compresión sin mejora",
             "informe_final.pdf · ya estaba optimizado", "hace 2 h"),
            ("✓", P.SUCCESS, "División completada",
             "hospital_central.pdf · 12 unidades", "ayer 18:42"),
        ]
        for i, (ico, col, titulo, sub, tiempo) in enumerate(eventos):
            fila = ctk.CTkFrame(actividad, fg_color="transparent", height=56)
            fila.pack(fill="x", padx=0, pady=0)
            fila.pack_propagate(False)

            icono = ctk.CTkFrame(fila, width=32, height=32, corner_radius=16,
                                 fg_color=col)
            icono.pack(side="left", padx=20)
            icono.pack_propagate(False)
            ctk.CTkLabel(icono, text=ico, font=F(13, "bold"),
                         text_color=P.TXT_INV).pack(expand=True)

            col_ = ctk.CTkFrame(fila, fg_color="transparent")
            col_.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(col_, text=titulo, font=F(12, "bold"),
                         text_color=P.TXT, anchor="w").pack(anchor="w", pady=(8, 0))
            ctk.CTkLabel(col_, text=sub, font=F(10),
                         text_color=P.TXT_2, anchor="w").pack(anchor="w")

            ctk.CTkLabel(fila, text=tiempo, font=F(10),
                         text_color=P.TXT_3).pack(side="right", padx=20)

            if i < len(eventos) - 1:
                ctk.CTkFrame(actividad, height=1, fg_color=P.BORDER
                             ).pack(fill="x", padx=20)

        return scroll

    def _accion_card(self, master, titulo, desc, color, icono, comando):
        card = ctk.CTkFrame(master, fg_color=P.CARD,
                            border_width=1, border_color=P.BORDER,
                            corner_radius=P.R_CARD, height=130)
        card.grid_propagate(False)

        franja = ctk.CTkFrame(card, height=3, corner_radius=2, fg_color=color)
        franja.pack(fill="x", padx=14, pady=(14, 0))

        ctk.CTkLabel(card, text=icono, font=F(22),
                     text_color=color, anchor="w"
                     ).pack(anchor="w", padx=16, pady=(10, 4))

        ctk.CTkLabel(card, text=titulo, font=F(13, "bold"),
                     text_color=P.TXT, anchor="w"
                     ).pack(anchor="w", padx=16)

        ctk.CTkLabel(card, text=desc, font=F(10),
                     text_color=P.TXT_2, anchor="w",
                     wraplength=180, justify="left"
                     ).pack(anchor="w", padx=16, pady=(2, 0))

        def _hover_in(_):
            card.configure(border_color=color)
        def _hover_out(_):
            card.configure(border_color=P.BORDER)

        for w in (card, *card.winfo_children()):
            w.bind("<Enter>", _hover_in, add="+")
            w.bind("<Leave>", _hover_out, add="+")
            w.bind("<Button-1>", lambda e: comando(), add="+")

        return card

    # ─── VISTA GENÉRICA DE MÓDULO ───
    def _view_modulo(self, clave):
        mod = MODULO_POR_CLAVE[clave]
        scroll = ctk.CTkScrollableFrame(self.content, fg_color="transparent",
                                        corner_radius=0)
        scroll.grid(row=0, column=0, sticky="nsew")

        interior = ctk.CTkFrame(scroll, fg_color="transparent")
        interior.pack(fill="both", expand=True, padx=36, pady=(28, 28))

        # Cabecera del módulo
        cab = ctk.CTkFrame(interior, fg_color="transparent")
        cab.pack(fill="x")

        izq = ctk.CTkFrame(cab, fg_color="transparent")
        izq.pack(side="left", fill="x", expand=True)

        fila_titulo = ctk.CTkFrame(izq, fg_color="transparent")
        fila_titulo.pack(anchor="w")

        ctk.CTkLabel(fila_titulo, text=mod.emoji, font=F(22),
                     text_color=mod.color).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(fila_titulo, text=mod.titulo, font=F(20, "bold"),
                     text_color=P.TXT).pack(side="left")

        ctk.CTkLabel(izq, text=mod.descripcion, font=F(12),
                     text_color=P.TXT_2, anchor="w"
                     ).pack(anchor="w", pady=(4, 0))

        Btn(cab, "Ayuda", icono="?", tipo="ghost", ancho=90
            ).pack(side="right")

        # Layout de dos columnas
        layout = ctk.CTkFrame(interior, fg_color="transparent")
        layout.pack(fill="both", expand=True, pady=(22, 0))
        layout.grid_columnconfigure(0, weight=3, uniform="")
        layout.grid_columnconfigure(1, weight=1, uniform="")

        # ─── Columna izquierda (formulario) ───
        col_izq = ctk.CTkFrame(layout, fg_color="transparent")
        col_izq.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        # Tarjeta: entradas
        card_entrada = Card(col_izq)
        card_entrada.pack(fill="x")

        SectionTitle(card_entrada, "Origen y destino",
                     "Selecciona dónde buscar los PDFs y dónde guardar los resultados."
                     ).pack(anchor="w", padx=22, pady=(20, 16))

        InputField(card_entrada, "Carpeta de origen",
                   "Ej. /home/usuario/Documentos/PDFs",
                   boton=("Examinar", lambda: None, "📂")
                   ).pack(fill="x", padx=22, pady=(0, 14))

        InputField(card_entrada, "Carpeta de salida (opcional)",
                   "Se usará la carpeta configurada por defecto",
                   boton=("Examinar", lambda: None, "📂")
                   ).pack(fill="x", padx=22, pady=(0, 20))

        # Tarjeta: parámetros (adaptada por módulo)
        card_params = Card(col_izq)
        card_params.pack(fill="x", pady=(14, 0))

        SectionTitle(card_params, "Parámetros del proceso",
                     self._descripcion_modulo(clave)
                     ).pack(anchor="w", padx=22, pady=(20, 16))

        for etiqueta, ph in self._campos_modulo(clave):
            InputField(card_params, etiqueta, ph
                       ).pack(fill="x", padx=22, pady=(0, 14))

        # Checkboxes de ejemplo
        checks = ctk.CTkFrame(card_params, fg_color="transparent")
        checks.pack(fill="x", padx=22, pady=(4, 20))
        for texto, activo in (("Aplicar tolerancia ortográfica", True),
                              ("Solo coincidencia de palabra completa", False)):
            cb = ctk.CTkCheckBox(checks, text=texto,
                                 font=F(11),
                                 text_color=P.TXT,
                                 fg_color=P.ACCENT, hover_color=P.ACCENT_HOVER,
                                 border_color=P.BORDER_STRONG,
                                 checkmark_color=P.TXT_INV)
            if activo:
                cb.select()
            cb.pack(anchor="w", pady=4)

        # Barra de acciones
        acciones = ctk.CTkFrame(col_izq, fg_color="transparent")
        acciones.pack(fill="x", pady=(18, 0))

        Btn(acciones, "Limpiar", tipo="ghost", icono="↺", ancho=100
            ).pack(side="left")
        Btn(acciones, f"Ejecutar {mod.titulo}", icono="▶",
            tipo="primary", ancho=180, height=42
            ).pack(side="right")

        # ─── Columna derecha (info + progreso) ───
        col_der = ctk.CTkFrame(layout, fg_color="transparent")
        col_der.grid(row=0, column=1, sticky="nsew")

        # Tarjeta de estado
        estado = Card(col_der)
        estado.pack(fill="x")
        SectionTitle(estado, "Estado del proceso",
                     "Listo para comenzar."
                     ).pack(anchor="w", padx=18, pady=(18, 14))

        barra = ctk.CTkProgressBar(estado, height=6, corner_radius=3,
                                   fg_color=P.CARD_ALT,
                                   progress_color=P.ACCENT)
        barra.set(0.42)
        barra.pack(fill="x", padx=18)

        info = ctk.CTkFrame(estado, fg_color="transparent")
        info.pack(fill="x", padx=18, pady=(10, 18))
        ctk.CTkLabel(info, text="42 de 100 archivos",
                     font=F(10), text_color=P.TXT_3).pack(side="left")
        ctk.CTkLabel(info, text="42%", font=F(10, "bold"),
                     text_color=P.ACCENT).pack(side="right")

        # Registro
        log_card = Card(col_der)
        log_card.pack(fill="both", expand=True, pady=(14, 0))
        SectionTitle(log_card, "Registro",
                     "Últimas operaciones del motor."
                     ).pack(anchor="w", padx=18, pady=(18, 10))

        log = ctk.CTkTextbox(log_card, height=220,
                             fg_color=P.CARD_ALT,
                             text_color=P.TXT_2,
                             border_width=1,
                             border_color=P.BORDER,
                             corner_radius=8,
                             font=FM(10))
        log.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        log.insert("1.0",
                   "[12:42:03] Motor iniciado\n"
                   "[12:42:03] Leyendo origen: /Documentos/PDFs\n"
                   "[12:42:04] Encontrados 100 archivos PDF\n"
                   "[12:42:04] Procesando informe_001.pdf…\n"
                   "[12:42:05] ✓ informe_001.pdf → 3 páginas extraídas\n"
                   "[12:42:06] Procesando informe_002.pdf…\n"
                   "[12:42:06] ✓ informe_002.pdf → 7 páginas extraídas\n"
                   "[12:42:07] Procesando informe_003.pdf…")
        log.configure(state="disabled")

        return scroll

    # ─── Helpers para personalizar módulos ───
    def _descripcion_modulo(self, clave):
        return {
            "extractor":  "Configura el texto de corte y las opciones de búsqueda.",
            "fusionador": "Ordena los PDFs y decide dónde guardar el resultado.",
            "divisor":    "Pega o carga la lista de unidades a separar.",
            "compresor":  "Elige nivel de compresión y motor de procesado.",
            "visor":      "Abre un PDF para navegar y buscar dentro.",
        }.get(clave, "Ajusta los parámetros del proceso.")

    def _campos_modulo(self, clave):
        return {
            "extractor": [
                ("Texto donde detener el corte", "Ej. FIN DEL DOCUMENTO"),
                ("Segundo texto en la misma página (opcional)", "Se exige también esta cadena"),
            ],
            "fusionador": [
                ("Nombre del archivo resultante", "fusionado.pdf"),
                ("Orden de los archivos", "Se ordenan en la lista inferior"),
            ],
            "divisor": [
                ("Lista de unidades", "Unidad 1\nUnidad 2\nUnidad 3…"),
            ],
            "compresor": [
                ("Nivel de compresión", "Ligera / Media / Fuerte"),
            ],
            "visor": [
                ("Ruta del PDF", "/ruta/al/archivo.pdf"),
            ],
        }.get(clave, [])

    # ─────────────────────────────────────────────
    #  NAVEGACIÓN
    # ─────────────────────────────────────────────
    def _show_view(self, clave: str):
        if clave not in self._vistas:
            return
        for v in self._vistas.values():
            v.grid_forget()
        self._vistas[clave].grid(row=0, column=0, sticky="nsew")

        for c, item in self._nav_items.items():
            item.set_activo(c == clave)

        mod = MODULO_POR_CLAVE[clave]
        self._bc_modulo.configure(text=mod.titulo)
        self._clave_actual = clave


if __name__ == "__main__":
    PrototipoApp().mainloop()