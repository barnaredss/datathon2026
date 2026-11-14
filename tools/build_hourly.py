"""Builds data/hourly_train.csv from the raw kit CSVs (official pipeline from the statement).
Usage: python tools/build_hourly.py
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data" / "train"

c = pd.read_csv(D / "contador.csv", parse_dates=["Fecha"]).set_index("Fecha")
load = (-c["Contador - POTENCIA ACTIVA EXPORTADA (kW)"]).clip(lower=0, upper=5000).resample("1h").mean().dropna()
inv = pd.read_csv(D / "inversor.csv", parse_dates=["Fecha"]).set_index("Fecha")
cols = [x for x in inv.columns if "POTENCIA ACTIVA" in x and "FASE" not in x and "SETPOINT" not in x]
pv = inv[cols].sum(axis=1).clip(lower=0).resample("1h").mean().dropna()
p = pd.read_csv(D / "precio_pvpc.csv", parse_dates=["Fecha"]).set_index("Fecha")
k = pd.read_csv(D / "co2_red.csv", parse_dates=["Fecha"]).set_index("Fecha")

df = pd.DataFrame({"load_kw": load, "pv_kw": pv,
                   "precio_eur_per_kwh": p["precio_eur_per_kwh"],
                   "co2_kg_per_kwh": k["co2_kg_per_kwh"]}).dropna()
df.to_csv(ROOT / "data" / "hourly_train.csv")
# price + CO2 alone cover more hours than the load (useful for signal studies)
pk = pd.DataFrame({"precio_eur_per_kwh": p["precio_eur_per_kwh"], "co2_kg_per_kwh": k["co2_kg_per_kwh"]}).dropna()
pk.to_csv(ROOT / "data" / "hourly_price_co2.csv")
print(f"hourly_train.csv: {len(df)} h  [{df.index.min()} -> {df.index.max()}] | PV cols used: {cols}")
print(f"hourly_price_co2.csv: {len(pk)} h")
