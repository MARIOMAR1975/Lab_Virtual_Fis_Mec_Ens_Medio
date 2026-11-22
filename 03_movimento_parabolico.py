# -*- coding: utf-8 -*-
"""
LABORATÓRIO VIRTUAL OFFLINE: Movimento Parabólico — formato compacto Tkinter + Matplotlib

Versão reorganizada no mesmo formato visual do LAB_MRU_MRUV:
- Painel de comando compacto à esquerda.
- Simulação experimental na parte superior.
- Gráficos em tempo real na parte inferior.
- Tabela experimental lateral compacta.
- Controles visíveis: iniciar, pausar, passo, resetar, registrar ponto, limpar tabela e exportar.
- Ritmo de animação contínuo por tempo físico, sem saltos entre quadros.

Física usada:
    x(t) = x0 + v0*cos(theta)*t
    y(t) = y0 + v0*sin(theta)*t - (1/2)g*t²
    vx(t) = v0*cos(theta)
    vy(t) = v0*sin(theta) - g*t
    ay(t) = -g

Bibliotecas: tkinter, numpy e matplotlib.
Funciona localmente, sem navegador e sem internet.
"""

import csv
import math
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

import numpy as np

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle, Circle, Wedge, FancyArrowPatch
from matplotlib.ticker import AutoMinorLocator


# =============================================================================
# IDENTIDADE VISUAL E LIMITES
# =============================================================================

NOME_APLICATIVO = "Laboratório Virtual — Movimento Parabólico"
VERSAO_APLICATIVO = "2.1"

COR_FUNDO = "#17162f"
COR_PAINEL = "#20243d"
COR_GRUPO = "#29304d"
COR_GRUPO_BORDA = "#64748b"
COR_CARD = "#f8fafc"
COR_CARD_BORDA = "#94a3b8"
COR_TEXTO_CLARO = "#f8fafc"
COR_TEXTO_SUAVE = "#c4b5fd"
COR_TEXTO_ESCURO = "#111827"
COR_TEXTO_SECUNDARIO = "#475569"
COR_CIANO = "#06b6d4"
COR_AZUL = "#0ea5e9"
COR_VERDE = "#22c55e"
COR_LARANJA = "#f97316"
COR_VERMELHO = "#f43f5e"
COR_MAGENTA = "#d946ef"
COR_ROXO = "#8b5cf6"
COR_AMARELO = "#facc15"
COR_CENA = "#ecfeff"
COR_GRAFICO = "#ffffff"
COR_GRADE = "#94a3b8"

DT_MIN = 0.001
DT_MAX = 1.0
RITMO_MIN = 0.01
RITMO_MAX = 32.0
INTERVALO_MIN = 0.001
MAX_DADOS = 10000

CORES_GRAFICOS = {
    "x": COR_AZUL,
    "y": COR_VERDE,
    "vx": COR_LARANJA,
    "vy": COR_VERMELHO,
    "v": COR_ROXO,
    "ay": "#14b8a6",
}

CORES_PLANETAS = [
    "#06b6d4", "#f97316", "#22c55e", "#8b5cf6", "#f43f5e",
    "#eab308", "#0ea5e9", "#d946ef", "#14b8a6", "#ef4444",
]


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def arredondar_fisico(valor, casas=9):
    try:
        numero = float(valor)
        return round(numero, casas) if math.isfinite(numero) else valor
    except (TypeError, ValueError):
        return valor


def formato_numero(valor, casas=3):
    """Formata com vírgula decimal para uso didático."""
    try:
        numero_float = float(valor)
        if not math.isfinite(numero_float):
            return "—"
        quantizador = Decimal("1").scaleb(-int(casas))
        numero = Decimal(str(numero_float)).quantize(quantizador, rounding=ROUND_HALF_UP)
        return f"{numero:.{int(casas)}f}".replace(".", ",")
    except (TypeError, ValueError, ArithmeticError):
        return str(valor)


def limitar(valor, minimo, maximo):
    return max(minimo, min(maximo, valor))


def nice_limits(valores, margem=0.12):
    vals = [float(v) for v in valores if np.isfinite(v)]
    if not vals:
        return -1.0, 1.0
    vmin, vmax = min(vals), max(vals)
    if abs(vmax - vmin) < 1e-12:
        delta = max(1.0, abs(vmax) * 0.25)
        return vmin - delta, vmax + delta
    span = vmax - vmin
    return vmin - margem * span, vmax + margem * span


# =============================================================================
# CLASSE PRINCIPAL
# =============================================================================

class LaboratorioMovimentoParabolico:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{NOME_APLICATIVO} | v{VERSAO_APLICATIVO}")
        self.root.geometry("1366x760")
        self.root.minsize(1100, 680)

        # Estado da simulação
        self.rodando = False
        self.t = 0.0
        self.dados = []
        self.indice = 0
        self.impacto = False
        self.after_id = None
        self.proximo_t_discreto = 0.0
        self.modo_comparacao = False
        self._suprimir_eventos = False

        # Controle temporal contínuo da animação.
        # O projétil avança pelo tempo real transcorrido entre quadros,
        # evitando saltos grandes e pausas visuais artificiais.
        self.ultimo_instante_loop = None
        self.ultimo_redesenho_grafico = 0.0
        self.ultimo_redesenho_tabela = 0.0

        # Gravidades disponíveis
        self.gravidades_planetas = {
            "Mercúrio": 3.70,
            "Vênus": 8.87,
            "Terra": 9.81,
            "Lua": 1.62,
            "Marte": 3.71,
            "Júpiter": 24.79,
            "Saturno": 10.44,
            "Urano": 8.69,
            "Netuno": 11.15,
            "Plutão": 0.62,
        }

        # Variáveis Tkinter
        self.var_planeta = tk.StringVar(value="Terra")
        self.var_y0 = tk.StringVar(value="20.0")
        self.var_v0 = tk.StringVar(value="25.0")
        self.var_angulo = tk.StringVar(value="40.0")
        self.var_g = tk.StringVar(value="9.81")
        self.var_tmax = tk.StringVar(value="8.0")
        self.var_dt = tk.StringVar(value="0.05")
        self.var_ritmo = tk.StringVar(value="6.00")

        self.var_grafico = tk.StringVar(value="Todos")
        self.var_registro = tk.StringVar(value="Contínua")
        self.var_intervalo_discreto = tk.StringVar(value="0.25")
        self.var_mostrar_vetores = tk.BooleanVar(value=True)
        self.var_mostrar_grade = tk.BooleanVar(value=True)
        self.var_mostrar_trajetoria = tk.BooleanVar(value=True)
        self.var_mostrar_cenario = tk.BooleanVar(value=True)

        self.opcoes_tipo_tabela = [
            "Altura × Tempo",
            "Posição horizontal × Tempo",
            "Velocidade vertical × Tempo",
            "Tabela completa: t, x, y, vx, vy",
            "Resultados do lançamento",
        ]
        self.var_tipo_tabela = tk.StringVar(value="Altura × Tempo")
        self.var_descricao_tabela = tk.StringVar(value="Tabela ativa: y em função do tempo.")

        self.mapa_grandezas_tabela = {
            "Tempo": {"chave": "t", "titulo": "t", "csv": "tempo_s", "casas": 3, "largura": 58},
            "x": {"chave": "x", "titulo": "x", "csv": "posicao_x_m", "casas": 3, "largura": 58},
            "y": {"chave": "y", "titulo": "y", "csv": "altura_y_m", "casas": 3, "largura": 58},
            "vx": {"chave": "vx", "titulo": "vx", "csv": "velocidade_x_m_s", "casas": 3, "largura": 62},
            "vy": {"chave": "vy", "titulo": "vy", "csv": "velocidade_y_m_s", "casas": 3, "largura": 62},
            "v": {"chave": "v", "titulo": "v", "csv": "velocidade_resultante_m_s", "casas": 3, "largura": 62},
            "ay": {"chave": "ay", "titulo": "ay", "csv": "aceleracao_y_m_s2", "casas": 3, "largura": 62},
        }

        self.var_status = tk.StringVar(value="Pronto para iniciar.")
        self.var_resultados = tk.StringVar(value="")

        self.configurar_estilo()
        self.criar_interface()
        self.configurar_eventos()
        self.reiniciar_simulacao(limpar_tabela=True)

    # -------------------------------------------------------------------------
    # ESTILO VISUAL
    # -------------------------------------------------------------------------
    def configurar_estilo(self):
        self.root.configure(bg=COR_FUNDO)
        estilo = ttk.Style()
        try:
            estilo.theme_use("clam")
        except Exception:
            pass

        estilo.configure("TFrame", background=COR_FUNDO)
        estilo.configure("Panel.TFrame", background=COR_PAINEL, relief="flat")
        estilo.configure("Card.TFrame", background=COR_CARD, relief="flat")
        estilo.configure("TLabel", background=COR_PAINEL, foreground=COR_TEXTO_CLARO, font=("Segoe UI", 8))
        estilo.configure("Title.TLabel", background=COR_FUNDO, foreground=COR_TEXTO_CLARO, font=("Segoe UI", 14, "bold"))
        estilo.configure("SubTitle.TLabel", background=COR_FUNDO, foreground="#a5f3fc", font=("Segoe UI", 8))
        estilo.configure("TButton", font=("Segoe UI", 7, "bold"), padding=(5, 3))
        estilo.configure("Accent.TButton", foreground="white", background=COR_AZUL)
        estilo.configure("Success.TButton", foreground="#052e16", background=COR_VERDE)
        estilo.configure("Warning.TButton", foreground="#431407", background=COR_AMARELO)
        estilo.configure("Danger.TButton", foreground="white", background=COR_VERMELHO)
        estilo.map("Accent.TButton", background=[("pressed", "#0369a1"), ("active", "#0284c7")])
        estilo.map("Success.TButton", background=[("pressed", "#15803d"), ("active", "#4ade80")])
        estilo.map("Warning.TButton", background=[("pressed", "#ca8a04"), ("active", "#fde047")])
        estilo.map("Danger.TButton", background=[("pressed", "#be123c"), ("active", "#fb7185")])
        estilo.configure("TEntry", fieldbackground="#111827", foreground=COR_TEXTO_CLARO, insertcolor=COR_TEXTO_CLARO)
        estilo.configure("TCombobox", fieldbackground="#111827", foreground=COR_TEXTO_CLARO)
        estilo.configure("Treeview", font=("Segoe UI", 7), rowheight=20, background="#ffffff", fieldbackground="#ffffff", foreground=COR_TEXTO_ESCURO)
        estilo.configure("Treeview.Heading", font=("Segoe UI", 7, "bold"), background="#cffafe", foreground="#164e63")
        estilo.map("Treeview", background=[("selected", COR_AZUL)], foreground=[("selected", "white")])

    # -------------------------------------------------------------------------
    # INTERFACE
    # -------------------------------------------------------------------------
    def criar_interface(self):
        self.criar_cabecalho()
        self.criar_corpo()

    def criar_cabecalho(self):
        cabecalho = ttk.Frame(self.root, style="TFrame", padding=(8, 5, 8, 2))
        cabecalho.grid(row=0, column=0, sticky="ew")
        cabecalho.columnconfigure(0, weight=1)

        ttk.Label(
            cabecalho,
            text=NOME_APLICATIVO,
            style="Title.TLabel"
        ).grid(row=0, column=0, sticky="w")

        ttk.Label(
            cabecalho,
            text="Trajetória, velocidade, alcance e comparação gravitacional",
            style="SubTitle.TLabel"
        ).grid(row=1, column=0, sticky="w", pady=(1, 0))

        acoes_cabecalho = ttk.Frame(cabecalho, style="TFrame")
        acoes_cabecalho.grid(row=0, column=1, rowspan=2, sticky="e", padx=(10, 0))

        self.btn_prepos = ttk.Button(
            acoes_cabecalho,
            text="Pré/Pós",
            style="Accent.TButton",
            command=self.exportar_roteiro_pre_pos_teste
        )
        self.btn_prepos.grid(row=0, column=0, sticky="e", padx=(0, 7))

        selo = tk.Label(
            acoes_cabecalho,
            text=f"Versão {VERSAO_APLICATIVO} • Offline",
            bg="#0e7490",
            fg="#ecfeff",
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=3,
            relief="flat"
        )
        selo.grid(row=0, column=1, sticky="e")

    def criar_corpo(self):
        corpo = ttk.Frame(self.root, style="TFrame", padding=(5, 3, 5, 5))
        corpo.grid(row=1, column=0, sticky="nsew")
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)

        corpo.columnconfigure(0, minsize=225, weight=0)
        corpo.columnconfigure(1, weight=1)
        corpo.rowconfigure(0, weight=1)

        self.criar_painel_controle(corpo)
        self.criar_area_trabalho(corpo)

    def criar_painel_controle(self, parent):
        painel = tk.Frame(parent, bg=COR_PAINEL, bd=0, highlightthickness=1, highlightbackground=COR_CIANO)
        painel.grid(row=0, column=0, sticky="nsw", padx=(0, 5))
        painel.grid_propagate(False)
        painel.configure(width=225)
        painel.columnconfigure(0, weight=1)

        tk.Label(
            painel,
            text="Painel de comando",
            bg=COR_PAINEL,
            fg="#a5f3fc",
            font=("Segoe UI", 10, "bold")
        ).grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 2))

        self.criar_grupo_modelo(painel, 1)
        self.criar_grupo_visualizacao(painel, 2)
        self.criar_grupo_botoes(painel, 3)
        self.criar_grupo_presets(painel, 4)

    def criar_grupo(self, parent, row, titulo):
        grupo = tk.Frame(parent, bg=COR_GRUPO, bd=0, highlightthickness=1, highlightbackground=COR_GRUPO_BORDA)
        grupo.grid(row=row, column=0, sticky="ew", padx=5, pady=2)
        for c in range(3):
            grupo.columnconfigure(c, weight=1)
        tk.Label(
            grupo,
            text=titulo.upper(),
            bg=COR_GRUPO,
            fg="#f0abfc",
            font=("Segoe UI", 7, "bold")
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=5, pady=(4, 1))
        return grupo

    def criar_grupo_modelo(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Modelo físico")
        self.criar_label_combo(grupo, 1, "Planeta", self.var_planeta, list(self.gravidades_planetas.keys()))
        self.criar_linha_entradas(grupo, 2, "h₀ (m)", self.var_y0, "v₀ (m/s)", self.var_v0)
        self.criar_linha_entradas(grupo, 3, "ângulo (°)", self.var_angulo, "g (m/s²)", self.var_g)
        self.criar_linha_entradas(grupo, 4, "t máx (s)", self.var_tmax, "Δt (s)", self.var_dt)

    def criar_grupo_visualizacao(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Visualização e coleta")
        self.criar_label_combo(grupo, 1, "Gráficos", self.var_grafico, ["Todos", "x(t)", "y(t)", "vx(t)", "vy(t)", "v(t)", "ay(t)", "Ocultar"])
        self.criar_label_combo(grupo, 2, "Ritmo", self.var_ritmo, [1.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 16.0])
        self.criar_label_combo(grupo, 3, "Coleta", self.var_registro, ["Contínua", "Discreta", "Manual"])
        self.criar_linha_entradas(grupo, 4, "Δt coleta", self.var_intervalo_discreto, "", tk.StringVar(value=""))

        linha = tk.Frame(grupo, bg=COR_GRUPO)
        linha.grid(row=5, column=0, columnspan=3, sticky="ew", padx=4, pady=(1, 4))
        for c in range(2):
            linha.columnconfigure(c, weight=1)

        opcoes = [
            ("trajetória", self.var_mostrar_trajetoria, 0, 0),
            ("vetores", self.var_mostrar_vetores, 0, 1),
            ("grade", self.var_mostrar_grade, 1, 0),
            ("cenário", self.var_mostrar_cenario, 1, 1),
        ]
        for texto, variavel, linha_grid, coluna_grid in opcoes:
            tk.Checkbutton(
                linha,
                text=texto,
                variable=variavel,
                bg=COR_GRUPO,
                fg=COR_TEXTO_CLARO,
                activebackground=COR_GRUPO,
                activeforeground="white",
                selectcolor="#111827",
                font=("Segoe UI", 7),
            ).grid(row=linha_grid, column=coluna_grid, sticky="w", padx=(0, 4), pady=1)

    def criar_grupo_botoes(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Controle da simulação")

        self.btn_iniciar = ttk.Button(grupo, text="Iniciar", style="Success.TButton", command=self.iniciar)
        self.btn_pausar = ttk.Button(grupo, text="Pausar", style="Warning.TButton", command=self.pausar)
        self.btn_passo = ttk.Button(grupo, text="Passo", command=self.passo)
        self.btn_reset = ttk.Button(grupo, text="Resetar", style="Danger.TButton", command=lambda: self.reiniciar_simulacao(limpar_tabela=True))
        self.btn_registrar = ttk.Button(grupo, text="Reg. ponto", command=self.registrar_ponto_manual)
        self.btn_limpar = ttk.Button(grupo, text="Limpar", command=self.limpar_tabela)
        self.btn_comparar = ttk.Button(grupo, text="Comparar", style="Accent.TButton", command=self.comparar_planetas)
        self.btn_csv = ttk.Button(grupo, text="CSV", command=self.exportar_csv)
        self.btn_relatorio = ttk.Button(grupo, text="Relatório", command=self.exportar_relatorio)
        botoes = [
            (self.btn_iniciar, 1, 0), (self.btn_pausar, 1, 1), (self.btn_passo, 1, 2),
            (self.btn_reset, 2, 0), (self.btn_registrar, 2, 1), (self.btn_limpar, 2, 2),
            (self.btn_comparar, 3, 0), (self.btn_csv, 3, 1), (self.btn_relatorio, 3, 2),
        ]
        for botao, r, c in botoes:
            botao.grid(row=r, column=c, sticky="ew", padx=2, pady=2)

        tk.Label(
            grupo,
            textvariable=self.var_status,
            bg=COR_GRUPO,
            fg="#a5f3fc",
            font=("Segoe UI", 7),
            wraplength=205,
            justify="left"
        ).grid(row=4, column=0, columnspan=3, sticky="ew", padx=5, pady=(1, 4))

    def criar_grupo_presets(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Situações prontas")
        b1 = ttk.Button(grupo, text="Baixo", command=lambda: self.aplicar_preset(1))
        b2 = ttk.Button(grupo, text="Longo", command=lambda: self.aplicar_preset(2))
        b3 = ttk.Button(grupo, text="Lua", command=lambda: self.aplicar_preset(3))
        b1.grid(row=1, column=0, sticky="ew", padx=2, pady=2)
        b2.grid(row=1, column=1, sticky="ew", padx=2, pady=2)
        b3.grid(row=1, column=2, sticky="ew", padx=2, pady=2)

    def criar_label_combo(self, parent, row, texto, variavel, opcoes):
        tk.Label(parent, text=texto, bg=COR_GRUPO, fg=COR_TEXTO_CLARO, font=("Segoe UI", 7)).grid(row=row, column=0, sticky="w", padx=5, pady=(1, 0))
        combo = ttk.Combobox(parent, textvariable=variavel, values=opcoes, state="readonly", font=("Segoe UI", 7), width=9)
        combo.grid(row=row, column=1, columnspan=2, sticky="ew", padx=5, pady=(1, 0))
        combo.bind("<<ComboboxSelected>>", lambda event: self.configuracao_alterada())
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
        tk.Label(f1, text=texto1, bg=COR_GRUPO, fg=COR_TEXTO_CLARO, font=("Segoe UI", 7)).grid(row=0, column=0, sticky="w")
        e1 = ttk.Entry(f1, textvariable=var1, font=("Segoe UI", 7), width=6)
        e1.grid(row=1, column=0, sticky="ew")
        if texto2:
            tk.Label(f2, text=texto2, bg=COR_GRUPO, fg=COR_TEXTO_CLARO, font=("Segoe UI", 7)).grid(row=0, column=0, sticky="w")
            e2 = ttk.Entry(f2, textvariable=var2, font=("Segoe UI", 7), width=6)
            e2.grid(row=1, column=0, sticky="ew")
            e2.bind("<FocusOut>", lambda event: self.configuracao_alterada())
        e1.bind("<FocusOut>", lambda event: self.configuracao_alterada())

    def criar_area_trabalho(self, parent):
        area = tk.Frame(parent, bg=COR_FUNDO)
        area.grid(row=0, column=1, sticky="nsew")
        area.columnconfigure(0, weight=1)
        area.columnconfigure(1, weight=0, minsize=225)
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

        self.fig_cena = Figure(figsize=(8, 3.8), dpi=100, facecolor=COR_CARD)
        self.ax_cena = self.fig_cena.add_subplot(111)
        self.canvas_cena = FigureCanvasTkAgg(self.fig_cena, master=card)
        self.canvas_cena.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=4)

    def criar_graficos(self, parent, row=0, column=0, padx=(0, 8)):
        card = tk.Frame(parent, bg=COR_CARD, bd=0, highlightthickness=1, highlightbackground=COR_ROXO)
        card.grid(row=row, column=column, sticky="nsew", padx=padx)
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=0)
        card.rowconfigure(1, weight=1)

        topo = tk.Frame(card, bg=COR_CARD)
        topo.grid(row=0, column=0, sticky="ew", padx=6, pady=(3, 0))
        topo.columnconfigure(0, weight=1)
        tk.Label(topo, text="Gráficos em tempo real", bg=COR_CARD, fg=COR_TEXTO_ESCURO, font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
        self.lbl_nota_grafico = tk.Label(topo, text="Mostrando x(t), y(t), vx(t), vy(t), v(t) e ay(t).", bg=COR_CARD, fg=COR_TEXTO_SECUNDARIO, font=("Segoe UI", 7))
        self.lbl_nota_grafico.grid(row=0, column=1, sticky="e")

        self.fig_graficos = Figure(figsize=(7.2, 4.0), dpi=100, facecolor=COR_CARD)
        self.canvas_graficos = FigureCanvasTkAgg(self.fig_graficos, master=card)
        self.canvas_graficos.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=5, pady=(2, 5))

    def criar_tabela_e_leituras(self, parent):
        card = tk.Frame(parent, bg=COR_CARD, bd=0, highlightthickness=1, highlightbackground=COR_LARANJA, width=225)
        card.grid(row=0, column=1, sticky="nsew")
        card.grid_propagate(False)
        card.columnconfigure(0, weight=1)
        card.rowconfigure(3, weight=1)

        topo = tk.Frame(card, bg=COR_CARD)
        topo.grid(row=0, column=0, sticky="ew", padx=8, pady=(7, 4))
        topo.columnconfigure(0, weight=1)
        tk.Label(topo, text="Tabela experimental", bg=COR_CARD, fg=COR_TEXTO_ESCURO, font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(topo, text="dados", bg=COR_CARD, fg=COR_LARANJA, font=("Segoe UI", 8, "bold")).grid(row=0, column=1, sticky="e")

        painel_tabela = tk.Frame(card, bg="#cffafe", bd=0, highlightthickness=1, highlightbackground="#22d3ee")
        painel_tabela.grid(row=1, column=0, sticky="ew", padx=7, pady=(0, 6))
        painel_tabela.columnconfigure(1, weight=1)
        tk.Label(painel_tabela, text="Grandeza", bg="#cffafe", fg="#164e63", font=("Segoe UI", 8, "bold")).grid(row=0, column=0, sticky="w", padx=8, pady=(7, 3))
        combo_tipo = ttk.Combobox(painel_tabela, textvariable=self.var_tipo_tabela, values=self.opcoes_tipo_tabela, state="readonly", width=17, font=("Segoe UI", 8))
        combo_tipo.grid(row=0, column=1, sticky="ew", padx=8, pady=(7, 3))
        combo_tipo.bind("<<ComboboxSelected>>", lambda event: self.aplicar_configuracao_tabela())
        tk.Label(painel_tabela, textvariable=self.var_descricao_tabela, bg="#cffafe", fg="#155e75", font=("Segoe UI", 8), justify="left", wraplength=205).grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(2, 7))

        resultados = tk.Label(card, textvariable=self.var_resultados, bg="#fef9c3", fg="#713f12", font=("Segoe UI", 8, "bold"), justify="left", wraplength=205)
        resultados.grid(row=2, column=0, sticky="ew", padx=7, pady=(0, 6))

        frame_tabela = tk.Frame(card, bg=COR_CARD)
        frame_tabela.grid(row=3, column=0, sticky="nsew", padx=7, pady=(0, 7))
        frame_tabela.columnconfigure(0, weight=1)
        frame_tabela.rowconfigure(0, weight=1)
        self.tabela = ttk.Treeview(frame_tabela, columns=(), show="headings", height=28)
        barra_y = ttk.Scrollbar(frame_tabela, orient="vertical", command=self.tabela.yview)
        barra_x = ttk.Scrollbar(frame_tabela, orient="horizontal", command=self.tabela.xview)
        self.tabela.configure(yscrollcommand=barra_y.set, xscrollcommand=barra_x.set)
        self.tabela.grid(row=0, column=0, sticky="nsew")
        barra_y.grid(row=0, column=1, sticky="ns")
        barra_x.grid(row=1, column=0, sticky="ew")
        self.aplicar_configuracao_tabela()

    # -------------------------------------------------------------------------
    # EVENTOS E VALIDAÇÃO
    # -------------------------------------------------------------------------
    def configurar_eventos(self):
        variaveis = [
            self.var_planeta, self.var_y0, self.var_v0, self.var_angulo, self.var_g,
            self.var_tmax, self.var_dt, self.var_ritmo, self.var_grafico,
            self.var_registro, self.var_tipo_tabela, self.var_intervalo_discreto,
            self.var_mostrar_vetores, self.var_mostrar_grade, self.var_mostrar_trajetoria,
            self.var_mostrar_cenario,
        ]
        for var in variaveis:
            var.trace_add("write", lambda *args: self.configuracao_alterada(suave=True))
        self.root.protocol("WM_DELETE_WINDOW", self.fechar)

    def configuracao_alterada(self, suave=False):
        if self._suprimir_eventos:
            return

        # Quando muda o planeta, atualiza a gravidade automaticamente.
        planeta = self.var_planeta.get()
        if planeta in self.gravidades_planetas:
            g_planeta = self.gravidades_planetas[planeta]
            try:
                g_atual = self.ler_numero(self.var_g, "gravidade")
            except ValueError:
                g_atual = None
            if not suave and (g_atual is None or abs(g_atual - g_planeta) > 1e-9):
                self._suprimir_eventos = True
                try:
                    self.var_g.set(f"{g_planeta:.2f}")
                finally:
                    self._suprimir_eventos = False

        if not self.validar_parametros(mostrar_erro=False):
            return
        if self.t == 0:
            self.dados = []
            self.indice = 0
            self.proximo_t_discreto = 0.0
            self.registrar_ponto(forcar=True)
        self.atualizar_tudo()

    def ler_numero(self, variavel, nome):
        """Lê um campo numérico aceitando ponto ou vírgula decimal."""
        texto = str(variavel.get()).strip().replace(",", ".")
        if not texto:
            raise ValueError(f"Preencha o campo {nome}.")
        try:
            numero = float(texto)
        except (TypeError, ValueError) as erro:
            raise ValueError(f"O campo {nome} deve conter um número válido.") from erro
        if not math.isfinite(numero):
            raise ValueError(f"O campo {nome} deve conter um número finito.")
        return numero

    def validar_parametros(self, mostrar_erro=True):
        try:
            y0 = self.ler_numero(self.var_y0, "altura inicial")
            v0 = self.ler_numero(self.var_v0, "velocidade inicial")
            ang = self.ler_numero(self.var_angulo, "ângulo")
            g = self.ler_numero(self.var_g, "gravidade")
            tmax = self.ler_numero(self.var_tmax, "tempo máximo")
            dt = self.ler_numero(self.var_dt, "passo Δt")
            ritmo = self.ler_numero(self.var_ritmo, "ritmo")
            intervalo = self.ler_numero(self.var_intervalo_discreto, "intervalo de coleta")
        except ValueError as erro:
            if mostrar_erro:
                messagebox.showerror("Erro nos parâmetros", str(erro))
            return False

        mensagens = []
        if y0 < 0:
            mensagens.append("A altura inicial h₀ não pode ser negativa.")
        if v0 < 0:
            mensagens.append("A velocidade inicial v₀ não pode ser negativa.")
        if g <= 0:
            mensagens.append("A gravidade deve ser maior que zero.")
        if not (-89.0 <= ang <= 89.0):
            mensagens.append("O ângulo deve ficar entre -89° e 89° para manter a visualização didática.")
        if tmax <= 0:
            mensagens.append("O tempo máximo deve ser maior que zero.")
        if not (DT_MIN <= dt <= DT_MAX):
            mensagens.append(f"O passo Δt deve ficar entre {DT_MIN:g} s e {DT_MAX:g} s.")
        if intervalo < INTERVALO_MIN:
            mensagens.append(f"O intervalo de coleta deve ser pelo menos {INTERVALO_MIN:g} s.")
        if not (RITMO_MIN <= ritmo <= RITMO_MAX):
            mensagens.append(f"O ritmo deve ficar entre {RITMO_MIN:g} e {RITMO_MAX:g}.")
        if mensagens:
            if mostrar_erro:
                messagebox.showerror("Parâmetros inválidos", "\n".join(mensagens))
            return False
        return True

    # -------------------------------------------------------------------------
    # FÍSICA
    # -------------------------------------------------------------------------
    def obter_config(self):
        y0 = max(self.ler_numero(self.var_y0, "altura inicial"), 0.0)
        v0 = max(self.ler_numero(self.var_v0, "velocidade inicial"), 0.0)
        ang = self.ler_numero(self.var_angulo, "ângulo")
        g = max(self.ler_numero(self.var_g, "gravidade"), 1e-6)
        tmax = max(self.ler_numero(self.var_tmax, "tempo máximo"), 0.01)
        dt = limitar(self.ler_numero(self.var_dt, "passo Δt"), DT_MIN, DT_MAX)
        ritmo = limitar(self.ler_numero(self.var_ritmo, "ritmo"), RITMO_MIN, RITMO_MAX)
        return y0, v0, ang, g, tmax, dt, ritmo

    def parametros_derivados(self):
        y0, v0, ang, g, tmax, dt, ritmo = self.obter_config()
        rad = math.radians(ang)
        vx0 = v0 * math.cos(rad)
        vy0 = v0 * math.sin(rad)
        disc = max(vy0 * vy0 + 2.0 * g * y0, 0.0)
        t_voo = (vy0 + math.sqrt(disc)) / g if g > 0 else tmax
        t_voo = max(t_voo, 0.0)
        hmax = y0 + (vy0 * vy0) / (2.0 * g) if vy0 > 0 else y0
        t_hmax = vy0 / g if vy0 > 0 else 0.0
        alcance = vx0 * t_voo
        tempo_simulacao = min(t_voo, tmax)
        return {
            "y0": y0,
            "v0": v0,
            "ang": ang,
            "g": g,
            "tmax": tmax,
            "dt": dt,
            "ritmo": ritmo,
            "vx0": vx0,
            "vy0": vy0,
            "t_voo": t_voo,
            "hmax": hmax,
            "t_hmax": t_hmax,
            "alcance": alcance,
            "tempo_simulacao": tempo_simulacao,
        }

    def fisica_em(self, tempo):
        p = self.parametros_derivados()
        t = max(0.0, min(float(tempo), p["t_voo"]))
        x = p["vx0"] * t
        y = p["y0"] + p["vy0"] * t - 0.5 * p["g"] * t * t
        if y < 0 and t >= p["t_voo"]:
            y = 0.0
        vx = p["vx0"]
        vy = p["vy0"] - p["g"] * t
        v = math.sqrt(vx * vx + vy * vy)
        return {
            "t": arredondar_fisico(t),
            "x": arredondar_fisico(x),
            "y": arredondar_fisico(max(y, 0.0)),
            "vx": arredondar_fisico(vx),
            "vy": arredondar_fisico(vy),
            "v": arredondar_fisico(v),
            "ay": arredondar_fisico(-p["g"]),
            "g": p["g"],
            "planeta": self.var_planeta.get(),
        }

    # -------------------------------------------------------------------------
    # CONTROLES DA SIMULAÇÃO
    # -------------------------------------------------------------------------
    def iniciar(self):
        if not self.validar_parametros(mostrar_erro=True):
            return
        if self.impacto:
            self.reiniciar_simulacao(limpar_tabela=True)
        self.rodando = True
        self.modo_comparacao = False
        self.ultimo_instante_loop = time.perf_counter()
        agora = self.ultimo_instante_loop
        self.ultimo_redesenho_grafico = agora
        self.ultimo_redesenho_tabela = agora
        self.var_status.set("Simulação contínua em andamento.")
        self.agendar_animacao()

    def pausar(self):
        self.rodando = False
        self.ultimo_instante_loop = None
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None
        self.var_status.set("Simulação pausada.")

    def passo(self):
        if not self.validar_parametros(mostrar_erro=True):
            return
        self.pausar()
        p = self.parametros_derivados()
        self.avancar(p["dt"])
        self.var_status.set("Avanço de um passo Δt realizado.")

    def agendar_animacao(self):
        if self.rodando:
            # Aproximadamente 60 FPS para movimento contínuo, sem sensação de pausa.
            self.after_id = self.root.after(16, self.loop_animacao)

    def loop_animacao(self):
        if not self.rodando:
            return
        try:
            p = self.parametros_derivados()
            agora = time.perf_counter()
            if self.ultimo_instante_loop is None:
                self.ultimo_instante_loop = agora
            dt_real = agora - self.ultimo_instante_loop
            self.ultimo_instante_loop = agora

            # Usa o tempo físico real entre quadros. O limite superior evita salto
            # grande caso o computador trave momentaneamente ou a janela seja movida.
            dt_real = max(0.001, min(dt_real, 0.040))
            incremento = dt_real * p["ritmo"]
            self.avancar(incremento, animacao=True)
        except Exception as erro:
            self.rodando = False
            self.ultimo_instante_loop = None
            messagebox.showerror("Erro durante a simulação", str(erro))
            return
        self.agendar_animacao()

    def avancar(self, incremento, animacao=False):
        p = self.parametros_derivados()
        t_novo = self.t + incremento
        if t_novo >= p["tempo_simulacao"]:
            t_novo = p["tempo_simulacao"]
            self.impacto = True
            self.rodando = False
            self.ultimo_instante_loop = None
            if p["tempo_simulacao"] < p["t_voo"] - 1e-9:
                self.var_status.set("Tempo máximo atingido. Simulação finalizada.")
            else:
                self.var_status.set("A bola atingiu o solo. Simulação finalizada.")
        self.t = arredondar_fisico(t_novo)
        self.registrar_ponto(forcar=(self.var_registro.get() == "Contínua"))

        if animacao:
            # Para manter o movimento contínuo, a cena é atualizada a cada quadro.
            # Gráficos e tabela são atualizados em frequência menor, evitando travas.
            self.desenhar_cena()
            self.atualizar_resultados()
            agora = time.perf_counter()
            if self.impacto or agora - self.ultimo_redesenho_grafico >= 0.12:
                self.desenhar_graficos()
                self.ultimo_redesenho_grafico = agora
            if self.impacto or agora - self.ultimo_redesenho_tabela >= 0.30:
                self.atualizar_tabela()
                self.ultimo_redesenho_tabela = agora
        else:
            self.atualizar_tudo()

    def reiniciar_simulacao(self, limpar_tabela=False):
        self.pausar()
        self.t = 0.0
        self.indice = 0
        self.impacto = False
        self.modo_comparacao = False
        self.proximo_t_discreto = 0.0
        self.ultimo_instante_loop = None
        agora = time.perf_counter()
        self.ultimo_redesenho_grafico = agora
        self.ultimo_redesenho_tabela = agora
        if limpar_tabela:
            self.dados = []
        self.registrar_ponto(forcar=True)
        self.var_status.set("Simulação reiniciada.")
        self.atualizar_tudo()

    def registrar_ponto_manual(self):
        if not self.validar_parametros(mostrar_erro=True):
            return
        self.registrar_ponto(forcar=True)
        self.var_status.set("Ponto experimental registrado manualmente.")
        self.atualizar_tabela()

    def registrar_ponto(self, forcar=False):
        tipo = self.var_registro.get()
        if not forcar:
            if tipo == "Manual":
                return
            if tipo == "Discreta" and self.t + 1e-9 < self.proximo_t_discreto:
                return

        estado = self.fisica_em(self.t)
        if self.dados and abs(self.dados[-1]["t"] - estado["t"]) < 1e-9 and not forcar:
            return
        self.indice += 1
        estado["n"] = self.indice
        self.dados.append(estado)
        if len(self.dados) > MAX_DADOS:
            self.dados = self.dados[-MAX_DADOS:]

        if tipo == "Discreta":
            intervalo = max(self.ler_numero(self.var_intervalo_discreto, "intervalo de coleta"), INTERVALO_MIN)
            self.proximo_t_discreto = self.t + intervalo

    def limpar_tabela(self):
        self.dados = []
        self.indice = 0
        self.proximo_t_discreto = 0.0
        self.registrar_ponto(forcar=True)
        self.var_status.set("Tabela limpa.")
        self.atualizar_tabela()

    def aplicar_preset(self, n):
        self._suprimir_eventos = True
        try:
            if n == 1:
                valores = ("Terra", "12.0", "14.0", "35.0", "9.81", "5.0")
            elif n == 2:
                valores = ("Terra", "20.0", "28.0", "45.0", "9.81", "8.0")
            else:
                valores = ("Lua", "10.0", "18.0", "45.0", "1.62", "20.0")
            variaveis = (
                self.var_planeta, self.var_y0, self.var_v0,
                self.var_angulo, self.var_g, self.var_tmax,
            )
            for variavel, valor in zip(variaveis, valores):
                variavel.set(valor)
        finally:
            self._suprimir_eventos = False
        self.reiniciar_simulacao(limpar_tabela=True)

    # -------------------------------------------------------------------------
    # TABELA
    # -------------------------------------------------------------------------
    def obter_colunas_tabela(self):
        tipo = self.var_tipo_tabela.get()
        if tipo == "Posição horizontal × Tempo":
            return ["Tempo", "x"]
        if tipo == "Velocidade vertical × Tempo":
            return ["Tempo", "vy"]
        if tipo == "Tabela completa: t, x, y, vx, vy":
            return ["Tempo", "x", "y", "vx", "vy"]
        if tipo == "Resultados do lançamento":
            return ["Tempo", "x", "y", "v"]
        return ["Tempo", "y"]

    def aplicar_configuracao_tabela(self):
        if not hasattr(self, "tabela"):
            return
        selecionadas = self.obter_colunas_tabela()
        colunas = ["n"] + [self.mapa_grandezas_tabela[g]["chave"] for g in selecionadas]
        self.tabela.configure(columns=colunas)
        self.tabela.heading("n", text="#")
        self.tabela.column("n", width=30, anchor="center", stretch=False)
        for grandeza in selecionadas:
            meta = self.mapa_grandezas_tabela[grandeza]
            chave = meta["chave"]
            self.tabela.heading(chave, text=meta["titulo"])
            self.tabela.column(chave, width=meta["largura"], anchor="center", stretch=False)
        tipo = self.var_tipo_tabela.get()
        if tipo == "Posição horizontal × Tempo":
            self.var_descricao_tabela.set("Tabela ativa: x em função do tempo.")
        elif tipo == "Velocidade vertical × Tempo":
            self.var_descricao_tabela.set("Tabela ativa: vy em função do tempo.")
        elif tipo == "Tabela completa: t, x, y, vx, vy":
            self.var_descricao_tabela.set("Tabela ativa: t, x, y, vx e vy.")
        elif tipo == "Resultados do lançamento":
            self.var_descricao_tabela.set("Tabela ativa: dados principais do lançamento.")
        else:
            self.var_descricao_tabela.set("Tabela ativa: y em função do tempo.")
        self.atualizar_tabela()

    def atualizar_tabela(self):
        if not hasattr(self, "tabela"):
            return
        for item in self.tabela.get_children():
            self.tabela.delete(item)
        colunas = self.obter_colunas_tabela()
        for d in self.dados[-300:]:
            valores = [d.get("n", "")]
            for g in colunas:
                meta = self.mapa_grandezas_tabela[g]
                valores.append(formato_numero(d.get(meta["chave"], 0.0), meta["casas"]))
            self.tabela.insert("", "end", values=valores)

    # -------------------------------------------------------------------------
    # DESENHO DA CENA E GRÁFICOS
    # -------------------------------------------------------------------------
    def atualizar_tudo(self):
        self.desenhar_cena()
        self.desenhar_graficos()
        self.atualizar_tabela()
        self.atualizar_resultados()

    def atualizar_resultados(self):
        p = self.parametros_derivados()
        texto = (
            f"T voo: {formato_numero(p['t_voo'], 3)} s\n"
            f"Alcance: {formato_numero(p['alcance'], 3)} m\n"
            f"Altura máx.: {formato_numero(p['hmax'], 3)} m\n"
            f"t(hmáx): {formato_numero(p['t_hmax'], 3)} s"
        )
        self.var_resultados.set(texto)

    def amostras_trajetoria(self, ate_t=None, n=350):
        p = self.parametros_derivados()
        fim = p["t_voo"] if ate_t is None else max(0.0, min(ate_t, p["t_voo"]))
        if fim <= 0:
            ts = np.array([0.0])
        else:
            ts = np.linspace(0.0, fim, max(2, n))
        xs = p["vx0"] * ts
        ys = p["y0"] + p["vy0"] * ts - 0.5 * p["g"] * ts * ts
        ys = np.maximum(ys, 0.0)
        return ts, xs, ys

    def desenhar_cena(self):
        ax = self.ax_cena
        ax.clear()
        p = self.parametros_derivados()
        estado = self.fisica_em(self.t)
        ts_total, xs_total, ys_total = self.amostras_trajetoria(n=400)
        ts_atual, xs_atual, ys_atual = self.amostras_trajetoria(ate_t=self.t, n=180)

        max_x = max(float(np.max(xs_total)) if len(xs_total) else 10.0, p["alcance"], 10.0)
        max_y = max(float(np.max(ys_total)) if len(ys_total) else 10.0, p["hmax"], p["y0"], 10.0)
        ax.set_xlim(-0.08 * max_x - 1.5, max_x * 1.10 + 2.0)
        ax.set_ylim(-0.10 * max_y - 1.0, max_y * 1.25 + 2.0)
        ax.set_title("Simulação experimental — lançamento parabólico", fontsize=11, fontweight="bold")
        ax.set_facecolor(COR_CENA)
        if self.var_mostrar_grade.get():
            ax.grid(True, color="#67e8f9", linestyle="--", linewidth=0.65, alpha=0.50)
        else:
            ax.grid(False)

        # Solo
        ax.axhline(0, color="#15803d", linewidth=2.2)
        ax.add_patch(Rectangle((ax.get_xlim()[0], ax.get_ylim()[0]), ax.get_xlim()[1] - ax.get_xlim()[0], -ax.get_ylim()[0],
                               facecolor="#86efac", edgecolor="none", alpha=0.62, zorder=0))

        # Prédio/canhão simplificado
        if self.var_mostrar_cenario.get():
            largura_predio = max(1.2, 0.045 * max_x)
            ax.add_patch(Rectangle((-largura_predio, 0), largura_predio, p["y0"],
                                   facecolor="#6366f1", edgecolor="#312e81", linewidth=1.3, zorder=2))
            for h in np.linspace(0, p["y0"], 6)[1:-1]:
                ax.plot([-largura_predio, 0], [h, h], color="#c7d2fe", linewidth=0.8, alpha=0.85, zorder=3)
            ax.add_patch(Wedge((-0.25 * largura_predio, p["y0"]), 0.45 * largura_predio, 0, 180,
                               facecolor=COR_LARANJA, edgecolor="#9a3412", zorder=4))
            rad = math.radians(p["ang"])
            tubo_len = max(1.1, 0.08 * max_x)
            x0, y0 = 0.0, p["y0"]
            x1 = x0 + tubo_len * math.cos(rad)
            y1 = y0 + tubo_len * math.sin(rad)
            ax.plot([x0, x1], [y0, y1], color="#7c2d12", linewidth=6.0, solid_capstyle="round", zorder=5)
            ax.plot([x0, x1], [y0, y1], color="#fb923c", linewidth=3.0, solid_capstyle="round", zorder=6)

        if self.var_mostrar_trajetoria.get():
            ax.plot(xs_total, ys_total, color=COR_ROXO, linewidth=1.4, linestyle="--", alpha=0.78, label="Trajetória prevista")
            ax.plot(xs_atual, ys_atual, color=COR_CIANO, linewidth=2.8, label="Trajetória percorrida")

        raio_bola = max(0.18, 0.013 * max(max_x, max_y))
        ax.add_patch(Circle(
            (estado["x"], estado["y"]),
            radius=1.65 * raio_bola,
            facecolor=COR_AMARELO,
            edgecolor="none",
            alpha=0.30,
            zorder=7,
        ))
        bola = Circle((estado["x"], estado["y"]), radius=raio_bola,
                      facecolor=COR_VERMELHO, edgecolor="#881337", linewidth=1.4, zorder=8)
        ax.add_patch(bola)

        # Vetores velocidade e aceleração
        if self.var_mostrar_vetores.get():
            escala_v = 0.035 * max(max_x, max_y) / max(p["v0"], 1.0)
            escala_a = 0.050 * max(max_x, max_y) / max(p["g"], 1.0)
            x, y = estado["x"], estado["y"]
            vx, vy = estado["vx"], estado["vy"]
            ax.add_patch(FancyArrowPatch((x, y), (x + vx * escala_v, y + vy * escala_v),
                                         arrowstyle="->", mutation_scale=13, linewidth=2.2, color=COR_LARANJA, zorder=9))
            ax.text(x + vx * escala_v, y + vy * escala_v, "v", color=COR_LARANJA, fontsize=10, fontweight="bold")
            ax.add_patch(FancyArrowPatch((x + 0.5, y), (x + 0.5, y - p["g"] * escala_a),
                                         arrowstyle="->", mutation_scale=13, linewidth=2.2, color=COR_VERDE, zorder=9))
            ax.text(x + 0.65, y - p["g"] * escala_a, "g", color="#15803d", fontsize=10, fontweight="bold")

        # Pontos especiais
        x_hmax = p["vx0"] * p["t_hmax"]
        ax.scatter([p["alcance"]], [0], color=COR_LARANJA, edgecolor="white", linewidth=0.8, s=42, zorder=7)
        ax.scatter([x_hmax], [p["hmax"]], color=COR_MAGENTA, edgecolor="white", linewidth=0.8, s=42, zorder=7)
        ax.annotate("alcance", (p["alcance"], 0), xytext=(0, 9), textcoords="offset points",
                    ha="center", fontsize=7, color="#9a3412", fontweight="bold")
        ax.annotate("altura máxima", (x_hmax, p["hmax"]), xytext=(0, 9), textcoords="offset points",
                    ha="center", fontsize=7, color="#86198f", fontweight="bold")

        ax.set_xlabel("x (m)", fontsize=8)
        ax.set_ylabel("y (m)", fontsize=8)
        ax.tick_params(labelsize=7, colors=COR_TEXTO_SECUNDARIO)
        for spine in ax.spines.values():
            spine.set_color("#0891b2")
            spine.set_linewidth(0.8)
        if self.var_mostrar_trajetoria.get():
            legenda = ax.legend(loc="upper right", fontsize=7, frameon=True)
            legenda.get_frame().set_facecolor("white")
            legenda.get_frame().set_edgecolor(COR_CIANO)
            legenda.get_frame().set_alpha(0.94)
        self.fig_cena.tight_layout(pad=1.0)
        self.canvas_cena.draw_idle()

    def dados_para_grafico(self):
        if self.dados:
            fonte = self.dados
        else:
            p = self.parametros_derivados()
            ts = np.linspace(0, max(p["t_voo"], 0.001), 120)
            fonte = [self.fisica_em(t) for t in ts]
        return {
            "t": np.asarray([d["t"] for d in fonte], dtype=float),
            "x": np.asarray([d["x"] for d in fonte], dtype=float),
            "y": np.asarray([d["y"] for d in fonte], dtype=float),
            "vx": np.asarray([d["vx"] for d in fonte], dtype=float),
            "vy": np.asarray([d["vy"] for d in fonte], dtype=float),
            "v": np.asarray([d["v"] for d in fonte], dtype=float),
            "ay": np.asarray([d["ay"] for d in fonte], dtype=float),
        }

    def desenhar_graficos(self):
        self.fig_graficos.clear()
        escolha = self.var_grafico.get()
        if escolha == "Ocultar":
            self.lbl_nota_grafico.config(text="Gráficos ocultos.")
            self.canvas_graficos.draw_idle()
            return

        dados = self.dados_para_grafico()
        graficos = [
            ("x", "x(t)", "x (m)", CORES_GRAFICOS["x"]),
            ("y", "y(t)", "y (m)", CORES_GRAFICOS["y"]),
            ("vx", "vx(t)", "vx (m/s)", CORES_GRAFICOS["vx"]),
            ("vy", "vy(t)", "vy (m/s)", CORES_GRAFICOS["vy"]),
            ("v", "v(t)", "v (m/s)", CORES_GRAFICOS["v"]),
            ("ay", "ay(t)", "ay (m/s²)", CORES_GRAFICOS["ay"]),
        ]
        if escolha != "Todos":
            chave = escolha.replace("(t)", "")
            graficos = [g for g in graficos if g[0] == chave]
        quantidade = len(graficos)
        self.lbl_nota_grafico.config(text="Mostrando " + (", ".join(g[1] for g in graficos) if graficos else "nenhum gráfico") + ".")

        if quantidade == 1:
            axes = [self.fig_graficos.add_subplot(111)]
        elif quantidade == 2:
            axes = [self.fig_graficos.add_subplot(121), self.fig_graficos.add_subplot(122)]
        else:
            if quantidade <= 3:
                linhas, cols = 1, quantidade
            elif quantidade <= 4:
                linhas, cols = 2, 2
            else:
                linhas, cols = 2, 3
            axes = [self.fig_graficos.add_subplot(linhas, cols, i + 1) for i in range(quantidade)]

        for indice, (ax, (chave, titulo, ylabel, cor)) in enumerate(zip(axes, graficos)):
            ax.set_facecolor(COR_GRAFICO)
            ax.plot(dados["t"], dados[chave], color=cor, linewidth=2.2)
            if len(dados["t"]):
                ax.scatter([dados["t"][-1]], [dados[chave][-1]], color=cor, s=16, zorder=4)
            ax.set_title(titulo, fontsize=9, fontweight="bold")
            mostrar_eixo_x = quantidade <= 3 or indice >= cols
            ax.set_xlabel("t (s)" if mostrar_eixo_x else "", fontsize=8)
            ax.set_ylabel(ylabel, fontsize=8)
            ax.tick_params(labelsize=7, colors=COR_TEXTO_SECUNDARIO)
            ax.grid(True, color=COR_GRADE, linestyle="--", linewidth=0.55, alpha=0.38)
            ax.xaxis.set_minor_locator(AutoMinorLocator())
            ax.yaxis.set_minor_locator(AutoMinorLocator())
            ymin, ymax = nice_limits(dados[chave])
            ax.set_ylim(ymin, ymax)
            for spine in ax.spines.values():
                spine.set_color(cor)
                spine.set_linewidth(0.8)

        self.fig_graficos.tight_layout(pad=0.95)
        self.canvas_graficos.draw_idle()

    # -------------------------------------------------------------------------
    # COMPARAÇÃO PLANETÁRIA
    # -------------------------------------------------------------------------
    def comparar_planetas(self):
        if not self.validar_parametros(mostrar_erro=True):
            return
        self.pausar()
        self.modo_comparacao = True
        ax = self.ax_cena
        ax.clear()
        y0, v0, ang, g_atual, tmax, dt, ritmo = self.obter_config()
        rad = math.radians(ang)
        vx0 = v0 * math.cos(rad)
        vy0 = v0 * math.sin(rad)
        max_x, max_y = 10.0, max(10.0, y0)
        trajetorias = []
        for nome, g in self.gravidades_planetas.items():
            disc = max(vy0 * vy0 + 2.0 * g * y0, 0.0)
            t_voo = (vy0 + math.sqrt(disc)) / g
            ts = np.linspace(0, t_voo, 240)
            xs = vx0 * ts
            ys = np.maximum(y0 + vy0 * ts - 0.5 * g * ts * ts, 0.0)
            trajetorias.append((nome, xs, ys, t_voo))
            max_x = max(max_x, float(np.max(xs)))
            max_y = max(max_y, float(np.max(ys)))

        ax.set_title("Comparação planetária — mesma velocidade e ângulo", fontsize=11, fontweight="bold")
        ax.set_facecolor(COR_CENA)
        ax.axhline(0, color="#15803d", linewidth=2.2)
        ax.set_xlim(-1, max_x * 1.10 + 2)
        ax.set_ylim(-1, max_y * 1.20 + 2)
        ax.grid(True, color="#67e8f9", linestyle="--", linewidth=0.6, alpha=0.48)
        ax.add_patch(Rectangle((-1, -1), max_x * 1.10 + 3, 1,
                               facecolor="#86efac", edgecolor="none", alpha=0.62, zorder=0))
        planeta_atual = self.var_planeta.get()
        for indice, (nome, xs, ys, t_voo) in enumerate(trajetorias):
            destaque = nome == planeta_atual
            ax.plot(
                xs,
                ys,
                color=CORES_PLANETAS[indice % len(CORES_PLANETAS)],
                linewidth=2.8 if destaque else 1.7,
                alpha=1.0 if destaque else 0.82,
                label=f"{nome} ({t_voo:.1f}s)",
            )
        ax.set_xlabel("x (m)", fontsize=8)
        ax.set_ylabel("y (m)", fontsize=8)
        ax.tick_params(labelsize=7, colors=COR_TEXTO_SECUNDARIO)
        for spine in ax.spines.values():
            spine.set_color("#0891b2")
            spine.set_linewidth(0.8)
        legenda = ax.legend(loc="upper right", fontsize=6, ncol=2, frameon=True)
        legenda.get_frame().set_facecolor("white")
        legenda.get_frame().set_edgecolor(COR_ROXO)
        legenda.get_frame().set_alpha(0.94)
        self.fig_cena.tight_layout(pad=1.0)
        self.canvas_cena.draw_idle()

        self.var_status.set("Comparação planetária exibida na cena experimental.")
        self.desenhar_graficos()

    # -------------------------------------------------------------------------
    # EXPORTAÇÃO
    # -------------------------------------------------------------------------
    def exportar_csv(self):
        if not self.dados:
            messagebox.showinfo("Sem dados", "Não há dados para exportar.")
            return
        caminho = filedialog.asksaveasfilename(
            title="Salvar dados em CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"movimento_parabolico_{datetime.now():%Y%m%d_%H%M}.csv"
        )
        if not caminho:
            return
        colunas = ["n", "planeta", "t", "x", "y", "vx", "vy", "v", "ay", "g"]
        p = self.parametros_derivados()
        try:
            with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
                metadados = csv.writer(f, delimiter=";")
                metadados.writerow([NOME_APLICATIVO, f"versão {VERSAO_APLICATIVO}"])
                metadados.writerow(["Gerado em", datetime.now().strftime("%d/%m/%Y %H:%M:%S")])
                metadados.writerow(["Planeta", self.var_planeta.get(), "g (m/s²)", formato_numero(p["g"], 4)])
                metadados.writerow(["h₀ (m)", formato_numero(p["y0"], 4), "v₀ (m/s)", formato_numero(p["v0"], 4)])
                metadados.writerow(["Ângulo (°)", formato_numero(p["ang"], 4), "Registros", len(self.dados)])
                metadados.writerow([])
                writer = csv.DictWriter(f, fieldnames=colunas, delimiter=";")
                writer.writeheader()
                for dado in self.dados:
                    writer.writerow({chave: dado.get(chave, "") for chave in colunas})
            self.var_status.set("Dados exportados em CSV com metadados.")
            messagebox.showinfo("Exportação concluída", "Arquivo CSV salvo com sucesso.")
        except OSError as erro:
            messagebox.showerror("Erro ao exportar CSV", str(erro))

    def exportar_relatorio(self):
        p = self.parametros_derivados()
        caminho = filedialog.asksaveasfilename(
            title="Salvar relatório TXT",
            defaultextension=".txt",
            filetypes=[("Texto", "*.txt")],
            initialfile=f"relatorio_movimento_parabolico_{datetime.now():%Y%m%d_%H%M}.txt"
        )
        if not caminho:
            return
        texto = f"""{NOME_APLICATIVO.upper()}
Versão: {VERSAO_APLICATIVO}
Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}

Parâmetros:
Planeta/ambiente: {self.var_planeta.get()}
Altura inicial h0: {p['y0']:.4f} m
Velocidade inicial v0: {p['v0']:.4f} m/s
Ângulo: {p['ang']:.4f} graus
Gravidade: {p['g']:.4f} m/s²
Tempo máximo configurado: {p['tmax']:.4f} s
Passo numérico: {p['dt']:.4f} s
Modo de coleta: {self.var_registro.get()}
Pontos registrados: {len(self.dados)}

Resultados:
Tempo de voo: {p['t_voo']:.4f} s
Alcance horizontal: {p['alcance']:.4f} m
Altura máxima: {p['hmax']:.4f} m
Tempo até altura máxima: {p['t_hmax']:.4f} s

Equações usadas:
x(t) = v0 cos(theta) t
y(t) = h0 + v0 sin(theta) t - 1/2 g t²
vx(t) = v0 cos(theta)
vy(t) = v0 sin(theta) - g t
"""
        try:
            with open(caminho, "w", encoding="utf-8") as f:
                f.write(texto)
            self.var_status.set("Relatório exportado em TXT.")
            messagebox.showinfo("Exportação concluída", "Relatório TXT salvo com sucesso.")
        except OSError as erro:
            messagebox.showerror("Erro ao exportar relatório", str(erro))

    def exportar_roteiro_pre_pos_teste(self):
        nome = f"roteiro_pre_pos_teste_movimento_parabolico_{datetime.now():%Y%m%d_%H%M%S}.txt"
        caminho = filedialog.asksaveasfilename(
            title="Salvar roteiro de pré-teste e pós-teste",
            defaultextension=".txt",
            filetypes=[("Roteiro de texto", "*.txt"), ("Todos os arquivos", "*.*")],
            initialfile=nome,
        )
        if not caminho:
            return
        try:
            with open(caminho, "w", encoding="utf-8-sig") as f:
                f.write(self.gerar_roteiro_pre_pos_teste())
            self.var_status.set("Roteiro de pré-teste e pós-teste exportado.")
            messagebox.showinfo("Exportação concluída", "Roteiro Pré/Pós salvo com sucesso.")
        except OSError as erro:
            messagebox.showerror("Erro ao exportar Pré/Pós", str(erro))

    def gerar_roteiro_pre_pos_teste(self):
        try:
            p = self.parametros_derivados()
            configuracao = (
                f"planeta {self.var_planeta.get()}, h₀ = {formato_numero(p['y0'], 2)} m, "
                f"v₀ = {formato_numero(p['v0'], 2)} m/s e θ = {formato_numero(p['ang'], 1)}°"
            )
        except Exception:
            configuracao = "planeta Terra, h₀ = 20,00 m, v₀ = 25,00 m/s e θ = 40,0°"

        return f"""ROTEIRO DE PRÉ-TESTE E PÓS-TESTE - MOVIMENTO PARABÓLICO
{'=' * 72}
Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
Aplicação: {NOME_APLICATIVO} - versão {VERSAO_APLICATIVO}

Aluno(a): ___________________________________  Turma: ______________
Professor(a): ________________________________  Data: ____/____/______

OBJETIVOS DE APRENDIZAGEM
- Decompor a velocidade inicial nas componentes horizontal e vertical.
- Interpretar x(t), y(t), vx(t) e vy(t) no lançamento oblíquo.
- Relacionar ângulo, gravidade, altura inicial, alcance e tempo de voo.
- Comparar previsões teóricas, gráficos e dados produzidos pelo simulador.

PRÉ-TESTE
Responda antes de executar o laboratório.

1. Em um lançamento sem resistência do ar, qual componente da velocidade permanece constante? Justifique.
2. Qual é a direção e o sentido da aceleração durante todo o movimento?
3. O que acontece com a velocidade vertical no ponto de altura máxima?
4. Para lançamentos no mesmo nível e com a mesma rapidez, qual ângulo costuma produzir o maior alcance?
5. A massa do projétil altera a trajetória ideal? Explique.
6. Como uma gravidade menor afeta o tempo de voo e o alcance horizontal?
7. Desenhe a forma esperada dos gráficos x(t), y(t), vx(t) e vy(t).
8. Escreva as componentes iniciais vx₀ e vy₀ em função de v₀ e θ.

HIPÓTESES
Preencha antes da simulação usando: {configuracao}.

Ângulo; tempo de voo previsto; alcance previsto; altura máxima prevista
30°; ____________________; ____________________; ____________________
45°; ____________________; ____________________; ____________________
60°; ____________________; ____________________; ____________________

ATIVIDADE COM O LABORATÓRIO

Etapa A - Lançamento de referência
1. Aplique a configuração sugerida acima e selecione o registro contínuo.
2. Inicie a simulação e observe simultaneamente a trajetória, os vetores e os gráficos.
3. Registre tempo de voo, alcance, altura máxima e tempo até a altura máxima.
4. Verifique nos gráficos se vx permanece constante e se vy varia linearmente.

Etapa B - Influência do ângulo
1. Mantenha planeta, altura inicial e rapidez constantes.
2. Execute lançamentos com 30°, 45° e 60°.
3. Complete a tabela e compare os ângulos complementares 30° e 60°.

Ângulo; tempo de voo (s); alcance (m); altura máxima (m); t da altura máxima (s)
30°; ______________; ______________; ______________; ______________
45°; ______________; ______________; ______________; ______________
60°; ______________; ______________; ______________; ______________

Etapa C - Comparação planetária
1. Use o botão Comparar mantendo h₀, v₀ e θ constantes.
2. Compare Terra, Lua, Marte e Júpiter.
3. Ordene os ambientes do menor para o maior alcance.
4. Explique a relação observada entre gravidade e curvatura da trajetória.

Planeta; g (m/s²); tempo de voo (s); alcance (m); altura máxima (m)
Terra; 9,81; ______________; ______________; ______________
Lua; 1,62; ______________; ______________; ______________
Marte; 3,71; ______________; ______________; ______________
Júpiter; 24,79; ______________; ______________; ______________

Etapa D - Análise dos dados
1. Selecione cada modo gráfico e relacione sua forma às equações do movimento.
2. Use a tabela completa para conferir um instante antes, durante e depois da altura máxima.
3. Exporte o CSV e compare um ponto calculado manualmente com o simulador.

PÓS-TESTE
Responda após concluir a atividade.

1. Por que a trajetória é parabólica quando a resistência do ar é desprezada?
2. Explique por que vx é constante, mas o módulo da velocidade não é.
3. Como o gráfico vy(t) permite identificar o instante de altura máxima?
4. O ângulo de 45° sempre fornece o maior alcance? Considere uma altura inicial diferente de zero.
5. Compare Ec qualitativamente no lançamento, na altura máxima e imediatamente antes do impacto.
6. Por que o projétil permanece mais tempo no ar em ambientes de menor gravidade?
7. Cite duas limitações do modelo ideal usado no laboratório.
8. Use evidências da tabela ou dos gráficos para explicar uma hipótese que foi confirmada ou rejeitada.

SÍNTESE FINAL
Complete em três a cinco linhas:
O movimento horizontal é ________________________________________________
________________________________________________________________________
O movimento vertical é __________________________________________________
________________________________________________________________________
A principal evidência observada foi ______________________________________
________________________________________________________________________

CRITÉRIOS DE ANÁLISE
- Compreensão das componentes e da aceleração: 4 pontos.
- Interpretação de gráficos e tabelas: 3 pontos.
- Comparação entre ângulos e planetas: 2 pontos.
- Clareza da síntese final: 1 ponto.
"""

    def fechar(self):
        self.pausar()
        self.root.destroy()


def executar():
    root = tk.Tk()
    app = LaboratorioMovimentoParabolico(root)
    root.mainloop()


if __name__ == "__main__":
    executar()
