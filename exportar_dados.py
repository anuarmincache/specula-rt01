"""
SPECULA RT-01: exporta para CSV todas as entradas e saídas numéricas das simulações.

Uso (na raiz do repositório, depois de rodar as duas simulações):
    python exportar_dados.py
Gera a pasta dados/ com os parâmetros de entrada, as âncoras da literatura e os resultados.
Para gerar as figuras em PNG a partir dos PDFs: pdftoppm -png -r 130 -singlefile fig/X.pdf fig/X
"""
import csv, json, os
import numpy as np
import prosail

H = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(H, "dados"); os.makedirs(D, exist_ok=True)
O = json.load(open(os.path.join(H, "resultados_optica.json")))
C = json.load(open(os.path.join(H, "resultados_coorte.json")))

def escreve(nome, cab, linhas):
    with open(os.path.join(D, nome), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(cab); w.writerows(linhas)

# ------------------------------------------------------------ entradas
escreve("as7265x_canais.csv", ["canal_nm", "fwhm_nm", "fonte"],
        [[c, 20, "Datasheet ams AS7265x"] for c in O["parametros"]["centros"]])
orig = {"N": "Soares et al. 2022 (N=1,5)", "cab": "hipótese", "car": "hipótese",
        "cbrown": "Soares et al. 2022 (zero, folha verde)", "cw": "hipótese", "cm": "hipótese"}
P = O["parametros"]
escreve("folha_parametros_prospect.csv", ["parametro", "valor_base", "cv_entre_folhas", "cv_no_tempo", "origem"],
        [[k, v, P["cv_entre_folhas"].get(k, ""), P["cv_tempo"].get(k, ""), orig[k]] for k, v in P["base"].items()])
clima = [(1, 20, 28, 285), (2, 20, 28, 225), (3, 19, 27, 162), (4, 17, 26, 94), (5, 14, 23, 106), (6, 13, 22, 96),
         (7, 13, 22, 73), (8, 14, 24, 68), (9, 16, 26, 129), (10, 17, 27, 177), (11, 18, 27, 177), (12, 19, 28, 210)]
escreve("clima_apucarana_climatempo.csv", ["mes", "tmin_C", "tmax_C", "precip_mm", "fonte"],
        [list(r) + ["Climatempo, climatologia de 30 anos, acesso 11/11/2026"] for r in clima])
escreve("incubacao_por_mes.csv", ["mes", "ortolani_1971_dias", "moraes_1976_dias", "equacoes"],
        [[m, v["ortolani"], v["moraes"], "Y=63,47-1,526*Tmed ; Y=93,27-0,99*Tmax-1,51*Tmin (Alfonsi et al. 2019)"]
         for m, v in C["incubacao"].items()])
escreve("ancoras_epidemiologicas.csv", ["informacao", "valor", "local", "fonte"], [
    ("início da epidemia", "dezembro", "Varginha MG, 1998 a 2006", "Japiassú et al. 2005; Meira e Rodrigues 2009"),
    ("pico de incidência", "maio a julho", "Varginha MG", "Japiassú et al. 2005"),
    ("pico com controle químico", "15%", "Poço Fundo MG, 2008", "Lopes et al. 2012"),
    ("pico sem controle (organo-mineral)", "91%", "Poço Fundo MG, 2008", "Lopes et al. 2012"),
    ("pico sem controle (orgânico)", "87,5%", "Poço Fundo MG, 2008", "Lopes et al. 2012"),
    ("período de incubação no Brasil", "28 a 65 dias", "SP e MG", "Alfonsi et al. 2019"),
    ("amostragem padrão", "100 folhas do 3º e 4º par, terço médio", "Varginha MG", "Japiassú et al. 2005")])

# ------------------------------------------------------------ saídas da simulação óptica
linhas = []
for k, v in O["curvas"].items():
    modo, r, cen = k.split("|")
    for e, a, d in zip(O["efeitos"], v, O["dp"][k]):
        linhas.append([modo, r.replace("ruido", ""), cen, 100 * e, a, d, O["repeticoes"]])
escreve("resultado_auc_curvas.csv", ["modo", "ruido_pct", "cenario", "efeito_pct", "auc_media", "auc_dp", "repeticoes"], linhas)
escreve("resultado_auc_sensores.csv", ["sensor", "efeito_pct", "auc_media", "auc_dp"],
        [[k, 100 * e, a, d] for k, v in O["configs"].items() for e, a, d in zip(O["efeitos"], v, O["configs_dp"][k])])
escreve("resultado_mudanca_por_banda.csv", ["canal_nm", "cenario_A_10pct", "cenario_B_10pct"],
        [[c, O["mudanca_bandas_A10"][str(c)], O["mudanca_bandas_B10"][str(c)]] for c in P["centros"]])

def roda(p):
    return prosail.run_prospect(p["N"], p["cab"], p["car"], p["cbrown"], p["cw"], p["cm"], ant=0.0, prospect_version="D")
B = P["base"]; A = dict(B); A["car"] *= 1.1; A["cm"] *= 1.1; A["cw"] *= 0.9; Bb = dict(B); Bb["cab"] *= 0.9
wv, r0, _ = roda(B); _, rA, _ = roda(A); _, rB, _ = roda(Bb)
escreve("espectros_prospectd_400_1000nm.csv",
        ["comprimento_onda_nm", "refletancia_sadia", "refletancia_cenario_A_10pct", "refletancia_cenario_B_10pct"],
        [[int(wv[i]), round(r0[i], 6), round(rA[i], 6), round(rB[i], 6)] for i in np.where(wv <= 1000)[0]])

# ------------------------------------------------------------ saídas da simulação da coorte
k0 = list(next(iter(C["cenarios"].values())).keys())
escreve("resultado_coorte_cenarios.csv", ["incubacao", "perda_semanal", "incidencia_final"] + k0,
        [k.split("|") + [v[x] for x in k0] for k, v in C["cenarios"].items()])
k1 = list(next(iter(C["comparacao_calendarios"].values())).keys())
escreve("resultado_calendarios.csv", ["calendario", "incubacao"] + k1,
        [k.split("|") + [v[x] for x in k1] for k, v in C["comparacao_calendarios"].items()])
print("dados exportados:", sorted(os.listdir(D)))
