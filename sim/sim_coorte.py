"""
SPECULA - Simulacao 2: Monte Carlo da coorte de folhas etiquetadas em Cambira (PR).

Calendario do cronograma do site (v2): etiquetagem em 01/12/2027; fase intensiva com 2 visitas
por semana ate 29/02/2028; acompanhamento com 1 visita por semana ate 15/05/2028.

Fontes dos parametros:
- Progresso da doenca: inicio em dezembro e pico entre maio e julho em lavoura sem controle
  (Japiassu et al., 2005; Meira e Rodrigues, Varginha, 1998 a 2006); pico de 15% com controle
  quimico e de 87,5 a 91% sem controle no sul de Minas (Lopes et al., 2012).
- Periodo de incubacao: equacoes de Ortolani et al. (1971) e Moraes et al. (1976), revisadas por
  Alfonsi et al. (2019), com a climatologia mensal de Apucarana (Climatempo, 30 anos).
"""
import json, os, datetime as dt
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "..", "fig"); os.makedirs(FIG, exist_ok=True)
RNG = np.random.default_rng(20261112)

D0 = dt.date(2027, 12, 1)
def dia(d): return (d - D0).days

# ---------------------------------------------------------------- calendario de visitas
visitas = []
d = dt.date(2027, 12, 11)
while d <= dt.date(2028, 2, 29):          # fase intensiva: segunda e quinta
    if d.weekday() in (0, 3): visitas.append(dia(d))
    d += dt.timedelta(days=1)
d = dt.date(2028, 3, 1)
while d <= dt.date(2028, 5, 15):          # acompanhamento: segunda
    if d.weekday() == 0: visitas.append(dia(d))
    d += dt.timedelta(days=1)
VIS = np.array([dia(dt.date(2027, 12, 1))] + visitas)   # medicao inicial na etiquetagem
FIM = dia(dt.date(2028, 5, 15))

# ---------------------------------------------------------------- clima de Apucarana (Climatempo, minimas e maximas mensais)
TMIN = {1: 20, 2: 20, 3: 19, 4: 17, 5: 14, 6: 13, 7: 13, 8: 14, 9: 16, 10: 17, 11: 18, 12: 19}
TMAX = {1: 28, 2: 28, 3: 27, 4: 26, 5: 23, 6: 22, 7: 22, 8: 24, 9: 26, 10: 27, 11: 27, 12: 28}
def ip_ortolani(m):   # Y = 63,47 - 1,526 x Tmedia
    return 63.47 - 1.526 * (TMIN[m] + TMAX[m]) / 2
def ip_moraes(m):     # Y = 93,27 - 0,99 Tmax - 1,51 Tmin (pleno sol, macroclima)
    return 93.27 - 0.99 * TMAX[m] - 1.51 * TMIN[m]
def mes_do_dia(x): return (D0 + dt.timedelta(days=int(x))).month

# ---------------------------------------------------------------- curva de progresso (fracao das folhas etiquetadas que mostram lesao)
T50 = dia(dt.date(2028, 4, 1)); ESC = 18.0      # inicio em dezembro, pico entre maio e julho
def F(t, Pfin):
    g = lambda x: 1 / (1 + np.exp(-(x - T50) / ESC))
    return Pfin * (g(t) - g(0)) / (g(dia(dt.date(2028, 7, 31))) - g(0))

def roda(Pfin, perda_sem, eq, n=1500, rng=RNG):
    """Uma realizacao da campanha. Retorna lista de folhas positivas detectadas com suas medicoes."""
    u = rng.random(n)
    t_grid = np.arange(0, dia(dt.date(2028, 7, 31)) + 1)
    Fg = F(t_grid, Pfin)
    doente = u < Fg[-1]
    t_sint = np.interp(u[doente], Fg, t_grid)       # data de aparecimento do sintoma
    ipf = ip_ortolani if eq == "ortolani" else ip_moraes
    # incubacao do mes provavel da infeccao (iteracao simples), com variacao de +-15%
    ip = np.array([ipf(mes_do_dia(ts - 30)) for ts in t_sint])
    ip = np.array([ipf(mes_do_dia(ts - i)) for ts, i in zip(t_sint, ip)]) * (1 + 0.15 * rng.uniform(-1, 1, ip.size))
    t_inf = t_sint - ip
    # perda da folha ou da etiqueta (queda natural, poda, dano), taxa semanal constante
    t_perda = rng.exponential(7 / perda_sem, n)
    pos = []
    idx_doente = np.where(doente)[0]
    for k, i in enumerate(idx_doente):
        ts, ti = t_sint[k], t_inf[k]
        v_det = VIS[VIS >= ts]
        if v_det.size == 0 or v_det[0] > FIM: continue           # sintoma depois do fim da campanha
        if t_perda[i] < v_det[0]: continue                        # folha perdida antes de detectar
        pre = VIS[(VIS >= max(ti, 0)) & (VIS < ts) & (VIS < t_perda[i])]
        antes_inf = VIS[(VIS < ti) & (VIS < t_perda[i])]
        pos.append(dict(t_det=int(v_det[0]), lead=(v_det[0] - pre).tolist(), n_pre=int(pre.size), n_base=int(antes_inf.size)))
    vivas_fim = int(np.sum(t_perda > FIM))
    return pos, vivas_fim

CENARIOS = [0.10, 0.20, 0.40, 0.70]
N_MC = 300
res = {"visitas": int(VIS.size), "medicoes_max": int(VIS.size * 1500), "cenarios": {}}
for eq in ("ortolani", "moraes"):
    for perda in (0.005, 0.01, 0.02):
        for P in CENARIOS:
            npos, npre_med, n14, nbase_ok, vivas = [], [], [], [], []
            for _ in range(N_MC):
                pos, viv = roda(P, perda, eq)
                npos.append(len(pos)); vivas.append(viv)
                npre_med.append(np.median([p["n_pre"] for p in pos]) if pos else 0)
                n14.append(sum(any(14 <= l <= 21 for l in p["lead"]) for p in pos))
                nbase_ok.append(sum(p["n_base"] >= 2 for p in pos))
            res["cenarios"][f"{eq}|{perda}|{P}"] = dict(
                positivos_med=float(np.median(npos)), positivos_p5=float(np.percentile(npos, 5)), positivos_p95=float(np.percentile(npos, 95)),
                pre_por_positivo_med=float(np.median(npre_med)),
                com_medida_14a21d_med=float(np.median(n14)), com_medida_14a21d_p5=float(np.percentile(n14, 5)),
                com_linha_de_base_med=float(np.median(nbase_ok)),
                prob_96_em_14a21d=float(np.mean(np.array(n14) >= 96)),
                folhas_vivas_fim_med=float(np.median(vivas)))
            print(eq, perda, P, res["cenarios"][f"{eq}|{perda}|{P}"], flush=True)

# ---------------------------------------------------------------- figura 5: curvas de progresso, incubacao e calendario
fig, ax = plt.subplots(figsize=(7.2, 3.2))
tt = np.arange(0, dia(dt.date(2028, 7, 31)) + 1); datas = [D0 + dt.timedelta(days=int(x)) for x in tt]
for P, cor in zip(CENARIOS, ["#91bfdb", "#4575b4", "#fc8d59", "#d73027"]):
    ax.plot(datas, 100 * F(tt, P), color=cor, lw=1.5, label=f"incidência final {int(P*100)}%")
for v in VIS:
    ax.axvline(D0 + dt.timedelta(days=int(v)), color="0.75", lw=0.4, zorder=0)
ax.axvspan(D0 + dt.timedelta(days=FIM), datas[-1], color="0.9", zorder=0)
ax.text(D0 + dt.timedelta(days=FIM + 4), 70, "fora da\ncampanha", fontsize=7, color="0.35")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b/%y"))
ax.set_ylabel("Folhas etiquetadas com lesão (%)"); ax.legend(frameon=False, fontsize=7, loc="upper left")
ax.set_title("Cenários de progresso da ferrugem e as 34 visitas da campanha (linhas verticais)", fontsize=9)
ax2 = ax.twinx(); meses = list(range(12, 13)) + list(range(1, 8))
xm = [dt.date(2027 if m == 12 else 2028, m, 15) for m in meses]
ax2.plot(xm, [ip_ortolani(m) for m in meses], "k--", lw=0.9, label="incubação, Ortolani")
ax2.plot(xm, [ip_moraes(m) for m in meses], "k:", lw=0.9, label="incubação, Moraes")
ax2.set_ylabel("Incubação (dias)"); ax2.set_ylim(0, 70); ax2.legend(frameon=False, fontsize=7, loc="center left")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig5_progresso.pdf")); plt.close(fig)

# ---------------------------------------------------------------- figura 6: folhas positivas por cenario
fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.1), sharey=True)
for ax, eq, tit in [(axs[0], "ortolani", "Incubação curta (Ortolani)"), (axs[1], "moraes", "Incubação longa (Moraes)")]:
    for perda, cor, dx in [(0.005, "#1b7837", -1.2), (0.01, "#7570b3", 0), (0.02, "#d95f02", 1.2)]:
        m = [res["cenarios"][f"{eq}|{perda}|{P}"] for P in CENARIOS]
        x = np.array([100 * P for P in CENARIOS]) + dx
        ax.errorbar(x, [c["com_medida_14a21d_med"] for c in m],
                    yerr=[[c["com_medida_14a21d_med"] - c["com_medida_14a21d_p5"] for c in m], [0] * len(m)],
                    fmt="o-", ms=3.5, color=cor, capsize=2, lw=1, label=f"perda de {perda*100:.1f}% por semana")
    ax.axhline(96, color="k", ls="--", lw=0.8); ax.text(12, 105, "96 folhas: IC95% de ±10 pontos", fontsize=7)
    ax.set_xlabel("Incidência final nas folhas etiquetadas (%)"); ax.set_title(tit, fontsize=9)
axs[0].set_ylabel("Positivas com medida 14 a 21 dias antes"); axs[1].legend(frameon=False, fontsize=7, loc="upper left")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig6_positivos.pdf")); plt.close(fig)

# ---------------------------------------------------------------- figura 7: antecedencia das medicoes (cenario de referencia)
pos, _ = roda(0.20, 0.01, "ortolani", rng=np.random.default_rng(7))
leads = np.concatenate([p["lead"] for p in pos]) if pos else np.array([])
npre = [p["n_pre"] for p in pos]
res["referencia_20pct"] = dict(positivos=len(pos), pre_mediana=float(np.median(npre)), pre_p10=float(np.percentile(npre, 10)),
                              pre_p90=float(np.percentile(npre, 90)), medicoes_pre_total=int(leads.size))
fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.0))
axs[0].hist(npre, bins=np.arange(0, max(npre) + 2) - 0.5, color="#4575b4", edgecolor="w")
axs[0].set_xlabel("Medições antes do sintoma, por folha"); axs[0].set_ylabel("Folhas positivas")
axs[1].hist(leads, bins=np.arange(0, 71, 7), color="#1b7837", edgecolor="w")
axs[1].set_xlabel("Antecedência da medição (dias antes da lesão)"); axs[1].set_ylabel("Medições")
fig.suptitle("Cenário de referência: incidência de 20%, perda de 1% por semana, incubação de Ortolani", fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig7_antecedencia.pdf")); plt.close(fig)

res["incubacao"] = {m: dict(ortolani=round(ip_ortolani(m), 1), moraes=round(ip_moraes(m), 1)) for m in [12, 1, 2, 3, 4, 5, 6]}
json.dump(res, open(os.path.join(HERE, "..", "resultados_coorte.json"), "w"), indent=1)
print("ok", res["referencia_20pct"], res["incubacao"])

# ---------------------------------------------------------------- calendario alternativo, ajustado a epidemia
# Visitas semanais em dezembro e janeiro (linha de base), duas por semana de 01/02 a 15/05/2028.
def calendario_b():
    v = [dia(dt.date(2027, 12, 1))]
    d = dt.date(2027, 12, 6)
    while d <= dt.date(2028, 5, 15):
        if d < dt.date(2028, 2, 1):
            if d.weekday() == 0: v.append(dia(d))
        elif d.weekday() in (0, 3): v.append(dia(d))
        d += dt.timedelta(days=1)
    return np.array(v)

VIS_A = VIS.copy(); VIS_B = calendario_b()
comp = {}
for nome, V in (("A_atual", VIS_A), ("B_ajustado", VIS_B)):
    VIS = V
    for eq in ("ortolani", "moraes"):
        npre_all, npos = [], []
        for _ in range(N_MC):
            pos, _ = roda(0.20, 0.01, eq)
            npos.append(len(pos)); npre_all += [p["n_pre"] for p in pos]
        comp[f"{nome}|{eq}"] = dict(visitas=int(V.size), medicoes=int(V.size * 1500), positivos_med=float(np.median(npos)),
                                   pre_mediana=float(np.median(npre_all)), pre_p10=float(np.percentile(npre_all, 10)),
                                   pre_p90=float(np.percentile(npre_all, 90)), frac_pre_ge6=float(np.mean(np.array(npre_all) >= 6)))
        print(nome, eq, comp[f"{nome}|{eq}"], flush=True)
res["comparacao_calendarios"] = comp

fig, ax = plt.subplots(figsize=(6.0, 3.0))
for (nome, V), cor, dx in ((("Calendário atual (34 visitas)", VIS_A), "#7570b3", -0.2), (("Calendário ajustado à epidemia", VIS_B), "#1b7837", 0.2)):
    VIS = V; allp = []
    for _ in range(100):
        pos, _ = roda(0.20, 0.01, "ortolani"); allp += [p["n_pre"] for p in pos]
    h = np.bincount(allp, minlength=16)[:16] / len(allp)
    ax.bar(np.arange(16) + dx, h, width=0.4, color=cor, label=f"{nome.split(' (')[0]} ({V.size} visitas)")
ax.set_xlabel("Medições antes do sintoma, por folha positiva"); ax.set_ylabel("Fração das folhas positivas")
ax.legend(frameon=False, fontsize=7.5); ax.set_title("Efeito do calendário de visitas (incidência 20%, incubação de Ortolani)", fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig8_calendarios.pdf")); plt.close(fig)
json.dump(res, open(os.path.join(HERE, "..", "resultados_coorte.json"), "w"), indent=1)
print("ok2")
