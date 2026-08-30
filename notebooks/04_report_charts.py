# -*- coding: utf-8 -*-
"""Graphes du rapport PowerPoint (matplotlib, couleurs du drapeau togolais)."""
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

BASE = r"C:\Projet DATA IA\TOGO-ENVIRONNEMENT 2"
DATA = os.path.join(BASE, "data")
OUT = os.path.join(BASE, "rapport", "img")
os.makedirs(OUT, exist_ok=True)

GREEN, RED, GOLD, INK, MUT, GRID = "#0A7C46", "#D21034", "#E0A422", "#16251A", "#5E685C", "#E4E8DE"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 13, "text.color": INK,
    "axes.edgecolor": "#CBD3C2", "axes.labelcolor": INK, "xtick.color": MUT, "ytick.color": MUT,
    "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150,
})
fr = lambda v, _=None: f"{v:,.0f}".replace(",", " ")


def save(fig, name):
    fig.tight_layout()
    p = os.path.join(OUT, name)
    fig.savefig(p, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("ecrit", p)


# 1. Fracture ville/campagne + projection
e = pd.read_csv(os.path.join(DATA, "electrification.csv")).dropna(subset=["rural", "urbain"], how="all")
er = e.dropna(subset=["rural"])
rec = er[er["annee"] >= 2010]
slope = np.polyfit(rec["annee"], rec["rural"], 1)[0]
ly = int(er["annee"].max()); lr = float(er[er.annee == ly]["rural"].iloc[0])
proj_year = int(round(ly + (99 - lr) / slope))
px = list(range(ly, proj_year + 1)); py = [min(100, lr + slope * (x - ly)) for x in px]
fig, ax = plt.subplots(figsize=(7.6, 4.2))
ax.fill_between(e["annee"], e["rural"], e["urbain"], color=RED, alpha=0.06)
ax.plot(e["annee"], e["urbain"], color=GREEN, lw=3, label="Urbain")
ax.plot(e["annee"], e["rural"], color=RED, lw=3, label="Rural")
ax.plot(e["annee"], e["national"], color=MUT, lw=1.4, ls=":", label="National")
ax.plot(px, py, color=GOLD, lw=2.4, ls="--", label=f"Projection rural (~{proj_year})")
ax.axhline(99, color=GREEN, lw=1, ls="--", alpha=.7)
ax.text(2000.5, 100.5, "Accès universel", color=GREEN, fontsize=10)
ax.axvline(2030, color=INK, lw=1.2, alpha=.6)
ax.text(2031, 4, "Objectif 2030", color=INK, fontsize=10)
ax.annotate(f"~{proj_year}", xy=(proj_year, 99), xytext=(proj_year - 9, 86), color=GOLD, fontsize=13,
            fontweight="bold", arrowprops=dict(arrowstyle="->", color=GOLD))
ax.set_ylim(0, 108); ax.set_xlim(2000, proj_year + 2)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
ax.legend(loc="center left", frameon=False, fontsize=10.5)
save(fig, "fracture.png")

# 2. Déforestation 1990-2021
s = pd.read_csv(os.path.join(DATA, "foret_surface.csv"))
fig, ax = plt.subplots(figsize=(7.6, 4.2))
ax.fill_between(s["annee"], s["surface_km2"], color=RED, alpha=0.10)
ax.plot(s["annee"], s["surface_km2"], color=RED, lw=3)
for i in (0, len(s) - 1):
    r = s.iloc[i]
    ax.annotate(f"{fr(r['surface_km2'])} km²", (r["annee"], r["surface_km2"]),
                textcoords="offset points", xytext=(0, 10 if i == 0 else -18),
                color=INK, fontsize=12, fontweight="bold", ha="center")
ax.set_ylim(0, s["surface_km2"].max() * 1.15)
ax.yaxis.set_major_formatter(FuncFormatter(fr))
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
save(fig, "deforestation.png")

# 3. Émissions par secteur
g = pd.read_csv(os.path.join(DATA, "emissions_secteur.csv")).sort_values("part_pct")
SHORT = {"Agriculture, Foresterie et autres Affectations des Terres (AFAT)": "Agriculture & forêts\n(AFAT)",
         "Energie": "Énergie", "Procédés Industriels et Utilisation des Produits (PIUP)": "Industrie (PIUP)",
         "Déchets": "Déchets"}
g["court"] = g["secteur"].map(lambda x: SHORT.get(x, x))
cols = [RED if x.strip().startswith("Energie") else (GREEN if "AFAT" in x else GOLD) for x in g["secteur"]]
fig, ax = plt.subplots(figsize=(7.6, 4.2))
ax.barh(g["court"], g["part_pct"], color=cols, height=0.62)
for y, v in enumerate(g["part_pct"]):
    ax.text(v + 1.5, y, f"{v:.0f}%", va="center", fontsize=12, fontweight="bold", color=INK)
ax.set_xlim(0, 100); ax.grid(axis="x", color=GRID); ax.set_axisbelow(True)
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
save(fig, "emissions.png")

# 4. Tendance climatique par ville
t = pd.read_csv(os.path.join(DATA, "temperatures_tendance.csv")).sort_values("lat")
t["dec"] = (t["pente_c_par_an"] * 10).round(2)
fig, ax = plt.subplots(figsize=(7.6, 4.6))
bars = ax.barh(t["villes"], t["dec"], color=[RED if v > 0 else GREEN for v in t["dec"]], height=0.62)
for y, v in enumerate(t["dec"]):
    ax.text(v + (0.03 if v >= 0 else -0.03), y, f"{v:+.2f}".replace(".", ","),
            va="center", ha="left" if v >= 0 else "right", fontsize=11, fontweight="bold", color=INK)
ax.axvline(0, color="#CBD3C2", lw=1)
ax.set_xlim(t["dec"].min() - 0.35, t["dec"].max() + 0.4)
ax.grid(axis="x", color=GRID); ax.set_axisbelow(True)
ax.set_xlabel("°C / décennie (2013-2019)")
save(fig, "climat.png")

print("\nOK - 4 graphes dans", OUT)
