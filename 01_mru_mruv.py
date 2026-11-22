# -*- coding: utf-8 -*-
"""
LABORATÓRIO VIRTUAL OFFLINE: MRU e MRUV — versão compacta Tkinter + Matplotlib

Autor: Mario Omar Calla Salcedo / Maestría Profesional en Enseñanza de la Física

Transformação do simulador originalmente feito em HTML/servidor local para uma
aplicação gráfica Python nativa, usando apenas os imports permitidos pelo usuário.

Recursos principais:
- Seleção entre MRU e MRUV.
- Simulação animada de carrinho sobre mesa com sensor, escala métrica e vetores.
- Gráficos dinâmicos em tempo real de x(t), v(t) e a(t), com seleção de visualização.
- Ajuste de curva opcional para x(t), usando scipy.optimize.curve_fit.
- Tabela experimental no formato grandeza versus tempo: x(t), v(t), a(t), dados completos ou dados com erro experimental.
- Coleta contínua, discreta ou manual, com intervalo de amostragem configurável.
- Erro experimental opcional na posição, com cálculo de erro absoluto, percentual e RMSE.
- Exportação CSV, relatório automático em TXT e roteiro de pré-teste/pós-teste.
- Painel de comando compacto para manter os controles visíveis na tela.
- Botões Iniciar, Pausar, Passo Δt, Resetar, Registrar ponto e Limpar tabela.
- Situações prontas para uso didático em sala de aula.

Observação:
Este arquivo não usa navegador, servidor local, HTML, JavaScript, socket,
threading, webbrowser ou qualquer biblioteca fora da lista autorizada.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch, Arc
from scipy.optimize import curve_fit
import csv
import math
import time
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as patches
from matplotlib.ticker import AutoMinorLocator


# =============================================================================
# IDENTIDADE VISUAL E LIMITES
# =============================================================================

NOME_APLICATIVO = "Laboratório Virtual — MRU e MRUV"
VERSAO_APLICATIVO = "2.1"
AUTOR = "Mario Omar Calla Salcedo"

COR_FUNDO = "#181426"
COR_PAINEL = "#232036"
COR_GRUPO = "#302b46"
COR_GRUPO_BORDA = "#64748b"
COR_CARD = "#f8fafc"
COR_TEXTO_CLARO = "#f8fafc"
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
COR_CENA_MRU = "#ecfeff"
COR_CENA_MRUV = "#fff7ed"
COR_GRAFICO = "#ffffff"
COR_GRADE = "#94a3b8"

DT_MIN = 0.001
DT_MAX = 1.0
RITMO_MIN = 0.01
RITMO_MAX = 16.0
INTERVALO_MIN = 0.001
MAX_DADOS = 5000
INTERVALO_GRAFICO_S = 0.12
INTERVALO_TABELA_S = 0.25

CORES_GRAFICOS = {
    "x": COR_AZUL,
    "v": COR_VERDE,
    "a": COR_VERMELHO,
}

CORES_FUNDO_GRAFICOS = {
    "x": "#eff6ff",
    "v": "#f0fdf4",
    "a": "#fff1f2",
}

CORES_GRUPOS = {
    "Modelo físico": "#67e8f9",
    "Visualização e coleta": "#f0abfc",
    "Controle da simulação": "#86efac",
    "Situações prontas": "#fdba74",
    "Uso didático": "#c4b5fd",
}


# =============================================================================
# FUNÇÕES MATEMÁTICAS PARA AJUSTE DE CURVA
# =============================================================================

def modelo_linear(t, c0, c1):
    """Modelo linear: x(t) = c0 + c1*t."""
    return c0 + c1 * t


def modelo_quadratico(t, c0, c1, c2):
    """Modelo quadrático: x(t) = c0 + c1*t + c2*t²."""
    return c0 + c1 * t + c2 * t * t


def arredondar_fisico(valor, casas=9):
    """
    Arredonda valores físicos para evitar pequenas oscilações numéricas de ponto flutuante.

    Exemplo: 0.15000000000000002 passa a 0.15. Isso é importante para que
    a tabela de MRUV mostre uma sequência regular quando a aceleração é constante.
    """
    try:
        numero = float(valor)
        return round(numero, casas) if math.isfinite(numero) else valor
    except (TypeError, ValueError):
        return valor


def formato_numero(valor, casas=3):
    """
    Converte número para texto com vírgula decimal usando arredondamento decimal.

    A tabela do MRUV precisa de mais casas decimais, porque, por exemplo,
    com a = 0,5 m/s² e Δt = 0,05 s, a variação correta da velocidade é
    Δv = a·Δt = 0,025 m/s. Se a tabela mostrar somente duas casas,
    essa variação aparece alternando entre 0,02 e 0,03, parecendo erro.
    """
    try:
        numero_float = float(valor)
        if not math.isfinite(numero_float):
            return "—"
        quantizador = Decimal("1").scaleb(-int(casas))
        numero = Decimal(str(numero_float)).quantize(quantizador, rounding=ROUND_HALF_UP)
        return f"{numero:.{int(casas)}f}".replace(".", ",")
    except (TypeError, ValueError, ArithmeticError):
        return str(valor)


# =============================================================================
# CLASSE PRINCIPAL DA APLICAÇÃO
# =============================================================================

class LaboratorioMRUMRUV:
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
        self.limite_atingido = False
        self.after_id = None
        self.proximo_t_discreto = 0.0
        self._suprimir_eventos = False
        self.ultimo_redesenho_grafico = 0.0
        self.ultimo_redesenho_tabela = 0.0

        # Variáveis Tkinter
        self.var_modo = tk.StringVar(value="MRU")
        self.var_x0 = tk.StringVar(value="0.00")
        self.var_v0 = tk.StringVar(value="0.40")
        self.var_a = tk.StringVar(value="0.00")
        self.var_L = tk.StringVar(value="2.00")
        self.var_tmax = tk.StringVar(value="5.00")
        self.var_dt = tk.StringVar(value="0.05")
        self.var_ritmo = tk.StringVar(value="1.00")
        self.var_grafico = tk.StringVar(value="Todos")
        self.var_ajuste = tk.BooleanVar(value=False)
        self.var_registro = tk.StringVar(value="Contínua")
        self.var_intervalo_discreto = tk.StringVar(value="0.25")
        self.var_erro_experimental = tk.BooleanVar(value=False)
        self.var_sigma_x = tk.StringVar(value="0.005")

        # Configuração da tabela experimental
        # A tabela principal fica, por padrão, em posição versus tempo: x(t).
        # O usuário pode trocar a grandeza dependente para velocidade ou aceleração.
        self.opcoes_tipo_tabela = [
            "Posição × Tempo",
            "Velocidade × Tempo",
            "Aceleração × Tempo",
            "Tabela completa: t, x, v, a",
            "Dados com erro experimental",
        ]
        self.var_tipo_tabela = tk.StringVar(value="Posição × Tempo")
        self.var_descricao_tabela = tk.StringVar(value="Tabela ativa: x em função de t.")
        self.mapa_grandezas_tabela = {
            # Colunas compactas: tempo e posição aparecem com 4 caracteres típicos,
            # por exemplo 0,00; 1,25; 2,00. Assim a tabela ocupa menos largura.
            # Usamos 3 casas decimais para preservar a regularidade do MRUV.
            # Ex.: a = 0,500 m/s² e Δt = 0,050 s => Δv = 0,025 m/s em cada passo.
            "Tempo": {"chave": "t", "titulo": "t", "csv": "tempo_s", "casas": 3, "largura": 58},
            "Posição": {"chave": "x", "titulo": "xₑ", "csv": "posicao_experimental_m", "casas": 3, "largura": 58},
            "Posição teórica": {"chave": "x_teo", "titulo": "xₜ", "csv": "posicao_teorica_m", "casas": 3, "largura": 58},
            "Velocidade": {"chave": "v", "titulo": "v", "csv": "velocidade_m_s", "casas": 3, "largura": 66},
            "Aceleração": {"chave": "a", "titulo": "a", "csv": "aceleracao_m_s2", "casas": 3, "largura": 66},
            "Erro absoluto": {"chave": "erro_x", "titulo": "Δx", "csv": "erro_absoluto_m", "casas": 4, "largura": 62},
            "Erro percentual": {"chave": "erro_x_pct", "titulo": "%", "csv": "erro_percentual", "casas": 2, "largura": 50},
        }

        self.var_status = tk.StringVar(value="Pronto para iniciar.")
        self.var_equacoes = tk.StringVar(value="")
        self.var_interpretacao = tk.StringVar(value="")

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
        estilo.configure("GroupTitle.TLabel", background=COR_GRUPO, foreground="#f0abfc", font=("Segoe UI", 8, "bold"))
        estilo.configure("CardTitle.TLabel", background=COR_CARD, foreground=COR_TEXTO_ESCURO, font=("Segoe UI", 10, "bold"))
        estilo.configure("Metric.TLabel", background="#cffafe", foreground="#155e75", font=("Segoe UI", 8))
        estilo.configure("MetricValue.TLabel", background="#cffafe", foreground="#164e63", font=("Segoe UI", 13, "bold"))
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
            text="Cinemática retilínea, aquisição de dados e análise experimental",
            style="SubTitle.TLabel"
        )
        subtitulo.grid(row=1, column=0, sticky="w", pady=(1, 0))

        selo = tk.Label(
            cabecalho,
            text=f"Versão {VERSAO_APLICATIVO} • Offline",
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

        titulo = tk.Label(
            painel,
            text="Painel de comando",
            bg=COR_PAINEL,
            fg="#a5f3fc",
            font=("Segoe UI", 10, "bold")
        )
        titulo.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 2))

        self.criar_grupo_modelo(painel, 1)
        self.criar_grupo_visualizacao(painel, 2)
        self.criar_grupo_botoes(painel, 3)
        self.criar_grupo_presets(painel, 4)

    def criar_grupo(self, parent, row, titulo):
        cor_destaque = CORES_GRUPOS.get(titulo, COR_GRUPO_BORDA)
        grupo = tk.Frame(parent, bg=COR_GRUPO, bd=0, highlightthickness=1, highlightbackground=cor_destaque)
        grupo.grid(row=row, column=0, sticky="ew", padx=5, pady=2)
        for c in range(3):
            grupo.columnconfigure(c, weight=1)

        lbl = tk.Label(
            grupo,
            text=titulo.upper(),
            bg=COR_GRUPO,
            fg=cor_destaque,
            font=("Segoe UI", 7, "bold")
        )
        lbl.grid(row=0, column=0, columnspan=3, sticky="w", padx=5, pady=(4, 1))
        return grupo

    def criar_grupo_modelo(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Modelo físico")

        self.criar_label_combo(grupo, 1, "Tipo de movimento", self.var_modo, ["MRU", "MRUV"])
        self.criar_linha_entradas(grupo, 2, "x₀ (m)", self.var_x0, "v₀ (m/s)", self.var_v0)
        self.criar_linha_entradas(grupo, 3, "a (m/s²)", self.var_a, "L mesa (m)", self.var_L)
        self.criar_linha_entradas(grupo, 4, "t máximo (s)", self.var_tmax, "Δt (s)", self.var_dt)

    def criar_grupo_visualizacao(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Visualização e coleta")
        self.criar_label_combo(grupo, 1, "Gráficos", self.var_grafico, ["Todos", "x(t)", "v(t)", "a(t)"])
        self.criar_label_combo(grupo, 2, "Ritmo", self.var_ritmo, [0.25, 0.5, 1.0, 2.0, 4.0])
        self.criar_label_combo(grupo, 3, "Tipo de coleta", self.var_registro, ["Contínua", "Discreta", "Manual"])
        self.criar_linha_entradas(grupo, 4, "Δt coleta (s)", self.var_intervalo_discreto, "σx erro (m)", self.var_sigma_x)

        chk_ajuste = tk.Checkbutton(
            grupo,
            text="Ajuste x(t)",
            variable=self.var_ajuste,
            bg=COR_GRUPO,
            fg=COR_TEXTO_CLARO,
            activebackground=COR_GRUPO,
            activeforeground="#ffffff",
            selectcolor="#111827",
            font=("Segoe UI", 7)
        )
        chk_ajuste.grid(row=5, column=0, sticky="w", padx=5, pady=(1, 4))

        chk_erro = tk.Checkbutton(
            grupo,
            text="Erro exp.",
            variable=self.var_erro_experimental,
            bg=COR_GRUPO,
            fg=COR_TEXTO_CLARO,
            activebackground=COR_GRUPO,
            activeforeground="#ffffff",
            selectcolor="#111827",
            font=("Segoe UI", 7)
        )
        chk_erro.grid(row=5, column=1, columnspan=2, sticky="w", padx=5, pady=(1, 4))

    def criar_grupo_botoes(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Controle da simulação")

        self.btn_iniciar = ttk.Button(grupo, text="Iniciar", style="Success.TButton", command=self.iniciar)
        self.btn_pausar = ttk.Button(grupo, text="Pausar", style="Warning.TButton", command=self.pausar)
        self.btn_passo = ttk.Button(grupo, text="Passo", command=self.passo)
        self.btn_reset = ttk.Button(grupo, text="Resetar", style="Danger.TButton", command=lambda: self.reiniciar_simulacao(limpar_tabela=True))
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
        b1 = ttk.Button(grupo, text="MRU lento", command=lambda: self.aplicar_preset(1))
        b2 = ttk.Button(grupo, text="MRU rápido", command=lambda: self.aplicar_preset(2))
        b3 = ttk.Button(grupo, text="MRUV acelerado", command=lambda: self.aplicar_preset(3))
        b1.grid(row=1, column=0, sticky="ew", padx=2, pady=2)
        b2.grid(row=1, column=1, sticky="ew", padx=2, pady=2)
        b3.grid(row=1, column=2, sticky="ew", padx=2, pady=2)
        grupo.columnconfigure(2, weight=1)
        grupo.columnconfigure(0, weight=1)
        grupo.columnconfigure(1, weight=1)

    def criar_grupo_didatico(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Uso didático")
        texto = (
            "Sugestão: peça aos estudantes que prevejam o formato dos gráficos antes de iniciar. "
            "Depois, comparem a animação, a tabela e os gráficos para discutir velocidade constante, "
            "aceleração constante e inclinação de x(t)."
        )
        lbl = tk.Label(
            grupo,
            text=texto,
            bg=COR_GRUPO,
            fg=COR_TEXTO_CLARO,
            font=("Segoe UI", 8),
            wraplength=245,
            justify="left"
        )
        lbl.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))

    def criar_label_combo(self, parent, row, texto, variavel, opcoes):
        lbl = tk.Label(parent, text=texto, bg=COR_GRUPO, fg=COR_TEXTO_CLARO, font=("Segoe UI", 7))
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

        tk.Label(f1, text=texto1, bg=COR_GRUPO, fg=COR_TEXTO_CLARO, font=("Segoe UI", 7)).grid(row=0, column=0, sticky="w")
        e1 = ttk.Entry(f1, textvariable=var1, font=("Segoe UI", 7), width=6)
        e1.grid(row=1, column=0, sticky="ew")

        tk.Label(f2, text=texto2, bg=COR_GRUPO, fg=COR_TEXTO_CLARO, font=("Segoe UI", 7)).grid(row=0, column=0, sticky="w")
        e2 = ttk.Entry(f2, textvariable=var2, font=("Segoe UI", 7), width=6)
        e2.grid(row=1, column=0, sticky="ew")

        e1.bind("<FocusOut>", lambda event: self.configuracao_alterada())
        e2.bind("<FocusOut>", lambda event: self.configuracao_alterada())

    def criar_area_trabalho(self, parent):
        area = tk.Frame(parent, bg=COR_FUNDO)
        area.grid(row=0, column=1, sticky="nsew")
        area.columnconfigure(0, weight=1)
        # Tabela lateral estreita: libera mais espaço para a animação e gráficos.
        area.columnconfigure(1, weight=0, minsize=225)
        area.rowconfigure(0, weight=1)

        # Área esquerda: cena experimental acima e gráficos abaixo.
        visual = tk.Frame(area, bg=COR_FUNDO)
        visual.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        visual.columnconfigure(0, weight=1)
        # Divisão equilibrada: experiência visível e gráficos sem cortes.
        visual.rowconfigure(0, weight=12, minsize=0, uniform="visual_split")
        visual.rowconfigure(1, weight=13, minsize=0, uniform="visual_split")

        self.criar_cena(visual)
        self.criar_graficos(visual, row=1, column=0, padx=(0, 0))

        # Área direita: tabela vertical ocupando toda a altura, do topo ao rodapé.
        self.criar_tabela_e_leituras(area)

    def criar_cena(self, parent):
        card = tk.Frame(parent, bg=COR_CARD, bd=0, highlightthickness=1, highlightbackground=COR_CIANO)
        card.grid(row=0, column=0, sticky="nsew", pady=(0, 4))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=1)

        # Sem cabeçalho interno: a cena sobe e libera altura para as gráficas.
        self.fig_cena = Figure(figsize=(8, 3.6), dpi=100, facecolor=COR_CARD)
        self.ax_cena = self.fig_cena.add_subplot(111)
        self.canvas_cena = FigureCanvasTkAgg(self.fig_cena, master=card)
        self.canvas_cena.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=4)

    def criar_inferior(self, parent):
        inferior = tk.Frame(parent, bg=COR_FUNDO)
        inferior.grid(row=1, column=0, sticky="nsew")
        inferior.columnconfigure(0, weight=3)
        inferior.columnconfigure(1, weight=2)
        inferior.rowconfigure(0, weight=1)

        self.criar_graficos(inferior)
        self.criar_tabela_e_leituras(inferior)

    def criar_graficos(self, parent, row=0, column=0, padx=(0, 8)):
        card = tk.Frame(parent, bg=COR_CARD, bd=0, highlightthickness=1, highlightbackground=COR_ROXO)
        card.grid(row=row, column=column, sticky="nsew", padx=padx)
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=0)
        card.rowconfigure(1, weight=1)

        topo = tk.Frame(card, bg=COR_CARD)
        topo.grid(row=0, column=0, sticky="ew", padx=6, pady=(3, 0))
        topo.columnconfigure(0, weight=1)

        tk.Label(
            topo,
            text="Gráficos em tempo real",
            bg=COR_CARD,
            fg=COR_TEXTO_ESCURO,
            font=("Segoe UI", 9, "bold")
        ).grid(row=0, column=0, sticky="w")

        self.lbl_nota_grafico = tk.Label(
            topo,
            text="Mostrando x(t), v(t) e a(t).",
            bg=COR_CARD,
            fg=COR_TEXTO_SECUNDARIO,
            font=("Segoe UI", 7)
        )
        self.lbl_nota_grafico.grid(row=0, column=1, sticky="e")

        self.fig_graficos = Figure(figsize=(7.2, 3.8), dpi=100, facecolor=COR_CARD)
        self.canvas_graficos = FigureCanvasTkAgg(self.fig_graficos, master=card)
        self.canvas_graficos.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=5, pady=(2, 5))

    def criar_tabela_e_leituras(self, parent):
        card = tk.Frame(parent, bg=COR_CARD, bd=0, highlightthickness=1, highlightbackground=COR_LARANJA, width=225)
        card.grid(row=0, column=1, sticky="nsew")
        card.grid_propagate(False)
        card.columnconfigure(0, weight=1)
        card.rowconfigure(2, weight=1)

        topo = tk.Frame(card, bg=COR_CARD)
        topo.grid(row=0, column=0, sticky="ew", padx=8, pady=(7, 4))
        topo.columnconfigure(0, weight=1)

        tk.Label(
            topo,
            text="Tabela experimental",
            bg=COR_CARD,
            fg=COR_TEXTO_ESCURO,
            font=("Segoe UI", 10, "bold")
        ).grid(row=0, column=0, sticky="w")

        tk.Label(
            topo,
            text="dados",
            bg=COR_CARD,
            fg=COR_LARANJA,
            font=("Segoe UI", 8, "bold")
        ).grid(row=0, column=1, sticky="e")

        painel_tabela = tk.Frame(card, bg="#cffafe", bd=0, highlightthickness=1, highlightbackground="#22d3ee")
        painel_tabela.grid(row=1, column=0, sticky="ew", padx=7, pady=(0, 6))
        painel_tabela.columnconfigure(1, weight=1)

        tk.Label(
            painel_tabela,
            text="Grandeza",
            bg="#cffafe",
            fg="#164e63",
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
            bg="#cffafe",
            fg="#155e75",
            font=("Segoe UI", 8),
            justify="left",
            wraplength=205
        ).grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(2, 7))

        frame_tabela = tk.Frame(card, bg=COR_CARD)
        frame_tabela.grid(row=2, column=0, sticky="nsew", padx=7, pady=(0, 7))
        frame_tabela.columnconfigure(0, weight=1)
        frame_tabela.rowconfigure(0, weight=1)

        self.tabela = ttk.Treeview(frame_tabela, columns=(), show="headings", height=28)
        self.tabela.tag_configure("linha_par", background="#ecfeff")
        self.tabela.tag_configure("linha_impar", background="#fff7ed")
        barra_y = ttk.Scrollbar(frame_tabela, orient="vertical", command=self.tabela.yview)
        barra_x = ttk.Scrollbar(frame_tabela, orient="horizontal", command=self.tabela.xview)
        self.tabela.configure(yscrollcommand=barra_y.set, xscrollcommand=barra_x.set)
        self.tabela.grid(row=0, column=0, sticky="nsew")
        barra_y.grid(row=0, column=1, sticky="ns")
        barra_x.grid(row=1, column=0, sticky="ew")

        self.aplicar_configuracao_tabela()

    def obter_colunas_tabela(self):
        tipo = self.var_tipo_tabela.get()

        if tipo == "Velocidade × Tempo":
            return ["Tempo", "Velocidade"]
        if tipo == "Aceleração × Tempo":
            return ["Tempo", "Aceleração"]
        if tipo == "Tabela completa: t, x, v, a":
            return ["Tempo", "Posição", "Velocidade", "Aceleração"]
        if tipo == "Dados com erro experimental":
            return ["Tempo", "Posição", "Posição teórica", "Erro absoluto", "Erro percentual"]

        # Configuração padrão: posição versus tempo.
        return ["Tempo", "Posição"]

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
        if tipo == "Velocidade × Tempo":
            self.var_descricao_tabela.set("Tabela ativa: v em função de t, com 3 casas decimais.")
        elif tipo == "Aceleração × Tempo":
            self.var_descricao_tabela.set("Tabela ativa: a em função de t, com 3 casas decimais.")
        elif tipo == "Tabela completa: t, x, v, a":
            self.var_descricao_tabela.set("Tabela ativa: t, x, v e a, com 3 casas decimais.")
        elif tipo == "Dados com erro experimental":
            self.var_descricao_tabela.set("Tabela ativa: x experimental, x teórica, erro absoluto e erro percentual.")
        else:
            self.var_descricao_tabela.set("Tabela ativa: x em função de t, com 3 casas decimais.")

        self.atualizar_tabela()

    # -------------------------------------------------------------------------
    # EVENTOS E VALIDAÇÃO
    # -------------------------------------------------------------------------
    def configurar_eventos(self):
        variaveis = [
            self.var_modo, self.var_x0, self.var_v0, self.var_a, self.var_L,
            self.var_tmax, self.var_dt, self.var_ritmo, self.var_grafico,
            self.var_registro, self.var_tipo_tabela, self.var_intervalo_discreto,
            self.var_sigma_x, self.var_erro_experimental, self.var_ajuste,
        ]
        for var in variaveis:
            var.trace_add("write", lambda *args: self.configuracao_alterada(suave=True))

        self.root.protocol("WM_DELETE_WINDOW", self.fechar)

    def configuracao_alterada(self, suave=False):
        if self._suprimir_eventos:
            return

        if self.var_modo.get() == "MRU":
            try:
                aceleracao = self.ler_numero(self.var_a, "aceleração")
            except ValueError:
                aceleracao = None
            if aceleracao is None or abs(aceleracao) > 1e-12:
                self._suprimir_eventos = True
                try:
                    self.var_a.set("0.00")
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
            L = self.ler_numero(self.var_L, "comprimento da mesa")
            tmax = self.ler_numero(self.var_tmax, "tempo máximo")
            dt = self.ler_numero(self.var_dt, "passo Δt")
            x0 = self.ler_numero(self.var_x0, "posição inicial")
            self.ler_numero(self.var_v0, "velocidade inicial")
            self.ler_numero(self.var_a, "aceleração")
            ritmo = self.ler_numero(self.var_ritmo, "ritmo")
            intervalo_discreto = self.ler_numero(self.var_intervalo_discreto, "intervalo de coleta")
            sigma_x = self.ler_numero(self.var_sigma_x, "incerteza σx")
        except ValueError as erro:
            if mostrar_erro:
                messagebox.showerror("Erro nos parâmetros", str(erro))
            return False

        mensagens = []
        if L <= 0:
            mensagens.append("O comprimento da mesa deve ser maior que zero.")
        if tmax <= 0:
            mensagens.append("O tempo máximo deve ser maior que zero.")
        if not (DT_MIN <= dt <= DT_MAX):
            mensagens.append(f"O passo Δt deve ficar entre {DT_MIN:g} s e {DT_MAX:g} s.")
        if dt > tmax:
            mensagens.append("O passo Δt não deve ser maior que o tempo máximo.")
        if x0 < 0 or x0 > L:
            mensagens.append("A posição inicial x₀ deve estar entre 0 e L.")
        if not (RITMO_MIN <= ritmo <= RITMO_MAX):
            mensagens.append(f"O ritmo deve ficar entre {RITMO_MIN:g} e {RITMO_MAX:g}.")
        if intervalo_discreto < INTERVALO_MIN:
            mensagens.append(f"O intervalo da coleta discreta deve ser pelo menos {INTERVALO_MIN:g} s.")
        if sigma_x < 0:
            mensagens.append("O erro experimental σx não pode ser negativo.")

        if mensagens:
            if mostrar_erro:
                messagebox.showerror("Parâmetros inválidos", "\n".join(mensagens))
            return False
        return True

    # -------------------------------------------------------------------------
    # FÍSICA DO MOVIMENTO
    # -------------------------------------------------------------------------
    def obter_config(self):
        modo = self.var_modo.get()
        x0 = self.ler_numero(self.var_x0, "posição inicial")
        v0 = self.ler_numero(self.var_v0, "velocidade inicial")
        a = 0.0 if modo == "MRU" else self.ler_numero(self.var_a, "aceleração")
        L = max(self.ler_numero(self.var_L, "comprimento da mesa"), 0.01)
        tmax = max(self.ler_numero(self.var_tmax, "tempo máximo"), 0.01)
        dt = min(max(self.ler_numero(self.var_dt, "passo Δt"), DT_MIN), DT_MAX)
        ritmo = min(max(self.ler_numero(self.var_ritmo, "ritmo"), RITMO_MIN), RITMO_MAX)
        return modo, x0, v0, a, L, tmax, dt, ritmo

    def fisica_em(self, tempo):
        modo, x0, v0, a, L, tmax, dt, ritmo = self.obter_config()
        if modo == "MRU":
            a = 0.0
            x = x0 + v0 * tempo
            v = v0
        else:
            x = x0 + v0 * tempo + 0.5 * a * tempo * tempo
            v = v0 + a * tempo
        x_clamp = min(max(x, 0.0), L)
        return {
            "t": arredondar_fisico(tempo),
            "x": arredondar_fisico(x_clamp),
            "x_real": arredondar_fisico(x),
            "v": arredondar_fisico(v),
            "a": arredondar_fisico(a),
            "modo": modo,
            "L": L,
            "tmax": tmax,
            "dt": dt,
            "ritmo": ritmo
        }

    def tempo_impacto_limite(self, t_antigo, t_novo):
        """Calcula, quando possível, o instante em que o carrinho toca x=0 ou x=L."""
        modo, x0, v0, a, L, tmax, dt, ritmo = self.obter_config()
        candidatos = []

        if modo == "MRU" or abs(a) < 1e-12:
            if abs(v0) > 1e-12:
                for alvo in (0.0, L):
                    tc = (alvo - x0) / v0
                    if t_antigo <= tc <= t_novo:
                        candidatos.append(tc)
        else:
            for alvo in (0.0, L):
                # 0.5*a*t² + v0*t + (x0 - alvo) = 0
                A = 0.5 * a
                B = v0
                C = x0 - alvo
                delta = B * B - 4.0 * A * C
                if delta >= 0:
                    raiz = math.sqrt(delta)
                    for tc in ((-B - raiz) / (2.0 * A), (-B + raiz) / (2.0 * A)):
                        if t_antigo <= tc <= t_novo:
                            candidatos.append(tc)

        if candidatos:
            return min(candidatos)
        return None

    # -------------------------------------------------------------------------
    # CONTROLE DA SIMULAÇÃO
    # -------------------------------------------------------------------------
    def iniciar(self):
        if not self.validar_parametros(mostrar_erro=True):
            return
        if self.rodando:
            return
        if self.limite_atingido:
            self.reiniciar_simulacao(limpar_tabela=True)
        self.rodando = True
        agora = time.perf_counter()
        self.ultimo_redesenho_grafico = agora
        self.ultimo_redesenho_tabela = agora
        self.var_status.set("Simulação em andamento.")
        self.agendar_animacao()

    def pausar(self):
        self.rodando = False
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
        modo, x0, v0, a, L, tmax, dt, ritmo = self.obter_config()
        self.avancar(dt)
        if not self.limite_atingido:
            self.var_status.set("Avanço de um passo Δt realizado.")

    def agendar_animacao(self):
        if self.rodando:
            self.after_id = self.root.after(25, self.loop_animacao)

    def loop_animacao(self):
        if not self.rodando:
            return
        try:
            modo, x0, v0, a, L, tmax, dt, ritmo = self.obter_config()
            incremento = dt * ritmo
            self.avancar(incremento, animacao=True)
        except Exception as erro:
            self.rodando = False
            messagebox.showerror("Erro durante a simulação", str(erro))
            return
        self.agendar_animacao()

    def avancar(self, incremento, animacao=False):
        modo, x0, v0, a, L, tmax, dt, ritmo = self.obter_config()
        if self.limite_atingido:
            return

        t_antigo = self.t
        # Mantém o tempo nos múltiplos esperados de Δt e evita acúmulo de erro
        # como 0.15000000000000002, que prejudica a leitura da tabela.
        t_novo = arredondar_fisico(min(self.t + incremento, tmax))
        p_novo = self.fisica_em(t_novo)

        cruzou_limite = p_novo["x_real"] < 0.0 or p_novo["x_real"] > L
        if cruzou_limite:
            t_limite = self.tempo_impacto_limite(t_antigo, t_novo)
            if t_limite is not None:
                self.t = min(max(t_limite, 0.0), tmax)
            else:
                self.t = t_novo
            self.limite_atingido = True
            self.rodando = False
            self.var_status.set("O carrinho atingiu o limite da mesa.")
        else:
            self.t = t_novo
            if self.t >= tmax:
                self.limite_atingido = True
                self.rodando = False
                self.var_status.set("Tempo máximo atingido.")

        modo_registro = self.var_registro.get()
        if modo_registro == "Contínua":
            self.registrar_ponto(forcar=False)
        elif modo_registro == "Discreta":
            self.registrar_ponto_discreto()

        if animacao:
            self.atualizar_modelo_didatico()
            self.desenhar_cena()
            agora = time.perf_counter()
            if self.limite_atingido or agora - self.ultimo_redesenho_grafico >= INTERVALO_GRAFICO_S:
                self.desenhar_graficos()
                self.ultimo_redesenho_grafico = agora
            if self.limite_atingido or agora - self.ultimo_redesenho_tabela >= INTERVALO_TABELA_S:
                self.atualizar_tabela()
                self.ultimo_redesenho_tabela = agora
        else:
            self.atualizar_tudo()

    def reiniciar_simulacao(self, limpar_tabela=True):
        if not self.validar_parametros(mostrar_erro=True):
            return
        self.rodando = False
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except Exception:
                pass
        self.after_id = None
        self.t = 0.0
        self.limite_atingido = False
        if limpar_tabela:
            self.dados = []
            self.indice = 0
        self.proximo_t_discreto = 0.0
        self.registrar_ponto(forcar=True)
        try:
            self.proximo_t_discreto = max(
                self.ler_numero(self.var_intervalo_discreto, "intervalo de coleta"),
                self.ler_numero(self.var_dt, "passo Δt"),
                INTERVALO_MIN,
            )
        except ValueError:
            self.proximo_t_discreto = 0.25
        agora = time.perf_counter()
        self.ultimo_redesenho_grafico = agora
        self.ultimo_redesenho_tabela = agora
        self.var_status.set("Simulação reiniciada.")
        self.atualizar_tudo()

    def limpar_tabela(self):
        if not self.validar_parametros(mostrar_erro=True):
            return
        self.dados = []
        self.indice = 0
        self.proximo_t_discreto = 0.0
        self.registrar_ponto(forcar=True)
        try:
            self.proximo_t_discreto = max(
                self.ler_numero(self.var_intervalo_discreto, "intervalo de coleta"),
                self.ler_numero(self.var_dt, "passo Δt"),
                INTERVALO_MIN,
            )
        except ValueError:
            self.proximo_t_discreto = 0.25
        self.var_status.set("Tabela limpa e ponto inicial registrado.")
        self.atualizar_tudo()

    def registrar_ponto_manual(self):
        if not self.validar_parametros(mostrar_erro=True):
            return
        self.registrar_ponto(forcar=True)
        self.var_status.set("Ponto experimental registrado manualmente.")
        self.atualizar_tabela()
        self.desenhar_graficos()

    def registrar_ponto_discreto(self):
        """Registra pontos somente quando o tempo alcança o intervalo de coleta definido."""
        try:
            intervalo = max(
                self.ler_numero(self.var_intervalo_discreto, "intervalo de coleta"),
                self.ler_numero(self.var_dt, "passo Δt"),
                INTERVALO_MIN,
            )
        except ValueError:
            intervalo = 0.25

        if self.t + 1e-10 >= self.proximo_t_discreto:
            self.registrar_ponto(forcar=False)
            while self.proximo_t_discreto <= self.t + 1e-10:
                self.proximo_t_discreto = arredondar_fisico(self.proximo_t_discreto + intervalo)

    def registrar_ponto(self, forcar=False):
        p = self.fisica_em(self.t)
        if self.dados and not forcar:
            ultimo = self.dados[-1]
            if abs(ultimo.get("t_teo", ultimo["t"]) - p["t"]) < 1e-10:
                return

        x_teorico = float(p["x"])
        sigma_x = max(self.ler_numero(self.var_sigma_x, "incerteza σx"), 0.0)
        erro_aplicado = 0.0
        if self.var_erro_experimental.get() and sigma_x > 0:
            erro_aplicado = float(np.random.normal(0.0, sigma_x))

        x_experimental = x_teorico + erro_aplicado
        erro_abs = x_experimental - x_teorico
        if abs(x_teorico) > 1e-12:
            erro_pct = 100.0 * erro_abs / x_teorico
        else:
            erro_pct = 0.0 if abs(erro_abs) < 1e-12 else 100.0

        self.dados.append({
            "n": self.indice,
            "t": p["t"],
            "t_teo": p["t"],
            "x": arredondar_fisico(x_experimental),
            "x_teo": arredondar_fisico(x_teorico),
            "v": p["v"],
            "a": p["a"],
            "erro_x": arredondar_fisico(erro_abs),
            "erro_x_pct": arredondar_fisico(erro_pct),
            "sigma_x": sigma_x,
            "modo": p["modo"]
        })
        self.indice += 1
        if len(self.dados) > MAX_DADOS:
            self.dados = self.dados[-MAX_DADOS:]

    def aplicar_preset(self, numero):
        self.pausar()
        self._suprimir_eventos = True
        try:
            if numero == 1:
                valores = ("MRU", "0.00", "0.35", "0.00", "2.00", "5.00", "0.05")
                status = "Situação pronta: MRU lento."
            elif numero == 2:
                valores = ("MRU", "0.00", "0.75", "0.00", "2.00", "4.00", "0.05")
                status = "Situação pronta: MRU rápido."
            else:
                valores = ("MRUV", "0.00", "0.10", "0.35", "2.00", "5.00", "0.05")
                status = "Situação pronta: MRUV com aceleração constante."
            variaveis = (
                self.var_modo, self.var_x0, self.var_v0, self.var_a,
                self.var_L, self.var_tmax, self.var_dt,
            )
            for variavel, valor in zip(variaveis, valores):
                variavel.set(valor)
        finally:
            self._suprimir_eventos = False
        self.reiniciar_simulacao(limpar_tabela=True)
        self.var_status.set(status)

    # -------------------------------------------------------------------------
    # ATUALIZAÇÃO VISUAL
    # -------------------------------------------------------------------------
    def atualizar_tudo(self):
        if not self.validar_parametros(mostrar_erro=False):
            return
        self.atualizar_modelo_didatico()
        self.desenhar_cena()
        self.desenhar_graficos()
        self.atualizar_tabela()

    def atualizar_modelo_didatico(self):
        modo, x0, v0, a, L, tmax, dt, ritmo = self.obter_config()
        if modo == "MRU":
            eq = (
                "Modelo: MRU\n"
                "x(t) = x₀ + v·t\n"
                f"x(t) = {formato_numero(x0,2)} + ({formato_numero(v0,2)})·t\n"
                f"v(t) = {formato_numero(v0,2)} m/s\n"
                "a(t) = 0 m/s²"
            )
            interp = (
                "Interpretação didática: no MRU, a velocidade é constante, "
                "o gráfico x(t) é uma reta e o gráfico a(t) permanece em zero."
            )
        else:
            eq = (
                "Modelo: MRUV\n"
                "x(t) = x₀ + v₀·t + ½a·t²\n"
                f"x(t) = {formato_numero(x0,2)} + ({formato_numero(v0,2)})·t + ½({formato_numero(a,2)})·t²\n"
                f"v(t) = {formato_numero(v0,2)} + ({formato_numero(a,2)})·t\n"
                f"a(t) = {formato_numero(a,2)} m/s²"
            )
            delta_v = a * dt * ritmo
            interp = (
                "Interpretação didática: no MRUV, a aceleração constante altera a velocidade; "
                "por isso, x(t) se torna parabólico e v(t) se torna linear. "
                f"Em cada avanço temporal desta configuração, Δv = a·Δt·ritmo = {formato_numero(delta_v,3)} m/s."
            )

        modo_coleta = self.var_registro.get()
        if modo_coleta == "Discreta":
            intervalo = self.ler_numero(self.var_intervalo_discreto, "intervalo de coleta")
            interp += f" Coleta discreta ativa: um ponto a cada {formato_numero(intervalo, 3)} s."
        elif modo_coleta == "Manual":
            interp += " Coleta manual ativa: use o botão Registrar ponto para montar a tabela."
        else:
            interp += " Coleta contínua ativa: a tabela acompanha cada avanço temporal."

        if self.var_erro_experimental.get():
            sigma = self.ler_numero(self.var_sigma_x, "incerteza σx")
            interp += f" Erro experimental simulado: posição medida xₑ = xₜ + ruído normal com σx = {formato_numero(sigma, 4)} m."

        self.var_equacoes.set(eq)
        self.var_interpretacao.set(interp)

    def desenhar_cena(self):
        p = self.fisica_em(self.t)
        modo, x0, v0, a, L, tmax, dt, ritmo = self.obter_config()

        ax = self.ax_cena
        ax.clear()
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

        # Fundo
        cor_cena = COR_CENA_MRU if modo == "MRU" else COR_CENA_MRUV
        cor_modo = COR_CIANO if modo == "MRU" else COR_LARANJA
        ax.add_patch(Rectangle((0, 0), 1, 1, facecolor=cor_cena, edgecolor="none"))
        ax.text(
            0.035,
            0.92,
            f"{modo}  |  t = {formato_numero(self.t, 2)} s",
            fontsize=8.5,
            weight="bold",
            color="#164e63" if modo == "MRU" else "#9a3412",
            bbox=dict(boxstyle="round,pad=0.30", facecolor="#cffafe" if modo == "MRU" else "#ffedd5", edgecolor=cor_modo, alpha=0.96),
        )
        ax.text(
            0.965,
            0.92,
            f"v = {formato_numero(p['v'], 2)} m/s   a = {formato_numero(p['a'], 2)} m/s²",
            ha="right",
            fontsize=8.2,
            weight="bold",
            color="#701a75",
            bbox=dict(boxstyle="round,pad=0.30", facecolor="#fae8ff", edgecolor=COR_MAGENTA, alpha=0.96),
        )
        # Cabeçalho interno removido para deixar a experiência visual mais limpa
        # e aproveitar melhor a altura da cena animada.

        left = 0.09
        right = 0.94
        table_y = 0.36
        table_h = 0.055
        usable = right - left
        x_px = left + (p["x"] / L) * usable if L > 0 else left

        # Sombra e mesa
        ax.add_patch(patches.Ellipse((0.52, 0.18), 0.74, 0.045, facecolor="#0f172a", alpha=0.12, edgecolor="none"))
        ax.add_patch(FancyBboxPatch((left, table_y), usable, table_h, boxstyle="round,pad=0.004,rounding_size=0.014", facecolor="#0f766e", edgecolor="#134e4a", linewidth=1.4))
        ax.add_patch(Rectangle((left + 0.025, 0.10), 0.018, table_y - 0.10, facecolor="#334155", edgecolor="none"))
        ax.add_patch(Rectangle((right - 0.043, 0.10), 0.018, table_y - 0.10, facecolor="#334155", edgecolor="none"))

        # Escala métrica
        for i in range(11):
            xx = left + i * usable / 10
            tamanho = 0.058 if i % 5 == 0 else 0.037
            ax.plot([xx, xx], [table_y + table_h + 0.004, table_y + table_h + tamanho], color="#134e4a", linewidth=0.9)
            if i % 2 == 0:
                valor = L * i / 10
                ax.text(xx - 0.025, table_y + table_h + tamanho + 0.018, f"{formato_numero(valor,1)} m", fontsize=7.2, color="#0f172a")

        ax.text(left - 0.006, table_y - 0.055, "0 m", fontsize=8, weight="bold", color="#0f172a")
        ax.text(right - 0.034, table_y - 0.055, f"{formato_numero(L,1)} m", fontsize=8, weight="bold", color="#0f172a")

        # Sensor
        sensor_x = left - 0.055
        sensor_y = table_y + table_h + 0.03
        ax.add_patch(FancyBboxPatch((sensor_x, sensor_y), 0.038, 0.135, boxstyle="round,pad=0.004,rounding_size=0.012", facecolor="#4338ca", edgecolor="#312e81", linewidth=1.2))
        ax.add_patch(Circle((sensor_x + 0.019, sensor_y + 0.074), 0.010, facecolor=COR_AMARELO, edgecolor="#fef9c3", linewidth=0.8))
        ax.text(sensor_x - 0.012, sensor_y + 0.153, "sensor", fontsize=7.5, weight="bold", color="#0f172a")

        for largura in (0.07, 0.12, 0.17, 0.22):
            ax.add_patch(Arc((sensor_x + 0.038, sensor_y + 0.074), largura, largura * 0.72, angle=0, theta1=-35, theta2=35, color=COR_CIANO, alpha=0.52, linewidth=1.2))

        # Carrinho
        if len(self.dados) > 1 and L > 0:
            posicoes_recentes = []
            for dado in self.dados[-36:]:
                x_dado = min(max(float(dado.get("x_teo", dado.get("x", 0.0))), 0.0), L)
                posicoes_recentes.append(left + (x_dado / L) * usable)
            ax.scatter(
                posicoes_recentes,
                [table_y + table_h + 0.012] * len(posicoes_recentes),
                s=13,
                color=COR_CIANO,
                alpha=0.48,
                edgecolors="none",
                zorder=3,
            )
        self.desenhar_carrinho(ax, x_px, table_y + table_h + 0.105)

        # Marcador de posição
        ax.plot([x_px, x_px], [table_y + table_h + 0.005, table_y + 0.42], color=COR_MAGENTA, linewidth=1.5, linestyle="--", alpha=0.88)
        ax.text(max(0.02, min(0.88, x_px - 0.035)), table_y + 0.435, f"x = {formato_numero(p['x'],2)} m", fontsize=8, weight="bold", color="#86198f")
        if self.var_erro_experimental.get():
            sigma = self.ler_numero(self.var_sigma_x, "incerteza σx")
            ax.text(0.70, 0.82, f"erro experimental: σx = {formato_numero(sigma,4)} m", fontsize=7.4, color="#7c2d12",
                    bbox=dict(boxstyle="round,pad=0.25", facecolor="#ffedd5", edgecolor=COR_LARANJA, alpha=0.96))

        # Vetores de velocidade e aceleração
        base_y = table_y + 0.54
        v_len = max(-0.17, min(0.17, p["v"] * 0.13))
        if abs(p["v"]) > 0.01:
            self.desenhar_vetor(ax, x_px, base_y, x_px + v_len, base_y, COR_AZUL, "v")

        a_len = max(-0.17, min(0.17, p["a"] * 0.20))
        if abs(p["a"]) > 0.01:
            self.desenhar_vetor(ax, x_px, base_y + 0.095, x_px + a_len, base_y + 0.095, COR_LARANJA, "a")

        self.fig_cena.tight_layout(pad=0.08)
        self.canvas_cena.draw_idle()

    def desenhar_carrinho(self, ax, x, y):
        # Sombra
        ax.add_patch(patches.Ellipse((x, y - 0.102), 0.100, 0.024, facecolor="#0f172a", alpha=0.22, edgecolor="none"))

        # Corpo
        ax.add_patch(FancyBboxPatch((x - 0.058, y - 0.045), 0.116, 0.064, boxstyle="round,pad=0.006,rounding_size=0.018", facecolor=COR_VERMELHO, edgecolor="#881337", linewidth=1.3))

        # Cabine
        ax.add_patch(FancyBboxPatch((x - 0.030, y + 0.012), 0.062, 0.052, boxstyle="round,pad=0.004,rounding_size=0.014", facecolor=COR_AMARELO, edgecolor="#a16207", linewidth=1.1))
        ax.add_patch(Rectangle((x - 0.018, y + 0.022), 0.020, 0.024, facecolor="#ecfeff", edgecolor="none", alpha=0.96))
        ax.add_patch(Rectangle((x + 0.006, y + 0.022), 0.018, 0.024, facecolor="#ecfeff", edgecolor="none", alpha=0.96))

        # Rodas
        self.desenhar_roda(ax, x - 0.037, y - 0.052)
        self.desenhar_roda(ax, x + 0.039, y - 0.052)

        ax.text(x - 0.032, y - 0.017, "carrinho", fontsize=6.9, weight="bold", color="#111827")

    def desenhar_roda(self, ax, x, y):
        ax.add_patch(Circle((x, y), 0.019, facecolor="#111827", edgecolor="#020617", linewidth=0.8))
        ax.add_patch(Circle((x, y), 0.008, facecolor=COR_CIANO, edgecolor="#cffafe", linewidth=0.6))

    def desenhar_vetor(self, ax, x1, y1, x2, y2, cor, rotulo):
        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(x1, y1),
            arrowprops=dict(arrowstyle="-|>", color=cor, linewidth=2.4, shrinkA=0, shrinkB=0)
        )
        ax.text(x2 + 0.01 if x2 >= x1 else x2 - 0.025, y2 + 0.018, rotulo, fontsize=10, weight="bold", color=cor)

    def desenhar_graficos(self):
        modo_grafico = self.var_grafico.get()
        self.fig_graficos.clear()

        if not self.dados:
            dados_plot = [self.fisica_em(0.0)]
        else:
            dados_plot = self.dados

        if modo_grafico == "Todos":
            gs = gridspec.GridSpec(1, 3, figure=self.fig_graficos, wspace=0.38)
            axes = [self.fig_graficos.add_subplot(gs[0, i]) for i in range(3)]
            self.plotar_serie(axes[0], dados_plot, "x", "Posição em função do tempo", "x (m)")
            self.plotar_serie(axes[1], dados_plot, "v", "Velocidade em função do tempo", "v (m/s)")
            self.plotar_serie(axes[2], dados_plot, "a", "Aceleração em função do tempo", "a (m/s²)")
            self.lbl_nota_grafico.config(text="Mostrando x(t), v(t) e a(t).")
        else:
            ax = self.fig_graficos.add_subplot(111)
            if modo_grafico == "x(t)":
                self.plotar_serie(ax, dados_plot, "x", "Posição em função do tempo", "x (m)")
                self.lbl_nota_grafico.config(text="Mostrando somente x(t).")
            elif modo_grafico == "v(t)":
                self.plotar_serie(ax, dados_plot, "v", "Velocidade em função do tempo", "v (m/s)")
                self.lbl_nota_grafico.config(text="Mostrando somente v(t).")
            else:
                self.plotar_serie(ax, dados_plot, "a", "Aceleração em função do tempo", "a (m/s²)")
                self.lbl_nota_grafico.config(text="Mostrando somente a(t).")

        if modo_grafico == "Todos":
            self.fig_graficos.subplots_adjust(left=0.065, right=0.985, top=0.88, bottom=0.19, wspace=0.42)
        else:
            self.fig_graficos.subplots_adjust(left=0.075, right=0.985, top=0.925, bottom=0.135)
        self.canvas_graficos.draw_idle()

    def plotar_serie(self, ax, dados, chave, titulo, ylabel):
        modo, x0, v0, a, L, tmax, dt, ritmo = self.obter_config()
        t = np.array([d["t"] for d in dados], dtype=float)
        y = np.array([d[chave] for d in dados], dtype=float)

        if len(t) == 0:
            t = np.array([0.0])
            y = np.array([0.0])

        cor = CORES_GRAFICOS[chave]
        ax.set_facecolor(CORES_FUNDO_GRAFICOS.get(chave, COR_GRAFICO))
        ax.plot(t, y, color=cor, linewidth=2.1, marker="o", markersize=2.4, markevery=max(1, len(t)//40))
        ax.fill_between(t, 0.0, y, color=cor, alpha=0.08)
        ax.axhline(0.0, color="#64748b", linewidth=0.7, alpha=0.45)
        if len(t):
            ax.scatter([t[-1]], [y[-1]], s=34, color=cor, edgecolor="white", linewidth=0.9, zorder=5)

        if chave == "x" and self.var_erro_experimental.get() and len(dados) > 0:
            try:
                sigma_x = max(self.ler_numero(self.var_sigma_x, "incerteza σx"), 0.0)
                if sigma_x > 0:
                    ax.errorbar(t, y, yerr=sigma_x, fmt="none", ecolor=COR_LARANJA, elinewidth=0.9, capsize=2, alpha=0.65)
                y_teo = np.array([d.get("x_teo", d["x"]) for d in dados], dtype=float)
                ax.plot(t, y_teo, color=COR_ROXO, linewidth=1.4, linestyle="--", alpha=0.75)
                ax.text(0.02, 0.72, "pontos: x experimental | tracejado: x teórico", transform=ax.transAxes, fontsize=7.1, color="#4c1d95")
            except Exception:
                pass

        if chave == "x" and self.var_ajuste.get():
            self.plotar_ajuste(ax, t, y)

        ax.set_title(titulo, fontsize=8.5, pad=5, loc="left", fontweight="bold", color=COR_TEXTO_ESCURO)
        ax.set_xlabel("t (s)", fontsize=7.2, labelpad=1)
        ax.set_ylabel(ylabel, fontsize=7.2, labelpad=2)
        ax.tick_params(axis="both", labelsize=6.8, pad=1, colors=COR_TEXTO_SECUNDARIO)
        ax.grid(True, which="major", color=COR_GRADE, linewidth=0.6, alpha=0.38)
        ax.grid(True, which="minor", color=COR_GRADE, linewidth=0.4, alpha=0.18)
        ax.xaxis.set_minor_locator(AutoMinorLocator())
        ax.yaxis.set_minor_locator(AutoMinorLocator())

        # Escala horizontal dinâmica:
        # Antes, o eixo do tempo ia até t máximo, mesmo quando a tomada de dados
        # terminava antes. Por isso os pontos ficavam concentrados na metade da
        # gráfica. Agora o eixo se ajusta ao último tempo realmente registrado.
        t_min = float(np.min(t)) if len(t) else 0.0
        t_max_dado = float(np.max(t)) if len(t) else 0.0
        janela_minima = max(float(dt), 0.05)

        if t_max_dado <= t_min + 1e-12:
            ax.set_xlim(0.0, janela_minima)
        else:
            margem_t = max(0.015, 0.03 * (t_max_dado - t_min))
            ax.set_xlim(max(0.0, t_min - margem_t), t_max_dado + margem_t)

        # Escala vertical dinâmica:
        # A posição não fica mais presa ao comprimento total L da mesa. Assim,
        # se a coleta terminar antes de usar toda a mesa, os dados ainda ocupam
        # bem a altura da gráfica.
        if chave == "x":
            ymin = float(np.min(y))
            ymax = float(np.max(y))
        elif chave == "a":
            ymin = min(0.0, float(np.min(y)))
            ymax = max(0.0, float(np.max(y)))
        else:
            ymin = float(np.min(y))
            ymax = float(np.max(y))

        if abs(ymax - ymin) < 1e-12:
            margem = max(0.5, abs(ymax) * 0.25 + 0.1)
            ymin -= margem
            ymax += margem
        else:
            margem = 0.12 * (ymax - ymin)
            ymin -= margem
            ymax += margem
        ax.set_ylim(ymin, ymax)
        for spine in ax.spines.values():
            spine.set_color(cor)
            spine.set_linewidth(0.9)

        if len(t) > 0:
            ax.axvline(float(t[-1]), color=COR_MAGENTA, linestyle="--", linewidth=1.0, alpha=0.48)

    def plotar_ajuste(self, ax, t, x):
        if len(t) < 3:
            ax.text(0.02, 0.86, "Ajuste: dados insuficientes", transform=ax.transAxes, fontsize=7.5, color="#9f1239")
            return

        try:
            resultado = self.calcular_ajuste_posicao(t, x)
            if not resultado:
                raise ValueError("ajuste vazio")
            tt = resultado["tt"]
            xx = resultado["xx"]
            texto = resultado["texto_grafico"]

            ax.plot(tt, xx, color=COR_MAGENTA, linestyle="--", linewidth=1.8)
            ax.text(
                0.02,
                0.86,
                texto,
                transform=ax.transAxes,
                fontsize=7.3,
                color="#701a75",
                bbox=dict(boxstyle="round,pad=0.25", facecolor="#fae8ff", edgecolor=COR_MAGENTA, alpha=0.95)
            )
        except Exception:
            ax.text(0.02, 0.86, "Ajuste não calculado", transform=ax.transAxes, fontsize=7.5, color="#9f1239")

    def atualizar_tabela(self):
        if not hasattr(self, "tabela"):
            return

        for item in self.tabela.get_children():
            self.tabela.delete(item)

        selecionadas = self.obter_colunas_tabela()
        metadados = [self.mapa_grandezas_tabela[g] for g in selecionadas]

        # Mostra as últimas 350 linhas para manter a interface leve.
        inicio = max(0, len(self.dados) - 350)
        for numero_linha, d in enumerate(self.dados[inicio:]):
            valores = [d["n"]]
            for meta in metadados:
                valores.append(formato_numero(d.get(meta["chave"], 0.0), meta["casas"]))

            tag = "linha_par" if numero_linha % 2 == 0 else "linha_impar"
            self.tabela.insert("", "end", values=tuple(valores), tags=(tag,))

        filhos = self.tabela.get_children()
        if filhos:
            self.tabela.see(filhos[-1])

    # -------------------------------------------------------------------------
    # ANÁLISE EXPERIMENTAL, RELATÓRIO E PRÉ/PÓS-TESTE
    # -------------------------------------------------------------------------
    def calcular_ajuste_posicao(self, t=None, x=None):
        """Calcula o ajuste de x(t) e retorna parâmetros, curva ajustada e R²."""
        if t is None or x is None:
            if len(self.dados) < 3:
                return None
            t = np.array([d["t"] for d in self.dados], dtype=float)
            x = np.array([d["x"] for d in self.dados], dtype=float)
        else:
            t = np.array(t, dtype=float)
            x = np.array(x, dtype=float)

        if len(t) < 3 or np.max(t) - np.min(t) < 1e-12:
            return None

        modo, x0, v0, a, L, tmax, dt, ritmo = self.obter_config()
        if modo == "MRU":
            popt, _ = curve_fit(modelo_linear, t, x, p0=[x[0], v0])
            xx_pred = modelo_linear(t, *popt)
            tt = np.linspace(float(np.min(t)), float(np.max(t)), 150)
            xx = modelo_linear(tt, *popt)
            ss_res = float(np.sum((x - xx_pred) ** 2))
            ss_tot = float(np.sum((x - np.mean(x)) ** 2))
            r2 = 1.0 if ss_tot < 1e-15 else 1.0 - ss_res / ss_tot
            texto_grafico = f"Ajuste: x={popt[0]:.3f}+{popt[1]:.3f}t | R²={r2:.4f}"
            texto_relatorio = (
                f"x(t) = {popt[0]:.6f} + ({popt[1]:.6f})·t; "
                f"velocidade experimental v = {popt[1]:.6f} m/s; R² = {r2:.6f}."
            )
            return {
                "modo": modo,
                "popt": popt,
                "tt": tt,
                "xx": xx,
                "r2": r2,
                "texto_grafico": texto_grafico,
                "texto_relatorio": texto_relatorio,
                "v_ajuste": float(popt[1]),
                "a_ajuste": 0.0,
            }

        popt, _ = curve_fit(modelo_quadratico, t, x, p0=[x[0], v0, 0.5 * a])
        xx_pred = modelo_quadratico(t, *popt)
        tt = np.linspace(float(np.min(t)), float(np.max(t)), 150)
        xx = modelo_quadratico(tt, *popt)
        ss_res = float(np.sum((x - xx_pred) ** 2))
        ss_tot = float(np.sum((x - np.mean(x)) ** 2))
        r2 = 1.0 if ss_tot < 1e-15 else 1.0 - ss_res / ss_tot
        a_ajuste = 2.0 * float(popt[2])
        texto_grafico = f"Ajuste: x={popt[0]:.3f}+{popt[1]:.3f}t+{popt[2]:.3f}t² | R²={r2:.4f}"
        texto_relatorio = (
            f"x(t) = {popt[0]:.6f} + ({popt[1]:.6f})·t + ({popt[2]:.6f})·t²; "
            f"velocidade inicial experimental v₀ = {popt[1]:.6f} m/s; "
            f"aceleração experimental a = 2·{popt[2]:.6f} = {a_ajuste:.6f} m/s²; R² = {r2:.6f}."
        )
        return {
            "modo": modo,
            "popt": popt,
            "tt": tt,
            "xx": xx,
            "r2": r2,
            "texto_grafico": texto_grafico,
            "texto_relatorio": texto_relatorio,
            "v_ajuste": float(popt[1]),
            "a_ajuste": a_ajuste,
        }

    def calcular_estatisticas_erro(self):
        if not self.dados:
            return None
        erros = np.array([d.get("erro_x", 0.0) for d in self.dados], dtype=float)
        abs_erros = np.abs(erros)
        return {
            "erro_medio": float(np.mean(erros)),
            "erro_abs_medio": float(np.mean(abs_erros)),
            "erro_abs_max": float(np.max(abs_erros)),
            "rmse": float(np.sqrt(np.mean(erros ** 2))),
        }

    def gerar_texto_relatorio(self):
        modo, x0, v0, a, L, tmax, dt, ritmo = self.obter_config()
        intervalo_coleta = self.ler_numero(self.var_intervalo_discreto, "intervalo de coleta")
        sigma_x = self.ler_numero(self.var_sigma_x, "incerteza σx")
        ajuste = self.calcular_ajuste_posicao()
        erro = self.calcular_estatisticas_erro()
        data_hora = datetime.now().strftime("%d/%m/%Y às %H:%M")
        linhas = []
        linhas.append(NOME_APLICATIVO.upper())
        linhas.append("=" * 72)
        linhas.append(f"Versão: {VERSAO_APLICATIVO}")
        linhas.append(f"Autor: {AUTOR}")
        linhas.append(f"Gerado em: {data_hora}")
        linhas.append("")
        linhas.append("1. IDENTIFICAÇÃO")
        linhas.append("Componente curricular: Física — Cinemática.")
        linhas.append("Objeto de conhecimento: Movimento Retilíneo Uniforme e Movimento Retilíneo Uniformemente Variado.")
        linhas.append("Público sugerido: Ensino Médio.")
        linhas.append("")
        linhas.append("2. OBJETIVO DA EXPERIÊNCIA")
        linhas.append("Analisar a relação entre posição, velocidade, aceleração e tempo por meio de uma simulação experimental controlada.")
        linhas.append("")
        linhas.append("3. CONFIGURAÇÃO FÍSICA")
        linhas.append(f"Tipo de movimento: {modo}")
        linhas.append(f"Posição inicial x₀: {x0:.6f} m")
        linhas.append(f"Velocidade inicial v₀: {v0:.6f} m/s")
        linhas.append(f"Aceleração a: {a:.6f} m/s²")
        linhas.append(f"Comprimento da mesa L: {L:.6f} m")
        linhas.append(f"Tempo máximo: {tmax:.6f} s")
        linhas.append(f"Passo de integração/visualização Δt: {dt:.6f} s")
        linhas.append(f"Ritmo de simulação: {ritmo:.2f}×")
        linhas.append("")
        linhas.append("4. COLETA DE DADOS")
        linhas.append(f"Tipo de coleta: {self.var_registro.get()}")
        linhas.append(f"Intervalo da coleta discreta: {intervalo_coleta:.6f} s")
        linhas.append(f"Quantidade de pontos registrados: {len(self.dados)}")
        linhas.append(f"Erro experimental na posição: {'ativado' if self.var_erro_experimental.get() else 'desativado'}")
        linhas.append(f"Incerteza simulada σx: {sigma_x:.6f} m")
        linhas.append("")
        linhas.append("5. TRATAMENTO DOS DADOS")
        if ajuste:
            linhas.append(ajuste["texto_relatorio"])
        else:
            linhas.append("Ajuste de curva não calculado: são necessários pelo menos 3 pontos com tempos diferentes.")
        if erro:
            linhas.append(f"Erro médio Δx: {erro['erro_medio']:.6f} m")
            linhas.append(f"Erro absoluto médio |Δx|: {erro['erro_abs_medio']:.6f} m")
            linhas.append(f"Erro absoluto máximo: {erro['erro_abs_max']:.6f} m")
            linhas.append(f"RMSE da posição: {erro['rmse']:.6f} m")
        linhas.append("")
        linhas.append("6. INTERPRETAÇÃO FÍSICA")
        if modo == "MRU":
            linhas.append("No MRU, espera-se que x(t) seja linear, v(t) seja aproximadamente constante e a(t) seja nula.")
            linhas.append("O coeficiente angular do ajuste linear representa a velocidade experimental do carrinho.")
        else:
            linhas.append("No MRUV, espera-se que x(t) seja parabólico, v(t) seja linear e a(t) permaneça aproximadamente constante.")
            linhas.append("No ajuste quadrático x = c0 + c1·t + c2·t², a aceleração experimental é a = 2·c2.")
        linhas.append("")
        linhas.append("7. CONCLUSÃO AUTOMÁTICA")
        if ajuste and ajuste["r2"] >= 0.98:
            linhas.append("Os dados apresentam forte concordância com o modelo teórico escolhido, segundo o valor de R².")
        elif ajuste:
            linhas.append("Os dados apresentam concordância parcial com o modelo; recomenda-se discutir erros experimentais, amostragem e condições iniciais.")
        else:
            linhas.append("A conclusão quantitativa depende de nova coleta com mais pontos experimentais.")
        linhas.append("")
        linhas.append("8. TABELA DE DADOS")
        linhas.append("n; t(s); x_exp(m); x_teo(m); erro_x(m); erro_x(%); v(m/s); a(m/s²)")
        for d in self.dados[:500]:
            linhas.append(
                f"{d['n']}; {d.get('t', 0.0):.6f}; {d.get('x', 0.0):.6f}; {d.get('x_teo', 0.0):.6f}; "
                f"{d.get('erro_x', 0.0):.6f}; {d.get('erro_x_pct', 0.0):.4f}; {d.get('v', 0.0):.6f}; {d.get('a', 0.0):.6f}"
            )
        if len(self.dados) > 500:
            linhas.append(f"... {len(self.dados) - 500} linhas adicionais omitidas no relatório para manter o arquivo leve.")
        linhas.append("")
        linhas.append("9. ORIENTAÇÃO DIDÁTICA")
        linhas.append("Antes da simulação, solicitar que os estudantes prevejam o formato de x(t), v(t) e a(t).")
        linhas.append("Após a simulação, comparar previsão, tabela, gráfico e ajuste matemático, discutindo fontes de erro experimental.")
        return "\n".join(linhas)

    def gerar_roteiro_pre_pos_teste(self):
        return """ROTEIRO DE PRÉ-TESTE E PÓS-TESTE — MRU/MRUV
================================================================

Público-alvo: estudantes do Ensino Médio.
Objetivo: diagnosticar conhecimentos prévios e verificar aprendizagem após o uso do laboratório virtual.
Orientação: aplicar o pré-teste antes da simulação e o pós-teste após a discussão dos gráficos, tabela e relatório.
Tempo sugerido: 10 a 15 minutos para cada etapa.

A) PRÉ-TESTE — ANTES DA SIMULAÇÃO
1. O que significa dizer que um corpo está em movimento retilíneo?
2. Em um MRU, o que acontece com a velocidade ao longo do tempo?
3. Em um MRUV, o que acontece com a velocidade quando a aceleração é constante?
4. Qual deve ser o formato do gráfico posição × tempo no MRU?
5. Qual deve ser o formato do gráfico posição × tempo no MRUV?
6. O que representa a inclinação de um gráfico posição × tempo?
7. Em uma coleta experimental, por que os valores medidos podem ser diferentes dos valores teóricos?
8. Explique, com suas palavras, o que é erro experimental.

B) ATIVIDADE COM O LABORATÓRIO VIRTUAL
1. Escolha MRU e registre dados com coleta contínua.
2. Repita a experiência usando coleta discreta com intervalo maior de amostragem.
3. Ative o erro experimental e observe como os pontos se afastam da curva teórica.
4. Use o ajuste de curva em x(t) e observe o valor de R².
5. Exporte o relatório automático e discuta as conclusões com a turma.

C) PÓS-TESTE — APÓS A SIMULAÇÃO
1. Como você reconhece um MRU analisando o gráfico posição × tempo?
2. Como você reconhece um MRUV analisando o gráfico posição × tempo?
3. No MRU, que grandeza física é obtida pela inclinação da reta x(t)?
4. No MRUV, por que a curva x(t) não é uma reta?
5. O que significa um valor de R² próximo de 1 no ajuste da curva?
6. Qual foi a diferença observada entre coleta contínua e coleta discreta?
7. O que aconteceu com os dados quando o erro experimental foi ativado?
8. Cite uma possível fonte de erro em uma experiência real com carrinho e sensor.

D) QUESTÕES DE VALIDAÇÃO PEDAGÓGICA — ESCALA LIKERT
Marque: 1 = discordo totalmente; 2 = discordo; 3 = neutro; 4 = concordo; 5 = concordo totalmente.
1. A simulação ajudou a compreender a diferença entre MRU e MRUV. [1] [2] [3] [4] [5]
2. Os gráficos facilitaram a interpretação do movimento. [1] [2] [3] [4] [5]
3. A tabela de dados ajudou a relacionar tempo, posição, velocidade e aceleração. [1] [2] [3] [4] [5]
4. A opção de erro experimental ajudou a compreender limitações de medidas reais. [1] [2] [3] [4] [5]
5. O relatório automático contribuiu para organizar a análise da experiência. [1] [2] [3] [4] [5]

E) CRITÉRIOS DE ANÁLISE DO PROFESSOR
- Comparar respostas do pré-teste e pós-teste.
- Observar se o estudante reconhece a forma dos gráficos.
- Verificar se o estudante diferencia valor teórico, valor experimental e erro.
- Analisar se o estudante interpreta corretamente o ajuste de curva e o R².
"""

    def salvar_texto_em_arquivo(self, titulo, initialfile, conteudo):
        caminho = filedialog.asksaveasfilename(
            title=titulo,
            defaultextension=".txt",
            initialfile=initialfile,
            filetypes=[("Arquivo de texto", "*.txt"), ("Todos os arquivos", "*.*")]
        )
        if not caminho:
            return
        try:
            with open(caminho, "w", encoding="utf-8-sig") as arquivo:
                arquivo.write(conteudo)
            self.var_status.set(f"Arquivo salvo: {caminho}")
            messagebox.showinfo("Arquivo salvo", "O arquivo foi gerado com sucesso.")
        except OSError as erro:
            messagebox.showerror("Erro ao salvar", f"Não foi possível salvar o arquivo.\n\nDetalhes: {erro}")

    def exportar_relatorio(self):
        if not self.dados:
            messagebox.showwarning("Sem dados", "Não há dados para gerar o relatório.")
            return
        if not self.validar_parametros(mostrar_erro=True):
            return
        self.salvar_texto_em_arquivo(
            "Salvar relatório automático",
            f"relatorio_mru_mruv_{datetime.now():%Y%m%d_%H%M}.txt",
            self.gerar_texto_relatorio()
        )

    def exportar_roteiro_pre_pos_teste(self):
        self.salvar_texto_em_arquivo(
            "Salvar roteiro de pré-teste e pós-teste",
            f"roteiro_pre_pos_mru_mruv_{datetime.now():%Y%m%d_%H%M}.txt",
            self.gerar_roteiro_pre_pos_teste()
        )

    # -------------------------------------------------------------------------
    # EXPORTAÇÃO
    # -------------------------------------------------------------------------
    def exportar_csv(self):
        if not self.dados:
            messagebox.showwarning("Sem dados", "Não há dados para exportar.")
            return
        if not self.validar_parametros(mostrar_erro=True):
            return

        caminho = filedialog.asksaveasfilename(
            title="Salvar dados experimentais",
            defaultextension=".csv",
            initialfile=f"dados_mru_mruv_{datetime.now():%Y%m%d_%H%M}.csv",
            filetypes=[("Arquivo CSV", "*.csv"), ("Todos os arquivos", "*.*")]
        )
        if not caminho:
            return

        try:
            selecionadas = self.obter_colunas_tabela()
            metadados = [self.mapa_grandezas_tabela[g] for g in selecionadas]
            modo, x0, v0, a, L, tmax, dt, ritmo = self.obter_config()

            with open(caminho, "w", newline="", encoding="utf-8-sig") as arquivo:
                escritor = csv.writer(arquivo, delimiter=";")
                escritor.writerow([NOME_APLICATIVO, f"versão {VERSAO_APLICATIVO}"])
                escritor.writerow(["Gerado em", datetime.now().strftime("%d/%m/%Y %H:%M:%S")])
                escritor.writerow(["Movimento", modo, "Registros", len(self.dados)])
                escritor.writerow(["x₀ (m)", formato_numero(x0, 4), "v₀ (m/s)", formato_numero(v0, 4)])
                escritor.writerow(["a (m/s²)", formato_numero(a, 4), "L (m)", formato_numero(L, 4)])
                escritor.writerow([])
                escritor.writerow(["indice"] + [meta["csv"] for meta in metadados])
                for d in self.dados:
                    linha = [d["n"]]
                    for meta in metadados:
                        linha.append(str(round(d.get(meta["chave"], 0.0), 8)).replace(".", ","))
                    escritor.writerow(linha)

            self.var_status.set("Arquivo CSV exportado conforme as colunas selecionadas na tabela.")
            messagebox.showinfo("Exportação concluída", "Os dados selecionados foram salvos em CSV.")
        except OSError as erro:
            messagebox.showerror("Erro ao exportar", f"Não foi possível salvar o arquivo.\n\nDetalhes: {erro}")

    # -------------------------------------------------------------------------
    # FECHAMENTO
    # -------------------------------------------------------------------------
    def fechar(self):
        self.rodando = False
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except Exception:
                pass
        self.root.destroy()


# =============================================================================
# EXECUÇÃO
# =============================================================================

def main():
    root = tk.Tk()
    app = LaboratorioMRUMRUV(root)
    root.mainloop()


if __name__ == "__main__":
    main()
