#!/usr/bin/env python3
"""
aplicar_confirmacion.py — Conecta el cuadro "¿Son la misma unidad?" a tu Inte.py.

Uso:
    python3 aplicar_confirmacion.py /home/iker/Escritorio/AAA/Interfaz/Inte.py

Hace una copia de seguridad (Inte.py.bak), agrega las piezas que faltan y avisa
de cualquier paso que no pudo aplicar. Se puede correr varias veces sin duplicar nada.
"""
import ast
import os
import re
import shutil
import sys

METODOS = '''    # ---------- CONFIRMACIÓN DE UNIDADES PARECIDAS ----------
    def _confirmar_desde_hilo(self, valor, unidad, paginas, indice, total):
        """Corre en el HILO del motor: pide la respuesta a la interfaz y espera."""
        respuesta, listo = {"ok": False}, threading.Event()
        self.cola.put(MsgPregunta(valor, unidad, paginas, indice, total, respuesta, listo))
        while not listo.wait(0.2):
            if self.evento_cancelar.is_set():
                return False
        return respuesta["ok"]

    def _preguntar(self, msg):
        """Corre en el hilo principal: muestra el cuadro Sí / No."""
        if self._panel_activo is not None:
            self._panel_activo.lbl_progreso.configure(
                text=f"Esperando tu confirmación ({msg.indice} de {msg.total})...")

        def responder(si):
            msg.respuesta["ok"] = si
            msg.listo.set()

        mostrar_dialogo_confirmacion(self, msg.valor, msg.unidad, msg.paginas,
                                     msg.indice, msg.total, responder)

'''


def p_import(t):
    m = re.search(r"^_preparar_path\(\)[ \t]*$", t, re.M)
    if not m:
        return None
    return t[:m.end()] + "\nfrom dialogo_confirmar import mostrar_dialogo_confirmacion" + t[m.end():]


def p_namedtuple(t):
    m = re.search(r"^MsgFin[ \t]*=[ \t]*namedtuple\([^\n]*\)[ \t]*$", t, re.M)
    if not m:
        return None
    nueva = '\nMsgPregunta = namedtuple("MsgPregunta", "valor unidad paginas indice total respuesta listo")'
    return t[:m.end()] + nueva + t[m.end():]


def p_metodos(t):
    m = (re.search(r"^[ \t]*# -+ BOMBEO DE LA COLA -+[ \t]*$", t, re.M)
         or re.search(r"^[ \t]*def _procesar_cola\(self\):", t, re.M))
    if not m:
        return None
    return t[:m.start()] + METODOS + t[m.start():]


def p_elif(t):
    m = re.search(r"^([ \t]*)elif isinstance\(msg, MsgFin\):\n[ \t]*self\._terminar\(msg\.resumen, msg\.error\)[ \t]*\n",
                  t, re.M)
    if not m:
        return None
    sangria = m.group(1)
    nuevo = (f"{sangria}elif isinstance(msg, MsgPregunta):\n"
             f"{sangria}    self._preguntar(msg)\n")
    return t[:m.end()] + nuevo + t[m.end():]


def p_kwargs(t):
    patron = r"kwargs = dict\(origen=origen, destino=destino, unidades=unidades\)"
    if not re.search(patron, t):
        return None
    return re.sub(patron,
                  "kwargs = dict(origen=origen, destino=destino, unidades=unidades,\n"
                  "                      callback_confirmar=self._confirmar_desde_hilo)", t, count=1)


def p_avisos(t):
    viejo = "hay_avisos = bool(errores or sin_texto or sin_paginas)"
    if viejo not in t:
        return None
    return t.replace(viejo, 'hay_avisos = bool(errores or sin_texto or sin_paginas '
                            'or _attr(resumen, "paginas_huerfanas", 0))', 1)


PASOS = [
    ("import del cuadro de diálogo", p_import, True),
    ("tipo de mensaje MsgPregunta", p_namedtuple, True),
    ("métodos _confirmar_desde_hilo y _preguntar", p_metodos, True),
    ("rama MsgPregunta en _procesar_cola", p_elif, True),
    ("callback_confirmar en _iniciar_division", p_kwargs, True),
    ("aviso final cuando quedan páginas sin asignar", p_avisos, False),   # opcional
]


def aplicar(texto):
    ok, fallos = [], []
    for nombre, fn, obligatorio in PASOS:
        nuevo = fn(texto)
        if nuevo is None:
            fallos.append((nombre, obligatorio))
        else:
            texto, _ = nuevo, ok.append(nombre)
    return texto, ok, fallos


def main():
    if len(sys.argv) != 2:
        sys.exit("Uso: python3 aplicar_confirmacion.py RUTA/Inte.py")
    ruta = sys.argv[1]
    if not os.path.isfile(ruta):
        sys.exit(f"No existe: {ruta}")
    texto = open(ruta, encoding="utf-8").read()

    if "def _confirmar_desde_hilo" in texto:
        sys.exit("Este archivo ya tiene la confirmación conectada. No se cambió nada.")

    nuevo, ok, fallos = aplicar(texto)
    graves = [n for n, obligatorio in fallos if obligatorio]
    if graves:
        print("✗ No se modificó nada. No encontré dónde aplicar:")
        for n in graves:
            print("   -", n)
        sys.exit("Tu Inte.py difiere de lo esperado; mándame ese archivo y lo adapto.")
    try:
        ast.parse(nuevo)
    except SyntaxError as e:
        sys.exit(f"✗ El resultado tenía un error de sintaxis ({e}); no se modificó nada.")

    respaldo, n = ruta + ".bak", 1
    while os.path.exists(respaldo):
        n += 1
        respaldo = f"{ruta}.bak{n}"
    shutil.copy2(ruta, respaldo)
    open(ruta, "w", encoding="utf-8").write(nuevo)

    print(f"✓ Listo. Copia de seguridad: {respaldo}")
    for nombre in ok:
        print("   +", nombre)
    for nombre, _ in fallos:
        print("   (omitido, opcional):", nombre)


if __name__ == "__main__":
    main()
