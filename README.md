# Laboratórios Virtuais de Física — Mecânica (Ensino Médio)

Conjunto de **seis laboratórios virtuais em Python** para o ensino de mecânica no Ensino Médio.
Cada laboratório é um aplicativo de janela (Tkinter + Matplotlib) que **funciona sem internet**,
com simulação animada, gráficos em tempo real, tabela experimental, exportação de dados e
roteiro de pré-teste/pós-teste.

- **Repositório:** https://github.com/MARIOMAR1975/Lab_Virtual_Fis_Mec_Ens_Medio
- **Versão do conjunto:** `v1.0.0` (22/11/2026) — ver [CHANGELOG.md](CHANGELOG.md)
- **Licença:** [MIT](LICENSE) — uso, cópia, modificação e distribuição livres, com aviso de autoria
- **Autor:** Mario Omar Calla Salcedo

## Os seis módulos

| # | Módulo (código-fonte) | O que simula | Roteiro |
|---|---|---|---|
| 1 | [`01_mru_mruv.py`](01_mru_mruv.py) | Carrinho sobre mesa com sensor e régua; MRU e MRUV; gráficos x(t), v(t), a(t); ajuste de curva opcional; erro experimental opcional | [roteiro](01_mru_mruv.md) |
| 2 | [`02_queda_livre.py`](02_queda_livre.py) | Queda livre ideal: h(t) = h₀ − ½gt², v = gt; ajuste h₀ = A·t²; tabela de ensaios | [roteiro](02_queda_livre.md) |
| 3 | [`03_movimento_parabolico.py`](03_movimento_parabolico.py) | Lançamento oblíquo: x(t), y(t), vx(t), vy(t); ângulo, altura inicial e gravidade (Terra, Lua, Marte, Júpiter) | [roteiro](03_movimento_parabolico.md) |
| 4 | [`04_segunda_lei_newton.py`](04_segunda_lei_newton.py) | Carrinho ligado por fio e polia a um bloco suspenso, com atrito (μ); F, a, T; ajustes linear e hiperbólico | [roteiro](04_segunda_lei_newton.md) |
| 5 | [`05_conservacao_energia_mecanica.py`](05_conservacao_energia_mecanica.py) | Carrinho em pista (montanhas, rampa ou vale), com e sem atrito; Ep, Ec, Em e energia dissipada | [roteiro](05_conservacao_energia_mecanica.md) |
| 6 | [`06_coeficiente_restituicao.py`](06_coeficiente_restituicao.py) | Bolinha que quica; alturas H₀, H₁, H₂…; estimativa de e = √(Hᵢ/Hᵢ₋₁) por alturas e por velocidades | [roteiro](06_coeficiente_restituicao.md) |

Todos os módulos oferecem: botões Iniciar/Pausar/Passo/Resetar, tabela experimental,
exportação em **CSV**, relatório em **TXT** e roteiro de **pré-teste/pós-teste** (botões do próprio aplicativo).

## Instalação rápida

Requisitos: **Python 3.10 ou superior** com tkinter (testado apenas na versão 3.12; as versões mínimas dos pacotes são indicativas).

```bash
# 1) baixar o projeto (botão verde "Code" → "Download ZIP") e abrir a pasta no terminal
# 2) (opcional, recomendado) ambiente virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux / macOS

# 3) instalar as dependências
pip install -r requirements.txt

# 4) conferir o ambiente
python verificar_instalacao.py

# 5) abrir um laboratório
python 01_mru_mruv.py
```

Instruções detalhadas por sistema operacional: [INSTALACAO.md](INSTALACAO.md).

## Dependências

| Pacote | Uso | Versão mínima indicada |
|---|---|---|
| tkinter | interface gráfica (biblioteca padrão do Python) | — |
| numpy | cálculo numérico | 1.24 |
| matplotlib | gráficos e desenho das cenas | 3.7 |
| scipy | ajuste de curva (somente módulo 1) | 1.10 |

Bibliotecas padrão usadas: `csv`, `math`, `time`, `datetime`, `decimal`, `random`.
Nenhum módulo usa navegador, servidor local ou conexão de rede.

## Estrutura do repositório

Os arquivos estão na pasta principal do projeto. Cada módulo `.py` possui
um roteiro `.md` com o mesmo nome. A pasta principal também contém
`INSTALACAO.md`, `requirements.txt`, `verificar_instalacao.py`,
`CHANGELOG.md`, `CITATION.cff` e `LICENSE`.

## Verificação realizada

Em 25/11/2026, o comando `python verificar_instalacao.py` verificou as
bibliotecas e compilou os seis módulos em ambiente Linux com Python 3.12.14,
NumPy 2.3.5, Matplotlib 3.10.8, SciPy 1.17.0 e Tkinter 9.0.

Esse procedimento confere a importação das bibliotecas e a sintaxe dos módulos.
A verificação do funcionamento dos controles, dos gráficos e dos resultados
físicos exige executar as atividades de cada roteiro.

## Como citar

Veja [CITATION.cff](CITATION.cff) (o GitHub mostra a opção "Cite this repository").

## Licença

Distribuído sob a licença MIT — veja o arquivo [LICENSE](LICENSE).
