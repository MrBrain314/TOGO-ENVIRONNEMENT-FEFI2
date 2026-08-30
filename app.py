# -*- coding: utf-8 -*-
"""
=====================================================================
 PANORAMA · Énergie & transition écologique au Togo
 Data Challenge Environnement · Défi 2 · Togo AI Lab / MESPTN
 Tableau de bord · salle de contrôle nationale (Plotly Dash)
=====================================================================
 Lancement local :  python app.py   →  http://127.0.0.1:8050
"""
import os
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output, ctx, ALL, no_update

# --------------------------------------------------------------------
BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")

# ---- palette (salle de contrôle · mode clair) ----
BG, PANEL, PANEL2 = "#EAEDE5", "#FFFFFF", "#F3F5EF"
MINT, AMBER, VERM = "#0A7C46", "#E0A422", "#D21034"   # vert drapeau, jaune doré, rouge drapeau
MINT_R, VERM_R = "#1E9E5A", "#E23B22"
INK, INK2, MUT, MUT2 = "#16251A", "#33422F", "#66715F", "#8A9384"
LINE = "#DDE1D7"
REG_COL = {"Maritime": "#1E9E5A", "Plateaux": "#0A7C46", "Centrale": "#E0A422",
           "Kara": "#E28A1E", "Savanes": "#D21034"}
REGIONS = ["Maritime", "Plateaux", "Centrale", "Kara", "Savanes"]
ALLREG = "Tout le pays"


# --------------------------------------------------------------------
def load():
    d = {}
    for f in ["electrification", "cuisson", "biomasse", "coupures", "foret_surface",
              "emissions_secteur", "emissions_gaz", "co2_electricite",
              "temperatures", "temperatures_tendance", "forets", "forets_region", "pib"]:
        p = os.path.join(DATA, f + ".csv")
        d[f] = pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()
    d["kpis"] = json.load(open(os.path.join(DATA, "kpis.json"), encoding="utf-8"))
    d["geo"] = json.load(open(os.path.join(DATA, "forets.geojson"), encoding="utf-8"))
    for i, ft in enumerate(d["geo"]["features"]):
        ft["id"] = i
        ft["properties"]["idx"] = i
    rp = os.path.join(DATA, "togo_regions.geojson")
    d["regions"] = json.load(open(rp, encoding="utf-8")) if os.path.exists(rp) else {"type": "FeatureCollection", "features": []}
    return d


D = load()
K = D["kpis"]


def _bbox(geom):
    xs, ys = [], []

    def walk(c):
        if c and isinstance(c[0], (int, float)):
            xs.append(c[0]); ys.append(c[1])
        else:
            for cc in c:
                walk(cc)
    walk(geom["coordinates"])
    return min(xs), min(ys), max(xs), max(ys)


def _region_views():
    import math
    v = {}
    for f in D["regions"]["features"]:
        minx, miny, maxx, maxy = _bbox(f["geometry"])
        span = max(maxx - minx, maxy - miny) or 1
        zoom = max(6.0, min(8.2, math.log2(360 / span) - 1.15))
        v[f["properties"]["region"]] = ((miny + maxy) / 2, (minx + maxx) / 2, zoom)
    return v


REGION_VIEW = _region_views()


def fr(x):
    return f"{x:,.0f}".replace(",", " ")


def fr_m(x):
    return f"{x/1e6:.2f} M".replace(".", ",")


def c1(v):
    """décimale française : 0.9 -> 0,9"""
    return f"{v:.1f}".replace(".", ",")


def c2(v):
    return f"{v:+.2f}".replace(".", ",")


# ====================================================================
# STYLE PLOTLY
# ====================================================================
def sty(fig, h=250, legend=False, m=None):
    fig.update_layout(
        height=h, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Hanken Grotesk, sans-serif", color=INK2, size=12),
        margin=m or dict(l=6, r=10, t=6, b=6),
        showlegend=legend,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10, color=MUT),
                    orientation="h", y=1.16, x=0),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=LINE,
                        font=dict(family="Hanken Grotesk", size=12, color=INK)))
    fig.update_xaxes(gridcolor="#E7EBE1", linecolor="#CBD3C2", zeroline=False,
                     tickfont=dict(size=10, color=MUT), title=None)
    fig.update_yaxes(gridcolor="#E7EBE1", linecolor="#CBD3C2", zeroline=False,
                     tickfont=dict(size=10, color=MUT), title=None)
    return fig


# ====================================================================
# FIGURES
# ====================================================================
def fig_fracture():
    e = D["electrification"].dropna(subset=["rural", "urbain"], how="all")
    f = go.Figure()
    f.add_trace(go.Scatter(x=e["annee"], y=e["urbain"], name="Urbain", mode="lines",
                           line=dict(color=MINT, width=3), hovertemplate="%{y:.0f}%<extra>Urbain</extra>"))
    f.add_trace(go.Scatter(x=e["annee"], y=e["rural"], name="Rural", mode="lines",
                           line=dict(color=VERM, width=3), fill="tonexty",
                           fillcolor="rgba(210,16,52,0.09)",
                           hovertemplate="%{y:.0f}%<extra>Rural</extra>"))
    f.add_trace(go.Scatter(x=e["annee"], y=e["national"], name="National", mode="lines",
                           line=dict(color=MUT, width=1.3, dash="dot"),
                           hovertemplate="%{y:.0f}%<extra>National</extra>"))
    f.update_yaxes(range=[0, 100], ticksuffix="%")
    return sty(f, 236, legend=True)


def fig_projection():
    e = D["electrification"].dropna(subset=["rural"]).copy()
    rec = e[e["annee"] >= 2010]
    slope = float(np.polyfit(rec["annee"], rec["rural"], 1)[0])
    ly = int(e["annee"].max()); lr = float(e.loc[e.annee == ly, "rural"].iloc[0])
    proj_year = int(round(ly + (99 - lr) / slope))
    px = list(range(ly, proj_year + 1))
    py = [min(100, lr + slope * (x - ly)) for x in px]
    f = go.Figure()
    f.add_trace(go.Scatter(x=e["annee"], y=e["rural"], name="Rural observé", mode="lines",
                           line=dict(color=VERM, width=3), hovertemplate="%{y:.0f}%<extra>%{x}</extra>"))
    f.add_trace(go.Scatter(x=px, y=py, name="Projection", mode="lines",
                           line=dict(color=AMBER, width=2, dash="dot"),
                           hovertemplate="%{y:.0f}%<extra>projection %{x}</extra>"))
    f.add_hline(y=99, line=dict(color=MINT, width=1, dash="dash"))
    f.add_annotation(x=e["annee"].min() + 3, y=99, text="Accès universel", showarrow=False,
                     yshift=9, font=dict(color=MINT, size=10))
    f.add_vline(x=2030, line=dict(color=INK2, width=1))
    f.add_annotation(x=2030, y=6, text="Objectif 2030", showarrow=False, xshift=40,
                     font=dict(color=INK2, size=10))
    f.add_annotation(x=proj_year, y=99, text=f"~{proj_year}", showarrow=True, arrowhead=2,
                     ax=-24, ay=-26, arrowcolor=AMBER, font=dict(color=AMBER, size=13, family="Chivo"))
    f.update_yaxes(range=[0, 106], ticksuffix="%")
    f.update_xaxes(range=[e["annee"].min(), proj_year + 2])
    return sty(f, 236, legend=True), proj_year, slope


def fig_coupures():
    c = D["coupures"].dropna(subset=["pct_firmes_coupees"])
    f = go.Figure(go.Bar(x=c["annee"].astype(int).astype(str), y=c["pct_firmes_coupees"],
                         marker_color=([AMBER, VERM] * 3)[:len(c)], width=0.5,
                         text=c["pct_firmes_coupees"].map(lambda v: f"{v:.0f}%"),
                         textposition="outside", textfont=dict(color=INK, family="Chivo"),
                         hovertemplate="%{y:.0f}% des entreprises<extra>%{x}</extra>"))
    f.update_yaxes(range=[0, 112], ticksuffix="%")
    return sty(f, 150)


def fig_cuisson():
    cu = D["cuisson"]
    f = go.Figure()
    f.add_trace(go.Scatter(x=cu["annee"], y=cu["urbain"], name="Urbain", mode="lines",
                           line=dict(color=MINT, width=3), hovertemplate="%{y:.1f}%<extra>Urbain</extra>"))
    f.add_trace(go.Scatter(x=cu["annee"], y=cu["rural"], name="Rural", mode="lines",
                           line=dict(color=VERM, width=3), hovertemplate="%{y:.1f}%<extra>Rural</extra>"))
    f.update_yaxes(ticksuffix="%", range=[0, max(30, float(cu["urbain"].max()) + 4)])
    return sty(f, 220, legend=True)


def fig_biomasse():
    b = D["biomasse"]
    f = go.Figure(go.Scatter(x=b["annee"], y=b["biomasse_pct"], mode="lines",
                             line=dict(color=AMBER, width=3), fill="tozeroy",
                             fillcolor="rgba(224,164,34,0.16)",
                             hovertemplate="%{y:.0f}%<extra>%{x}</extra>"))
    f.update_yaxes(ticksuffix="%", range=[0, 100])
    return sty(f, 220)


def fig_deforestation():
    s = D["foret_surface"]
    f = go.Figure(go.Scatter(x=s["annee"], y=s["surface_km2"], mode="lines",
                             line=dict(color=VERM, width=3), fill="tozeroy",
                             fillcolor="rgba(210,16,52,0.09)",
                             hovertemplate="%{y:,.0f} km²<extra>%{x}</extra>"))
    y1 = s.iloc[-1]
    f.add_annotation(x=y1["annee"], y=y1["surface_km2"], text=f"{fr(y1['surface_km2'])} km²",
                     showarrow=False, yshift=-14, font=dict(color=VERM_R, size=11, family="Chivo"))
    f.update_yaxes(range=[0, float(s["surface_km2"].max()) * 1.12])
    return sty(f, 220)


def fig_ges():
    s = D["emissions_secteur"].copy().sort_values("part_pct")
    SHORT = {
        "Agriculture, Foresterie et autres Affectations des Terres (AFAT)": "Agriculture & forêts (AFAT)",
        "Energie": "Énergie",
        "Procédés Industriels et Utilisation des Produits (PIUP)": "Industrie (PIUP)",
        "Déchets": "Déchets",
    }
    s["court"] = s["secteur"].map(lambda x: SHORT.get(x, x))
    cols = [VERM if x.strip().startswith("Energie") else (MINT_R if ("AFAT" in x or "Agri" in x or "Forêt" in x)
            else AMBER) for x in s["secteur"]]
    f = go.Figure(go.Bar(x=s["part_pct"], y=s["court"], orientation="h", marker_color=cols,
                         text=s["part_pct"].map(lambda v: f"{v:.0f}%"), textposition="outside",
                         textfont=dict(color=INK, family="Chivo"),
                         hovertemplate="%{y} : %{x:.1f}%<extra></extra>"))
    f.update_xaxes(range=[0, 100], ticksuffix="%")
    return sty(f, 236)


def fig_co2():
    c = D["co2_electricite"]
    f = go.Figure(go.Scatter(x=c["annee"], y=c["co2_mt"], mode="lines",
                             line=dict(color=AMBER, width=3),
                             hovertemplate="%{y:.3f} Mt<extra>%{x}</extra>"))
    return sty(f, 236)


def fig_temp(region):
    tv = D["temperatures"]; tr = D["temperatures_tendance"].sort_values("lat")
    order = tr["villes"].tolist()
    if region != ALLREG:
        m = tr.set_index("villes")["region"]
        order = [v for v in order if m.get(v) == region]
    rec = tv[tv["annee"] == tv["annee"].max()]
    rec = rec[rec["villes"].isin(order)].set_index("villes").reindex(order).reset_index()
    f = go.Figure()
    f.add_trace(go.Bar(x=rec["villes"], y=rec["tmax"], name="Max", marker_color=VERM,
                       hovertemplate="%{y:.1f}°C<extra>Max · %{x}</extra>"))
    f.add_trace(go.Bar(x=rec["villes"], y=rec["tmin"], name="Min", marker_color=MINT,
                       hovertemplate="%{y:.1f}°C<extra>Min · %{x}</extra>"))
    f.update_layout(barmode="group")
    f.update_yaxes(ticksuffix="°C")
    return sty(f, 236, legend=True)


def fig_trend(region):
    tr = D["temperatures_tendance"].sort_values("lat").copy()
    if region != ALLREG:
        tr = tr[tr["region"] == region]
    tr["dec"] = (tr["pente_c_par_an"] * 10).round(2)
    f = go.Figure(go.Bar(x=tr["dec"], y=tr["villes"], orientation="h",
                         marker_color=[VERM if v > 0 else MINT for v in tr["dec"]],
                         text=tr["dec"].map(lambda v: f"{v:+.2f}".replace(".", ",")), textposition="outside",
                         textfont=dict(color=INK, family="Chivo"), cliponaxis=False,
                         hovertemplate="%{y} : %{x:+.2f} °C/déc.<extra></extra>"))
    lo = float(tr["dec"].min()); hi = float(tr["dec"].max())
    f.update_xaxes(range=[min(lo, 0) - 0.28, max(hi, 0) + 0.42], ticksuffix=" °C")
    return sty(f, 236)


def fig_map(region):
    geo = D["geo"]
    feats = geo["features"] if region == ALLREG else \
        [f for f in geo["features"] if f["properties"].get("region") == region]
    sub = {"type": "FeatureCollection", "features": feats}
    ids = [f["id"] for f in feats]
    surf = [f["properties"]["surface_km2"] for f in feats]
    noms = [f["properties"]["nom"] for f in feats]
    regs = [f["properties"].get("region", "") for f in feats]
    cd = np.stack([noms, regs, surf], axis=-1) if feats else np.empty((0, 3))
    fig = go.Figure()
    # forêts classées (polygones)
    if feats:
        fig.add_trace(go.Choroplethmap(
            geojson=sub, locations=ids, featureidkey="id", z=surf,
            colorscale=[[0, "#CFEBDB"], [0.5, "#4FA97B"], [1, "#0A7C46"]],
            marker=dict(line=dict(color="#FFFFFF", width=0.8), opacity=0.92), showscale=False,
            customdata=cd,
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]} · %{customdata[2]} km²<extra></extra>"))
    # villes / stations climatiques
    tv = D["temperatures"]
    rec = tv[tv["annee"] == tv["annee"].max()].copy()
    if region != ALLREG:
        rec = rec[rec["region"] == region]
    if len(rec):
        fig.add_trace(go.Scattermap(
            lat=rec["lat"], lon=rec["lon"], mode="markers",
            marker=dict(size=13, color=rec["tmax"], colorscale=[[0, "#1E9E5A"], [.5, "#E0A422"], [1, "#D21034"]],
                        showscale=False, opacity=.95),
            customdata=np.stack([rec["villes"], rec["tmax"], rec["region"]], axis=-1),
            hovertemplate="<b>%{customdata[0]}</b> · %{customdata[2]}<br>Max %{customdata[1]:.1f}°C<extra></extra>",
            name="Villes"))
    # contours des régions + surbrillance de la région choisie
    layers = [dict(source=D["regions"], type="line",
                   color="rgba(90,110,80,0.35)", line=dict(width=1))]
    if region != ALLREG:
        sel = {"type": "FeatureCollection",
               "features": [f for f in D["regions"]["features"] if f["properties"]["region"] == region]}
        layers += [dict(source=sel, type="fill", color="rgba(10,124,70,0.10)"),
                   dict(source=sel, type="line", color="#0A7C46", line=dict(width=2.6))]
    center = {"lat": 8.6, "lon": 1.0}
    zoom = 5.75
    if region != ALLREG and region in REGION_VIEW:
        la, lo, zm = REGION_VIEW[region]
        center = {"lat": la, "lon": lo}
        zoom = zm
    fig.update_layout(map=dict(style="carto-positron", zoom=zoom, center=center, layers=layers),
                      margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      showlegend=False,
                      hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=LINE,
                                      font=dict(family="Hanken Grotesk", size=12, color=INK)))
    return fig


# ====================================================================
# APP
# ====================================================================
# style.css, logo.jpg et icons/ sont servis automatiquement depuis le dossier "assets/".
app = Dash(__name__, suppress_callback_exceptions=True, title="PANORAMA · Énergie Togo",
           meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}])
server = app.server

app.index_string = """<!DOCTYPE html>
<html>
<head>
  {%metas%}<title>{%title%}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Chivo:wght@400;700;900&family=Hanken+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
  {%favicon%}{%css%}
</head>
<body><div class="app-root">{%app_entry%}</div>
{%config%}{%scripts%}{%renderer%}</body></html>"""


# ---- icônes (SVG data-URI, couleur bakée selon l'état) ----
ICONS = {
    "panorama": "M3 12l9-8 9 8M5 10v9h14v-9",
    "elec": "M13 2L4 14h6l-1 8 9-12h-6z",
    "foret": "M12 3l4 7h-3l3 6h-4v4h-2v-4H5l3-6H5z",
    "emis": "M4 18h16M6 18V9M11 18V5M16 18v-8",
    "climat": "M12 3v2M4.5 7.5l1.4 1.4M2 15h2M20 15h2M9 11a3 3 0 016 0M6 17h11a2.5 2.5 0 010 5H6",
    "agir": "M12 3a9 9 0 109 9M12 3v9l6-3",
}
NAV = [("panorama", "Vue"), ("elec", "Élec"), ("foret", "Bois"),
       ("emis", "GES"), ("climat", "Climat"), ("agir", "Agir")]


def svg_uri(path, color):
    c = color.replace("#", "%23")
    s = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
         f"stroke='{c}' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>"
         f"<path d='{path}'/></svg>")
    return "data:image/svg+xml;utf8," + s.replace("<", "%3C").replace(">", "%3E").replace('"', "'").replace("#", "%23")


def build_rail(active_sec):
    items = []
    for sec, label in NAV:
        act = (active_sec == sec)
        items.append(html.Button(
            id={"role": "nav", "sec": sec},
            className="rail-btn" + (" active" if act else ""),
            n_clicks=0, title=label,
            children=[
                html.Img(src=svg_uri(ICONS[sec], MINT if act else MUT),
                         style={"width": "19px", "height": "19px"}),
                html.Span(label, className="rlab"),
            ]))
    return html.Div(className="rail", children=[
        html.Img(src="/assets/logo.jpg", className="rail-logo-img",
                 title="République Togolaise · PANORAMA"),
        *items,
        html.Div("TOGO · ENVIRONNEMENT · DÉFI 2", className="rail-foot"),
    ])


def header(region):
    segs = [html.Button(ALLREG, id={"role": "region", "reg": ALLREG},
                        className="seg-btn" + (" on" if region == ALLREG else ""), n_clicks=0)]
    for r in REGIONS:
        segs.append(html.Button(r, id={"role": "region", "reg": r},
                    className="seg-btn" + (" on" if region == r else ""), n_clicks=0))
    return html.Div(className="header", children=[
        html.Div(className="brand", children=[
            html.Div("PANORAMA · Data Challenge Environnement", className="k"),
            html.Div(["Énergie ", html.Span("&", className="amp"),
                      " transition écologique au Togo"], className="t"),
            html.Div("Électrifier sans déforester · 6 jeux de données ouvertes", className="s"),
        ]),
        html.Div(className="header-spacer"),
        html.Div("Région", className="scope-lab"),
        html.Div(className="seg", children=segs),
    ])


app.layout = html.Div(className="app-grid", children=[
    dcc.Store(id="section", data="panorama"),
    dcc.Store(id="region", data=ALLREG),
    dcc.Store(id="zoom-sink"),
    html.Div(id="rail-container"),
    html.Div(className="main", children=[
        html.Div(id="header-container"),
        html.Div(id="body", className="body"),
    ]),
])


# ====================================================================
# COMPOSANTS
# ====================================================================
def kpi(kn, kl, cls="", ksub=None, ic=None):
    ch = [html.Div(kn, className="kn num"), html.Div(kl, className="kl")]
    if ksub:
        ch.append(html.Div(ksub, className="ksub"))
    if ic:
        ck = cls.strip() if cls.strip() in ("good", "warn", "crit") else "good"
        ch.insert(0, html.Img(src=f"/assets/icons/{ic}_{ck}.png", className="kico"))
    return html.Div(className=f"kpi {cls}", children=ch)


def sect_head(n, h, tag):
    return html.Div(className="sect-head", children=[
        html.Span(n, className="n"), html.Span(h, className="h"), html.Span(tag, className="tag")])


def scope_chip(region, note):
    txt = "Vue nationale" if region == ALLREG else f"Filtré : {region}"
    return html.Div(className="scope-note", children=[html.Span("◉ " + txt + " · "), html.B(note)])


def graph(fig):
    return dcc.Graph(figure=fig, config={"displayModeBar": False, "responsive": True})


def map_with_zoom(region, h):
    return html.Div(className="map-wrap", children=[
        dcc.Graph(id={"role": "map", "idx": 0}, figure=fig_map(region),
                  config={"displayModeBar": False, "responsive": True, "scrollZoom": True},
                  style={"height": f"{h}px"}),
        html.Div(className="map-zoom", children=[
            html.Button("+", id={"role": "zoombtn", "dir": "in"}, n_clicks=0, title="Zoomer"),
            html.Button("−", id={"role": "zoombtn", "dir": "out"}, n_clicks=0, title="Dézoomer"),
        ]),
    ])


def foot():
    return html.Div(className="foot", children=[
        html.Span("Sources : WDI · opendata.gouv.tg · accès électricité & cuisson, biomasse, "
                  "émissions de gaz à effet de serre (GES), CO₂ électricité, températures 10 villes, 53 zones protégées."),
        html.Span("Développé par Bastou OURO-TAGBA · MESPTN / Togo AI Lab"),
    ])


def region_stats(region):
    freg = D["forets_region"]; row = freg[freg["region"] == region]
    nb = int(row["nb"].sum()) if len(row) else 0
    surf = float(row["surface_km2"].sum()) if len(row) else 0.0
    tot = float(freg["surface_km2"].sum())
    share = 100 * surf / tot if tot else 0.0
    tr = D["temperatures_tendance"]; trr = tr[tr["region"] == region]
    warm = round(float(trr["pente_c_par_an"].mean()) * 10, 2) if len(trr) else 0.0
    nvil = int(trr["villes"].nunique())
    tv = D["temperatures"]; last = tv[tv["annee"] == tv["annee"].max()]
    lr = last[last["region"] == region]
    if len(lr):
        hot = lr.loc[lr["tmax"].idxmax()]
        hot_city, hot_t = str(hot["villes"]), float(hot["tmax"])
    else:
        hot_city, hot_t = "-", 0.0
    return dict(nb=nb, surf=surf, share=share, warm=warm, nvil=nvil, hot_city=hot_city, hot_t=hot_t)


def panorama_band(region):
    if region == ALLREG:
        return [
            kpi(fr_m(K["sans_elec_total"]), "Togolais sans électricité", "crit",
                f"{K['sans_elec_rural_pct']:.0f} % de ce déficit est rural · {K['annee_ref']}", ic="bolt"),
            kpi(f"{K['cuisson_sans_pct']:.0f} %", "cuisinent sans énergie propre", "crit",
                f"soit {fr_m(K['pop_sans_cuisson'])} de personnes au bois / charbon", ic="flame"),
            kpi(f"−{fr(K['foret_perte_km2'])}", "km² de forêts perdus depuis 1990", "warn",
                f"−{K['foret_perte_pct']:.0f} % du couvert · ~{K['foret_perte_an']} km²/an", ic="tree"),
            kpi(f"{K['coupures_pct_firmes']:.0f} %", "des entreprises subissent des coupures", "warn",
                f"~{c1(K['coupures_par_mois'])} coupures/mois · {K['coupures_annee']}", ic="power"),
        ]
    rs = region_stats(region)
    return [
        kpi(f"{rs['nb']}", f"forêts classées · {region}", "good",
            f"{rs['share']:.0f} % du couvert classé national", ic="tree"),
        kpi(f"{fr(rs['surf'])}", "km² d'aires protégées", "good", "surface classée de la région", ic="leaf"),
        kpi(c2(rs['warm']), "°C / décennie (réchauffement)", "warn",
            f"{rs['nvil']} station(s) climatique(s)", ic="thermo"),
        kpi(f"{c1(rs['hot_t'])} °C", f"pic de chaleur · {rs['hot_city']}", "crit",
            "température max relevée · dernière année", ic="sun"),
    ]


def panorama_side(region):
    if region == ALLREG:
        return [
            html.Div(className="panel", children=[
                html.Div(className="panel-title", children=[html.Span("Fracture", className="kick v")]),
                html.H4("Accès à l'électricité · ville vs campagne"),
                graph(fig_fracture()),
            ]),
            html.Div(className="insight", children=[
                html.Span("Le fil rouge", className="kick"),
                html.P(["En campagne, seuls ", html.B(f"{K['elec_rural']:.0f} %"),
                        " ont l'électricité et ", html.B(f"{c1(K['cuisson_rural'])} %"),
                        " cuisinent proprement. Le bois comble le vide, et la forêt recule de ",
                        html.Span(f"~{K['foret_perte_an']} km²/an", className="o"), "."]),
                html.Div(className="reco", children=[
                    html.Div("▸ La bascule", className="t"),
                    html.Div("Solaire hors-réseau + cuisson propre : électrifier les villages "
                             "sans prélever sur le couvert forestier.", className="d")]),
            ]),
        ]
    rs = region_stats(region)
    priorite = {
        "Plateaux": "Couvert classé le plus vaste du pays : desserrer en priorité la pression du bois-énergie.",
        "Centrale": "Second pôle de forêts classées : protéger face à la demande rurale en bois.",
        "Maritime": "Reliques forestières quasi disparues : protéger l'existant, accélérer la cuisson propre.",
        "Kara": "Électrification solaire rurale et foyers améliorés à prioriser.",
        "Savanes": "Zone la plus au nord et la plus chaude : solaire hors-réseau et cuisson propre prioritaires.",
    }.get(region, "Solaire hors-réseau et cuisson propre à prioriser.")
    return [
        html.Div(className="panel", children=[
            html.Div(className="panel-title", children=[html.Span("Climat régional", className="kick a")]),
            html.H4(f"Températures des villes · {region}"),
            graph(fig_temp(region)),
        ]),
        html.Div(className="insight", children=[
            html.Span(f"Profil · {region}", className="kick"),
            html.P(["La région ", html.B(region), " compte ", html.B(f"{rs['nb']} forêts classées"),
                    f" ({fr(rs['surf'])} km², {rs['share']:.0f} % du couvert national). Réchauffement ",
                    html.Span(f"{c2(rs['warm'])} °C/décennie", className="o"),
                    f", pic à {c1(rs['hot_t'])} °C ({rs['hot_city']})."]),
            html.Div(className="reco", children=[
                html.Div("▸ Priorité régionale", className="t"),
                html.Div(priorite, className="d")]),
        ]),
    ]


# ---- PANORAMA ----
def sec_panorama(region):
    scope = [] if region == ALLREG else [scope_chip(
        region, "Profil régional (forêts + climat). Accès électricité et cuisson ne sont "
        "disponibles qu'au niveau national.")]
    map_title = ("53 forêts classées & 10 stations climatiques" if region == ALLREG
                 else f"Forêts classées & stations · {region}")
    return [
        sect_head("00", "Le Togo en un écran", "Électrifier sans déforester · le tableau de bord national."),
        *scope,
        html.Div(className="kpi-band", children=panorama_band(region)),
        html.Div(className="grid g-map", children=[
            html.Div(className="panel pad0", children=[
                html.Div(style={"padding": "12px 15px 2px"}, children=[
                    html.Div(className="panel-title", children=[
                        html.Span("Carte pilote", className="kick"),
                        html.Span("Cliquez une forêt pour filtrer, ou une région en haut",
                                  style={"fontSize": ".7rem", "color": MUT, "marginLeft": "auto"})]),
                    html.H4(map_title),
                ]),
                map_with_zoom(region, 396),
                html.Div(className="legend-row", style={"padding": "0 15px 12px"}, children=[
                    html.Span(className="chip", children=[html.Span(className="d", style={"background": MINT}), "Forêt classée (surface)"]),
                    html.Span(className="chip", children=[html.Span(className="d", style={"background": AMBER}), "Station climatique (T° max)"]),
                ]),
            ]),
            html.Div(className="grid", style={"gridTemplateColumns": "1fr", "gap": "12px"},
                     children=panorama_side(region)),
        ]),
        foot(),
    ]


# ---- ÉLECTRIFICATION ----
def sec_elec(region):
    e = D["electrification"].dropna(subset=["ecart_urbain_rural"])
    gap0 = float(e.iloc[0]["ecart_urbain_rural"]); gap1 = float(e.iloc[-1]["ecart_urbain_rural"])
    figp, proj_year, slope = fig_projection()
    cp = D["coupures"].dropna(subset=["pct_ventes_perdues"])
    pv = float(cp.iloc[0]["pct_ventes_perdues"]) if len(cp) else None
    return [
        sect_head("01", "La fracture de la lumière & la fiabilité du réseau",
                  "Ville et campagne face à l'accès, et un réseau qui flanche."),
        *([] if region == ALLREG else [scope_chip(region,
          "Accès à l'électricité : donnée nationale (rural / urbain), non déclinée par région.")]),
        html.Div(className="kpi-band", children=[
            kpi(f"{K['elec_rural']:.0f} %", f"accès rural · {K['annee_ref']}", "crit", ic="home"),
            kpi(f"{K['elec_urbain']:.0f} %", "accès urbain", "good", ic="city"),
            kpi([f"{gap1:.0f}", html.Span("points de %", className="kn-unit")],
                "d'écart ville / campagne", "warn", f"×{c1(gap1/gap0)} depuis 2000", ic="gap"),
            kpi(fr_m(K["sans_elec_total"]), "personnes sans électricité", "crit",
                f"dont {K['sans_elec_rural_pct']:.0f} % en zone rurale", ic="bolt"),
        ]),
        html.Div(className="grid g-2", children=[
            html.Div(className="panel", children=[
                html.Div(className="panel-title", children=[html.Span("Trajectoire", className="kick")]),
                html.H4("Accès à l'électricité (2000-2022)"),
                graph(fig_fracture()),
            ]),
            html.Div(className="panel", children=[
                html.Div(className="panel-title", children=[html.Span("Projection", className="kick a")]),
                html.H4(f"Au rythme actuel, le rural attend ~{proj_year}"),
                graph(figp),
            ]),
        ]),
        html.Div(className="grid g-side", style={"marginTop": "12px"}, children=[
            html.Div(className="panel", children=[
                html.Div(className="panel-title", children=[html.Span("Fiabilité du réseau · coupures", className="kick a")]),
                html.H4("Un réseau qui flanche : les entreprises témoignent"),
                html.Div(className="psub", children="Part des entreprises subissant des coupures d'électricité"),
                graph(fig_coupures()),
                html.Div(className="mini", children=[
                    html.Div([html.Div(c1(K['coupures_par_mois']), className="v o"),
                              html.Div("coupures / mois (2016)", className="k")]),
                    html.Div([html.Div(f"{pv:.0f} %" if pv else "n.d.", className="v r"),
                              html.Div("des ventes perdues (firmes touchées, 2009)", className="k")]),
                ]),
            ]),
            html.Div(className="insight", children=[
                html.Span("Ce que ça change", className="kick"),
                html.P([html.B("L'électrification a creusé l'inégalité"),
                        f" : l'écart ville/campagne est passé de {gap0:.0f} à {gap1:.0f} points. "
                        "La ville a foncé, la campagne avance à petits pas."]),
                html.P(["Et là où le réseau arrive, il ", html.Span("flanche", className="o"),
                        f" : {K['coupures_pct_firmes']:.0f} % des entreprises subissent des coupures. "
                        "Étendre un réseau fragile ne suffira pas."]),
                html.Div(className="reco", children=[
                    html.Div("▸ LEVIER · Solaire hors-réseau", className="t"),
                    html.Div("Mini-centrales et kits solaires : la seule voie pour électrifier les "
                             "villages avant 2030, sans dépendre d'un réseau saturé.", className="d")]),
            ]),
        ]),
        foot(),
    ]


# ---- CUISSON & FORÊTS ----
def sec_foret(region):
    freg = D["forets_region"]
    if region == ALLREG:
        nb = int(freg["nb"].sum()); surf = float(freg["surface_km2"].sum())
    else:
        row = freg[freg["region"] == region]
        nb = int(row["nb"].sum()) if len(row) else 0
        surf = float(row["surface_km2"].sum()) if len(row) else 0.0
    forets = D["forets"].copy()
    if region != ALLREG:
        forets = forets[forets["region"] == region]
    forets = forets.sort_values("surface_km2", ascending=False).head(40)
    flist = html.Div(className="flist", children=[
        html.Div(className="frow", children=[
            html.Span(r["nom"], className="fn", title=str(r["nom"])),
            html.Span(f"{r['surface_km2']:.1f} km²", className="fv")])
        for _, r in forets.iterrows()]) if len(forets) else \
        html.Div("Aucune forêt classée référencée pour cette région.", className="psub")
    return [
        sect_head("02", "Le feu de bois & le recul des forêts",
                  "La cuisson au bois, ou l'absence de choix qui pèse sur la forêt."),
        html.Div(className="kpi-band", children=[
            kpi(f"{c1(K['cuisson_rural'])} %", "de cuisson propre en campagne", "crit", ic="flame"),
            kpi(f"{K['biomasse_pct']:.0f} %", f"de biomasse dans l'énergie ({K['biomasse_annee']})", "warn", ic="tree"),
            kpi(f"−{K['foret_perte_pct']:.0f} %", "de couvert forestier depuis 1990", "warn",
                f"{fr(K['foret_1990'])} → {fr(K['foret_2021'])} km²", ic="chartup"),
            kpi(f"{nb}", "forêts classées" + ("" if region == ALLREG else f" · {region}"), "good",
                f"{fr(surf)} km² protégés", ic="leaf"),
        ]),
        html.Div(className="grid g-2", children=[
            html.Div(className="panel", children=[
                html.Div(className="panel-title", children=[html.Span("Cuisson propre", className="kick v")]),
                html.H4("Accès à une cuisson propre (% population)"),
                graph(fig_cuisson()),
            ]),
            html.Div(className="panel", children=[
                html.Div(className="panel-title", children=[html.Span("Déforestation", className="kick a")]),
                html.H4("Superficie forestière nationale (1990-2021)"),
                graph(fig_deforestation()),
            ]),
        ]),
        html.Div(className="grid g-map", style={"marginTop": "12px"}, children=[
            html.Div(className="panel pad0", children=[
                html.Div(style={"padding": "12px 15px 2px"}, children=[
                    html.Div(className="panel-title", children=[html.Span("Patrimoine à protéger", className="kick")]),
                    html.H4("Les forêts classées" + ("" if region == ALLREG else f" · {region}")),
                ]),
                map_with_zoom(region, 340),
                html.Div(className="legend-row", style={"padding": "0 15px 12px"}, children=[
                    html.Span(className="chip", children=[html.Span(className="d", style={"background": MINT}), "Forêt classée (surface)"]),
                    html.Span(className="chip", children=[html.Span(className="d", style={"background": AMBER}), "Station climatique (T° max)"]),
                ]),
            ]),
            html.Div(className="panel", children=[
                html.Div(className="panel-title", children=[html.Span("Inventaire", className="kick")]),
                html.H4(f"{nb} forêts · {fr(surf)} km²"),
                html.Div(className="psub", children="Cliquez une région (en haut) pour filtrer la carte et la liste."),
                flist,
            ]),
        ]),
        html.Div(className="insight", style={"marginTop": "12px"}, children=[
            html.Span("Le lien qui compte", className="kick"),
            html.P([f"Presque tous les ménages ruraux (", html.B(f"{100-K['cuisson_rural']:.0f} %"),
                    ") brûlent bois ou charbon. La forêt a perdu ",
                    html.Span(f"{fr(K['foret_perte_km2'])} km² depuis 1990", className="o"),
                    f" (−{K['foret_perte_pct']:.0f} %). Chaque repas prélève sur le couvert. Les ",
                    html.B("Plateaux et la Centrale"), " concentrent les forêts sous pression."]),
        ]),
        foot(),
    ]


# ---- ÉMISSIONS ----
def sec_emis(region):
    return [
        sect_head("03", "L'empreinte carbone", "D'où viennent vraiment les émissions du Togo ?"),
        *([] if region == ALLREG else [scope_chip(region,
          "Bilan d'émissions : donnée nationale, non déclinée par région.")]),
        html.Div(className="kpi-band", children=[
            kpi(f"{K['part_energie_ges']:.0f} %", "des gaz à effet de serre (GES) viennent de l'Énergie", "good", ic="bolt"),
            kpi("AFAT", "agriculture, forêts & terres dominent", "warn", "le premier poste d'émissions", ic="leaf"),
            kpi(f"{K['co2_elec_mt']:.2f} Mt", "CO₂ de la production d'électricité", "warn", "en hausse avec le raccordement", ic="factory"),
            kpi(f"{K['pib_hab']}", "PIB/hab (USD)", "good", "une transition à financer sobrement", ic="money"),
        ]),
        html.Div(className="grid g-2", children=[
            html.Div(className="panel", children=[
                html.Div(className="panel-title", children=[html.Span("Par secteur · 2018", className="kick")]),
                html.H4("Part des secteurs dans les émissions de gaz à effet de serre (GES)"),
                graph(fig_ges()),
            ]),
            html.Div(className="panel", children=[
                html.Div(className="panel-title", children=[html.Span("Électricité · 1970-2022", className="kick a")]),
                html.H4("CO₂ de la production d'électricité (Mt CO₂e)"),
                graph(fig_co2()),
            ]),
        ]),
        html.Div(className="insight", style={"marginTop": "12px"}, children=[
            html.Span("La nuance de rigueur", className="kick"),
            html.P(["Contre-intuitif mais essentiel : l'Énergie ne pèse que ",
                    html.B(f"{K['part_energie_ges']:.0f} %"), " des gaz à effet de serre (GES) : l'agriculture et l'usage des "
                    "terres dominent. L'électrification rurale est d'abord un levier d'",
                    html.B("équité"), " et de ", html.B("protection des forêts"), ", plus que de climat."]),
            html.P(["Mais le CO₂ de l'électricité ", html.Span("augmente", className="o"),
                    " avec le raccordement : la transition doit rester ", html.B("solaire"),
                    ", pour ne pas troquer le bois contre le fossile."]),
        ]),
        foot(),
    ]


# ---- CLIMAT ----
def sec_climat(region):
    tr = D["temperatures_tendance"]
    trr = tr[tr["region"] == region] if region != ALLREG else tr
    warm = round(float(trr["pente_c_par_an"].mean()) * 10, 2) if len(trr) else K["rechauffement_moyen"]
    nb_villes = trr["villes"].nunique()
    n_up = int((trr["pente_c_par_an"] > 0).sum()); n_tot = int(len(trr))
    # gradient spatial : amplitude de température entre villes (fait structurel)
    tv = D["temperatures"]; last = tv[tv["annee"] == tv["annee"].max()].copy()
    if region != ALLREG:
        last = last[last["region"] == region]
    grad = float(last["tmax"].max() - last["tmax"].min()) if len(last) > 1 else 0.0
    hot = last.loc[last["tmax"].idxmax(), "villes"] if len(last) else "-"
    cold = last.loc[last["tmax"].idxmin(), "villes"] if len(last) else "-"
    return [
        sect_head("04", "Du Sud au Nord", "Deux lectures d'un même thermomètre : où il fait chaud, et si ça se réchauffe."),
        scope_chip(region, "Le filtre région (en haut) sélectionne les villes correspondantes."),
        html.Div(className="kpi-band", children=[
            kpi(f"+{c1(grad)} °C", "d'écart entre villes (même année)", "good",
                f"le + chaud : {hot} · le + frais : {cold}", ic="thermo"),
            kpi(f"{nb_villes}", "stations de mesure" + ("" if region == ALLREG else f" · {region}"), "good",
                "relevés mensuels 2013-2019", ic="pin"),
            kpi(f"{c2(warm)}", "°C / décennie (tendance moyenne)", "warn",
                f"{n_up} villes sur {n_tot} se réchauffent · 2013-2019", ic="chartup"),
            kpi("Chaleur → froid", "hypothèse : plus de refroidissement", "warn",
                "donc plus de demande d'électricité (lien indirect)", ic="sun"),
        ]),
        html.Div(className="grid g-2", children=[
            html.Div(className="panel", children=[
                html.Div(className="panel-title", children=[html.Span("Lecture 1 · le fait", className="kick")]),
                html.H4("Où il fait chaud : le gradient Sud → Nord"),
                html.Div(className="psub", children="Températures min / max par ville, ordonnées du Sud (Lomé) "
                         "au Nord (Dapaong). Plus on monte vers le Nord soudanien, plus il fait chaud."),
                graph(fig_temp(region)),
            ]),
            html.Div(className="panel", children=[
                html.Div(className="panel-title", children=[html.Span("Lecture 2 · la tendance", className="kick a")]),
                html.H4("Se réchauffe-t-il ? Tendance 2013-2019"),
                html.Div(className="psub", children="Pente de la température moyenne par ville sur 2013-2019, "
                         f"exprimée par décennie (régression linéaire). {n_up} villes sur {n_tot} se réchauffent."),
                graph(fig_trend(region)),
            ]),
        ]),
        html.Div(className="insight", style={"marginTop": "12px"}, children=[
            html.Span("Comment lire cette section", className="kick"),
            html.P([html.B("1. Un fait solide"), " : il fait structurellement ",
                    html.B("plus chaud au Nord"), f" qu'au Sud (jusqu'à {c1(grad)} °C d'écart entre villes). "
                    "Or c'est justement au Nord et en zone rurale que l'accès à l'électricité est le plus faible."]),
            html.P([html.B("2. Notre analyse de tendance"), " : sur 2013-2019, ",
                    html.B(f"{n_up} villes sur {n_tot} se réchauffent"), ", pour une moyenne de ",
                    html.Span(f"{c2(warm)} °C/décennie", className="o"),
                    " (régression linéaire de la température moyenne)."]),
            html.P(["Ce que ça implique : plus de chaleur = plus de besoins de refroidissement, donc de demande "
                    "d'électricité (lien indirect, non mesuré ici). Raison de plus pour une électricité ",
                    html.B("propre et fiable"), "."]),
        ]),
        foot(),
    ]


# ---- AGIR ----
def sec_agir(region):
    cards = [
        ("01", "Solariser les villages", MINT,
         "L'écart rural (25 %) se comble par le hors-réseau : mini-centrales et kits solaires, là où "
         "le raccordement est lent, coûteux, et le réseau peu fiable.",
         "Cible : zones rurales des Savanes, Kara, Centrale", "solar"),
        ("02", "Sortir du bois de cuisson", VERM,
         "0,9 % de cuisson propre en campagne : diffuser GPL et foyers améliorés allège directement la "
         "pression sur les forêts et la santé des ménages.",
         "Cible : ménages ruraux à l'échelle nationale", "pot"),
        ("03", "Garder une électricité propre", AMBER,
         "Le CO₂ de l'électricité augmente avec le raccordement : privilégier le solaire pour ne pas "
         "remplacer le bois par le fossile.",
         "Cible : mix électrique national", "cleanpower"),
        ("04", "Protéger les forêts sous pression", "#E28A1E",
         "Cibler les Plateaux et la Centrale, qui portent l'essentiel du couvert classé et subissent la "
         "demande rurale en bois-énergie.",
         "Cible : Plateaux (320 km²) & Centrale (256 km²)", "shield"),
    ]
    return [
        sect_head("05", "Agir, sobrement", "Quatre leviers pour électrifier sans déforester."),
        html.Div(className="reco-grid", children=[
            html.Div(className="reco-card", children=[
                html.Div(f"LEVIER {n}", className="lv", style={"color": col}),
                html.H4(t),
                html.P(txt),
                html.Div(who, className="who"),
                html.Div(className="ico", style={"borderColor": col + "55"},
                         children=html.Img(src=f"/assets/icons/{icn}_lv.png",
                                           style={"width": "22px", "height": "22px"})),
            ]) for (n, t, col, txt, who, icn) in cards]),
        html.Div(className="insight", style={"marginTop": "12px"}, children=[
            html.Span("La synthèse", className="kick"),
            html.P([html.B("Électrifier sans déforester"), " tient en une équation : ",
                    html.B("solaire hors-réseau"), " pour l'accès, ", html.B("cuisson propre"),
                    " pour épargner la forêt, ", html.B("mix solaire"), " pour ne pas carboniser la "
                    "transition. Une politique d'équité, de santé et de climat à la fois."]),
        ]),
        foot(),
    ]


SECTIONS = {"panorama": sec_panorama, "elec": sec_elec, "foret": sec_foret,
            "emis": sec_emis, "climat": sec_climat, "agir": sec_agir}


# ====================================================================
# CALLBACKS
# ====================================================================
@app.callback(Output("section", "data"),
              Input({"role": "nav", "sec": ALL}, "n_clicks"),
              prevent_initial_call=True)
def on_nav(_):
    t = ctx.triggered_id
    return t["sec"] if t else no_update


@app.callback(Output("region", "data"),
              Input({"role": "region", "reg": ALL}, "n_clicks"),
              Input({"role": "map", "idx": ALL}, "clickData"),
              prevent_initial_call=True)
def on_region(_, mapclicks):
    t = ctx.triggered_id
    if isinstance(t, dict) and t.get("role") == "map":
        for c in (mapclicks or []):
            if c and c.get("points"):
                cd = c["points"][0].get("customdata")
                if cd and len(cd) >= 2 and cd[1] in REGIONS:
                    return cd[1]
        return no_update
    if isinstance(t, dict) and t.get("role") == "region":
        return t["reg"]
    return no_update


app.clientside_callback(
    """
    function(_){
        setTimeout(function(){
            function getGd(){
                var gd = null;
                document.querySelectorAll('.js-plotly-plot').forEach(function(el){
                    if(el._fullLayout && el._fullLayout.map) gd = el;
                });
                return gd;
            }
            document.querySelectorAll('.map-zoom button').forEach(function(b){
                if(b.dataset.bound) return;
                b.dataset.bound = '1';
                b.addEventListener('click', function(){
                    var gd = getGd();
                    if(!gd || !window.Plotly) return;
                    var z = 5.75;
                    try { z = gd._fullLayout.map._subplot.map.getZoom(); } catch(e){}
                    if(z == null){ try { z = gd._fullLayout.map.zoom; } catch(e){} }
                    z = (z || 5.75) + (b.textContent.trim() === '+' ? 0.9 : -0.9);
                    z = Math.max(3, Math.min(14, z));
                    window.Plotly.relayout(gd, {'map.zoom': z});
                });
            });
        }, 250);
        return window.dash_clientside.no_update;
    }
    """,
    Output("zoom-sink", "data"),
    Input("body", "children"),
)


@app.callback(Output("rail-container", "children"), Input("section", "data"))
def render_rail(sec):
    return build_rail(sec)


@app.callback(Output("header-container", "children"), Input("region", "data"))
def render_header(region):
    return header(region)


@app.callback(Output("body", "children"),
              Input("section", "data"), Input("region", "data"))
def render_body(sec, region):
    fn = SECTIONS.get(sec, sec_panorama)
    return fn(region or ALLREG)


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=8050)
