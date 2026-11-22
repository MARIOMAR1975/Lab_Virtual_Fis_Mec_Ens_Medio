# -*- coding: utf-8 -*-
"""Laboratório virtual profissional para o estudo da queda livre.

A interface combina uma cena experimental panorâmica, gráficos em tempo real,
coleta contínua/discreta/manual, ajuste de h0 = A·t², tabela de ensaios e
exportações em formatos adequados ao uso didático.

Modelo físico ideal, sem resistência do ar:
    h(t) = h0 - (1/2) g t²
    v(t) = g t
    t_queda = sqrt(2 h0 / g)

Requisitos:
    Python 3.x, tkinter, numpy, matplotlib

Execução:
    python 02_queda_livre.py
"""

import csv
import math
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch, Arc
from matplotlib.ticker import AutoMinorLocator
import matplotlib.gridspec as gridspec


# Identidade da aplicação e paleta de alto contraste.
NOME_APLICATIVO = "Laboratório Virtual — Queda Livre"
VERSAO_APLICATIVO = "2.1"
AUTOR = "Mario Omar Calla Salcedo"

COR_FUNDO = "#181426"
COR_PAINEL = "#232036"
COR_GRUPO = "#302b46"
COR_GRUPO_BORDA = "#64748b"
COR_TEXTO = "#f8fafc"
COR_TEXTO_SUAVE = "#cbd5e1"
COR_CARD = "#f8fafc"
COR_CENA = "#ecfeff"
COR_GRAFICO = "#ffffff"
COR_GRADE = "#cbd5e1"
COR_CIANO = "#06b6d4"
COR_AZUL = "#0ea5e9"
COR_VERDE = "#22c55e"
COR_LARANJA = "#f97316"
COR_VERMELHO = "#f43f5e"
COR_MAGENTA = "#d946ef"
COR_ROXO = "#8b5cf6"
COR_AMARELO = "#facc15"

DT_MIN = 0.001
DT_MAX = 0.5
RITMO_MIN = 0.01
RITMO_MAX = 16.0
INTERVALO_MIN = 0.001
MAX_DADOS = 10000
INTERVALO_GRAFICO = 0.12
INTERVALO_TABELA = 0.25


# =============================================================================
# FUNÇÕES MATEMÁTICAS E FORMATAÇÃO
# =============================================================================

def arredondar_fisico(valor, casas=9):
    """Evita pequenas oscilações numéricas de ponto flutuante em tabelas."""
    try:
        return round(float(valor), int(casas))
    except (TypeError, ValueError, OverflowError):
        return valor


def formato_numero(valor, casas=3):
    """Converte número para texto com vírgula decimal e arredondamento decimal."""
    try:
        quantizador = Decimal("1").scaleb(-int(casas))
        numero = Decimal(str(float(valor))).quantize(quantizador, rounding=ROUND_HALF_UP)
        return f"{numero:.{int(casas)}f}".replace(".", ",")
    except (TypeError, ValueError, ArithmeticError):
        return str(valor)


def limitar(valor, minimo, maximo):
    return max(minimo, min(maximo, valor))


def converter_numero(valor):
    """Aceita ponto ou vírgula decimal e rejeita valores não finitos."""
    texto = str(valor).strip().replace(" ", "").replace(",", ".")
    numero = float(texto)
    if not math.isfinite(numero):
        raise ValueError("O valor deve ser um número finito.")
    return numero


def modelo_altura(h0, g, t):
    """Altura instantânea acima da mesa: h(t) = h0 - 0,5*g*t²."""
    return h0 - 0.5 * g * t * t


def modelo_velocidade(g, t):
    """Velocidade vertical para baixo: v(t) = g*t."""
    return g * t


def tempo_queda_teorico(h0, g):
    """Tempo físico de queda a partir do repouso."""
    if h0 <= 0 or g <= 0:
        return 0.0
    return math.sqrt(2.0 * h0 / g)


# =============================================================================
# CLASSE PRINCIPAL DA APLICAÇÃO
# =============================================================================

class LaboratorioQuedaLivre:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{NOME_APLICATIVO} | v{VERSAO_APLICATIVO}")
        self.root.geometry("1366x720")
        self.root.minsize(1100, 650)

        # Estado da simulação
        self.rodando = False
        self.t = 0.0
        self.h = 10.0
        self.v = 0.0
        self.dados_serie = []
        self.ensaios = []
        self.indice_serie = 0
        self.indice_ensaios = 0
        self.limite_atingido = False
        self.after_id = None
        self.proximo_t_discreto = 0.0
        self.ajuste_resultado = None
        self._suprimir_eventos = False
        self._ultimo_redesenho_grafico = 0.0
        self._ultima_atualizacao_tabela = 0.0

        # Ambientes gravitacionais
        self.corpos = {
            "Terra": (9.81, "Referência padrão para experimentos escolares."),
            "Lua": (1.62, "Gravidade lunar: queda mais lenta."),
            "Mercúrio": (3.70, "Gravidade menor que a terrestre."),
            "Vênus": (8.87, "Gravidade próxima à terrestre."),
            "Marte": (3.71, "Gravidade marciana: queda mais lenta."),
            "Júpiter": (24.79, "Gravidade muito intensa."),
            "Saturno": (10.44, "Gravidade semelhante à terrestre."),
            "Urano": (8.69, "Gravidade um pouco menor que a terrestre."),
            "Netuno": (11.15, "Gravidade um pouco maior que a terrestre."),
            "Personalizado": (9.81, "Use o campo g para definir uma gravidade própria."),
        }

        # Variáveis Tkinter
        self.var_h0 = tk.StringVar(value="10,00")
        self.var_corpo = tk.StringVar(value="Terra")
        self.var_g = tk.StringVar(value="9,81")
        self.var_tmax = tk.StringVar(value="5,00")
        self.var_dt = tk.StringVar(value="0,05")
        self.var_ritmo = tk.StringVar(value="1,00")
        self.var_grafico = tk.StringVar(value="Todos")
        self.var_ajuste = tk.BooleanVar(value=False)
        self.var_registro = tk.StringVar(value="Contínua")
        self.var_intervalo_discreto = tk.StringVar(value="0,10")
        self.var_erro_experimental = tk.BooleanVar(value=False)
        self.var_sigma_t = tk.StringVar(value="0,010")

        # Tabela lateral no mesmo espírito do MRU/MRUV: seletor de grandeza.
        self.opcoes_tipo_tabela = [
            "Altura inicial × tempo de queda",
            "Altura instantânea × tempo",
            "Velocidade × tempo",
            "Tabela completa: t, h, v, g",
            "Dados com erro experimental",
        ]
        self.var_tipo_tabela = tk.StringVar(value="Tabela completa: t, h, v, g")
        self.var_descricao_tabela = tk.StringVar(value="Tabela ativa: t, h, v e g da queda atual.")
        self.mapa_colunas_tabela = {
            "Ensaio": {"chave": "n", "titulo": "#", "csv": "ensaio", "casas": 0, "largura": 35},
            "Amostra": {"chave": "amostra", "titulo": "#", "csv": "amostra", "casas": 0, "largura": 35},
            "Tempo": {"chave": "t", "titulo": "t", "csv": "tempo_s", "casas": 3, "largura": 58},
            "Altura": {"chave": "h", "titulo": "h", "csv": "altura_m", "casas": 3, "largura": 64},
            "Altura inicial": {"chave": "h0", "titulo": "h₀", "csv": "altura_inicial_m", "casas": 3, "largura": 70},
            "Tempo de queda": {"chave": "tq", "titulo": "tq", "csv": "tempo_queda_s", "casas": 4, "largura": 72},
            "Tempo experimental": {"chave": "t_exp", "titulo": "tₑ", "csv": "tempo_experimental_s", "casas": 4, "largura": 72},
            "Velocidade": {"chave": "v", "titulo": "v", "csv": "velocidade_m_s", "casas": 3, "largura": 68},
            "Gravidade": {"chave": "g", "titulo": "g", "csv": "gravidade_m_s2", "casas": 3, "largura": 62},
            "Erro absoluto": {"chave": "erro_t", "titulo": "Δt", "csv": "erro_tempo_s", "casas": 4, "largura": 58},
            "Erro percentual": {"chave": "erro_pct", "titulo": "%", "csv": "erro_percentual", "casas": 2, "largura": 48},
        }

        self.var_status = tk.StringVar(value="Pronto para iniciar.")
        self.var_equacoes = tk.StringVar(value="")
        self.var_interpretacao = tk.StringVar(value="")

        self.configurar_estilo()
        self.criar_interface()
        self.configurar_eventos()
        self.reiniciar_simulacao(limpar_tabela=False)

    # -------------------------------------------------------------------------
    # ESTILO VISUAL
    # -------------------------------------------------------------------------
    def configurar_estilo(self):
        self.root.configure(bg=COR_FUNDO)
        estilo = ttk.Style()
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass

        estilo.configure("TFrame", background=COR_FUNDO)
        estilo.configure("Panel.TFrame", background=COR_PAINEL, relief="flat")
        estilo.configure("Card.TFrame", background=COR_CARD, relief="flat")
        estilo.configure("TLabel", background=COR_PAINEL, foreground=COR_TEXTO, font=("Segoe UI", 8))
        estilo.configure("Title.TLabel", background=COR_FUNDO, foreground=COR_TEXTO, font=("Segoe UI Semibold", 14))
        estilo.configure("SubTitle.TLabel", background=COR_FUNDO, foreground=COR_TEXTO_SUAVE, font=("Segoe UI", 8))
        estilo.configure("TButton", font=("Segoe UI Semibold", 7), padding=(5, 3), borderwidth=0)
        estilo.map("TButton", background=[("active", "#475569")], foreground=[("disabled", "#94a3b8")])

        botoes = {
            "Accent.TButton": (COR_AZUL, "#0284c7"),
            "Success.TButton": (COR_VERDE, "#16a34a"),
            "Warning.TButton": (COR_LARANJA, "#ea580c"),
            "Danger.TButton": (COR_VERMELHO, "#e11d48"),
        }
        for nome, (normal, ativo) in botoes.items():
            estilo.configure(nome, foreground="#ffffff", background=normal, font=("Segoe UI Semibold", 7), padding=(5, 3))
            estilo.map(nome, background=[("pressed", ativo), ("active", ativo)], foreground=[("disabled", "#e2e8f0")])

        estilo.configure(
            "TEntry", fieldbackground="#151225", foreground=COR_TEXTO,
            insertcolor=COR_AMARELO, bordercolor="#64748b", lightcolor="#64748b", darkcolor="#64748b"
        )
        estilo.configure(
            "TCombobox", fieldbackground="#151225", background="#151225", foreground=COR_TEXTO,
            arrowcolor=COR_CIANO, bordercolor="#64748b", lightcolor="#64748b", darkcolor="#64748b"
        )
        estilo.map(
            "TCombobox", fieldbackground=[("readonly", "#151225")],
            foreground=[("readonly", COR_TEXTO)], selectbackground=[("readonly", COR_ROXO)]
        )
        estilo.configure("Treeview", font=("Segoe UI", 7), rowheight=20, background="#ffffff", fieldbackground="#ffffff", foreground="#172033")
        estilo.map("Treeview", background=[("selected", COR_AZUL)], foreground=[("selected", "#ffffff")])
        estilo.configure("Treeview.Heading", font=("Segoe UI Semibold", 7), background="#cffafe", foreground="#164e63", relief="flat")
        estilo.map("Treeview.Heading", background=[("active", "#a5f3fc")])

    # -------------------------------------------------------------------------
    # CRIAÇÃO DA INTERFACE
    # -------------------------------------------------------------------------
    def criar_interface(self):
        self.criar_cabecalho()
        self.criar_corpo()

    def criar_cabecalho(self):
        cabecalho = ttk.Frame(self.root, style="TFrame", padding=(8, 5, 8, 2))
        cabecalho.grid(row=0, column=0, sticky="ew")
        cabecalho.columnconfigure(0, weight=1)

        titulo = ttk.Label(
            cabecalho,
            text=NOME_APLICATIVO,
            style="Title.TLabel"
        )
        titulo.grid(row=0, column=0, sticky="w")

        subtitulo = ttk.Label(
            cabecalho,
            text="Movimento vertical, gravidade e análise experimental do tempo de queda",
            style="SubTitle.TLabel"
        )
        subtitulo.grid(row=1, column=0, sticky="w", pady=(1, 0))

        selo = tk.Label(
            cabecalho,
            text=f"OFFLINE  •  v{VERSAO_APLICATIVO}",
            bg="#0e7490",
            fg="#ecfeff",
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=3,
            relief="flat"
        )
        selo.grid(row=0, column=1, rowspan=2, sticky="e", padx=(10, 0))

    def criar_corpo(self):
        corpo = ttk.Frame(self.root, style="TFrame", padding=(5, 3, 5, 5))
        corpo.grid(row=1, column=0, sticky="nsew")
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)

        corpo.columnconfigure(0, minsize=235, weight=0)
        corpo.columnconfigure(1, weight=1)
        corpo.rowconfigure(0, weight=1)

        self.criar_painel_controle(corpo)
        self.criar_area_trabalho(corpo)

    def criar_painel_controle(self, parent):
        painel = tk.Frame(parent, bg=COR_PAINEL, bd=0, highlightthickness=1, highlightbackground=COR_CIANO)
        painel.grid(row=0, column=0, sticky="nsw", padx=(0, 5))
        painel.grid_propagate(False)
        painel.configure(width=235)
        painel.columnconfigure(0, weight=1)

        titulo = tk.Label(
            painel,
            text="Painel de comando",
            bg=COR_PAINEL,
            fg=COR_TEXTO,
            font=("Segoe UI", 10, "bold")
        )
        titulo.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 2))

        self.criar_grupo_modelo(painel, 1)
        self.criar_grupo_visualizacao(painel, 2)
        self.criar_grupo_botoes(painel, 3)
        self.criar_grupo_presets(painel, 4)
        self.criar_grupo_didatico(painel, 5)

    def criar_grupo(self, parent, row, titulo):
        acentos = {
            "Modelo físico": COR_CIANO,
            "Visualização e coleta": COR_ROXO,
            "Controle da simulação": COR_VERDE,
            "Situações prontas": COR_LARANJA,
            "Modelo didático": COR_MAGENTA,
        }
        acento = acentos.get(titulo, COR_GRUPO_BORDA)
        grupo = tk.Frame(parent, bg=COR_GRUPO, bd=0, highlightthickness=1, highlightbackground=acento)
        grupo.grid(row=row, column=0, sticky="ew", padx=5, pady=2)
        for c in range(3):
            grupo.columnconfigure(c, weight=1)

        lbl = tk.Label(
            grupo,
            text=titulo.upper(),
            bg=COR_GRUPO,
            fg=acento,
            font=("Segoe UI", 7, "bold")
        )
        lbl.grid(row=0, column=0, columnspan=3, sticky="w", padx=5, pady=(4, 1))
        return grupo

    def criar_grupo_modelo(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Modelo físico")
        self.criar_label_combo(grupo, 1, "Ambiente", self.var_corpo, list(self.corpos.keys()))
        self.criar_linha_entradas(grupo, 2, "h₀ (m)", self.var_h0, "g (m/s²)", self.var_g)
        self.criar_linha_entradas(grupo, 3, "t janela (s)", self.var_tmax, "Δt (s)", self.var_dt)

    def criar_grupo_visualizacao(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Visualização e coleta")
        self.criar_label_combo(grupo, 1, "Gráficos", self.var_grafico, ["Todos", "h(t)", "v(t)", "h₀ × tqueda"])
        self.criar_label_combo(grupo, 2, "Ritmo", self.var_ritmo, [0.25, 0.5, 1.0, 2.0, 4.0])
        self.criar_label_combo(grupo, 3, "Tipo de coleta", self.var_registro, ["Contínua", "Discreta", "Manual"])
        self.criar_linha_entradas(grupo, 4, "Δt coleta (s)", self.var_intervalo_discreto, "σt erro (s)", self.var_sigma_t)

        chk_ajuste = tk.Checkbutton(
            grupo,
            text="Ajuste h₀(tq)",
            variable=self.var_ajuste,
            bg=COR_GRUPO,
            fg=COR_TEXTO,
            activebackground=COR_GRUPO,
            activeforeground="#ffffff",
            selectcolor="#151225",
            font=("Segoe UI", 7)
        )
        chk_ajuste.grid(row=5, column=0, sticky="w", padx=5, pady=(1, 4))

        chk_erro = tk.Checkbutton(
            grupo,
            text="Erro exp.",
            variable=self.var_erro_experimental,
            bg=COR_GRUPO,
            fg=COR_TEXTO,
            activebackground=COR_GRUPO,
            activeforeground="#ffffff",
            selectcolor="#151225",
            font=("Segoe UI", 7)
        )
        chk_erro.grid(row=5, column=1, columnspan=2, sticky="w", padx=5, pady=(1, 4))

    def criar_grupo_botoes(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Controle da simulação")

        self.btn_iniciar = ttk.Button(grupo, text="Iniciar", style="Success.TButton", command=self.iniciar)
        self.btn_pausar = ttk.Button(grupo, text="Pausar", style="Warning.TButton", command=self.pausar)
        self.btn_passo = ttk.Button(grupo, text="Passo", command=self.passo)
        self.btn_reset = ttk.Button(grupo, text="Resetar", style="Danger.TButton", command=lambda: self.reiniciar_simulacao(limpar_tabela=False))
        self.btn_registrar = ttk.Button(grupo, text="Reg. ponto", command=self.registrar_ponto_manual)
        self.btn_limpar = ttk.Button(grupo, text="Limpar", command=self.limpar_tabela)
        self.btn_csv = ttk.Button(grupo, text="CSV", command=self.exportar_csv)
        self.btn_relatorio = ttk.Button(grupo, text="Relatório", command=self.exportar_relatorio)
        self.btn_prepos = ttk.Button(grupo, text="Pré/Pós", command=self.exportar_roteiro_pre_pos_teste)

        botoes = [
            (self.btn_iniciar, 1, 0), (self.btn_pausar, 1, 1), (self.btn_passo, 1, 2),
            (self.btn_reset, 2, 0), (self.btn_registrar, 2, 1), (self.btn_limpar, 2, 2),
            (self.btn_csv, 3, 0), (self.btn_relatorio, 3, 1), (self.btn_prepos, 3, 2),
        ]
        for botao, r, c in botoes:
            botao.grid(row=r, column=c, sticky="ew", padx=2, pady=2)

        for c in range(3):
            grupo.columnconfigure(c, weight=1)

        lbl_status = tk.Label(
            grupo,
            textvariable=self.var_status,
            bg=COR_GRUPO,
            fg="#a5f3fc",
            font=("Segoe UI", 7),
            wraplength=205,
            justify="left"
        )
        lbl_status.grid(row=4, column=0, columnspan=3, sticky="ew", padx=5, pady=(1, 4))

    def criar_grupo_presets(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Situações prontas")
        b1 = ttk.Button(grupo, text="Baixa", command=lambda: self.aplicar_preset(1))
        b2 = ttk.Button(grupo, text="Média", command=lambda: self.aplicar_preset(2))
        b3 = ttk.Button(grupo, text="Alta", command=lambda: self.aplicar_preset(3))
        b1.grid(row=1, column=0, sticky="ew", padx=2, pady=2)
        b2.grid(row=1, column=1, sticky="ew", padx=2, pady=2)
        b3.grid(row=1, column=2, sticky="ew", padx=2, pady=2)
        grupo.columnconfigure(2, weight=1)
        grupo.columnconfigure(0, weight=1)
        grupo.columnconfigure(1, weight=1)

    def criar_grupo_didatico(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Modelo didático")
        lbl_equacoes = tk.Label(
            grupo,
            textvariable=self.var_equacoes,
            bg=COR_GRUPO,
            fg="#a5f3fc",
            font=("Segoe UI", 7),
            wraplength=210,
            justify="left"
        )
        lbl_equacoes.grid(row=1, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 3))
        lbl_interpretacao = tk.Label(
            grupo,
            textvariable=self.var_interpretacao,
            bg=COR_GRUPO,
            fg=COR_TEXTO_SUAVE,
            font=("Segoe UI", 7),
            wraplength=210,
            justify="left"
        )
        lbl_interpretacao.grid(row=2, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 7))

    def criar_label_combo(self, parent, row, texto, variavel, opcoes):
        lbl = tk.Label(parent, text=texto, bg=COR_GRUPO, fg=COR_TEXTO_SUAVE, font=("Segoe UI", 7))
        lbl.grid(row=row, column=0, sticky="w", padx=5, pady=(1, 0))
        combo = ttk.Combobox(parent, textvariable=variavel, values=opcoes, state="readonly", font=("Segoe UI", 7), width=9)
        combo.grid(row=row, column=1, columnspan=2, sticky="ew", padx=5, pady=(1, 0))
        combo.bind("<<ComboboxSelected>>", lambda event: self.configuracao_alterada())
        parent.columnconfigure(1, weight=1)
        return combo

    def criar_linha_entradas(self, parent, row, texto1, var1, texto2, var2):
        frame = tk.Frame(parent, bg=COR_GRUPO)
        frame.grid(row=row, column=0, columnspan=3, sticky="ew", padx=5, pady=1)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        f1 = tk.Frame(frame, bg=COR_GRUPO)
        f2 = tk.Frame(frame, bg=COR_GRUPO)
        f1.grid(row=0, column=0, sticky="ew", padx=(0, 3))
        f2.grid(row=0, column=1, sticky="ew", padx=(3, 0))
        f1.columnconfigure(0, weight=1)
        f2.columnconfigure(0, weight=1)

        tk.Label(f1, text=texto1, bg=COR_GRUPO, fg=COR_TEXTO_SUAVE, font=("Segoe UI", 7)).grid(row=0, column=0, sticky="w")
        e1 = ttk.Entry(f1, textvariable=var1, font=("Segoe UI", 7), width=6)
        e1.grid(row=1, column=0, sticky="ew")

        tk.Label(f2, text=texto2, bg=COR_GRUPO, fg=COR_TEXTO_SUAVE, font=("Segoe UI", 7)).grid(row=0, column=0, sticky="w")
        e2 = ttk.Entry(f2, textvariable=var2, font=("Segoe UI", 7), width=6)
        e2.grid(row=1, column=0, sticky="ew")

        e1.bind("<FocusOut>", lambda event: self.configuracao_alterada())
        e2.bind("<FocusOut>", lambda event: self.configuracao_alterada())

    def criar_area_trabalho(self, parent):
        area = tk.Frame(parent, bg=COR_FUNDO)
        area.grid(row=0, column=1, sticky="nsew")
        area.columnconfigure(0, weight=1)
        area.columnconfigure(1, weight=0, minsize=235)
        area.rowconfigure(0, weight=1)

        visual = tk.Frame(area, bg=COR_FUNDO)
        visual.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        visual.columnconfigure(0, weight=1)
        visual.rowconfigure(0, weight=12, minsize=0, uniform="visual_split")
        visual.rowconfigure(1, weight=13, minsize=0, uniform="visual_split")

        self.criar_cena(visual)
        self.criar_graficos(visual, row=1, column=0, padx=(0, 0))
        self.criar_tabela_e_leituras(area)

    def criar_cena(self, parent):
        card = tk.Frame(parent, bg=COR_CARD, bd=0, highlightthickness=1, highlightbackground=COR_CIANO)
        card.grid(row=0, column=0, sticky="nsew", pady=(0, 4))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=1)

        self.fig_cena = Figure(figsize=(8, 3.6), dpi=100, facecolor=COR_CENA)
        self.ax_cena = self.fig_cena.add_subplot(111)
        self.canvas_cena = FigureCanvasTkAgg(self.fig_cena, master=card)
        self.canvas_cena.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=4)

    def criar_graficos(self, parent, row=0, column=0, padx=(0, 8)):
        card = tk.Frame(parent, bg=COR_CARD, bd=0, highlightthickness=1, highlightbackground=COR_ROXO)
        card.grid(row=row, column=column, sticky="nsew", padx=padx)
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=0)
        card.rowconfigure(1, weight=1)

        topo = tk.Frame(card, bg="#f8fafc")
        topo.grid(row=0, column=0, sticky="ew", padx=6, pady=(3, 0))
        topo.columnconfigure(0, weight=1)

        tk.Label(
            topo,
            text="Gráficos em tempo real",
            bg="#f8fafc",
            fg="#0f172a",
            font=("Segoe UI", 9, "bold")
        ).grid(row=0, column=0, sticky="w")

        self.lbl_nota_grafico = tk.Label(
            topo,
            text="Mostrando h(t), v(t) e h₀ × tq.",
            bg="#f8fafc",
            fg="#475569",
            font=("Segoe UI", 7)
        )
        self.lbl_nota_grafico.grid(row=0, column=1, sticky="e")

        self.fig_graficos = Figure(figsize=(7.2, 3.8), dpi=100, facecolor=COR_GRAFICO)
        self.canvas_graficos = FigureCanvasTkAgg(self.fig_graficos, master=card)
        self.canvas_graficos.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=5, pady=(2, 5))

    def criar_tabela_e_leituras(self, parent):
        card = tk.Frame(parent, bg=COR_CARD, bd=0, highlightthickness=1, highlightbackground=COR_LARANJA, width=235)
        card.grid(row=0, column=1, sticky="nsew")
        card.grid_propagate(False)
        card.columnconfigure(0, weight=1)
        card.rowconfigure(2, weight=1)

        topo = tk.Frame(card, bg="#f8fafc")
        topo.grid(row=0, column=0, sticky="ew", padx=8, pady=(7, 4))
        topo.columnconfigure(0, weight=1)

        tk.Label(
            topo,
            text="Tabela experimental",
            bg="#f8fafc",
            fg="#0f172a",
            font=("Segoe UI", 10, "bold")
        ).grid(row=0, column=0, sticky="w")

        tk.Label(
            topo,
            text="compacta",
            bg="#f8fafc",
            fg="#475569",
            font=("Segoe UI", 8, "bold")
        ).grid(row=0, column=1, sticky="e")

        painel_tabela = tk.Frame(card, bg="#e0f2fe", bd=0, highlightthickness=1, highlightbackground="#bae6fd")
        painel_tabela.grid(row=1, column=0, sticky="ew", padx=7, pady=(0, 6))
        painel_tabela.columnconfigure(1, weight=1)

        tk.Label(
            painel_tabela,
            text="Grandeza",
            bg="#e0f2fe",
            fg="#0f172a",
            font=("Segoe UI", 8, "bold")
        ).grid(row=0, column=0, sticky="w", padx=8, pady=(7, 3))

        combo_tipo = ttk.Combobox(
            painel_tabela,
            textvariable=self.var_tipo_tabela,
            values=self.opcoes_tipo_tabela,
            state="readonly",
            width=17,
            font=("Segoe UI", 8)
        )
        combo_tipo.grid(row=0, column=1, sticky="ew", padx=8, pady=(7, 3))
        combo_tipo.bind("<<ComboboxSelected>>", lambda event: self.aplicar_configuracao_tabela())

        tk.Label(
            painel_tabela,
            textvariable=self.var_descricao_tabela,
            bg="#e0f2fe",
            fg="#334155",
            font=("Segoe UI", 8),
            justify="left",
            wraplength=205
        ).grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(2, 7))

        frame_tabela = tk.Frame(card, bg="#f8fafc")
        frame_tabela.grid(row=2, column=0, sticky="nsew", padx=7, pady=(0, 7))
        frame_tabela.columnconfigure(0, weight=1)
        frame_tabela.rowconfigure(0, weight=1)

        self.tabela = ttk.Treeview(frame_tabela, columns=(), show="headings", height=28)
        barra_y = ttk.Scrollbar(frame_tabela, orient="vertical", command=self.tabela.yview)
        barra_x = ttk.Scrollbar(frame_tabela, orient="horizontal", command=self.tabela.xview)
        self.tabela.configure(yscrollcommand=barra_y.set, xscrollcommand=barra_x.set)
        self.tabela.grid(row=0, column=0, sticky="nsew")
        barra_y.grid(row=0, column=1, sticky="ns")
        barra_x.grid(row=1, column=0, sticky="ew")
        self.tabela.tag_configure("par", background="#ecfeff")
        self.tabela.tag_configure("impar", background="#ffffff")

        self.aplicar_configuracao_tabela()

    def obter_colunas_tabela(self):
        tipo = self.var_tipo_tabela.get()
        if tipo == "Altura instantânea × tempo":
            return ["Amostra", "Tempo", "Altura"]
        if tipo == "Velocidade × tempo":
            return ["Amostra", "Tempo", "Velocidade"]
        if tipo == "Tabela completa: t, h, v, g":
            return ["Amostra", "Tempo", "Altura", "Velocidade", "Gravidade"]
        if tipo == "Dados com erro experimental":
            return ["Ensaio", "Altura inicial", "Tempo de queda", "Tempo experimental", "Erro absoluto", "Erro percentual"]
        return ["Ensaio", "Altura inicial", "Tempo de queda"]

    def aplicar_configuracao_tabela(self):
        """Configura as colunas do Treeview e força a atualização dos valores.

        A ordem é importante: primeiro definimos as colunas e os cabeçalhos;
        depois apagamos e inserimos as linhas. Isso evita que a tabela fique
        visualmente vazia em algumas versões do Tkinter no Windows.
        """
        if not hasattr(self, "tabela"):
            return

        selecionadas = self.obter_colunas_tabela()
        colunas = [self.mapa_colunas_tabela[g]["chave"] for g in selecionadas]

        self.tabela.configure(columns=colunas, displaycolumns=colunas)

        for grandeza in selecionadas:
            meta = self.mapa_colunas_tabela[grandeza]
            chave = meta["chave"]
            self.tabela.heading(chave, text=meta["titulo"])
            self.tabela.column(chave, width=meta["largura"], anchor="center", stretch=False)

        tipo = self.var_tipo_tabela.get()
        if tipo == "Altura instantânea × tempo":
            self.var_descricao_tabela.set("Tabela ativa: h(t) da queda em andamento.")
        elif tipo == "Velocidade × tempo":
            self.var_descricao_tabela.set("Tabela ativa: v(t) para baixo, com g constante.")
        elif tipo == "Tabela completa: t, h, v, g":
            self.var_descricao_tabela.set("Tabela ativa: t, h, v e g da queda atual. Mostra valores desde t = 0.")
        elif tipo == "Dados com erro experimental":
            self.var_descricao_tabela.set("Tabela ativa: tq teórico, tq experimental e erro. O ensaio aparece ao finalizar a queda.")
        else:
            self.var_descricao_tabela.set("Tabela ativa: h₀ em função do tempo total de queda. O ensaio aparece ao finalizar a queda.")

        self.atualizar_tabela()

    # -------------------------------------------------------------------------
    # EVENTOS E VALIDAÇÃO
    # -------------------------------------------------------------------------
    def configurar_eventos(self):
        variaveis = [
            self.var_h0, self.var_corpo, self.var_g, self.var_tmax, self.var_dt,
            self.var_ritmo, self.var_grafico, self.var_registro, self.var_tipo_tabela,
            self.var_intervalo_discreto, self.var_sigma_t, self.var_erro_experimental,
            self.var_ajuste,
        ]
        for var in variaveis:
            var.trace_add("write", lambda *args: self.configuracao_alterada(suave=True))

        self.root.bind("<Return>", lambda event: self.iniciar())
        self.root.bind("<space>", lambda event: self.pausar())
        self.root.protocol("WM_DELETE_WINDOW", self.fechar)

    def configuracao_alterada(self, suave=False):
        if self._suprimir_eventos:
            return

        # Selecionar um corpo atualiza g automaticamente, exceto no modo personalizado.
        corpo = self.var_corpo.get()
        if corpo in self.corpos and corpo != "Personalizado":
            g_corpo = self.corpos[corpo][0]
            try:
                g_atual = converter_numero(self.var_g.get())
            except (TypeError, ValueError):
                g_atual = None
            if g_atual is None or abs(g_atual - g_corpo) > 1e-9:
                self._suprimir_eventos = True
                self.var_g.set(formato_numero(g_corpo, 2))
                self._suprimir_eventos = False

        if not self.validar_parametros(mostrar_erro=not suave):
            self.var_equacoes.set("Complete os campos numéricos para atualizar a experiência.")
            return

        if self.t == 0 and not self.rodando:
            self.preparar_estado_inicial_sem_limpar_ensaios()

        self.atualizar_tudo()

    def validar_parametros(self, mostrar_erro=True):
        try:
            h0 = converter_numero(self.var_h0.get())
            g = converter_numero(self.var_g.get())
            tmax = converter_numero(self.var_tmax.get())
            dt = converter_numero(self.var_dt.get())
            ritmo = converter_numero(self.var_ritmo.get())
            intervalo_discreto = converter_numero(self.var_intervalo_discreto.get())
            sigma_t = converter_numero(self.var_sigma_t.get())
        except (TypeError, ValueError):
            if mostrar_erro:
                messagebox.showerror("Erro nos parâmetros", "Verifique se todos os campos numéricos foram preenchidos corretamente.")
            return False

        mensagens = []
        if h0 <= 0:
            mensagens.append("A altura inicial h₀ deve ser maior que zero.")
        if g <= 0:
            mensagens.append("A gravidade g deve ser maior que zero.")
        if tmax <= 0:
            mensagens.append("A janela de tempo deve ser maior que zero.")
        if dt < DT_MIN:
            mensagens.append(f"O passo Δt deve ser maior ou igual a {formato_numero(DT_MIN, 3)} s.")
        if dt > DT_MAX:
            mensagens.append("Para boa visualização, use Δt menor ou igual a 0,5 s.")
        if not RITMO_MIN <= ritmo <= RITMO_MAX:
            mensagens.append("O ritmo deve estar entre 0,01× e 16×.")
        if intervalo_discreto < INTERVALO_MIN:
            mensagens.append("O intervalo de coleta discreta deve ser maior ou igual a 0,001 s.")
        if sigma_t < 0:
            mensagens.append("O erro experimental σt não pode ser negativo.")

        if mensagens:
            if mostrar_erro:
                messagebox.showerror("Parâmetros inválidos", "\n".join(mensagens))
            return False
        return True

    def obter_config(self):
        h0 = max(0.001, converter_numero(self.var_h0.get()))
        g = max(0.001, converter_numero(self.var_g.get()))
        tmax = max(0.1, converter_numero(self.var_tmax.get()))
        dt = limitar(converter_numero(self.var_dt.get()), DT_MIN, DT_MAX)
        ritmo = limitar(converter_numero(self.var_ritmo.get()), RITMO_MIN, RITMO_MAX)
        intervalo = max(INTERVALO_MIN, converter_numero(self.var_intervalo_discreto.get()))
        sigma_t = max(0.0, converter_numero(self.var_sigma_t.get()))
        return h0, g, tmax, dt, ritmo, intervalo, sigma_t

    # -------------------------------------------------------------------------
    # CONTROLE DA SIMULAÇÃO
    # -------------------------------------------------------------------------
    def preparar_estado_inicial_sem_limpar_ensaios(self):
        try:
            h0, g, *_ = self.obter_config()
        except (TypeError, ValueError):
            h0, g = 10.0, 9.81
        self.t = 0.0
        self.h = h0
        self.v = 0.0
        self.limite_atingido = False
        self.dados_serie = []
        self.indice_serie = 0
        self.proximo_t_discreto = 0.0
        self.registrar_ponto(forcar=True)

    def iniciar(self):
        if not self.validar_parametros(mostrar_erro=True):
            return
        self.cancelar_after()
        self.preparar_estado_inicial_sem_limpar_ensaios()
        self.rodando = True
        self.var_status.set("Simulação em andamento: a esfera foi solta a partir do repouso.")
        self.agendar_animacao()
        self.atualizar_tudo()

    def pausar(self):
        if self.rodando:
            self.rodando = False
            self.var_status.set("Simulação pausada. Use Iniciar para reiniciar ou Passo para avançar manualmente.")
        else:
            if not self.limite_atingido:
                self.rodando = True
                self.var_status.set("Simulação retomada.")
                self.agendar_animacao()
        self.atualizar_tudo()

    def passo(self):
        if not self.validar_parametros(mostrar_erro=True):
            return
        if self.limite_atingido:
            self.var_status.set("A esfera já chegou à mesa. Use Resetar ou mude a altura inicial para novo ensaio.")
            return
        self.rodando = False
        self.avancar(forcar_registro=True)
        self.atualizar_tudo()

    def agendar_animacao(self):
        self.cancelar_after()
        self.after_id = self.root.after(30, self.loop_animacao)

    def cancelar_after(self):
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except tk.TclError:
                pass
            self.after_id = None

    def loop_animacao(self):
        self.after_id = None
        if self.rodando:
            self.avancar()
            self.atualizar_tudo(animacao=True)
            if self.rodando:
                self.agendar_animacao()

    def avancar(self, forcar_registro=False):
        h0, g, _tmax, dt, ritmo, _intervalo, _sigma_t = self.obter_config()
        tq = tempo_queda_teorico(h0, g)

        incremento = dt * ritmo
        novo_t = self.t + incremento
        if novo_t >= tq:
            novo_t = tq
            self.limite_atingido = True
            self.rodando = False

        self.t = arredondar_fisico(novo_t)
        self.h = max(0.0, arredondar_fisico(modelo_altura(h0, g, self.t)))
        self.v = arredondar_fisico(modelo_velocidade(g, self.t))

        self.registrar_ponto(forcar=forcar_registro or self.limite_atingido)

        if self.limite_atingido:
            self.registrar_ensaio_final()
            self.var_status.set(
                f"Queda concluída: h₀ = {formato_numero(h0, 3)} m; tq = {formato_numero(tq, 4)} s."
            )

    def reiniciar_simulacao(self, limpar_tabela=False):
        self.cancelar_after()
        self.rodando = False
        if limpar_tabela:
            self.ensaios = []
            self.indice_ensaios = 0
            self.ajuste_resultado = None
        self.preparar_estado_inicial_sem_limpar_ensaios()
        self.var_status.set("Simulação reiniciada. A tabela de ensaios foi preservada." if not limpar_tabela else "Simulação reiniciada e tabela limpa.")
        self.atualizar_tudo()

    def limpar_tabela(self):
        self.ensaios = []
        self.indice_ensaios = 0
        self.ajuste_resultado = None
        self.var_status.set("Tabela experimental limpa. Execute novas quedas para construir o gráfico h₀ × tq.")
        self.atualizar_tudo()

    def registrar_ponto_manual(self):
        self.registrar_ponto(forcar=True)
        self.var_status.set("Ponto manual registrado na tabela da queda atual.")
        self.atualizar_tudo()

    def registrar_ponto(self, forcar=False):
        h0, g, *_ = self.obter_config()
        modo = self.var_registro.get()

        deve_registrar = bool(forcar)
        if not deve_registrar and modo == "Contínua":
            deve_registrar = True
        elif not deve_registrar and modo == "Discreta":
            intervalo = max(INTERVALO_MIN, converter_numero(self.var_intervalo_discreto.get()))
            if self.t + 1e-12 >= self.proximo_t_discreto:
                deve_registrar = True
                while self.proximo_t_discreto <= self.t + 1e-12:
                    self.proximo_t_discreto += intervalo
        elif modo == "Manual" and not forcar:
            deve_registrar = False

        if not deve_registrar:
            return

        # Evita duplicar o mesmo instante em registros forçados consecutivos.
        if self.dados_serie and abs(self.dados_serie[-1]["t"] - self.t) < 1e-12:
            self.dados_serie[-1].update({"h": self.h, "v": self.v, "g": g, "h0": h0})
            return

        self.indice_serie += 1
        self.dados_serie.append({
            "amostra": self.indice_serie,
            "t": float(self.t),
            "h": float(self.h),
            "v": float(self.v),
            "g": float(g),
            "h0": float(h0),
        })
        if len(self.dados_serie) > MAX_DADOS:
            del self.dados_serie[:-MAX_DADOS]

    def registrar_ensaio_final(self):
        h0, g, *_rest, sigma_t = self.obter_config()
        tq = tempo_queda_teorico(h0, g)

        # Não duplica se o último ensaio tem mesma altura, g e tempo dentro da tolerância.
        if self.ensaios:
            ultimo = self.ensaios[-1]
            if abs(ultimo["h0"] - h0) < 1e-9 and abs(ultimo["g"] - g) < 1e-9 and abs(ultimo["tq"] - tq) < 1e-9:
                return

        if self.var_erro_experimental.get() and sigma_t > 0:
            t_exp = max(0.0, tq + float(np.random.normal(0.0, sigma_t)))
        else:
            t_exp = tq
        erro_t = abs(t_exp - tq)
        erro_pct = (erro_t / tq * 100.0) if tq > 0 else 0.0

        self.indice_ensaios += 1
        self.ensaios.append({
            "n": self.indice_ensaios,
            "h0": float(h0),
            "tq": float(tq),
            "t_exp": float(t_exp),
            "erro_t": float(erro_t),
            "erro_pct": float(erro_pct),
            "g": float(g),
            "corpo": self.var_corpo.get(),
        })
        self.ajuste_resultado = self.calcular_ajuste_altura_tempo()

    def aplicar_preset(self, codigo):
        self.cancelar_after()
        self.rodando = False
        self._suprimir_eventos = True
        if codigo == 1:
            self.var_corpo.set("Terra")
            self.var_g.set("9,81")
            self.var_h0.set("2,00")
            self.var_tmax.set("2,00")
            self.var_dt.set("0,02")
            mensagem = "Preset aplicado: queda de baixa altura em ambiente terrestre."
        elif codigo == 2:
            self.var_corpo.set("Terra")
            self.var_g.set("9,81")
            self.var_h0.set("10,00")
            self.var_tmax.set("4,00")
            self.var_dt.set("0,05")
            mensagem = "Preset aplicado: queda média para observar a curvatura de h(t)."
        else:
            self.var_corpo.set("Lua")
            self.var_g.set("1,62")
            self.var_h0.set("10,00")
            self.var_tmax.set("6,00")
            self.var_dt.set("0,05")
            mensagem = "Preset aplicado: queda na Lua para comparar o efeito de g menor."
        self._suprimir_eventos = False
        self.preparar_estado_inicial_sem_limpar_ensaios()
        self.var_status.set(mensagem)
        self.atualizar_tudo()

    # -------------------------------------------------------------------------
    # ATUALIZAÇÃO VISUAL
    # -------------------------------------------------------------------------
    def atualizar_tudo(self, animacao=False):
        if not self.validar_parametros(mostrar_erro=False):
            return
        self.atualizar_modelo_didatico()
        self.desenhar_cena()
        agora = time.monotonic()
        atualizar_grafico = not animacao or self.limite_atingido or agora - self._ultimo_redesenho_grafico >= INTERVALO_GRAFICO
        atualizar_tabela = not animacao or self.limite_atingido or agora - self._ultima_atualizacao_tabela >= INTERVALO_TABELA
        if atualizar_grafico:
            self.desenhar_graficos()
            self._ultimo_redesenho_grafico = agora
        if atualizar_tabela:
            self.atualizar_tabela()
            self._ultima_atualizacao_tabela = agora

    def atualizar_modelo_didatico(self):
        try:
            h0, g, *_ = self.obter_config()
            tq = tempo_queda_teorico(h0, g)
            corpo = self.var_corpo.get()
            info = self.corpos.get(corpo, (g, ""))[1]
            self.var_equacoes.set(
                f"h(t)=h₀−(1/2)gt² | v(t)=gt | tq=√(2h₀/g) | tq={formato_numero(tq, 4)} s"
            )
            self.var_interpretacao.set(info)
        except (TypeError, ValueError):
            self.var_equacoes.set("Aguardando parâmetros válidos.")
            self.var_interpretacao.set("")

    def desenhar_cena(self):
        self.ax_cena.clear()
        ax = self.ax_cena
        ax.set_xlim(0, 16)
        ax.set_ylim(0, 9)
        ax.axis("off")

        h0, g, *_ = self.obter_config()
        tq = tempo_queda_teorico(h0, g)
        h_atual = limitar(self.h, 0.0, h0)
        y_base = 1.45
        y_topo = 7.45
        y_bola = y_base + (h_atual / h0) * (y_topo - y_base) if h0 > 0 else y_base
        x_bola = 7.2

        # Ambiente experimental em formato panorâmico.
        ax.set_facecolor(COR_CENA)
        ax.add_patch(Rectangle((0, 0), 16, 9, facecolor=COR_CENA, edgecolor="#67e8f9", linewidth=1.0))
        for x in np.linspace(0.8, 15.2, 19):
            ax.plot([x, x], [0.35, 8.25], color="#cffafe", lw=0.55, zorder=0)
        for y in np.linspace(0.55, 8.05, 11):
            ax.plot([0.35, 15.65], [y, y], color="#cffafe", lw=0.55, zorder=0)

        # Bancada e suporte do sensor.
        ax.add_patch(Rectangle((0.65, 0.72), 14.7, 0.56, facecolor="#0f766e", edgecolor="#134e4a", lw=1.2, zorder=2))
        ax.add_patch(Rectangle((1.05, 0.18), 0.30, 0.54, facecolor="#115e59", edgecolor="#134e4a", zorder=1))
        ax.add_patch(Rectangle((14.65, 0.18), 0.30, 0.54, facecolor="#115e59", edgecolor="#134e4a", zorder=1))
        ax.text(8.0, 0.99, "BANCADA EXPERIMENTAL", ha="center", va="center", fontsize=7.5, color="#ecfeff", fontweight="bold", zorder=3)

        ax.add_patch(Rectangle((13.75, 1.28), 0.19, 6.95, facecolor="#4338ca", edgecolor="#312e81", zorder=3))
        ax.add_patch(Rectangle((12.60, 1.20), 2.50, 0.18, facecolor="#6366f1", edgecolor="#312e81", zorder=3))
        ax.add_patch(Rectangle((7.05, 7.88), 6.80, 0.17, facecolor="#4338ca", edgecolor="#312e81", zorder=3))
        ax.add_patch(FancyBboxPatch((6.79, 7.57), 0.82, 0.55, boxstyle="round,pad=0.03,rounding_size=0.08", facecolor=COR_ROXO, edgecolor="#5b21b6", lw=1.2, zorder=4))
        ax.add_patch(Circle((7.20, 7.66), 0.07, facecolor=COR_AMARELO, edgecolor="#a16207", lw=0.7, zorder=5))
        ax.text(7.20, 8.36, "SENSOR", ha="center", va="bottom", fontsize=7.5, color="#4c1d95", fontweight="bold", zorder=5)

        for largura, alpha in [(0.55, 0.9), (0.88, 0.65), (1.20, 0.40)]:
            ax.add_patch(Arc((7.20, 7.50), largura, largura * 0.48, theta1=215, theta2=325, color=COR_MAGENTA, lw=1.3, alpha=alpha, zorder=4))

        # Escala vertical proporcional à altura escolhida.
        x_regua = 3.0
        ax.plot([x_regua, x_regua], [y_base, y_topo], color="#164e63", lw=2.0, zorder=4)
        for frac in np.linspace(0, 1, 5):
            y_marca = y_base + frac * (y_topo - y_base)
            altura_marca = frac * h0
            ax.plot([x_regua - 0.15, x_regua + 0.15], [y_marca, y_marca], color="#164e63", lw=1.0, zorder=4)
            ax.text(x_regua - 0.25, y_marca, f"{formato_numero(altura_marca, 1)} m", ha="right", va="center", fontsize=7, color="#164e63")
        ax.text(x_regua, 7.80, "ALTURA", ha="center", va="bottom", fontsize=7.5, color="#164e63", fontweight="bold")

        # Trajetória, posições anteriores e esfera.
        ax.plot([x_bola, x_bola], [y_base, y_topo], color="#67e8f9", lw=1.1, ls=(0, (3, 3)), zorder=2)
        if y_bola < y_topo - 0.25:
            for indice, y_rastro in enumerate(np.linspace(y_bola + 0.45, y_topo, 5)):
                alpha = 0.16 + indice * 0.08
                ax.add_patch(Circle((x_bola, y_rastro), 0.13, facecolor=COR_VERMELHO, edgecolor="none", alpha=alpha, zorder=3))
        ax.add_patch(Circle((x_bola, y_bola), 0.30, facecolor=COR_VERMELHO, edgecolor="#9f1239", lw=1.4, zorder=6))
        ax.add_patch(Circle((x_bola - 0.10, y_bola + 0.11), 0.075, facecolor="#ffe4e6", edgecolor="none", alpha=0.95, zorder=7))

        # Vetores velocidade e gravidade.
        if self.v > 0.01:
            tamanho = limitar(0.22 + 0.045 * self.v, 0.30, 1.35)
            ax.annotate(
                "",
                xy=(x_bola + 0.62, y_bola - tamanho),
                xytext=(x_bola + 0.62, y_bola + 0.18),
                arrowprops=dict(arrowstyle="-|>", lw=2.2, color=COR_LARANJA),
                zorder=7
            )
            ax.text(x_bola + 0.84, y_bola - tamanho * 0.48, "v", fontsize=8, color="#c2410c", fontweight="bold")

        ax.annotate("", xy=(x_bola - 0.65, y_bola - 0.85), xytext=(x_bola - 0.65, y_bola + 0.15),
                    arrowprops=dict(arrowstyle="-|>", lw=2.0, color=COR_VERDE), zorder=7)
        ax.text(x_bola - 0.90, y_bola - 0.42, "g", fontsize=8, color="#15803d", fontweight="bold")

        # Leituras essenciais, separadas por cor e sempre visíveis.
        ax.text(0.55, 8.55, "QUEDA LIVRE", fontsize=11, fontweight="bold", color="#172033")
        ax.text(9.25, 8.55, self.var_corpo.get().upper(), fontsize=8, fontweight="bold", color="#6d28d9")
        ax.text(9.25, 7.25, f"t = {formato_numero(self.t, 3)} s", fontsize=9, fontweight="bold", color="#0369a1")
        ax.text(11.35, 7.25, f"h = {formato_numero(h_atual, 2)} m", fontsize=9, fontweight="bold", color="#0891b2")
        ax.text(9.25, 6.65, f"v = {formato_numero(self.v, 2)} m/s", fontsize=9, fontweight="bold", color="#c2410c")
        ax.text(11.35, 6.65, f"g = {formato_numero(g, 2)} m/s²", fontsize=9, fontweight="bold", color="#15803d")
        progresso = limitar(self.t / tq if tq > 0 else 0.0, 0.0, 1.0)
        ax.plot([9.25, 13.45], [6.05, 6.05], color="#bae6fd", lw=5.0, solid_capstyle="round", zorder=2)
        ax.plot([9.25, 9.25 + 4.20 * progresso], [6.05, 6.05], color=COR_AZUL, lw=5.0, solid_capstyle="round", zorder=3)
        ax.text(13.65, 6.05, f"{progresso * 100:.0f}%", ha="right", va="center", fontsize=7.5, color="#075985", fontweight="bold")

        self.fig_cena.subplots_adjust(left=0.01, right=0.99, top=0.98, bottom=0.02)
        self.canvas_cena.draw_idle()

    def configurar_eixo(self, ax, titulo, xlabel, ylabel, cor_fundo="#ffffff"):
        ax.set_facecolor(cor_fundo)
        ax.set_title(titulo, fontsize=8.5, fontweight="bold", color="#172033", pad=5)
        ax.set_xlabel(xlabel, fontsize=7)
        ax.set_ylabel(ylabel, fontsize=7)
        ax.tick_params(axis="both", labelsize=7, colors="#475569")
        ax.grid(True, which="major", color=COR_GRADE, alpha=0.75, linewidth=0.65)
        ax.grid(True, which="minor", color=COR_GRADE, alpha=0.35, linewidth=0.45)
        ax.xaxis.set_minor_locator(AutoMinorLocator())
        ax.yaxis.set_minor_locator(AutoMinorLocator())
        for lado in ("top", "right"):
            ax.spines[lado].set_visible(False)
        ax.spines["left"].set_color("#94a3b8")
        ax.spines["bottom"].set_color("#94a3b8")

    def desenhar_graficos(self):
        self.fig_graficos.clear()
        escolha = self.var_grafico.get()
        h0, g, tmax, *_ = self.obter_config()
        tq = tempo_queda_teorico(h0, g)

        t_dados = np.array([d["t"] for d in self.dados_serie], dtype=float) if self.dados_serie else np.array([0.0])
        h_dados = np.array([d["h"] for d in self.dados_serie], dtype=float) if self.dados_serie else np.array([h0])
        v_dados = np.array([d["v"] for d in self.dados_serie], dtype=float) if self.dados_serie else np.array([0.0])

        t_lim = max(float(tmax), tq, float(t_dados.max()) if t_dados.size else 0.0, 0.1)
        t_teorico = np.linspace(0, max(tq, 0.1), 300)
        h_teorico = np.maximum(0.0, modelo_altura(h0, g, t_teorico))
        v_teorico = modelo_velocidade(g, t_teorico)

        if escolha == "Todos":
            gs = gridspec.GridSpec(1, 3, figure=self.fig_graficos, wspace=0.42, top=0.86, bottom=0.22, left=0.06, right=0.98)
            eixos = [self.fig_graficos.add_subplot(gs[0, i]) for i in range(3)]
            self.lbl_nota_grafico.config(text="Mostrando h(t), v(t) e h₀ × tq.")
            self.plotar_altura_tempo(eixos[0], t_dados, h_dados, t_teorico, h_teorico, t_lim, h0)
            self.plotar_velocidade_tempo(eixos[1], t_dados, v_dados, t_teorico, v_teorico, t_lim)
            self.plotar_altura_inicial_tempoqueda(eixos[2])
        elif escolha == "h(t)":
            ax = self.fig_graficos.add_subplot(111)
            self.fig_graficos.subplots_adjust(top=0.90, bottom=0.17, left=0.10, right=0.96)
            self.lbl_nota_grafico.config(text="Mostrando apenas altura instantânea em função do tempo.")
            self.plotar_altura_tempo(ax, t_dados, h_dados, t_teorico, h_teorico, t_lim, h0)
        elif escolha == "v(t)":
            ax = self.fig_graficos.add_subplot(111)
            self.fig_graficos.subplots_adjust(top=0.90, bottom=0.17, left=0.10, right=0.96)
            self.lbl_nota_grafico.config(text="Mostrando apenas velocidade em função do tempo.")
            self.plotar_velocidade_tempo(ax, t_dados, v_dados, t_teorico, v_teorico, t_lim)
        else:
            ax = self.fig_graficos.add_subplot(111)
            self.fig_graficos.subplots_adjust(top=0.90, bottom=0.17, left=0.10, right=0.96)
            self.lbl_nota_grafico.config(text="Mostrando gráfico experimental h₀ × tq.")
            self.plotar_altura_inicial_tempoqueda(ax)

        self.canvas_graficos.draw_idle()

    def plotar_altura_tempo(self, ax, t_dados, h_dados, t_teorico, h_teorico, t_lim, h0):
        ax.fill_between(t_teorico, 0, h_teorico, color=COR_CIANO, alpha=0.10)
        ax.plot(t_teorico, h_teorico, color=COR_ROXO, lw=1.7, ls="--", label="modelo")
        ax.plot(t_dados, h_dados, color=COR_CIANO, marker="o", markerfacecolor="#ffffff", markeredgecolor="#0891b2", ms=3.0, lw=1.25, label="dados")
        ax.scatter([t_dados[-1]], [h_dados[-1]], s=30, color=COR_VERMELHO, edgecolor="#ffffff", linewidth=0.8, zorder=5)
        ax.set_xlim(0, max(t_lim, 0.1))
        ax.set_ylim(-0.03 * h0, max(h0 * 1.08, 0.5))
        self.configurar_eixo(ax, "Altura h(t)", "t (s)", "h (m)", "#ecfeff")
        ax.legend(fontsize=6, loc="upper right", frameon=True, framealpha=0.9, edgecolor="#a5f3fc")

    def plotar_velocidade_tempo(self, ax, t_dados, v_dados, t_teorico, v_teorico, t_lim):
        vmax = max(float(v_teorico.max()) if v_teorico.size else 0.0, float(v_dados.max()) if v_dados.size else 0.0, 0.5)
        ax.fill_between(t_teorico, 0, v_teorico, color=COR_LARANJA, alpha=0.10)
        ax.plot(t_teorico, v_teorico, color=COR_MAGENTA, lw=1.7, ls="--", label="modelo")
        ax.plot(t_dados, v_dados, color=COR_LARANJA, marker="o", markerfacecolor="#ffffff", markeredgecolor="#c2410c", ms=3.0, lw=1.25, label="dados")
        ax.scatter([t_dados[-1]], [v_dados[-1]], s=30, color=COR_VERMELHO, edgecolor="#ffffff", linewidth=0.8, zorder=5)
        ax.set_xlim(0, max(t_lim, 0.1))
        ax.set_ylim(0, vmax * 1.15)
        self.configurar_eixo(ax, "Velocidade v(t)", "t (s)", "v (m/s)", "#fff7ed")
        ax.legend(fontsize=6, loc="upper left", frameon=True, framealpha=0.9, edgecolor="#fed7aa")

    def plotar_altura_inicial_tempoqueda(self, ax):
        if self.ensaios:
            tempos = np.array([e["t_exp"] if self.var_erro_experimental.get() else e["tq"] for e in self.ensaios], dtype=float)
            alturas = np.array([e["h0"] for e in self.ensaios], dtype=float)
            ax.scatter(tempos, alturas, s=30, color=COR_VERDE, edgecolor="#166534", linewidth=0.8, label="ensaios", zorder=4)
            for e in self.ensaios:
                tx = e["t_exp"] if self.var_erro_experimental.get() else e["tq"]
                ax.text(tx, e["h0"], str(e["n"]), fontsize=6, color="#166534", ha="left", va="bottom")
        else:
            tempos = np.array([], dtype=float)
            alturas = np.array([], dtype=float)
            ax.text(0.5, 0.5, "Execute quedas com alturas diferentes\npara construir este gráfico.",
                    transform=ax.transAxes, ha="center", va="center", fontsize=8, color="#64748b")

        if self.var_ajuste.get() and len(self.ensaios) >= 2:
            ajuste = self.calcular_ajuste_altura_tempo()
            if ajuste:
                t_plot = np.linspace(0, max(tempos.max() * 1.08, 0.1), 300)
                h_plot = ajuste["A"] * t_plot ** 2
                ax.plot(t_plot, h_plot, color=COR_MAGENTA, lw=1.6, ls="--", label=f"ajuste: g≈{ajuste['g_est']:.3f}")
                texto = f"h₀ = A·t²\nA = {ajuste['A']:.4f}\ng = 2A = {ajuste['g_est']:.4f} m/s²\nR² = {ajuste['r2']:.4f}"
                ax.text(0.02, 0.96, texto, transform=ax.transAxes, ha="left", va="top", fontsize=6.6,
                        bbox=dict(boxstyle="round,pad=0.25", facecolor="#fdf4ff", edgecolor="#f0abfc", alpha=0.95))

        xmax = max(tempos.max() * 1.12 if tempos.size else 2.0, 0.5)
        h0_atual, *_ = self.obter_config()
        ymax = max(alturas.max() * 1.12 if alturas.size else h0_atual * 1.1, 1.0)
        ax.set_xlim(0, xmax)
        ax.set_ylim(0, ymax)
        self.configurar_eixo(ax, "Ensaios h₀ × tq", "tq (s)", "h₀ (m)", "#f0fdf4")
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(handles, labels, fontsize=6, loc="lower right", frameon=True, framealpha=0.9, edgecolor="#bbf7d0")

    # -------------------------------------------------------------------------
    # TABELAS, AJUSTES E EXPORTAÇÕES
    # -------------------------------------------------------------------------
    def atualizar_tabela(self):
        """Atualiza a tabela experimental sem perder as colunas nem os valores.

        - Para h₀ × tq e dados com erro: mostra os ensaios concluídos.
        - Para h(t), v(t) e tabela completa: mostra os dados da queda atual,
          começando em t = 0, como no laboratório MRU/MRUV.
        """
        if not hasattr(self, "tabela"):
            return

        tipo = self.var_tipo_tabela.get()
        colunas = self.obter_colunas_tabela()
        chaves = [self.mapa_colunas_tabela[g]["chave"] for g in colunas]

        # Garante que as colunas estejam ativas antes de inserir linhas.
        self.tabela.configure(columns=chaves, displaycolumns=chaves)
        for grandeza in colunas:
            meta = self.mapa_colunas_tabela[grandeza]
            chave = meta["chave"]
            self.tabela.heading(chave, text=meta["titulo"])
            self.tabela.column(chave, width=meta["largura"], anchor="center", stretch=False)

        for item in self.tabela.get_children():
            self.tabela.delete(item)

        linhas_inseridas = 0

        if tipo in ("Altura inicial × tempo de queda", "Dados com erro experimental"):
            # Mostra ensaios finalizados. A tabela deixa de ficar vazia mostrando
            # uma linha de previsão enquanto ainda não há ensaio concluído.
            fonte = list(self.ensaios)
            if not fonte:
                h0, g, *_ = self.obter_config()
                tq = tempo_queda_teorico(h0, g)
                fonte = [{
                    "n": 1,
                    "h0": float(h0),
                    "tq": float(tq),
                    "t_exp": float(tq),
                    "erro_t": 0.0,
                    "erro_pct": 0.0,
                    "g": float(g),
                    "corpo": self.var_corpo.get(),
                }]

            for ensaio in fonte:
                valores = []
                for grandeza in colunas:
                    meta = self.mapa_colunas_tabela[grandeza]
                    chave = meta["chave"]
                    valor = ensaio.get(chave, "")
                    if chave == "n":
                        valores.append(str(valor))
                    else:
                        valores.append(formato_numero(valor, meta["casas"]))
                tag = "par" if linhas_inseridas % 2 == 0 else "impar"
                self.tabela.insert("", "end", values=valores, tags=(tag,))
                linhas_inseridas += 1
        else:
            # Mostra os dados da queda atual. Mesmo antes de iniciar, há uma linha t=0.
            if not self.dados_serie:
                self.registrar_ponto(forcar=True)
            for dado in self.dados_serie:
                valores = []
                for grandeza in colunas:
                    meta = self.mapa_colunas_tabela[grandeza]
                    chave = meta["chave"]
                    valor = dado.get(chave, "")
                    if chave == "amostra":
                        valores.append(str(valor))
                    else:
                        valores.append(formato_numero(valor, meta["casas"]))
                tag = "par" if linhas_inseridas % 2 == 0 else "impar"
                self.tabela.insert("", "end", values=valores, tags=(tag,))
                linhas_inseridas += 1

        # Mantém a última linha visível durante a simulação.
        filhos = self.tabela.get_children()
        if filhos:
            self.tabela.see(filhos[-1])

    def calcular_ajuste_altura_tempo(self):
        if len(self.ensaios) < 2:
            return None
        t = np.array([e["t_exp"] if self.var_erro_experimental.get() else e["tq"] for e in self.ensaios], dtype=float)
        h = np.array([e["h0"] for e in self.ensaios], dtype=float)
        x = t ** 2
        denominador = float(np.dot(x, x))
        if denominador <= 0:
            return None
        A = float(np.dot(x, h) / denominador)
        h_pred = A * x
        r2 = self.calcular_r2(h, h_pred)
        return {"A": A, "g_est": 2.0 * A, "r2": r2, "n": len(self.ensaios)}

    def calcular_r2(self, y, y_pred):
        if len(y) < 2:
            return 1.0
        ss_res = float(np.sum((y - y_pred) ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        if ss_tot <= 1e-15:
            return 1.0
        return 1.0 - ss_res / ss_tot

    def gerar_texto_relatorio(self):
        h0, g, tmax, dt, ritmo, intervalo, sigma_t = self.obter_config()
        tq = tempo_queda_teorico(h0, g)
        ajuste = self.calcular_ajuste_altura_tempo()
        linhas = []
        linhas.append("RELATÓRIO AUTOMÁTICO — LABORATÓRIO VIRTUAL DE QUEDA LIVRE")
        linhas.append("=" * 72)
        linhas.append(f"Aplicação: {NOME_APLICATIVO} | versão {VERSAO_APLICATIVO}")
        linhas.append(f"Autor: {AUTOR}")
        linhas.append(f"Data/hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        linhas.append("")
        linhas.append("1. Modelo físico")
        linhas.append("   h(t) = h0 - (1/2) g t²")
        linhas.append("   v(t) = g t")
        linhas.append("   tq = sqrt(2 h0 / g)")
        linhas.append("")
        linhas.append("2. Parâmetros atuais")
        linhas.append(f"   Ambiente: {self.var_corpo.get()}")
        linhas.append(f"   h0 atual: {h0:.6f} m")
        linhas.append(f"   g: {g:.6f} m/s²")
        linhas.append(f"   tq teórico atual: {tq:.6f} s")
        linhas.append(f"   janela temporal: {tmax:.6f} s")
        linhas.append(f"   dt: {dt:.6f} s")
        linhas.append(f"   ritmo visual: {ritmo:.3f}x")
        linhas.append(f"   coleta: {self.var_registro.get()} | intervalo discreto: {intervalo:.6f} s")
        linhas.append(f"   erro experimental: {self.var_erro_experimental.get()} | sigma_t: {sigma_t:.6f} s")
        linhas.append("")
        linhas.append("3. Ensaios registrados")
        if not self.ensaios:
            linhas.append("   Nenhum ensaio registrado.")
        else:
            linhas.append("   Nº; h0(m); tq_teorico(s); tq_exp(s); erro_t(s); erro(%); g(m/s²); corpo")
            for e in self.ensaios:
                linhas.append(
                    f"   {e['n']}; {e['h0']:.6f}; {e['tq']:.6f}; {e['t_exp']:.6f}; "
                    f"{e['erro_t']:.6f}; {e['erro_pct']:.3f}; {e['g']:.6f}; {e['corpo']}"
                )
        linhas.append("")
        linhas.append("4. Ajuste experimental h0 = A·t²")
        if ajuste:
            linhas.append(f"   A = {ajuste['A']:.8f}")
            linhas.append(f"   g estimado = 2A = {ajuste['g_est']:.8f} m/s²")
            linhas.append(f"   R² = {ajuste['r2']:.6f}")
            linhas.append(f"   Número de ensaios: {ajuste['n']}")
        else:
            linhas.append("   Ajuste indisponível: registre pelo menos 2 ensaios.")
        linhas.append("")
        linhas.append("5. Interpretação didática")
        linhas.append("   Em queda livre ideal, a altura inicial é proporcional ao quadrado do tempo de queda.")
        linhas.append("   Assim, o gráfico h0 × tq não é linear; o ajuste adequado é quadrático com intercepto nulo.")
        linhas.append("   A constante A obtida no ajuste corresponde a g/2.")
        return "\n".join(linhas)

    def gerar_roteiro_pre_pos_teste(self):
        return """ROTEIRO DIDÁTICO — PRÉ-TESTE E PÓS-TESTE: QUEDA LIVRE

Objetivo geral:
Investigar, com auxílio de um laboratório virtual offline, a relação entre altura inicial, tempo de queda e gravidade em um movimento de queda livre ideal.

PRÉ-TESTE
1. Quando a altura inicial aumenta, o tempo de queda aumenta de forma linear ou não linear? Justifique.
2. Se uma esfera é solta do repouso, sua velocidade permanece constante? Explique.
3. Qual grandeza física determina a aceleração da esfera em queda livre ideal?
4. O gráfico h(t) deve ser uma reta ou uma curva? Por quê?
5. Como você poderia estimar g usando várias alturas e seus tempos de queda?

PROCEDIMENTO COM A SIMULAÇÃO
1. Escolha o ambiente Terra e uma altura inicial pequena, por exemplo 2 m.
2. Inicie a queda e registre o tempo total.
3. Repita para 5 m, 10 m, 15 m e 20 m.
4. Observe a tabela altura inicial × tempo de queda.
5. Ative o ajuste h₀ = A·t² e compare g estimado com o valor configurado.

PÓS-TESTE
1. O gráfico altura inicial × tempo de queda foi linear? Explique usando a equação h₀ = (g/2)t².
2. O que acontece com o tempo de queda quando a gravidade diminui?
3. Como o gráfico v(t) mostra que a aceleração é constante?
4. Qual foi o valor de g estimado pelo ajuste? Ele ficou próximo do esperado?
5. Cite uma limitação do modelo usado nesta simulação.
"""

    def salvar_texto_em_arquivo(self, titulo, conteudo, extensao="txt"):
        nome_base = "roteiro_queda_livre" if "roteiro" in titulo.lower() else "relatorio_queda_livre"
        nome_padrao = f"{nome_base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{extensao}"
        caminho = filedialog.asksaveasfilename(
            title=titulo,
            defaultextension=f".{extensao}",
            initialfile=nome_padrao,
            filetypes=[("Arquivo de texto", "*.txt"), ("Todos os arquivos", "*.*")]
        )
        if not caminho:
            return
        try:
            with open(caminho, "w", encoding="utf-8-sig") as arquivo:
                arquivo.write(conteudo)
            messagebox.showinfo("Arquivo salvo", f"Arquivo salvo com sucesso:\n{caminho}")
        except OSError as erro:
            messagebox.showerror("Erro ao salvar", f"Não foi possível salvar o arquivo.\n\n{erro}")

    def exportar_relatorio(self):
        if not self.validar_parametros(mostrar_erro=True):
            return
        self.salvar_texto_em_arquivo("Salvar relatório da queda livre", self.gerar_texto_relatorio(), "txt")

    def exportar_roteiro_pre_pos_teste(self):
        self.salvar_texto_em_arquivo("Salvar roteiro pré/pós-teste", self.gerar_roteiro_pre_pos_teste(), "txt")

    def exportar_csv(self):
        if not self.validar_parametros(mostrar_erro=True):
            return
        caminho = filedialog.asksaveasfilename(
            title="Salvar dados da queda livre em CSV",
            defaultextension=".csv",
            initialfile=f"dados_queda_livre_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            filetypes=[("Arquivo CSV", "*.csv"), ("Todos os arquivos", "*.*")]
        )
        if not caminho:
            return

        try:
            with open(caminho, "w", newline="", encoding="utf-8-sig") as arquivo:
                writer = csv.writer(arquivo, delimiter=";")
                writer.writerow(["LABORATÓRIO VIRTUAL DE QUEDA LIVRE"])
                writer.writerow(["Versão", VERSAO_APLICATIVO])
                writer.writerow(["Autor", AUTOR])
                writer.writerow(["Exportado em", datetime.now().strftime("%d/%m/%Y %H:%M:%S")])
                writer.writerow([])
                writer.writerow(["ENSAIOS: altura inicial x tempo de queda"])
                writer.writerow(["ensaio", "altura_inicial_m", "tempo_teorico_s", "tempo_experimental_s", "erro_tempo_s", "erro_percentual", "gravidade_m_s2", "corpo"])
                for e in self.ensaios:
                    writer.writerow([e["n"], e["h0"], e["tq"], e["t_exp"], e["erro_t"], e["erro_pct"], e["g"], e["corpo"]])

                writer.writerow([])
                writer.writerow(["SÉRIE TEMPORAL DA QUEDA ATUAL"])
                writer.writerow(["amostra", "tempo_s", "altura_m", "velocidade_m_s", "gravidade_m_s2", "altura_inicial_m"])
                for d in self.dados_serie:
                    writer.writerow([d["amostra"], d["t"], d["h"], d["v"], d["g"], d["h0"]])

                ajuste = self.calcular_ajuste_altura_tempo()
                if ajuste:
                    writer.writerow([])
                    writer.writerow(["AJUSTE h0 = A*t^2"])
                    writer.writerow(["A", ajuste["A"]])
                    writer.writerow(["g_estimado_m_s2", ajuste["g_est"]])
                    writer.writerow(["R2", ajuste["r2"]])

            messagebox.showinfo("CSV exportado", f"Dados exportados com sucesso:\n{caminho}")
        except OSError as erro:
            messagebox.showerror("Erro ao exportar", f"Não foi possível exportar os dados.\n\n{erro}")

    def fechar(self):
        self.cancelar_after()
        self.root.destroy()


# =============================================================================
# EXECUÇÃO
# =============================================================================

def main():
    root = tk.Tk()
    app = LaboratorioQuedaLivre(root)
    root.mainloop()


if __name__ == "__main__":
    main()
