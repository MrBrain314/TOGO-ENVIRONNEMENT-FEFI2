# -*- coding: utf-8 -*-
"""Profilage des 6 jeux de donnees du Defi 2 - Energie propre et inclusive au Togo."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd
pd.set_option("display.width", 200); pd.set_option("display.max_columns", 40)
RAW = r"C:\Projet DATA IA\TOGO-ENVIRONNEMENT 2\data\donnees_brutes"

def sep(t): print("\n" + "=" * 70 + f"\n### {t}\n" + "=" * 70)

# 1. MULTISECTORIEL (gros fichier)
sep("1. MULTISECTORIEL (electricite, cuisson, population, economie)")
m = pd.read_csv(RAW + r"\multisectoriel.csv")
print("shape:", m.shape, "| colonnes:", list(m.columns))
print(m.head(3).to_string())
# reperer la colonne d'indicateur
for c in m.columns:
    if m[c].dtype == object:
        nu = m[c].nunique()
        if 3 < nu < 2000:
            print(f"\ncolonne '{c}' : {nu} valeurs uniques")
# chercher indicateurs electricite/cuisson
txtcols = [c for c in m.columns if m[c].dtype == object]
if txtcols:
    ind_col = max(txtcols, key=lambda c: m[c].nunique())
    print(f"\n-> colonne indicateur probable : '{ind_col}'")
    inds = m[ind_col].dropna().unique()
    kw = ["electric", "électric", "cook", "cuis", "fuel", "combustib", "wood", "bois",
          "charcoal", "charbon", "rural", "urban", "population", "gdp", "pib", "energy", "énergie"]
    hits = [i for i in inds if any(k in str(i).lower() for k in kw)]
    print(f"indicateurs pertinents ({len(hits)}) :")
    for h in hits[:40]:
        print("   -", h)

for name, f in [("2. GES par secteur", "ges_secteur.csv"),
                ("3. Temperatures 10 villes", "temperatures.csv"),
                ("4. Energies renouvelables/biomasse", "energies_renouvelables.csv"),
                ("5. CO2 electricite 1970-2022", "co2_energie.csv"),
                ("6. Zones protegees / forets", "zones_protegees.csv")]:
    sep(name)
    d = pd.read_csv(RAW + "\\" + f)
    print("shape:", d.shape, "| colonnes:", list(d.columns))
    print(d.head(5).to_string())
