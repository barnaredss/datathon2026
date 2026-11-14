# -*- coding: utf-8 -*-
"""Genera slides/presentacion.pptx. TODO el texto esta en TEAM, MEMBERS, LB y SLIDES (arriba)."""
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from PIL import Image

TEAM = "hackers la l"
MEMBERS = "Alexander Hall Parrilla · Oscar Senesi Aladjem"
LB = {"score": "6,43", "dco2": "5,96 %", "dcoste": "7,52 %", "infr": "0"}

SLIDES = [
 {"kind": "cover",
  "title": "La batería del campus, operada en el óptimo",
  "subtitle": "Repte UPC Sostenible · Datathon 2026",
  "kpis": [(LB["score"], "Score en el leaderboard público"),
           (LB["infr"], "infracciones"),
           ("99,9 %", "del óptimo teórico con información perfecta")],
  "notes": "Presentamos cómo operamos la batería del campus y por qué creemos que no se puede hacer mucho mejor. Los tres números de la portada resumen el resultado. Fuente: analysis/strategy_findings.md, puntos 1 y 6."},
 {"kind": "formula",
  "title": "Decidir cada hora sin conocer la demanda futura",
  "formula": "Score = 70·ΔCO2 + 30·ΔCoste − 0,20·infracciones",
  "bullets": ["Batería de 2.000 kWh, ±500 kW y 90 % de rendimiento ida y vuelta.",
              "Una decisión por hora durante 2.016 h de test.",
              "Conocemos precio y CO2 de las próximas 24 h.",
              "No conocemos la demanda ni la solar futuras."],
  "notes": "Este es el reto: operar la batería hora a hora y maximizar el Score oficial. Solo vemos 24 horas de precio y CO2 hacia delante. Fuente: analysis/strategy_findings.md, puntos 1 y 6 (parámetros del reto en CLAUDE.md)."},
 {"kind": "fig_text",
  "title": "La solar es el 2,4 % de la demanda: la batería nunca vierte a red",
  "figure": "eda_escala.png",
  "bullets": ["La solar es solo el 2,4 % de la energía consumida.",
              "La demanda neta supera 500 kW en el 99,5 % de las horas.",
              "Nunca es negativa: la batería nunca exporta a la red.",
              "Prever demanda o solar no aporta nada."],
  "notes": "La escala lo decide todo. Con una solar tan pequeña, toda la energía que la batería descarga se consume en el campus. Por tanto el problema es arbitraje puro de precio y CO2. Fuente: analysis/eda_findings.md, puntos 10 y 11."},
 {"kind": "callouts",
  "title": "Los datos tienen fallos y los hemos tenido en cuenta",
  "callouts": [("Contador congelado", "Cada noche, de 22:05 a 06:00, repite un solo valor: el 33,5 % de las filas."),
               ("Noviembre de 2025 sin datos", "Los cuatro ficheros de sensores solo tienen una fila ese mes."),
               ("15 horas con demanda 0", "Son averías del medidor, no consumo real.")],
  "bullets": ["No construimos la estrategia sobre un modelo de demanda, y protegimos el controlador frente a averías del contador."],
  "notes": "Auditamos los datos antes de modelar. La demanda nocturna es desconocida y hay huecos y ceros por averías. Por eso no fiamos la estrategia a un modelo de demanda. Fuente: analysis/eda_findings.md, puntos 2, 5 y 6."},
 {"kind": "fig_text",
  "title": "Precio y CO2 no ordenan las horas igual",
  "figure": "eda_precio_vs_co2.png",
  "bullets": ["Correlación horaria entre precio y CO2: r = 0,58.",
              "Ambos tienen su valle al mediodía y su pico por la tarde.",
              "De noche el CO2 es alto aunque el precio sea bajo.",
              "Hace falta una sola señal combinada."],
  "notes": "Si solo usáramos el precio, cargaríamos de noche con energía sucia. Si solo usáramos el CO2, ignoraríamos el coste. Necesitamos combinarlos con el peso correcto. Fuente: analysis/eda_findings.md, puntos 13 a 15."},
 {"kind": "formula",
  "title": "El Score es lineal: basta una sola señal por hora",
  "formula_lines": ["Score = 70·ΔCO2 + 30·ΔCoste, con bases constantes",
                    "→ minimizar la suma horaria de (importación de red) × w_t",
                    "w_t = CO2_t + λ·precio_t,   λ = (0,3/0,7)·CO2_base/Coste_base = 0,2593 kg/EUR"],
  "bullets": ["Lectura: la fórmula oficial valora una tonelada de CO2 en unos 3.900 EUR."],
  "notes": "Como las bases son constantes, el Score es lineal en lo que importamos de la red. La señal w_t reúne CO2 y precio con un único peso. El peso 0,2593 se calibró con datos oficiales; implica entre 3.857 y 3.973 EUR por tonelada. Fuente: analysis/whatif_findings.md, punto 4; analysis/strategy_findings.md, punto 3."},
 {"kind": "callouts",
  "title": "MPC con programación lineal exacta, cada hora",
  "callouts": [("1. Leer", "Precio y CO2 de las próximas 24 h y el nivel de la batería."),
               ("2. Optimizar", "LP exacto: carga, descarga, nivel y rendimiento, hora a hora."),
               ("3. Actuar", "Aplicar solo la primera hora, con recorte de seguridad. Repetir.")],
  "bullets": ["0 infracciones por construcción; respaldo por reglas si fallara el solver. "
              "Unos 7 s para las 2.016 h (límite 60 s); solo numpy y scipy, sin modelo entrenado."],
  "notes": "El controlador es simple y robusto. El LP incluye carga, descarga, nivel de batería y rendimiento. No hay modelo entrenado que pueda romperse. Fuente: analysis/strategy_findings.md, punto 6; agent/agent.py."},
 {"kind": "fig_text",
  "title": "Carga al mediodía barato y limpio, descarga en la punta",
  "figure": "est_semana.png",
  "bullets": ["Carga en el valle del mediodía y algunas noches.",
              "Descarga en la punta de la tarde-noche.",
              "Unos 1,4 ciclos equivalentes por día."],
  "notes": "Una semana típica de diciembre: la batería hace lo que haría una persona con buen criterio, pero decidiendo con la señal combinada. Fuente: analysis/strategy_findings.md, puntos 4 y 6."},
 {"kind": "optimal",
  "title": "¿Es óptimo? Sí: 99,9 % de la cota teórica",
  "figure": "est_escalera.png",
  "kpis": [("5,6667", "frente a 5,6753 (entrenamiento, 99,85 %)"),
           ("6,1241", "frente a 6,1250 (semanas tipo test, 99,99 %)")],
  "bullets": ["Solo precio alcanza el 73-76 %; solo CO2, el 91-92 %."],
  "notes": "Comparamos contra un LP con información perfecta de todo el año. Estamos a menos de un 0,15 % en entrenamiento. No hay margen real de mejora. Fuente: analysis/strategy_findings.md, punto 1."},
 {"kind": "rows",
  "title": "Probamos y descartamos, con números",
  "figure": "est_horizonte.png",
  "rows": [("Predecir demanda o solar", "Como máximo +0,007 puntos."),
           ("Más horizonte", "Con 12 h ya se obtiene 6,1235 de 6,1241."),
           ("Calibrar λ", "Nuestro valor está en el máximo del barrido."),
           ("Avería del contador", "Supusimos la semana de noviembre sin demanda y creamos una protección (recupera hasta el 98 % de la pérdida simulada). El resultado en el leaderboard fue idéntico: la hipótesis era falsa para este test. La protección queda solo como robustez.")],
  "notes": "Descartamos con números, no con opiniones. La última fila es honesta: la hipótesis de la avería no se cumplió y no aporta puntos. Fuente: analysis/strategy_findings.md, puntos 2, 3 y 6; analysis/outage_findings.md, resultado en el leaderboard."},
 {"kind": "fig_text",
  "title": "El mismo optimizador responde a las preguntas de UPC Sostenible",
  "figure": "whatif_dimensionado.png",
  "bullets": ["Duplicar energía o potencia da +22 %; las dos, +98 %. Para el CO2, más kWh.",
              "Cada punto de rendimiento vale unos 1.900 EUR/año.",
              "Más solar ayuda a la batería solo desde 4,25 veces la actual.",
              "Un horario fijo de operador logra el 79 % del óptimo (en muestra)."],
  "text_size": 16,
  "notes": "El mismo optimizador responde a preguntas de planificación. La regla fija (cargar 12-16 h, descargar 18-21 h en invierno y 20-23 h en verano) es seguible por un operador; su 79 % está medido sobre los datos con los que se ajustó. Fuente: analysis/whatif_findings.md, puntos 1, 2, 3 y 5."},
 {"kind": "conclusions",
  "title": "Estamos en el techo teórico, y sabemos por qué",
  "bullets": ["Los datos mandan: con una solar del 2,4 %, es arbitraje, no predicción.",
              "El Score es lineal: una señal y un LP exacto dan el 99,9 % del óptimo.",
              "0 infracciones, 7 s de cálculo y un controlador robusto ante averías.",
              "El mismo optimizador sirve a UPC para dimensionar y planificar."],
  "kpis": [("42 t CO2/año", "evitadas (anualizado desde el año de entrenamiento)"),
           ("91.000 EUR/año", "ahorrados (anualizado desde el año de entrenamiento)")],
  "notes": "Cerramos con tres ideas y dos cifras anualizadas desde el entrenamiento. Fuente: analysis/strategy_findings.md, punto 6 (42,30 t y 91.380 EUR al año)."},
 # ---- Material de apoyo ----
 {"kind": "divider", "title": "Material de apoyo",
  "notes": "Diapositivas de apoyo para preguntas. Fuente: analysis/*.md."},
 {"kind": "bullets",
  "title": "B1. Formulación del LP en notación simple",
  "bullets": ["Variables por hora: carga c_t, descarga d_t, nivel de batería s_t.",
              "Restricciones: 0 ≤ c_t, d_t ≤ 500 kW; 0 ≤ s_t ≤ 2.000 kWh.",
              "Dinámica: s_t+1 = s_t + η·c_t − d_t/η, con η = √0,9.",
              "Objetivo: minimizar Σ w_t·(import_t), con import_t = demanda_t + c_t − d_t."],
  "notes": "Formulación del LP que resuelve el agente. La demanda neta es siempre mayor que la descarga, así que no hay exportación. Fuente: agent/agent.py; analysis/eda_findings.md, punto 11."},
 {"kind": "fig_text",
  "title": "B2. Frontera CO2-coste y peso del 70/30",
  "figure": "est_pareto.png",
  "bullets": ["Solo CO2 (λ = 0): ΔCO2 6,110 %, ΔCoste 4,607 %.",
              "Nuestro λ = 0,2593: score 6,1241, el máximo del barrido.",
              "Subir el peso del CO2 a 1 cuesta unos 11.465 EUR por tonelada."],
  "notes": "La curva es cóncava: el último CO2 es cada vez más caro. Fuente: analysis/strategy_findings.md, punto 3; analysis/whatif_findings.md, punto 4."},
 {"kind": "two_figs",
  "title": "B3. Rendimiento y solar: qué compensa mejorar",
  "figures": ["whatif_rendimiento.png", "whatif_solar.png"],
  "bullets": ["Rendimiento 90 % → 98 %: +15.355 EUR/año (+16,9 %).",
              "Sin excedente solar, más FV no mejora el valor de la batería."],
  "notes": "Dos figuras de planificación. Fuente: analysis/whatif_findings.md, puntos 2 y 3."},
 {"kind": "table",
  "title": "B4. Robustez ante averías del contador: v2 frente a v1",
  "header": ["Escenario (pseudo-test)", "Cota", "v1", "v2"],
  "table": [["Normal", "6,1250", "6,1241", "6,1241"],
            ["3.ª semana sin datos", "6,5090", "6,4591", "6,5078"],
            ["1.ª semana sin datos", "6,3280", "6,3099", "6,3220"],
            ["Última semana sin datos", "5,6202", "5,4469", "5,4867"],
            ["3.ª y última sin datos", "5,9830", "5,7300", "5,8308"],
            ["Una semana con demanda de 200 kW", "6,4770", "6,3725", "6,4428"]],
  "bullets": ["Sin avería, v2 es idéntico a v1; 0 infracciones en todos los escenarios."],
  "notes": "Tabla de robustez. En el leaderboard v1 y v2 dieron el mismo resultado. Fuente: analysis/outage_findings.md, tabla de resultados."},
 {"kind": "fig_text",
  "title": "B5. La regla del operador recoge el 79 % del óptimo",
  "figure": "whatif_operador.png",
  "bullets": ["Cargar de 12 a 16 h; descargar 18-21 h en invierno y 20-23 h en verano.",
              "Da 4,4945, el 79,2 % del óptimo (ajustada sobre train).",
              "El 21 % restante exige mirar precio y CO2 del día."],
  "notes": "La regla es una referencia para el operador. Fuente: analysis/whatif_findings.md, punto 5."},
 {"kind": "table",
  "title": "B6. Media semana de test se mueve 0,14; el test completo, 0,01",
  "header": ["Peso λ", "Test completo", "1.ª mitad de cada semana", "2.ª mitad"],
  "table": [["0,18", "6,1164", "7,1099", "4,9948"],
            ["0,21", "6,1219", "7,1218", "4,9928"],
            ["0,23", "6,1248", "7,0279", "5,1036"],
            ["0,2593 (nuestro)", "6,1241", "7,0237", "5,1055"],
            ["0,27", "6,1212", "6,9784", "5,1475"],
            ["0,32", "6,1133", "6,9905", "5,1158"]],
  "bullets": ["Lo que gana una mitad lo pierde la otra: las diferencias pequeñas en el leaderboard son ruido del reparto."],
  "notes": "El leaderboard público puntúa la mitad de las horas, pero la batería se simula sobre todas. Un cambio mínimo de λ mueve una carga o una descarga al otro lado del reparto. El test completo apenas cambia. Fuente: analysis/split_noise_findings.md, puntos 1 a 3."},
]

# ------------------------------------------------------------------ diseño
TXT = RGBColor(0x22, 0x22, 0x22); ACC = RGBColor(0x00, 0x9E, 0x73); GRY = RGBColor(0x66, 0x66, 0x66)
LIGHT = RGBColor(0xF3, 0xF6, 0xF5)
FONT = "Segoe UI"
ROOT = Path(__file__).resolve().parent
FIG = ROOT.parent / "figures"
W, H = 13.333, 7.5

prs = Presentation(); prs.slide_width = Inches(W); prs.slide_height = Inches(H)
blank = prs.slide_layouts[6]

def tb(s, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    t = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); tf = t.text_frame
    tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05); tf.margin_top = tf.margin_bottom = Inches(0.03)
    return tf

def run(p, text, size, color=TXT, bold=False):
    r = p.add_run(); r.text = text; f = r.font
    f.name = FONT; f.size = Pt(size); f.bold = bold; f.color.rgb = color
    return r

def para(tf, text, size, color=TXT, bold=False, first=False, align=None, space=6):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    if text:
        run(p, text, size, color, bold)
    p.space_after = Pt(space)
    if align is not None: p.alignment = align
    return p

def title(s, text, size=28):
    tf = tb(s, 0.5, 0.35, 12.3, 0.8, MSO_ANCHOR.MIDDLE); para(tf, text, size, TXT, True, first=True, space=0)
    ln = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.55), Inches(1.15), Inches(0.9), Inches(0.05))
    ln.fill.solid(); ln.fill.fore_color.rgb = ACC; ln.line.fill.background()

def footer(s, n):
    tf = tb(s, 0.5, 7.05, 9, 0.3); para(tf, "Repte UPC Sostenible · Datathon 2026 · " + TEAM, 10, GRY, first=True, space=0)
    tf = tb(s, 11.8, 7.05, 1.0, 0.3); para(tf, str(n), 10, GRY, first=True, align=PP_ALIGN.RIGHT, space=0)

def bullets(s, items, x, y, w, h, size=18):
    tf = tb(s, x, y, w, h)
    for i, b in enumerate(items):
        p = para(tf, "", size, first=(i == 0), space=10)
        run(p, "▪ ", size, ACC, True); run(p, b, size)
    return tf

def picture(s, name, x, y, w, h):
    im = Image.open(FIG / name); ar = im.width / im.height
    pw, ph = (w, w / ar) if w / h < ar else (h * ar, h)
    s.shapes.add_picture(str(FIG / name), Inches(x + (w - pw) / 2), Inches(y + (h - ph) / 2), Inches(pw), Inches(ph))

def kpi(s, x, y, w, h, num, label, numsize=36):
    box = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    box.fill.solid(); box.fill.fore_color.rgb = LIGHT; box.line.fill.background()
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(0.07), Inches(h))
    bar.fill.solid(); bar.fill.fore_color.rgb = ACC; bar.line.fill.background()
    tf = tb(s, x + 0.15, y + 0.05, w - 0.25, h - 0.1, MSO_ANCHOR.MIDDLE)
    para(tf, num, numsize, ACC, True, first=True, space=2); para(tf, label, 13, GRY, space=0)

def callout(s, x, y, w, h, head, text):
    box = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    box.fill.solid(); box.fill.fore_color.rgb = LIGHT; box.line.color.rgb = ACC; box.line.width = Pt(1.25)
    tf = tb(s, x + 0.15, y + 0.1, w - 0.3, h - 0.2)
    para(tf, head, 20, ACC, True, first=True, space=6); para(tf, text, 17, TXT, space=0)

def build(d, n):
    s = prs.slides.add_slide(blank); k = d["kind"]
    s.notes_slide.notes_text_frame.text = d["notes"]
    if k == "cover":
        tf = tb(s, 0.8, 1.2, 11.7, 1.6, MSO_ANCHOR.BOTTOM); para(tf, d["title"], 40, TXT, True, first=True, space=0)
        r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.85), Inches(2.95), Inches(1.4), Inches(0.07))
        r.fill.solid(); r.fill.fore_color.rgb = ACC; r.line.fill.background()
        tf = tb(s, 0.8, 3.15, 11.7, 1.4)
        para(tf, d["subtitle"], 20, GRY, first=True); para(tf, TEAM, 18, TXT, True, space=2); para(tf, MEMBERS, 16, GRY, space=0)
        for i, (a, b) in enumerate(d["kpis"]):
            kpi(s, 0.85 + i * 4.0, 5.0, 3.7, 1.5, a, b, 40)
        return
    title(s, d["title"]); footer(s, n)
    if k == "divider":
        tf = tb(s, 0.8, 3.0, 11, 1.2); para(tf, d["title"], 40, ACC, True, first=True)
    elif k == "formula":
        if "formula" in d:
            tf = tb(s, 0.5, 1.6, 12.3, 1.3, MSO_ANCHOR.MIDDLE)
            para(tf, d["formula"], 38, ACC, True, first=True, align=PP_ALIGN.CENTER, space=0)
            bullets(s, d["bullets"], 1.0, 3.5, 11.3, 3.3, 20)
        else:
            tf = tb(s, 0.7, 1.6, 11.9, 3.4)
            for i, l in enumerate(d["formula_lines"]):
                para(tf, l, 24 if i < 2 else 22, ACC if i == 0 else TXT, True, first=(i == 0), space=22)
            bullets(s, d["bullets"], 0.7, 5.3, 11.9, 1.5, 20)
    elif k == "bullets":
        bullets(s, d["bullets"], 0.8, 1.7, 11.7, 5.0, 20)
    elif k == "fig_text":
        picture(s, d["figure"], 0.45, 1.5, 8.2, 5.4)
        bullets(s, d["bullets"], 8.85, 1.6, 4.1, 5.2, d.get("text_size", 16))
    elif k == "two_figs":
        picture(s, d["figures"][0], 0.45, 1.4, 6.2, 3.8); picture(s, d["figures"][1], 6.7, 1.4, 6.2, 3.8)
        bullets(s, d["bullets"], 0.8, 5.5, 11.7, 1.4, 18)
    elif k == "callouts":
        for i, (a, b) in enumerate(d["callouts"]):
            callout(s, 0.55 + i * 4.15, 1.7, 3.95, 2.9, a, b)
        bullets(s, d["bullets"], 0.55, 5.1, 12.2, 1.5, 20)
    elif k == "optimal":
        picture(s, d["figure"], 0.4, 1.4, 9.0, 5.0)
        for i, (a, b) in enumerate(d["kpis"]):
            kpi(s, 9.6, 1.6 + i * 1.75, 3.3, 1.55, a, b, 34)
        bullets(s, d["bullets"], 0.55, 6.4, 12.2, 0.6, 16)
    elif k == "rows":
        y = 1.5
        for (a, b), h in zip(d["rows"], [0.75, 0.75, 0.75, 1.85]):
            box = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(y), Inches(8.0), Inches(h))
            box.fill.solid(); box.fill.fore_color.rgb = LIGHT; box.line.fill.background()
            bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(y), Inches(0.07), Inches(h))
            bar.fill.solid(); bar.fill.fore_color.rgb = ACC; bar.line.fill.background()
            tf = tb(s, 0.7, y + 0.03, 7.7, h - 0.06, MSO_ANCHOR.MIDDLE)
            p = para(tf, "", 16, first=True, space=0); run(p, a + ": ", 16, ACC, True); run(p, b, 16)
            y += h + 0.15
        picture(s, d["figure"], 8.7, 1.5, 4.3, 2.4)
    elif k == "conclusions":
        bullets(s, d["bullets"], 0.8, 1.6, 11.7, 2.6, 20)
        for i, (a, b) in enumerate(d["kpis"]):
            kpi(s, 0.85 + i * 6.0, 4.7, 5.6, 1.8, a, b, 40)
    elif k == "table":
        rows, cols = len(d["table"]) + 1, 4
        gt = s.shapes.add_table(rows, cols, Inches(0.8), Inches(1.6), Inches(11.7), Inches(0.5 * rows)).table
        for c, wd in enumerate([5.7, 2.0, 2.0, 2.0]): gt.columns[c].width = Inches(wd)
        for r in range(rows):
            for c in range(cols):
                cell = gt.cell(r, c); txt = d["header"][c] if r == 0 else d["table"][r - 1][c]
                cell.fill.solid(); cell.fill.fore_color.rgb = ACC if r == 0 else (LIGHT if r % 2 else RGBColor(255, 255, 255))
                p = cell.text_frame.paragraphs[0]
                run(p, txt, 16, RGBColor(255, 255, 255) if r == 0 else TXT, r == 0)
                if c: p.alignment = PP_ALIGN.RIGHT
        bullets(s, d["bullets"], 0.8, 5.5, 11.7, 1.2, 18)

for i, d in enumerate(SLIDES, 1):
    build(d, i)
prs.save(ROOT / "presentacion.pptx")
print("OK", len(SLIDES), "diapositivas")
