# -*- coding: utf-8 -*-
"""
LABORATÓRIO VIRTUAL OFFLINE: Conservação da Energia Mecânica — Tkinter + Matplotlib

Versão reestruturada no mesmo formato visual e operacional do arquivo
LAB_MRU_MRUV(12).py: aplicação Python nativa, sem navegador, sem servidor local,
com painel compacto, cena experimental, gráficos, tabela vertical e exportação.

Autor: Mario Omar Calla Salcedo / Mestrado em Ensino Profissional em Física

Como executar:
    python 05_conservacao_energia_mecanica.py

Recursos principais:
- Simulação animada de um carrinho em pista com montanhas decrescentes, rampa ou vale.
- Conservação da energia mecânica total sem atrito: Em = Ep + Ec aproximadamente constante.
- Modo com atrito para visualizar dissipação de energia mecânica.
- Cena experimental com carrinho, pista, escala, vetor velocidade e indicação de altura.
- Gráficos em tempo real de h(t), v(t), x(t), Ep(t), Ec(t), Em(t) e Ed(t).
- Tabela experimental compacta com seleção da grandeza registrada.
- Ajuste de curva opcional para o gráfico escolhido, com equação e R².
- Exportação CSV, relatório TXT e roteiro de pré-teste/pós-teste.
- Interface compacta para manter controles, animação, gráficos e tabela visíveis.
"""

import csv
import math
import time
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch
from matplotlib.transforms import Affine2D
from matplotlib.ticker import AutoMinorLocator


# Identidade da aplicação e paleta científica de alto contraste.
NOME_APLICATIVO = "Laboratório Virtual — Conservação da Energia Mecânica"
VERSAO_APLICATIVO = "2.1"
AUTOR = "Mario Omar Calla Salcedo"

COR_FUNDO = "#181426"
COR_PAINEL = "#232036"
COR_GRUPO = "#302b46"
COR_TEXTO = "#f8fafc"
COR_TEXTO_SUAVE = "#cbd5e1"
COR_CARD = "#f8fafc"
COR_CENA = "#ecfeff"
COR_GRADE = "#cbd5e1"
COR_AZUL = "#0ea5e9"
COR_CIANO = "#06b6d4"
COR_VERDE = "#22c55e"
COR_LARANJA = "#f97316"
COR_VERMELHO = "#f43f5e"
COR_MAGENTA = "#d946ef"
COR_ROXO = "#8b5cf6"
COR_AMARELO = "#facc15"

DT_MIN = 0.001
DT_MAX = 0.05
RITMO_MIN = 0.5
RITMO_MAX = 8.0
MAX_DADOS = 12000
INTERVALO_GRAFICO = 0.12
INTERVALO_TABELA = 0.25


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def clamp(valor, minimo, maximo):
    """Limita um valor ao intervalo [mínimo, máximo]."""
    return max(minimo, min(maximo, valor))


def formato_numero(valor, casas=3):
    """Formata número com vírgula decimal e arredondamento físico."""
    try:
        valor = float(valor)
        if not math.isfinite(valor):
            return "—"
        quantizador = Decimal("1").scaleb(-int(casas))
        numero = Decimal(str(valor)).quantize(quantizador, rounding=ROUND_HALF_UP)
        return f"{numero:.{int(casas)}f}".replace(".", ",")
    except (TypeError, ValueError, ArithmeticError):
        return str(valor)


def converter_numero(valor):
    """Aceita ponto ou vírgula decimal e rejeita valores não finitos."""
    texto = str(valor).strip().replace(" ", "").replace(",", ".")
    numero = float(texto)
    if not math.isfinite(numero):
        raise ValueError("O valor deve ser um número finito.")
    return numero


def media(valores):
    filtrados = [float(v) for v in valores if isinstance(v, (int, float, np.floating)) and math.isfinite(float(v))]
    return sum(filtrados) / len(filtrados) if filtrados else float("nan")


def erro_percentual(valor, referencia):
    referencia = float(referencia)
    if abs(referencia) < 1e-12:
        return 0.0
    return 100.0 * abs(float(valor) - referencia) / abs(referencia)


# =============================================================================
# CLASSE PRINCIPAL DA APLICAÇÃO
# =============================================================================

class LaboratorioConservacaoEnergia:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{NOME_APLICATIVO} | v{VERSAO_APLICATIVO}")
        self.root.geometry("1366x720")
        self.root.minsize(1100, 650)

        # Estado físico
        self.L = 10.0
        self.t = 0.0
        self.x = 0.0
        self.vx = 0.0
        self.E0 = 1.0
        self.rodando = False
        self.finalizado = False
        self.after_id = None
        self.sentido_preferencial = 1.0
        self.contador_tabela = 0
        self._suprimir_eventos = False
        self._ultimo_redesenho_grafico = 0.0
        self._ultima_atualizacao_tabela = 0.0

        # Históricos experimentais
        self.t_hist = []
        self.x_hist = []
        self.h_hist = []
        self.v_hist = []
        self.Ep_hist = []
        self.Ec_hist = []
        self.Em_hist = []
        self.Ed_hist = []
        self.erro_hist = []

        # Variáveis Tkinter
        self.var_massa = tk.StringVar(value="1,00")
        self.var_altura = tk.StringVar(value="2,70")
        self.var_g = tk.StringVar(value="9,81")
        self.var_v0 = tk.StringVar(value="0,00")
        self.var_b = tk.StringVar(value="0,12")
        self.var_dt = tk.StringVar(value="0,01")
        self.var_ritmo = tk.StringVar(value="2,00")
        self.var_atrito = tk.BooleanVar(value=False)
        self.var_ajuste = tk.BooleanVar(value=False)
        self.var_percurso = tk.StringVar(value="Montanhas decrescentes")
        self.var_grafico = tk.StringVar(value="Todos")
        self.var_tabela = tk.StringVar(value="Energia mecânica")
        self.var_modelo_ajuste = tk.StringVar(value="Linear")
        self.var_status = tk.StringVar(value="Pronto para iniciar.")
        self.var_descricao_tabela = tk.StringVar(value="Tabela ativa: Em e erro percentual em relação a Em inicial.")

        # Leituras rápidas
        self.var_leitura_t = tk.StringVar(value="0,000 s")
        self.var_leitura_x = tk.StringVar(value="0,000 m")
        self.var_leitura_h = tk.StringVar(value="0,000 m")
        self.var_leitura_v = tk.StringVar(value="0,000 m/s")
        self.var_leitura_Em = tk.StringVar(value="0,000 J")
        self.var_leitura_erro = tk.StringVar(value="0,000 %")

        self.opcoes_tabela = [
            "Energia completa",
            "Altura × Tempo",
            "Velocidade × Tempo",
            "Posição × Tempo",
            "Energia mecânica",
            "Energia dissipada",
        ]

        self.mapa_tabela = {
            "Tempo": {"chave": "t", "titulo": "t", "csv": "tempo_s", "casas": 3, "largura": 58},
            "Posição": {"chave": "x", "titulo": "x", "csv": "posicao_m", "casas": 3, "largura": 58},
            "Altura": {"chave": "h", "titulo": "h", "csv": "altura_m", "casas": 3, "largura": 58},
            "Velocidade": {"chave": "v", "titulo": "v", "csv": "velocidade_m_s", "casas": 3, "largura": 66},
            "Energia potencial": {"chave": "Ep", "titulo": "Ep", "csv": "energia_potencial_J", "casas": 3, "largura": 62},
            "Energia cinética": {"chave": "Ec", "titulo": "Ec", "csv": "energia_cinetica_J", "casas": 3, "largura": 62},
            "Energia mecânica": {"chave": "Em", "titulo": "Em", "csv": "energia_mecanica_J", "casas": 3, "largura": 62},
            "Energia dissipada": {"chave": "Ed", "titulo": "Ed", "csv": "energia_dissipada_J", "casas": 3, "largura": 62},
            "Erro percentual": {"chave": "erro", "titulo": "%", "csv": "erro_percentual_Em", "casas": 4, "largura": 58},
        }

        self.recalcular_perfil_base()
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
        except tk.TclError:
            pass

        estilo.configure("TFrame", background=COR_FUNDO)
        estilo.configure("Panel.TFrame", background=COR_PAINEL, relief="flat")
        estilo.configure("Card.TFrame", background=COR_CARD, relief="flat")
        estilo.configure("TLabel", background=COR_PAINEL, foreground=COR_TEXTO, font=("Segoe UI", 8))
        estilo.configure("Title.TLabel", background=COR_FUNDO, foreground=COR_TEXTO, font=("Segoe UI Semibold", 14))
        estilo.configure("SubTitle.TLabel", background=COR_FUNDO, foreground=COR_TEXTO_SUAVE, font=("Segoe UI", 8))
        estilo.configure("TButton", font=("Segoe UI Semibold", 7), padding=(5, 3), borderwidth=0)
        botoes = {
            "Accent.TButton": (COR_AZUL, "#0284c7"),
            "Success.TButton": (COR_VERDE, "#16a34a"),
            "Warning.TButton": (COR_LARANJA, "#ea580c"),
            "Danger.TButton": (COR_VERMELHO, "#e11d48"),
        }
        for nome, (normal, ativo) in botoes.items():
            estilo.configure(nome, foreground="#ffffff", background=normal, font=("Segoe UI Semibold", 7), padding=(5, 3))
            estilo.map(nome, background=[("pressed", ativo), ("active", ativo)])
        estilo.configure("TEntry", fieldbackground="#151225", foreground=COR_TEXTO, insertcolor=COR_AMARELO,
                         bordercolor="#64748b", lightcolor="#64748b", darkcolor="#64748b")
        estilo.configure("TCombobox", fieldbackground="#151225", background="#151225", foreground=COR_TEXTO,
                         arrowcolor=COR_CIANO, bordercolor="#64748b", lightcolor="#64748b", darkcolor="#64748b")
        estilo.map("TCombobox", fieldbackground=[("readonly", "#151225")], foreground=[("readonly", COR_TEXTO)],
                   selectbackground=[("readonly", COR_ROXO)])
        estilo.configure("Treeview", font=("Segoe UI", 7), rowheight=20, background="#ffffff", fieldbackground="#ffffff", foreground="#172033")
        estilo.map("Treeview", background=[("selected", COR_AZUL)], foreground=[("selected", "#ffffff")])
        estilo.configure("Treeview.Heading", font=("Segoe UI Semibold", 7), background="#cffafe", foreground="#164e63", relief="flat")

    # -------------------------------------------------------------------------
    # CONSTRUÇÃO DA INTERFACE
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
            style="Title.TLabel",
        )
        titulo.grid(row=0, column=0, sticky="w")

        subtitulo = ttk.Label(
            cabecalho,
            text="Transformações entre energia potencial, cinética, mecânica e dissipada",
            style="SubTitle.TLabel",
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
            relief="flat",
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
            font=("Segoe UI", 10, "bold"),
        )
        titulo.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 2))

        self.criar_grupo_modelo(painel, 1)
        self.criar_grupo_visualizacao(painel, 2)
        self.criar_grupo_botoes(painel, 3)
        self.criar_grupo_presets(painel, 4)

    def criar_grupo(self, parent, row, titulo):
        acentos = {
            "Modelo físico": COR_CIANO,
            "Visualização e coleta": COR_ROXO,
            "Controle da simulação": COR_VERDE,
            "Situações prontas": COR_LARANJA,
        }
        acento = acentos.get(titulo, "#64748b")
        grupo = tk.Frame(parent, bg=COR_GRUPO, bd=0, highlightthickness=1, highlightbackground=acento)
        grupo.grid(row=row, column=0, sticky="ew", padx=5, pady=2)
        for c in range(3):
            grupo.columnconfigure(c, weight=1)

        lbl = tk.Label(
            grupo,
            text=titulo.upper(),
            bg=COR_GRUPO,
            fg=acento,
            font=("Segoe UI", 7, "bold"),
        )
        lbl.grid(row=0, column=0, columnspan=3, sticky="w", padx=5, pady=(4, 1))
        return grupo

    def criar_grupo_modelo(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Modelo físico")
        self.criar_linha_entradas(grupo, 1, "m (kg)", self.var_massa, "Hmáx (m)", self.var_altura)
        self.criar_linha_entradas(grupo, 2, "g (m/s²)", self.var_g, "v₀ (m/s)", self.var_v0)
        self.criar_linha_entradas(grupo, 3, "b atrito", self.var_b, "Δt (s)", self.var_dt)
        self.criar_label_combo(grupo, 4, "Ritmo", self.var_ritmo, [0.5, 1.0, 2.0, 4.0, 8.0])

        chk_atrito = tk.Checkbutton(
            grupo,
            text="Atrito dissipativo",
            variable=self.var_atrito,
            command=lambda: self.reiniciar_simulacao(limpar_tabela=True),
            bg=COR_GRUPO,
            fg=COR_TEXTO,
            activebackground=COR_GRUPO,
            activeforeground="#ffffff",
            selectcolor="#151225",
            font=("Segoe UI", 7),
        )
        chk_atrito.grid(row=5, column=0, columnspan=3, sticky="w", padx=5, pady=(1, 4))

    def criar_grupo_visualizacao(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Visualização e coleta")
        self.criar_label_combo(grupo, 1, "Percurso", self.var_percurso, ["Montanhas decrescentes", "Rampa suave", "Vale e subida curta"])
        self.criar_label_combo(grupo, 2, "Gráficos", self.var_grafico, ["Todos", "Energia mecânica total", "Energias: Ep, Ec e Em", "Altura × tempo", "Velocidade × tempo", "Posição × tempo", "Energia dissipada"])
        self.criar_label_combo(grupo, 3, "Tabela", self.var_tabela, self.opcoes_tabela)
        self.criar_label_combo(grupo, 4, "Modelo ajuste", self.var_modelo_ajuste, ["Linear", "Quadrático", "Cúbico"])

        chk_ajuste = tk.Checkbutton(
            grupo,
            text="Ajuste de curva",
            variable=self.var_ajuste,
            bg=COR_GRUPO,
            fg=COR_TEXTO,
            activebackground=COR_GRUPO,
            activeforeground="#ffffff",
            selectcolor="#151225",
            font=("Segoe UI", 7),
        )
        chk_ajuste.grid(row=5, column=0, columnspan=3, sticky="w", padx=5, pady=(1, 4))

    def criar_grupo_botoes(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Controle da simulação")

        botoes = [
            ("Iniciar", "Success.TButton", self.iniciar),
            ("Pausar", "Warning.TButton", self.pausar),
            ("Passo", None, self.passo),
            ("Resetar", "Danger.TButton", lambda: self.reiniciar_simulacao(limpar_tabela=True)),
            ("➖ H", None, self.diminuir_altura),
            ("➕ H", None, self.aumentar_altura),
            ("CSV", None, self.exportar_csv),
            ("Relatório", None, self.exportar_relatorio),
            ("Pré/Pós", None, self.exportar_roteiro_pre_pos_teste),
        ]

        for i, (texto, estilo, comando) in enumerate(botoes):
            r = 1 + i // 3
            c = i % 3
            if estilo:
                btn = ttk.Button(grupo, text=texto, style=estilo, command=comando)
            else:
                btn = ttk.Button(grupo, text=texto, command=comando)
            btn.grid(row=r, column=c, sticky="ew", padx=2, pady=2)

        lbl_status = tk.Label(
            grupo,
            textvariable=self.var_status,
            bg=COR_GRUPO,
            fg="#a5f3fc",
            font=("Segoe UI", 7),
            wraplength=205,
            justify="left",
        )
        lbl_status.grid(row=4, column=0, columnspan=3, sticky="ew", padx=5, pady=(1, 4))

    def criar_grupo_presets(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Situações prontas")
        presets = [
            ("Sem atrito", lambda: self.aplicar_preset(1)),
            ("Com atrito", lambda: self.aplicar_preset(2)),
            ("Rampa", lambda: self.aplicar_preset(3)),
        ]
        for i, (texto, comando) in enumerate(presets):
            ttk.Button(grupo, text=texto, command=comando).grid(row=1, column=i, sticky="ew", padx=2, pady=2)

        texto = (
            "Uso didático: sem atrito, Em deve permanecer horizontal; com atrito, Em diminui e Ed aumenta. "
            "Compare animação, tabela e gráficos."
        )
        tk.Label(
            grupo,
            text=texto,
            bg=COR_GRUPO,
            fg=COR_TEXTO_SUAVE,
            font=("Segoe UI", 7),
            wraplength=205,
            justify="left",
        ).grid(row=2, column=0, columnspan=3, sticky="ew", padx=5, pady=(2, 5))

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
        e1.bind("<Return>", lambda event: self.configuracao_alterada())
        e2.bind("<Return>", lambda event: self.configuracao_alterada())

    def criar_area_trabalho(self, parent):
        area = tk.Frame(parent, bg=COR_FUNDO)
        area.grid(row=0, column=1, sticky="nsew")
        area.columnconfigure(0, weight=1)
        area.columnconfigure(1, weight=0, minsize=250)
        area.rowconfigure(0, weight=1)

        visual = tk.Frame(area, bg=COR_FUNDO)
        visual.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        visual.columnconfigure(0, weight=1)
        visual.rowconfigure(0, weight=12, minsize=0, uniform="visual_split")
        visual.rowconfigure(1, weight=13, minsize=0, uniform="visual_split")

        self.criar_cena(visual)
        self.criar_graficos(visual)
        self.criar_tabela_e_leituras(area)

    def criar_cena(self, parent):
        card = tk.Frame(parent, bg=COR_CARD, bd=0, highlightthickness=1, highlightbackground=COR_CIANO)
        card.grid(row=0, column=0, sticky="nsew", pady=(0, 4))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=1)

        self.fig_cena = Figure(figsize=(8, 3.5), dpi=100, facecolor=COR_CENA)
        self.ax_cena = self.fig_cena.add_subplot(111)
        self.canvas_cena = FigureCanvasTkAgg(self.fig_cena, master=card)
        self.canvas_cena.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=4)

    def criar_graficos(self, parent):
        card = tk.Frame(parent, bg=COR_CARD, bd=0, highlightthickness=1, highlightbackground=COR_ROXO)
        card.grid(row=1, column=0, sticky="nsew")
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
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=0, sticky="w")

        self.lbl_nota_grafico = tk.Label(
            topo,
            text="Mostrando h(t), v(t) e energias.",
            bg="#f8fafc",
            fg="#475569",
            font=("Segoe UI", 7),
        )
        self.lbl_nota_grafico.grid(row=0, column=1, sticky="e")

        self.fig_graficos = Figure(figsize=(7.2, 3.8), dpi=100, facecolor="#ffffff")
        self.canvas_graficos = FigureCanvasTkAgg(self.fig_graficos, master=card)
        self.canvas_graficos.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=5, pady=(2, 5))

    def criar_tabela_e_leituras(self, parent):
        card = tk.Frame(parent, bg=COR_CARD, bd=0, highlightthickness=1, highlightbackground=COR_LARANJA, width=250)
        card.grid(row=0, column=1, sticky="nsew")
        card.grid_propagate(False)
        card.columnconfigure(0, weight=1)
        card.rowconfigure(3, weight=1)

        topo = tk.Frame(card, bg="#f8fafc")
        topo.grid(row=0, column=0, sticky="ew", padx=8, pady=(7, 3))
        topo.columnconfigure(0, weight=1)

        tk.Label(
            topo,
            text="Tabela experimental",
            bg="#f8fafc",
            fg="#0f172a",
            font=("Segoe UI", 10, "bold"),
        ).grid(row=0, column=0, sticky="w")

        tk.Label(
            topo,
            text="compacta",
            bg="#f8fafc",
            fg="#475569",
            font=("Segoe UI", 8, "bold"),
        ).grid(row=0, column=1, sticky="e")

        leituras = tk.Frame(card, bg="#eff6ff", bd=0, highlightthickness=1, highlightbackground="#bfdbfe")
        leituras.grid(row=1, column=0, sticky="ew", padx=7, pady=(0, 6))
        for c in range(2):
            leituras.columnconfigure(c, weight=1)

        self.criar_leitura(leituras, 0, 0, "t", self.var_leitura_t)
        self.criar_leitura(leituras, 0, 1, "x", self.var_leitura_x)
        self.criar_leitura(leituras, 1, 0, "h", self.var_leitura_h)
        self.criar_leitura(leituras, 1, 1, "v", self.var_leitura_v)
        self.criar_leitura(leituras, 2, 0, "Em", self.var_leitura_Em)
        self.criar_leitura(leituras, 2, 1, "erro", self.var_leitura_erro)

        painel_tabela = tk.Frame(card, bg="#e0f2fe", bd=0, highlightthickness=1, highlightbackground="#bae6fd")
        painel_tabela.grid(row=2, column=0, sticky="ew", padx=7, pady=(0, 6))
        painel_tabela.columnconfigure(1, weight=1)

        tk.Label(
            painel_tabela,
            text="Grandeza",
            bg="#e0f2fe",
            fg="#0f172a",
            font=("Segoe UI", 8, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=8, pady=(7, 3))

        combo = ttk.Combobox(
            painel_tabela,
            textvariable=self.var_tabela,
            values=self.opcoes_tabela,
            state="readonly",
            width=16,
            font=("Segoe UI", 8),
        )
        combo.grid(row=0, column=1, sticky="ew", padx=8, pady=(7, 3))
        combo.bind("<<ComboboxSelected>>", lambda event: self.aplicar_configuracao_tabela())

        tk.Label(
            painel_tabela,
            textvariable=self.var_descricao_tabela,
            bg="#e0f2fe",
            fg="#334155",
            font=("Segoe UI", 8),
            justify="left",
            wraplength=220,
        ).grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(2, 7))

        frame_tabela = tk.Frame(card, bg="#f8fafc")
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
        self.tabela.tag_configure("par", background="#ecfeff")
        self.tabela.tag_configure("impar", background="#ffffff")

        self.aplicar_configuracao_tabela()

    def criar_leitura(self, parent, row, col, titulo, variavel):
        caixa = tk.Frame(parent, bg="#eff6ff")
        caixa.grid(row=row, column=col, sticky="ew", padx=6, pady=3)
        tk.Label(caixa, text=titulo, bg="#eff6ff", fg="#475569", font=("Segoe UI", 7, "bold")).pack(anchor="w")
        tk.Label(caixa, textvariable=variavel, bg="#eff6ff", fg="#0f172a", font=("Segoe UI", 9, "bold")).pack(anchor="w")

    # -------------------------------------------------------------------------
    # CONFIGURAÇÃO DA TABELA
    # -------------------------------------------------------------------------
    def obter_colunas_tabela(self):
        tipo = self.var_tabela.get()
        if tipo == "Altura × Tempo":
            return ["Tempo", "Altura"]
        if tipo == "Velocidade × Tempo":
            return ["Tempo", "Velocidade"]
        if tipo == "Posição × Tempo":
            return ["Tempo", "Posição"]
        if tipo == "Energia mecânica":
            return ["Tempo", "Energia mecânica", "Erro percentual"]
        if tipo == "Energia dissipada":
            return ["Tempo", "Energia dissipada"]
        return ["Tempo", "Posição", "Altura", "Velocidade", "Energia potencial", "Energia cinética", "Energia mecânica", "Erro percentual"]

    def aplicar_configuracao_tabela(self):
        if not hasattr(self, "tabela"):
            return

        selecionadas = self.obter_colunas_tabela()
        colunas = ["n"] + [self.mapa_tabela[g]["chave"] for g in selecionadas]
        self.tabela.configure(columns=colunas)
        self.tabela.heading("n", text="#")
        self.tabela.column("n", width=30, anchor="center", stretch=False)

        for grandeza in selecionadas:
            meta = self.mapa_tabela[grandeza]
            chave = meta["chave"]
            self.tabela.heading(chave, text=meta["titulo"])
            self.tabela.column(chave, width=meta["largura"], anchor="center", stretch=False)

        tipo = self.var_tabela.get()
        if tipo == "Altura × Tempo":
            self.var_descricao_tabela.set("Tabela ativa: h em função de t.")
        elif tipo == "Velocidade × Tempo":
            self.var_descricao_tabela.set("Tabela ativa: v em função de t.")
        elif tipo == "Posição × Tempo":
            self.var_descricao_tabela.set("Tabela ativa: posição x em função de t.")
        elif tipo == "Energia mecânica":
            self.var_descricao_tabela.set("Tabela ativa: Em e erro percentual em relação a Em inicial.")
        elif tipo == "Energia dissipada":
            self.var_descricao_tabela.set("Tabela ativa: energia dissipada Ed = Em inicial − Em atual.")
        else:
            self.var_descricao_tabela.set("Tabela ativa: t, x, h, v, Ep, Ec, Em e erro de conservação.")

        self.atualizar_tabela(forcar=True)

    # -------------------------------------------------------------------------
    # EVENTOS E VALIDAÇÃO
    # -------------------------------------------------------------------------
    def configurar_eventos(self):
        variaveis = [
            self.var_massa, self.var_altura, self.var_g, self.var_v0, self.var_b,
            self.var_dt, self.var_ritmo, self.var_percurso,
            self.var_grafico, self.var_tabela, self.var_modelo_ajuste, self.var_ajuste,
        ]
        for var in variaveis:
            var.trace_add("write", lambda *args: self.configuracao_alterada(suave=True))

        self.root.protocol("WM_DELETE_WINDOW", self.fechar)

    def configuracao_alterada(self, suave=False):
        if self._suprimir_eventos:
            return
        if self.validar_parametros(mostrar_erro=not suave) is None:
            return
        if self.t == 0.0:
            self.recalcular_perfil_base()
            self.reiniciar_simulacao(limpar_tabela=True)
        else:
            self.atualizar_tudo()

    def validar_parametros(self, mostrar_erro=True):
        try:
            m = converter_numero(self.var_massa.get())
            H = converter_numero(self.var_altura.get())
            g = converter_numero(self.var_g.get())
            v0 = converter_numero(self.var_v0.get())
            b = converter_numero(self.var_b.get())
            dt = converter_numero(self.var_dt.get())
            ritmo = converter_numero(self.var_ritmo.get())
        except (TypeError, ValueError):
            if mostrar_erro:
                messagebox.showerror("Erro nos parâmetros", "Verifique se todos os campos numéricos foram preenchidos corretamente.")
            return None

        mensagens = []
        if m <= 0:
            mensagens.append("A massa deve ser maior que zero.")
        if H <= 0:
            mensagens.append("A altura máxima deve ser maior que zero.")
        if g <= 0:
            mensagens.append("A gravidade deve ser maior que zero.")
        if b < 0:
            mensagens.append("O coeficiente dissipativo b não pode ser negativo.")
        if dt < DT_MIN:
            mensagens.append("O passo Δt deve ser maior ou igual a 0,001 s.")
        if dt > DT_MAX:
            mensagens.append("Use Δt ≤ 0,05 s para preservar a estabilidade da simulação.")
        if not RITMO_MIN <= ritmo <= RITMO_MAX:
            mensagens.append("O ritmo deve estar entre 0,5× e 8×.")
        if abs(v0) > 30:
            mensagens.append("Use uma velocidade inicial com módulo menor ou igual a 30 m/s.")

        if mensagens:
            if mostrar_erro:
                messagebox.showerror("Erro nos parâmetros", "\n".join(mensagens))
            return None

        return m, H, g, v0, b, dt, ritmo

    # -------------------------------------------------------------------------
    # PERFIL GEOMÉTRICO DA PISTA
    # -------------------------------------------------------------------------
    def inicio_trecho_zero(self):
        return 0.94

    def perfil_montanhas_decrescentes(self, u):
        u = np.clip(u, 0.0, 1.0)
        inicio_zero = self.inicio_trecho_zero()
        s = np.clip(u / inicio_zero, 0.0, 1.0)
        envelope = (1.0 - s) ** 1.08
        ondulacao = 0.70 + 0.30 * (0.5 + 0.5 * np.cos(2.0 * np.pi * 5.0 * s))
        h = envelope * ondulacao
        return np.where(u >= inicio_zero, 0.0, np.clip(h, 0.0, 1.0))

    def perfil_rampa_suave(self, u):
        u = np.clip(u, 0.0, 1.0)
        inicio_zero = self.inicio_trecho_zero()
        s = np.clip(u / inicio_zero, 0.0, 1.0)
        h = (1.0 - s) ** 1.15
        return np.where(u >= inicio_zero, 0.0, np.clip(h, 0.0, 1.0))

    def perfil_vale_subida(self, u):
        u = np.clip(u, 0.0, 1.0)
        inicio_zero = self.inicio_trecho_zero()
        s = np.clip(u / inicio_zero, 0.0, 1.0)
        base = (1.0 - s) ** 1.12
        vale = 0.16 * np.exp(-((s - 0.45) / 0.12) ** 2)
        subida = 0.10 * np.exp(-((s - 0.68) / 0.10) ** 2)
        h = base - vale + subida
        return np.where(u >= inicio_zero, 0.0, np.clip(h, 0.0, 1.0))

    def perfil_raw(self, x):
        x_arr = np.asarray(x, dtype=float)
        u = np.clip(x_arr / self.L, 0.0, 1.0)
        tipo = self.var_percurso.get() if hasattr(self, "var_percurso") else "Montanhas decrescentes"
        if tipo == "Rampa suave":
            y = self.perfil_rampa_suave(u)
        elif tipo == "Vale e subida curta":
            y = self.perfil_vale_subida(u)
        else:
            y = self.perfil_montanhas_decrescentes(u)
        if np.isscalar(x):
            return float(np.asarray(y))
        return y

    def recalcular_perfil_base(self):
        xs = np.linspace(0.0, self.L, 2000)
        valores = self.perfil_raw(xs)
        self.base_min = float(np.min(valores))
        self.base_max = float(np.max(valores))

    def altura_pista_normalizada(self, x):
        intervalo = max(1e-9, self.base_max - self.base_min)
        return (self.perfil_raw(x) - self.base_min) / intervalo

    def altura_pista(self, x):
        H = max(0.20, converter_numero(self.var_altura.get()))
        y = H * self.altura_pista_normalizada(x)
        if np.isscalar(x):
            return float(np.asarray(y))
        return y

    def derivada_altura(self, x):
        dx = 1e-4 * self.L
        xp = min(self.L, x + dx)
        xm = max(0.0, x - dx)
        if abs(xp - xm) < 1e-12:
            return 0.0
        return (self.altura_pista(xp) - self.altura_pista(xm)) / (xp - xm)

    def segunda_derivada_altura(self, x):
        dx = 1e-4 * self.L
        xp = min(self.L, x + dx)
        xm = max(0.0, x - dx)
        return (self.altura_pista(xp) - 2.0 * self.altura_pista(x) + self.altura_pista(xm)) / (dx ** 2)

    # -------------------------------------------------------------------------
    # FÍSICA DO MOVIMENTO
    # -------------------------------------------------------------------------
    def aceleracao_x(self, x, vx):
        m = max(1e-9, converter_numero(self.var_massa.get()))
        g = max(1e-9, converter_numero(self.var_g.get()))
        b = max(0.0, converter_numero(self.var_b.get())) if self.var_atrito.get() else 0.0
        hp = self.derivada_altura(x)
        hpp = self.segunda_derivada_altura(x)
        denominador = max(1e-9, 1.0 + hp ** 2)
        ax = (-g * hp - hp * hpp * vx ** 2 - (b / m) * vx * denominador) / denominador
        return ax

    def passo_rk4(self, dt):
        if self.finalizado:
            return

        def f(x, vx):
            return vx, self.aceleracao_x(x, vx)

        x_anterior = self.x
        k1x, k1v = f(self.x, self.vx)
        k2x, k2v = f(self.x + 0.5 * dt * k1x, self.vx + 0.5 * dt * k1v)
        k3x, k3v = f(self.x + 0.5 * dt * k2x, self.vx + 0.5 * dt * k2v)
        k4x, k4v = f(self.x + dt * k3x, self.vx + dt * k3v)

        self.x += dt * (k1x + 2.0 * k2x + 2.0 * k3x + k4x) / 6.0
        self.vx += dt * (k1v + 2.0 * k2v + 2.0 * k3v + k4v) / 6.0

        self.tratar_limites(x_anterior)

        if not self.finalizado and not self.var_atrito.get():
            self.corrigir_velocidade_para_conservar_energia()

    def tratar_limites(self, x_anterior):
        if self.x >= self.L or (x_anterior < self.L <= self.x):
            self.x = self.L
            if not self.var_atrito.get():
                self.corrigir_velocidade_para_conservar_energia()
            self.rodando = False
            self.finalizado = True
            return

        if self.x < 0.0:
            self.x = 0.0
            self.vx = abs(self.vx)

    def corrigir_velocidade_para_conservar_energia(self):
        m = max(1e-9, converter_numero(self.var_massa.get()))
        g = max(1e-9, converter_numero(self.var_g.get()))
        h = self.altura_pista(self.x)
        hp = self.derivada_altura(self.x)
        Ec = max(0.0, self.E0 - m * g * h)
        v_trilho = math.sqrt(2.0 * Ec / m)

        if abs(self.vx) > 1e-10:
            sinal = 1.0 if self.vx >= 0 else -1.0
        elif abs(hp) > 1e-10:
            sinal = 1.0 if -hp >= 0 else -1.0
        else:
            sinal = self.sentido_preferencial

        self.vx = sinal * v_trilho / math.sqrt(1.0 + hp ** 2)

    def calcular_energias(self):
        m = max(1e-9, converter_numero(self.var_massa.get()))
        g = max(1e-9, converter_numero(self.var_g.get()))
        h = self.altura_pista(self.x)
        hp = self.derivada_altura(self.x)
        v = self.vx * math.sqrt(1.0 + hp ** 2)
        Ep = m * g * h
        Ec = 0.5 * m * v ** 2
        Em = Ep + Ec
        Ed = max(0.0, self.E0 - Em)
        erro = erro_percentual(Em, self.E0)
        return h, v, Ep, Ec, Em, Ed, erro

    def registrar_dados(self):
        h, v, Ep, Ec, Em, Ed, erro = self.calcular_energias()
        self.t_hist.append(float(self.t))
        self.x_hist.append(float(self.x))
        self.h_hist.append(float(h))
        self.v_hist.append(float(v))
        self.Ep_hist.append(float(Ep))
        self.Ec_hist.append(float(Ec))
        self.Em_hist.append(float(Em))
        self.Ed_hist.append(float(Ed))
        self.erro_hist.append(float(erro))

        limite = MAX_DADOS
        if len(self.t_hist) > limite:
            self.t_hist = self.t_hist[-limite:]
            self.x_hist = self.x_hist[-limite:]
            self.h_hist = self.h_hist[-limite:]
            self.v_hist = self.v_hist[-limite:]
            self.Ep_hist = self.Ep_hist[-limite:]
            self.Ec_hist = self.Ec_hist[-limite:]
            self.Em_hist = self.Em_hist[-limite:]
            self.Ed_hist = self.Ed_hist[-limite:]
            self.erro_hist = self.erro_hist[-limite:]

    # -------------------------------------------------------------------------
    # CONTROLES
    # -------------------------------------------------------------------------
    def iniciar(self):
        if self.validar_parametros() is None:
            return
        if self.finalizado:
            self.reiniciar_simulacao(limpar_tabela=True)
        self.rodando = True
        self.var_status.set("Simulação em execução.")

    def pausar(self):
        self.rodando = False
        self.var_status.set("Simulação pausada.")

    def passo(self):
        if self.validar_parametros() is None:
            return
        if not self.finalizado:
            dt = converter_numero(self.var_dt.get())
            self.passo_rk4(dt)
            self.t += dt
            self.registrar_dados()
            self.atualizar_tudo(forcar_tabela=True)
            self.var_status.set("Executado um passo Δt.")

    def reiniciar_simulacao(self, limpar_tabela=True):
        valores = self.validar_parametros(mostrar_erro=False)
        if valores is None:
            return

        m, H, g, v0, b, dt, ritmo = valores
        self.rodando = False
        self.finalizado = False
        self.t = 0.0
        self.x = 0.0
        self.recalcular_perfil_base()

        hp = self.derivada_altura(self.x)
        self.vx = v0 / math.sqrt(1.0 + hp ** 2)
        h, v, Ep, Ec, Em, Ed, erro = self.calcular_energias()
        self.E0 = Em
        self.limpar_historicos()
        self.registrar_dados()
        self.contador_tabela = 0
        self.var_status.set("Pronto para iniciar.")
        self.atualizar_tudo(forcar_tabela=True)

    def limpar_historicos(self):
        self.t_hist.clear()
        self.x_hist.clear()
        self.h_hist.clear()
        self.v_hist.clear()
        self.Ep_hist.clear()
        self.Ec_hist.clear()
        self.Em_hist.clear()
        self.Ed_hist.clear()
        self.erro_hist.clear()

    def aumentar_altura(self):
        if self.validar_parametros(mostrar_erro=True) is None:
            return
        self._suprimir_eventos = True
        self.var_altura.set(formato_numero(converter_numero(self.var_altura.get()) + 0.25, 2))
        self._suprimir_eventos = False
        self.reiniciar_simulacao(limpar_tabela=True)

    def diminuir_altura(self):
        if self.validar_parametros(mostrar_erro=True) is None:
            return
        self._suprimir_eventos = True
        self.var_altura.set(formato_numero(max(0.20, converter_numero(self.var_altura.get()) - 0.25), 2))
        self._suprimir_eventos = False
        self.reiniciar_simulacao(limpar_tabela=True)

    def aplicar_preset(self, numero):
        self._suprimir_eventos = True
        if numero == 1:
            self.var_massa.set("1,00")
            self.var_altura.set("2,70")
            self.var_v0.set("0,00")
            self.var_b.set("0,00")
            self.var_atrito.set(False)
            self.var_percurso.set("Montanhas decrescentes")
            self.var_grafico.set("Todos")
            self.var_tabela.set("Energia completa")
        elif numero == 2:
            self.var_massa.set("1,00")
            self.var_altura.set("2,70")
            self.var_v0.set("0,00")
            self.var_b.set("0,18")
            self.var_atrito.set(True)
            self.var_percurso.set("Montanhas decrescentes")
            self.var_grafico.set("Energia dissipada")
            self.var_tabela.set("Energia dissipada")
        else:
            self.var_massa.set("1,00")
            self.var_altura.set("2,00")
            self.var_v0.set("0,00")
            self.var_b.set("0,00")
            self.var_atrito.set(False)
            self.var_percurso.set("Rampa suave")
            self.var_grafico.set("Energia mecânica total")
            self.var_tabela.set("Energia mecânica")
        self._suprimir_eventos = False
        self.reiniciar_simulacao(limpar_tabela=True)

    # -------------------------------------------------------------------------
    # ATUALIZAÇÃO VISUAL
    # -------------------------------------------------------------------------
    def atualizar_tudo(self, forcar_tabela=False, animacao=False):
        if self.validar_parametros(mostrar_erro=False) is None:
            return
        self.desenhar_animacao()
        self.atualizar_leituras()
        self.atualizar_status()
        self.canvas_cena.draw_idle()
        agora = time.monotonic()
        atualizar_grafico = not animacao or self.finalizado or agora - self._ultimo_redesenho_grafico >= INTERVALO_GRAFICO
        atualizar_tabela = forcar_tabela or not animacao or self.finalizado or agora - self._ultima_atualizacao_tabela >= INTERVALO_TABELA
        if atualizar_grafico:
            self.desenhar_graficos()
            self.canvas_graficos.draw_idle()
            self._ultimo_redesenho_grafico = agora
        if atualizar_tabela:
            self.atualizar_tabela(forcar=True)
            self._ultima_atualizacao_tabela = agora

    def desenhar_animacao(self):
        ax = self.ax_cena
        ax.clear()

        H = max(0.20, converter_numero(self.var_altura.get()))
        xs = np.linspace(0.0, self.L, 800)
        hs = self.altura_pista(xs)
        ax.set_xlim(-0.40, self.L + 0.40)
        ax.set_ylim(-0.36, H * 1.22 + 0.42)
        ax.set_facecolor(COR_CENA)
        ax.set_title("Simulação experimental: carrinho em pista e transformação de energia", fontsize=10, fontweight="bold")
        ax.set_xlabel("posição horizontal x (m)", fontsize=8)
        ax.set_ylabel("altura h (m)", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.18)

        # Fundo didático e solo
        ax.axhline(0.0, linewidth=1.4, color="#64748b")
        ax.fill_between(xs, 0, hs, color="#ccfbf1", alpha=0.75, zorder=0)
        ax.plot(xs, hs, linewidth=6.0, color="#4338ca", solid_capstyle="round", zorder=2)
        ax.plot(xs, hs, linewidth=2.2, color=COR_AMARELO, solid_capstyle="round", zorder=3)

        # Percurso realizado
        if self.x > 0:
            xs_done = np.linspace(0.0, self.x, max(20, int(220 * self.x / self.L)))
            ax.plot(xs_done, self.altura_pista(xs_done) + 0.026, linewidth=3.0, color=COR_VERDE, zorder=4)

        # Suportes da pista
        for sx in np.linspace(0.8, 9.2, 7):
            sy = self.altura_pista(float(sx))
            ax.plot([sx, sx], [0, sy], color="#94a3b8", linewidth=1.5, zorder=1)
            ax.plot([sx - 0.12, sx + 0.12], [0, 0], color="#64748b", linewidth=1.8, zorder=1)

        # Escala vertical e pontos notáveis
        ax.plot([0, 0], [0, H], color="#8b5cf6", linewidth=1.4, linestyle="--")
        ax.text(0.10, H * 0.96, f"Hmáx = {H:.2f} m", color="#6d28d9", fontsize=8, fontweight="bold", va="top")
        ax.scatter([0], [self.altura_pista(0)], s=55, color="#15803d", edgecolors="white", linewidths=1.0, zorder=6)
        ax.scatter([self.L], [0], s=55, color="#b91c1c", edgecolors="white", linewidths=1.0, zorder=6)
        ax.text(0.12, self.altura_pista(0) + 0.10, "início", color="#166534", fontsize=8, fontweight="bold")
        ax.text(self.L - 0.12, 0.10, "fim: h = 0 m", color="#991b1b", fontsize=8, fontweight="bold", ha="right")

        self.desenhar_carrinho(ax)

        h, v, Ep, Ec, Em, Ed, erro = self.calcular_energias()
        modo = "com atrito" if self.var_atrito.get() else "sem atrito"
        fim_txt = " | FINALIZADO" if self.finalizado else ""
        texto = (
            f"{modo} | t={self.t:.2f} s | h={h:.2f} m | v={v:.2f} m/s | "
            f"Ep={Ep:.2f} J | Ec={Ec:.2f} J | Em={Em:.2f} J{fim_txt}"
        )
        ax.text(
            0.02,
            0.96,
            texto,
            transform=ax.transAxes,
            fontsize=8,
            va="top",
            bbox=dict(boxstyle="round,pad=0.32", facecolor="white", edgecolor="#cbd5e1", alpha=0.93),
        )

    def desenhar_carrinho(self, ax):
        h = self.altura_pista(self.x)
        hp = self.derivada_altura(self.x)
        theta = math.atan(hp)
        tangente = np.array([math.cos(theta), math.sin(theta)])
        normal = np.array([-math.sin(theta), math.cos(theta)])

        H = max(0.20, converter_numero(self.var_altura.get()))
        escala = float(np.clip(1.15 * math.sqrt(2.70 / H), 0.60, 1.45))
        largura = 0.70 * escala
        altura = 0.26 * escala
        raio = 0.082 * escala
        centro = np.array([self.x, h]) + normal * (altura * 0.62 + raio)

        sombra = FancyBboxPatch(
            (-largura / 2, -altura / 2),
            largura,
            altura,
            boxstyle="round,pad=0.02,rounding_size=0.05",
            facecolor="#ef4444",
            edgecolor="#7f1d1d",
            linewidth=1.5,
            zorder=8,
        )
        sombra.set_transform(Affine2D().rotate(theta).translate(centro[0], centro[1]) + ax.transData)
        ax.add_patch(sombra)

        janela = Rectangle(
            (-0.12 * escala, -0.055 * escala),
            0.24 * escala,
            0.11 * escala,
            facecolor="#bfdbfe",
            edgecolor="#1d4ed8",
            linewidth=1.0,
            zorder=9,
        )
        janela_centro = centro + normal * (altura * 0.10)
        janela.set_transform(Affine2D().rotate(theta).translate(janela_centro[0], janela_centro[1]) + ax.transData)
        ax.add_patch(janela)

        for deslocamento in [-0.24 * escala, 0.24 * escala]:
            pos = centro + tangente * deslocamento - normal * (altura * 0.57)
            roda = Circle(pos, raio, facecolor="#111827", edgecolor="#020617", linewidth=1.0, zorder=10)
            eixo = Circle(pos, raio * 0.34, facecolor="#f8fafc", edgecolor="#cbd5e1", linewidth=0.6, zorder=11)
            ax.add_patch(roda)
            ax.add_patch(eixo)

        # Vetor velocidade
        _, v, _, _, _, _, _ = self.calcular_energias()
        if not self.finalizado:
            sentido = 1.0 if self.vx >= 0 else -1.0
            comprimento = min(1.25, 0.28 + 0.08 * abs(v))
            inicio = centro + normal * (0.36 * escala)
            fim = inicio + sentido * tangente * comprimento
            ax.annotate(
                "",
                xy=fim,
                xytext=inicio,
                arrowprops=dict(arrowstyle="->", linewidth=2.0, color="#2563eb"),
                zorder=12,
            )
            ax.text(fim[0] + 0.05, fim[1] + 0.02, "v", color="#1d4ed8", fontsize=10, fontweight="bold")
        else:
            ax.text(centro[0], centro[1] + 0.34 * escala, "FIM", color="#b91c1c", fontsize=9, fontweight="bold", ha="center")

        ax.plot([self.x, self.x], [0, h], color="#16a34a", linewidth=1.3, linestyle="--", zorder=6)
        ax.text(self.x + 0.07, max(0.08, h / 2), f"h={h:.2f} m", color="#15803d", fontsize=8, fontweight="bold")

    def desenhar_graficos(self):
        self.fig_graficos.clear()
        tipo = self.var_grafico.get()
        t = np.asarray(self.t_hist, dtype=float)

        if tipo == "Todos":
            self.lbl_nota_grafico.config(text="Mostrando h(t), v(t) e energias.")
            gs = self.fig_graficos.add_gridspec(1, 3, wspace=0.42, top=0.87, bottom=0.23, left=0.07, right=0.98)
            axes = [self.fig_graficos.add_subplot(gs[0, i]) for i in range(3)]
            self.desenhar_eixo_altura(axes[0], t)
            self.desenhar_eixo_velocidade(axes[1], t)
            self.desenhar_eixo_energias(axes[2], t)
        else:
            self.lbl_nota_grafico.config(text=f"Mostrando {tipo}.")
            ax = self.fig_graficos.add_subplot(111)
            if tipo == "Energia mecânica total":
                self.desenhar_eixo_em(ax, t)
            elif tipo == "Energias: Ep, Ec e Em":
                self.desenhar_eixo_energias(ax, t)
            elif tipo == "Altura × tempo":
                self.desenhar_eixo_altura(ax, t)
            elif tipo == "Velocidade × tempo":
                self.desenhar_eixo_velocidade(ax, t)
            elif tipo == "Posição × tempo":
                self.desenhar_eixo_posicao(ax, t)
            elif tipo == "Energia dissipada":
                self.desenhar_eixo_ed(ax, t)
            self.desenhar_ajuste_se_necessario(ax)
            self.fig_graficos.subplots_adjust(left=0.10, right=0.97, top=0.88, bottom=0.20)

    def preparar_eixo(self, ax, titulo, ylabel, cor_fundo="#ffffff"):
        ax.set_facecolor(cor_fundo)
        ax.set_title(titulo, fontsize=8.5, fontweight="bold", color="#172033", pad=5)
        ax.set_xlabel("tempo (s)", fontsize=7)
        ax.set_ylabel(ylabel, fontsize=7)
        ax.grid(True, which="major", color=COR_GRADE, alpha=0.72, linewidth=0.6)
        ax.grid(True, which="minor", color=COR_GRADE, alpha=0.35, linewidth=0.4)
        ax.tick_params(axis="both", labelsize=7)
        ax.xaxis.set_minor_locator(AutoMinorLocator())
        ax.yaxis.set_minor_locator(AutoMinorLocator())
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#94a3b8")
        ax.spines["bottom"].set_color("#94a3b8")

    def eixo_x_tempo(self, ax, t):
        xmax = max(5.0, float(t[-1]) * 1.05) if len(t) else 5.0
        ax.set_xlim(0, xmax)
        return xmax

    def desenhar_eixo_altura(self, ax, t):
        self.preparar_eixo(ax, "Altura h(t)", "h (m)", "#f0fdf4")
        self.eixo_x_tempo(ax, t)
        h = np.asarray(self.h_hist, dtype=float)
        if len(t):
            ax.fill_between(t, 0, h, color=COR_VERDE, alpha=0.10)
            ax.plot(t, h, linewidth=1.8, color=COR_VERDE, label="h(t)")
            ax.scatter([t[-1]], [h[-1]], s=25, color=COR_VERMELHO, edgecolor="#ffffff", linewidth=0.7, zorder=5)
        ax.set_ylim(0, max(0.5, converter_numero(self.var_altura.get()) * 1.15))
        ax.legend(fontsize=7, loc="upper right")

    def desenhar_eixo_velocidade(self, ax, t):
        self.preparar_eixo(ax, "Velocidade v(t)", "v (m/s)", "#eff6ff")
        self.eixo_x_tempo(ax, t)
        v = np.asarray(self.v_hist, dtype=float)
        ax.axhline(0, linewidth=0.8, color="#0f172a")
        if len(t):
            ax.plot(t, v, linewidth=1.8, color=COR_AZUL, label="v(t)")
            ax.scatter([t[-1]], [v[-1]], s=25, color=COR_VERMELHO, edgecolor="#ffffff", linewidth=0.7, zorder=5)
            vmax = max(1.0, float(np.max(np.abs(v))))
            ax.set_ylim(-1.2 * vmax, 1.2 * vmax)
        else:
            ax.set_ylim(-1, 1)
        ax.legend(fontsize=7, loc="upper right")

    def desenhar_eixo_energias(self, ax, t):
        self.preparar_eixo(ax, "Energias Ep, Ec e Em", "energia (J)", "#fff7ed")
        self.eixo_x_tempo(ax, t)
        Ep = np.asarray(self.Ep_hist, dtype=float)
        Ec = np.asarray(self.Ec_hist, dtype=float)
        Em = np.asarray(self.Em_hist, dtype=float)
        if len(t):
            ax.plot(t, Ep, linewidth=1.7, color=COR_VERDE, label="Ep=mgh")
            ax.plot(t, Ec, linewidth=1.7, color=COR_AZUL, label="Ec=½mv²")
            ax.plot(t, Em, linewidth=2.0, color=COR_MAGENTA, label="Em=Ep+Ec")
            ax.plot([0, max(5.0, float(t[-1]) * 1.05)], [self.E0, self.E0], linewidth=1.1, linestyle="--", color="#111827", label="Em inicial")
            ymax = max(1.0, float(np.max(np.r_[Ep, Ec, Em, [self.E0]])) * 1.16)
            ax.set_ylim(0, ymax)
        else:
            ax.set_ylim(0, 1)
        ax.legend(fontsize=7, loc="upper right", ncol=2)

    def desenhar_eixo_em(self, ax, t):
        self.preparar_eixo(ax, "Energia mecânica total", "Em (J)", "#fdf4ff")
        xmax = self.eixo_x_tempo(ax, t)
        y = np.asarray(self.Em_hist, dtype=float)
        if len(t):
            ax.plot(t, y, linewidth=2.1, color=COR_MAGENTA, label="Em calculada")
            ax.plot([0, xmax], [self.E0, self.E0], linewidth=1.4, linestyle="--", color="#111827", label="referência constante")
            margem = max(0.5, 0.08 * max(abs(self.E0), 1.0))
            ymin = min(float(np.min(y)), self.E0) - margem
            ymax = max(float(np.max(y)), self.E0) + margem
            ax.set_ylim(ymin, ymax)
        else:
            ax.set_ylim(0, 1)
        ax.legend(fontsize=8, loc="upper right")
        ax.text(
            0.02,
            0.94,
            "Sem atrito: Em deve formar uma reta horizontal.",
            transform=ax.transAxes,
            fontsize=8,
            va="top",
            bbox=dict(boxstyle="round", facecolor="white", edgecolor="#cbd5e1", alpha=0.92),
        )

    def desenhar_eixo_posicao(self, ax, t):
        self.preparar_eixo(ax, "Posição horizontal", "x (m)", "#faf5ff")
        self.eixo_x_tempo(ax, t)
        x = np.asarray(self.x_hist, dtype=float)
        if len(t):
            ax.plot(t, x, linewidth=2.0, color=COR_ROXO, label="x(t)")
        ax.set_ylim(0, self.L * 1.08)
        ax.legend(fontsize=8, loc="upper left")

    def desenhar_eixo_ed(self, ax, t):
        self.preparar_eixo(ax, "Energia dissipada", "Ed (J)", "#fff7ed")
        self.eixo_x_tempo(ax, t)
        Ed = np.asarray(self.Ed_hist, dtype=float)
        if len(t):
            ax.fill_between(t, 0, Ed, color=COR_LARANJA, alpha=0.12)
            ax.plot(t, Ed, linewidth=2.0, color=COR_LARANJA, label="Ed(t)")
            ax.set_ylim(0, max(1.0, float(np.max(Ed)) * 1.25))
        else:
            ax.set_ylim(0, 1)
        ax.legend(fontsize=8, loc="upper left")

    # -------------------------------------------------------------------------
    # AJUSTE DE CURVA
    # -------------------------------------------------------------------------
    def dados_grafico_atual(self):
        tipo = self.var_grafico.get()
        t = np.asarray(self.t_hist, dtype=float)
        if tipo == "Altura × tempo":
            return t, np.asarray(self.h_hist, dtype=float), "h"
        if tipo == "Velocidade × tempo":
            return t, np.asarray(self.v_hist, dtype=float), "v"
        if tipo == "Posição × tempo":
            return t, np.asarray(self.x_hist, dtype=float), "x"
        if tipo == "Energia dissipada":
            return t, np.asarray(self.Ed_hist, dtype=float), "Ed"
        return t, np.asarray(self.Em_hist, dtype=float), "Em"

    def desenhar_ajuste_se_necessario(self, ax):
        if not self.var_ajuste.get() or self.var_grafico.get() == "Todos":
            return

        t, y, simbolo = self.dados_grafico_atual()
        if len(t) < 6:
            ax.text(
                0.02,
                0.08,
                "Ajuste: aguarde mais dados.",
                transform=ax.transAxes,
                fontsize=8,
                bbox=dict(boxstyle="round", facecolor="white", edgecolor="#cbd5e1", alpha=0.92),
            )
            return

        mascara = np.isfinite(t) & np.isfinite(y)
        t_fit = t[mascara]
        y_fit = y[mascara]
        if len(t_fit) < 6 or np.allclose(np.std(y_fit), 0.0):
            ax.text(
                0.02,
                0.08,
                "Ajuste não necessário: dados quase constantes.",
                transform=ax.transAxes,
                fontsize=8,
                bbox=dict(boxstyle="round", facecolor="white", edgecolor="#cbd5e1", alpha=0.92),
            )
            return

        try:
            modelo = self.var_modelo_ajuste.get()
            grau = {"Linear": 1, "Quadrático": 2, "Cúbico": 3}.get(modelo, 1)
            coef = np.polyfit(t_fit, y_fit, grau)
            pol = np.poly1d(coef)
            tt = np.linspace(float(np.min(t_fit)), float(np.max(t_fit)), 300)
            yy = pol(tt)
            y_pred = pol(t_fit)
            ss_res = float(np.sum((y_fit - y_pred) ** 2))
            ss_tot = float(np.sum((y_fit - np.mean(y_fit)) ** 2))
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 1.0

            ax.plot(tt, yy, linewidth=2.0, linestyle="--", color="#111827", label=f"ajuste {modelo.lower()}")
            ax.legend(fontsize=8)
            equacao = self.formatar_equacao_polinomial(simbolo, modelo, coef, r2)
            ax.text(
                0.02,
                0.08,
                equacao,
                transform=ax.transAxes,
                fontsize=8,
                va="bottom",
                bbox=dict(boxstyle="round", facecolor="white", edgecolor="#cbd5e1", alpha=0.92),
            )
        except (TypeError, ValueError, np.linalg.LinAlgError) as erro:
            ax.text(
                0.02,
                0.08,
                f"Ajuste não convergiu: {erro}",
                transform=ax.transAxes,
                fontsize=8,
                bbox=dict(boxstyle="round", facecolor="white", edgecolor="#cbd5e1", alpha=0.92),
            )

    def formatar_equacao_polinomial(self, simbolo, modelo, coef, r2):
        if modelo == "Linear":
            return f"Ajuste linear: {simbolo}(t) = {coef[0]:.4g}t + {coef[1]:.4g}\nR² = {r2:.5f}"
        if modelo == "Quadrático":
            return f"Ajuste quadrático: {simbolo}(t) = {coef[0]:.4g}t² + {coef[1]:.4g}t + {coef[2]:.4g}\nR² = {r2:.5f}"
        return f"Ajuste cúbico: {simbolo}(t) = {coef[0]:.4g}t³ + {coef[1]:.4g}t² + {coef[2]:.4g}t + {coef[3]:.4g}\nR² = {r2:.5f}"

    # -------------------------------------------------------------------------
    # TABELA, LEITURAS E STATUS
    # -------------------------------------------------------------------------
    def atualizar_tabela(self, forcar=False):
        if not hasattr(self, "tabela"):
            return

        self.contador_tabela += 1
        if self.rodando and not forcar and self.contador_tabela % 10 != 0:
            return

        for item in self.tabela.get_children():
            self.tabela.delete(item)

        selecionadas = self.obter_colunas_tabela()
        dados = self.obter_linhas_tabela()
        max_linhas = 350
        inicio = max(0, len(dados) - max_linhas)
        for i, linha in enumerate(dados[inicio:], start=inicio + 1):
            valores = [i]
            for grandeza in selecionadas:
                meta = self.mapa_tabela[grandeza]
                valores.append(formato_numero(linha[meta["chave"]], meta["casas"]))
            tag = "par" if i % 2 == 0 else "impar"
            self.tabela.insert("", "end", values=valores, tags=(tag,))

        filhos = self.tabela.get_children()
        if filhos:
            self.tabela.see(filhos[-1])

    def obter_linhas_tabela(self):
        linhas = []
        for i in range(len(self.t_hist)):
            linhas.append({
                "t": self.t_hist[i],
                "x": self.x_hist[i],
                "h": self.h_hist[i],
                "v": self.v_hist[i],
                "Ep": self.Ep_hist[i],
                "Ec": self.Ec_hist[i],
                "Em": self.Em_hist[i],
                "Ed": self.Ed_hist[i],
                "erro": self.erro_hist[i],
            })
        return linhas

    def atualizar_leituras(self):
        if not self.t_hist:
            return
        h, v, Ep, Ec, Em, Ed, erro = self.calcular_energias()
        self.var_leitura_t.set(f"{formato_numero(self.t, 3)} s")
        self.var_leitura_x.set(f"{formato_numero(self.x, 3)} m")
        self.var_leitura_h.set(f"{formato_numero(h, 3)} m")
        self.var_leitura_v.set(f"{formato_numero(v, 3)} m/s")
        self.var_leitura_Em.set(f"{formato_numero(Em, 3)} J")
        self.var_leitura_erro.set(f"{formato_numero(erro, 4)} %")

    def atualizar_status(self):
        if not self.Em_hist:
            self.var_status.set("Aguardando dados.")
            return
        Em = float(self.Em_hist[-1])
        erro = erro_percentual(Em, self.E0)
        fim = " | finalizado em h = 0 m" if self.finalizado else ""
        if self.var_atrito.get():
            Ed = max(0.0, self.E0 - Em)
            self.var_status.set(f"Com atrito: Em={Em:.4f} J | Em₀={self.E0:.4f} J | Ed={Ed:.4f} J{fim}")
        else:
            self.var_status.set(f"Sem atrito: Em={Em:.4f} J | Em₀={self.E0:.4f} J | erro={erro:.6f}%{fim}")

    # -------------------------------------------------------------------------
    # EXPORTAÇÃO
    # -------------------------------------------------------------------------
    def exportar_csv(self):
        if self.validar_parametros(mostrar_erro=True) is None:
            return
        if len(self.t_hist) < 2:
            messagebox.showinfo("Exportação", "Ainda não há dados suficientes para exportar.")
            return
        caminho = filedialog.asksaveasfilename(
            title="Salvar dados da simulação",
            defaultextension=".csv",
            filetypes=[("Arquivo CSV", "*.csv")],
            initialfile=f"dados_conservacao_energia_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )
        if not caminho:
            return

        try:
            with open(caminho, "w", newline="", encoding="utf-8-sig") as arquivo:
                escritor = csv.writer(arquivo, delimiter=";")
                escritor.writerow([NOME_APLICATIVO])
                escritor.writerow(["Versão", VERSAO_APLICATIVO])
                escritor.writerow(["Autor", AUTOR])
                escritor.writerow(["Exportado em", datetime.now().strftime("%d/%m/%Y %H:%M:%S")])
                escritor.writerow([])
                escritor.writerow([
                    "n", "tempo_s", "posicao_m", "altura_m", "velocidade_m_s",
                    "energia_potencial_J", "energia_cinetica_J", "energia_mecanica_J",
                    "energia_dissipada_J", "erro_percentual_Em",
                ])
                for i in range(len(self.t_hist)):
                    escritor.writerow([
                        i + 1, self.t_hist[i], self.x_hist[i], self.h_hist[i], self.v_hist[i],
                        self.Ep_hist[i], self.Ec_hist[i], self.Em_hist[i], self.Ed_hist[i], self.erro_hist[i],
                    ])
        except OSError as erro:
            messagebox.showerror("Erro ao exportar", f"Não foi possível salvar o CSV.\n\n{erro}")
            return
        messagebox.showinfo("Exportação concluída", f"Dados salvos em:\n{caminho}")

    def exportar_relatorio(self):
        valores = self.validar_parametros(mostrar_erro=True)
        if valores is None:
            return
        if len(self.t_hist) < 2:
            messagebox.showinfo("Relatório", "Ainda não há dados suficientes para gerar relatório.")
            return
        caminho = filedialog.asksaveasfilename(
            title="Salvar relatório automático",
            defaultextension=".txt",
            filetypes=[("Arquivo TXT", "*.txt")],
            initialfile=f"relatorio_conservacao_energia_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )
        if not caminho:
            return

        m, H, g, v0, b, dt, _ritmo = valores
        erro_medio = media(self.erro_hist)
        Em_min = min(self.Em_hist)
        Em_max = max(self.Em_hist)
        Ed_final = self.Ed_hist[-1]
        modo = "com atrito" if self.var_atrito.get() else "sem atrito"
        texto = f"""RELATÓRIO AUTOMÁTICO — CONSERVAÇÃO DA ENERGIA MECÂNICA

Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
Aplicação: {NOME_APLICATIVO} | versão {VERSAO_APLICATIVO}
Autor: {AUTOR}
Modo: {modo}
Percurso: {self.var_percurso.get()}

Parâmetros:
- massa: {m:.4f} kg
- altura máxima: {H:.4f} m
- gravidade: {g:.4f} m/s²
- velocidade inicial: {v0:.4f} m/s
- coeficiente dissipativo b: {b:.4f}
- passo Δt: {dt:.4f} s

Resultados principais:
- tempo final registrado: {self.t_hist[-1]:.4f} s
- posição final: {self.x_hist[-1]:.4f} m
- energia mecânica inicial: {self.E0:.6f} J
- energia mecânica mínima registrada: {Em_min:.6f} J
- energia mecânica máxima registrada: {Em_max:.6f} J
- erro percentual médio de conservação: {erro_medio:.6f} %
- energia dissipada final: {Ed_final:.6f} J

Interpretação didática:
Sem atrito, a energia mecânica total Em = Ep + Ec deve permanecer aproximadamente constante,
pois ocorre apenas transformação entre energia potencial gravitacional e energia cinética.
Com atrito, parte da energia mecânica é convertida em energia térmica, de modo que Em diminui
e a energia dissipada Ed aumenta ao longo do movimento.
"""
        try:
            with open(caminho, "w", encoding="utf-8-sig") as arquivo:
                arquivo.write(texto)
        except OSError as erro:
            messagebox.showerror("Erro ao exportar", f"Não foi possível salvar o relatório.\n\n{erro}")
            return
        messagebox.showinfo("Relatório concluído", f"Relatório salvo em:\n{caminho}")

    def exportar_roteiro_pre_pos_teste(self):
        caminho = filedialog.asksaveasfilename(
            title="Salvar roteiro didático",
            defaultextension=".txt",
            filetypes=[("Arquivo TXT", "*.txt")],
            initialfile=f"roteiro_pre_pos_energia_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )
        if not caminho:
            return

        texto = """ROTEIRO DIDÁTICO — CONSERVAÇÃO DA ENERGIA MECÂNICA

Público-alvo: Ensino Médio
Objetivo: analisar a transformação entre energia potencial gravitacional e energia cinética em uma pista.

PRÉ-TESTE
1. O que significa dizer que a energia mecânica é conservada?
2. Em uma descida sem atrito, o que acontece com a energia potencial gravitacional?
3. Em que ponto da pista a energia cinética tende a ser maior?
4. O atrito aumenta ou diminui a energia mecânica total? Explique.
5. Como deveria ser o gráfico de Em(t) em uma situação ideal sem atrito?

ATIVIDADE COM A SIMULAÇÃO
1. Escolha o percurso "Montanhas decrescentes" e deixe o atrito desligado.
2. Observe a animação e registre como Ep, Ec e Em se comportam.
3. Ative o atrito e compare o novo gráfico com o caso sem atrito.
4. Exporte os dados em CSV e calcule a variação percentual de Em.

PÓS-TESTE
1. A energia potencial desaparece ou se transforma? Justifique.
2. Por que Em(t) fica quase horizontal no caso sem atrito?
3. O que representa a energia dissipada Ed?
4. Como o atrito altera o movimento do carrinho?
5. Cite uma situação real em que a energia mecânica não se conserva totalmente.
"""
        try:
            with open(caminho, "w", encoding="utf-8-sig") as arquivo:
                arquivo.write(texto)
        except OSError as erro:
            messagebox.showerror("Erro ao exportar", f"Não foi possível salvar o roteiro.\n\n{erro}")
            return
        messagebox.showinfo("Roteiro concluído", f"Roteiro salvo em:\n{caminho}")

    # -------------------------------------------------------------------------
    # LOOP E FECHAMENTO
    # -------------------------------------------------------------------------
    def loop_animacao(self):
        if self.rodando:
            try:
                dt = converter_numero(self.var_dt.get())
                ritmo = converter_numero(self.var_ritmo.get())
            except (TypeError, ValueError):
                dt = 0.01
                ritmo = 2.0

            dt = clamp(dt, 0.001, 0.05)
            ritmo = clamp(ritmo, 0.5, 8.0)
            passos = max(1, int(round(ritmo)))

            for _ in range(passos):
                if self.finalizado:
                    break
                self.passo_rk4(dt)
                self.t += dt
                self.registrar_dados()

            self.atualizar_tudo(animacao=True)

        self.after_id = self.root.after(25, self.loop_animacao)

    def fechar(self):
        self.rodando = False
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except tk.TclError:
                pass
        self.root.destroy()

    def executar(self):
        self.loop_animacao()
        self.root.mainloop()


if __name__ == "__main__":
    raiz = tk.Tk()
    app = LaboratorioConservacaoEnergia(raiz)
    app.executar()

