"""
SPECULA - Simulacao 1: deteccao de alteracoes foliares precoces pelo sensor AS7265x.

Modelo de folha: PROSPECT-D (Feret et al., 2017), via pacote prosail.
Sensor: 18 bandas gaussianas, FWHM 20 nm (datasheet ams AS7265x).
Saidas: figuras em ../fig e tabela de resultados em ../resultados_optica.json
"""
import json, os
import numpy as np
import prosail
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import roc_auc_score

RNG = np.random.default_rng(20261111)
HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "..", "fig"); os.makedirs(FIG, exist_ok=True)

# ---------------------------------------------------------------- parametros
# Folha sadia de referencia (valores tipicos de folha de dicotiledonea; N = 1,5 como em Soares et al., 2022)
BASE = dict(N=1.5, cab=45.0, car=10.0, cbrown=0.0, cw=0.015, cm=0.009)
# Variabilidade natural entre folhas (coeficiente de variacao; hipotese declarada no relatorio)
CV_ENTRE = dict(N=0.05, cab=0.15, car=0.15, cw=0.10, cm=0.10)
# Deriva natural da mesma folha entre visitas (envelhecimento em poucas semanas; hipotese)
CV_TEMPO = dict(N=0.005, cab=0.02, car=0.02, cw=0.02, cm=0.01)
# Centros das 18 bandas do AS7265x (datasheet ams) e largura a meia altura
CENTROS = np.array([410, 435, 460, 485, 510, 535, 560, 585, 610, 645, 680, 705, 730, 760, 810, 860, 900, 940])
FWHM = 20.0
# Sensor de 3 bandas largas tipo camera RGN (Mapir Survey3W, usado por Soares et al., 2022)
RGN = [(550, 60), (660, 40), (850, 80)]

def prospect(p):
    wv, r, t = prosail.run_prospect(p["N"], p["cab"], p["car"], p["cbrown"], p["cw"], p["cm"],
                                    ant=0.0, prospect_version="D")
    return wv, r

WV, R0 = prospect(BASE)

def filtro(centro, fwhm):
    s = fwhm / 2.3548
    w = np.exp(-0.5 * ((WV - centro) / s) ** 2)
    return w / w.sum()

F18 = np.array([filtro(c, FWHM) for c in CENTROS])
F3 = np.array([filtro(c, f) for c, f in RGN])

def bandas(r, F):
    return F @ r

# ---------------------------------------------------------------- cenarios de infeccao precoce
def infectar(p, s, cenario):
    q = dict(p)
    if cenario == "A":   # direcoes observadas a 15 DAI por Soares et al. (2022): carotenoides e materia seca sobem, agua cai, clorofila sem diferenca
        q["car"] *= (1 + s); q["cm"] *= (1 + s); q["cw"] *= (1 - s)
    elif cenario == "B": # perda de clorofila, tipica de fases posteriores da infeccao
        q["cab"] *= (1 - s)
    return q

def sorteia(p0, cv, rng):
    return {k: (v * (1 + cv[k] * rng.standard_normal()) if k in cv else v) for k, v in p0.items()}

def mede(r_band, ruido, rng):
    return r_band * (1 + ruido * rng.standard_normal(r_band.shape))

# ---------------------------------------------------------------- figura 1: espectros
fig, ax = plt.subplots(figsize=(7.2, 3.6))
for s, cor, rot in [(0, "#1b7837", "Sadia"), (0.10, "#b2182b", "Cenário A, efeito de 10%"), (0.10, "#2166ac", "Cenário B, efeito de 10%")]:
    cen = "A" if "A" in rot else ("B" if "B" in rot else "A")
    wv, r = prospect(infectar(BASE, s, cen))
    m = WV <= 1000
    ax.plot(WV[m], r[m], color=cor, lw=1.3, label=rot)
    ax.plot(CENTROS, bandas(r, F18), "o", color=cor, ms=3.5)
for c in CENTROS:
    ax.axvspan(c - FWHM / 2, c + FWHM / 2, color="0.85", alpha=0.35, lw=0)
ax.set_xlabel("Comprimento de onda (nm)"); ax.set_ylabel("Refletância da folha")
ax.set_xlim(400, 1000); ax.legend(frameon=False, fontsize=8, loc="upper left")
ax.set_title("PROSPECT-D: folha de café simulada e as 18 bandas do AS7265x (faixas cinza)", fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig1_espectros.pdf")); plt.close(fig)

# ---------------------------------------------------------------- figura 2: diferenca relativa por banda
sadia = bandas(R0, F18)
fig, ax = plt.subplots(figsize=(7.2, 3.2))
for s, cor in [(0.05, "#fdae61"), (0.10, "#d7191c"), (0.20, "#7b3294")]:
    rA = bandas(prospect(infectar(BASE, s, "A"))[1], F18)
    ax.plot(CENTROS, 100 * (rA / sadia - 1), "-o", color=cor, ms=3, label=f"Cenário A, efeito {int(s*100)}%")
rB = bandas(prospect(infectar(BASE, 0.10, "B"))[1], F18)
ax.plot(CENTROS, 100 * (rB / sadia - 1), "--s", color="#2166ac", ms=3, label="Cenário B, efeito 10%")
for n, ls in [(0.01, ":"), (0.02, "-.")]:
    ax.axhspan(-100 * n, 100 * n, color="0.6", alpha=0.15)
    ax.axhline(100 * n, color="0.4", ls=ls, lw=0.8); ax.axhline(-100 * n, color="0.4", ls=ls, lw=0.8)
ax.text(945, 2.2, "ruído 2%", fontsize=7, color="0.3", ha="right"); ax.text(945, 1.1, "ruído 1%", fontsize=7, color="0.3", ha="right")
ax.axhline(0, color="k", lw=0.5)
ax.set_xlabel("Centro da banda (nm)"); ax.set_ylabel("Mudança na refletância (%)")
ax.legend(frameon=False, fontsize=7, ncol=2); ax.set_title("Mudança relativa por banda frente ao ruído de medição", fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig2_bandas.pdf")); plt.close(fig)

# ---------------------------------------------------------------- deteccao: transversal x longitudinal
def auc_cv(X, y, rng):
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=int(rng.integers(1e9)))
    p = cross_val_predict(LinearDiscriminantAnalysis(), X, y, cv=skf, method="predict_proba")[:, 1]
    return roc_auc_score(y, p)

def experimento(s, cenario, ruido, F, n=200, n_base=4, rng=RNG, modo="transversal"):
    X, y = [], []
    for classe in (0, 1):
        for _ in range(n):
            folha = sorteia(BASE, CV_ENTRE, rng)          # cada folha tem seus proprios parametros
            if modo == "transversal":
                p = infectar(folha, s, cenario) if classe else folha
                r = bandas(prospect(p)[1], F)
                X.append(np.log(mede(r, ruido, rng)))
            else:
                # linha de base: media de n_base visitas da mesma folha, com deriva natural e ruido
                base = np.mean([np.log(mede(bandas(prospect(sorteia(folha, CV_TEMPO, rng))[1], F), ruido, rng))
                                for _ in range(n_base)], axis=0)
                atual = sorteia(folha, CV_TEMPO, rng)
                if classe:
                    atual = infectar(atual, s, cenario)
                r = bandas(prospect(atual)[1], F)
                X.append(np.log(mede(r, ruido, rng)) - base)
            y.append(classe)
    return auc_cv(np.array(X), np.array(y), rng)

efeitos = [0.0, 0.025, 0.05, 0.10, 0.15, 0.20]
REP = 3
def rep(*a, **k):
    v = [experimento(*a, **k) for _ in range(REP)]
    return round(float(np.mean(v)), 3), round(float(np.std(v)), 3)
res = {"efeitos": efeitos, "repeticoes": REP, "curvas": {}, "dp": {}}
for modo in ("transversal", "longitudinal"):
    for ruido in (0.01, 0.02):
        for cen in ("A", "B"):
            chave = f"{modo}|ruido{int(ruido*100)}|{cen}"
            out = [rep(s, cen, ruido, F18, modo=modo) for s in efeitos]
            res["curvas"][chave] = [o[0] for o in out]; res["dp"][chave] = [o[1] for o in out]
            print(chave, res["curvas"][chave], flush=True)

fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.2), sharey=True)
for ax, cen, tit in [(axs[0], "A", "Cenário A (Soares et al., 2022)"), (axs[1], "B", "Cenário B (perda de clorofila)")]:
    for modo, ls in [("transversal", "--"), ("longitudinal", "-")]:
        for ruido, cor in [(0.01, "#1b7837"), (0.02, "#d95f02")]:
            v = res["curvas"][f"{modo}|ruido{int(ruido*100)}|{cen}"]
            ax.errorbar([100 * e for e in efeitos], v, yerr=res["dp"][f"{modo}|ruido{int(ruido*100)}|{cen}"], fmt=ls, marker="o", ms=3, color=cor, capsize=2, lw=1,
                    label=f"{'autorreferência' if modo=='longitudinal' else 'comparação entre folhas'}, ruído {int(ruido*100)}%")
    ax.axhline(0.5, color="0.6", lw=0.6); ax.axhline(0.8, color="0.6", lw=0.6, ls=":")
    ax.set_title(tit, fontsize=9); ax.set_xlabel("Tamanho do efeito (%)")
axs[0].set_ylabel("AUC (validação cruzada)"); axs[0].set_ylim(0.4, 1.02)
axs[1].legend(frameon=False, fontsize=6.5, loc="lower right")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig3_auc.pdf")); plt.close(fig)

# ---------------------------------------------------------------- comparacao de configuracoes de sensor (longitudinal, ruido 1%)
Ffull = np.eye(len(WV))[(WV >= 400) & (WV <= 1000)][::5]   # espectrometro de referencia, 5 nm
configs = {"Espectrômetro (400 a 1000 nm, 5 nm)": Ffull, "AS7265x (18 bandas)": F18, "Câmera RGN (3 bandas largas)": F3}
res["configs"] = {}
for nome, F in configs.items():
    out = [rep(s, "A", 0.01, F, n=150, modo="longitudinal") for s in efeitos]
    res["configs"][nome] = [o[0] for o in out]; res.setdefault("configs_dp", {})[nome] = [o[1] for o in out]
    print(nome, res["configs"][nome], flush=True)
fig, ax = plt.subplots(figsize=(5.4, 3.2))
for (nome, v), cor in zip(res["configs"].items(), ["k", "#1b7837", "#b2182b"]):
    ax.plot([100 * e for e in efeitos], v, "-o", ms=3, color=cor, label=nome)
ax.axhline(0.5, color="0.6", lw=0.6); ax.set_ylim(0.4, 1.02)
ax.set_xlabel("Tamanho do efeito, cenário A (%)"); ax.set_ylabel("AUC")
ax.legend(frameon=False, fontsize=7, loc="lower right"); ax.set_title("Autorreferência com ruído de 1%: sensor x referência", fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig4_sensores.pdf")); plt.close(fig)

res["parametros"] = {"base": BASE, "cv_entre_folhas": CV_ENTRE, "cv_tempo": CV_TEMPO, "centros": CENTROS.tolist(), "fwhm": FWHM,
                     "rgn": RGN, "semente": 20261111}
res["mudanca_bandas_A10"] = dict(zip(CENTROS.tolist(), np.round(100 * (bandas(prospect(infectar(BASE, .10, 'A'))[1], F18) / sadia - 1), 2).tolist()))
res["mudanca_bandas_B10"] = dict(zip(CENTROS.tolist(), np.round(100 * (rB / sadia - 1), 2).tolist()))
json.dump(res, open(os.path.join(HERE, "..", "resultados_optica.json"), "w"), indent=1, ensure_ascii=False)
print("ok")
