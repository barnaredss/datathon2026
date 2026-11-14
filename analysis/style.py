"""Estilo común de matplotlib para todas las figuras de la presentación.

Uso:
    from analysis.style import apply, COLORS, save
    apply()
    ...
    save(fig, "eda_escala")      # -> figures/eda_escala.png (1600x900 px)
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "figures"

# Paleta segura para daltonismo (Okabe-Ito)
COLORS = {
    "precio": "#E69F00",
    "co2": "#0072B2",
    "senal": "#CC79A7",
    "carga": "#009E73",
    "descarga": "#D55E00",
    "demanda": "#333333",
    "solar": "#F0E442",
    "nuestro": "#009E73",
    "optimo": "#0072B2",
    "base": "#999999",
}


def apply():
    plt.rcParams.update({
        "figure.figsize": (8, 4.5),
        "figure.dpi": 200,
        "savefig.dpi": 200,
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.labelsize": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "legend.frameon": False,
        "figure.autolayout": True,
    })


def save(fig, name):
    FIG_DIR.mkdir(exist_ok=True)
    path = FIG_DIR / f"{name}.png"
    fig.savefig(path)
    plt.close(fig)
    return path
