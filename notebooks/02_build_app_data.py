# -*- coding: utf-8 -*-
"""
Defi 2 - PANORAMA | Construction des tables du tableau de bord.
Re-derive les 6 sources + ajoute les indicateurs differenciants :
  - population absolue sans electricite (le % masque le drame)
  - coupures / fiabilite du reseau (objectif 1 du defi)
  - trajectoire de la superficie forestiere 1990-2021 (deforestation)
Ecrit tout dans data/.
"""
import sys, os, json, shutil
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely import wkt

BASE = r"C:\Projet DATA IA\TOGO-ENVIRONNEMENT 2"
RAW = os.path.join(BASE, "data", "donnees_brutes")
OUT = os.path.join(BASE, "data")
os.makedirs(OUT, exist_ok=True)


def log(t): print("\n" + "-" * 62 + f"\n{t}\n" + "-" * 62)


# ============================================================
# Source nationale (WDI multisectoriel)
# ============================================================
wdi = pd.read_csv(os.path.join(RAW, "multisectoriel.csv"))
wdi = wdi[wdi["Country ISO3"] == "TGO"].copy()
wdi["Year"] = pd.to_numeric(wdi["Year"], errors="coerce")
wdi["Value"] = pd.to_numeric(wdi["Value"], errors="coerce")


def serie(nom):
    s = wdi[wdi["Indicator Name"] == nom][["Year", "Value"]].dropna()
    return s.groupby("Year")["Value"].mean()


# ---- 1. ELECTRIFICATION + population absolue sans electricite ----
log("1. Electrification : % + nombre absolu de personnes sans electricite")
nat = serie("Access to electricity (% of population)").rename("national")
rur = serie("Access to electricity, rural (% of rural population)").rename("rural")
urb = serie("Access to electricity, urban (% of urban population)").rename("urbain")
pop_r = serie("Rural population").rename("pop_rurale")
pop_u = serie("Urban population").rename("pop_urbaine")
pop_t = serie("Population, total").rename("pop_tot")

elec = pd.concat([nat, rur, urb, pop_r, pop_u, pop_t], axis=1)
elec = elec[elec.index >= 2000].reset_index().rename(columns={"Year": "annee"})
elec["ecart_urbain_rural"] = (elec["urbain"] - elec["rural"]).round(1)
elec["sans_elec_rural"] = (elec["pop_rurale"] * (1 - elec["rural"] / 100)).round(0)
elec["sans_elec_urbain"] = (elec["pop_urbaine"] * (1 - elec["urbain"] / 100)).round(0)
elec["sans_elec_total"] = elec["sans_elec_rural"] + elec["sans_elec_urbain"]
for c in ["national", "rural", "urbain"]:
    elec[c] = elec[c].round(1)
elec.to_csv(os.path.join(OUT, "electrification.csv"), index=False, encoding="utf-8")
print(elec[["annee", "rural", "urbain", "sans_elec_total"]].tail(4).to_string(index=False))

# ---- 2. CUISSON PROPRE + population absolue au bois/charbon ----
log("2. Cuisson propre + nombre absolu au bois/charbon")
ck_n = serie("Access to clean fuels and technologies for cooking (% of population)").rename("national")
ck_r = serie("Access to clean fuels and technologies for cooking, rural (% of rural population)").rename("rural")
ck_u = serie("Access to clean fuels and technologies for cooking, urban (% of urban population)").rename("urbain")
cuisson = pd.concat([ck_n, ck_r, ck_u, pop_t.rename("pop_tot")], axis=1)
cuisson = cuisson[cuisson.index >= 2000].reset_index().rename(columns={"Year": "annee"})
cuisson["pop_sans_cuisson_propre"] = (cuisson["pop_tot"] * (1 - cuisson["national"] / 100)).round(0)
for c in ["national", "rural", "urbain"]:
    cuisson[c] = cuisson[c].round(1)
cuisson.to_csv(os.path.join(OUT, "cuisson.csv"), index=False, encoding="utf-8")
print(cuisson[["annee", "rural", "urbain", "pop_sans_cuisson_propre"]].tail(4).to_string(index=False))

# ---- 3. BIOMASSE ----
log("3. Biomasse dans l'energie totale")
bio = pd.read_csv(os.path.join(RAW, "energies_renouvelables.csv"))
bio["value"] = pd.to_numeric(bio["value"], errors="coerce")
bio = bio.dropna(subset=["value"])[["date", "value"]].rename(columns={"date": "annee", "value": "biomasse_pct"})
bio = bio.sort_values("annee").reset_index(drop=True)
bio["biomasse_pct"] = bio["biomasse_pct"].round(1)
bio.to_csv(os.path.join(OUT, "biomasse.csv"), index=False, encoding="utf-8")
print("Biomasse", int(bio["annee"].min()), "->", int(bio["annee"].max()), "| dernier", bio.iloc[-1].to_dict())

# ---- 4. COUPURES / FIABILITE DU RESEAU (differenciateur, objectif 1) ----
log("4. Coupures / fiabilite du reseau (enquetes entreprises)")
outg = pd.concat([
    serie("Firms experiencing electrical outages (% of firms)").rename("pct_firmes_coupees"),
    serie("Power outages in firms in a typical month (number)").rename("coupures_par_mois"),
    serie("Value lost due to electrical outages (% of sales for affected firms)").rename("pct_ventes_perdues"),
], axis=1).dropna(how="all").reset_index().rename(columns={"Year": "annee"})
outg = outg.round(1)
outg.to_csv(os.path.join(OUT, "coupures.csv"), index=False, encoding="utf-8")
print(outg.to_string(index=False))

# ---- 5. TRAJECTOIRE FORESTIERE 1990-2021 (deforestation) ----
log("5. Superficie forestiere nationale 1990-2021")
fa = serie("Forest area (sq. km)").rename("surface_km2")
fp = serie("Forest area (% of land area)").rename("pct_terres")
foret_ts = pd.concat([fa, fp], axis=1).dropna(how="all").reset_index().rename(columns={"Year": "annee"})
foret_ts["surface_km2"] = foret_ts["surface_km2"].round(0)
foret_ts["pct_terres"] = foret_ts["pct_terres"].round(2)
foret_ts.to_csv(os.path.join(OUT, "foret_surface.csv"), index=False, encoding="utf-8")
p0, p1 = foret_ts.iloc[0], foret_ts.iloc[-1]
print(f"{int(p0.annee)}: {p0.surface_km2:,.0f} km2 -> {int(p1.annee)}: {p1.surface_km2:,.0f} km2 "
      f"| perte {p0.surface_km2 - p1.surface_km2:,.0f} km2")

# ---- 6. GDP / capita (contexte) ----
gdp = serie("GDP per capita (current US$)").rename("pib_hab").reset_index().rename(columns={"Year": "annee"})
gdp["pib_hab"] = gdp["pib_hab"].round(0)
gdp[gdp["annee"] >= 1990].to_csv(os.path.join(OUT, "pib.csv"), index=False, encoding="utf-8")

# ============================================================
# 7. EMISSIONS (GES 2018 par secteur + par gaz + CO2 electricite)
# ============================================================
log("7. Emissions")
ges = pd.read_csv(os.path.join(RAW, "ges_secteur.csv"))
ges["Value"] = pd.to_numeric(ges["Value"], errors="coerce")
ges_sect = ges[ges["type"] == "Total"][["secteur", "Value"]].rename(columns={"Value": "ges_gg"})
ges_sect = ges_sect[ges_sect["secteur"] != "Total"].sort_values("ges_gg", ascending=False)
ges_sect["part_pct"] = (100 * ges_sect["ges_gg"] / ges_sect["ges_gg"].sum()).round(1)
ges_sect.to_csv(os.path.join(OUT, "emissions_secteur.csv"), index=False, encoding="utf-8")
print(ges_sect.to_string(index=False))
ges_gaz = ges[(ges["secteur"] == "Total") & (ges["type"] != "Total")][["type", "Value"]].rename(columns={"Value": "gg"})
ges_gaz.to_csv(os.path.join(OUT, "emissions_gaz.csv"), index=False, encoding="utf-8")

co2 = pd.read_csv(os.path.join(RAW, "co2_energie.csv"))
co2["value"] = pd.to_numeric(co2["value"], errors="coerce")
co2 = co2.dropna(subset=["value"])[["date", "value"]].rename(columns={"date": "annee", "value": "co2_mt"})
co2.to_csv(os.path.join(OUT, "co2_electricite.csv"), index=False, encoding="utf-8")

# ============================================================
# 8. CLIMAT (10 villes, Sud -> Nord)
# ============================================================
log("8. Climat : temperatures 10 villes")
VILLES = {
 "Lomé": (6.13, 1.22, "Maritime"), "Tabligbo": (6.58, 1.50, "Maritime"),
 "Kouma konda": (6.95, 0.60, "Plateaux"), "Atakpamé": (7.53, 1.13, "Plateaux"),
 "Sotouboua": (8.56, 0.98, "Centrale"), "Sokodé": (8.98, 1.13, "Centrale"),
 "Kara": (9.55, 1.19, "Kara"), "Niamtougou": (9.77, 1.10, "Kara"),
 "Mango": (10.36, 0.47, "Savanes"), "Dapaong": (10.86, 0.21, "Savanes"),
}
tmp = pd.read_csv(os.path.join(RAW, "temperatures.csv"))
tmp["Value"] = pd.to_numeric(tmp["Value"], errors="coerce")
tmp["annee"] = tmp["Date"].str.extract(r"(\d{4})").astype(int)
tmp["type"] = np.where(tmp["libellés"].str.contains("max"), "tmax", "tmin")
tv = tmp.pivot_table(index=["villes", "annee"], columns="type", values="Value", aggfunc="mean").reset_index()
tv["tmoy"] = ((tv["tmax"] + tv["tmin"]) / 2).round(1)
tv["lat"] = tv["villes"].map(lambda v: VILLES.get(v, (np.nan,))[0])
tv["lon"] = tv["villes"].map(lambda v: VILLES.get(v, (np.nan, np.nan))[1])
tv["region"] = tv["villes"].map(lambda v: VILLES.get(v, (np.nan, np.nan, None))[2])
tv = tv.round({"tmax": 1, "tmin": 1, "tmoy": 1})
tv.to_csv(os.path.join(OUT, "temperatures.csv"), index=False, encoding="utf-8")


def pente(d):
    d = d.dropna(subset=["tmoy"])
    return np.polyfit(d["annee"], d["tmoy"], 1)[0] if len(d) >= 3 else np.nan


trend = tv.groupby("villes").apply(lambda d: pente(d), include_groups=False).rename("pente_c_par_an").reset_index()
trend = trend.merge(tv.groupby("villes")[["lat", "lon", "region"]].first().reset_index(), on="villes")
trend["pente_c_par_an"] = trend["pente_c_par_an"].round(3)
trend = trend.sort_values("lat")
trend.to_csv(os.path.join(OUT, "temperatures_tendance.csv"), index=False, encoding="utf-8")

# ============================================================
# 9. FORETS CLASSEES (53) : geometrie, region, surface
# ============================================================
log("9. Forets classees / zones protegees")
f = pd.read_csv(os.path.join(RAW, "zones_protegees.csv"))
f["geometry"] = f["geometry"].apply(lambda x: wkt.loads(x) if isinstance(x, str) else None)
gf = gpd.GeoDataFrame(f, geometry="geometry", crs=4326)
gf = gf[gf.geometry.notna() & gf.geometry.is_valid].copy()
gm = gf.to_crs(32631)
gf["surface_km2"] = (gm.area / 1e6).round(1)
gf["lon"] = gf.geometry.centroid.x
gf["lat"] = gf.geometry.centroid.y
gf = gf.rename(columns={"region_nom_bdd": "region", "prefecture_nom_bdd": "prefecture",
                        "etab_nom": "nom", "etab_creation_date": "creation"})
keep = ["region", "prefecture", "nom", "creation", "surface_km2", "lat", "lon", "geometry"]
gj = gf[keep].copy()
gj["geometry"] = gj.geometry.simplify(0.003, preserve_topology=True)
gj.to_file(os.path.join(OUT, "forets.geojson"), driver="GeoJSON")
gf[["region", "prefecture", "nom", "creation", "surface_km2", "lat", "lon"]].to_csv(
    os.path.join(OUT, "forets.csv"), index=False, encoding="utf-8")
freg = gf.groupby("region").agg(nb=("nom", "size"), surface_km2=("surface_km2", "sum")).reset_index()
freg = freg.sort_values("surface_km2", ascending=False).round({"surface_km2": 0})
freg.to_csv(os.path.join(OUT, "forets_region.csv"), index=False, encoding="utf-8")
print(freg.to_string(index=False))

# ============================================================
# 9b. FRONTIERES DES 5 REGIONS (ajout externe, uniquement cartographique)
#     Source : geoBoundaries ADM1 Togo (frontieres administratives officielles).
#     Fichier source : data/togo_regions_geoBoundaries.geojson
# ============================================================
log("9b. Frontieres des 5 regions (geoBoundaries, cartographie)")
REGSRC = os.path.join(os.path.dirname(RAW), "togo_regions_geoBoundaries.geojson")
if os.path.exists(REGSRC):
    gb = json.load(open(REGSRC, encoding="utf-8"))
    NAME = {"Savanes Region": "Savanes", "Kara Region": "Kara", "Centrale Region": "Centrale",
            "Plateaux Region": "Plateaux", "Maritime Region": "Maritime"}
    out = {"type": "FeatureCollection", "features": []}
    for ft in gb["features"]:
        nm = NAME.get(ft["properties"].get("shapeName"))
        out["features"].append({"type": "Feature", "id": nm, "properties": {"region": nm},
                                "geometry": ft["geometry"]})
    json.dump(out, open(os.path.join(OUT, "togo_regions.geojson"), "w", encoding="utf-8"), ensure_ascii=False)
    print("  regions:", [f["properties"]["region"] for f in out["features"]])
else:
    print("  (fichier geoBoundaries absent - togo_regions.geojson conserve tel quel)")

# ============================================================
# 10. KPIs
# ============================================================
log("10. KPIs")


def last(df, col):
    return float(df.dropna(subset=[col]).sort_values("annee")[col].iloc[-1])


ly = int(elec.dropna(subset=["rural"])["annee"].max())
K = {
 "annee_ref": ly,
 "elec_rural": last(elec, "rural"), "elec_urbain": last(elec, "urbain"),
 "elec_national": last(elec, "national"),
 "elec_ecart": round(last(elec, "urbain") - last(elec, "rural"), 1),
 "sans_elec_total": int(last(elec, "sans_elec_total")),
 "sans_elec_rural": int(last(elec, "sans_elec_rural")),
 "sans_elec_rural_pct": round(100 * last(elec, "sans_elec_rural") / last(elec, "sans_elec_total"), 0),
 "pop_tot": int(last(elec, "pop_tot")),
 "sans_elec_pct_pop": round(100 * last(elec, "sans_elec_total") / last(elec, "pop_tot"), 1),
 "cuisson_national": last(cuisson, "national"), "cuisson_rural": last(cuisson, "rural"),
 "cuisson_urbain": last(cuisson, "urbain"),
 "pop_sans_cuisson": int(last(cuisson, "pop_sans_cuisson_propre")),
 "cuisson_sans_pct": round(100 - last(cuisson, "national"), 1),
 "biomasse_pct": float(bio.iloc[-1]["biomasse_pct"]), "biomasse_annee": int(bio.iloc[-1]["annee"]),
 "co2_elec_mt": float(co2[co2.annee == co2.annee.max()]["co2_mt"].iloc[0]),
 "part_energie_ges": float(ges_sect[ges_sect["secteur"] == "Energie"]["part_pct"].iloc[0]),
 "foret_1990": int(foret_ts.iloc[0]["surface_km2"]), "foret_2021": int(foret_ts.iloc[-1]["surface_km2"]),
 "foret_perte_km2": int(foret_ts.iloc[0]["surface_km2"] - foret_ts.iloc[-1]["surface_km2"]),
 "foret_perte_pct": round(100 * (foret_ts.iloc[0]["surface_km2"] - foret_ts.iloc[-1]["surface_km2"]) / foret_ts.iloc[0]["surface_km2"], 0),
 "foret_perte_an": int(round((foret_ts.iloc[0]["surface_km2"] - foret_ts.iloc[-1]["surface_km2"]) / (foret_ts.iloc[-1]["annee"] - foret_ts.iloc[0]["annee"]))),
 "foret_pct_terres": float(foret_ts.iloc[-1]["pct_terres"]),
 "coupures_pct_firmes": float(outg.dropna(subset=["pct_firmes_coupees"]).iloc[-1]["pct_firmes_coupees"]),
 "coupures_par_mois": float(outg.dropna(subset=["coupures_par_mois"]).iloc[-1]["coupures_par_mois"]),
 "coupures_annee": int(outg.dropna(subset=["pct_firmes_coupees"]).iloc[-1]["annee"]),
 "nb_forets": int(len(gf)), "surface_forets_km2": int(round(gf["surface_km2"].sum())),
 "nb_villes": int(tv["villes"].nunique()),
 "rechauffement_moyen": round(float(trend["pente_c_par_an"].mean()) * 10, 2),
 "pib_hab": int(last(gdp, "pib_hab")),
}
with open(os.path.join(OUT, "kpis.json"), "w", encoding="utf-8") as fp:
    json.dump(K, fp, ensure_ascii=False, indent=2)
print(json.dumps(K, ensure_ascii=False, indent=2))
print("\nOK - tables ecrites dans data/")
