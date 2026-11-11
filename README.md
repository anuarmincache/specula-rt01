# SPECULA, Relatório Técnico RT-01: prova de conceito por simulação

Este repositório reúne as duas simulações que sustentam o desenho do projeto SPECULA (Programa Centelha 3 Paraná).
São simulações, não experimentos: o estágio da solução é Ideia.

- `sim/sim_optica.py`: folha de café simulada com PROSPECT-D e medida pelo modelo do sensor AS7265x (18 bandas). Compara a detecção entre folhas diferentes com a autorreferência da mesma folha.
- `sim/sim_coorte.py`: Monte Carlo da coorte de 1.500 folhas etiquetadas em Cambira (PR), com incubação pelo clima local e progresso da doença ancorado em dados publicados.
- `relatorio_RT01.tex` e `relatorio_RT01.pdf`: relatório completo, com métodos, resultados, limitações e referências.

## Como reproduzir

    pip install -r requirements.txt
    cd sim
    python sim_optica.py     # gera fig1 a fig4 e resultados_optica.json (cerca de 4 minutos)
    python sim_coorte.py     # gera fig5 a fig8 e resultados_coorte.json (cerca de 1 minuto)
    cd ..
    python gen_tex.py        # escreve relatorio_RT01.tex com os números dos arquivos JSON
    pdflatex relatorio_RT01.tex

Sementes fixas: 20261111 (óptica) e 20261112 (coorte).

Repositório: https://github.com/anuarmincache/specula-rt01
