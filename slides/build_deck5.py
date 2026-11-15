"""Presentación de 5 minutos (10 diapositivas) -> slides/presentacion.pptx

Uso: ./.venv/Scripts/python.exe slides/build_deck5.py
Todo el texto está en SLIDES. Las imágenes salen de slides/img/ (figuras sin título y capturas de Volta).
La versión larga anterior está en slides/presentacion_completa.pptx.
"""
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
IMG = HERE / "img"

TEAM = "hackers la l"
MEMBERS = "Alexander Hall Parrilla · Oscar Senesi Aladjem"

C = {
    "dark": RGBColor(0x0B, 0x24, 0x18), "dark2": RGBColor(0x12, 0x33, 0x24),
    "on_dark": RGBColor(0xEA, 0xF6, 0xEE), "muted_dark": RGBColor(0x8F, 0xB5, 0xA0), "mint": RGBColor(0x4F, 0xD0, 0x8E),
    "light": RGBColor(0xF5, 0xF9, 0xF6), "card": RGBColor(0xFF, 0xFF, 0xFF), "ink": RGBColor(0x0F, 0x2A, 0x1D),
    "muted": RGBColor(0x5A, 0x76, 0x66), "accent": RGBColor(0x1C, 0x9A, 0x57), "line": RGBColor(0xD5, 0xE5, 0xDA),
    "tint": RGBColor(0xE3, 0xF3, 0xE9), "sun": RGBColor(0xE2, 0xC9, 0x2E), "discharge": RGBColor(0x0E, 0x4F, 0x33),
}
F_HEAD, F_BODY = "Segoe UI Semibold", "Segoe UI"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


def new(dark=False):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = C["dark"] if dark else C["light"]
    return s


def text(s, x, y, w, h, lines, size=16, color="ink", font=F_BODY, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         spacing=None, line_space=1.08):
    """lines: str, or list of str / list of (text, overrides) runs per paragraph."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    if isinstance(lines, str):
        lines = [lines]
    for i, para in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_space
        runs = para if isinstance(para, list) else [(para, {})]
        for t, o in runs:
            r = p.add_run()
            r.text = t
            r.font.size = Pt(o.get("size", size))
            r.font.name = o.get("font", font)
            r.font.color.rgb = C[o.get("color", color)]
            r.font.bold = o.get("bold", False)
            sp = o.get("spacing", spacing)
            if sp:
                r.font._element.set("spc", str(sp))
    return tb


def eyebrow(s, t, dark=False, y=0.62):
    text(s, 0.8, y, 11, 0.3, t.upper(), size=12, color="mint" if dark else "accent", font=F_HEAD, spacing=250)


def headline(s, t, dark=False, size=34, y=0.95, w=11.8, h=1.0):
    text(s, 0.8, y, w, h, t, size=size, color="on_dark" if dark else "ink", font=F_HEAD, line_space=1.0)


def footer(s, n, dark=False):
    col = "muted_dark" if dark else "muted"
    text(s, 0.8, 7.0, 6, 0.25, f"{TEAM} · Repte UPC Sostenible · Datathon 2026", size=10, color=col)
    text(s, 11.9, 7.0, 0.65, 0.25, f"{n:02d}", size=10, color=col, align=PP_ALIGN.RIGHT)


def stat(s, x, y, w, num, label, dark=False, size=44, label_size=13):
    text(s, x, y, w, 0.8, num, size=size, color="mint" if dark else "accent", font=F_HEAD, line_space=0.95)
    text(s, x, y + size / 72 * 1.08, w, 0.7, label, size=label_size, color="muted_dark" if dark else "muted")


def card(s, x, y, w, h, fill="card", line=None, radius=0.08):
    sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.adjustments[0] = radius
    sh.fill.solid()
    sh.fill.fore_color.rgb = C[fill]
    if line:
        sh.line.color.rgb = C[line]
        sh.line.width = Pt(1)
    else:
        sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


def dot(s, x, y, d, color):
    sh = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    sh.fill.solid()
    sh.fill.fore_color.rgb = C[color]
    sh.line.fill.background()
    sh.shadow.inherit = False


def picture(s, name, x, y, w=None, h=None):
    """Place an image inside the box (x, y, w, h), keeping its aspect ratio and centring it."""
    iw, ih = Image.open(IMG / name).size
    ar = iw / ih
    if w and h:
        if w / h > ar:
            pw, ph = h * ar, h
        else:
            pw, ph = w, w / ar
        x, y = x + (w - pw) / 2, y + (h - ph) / 2
    elif w:
        pw, ph = w, w / ar
    else:
        pw, ph = h * ar, h
    return s.shapes.add_picture(str(IMG / name), Inches(x), Inches(y), Inches(pw), Inches(ph))


def notes(s, t):
    s.notes_slide.notes_text_frame.text = t


# ---------------------------------------------------------------- 1. portada
s = new(dark=True)
eyebrow(s, "Repte UPC Sostenible · Datathon 2026", dark=True, y=0.9)
text(s, 0.8, 1.45, 11.5, 2.6, ["La batería del campus,", "operada en el óptimo"], size=60, color="on_dark", font=F_HEAD, line_space=0.95)
text(s, 0.8, 3.75, 11, 0.4, [[(TEAM, {"color": "mint", "font": F_HEAD}), ("   " + MEMBERS, {})]], size=17, color="muted_dark")
for i, (num, lab) in enumerate([("42 t", "de CO₂ evitadas al año\ncon la batería actual"),
                                ("91.000 €", "ahorrados al año\nen la factura del campus"),
                                ("0", "infracciones\nen todas las entregas")]):
    stat(s, 0.8 + i * 4.0, 4.85, 3.6, num, lab, dark=True, size=52, label_size=14)
notes(s, "Somos hackers la l. Hemos diseñado cómo operar la batería del campus para contaminar menos y pagar menos: unas 42 "
         "toneladas de CO2 y 91.000 euros al año con la batería actual, sin una sola infracción. Os contamos cómo pensamos el problema.")

# ---------------------------------------------------------------- 2. datos
s = new()
eyebrow(s, "01 · Los datos")
headline(s, "Antes de modelar, miramos los datos")
picture(s, "eda_escala.png", 0.8, 2.0, w=7.4, h=4.6)
stat(s, 8.75, 2.05, 3.9, "2,4 %", "es la solar frente a la demanda del campus")
stat(s, 8.75, 3.45, 3.9, "99,5 %", "de las horas la demanda neta supera los 500 kW de la batería")
card(s, 8.75, 4.95, 3.85, 1.6, fill="tint")
text(s, 9.0, 5.12, 3.4, 1.3, [[("La batería nunca vierte a red. ", {"font": F_HEAD}),
                               ("No hay nada que predecir: es arbitraje puro.", {})]], size=15)
footer(s, 2)
notes(s, "Lo primero fue mirar los datos. La solar es el 2,4 % de la demanda y la demanda neta supera los 500 kW de la "
         "batería el 99,5 % de las horas. Todo lo que la batería descarga se consume en el campus. Predecir demanda o solar "
         "no aporta nada: es comprar energía barata y limpia y usarla cuando es cara y sucia.")

# ---------------------------------------------------------------- 3. idea
s = new()
eyebrow(s, "02 · La idea")
headline(s, "El Score es lineal: basta una señal por hora")
card(s, 0.8, 2.0, 6.1, 3.35, fill="dark", radius=0.06)
text(s, 1.15, 2.3, 5.5, 0.4, "Score = 70·ΔCO₂ + 30·ΔCoste", size=17, color="muted_dark")
text(s, 1.15, 2.85, 5.5, 0.4, "con el caso base constante, equivale a", size=13, color="muted_dark")
text(s, 1.15, 3.3, 5.6, 1.0, [[("minimizar  Σ importación × ", {}), ("w", {"color": "mint"})]], size=26, color="on_dark", font=F_HEAD)
text(s, 1.15, 3.95, 5.6, 0.6, [[("w = CO₂ + λ·precio", {"color": "mint"})]], size=26, font=F_HEAD)
text(s, 1.15, 4.65, 5.5, 0.6, "λ = 0,26 kg/€: la fórmula valora el CO₂ a ≈ 3.900 € por tonelada", size=14, color="on_dark")
for i, (num, lab) in enumerate([("75 %", "del beneficio posible si solo miras el precio"), ("91 %", "si solo miras el CO₂"),
                                ("99,9 %", "con los dos, en su peso justo")]):
    stat(s, 0.8 + i * 2.1, 5.6, 2.0, num, lab, size=28, label_size=11.5)
picture(s, "eda_precio_vs_co2.png", 7.3, 2.0, w=5.3, h=3.6)
text(s, 7.3, 5.75, 5.3, 0.7, "Precio y CO₂ no ordenan las horas igual: de madrugada la luz es barata pero sucia.", size=12.5, color="muted")
footer(s, 3)
notes(s, "La idea clave: como el caso base es constante, el Score es lineal en lo que importamos de la red. Se reduce a "
         "una sola señal por hora, CO2 más lambda por precio, y lambda sale de la propia fórmula. Solo precio da el 75 % "
         "del óptimo, solo CO2 el 91 %; los dos con el peso correcto, el 99,9 %.")

# ---------------------------------------------------------------- 4. solución
s = new()
eyebrow(s, "03 · La solución")
headline(s, "Un programa lineal exacto, resuelto cada hora")
steps = [("Leer", "precio y CO₂ conocidos y nivel de la batería"),
         ("Optimizar", "plan exacto de carga y descarga para las próximas horas"),
         ("Actuar", "solo la primera hora, con recorte de seguridad: 0 infracciones")]
for i, (t, d) in enumerate(steps):
    y = 2.0 + i * 1.5
    card(s, 0.8, y, 4.35, 1.3, fill="card", line="line")
    text(s, 1.05, y + 0.2, 0.6, 0.9, f"{i + 1}", size=34, color="accent", font=F_HEAD)
    text(s, 1.7, y + 0.2, 3.3, 0.4, t, size=18, font=F_HEAD)
    text(s, 1.7, y + 0.62, 3.3, 0.6, d, size=12.5, color="muted")
picture(s, "est_semana.png", 5.55, 2.0, w=7.1, h=4.15)
text(s, 5.55, 6.25, 7.1, 0.5, "Una semana real: carga en horas baratas y limpias, descarga en la punta. Unos 7 s para las 2.016 h.",
     size=12.5, color="muted")
footer(s, 4)
notes(s, "Con una sola señal, el problema es un programa lineal. Cada hora leemos lo que se conoce, resolvemos el plan exacto, "
         "aplicamos solo la primera hora y repetimos. Un recorte de seguridad garantiza cero infracciones. Tarda segundos y "
         "no depende de ningún modelo entrenado.")

# ---------------------------------------------------------------- 5. prueba
s = new()
eyebrow(s, "04 · La prueba")
headline(s, "Hace lo mismo que un plan que conoce el futuro")
picture(s, "std_cum.png", 0.8, 2.0, w=7.6, h=4.7)
stat(s, 8.9, 2.05, 3.7, "8,51 t", "de CO₂ evitado por nuestro agente en 10 semanas de validación")
stat(s, 8.9, 3.4, 3.7, "8,55 t", "por un plan que conoce de antemano precios, CO₂ y demanda")
card(s, 8.9, 4.95, 3.7, 1.6, fill="tint")
text(s, 9.15, 5.12, 3.25, 1.3, [[("No queda margen. ", {"font": F_HEAD}), ("Mirar solo el precio evita la mitad; la plantilla oficial, una quinta parte.", {})]], size=15)
footer(s, 5)
notes(s, "No nos quedamos en que funciona: lo demostramos. Lo comparamos con un plan que conoce el futuro: todos los precios, "
         "el CO2 y la demanda. En diez semanas de validación, nosotros evitamos 8,51 toneladas de CO2 y ese plan 8,55. Mirar solo "
         "el precio evita la mitad. No queda margen de mejora.")

# ---------------------------------------------------------------- 6. modo difícil
s = new()
eyebrow(s, "05 · Modo difícil")
headline(s, "Ahora sí hay que prever")
text(s, 0.8, 1.55, 11, 0.35, "Batería ×3  ·  solar ×12  ·  solo 3 h de precio y CO₂ conocidas", size=16, color="muted")
rows = [("Precio y CO₂", "una regresión por cada hora de adelanto", "accent"),
        ("Demanda", "perfil semanal + calendario de festivos de la UPC", "accent"),
        ("Solar de la hora", "árboles con la meteo de la última hora", "sun"),
        ("Descarga prudente", "lo que el campus no consume se pierde", "discharge")]
for i, (t, d, col) in enumerate(rows):
    y = 2.05 + i * 1.12
    dot(s, 0.85, y + 0.12, 0.22, col)
    text(s, 1.3, y, 4.2, 0.4, t, size=17, font=F_HEAD)
    text(s, 1.3, y + 0.42, 4.2, 0.5, d, size=13, color="muted")
picture(s, "hard_horas.png", 5.75, 2.0, w=6.9, h=4.2)
text(s, 5.75, 6.3, 6.9, 0.5, "Despacho medio por hora: nuestro agente (verde) frente al plan que conoce el futuro (azul).",
     size=12.5, color="muted")
footer(s, 6)
notes(s, "El modo difícil cambia el problema. Ahora sobra sol al mediodía y solo vemos tres horas de mercado. Mantenemos el mismo "
         "optimizador y le damos tres previsiones: precio y CO2 con una regresión, demanda con el perfil semanal y el calendario "
         "de festivos de la UPC, y la solar de la hora con árboles. Y descargamos con prudencia, porque lo que el campus no "
         "consume se pierde. Nuestro despacho por hora es casi el del plan que conoce el futuro.")

# ---------------------------------------------------------------- 7. lo que falta
s = new()
eyebrow(s, "06 · Lo que aprendimos")
headline(s, "Sabemos qué información vale más")
picture(s, "hard_valor.png", 0.8, 2.0, w=7.9, h=4.7)
stat(s, 9.1, 2.05, 3.5, "93 %", "del beneficio de un plan perfecto, solo con previsiones")
stat(s, 9.1, 3.4, 3.5, "96 %", "si supiéramos la solar de esta hora o el precio de mañana")
card(s, 9.1, 4.95, 3.5, 1.6, fill="tint")
text(s, 9.35, 5.1, 3.05, 1.4, [[("Calendario sí, tiempo real no. ", {"font": F_HEAD}), ("Los festivos se conocen de antemano; el tiempo real del test sería conocer la respuesta.", {})]], size=14)
footer(s, 7)
notes(s, "Medimos qué aporta cada pieza frente a un plan perfecto: perfiles medios 88 %, con la regresión 91, con la descarga "
         "prudente y la solar 93. Y dimos al agente información perfecta por partes: saber la solar de esta hora o el precio de "
         "mañana lo llevaría al 96 %. Son las dos piezas que más valen. Usamos el calendario de festivos, que se conoce de "
         "antemano, pero no el tiempo real del test: eso sería conocer la respuesta.")

# ---------------------------------------------------------------- 8. Volta
s = new(dark=True)
eyebrow(s, "07 · Volta", dark=True)
text(s, 0.8, 1.0, 4.2, 0.9, "This is Volta.", size=40, color="on_dark", font=F_HEAD)
text(s, 0.8, 1.95, 3.9, 1.3, "Explica cada decisión de la batería y dice al campus cuándo consumir y cuándo aplazar.",
     size=15, color="muted_dark", line_space=1.15)
states = [("sun", "Gafas de sol", "carga con sol gratis"), ("mint", "Energía al campus", "descarga en horas de más CO₂"),
          ("muted_dark", "Duerme", "cuando no compensa mover energía")]
for i, (col, t, d) in enumerate(states):
    y = 3.55 + i * 0.95
    dot(s, 0.85, y + 0.1, 0.2, col)
    text(s, 1.25, y, 3.6, 0.35, t, size=15, color="on_dark", font=F_HEAD)
    text(s, 1.25, y + 0.36, 3.6, 0.4, d, size=12.5, color="muted_dark")
picture(s, "volta_dark.png", 5.0, 0.9, w=7.75, h=5.8)
footer(s, 8, dark=True)
notes(s, "Y para que todo esto sirva a quien usa el campus, hicimos Volta. Hora a hora dice qué hace la batería y por qué, y qué "
         "conviene hacer en el campus. Se pone gafas de sol cuando carga con sol, manda energía al campus cuando la red es cara "
         "y sucia, y duerme cuando no compensa. Si hay tiempo, demo de 15 segundos: ui/bot_local.html, botón Reproducir.")

# ---------------------------------------------------------------- 9. UPC
s = new()
eyebrow(s, "08 · Para UPC Sostenible")
headline(s, "El mismo optimizador sirve para decidir inversiones")
picture(s, "whatif_dimensionado.png", 0.8, 2.0, w=7.9, h=4.4)
text(s, 0.8, 6.45, 7.9, 0.4, "Ahorro y CO₂ evitado al año según capacidad y potencia. Recuadro: la batería actual.", size=12, color="muted")
stat(s, 9.1, 2.05, 3.5, "+98 %", "de ahorro duplicando energía y potencia (solo una: +22 %)", size=40)
stat(s, 9.1, 3.55, 3.5, "1.900 €", "al año por cada punto de rendimiento de la batería", size=40)
stat(s, 9.1, 5.05, 3.5, "79 %", "del óptimo con un horario fijo, sin optimizador", size=40)
footer(s, 9)
notes(s, "El mismo optimizador responde preguntas de inversión. Energía y potencia se necesitan: duplicar las dos casi duplica el "
         "ahorro. Cada punto de rendimiento vale unos 1.900 euros al año. Y un horario fijo, cargar a mediodía y descargar por la "
         "tarde, ya logra el 79 % del óptimo.")

# ---------------------------------------------------------------- 10. cierre
s = new(dark=True)
eyebrow(s, "Conclusión", dark=True, y=0.9)
text(s, 0.8, 1.45, 11.5, 1.8, ["Entender el problema", "antes de modelarlo"], size=54, color="on_dark", font=F_HEAD, line_space=0.95)
text(s, 0.8, 3.45, 11.7, 0.5, "Datos  →  una señal  →  óptimo demostrado  →  previsiones medidas  →  Volta", size=18, color="mint", font=F_HEAD)
stat(s, 0.8, 4.5, 4.0, "42 t", "de CO₂ evitadas al año con la batería actual", dark=True, size=52, label_size=14)
stat(s, 4.8, 4.5, 4.0, "91.000 €", "ahorrados al año", dark=True, size=52, label_size=14)
text(s, 9.0, 4.62, 3.6, 0.8, "Gracias", size=40, color="on_dark", font=F_HEAD, align=PP_ALIGN.RIGHT)
text(s, 9.0, 5.45, 3.6, 0.4, TEAM, size=15, color="muted_dark", align=PP_ALIGN.RIGHT)
text(s, 0.8, 6.75, 11.5, 0.3, "Anualizado desde el año de entrenamiento oficial. Solo datos oficiales y el calendario público.", size=10, color="muted_dark")
notes(s, "En resumen: entendimos el problema antes de modelarlo. Los datos dicen que es arbitraje; el Score se reduce a una señal; "
         "el programa lineal es óptimo y lo demostramos; en el modo difícil medimos qué aporta cada previsión; y Volta lo explica "
         "al campus. Unas 42 toneladas de CO2 y 91.000 euros al año. Gracias.")

import sys
OUT = HERE / (sys.argv[1] if len(sys.argv) > 1 else "presentacion.pptx")
prs.save(OUT)
print("OK %d diapositivas -> %s" % (len(prs.slides), OUT.name))
