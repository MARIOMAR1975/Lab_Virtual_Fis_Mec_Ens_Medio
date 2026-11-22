# -*- coding: utf-8 -*-
"""
LABORATÓRIO VIRTUAL OFFLINE: Segunda Lei de Newton — formato compacto Tkinter + Matplotlib

Autor: Mario Omar Calla Salcedo / Maestría Profesional en Enseñanza de la Física


Versão reorganizada tomando como referência o formato visual e funcional do arquivo
LAB_MRU_MRUV(16).py: cabeçalho escuro, painel de comando compacto, cena experimental
acima, gráficos em tempo real abaixo e tabela experimental lateral.

Sistema físico simulado:
- Carrinho sobre mesa horizontal conectado por fio ideal e polia ideal a um bloco suspenso.
- Atrito entre carrinho e mesa representado por coeficiente μ.
- Segunda Lei de Newton aplicada ao sistema carrinho + bloco:
      F_resultante = m_b g - f_atrito
      a = F_resultante / (m_c + m_b)
- Quando o peso do bloco suspenso não supera o atrito máximo, o sistema permanece em repouso.

Recursos principais:
- Interface offline em Python nativo, sem navegador e sem internet.
- Cena didática com carrinho, sensor, mesa, régua, polia, bloco suspenso, fio e vetores.
- Painel de comando compacto, no mesmo estilo do laboratório MRU/MRUV.
- Gráficos selecionáveis: x(t), v(t), a(t), F(t), T(t) ou todos.
- Tabela experimental lateral com diferentes grandezas.
- Coleta temporal contínua, discreta ou manual.
- Registro discreto por ensaio: massa 1 → força 1, massa 2 → força 2, força 1 → aceleração 1 etc.
- Registro de pontos para análise F × a.
- Ajuste linear e ajuste hiperbólico/inversamente proporcional para dados discretos.
- Exportação CSV, relatório TXT e roteiro pré-teste/pós-teste.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch, Arc
from matplotlib.ticker import AutoMinorLocator
import csv
import math
import time
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime


# Identidade da aplicação e paleta de alto contraste.
NOME_APLICATIVO = "Laboratório Virtual — Segunda Lei de Newton"
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
DT_MAX = 0.5
RITMO_MIN = 0.05
RITMO_MAX = 16.0
INTERVALO_MIN = 0.001
MAX_DADOS = 10000
INTERVALO_GRAFICO = 0.12
INTERVALO_TABELA = 0.25


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def arredondar_fisico(valor, casas=9):
    """Arredonda valores físicos para evitar ruído numérico de ponto flutuante."""
    try:
        return round(float(valor), casas)
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


def converter_numero(valor):
    """Aceita ponto ou vírgula decimal e rejeita valores não finitos."""
    texto = str(valor).strip().replace(" ", "").replace(",", ".")
    numero = float(texto)
    if not math.isfinite(numero):
        raise ValueError("O valor deve ser um número finito.")
    return numero


def calcular_rmse(y_true, y_pred):
    """Calcula a raiz do erro quadrático médio."""
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)
    if len(y_true) == 0:
        return 0.0
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def ajuste_linear(x, y):
    """Ajusta y = A*x + B e devolve coeficientes, previsão e RMSE."""
    x = np.array(x, dtype=float)
    y = np.array(y, dtype=float)
    mascara = np.isfinite(x) & np.isfinite(y)
    x = x[mascara]
    y = y[mascara]
    if len(x) < 2 or len(set(np.round(x, 9))) < 2:
        return None
    A, B = np.polyfit(x, y, 1)
    y_pred = A * x + B
    return {"A": float(A), "B": float(B), "x": x, "y": y, "y_pred": y_pred, "rmse": calcular_rmse(y, y_pred)}


def ajuste_hiperbolico_inverso(x, y):
    """Ajusta y = K/x + B, modelo inversamente proporcional com intercepto experimental."""
    x = np.array(x, dtype=float)
    y = np.array(y, dtype=float)
    mascara = np.isfinite(x) & np.isfinite(y) & (np.abs(x) > 1e-12)
    x = x[mascara]
    y = y[mascara]
    z = 1.0 / x
    if len(x) < 2 or len(set(np.round(z, 9))) < 2:
        return None
    K, B = np.polyfit(z, y, 1)
    y_pred = K / x + B
    return {"K": float(K), "B": float(B), "x": x, "y": y, "y_pred": y_pred, "rmse": calcular_rmse(y, y_pred)}


def colocar_equacao_interna(ax, texto, cor="#111827", fontsize=7):
    """Coloca a equação dentro da área gráfica, no canto superior esquerdo."""
    ax.text(
        0.03, 0.94, texto,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=fontsize,
        fontweight="bold",
        color=cor,
        bbox=dict(
            facecolor="#ffffff",
            edgecolor=cor,
            alpha=0.90,
            boxstyle="round,pad=0.25",
            linewidth=0.8
        ),
        zorder=10
    )


def formatar_eixo(ax, xlabel="Tempo (s)", ylabel="", titulo="", cor_fundo="#ffffff"):
    """Aplica acabamento visual profissional aos eixos."""
    ax.set_facecolor(cor_fundo)
    ax.grid(True, which="major", linestyle="-", linewidth=0.60, color=COR_GRADE, alpha=0.78)
    ax.grid(True, which="minor", linestyle=":", linewidth=0.40, color=COR_GRADE, alpha=0.45)
    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.yaxis.set_minor_locator(AutoMinorLocator())
    ax.set_title(titulo, fontsize=8.5, fontweight="bold", pad=5, color="#0f172a")
    ax.set_xlabel(xlabel, fontsize=7.5, fontweight="bold")
    ax.set_ylabel(ylabel, fontsize=7.5, fontweight="bold")
    ax.tick_params(axis="both", labelsize=7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#94a3b8")
    ax.spines["bottom"].set_color("#94a3b8")


def ajustar_limites_constantes(ax, xs, ys, margem_x=0.05, margem_y=0.10):
    """Evita limites idênticos em gráficos com grandeza constante."""
    if len(xs) == 0 or len(ys) == 0:
        return
    xmin, xmax = float(np.min(xs)), float(np.max(xs))
    ymin, ymax = float(np.min(ys)), float(np.max(ys))

    if abs(xmax - xmin) < 1e-12:
        xmin -= 0.5
        xmax += 0.5
    else:
        dx = (xmax - xmin) * margem_x
        xmin -= dx
        xmax += dx

    if abs(ymax - ymin) < 1e-12:
        base = max(abs(ymax), 1.0)
        ymin -= 0.10 * base
        ymax += 0.10 * base
    else:
        dy = (ymax - ymin) * margem_y
        ymin -= dy
        ymax += dy

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)


# =============================================================================
# CLASSE PRINCIPAL DA APLICAÇÃO
# =============================================================================

class LaboratorioSegundaLeiNewton:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{NOME_APLICATIVO} | v{VERSAO_APLICATIVO}")
        self.root.geometry("1366x720")
        self.root.minsize(1100, 650)

        # Estado da simulação
        self.rodando = False
        self.t = 0.0
        self.x = 0.0
        self.v = 0.0
        self.a = 0.0
        self.forca_resultante = 0.0
        self.tensao = 0.0
        self.atrito = 0.0
        self.peso_bloco = 0.0
        self.normal = 0.0
        self.wheel_angle = 0.0
        self.limite_atingido = False
        self.after_id = None
        self.indice = 0
        self.proximo_t_discreto = 0.0
        self.dados = []
        self.historico_dinamica = []
        self._suprimir_eventos = False
        self._ultimo_redesenho_grafico = 0.0
        self._ultima_atualizacao_tabela = 0.0

        # Variáveis Tkinter
        self.var_m_cart = tk.StringVar(value="0,50")
        self.var_m_block = tk.StringVar(value="0,20")
        self.var_mu = tk.StringVar(value="0,05")
        self.var_L = tk.StringVar(value="2,00")
        self.var_g = tk.StringVar(value="9,80")
        self.var_tmax = tk.StringVar(value="5,00")
        self.var_dt = tk.StringVar(value="0,05")
        self.var_ritmo = tk.StringVar(value="1,00")
        self.var_grafico = tk.StringVar(value="Todos")
        self.var_registro = tk.StringVar(value="Contínua")
        self.var_intervalo_discreto = tk.StringVar(value="0,25")
        self.var_tipo_tabela = tk.StringVar(value="Tabela completa: t, x, v, a, F, T")
        self.var_ajuste_discreto = tk.StringVar(value="Linear + hiperbólico")
        self.var_status = tk.StringVar(value="Pronto para iniciar.")
        self.var_descricao_tabela = tk.StringVar(value="Tabela ativa: t, x, v, a, F e T.")
        self.var_interpretacao = tk.StringVar(value="")

        self.opcoes_tipo_tabela = [
            "Posição × Tempo",
            "Velocidade × Tempo",
            "Aceleração × Tempo",
            "Força resultante × Tempo",
            "Tensão × Tempo",
            "Tabela completa: t, x, v, a, F, T",
            "Massa total × Força resultante",
            "Força resultante × Aceleração",
            "Massa total × Aceleração",
            "Dados discretos: massas, força e aceleração"
        ]

        self.tipos_tabela_discreta = {
            "Massa total × Força resultante",
            "Força resultante × Aceleração",
            "Massa total × Aceleração",
            "Dados discretos: massas, força e aceleração",
        }

        self.mapa_grandezas_tabela = {
            "Tempo": {"chave": "t", "titulo": "t", "csv": "tempo_s", "casas": 3, "largura": 54},
            "Posição": {"chave": "x", "titulo": "x", "csv": "posicao_m", "casas": 3, "largura": 54},
            "Velocidade": {"chave": "v", "titulo": "v", "csv": "velocidade_m_s", "casas": 3, "largura": 58},
            "Aceleração": {"chave": "a", "titulo": "a", "csv": "aceleracao_m_s2", "casas": 3, "largura": 58},
            "Força resultante": {"chave": "F", "titulo": "F", "csv": "forca_resultante_N", "casas": 3, "largura": 58},
            "Tensão": {"chave": "T", "titulo": "T", "csv": "tensao_N", "casas": 3, "largura": 58},
            "Atrito": {"chave": "fat", "titulo": "f", "csv": "forca_atrito_N", "casas": 3, "largura": 54},
            "Massa carrinho": {"chave": "m_cart", "titulo": "Mc", "csv": "massa_carrinho_kg", "casas": 3, "largura": 54},
            "Massa bloco": {"chave": "m_block", "titulo": "Mb", "csv": "massa_bloco_kg", "casas": 3, "largura": 54},
            "Massa total": {"chave": "Mtot", "titulo": "M", "csv": "massa_total_kg", "casas": 3, "largura": 54},
        }

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

        estilo.configure("TEntry", fieldbackground="#151225", foreground=COR_TEXTO, insertcolor=COR_AMARELO,
                         bordercolor="#64748b", lightcolor="#64748b", darkcolor="#64748b")
        estilo.configure("TCombobox", fieldbackground="#151225", background="#151225", foreground=COR_TEXTO,
                         arrowcolor=COR_CIANO, bordercolor="#64748b", lightcolor="#64748b", darkcolor="#64748b")
        estilo.map("TCombobox", fieldbackground=[("readonly", "#151225")], foreground=[("readonly", COR_TEXTO)],
                   selectbackground=[("readonly", COR_ROXO)])
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
            text="Sistema carrinho–bloco, forças resultantes e análise experimental de F = m·a",
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
            font=("Segoe UI", 7, "bold")
        )
        lbl.grid(row=0, column=0, columnspan=3, sticky="w", padx=5, pady=(4, 1))
        return grupo

    def criar_grupo_modelo(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Modelo físico")
        self.criar_linha_entradas(grupo, 1, "m carr. (kg)", self.var_m_cart, "m bloco (kg)", self.var_m_block)
        self.criar_linha_entradas(grupo, 2, "μ atrito", self.var_mu, "L mesa (m)", self.var_L)
        self.criar_linha_entradas(grupo, 3, "g (m/s²)", self.var_g, "t máx. (s)", self.var_tmax)
        self.criar_linha_entradas(grupo, 4, "Δt (s)", self.var_dt, "ritmo", self.var_ritmo)

    def criar_grupo_visualizacao(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Visualização e coleta")
        self.criar_label_combo(
            grupo, 1, "Gráficos", self.var_grafico,
            ["Todos", "x(t)", "v(t)", "a(t)", "F(t)", "T(t)", "Discretos", "F × a", "a × M", "F × M"]
        )
        self.criar_label_combo(grupo, 2, "Coleta temporal", self.var_registro, ["Contínua", "Discreta", "Manual"])
        self.criar_linha_entradas(grupo, 3, "Δt tempo (s)", self.var_intervalo_discreto, "", tk.StringVar(value=""))
        self.criar_label_combo(
            grupo, 4, "Ajuste discreto", self.var_ajuste_discreto,
            ["Linear", "Hiperbólico", "Linear + hiperbólico"]
        )

    def criar_grupo_botoes(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Controle da simulação")

        botoes = [
            ("Iniciar", self.iniciar, "Success.TButton"),
            ("Pausar", self.pausar, "Warning.TButton"),
            ("Passo", self.passo, "TButton"),
            ("Resetar", lambda: self.reiniciar_simulacao(limpar_tabela=True), "Danger.TButton"),
            ("Reg. tempo", self.registrar_ponto_manual, "TButton"),
            ("Limpar", self.limpar_tabela, "TButton"),
            ("Reg. medida", self.salvar_ponto_dinamica, "TButton"),
            ("Análise", self.mostrar_analise_dinamica, "Accent.TButton"),
            ("CSV", self.exportar_csv, "TButton"),
            ("Relatório", self.exportar_relatorio, "TButton"),
            ("Pré/Pós", self.exportar_roteiro_pre_pos_teste, "TButton"),
        ]

        for i, (texto, comando, estilo) in enumerate(botoes):
            r = 1 + i // 3
            c = i % 3
            ttk.Button(grupo, text=texto, command=comando, style=estilo).grid(row=r, column=c, sticky="ew", padx=2, pady=2)

        lbl_status = tk.Label(
            grupo,
            textvariable=self.var_status,
            bg=COR_GRUPO,
            fg="#a5f3fc",
            font=("Segoe UI", 7),
            wraplength=205,
            justify="left"
        )
        lbl_status.grid(row=5, column=0, columnspan=3, sticky="ew", padx=5, pady=(1, 4))

    def criar_grupo_presets(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Situações prontas")
        presets = [
            ("Sem atrito", 1),
            ("Atrito médio", 2),
            ("Equilíbrio", 3),
        ]
        for i, (texto, codigo) in enumerate(presets):
            ttk.Button(grupo, text=texto, command=lambda c=codigo: self.aplicar_preset(c)).grid(row=1, column=i, sticky="ew", padx=2, pady=2)

    def criar_grupo_didatico(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Modelo didático")
        tk.Label(
            grupo,
            text="F = m·a  |  Fres = mb·g − μ·mc·g",
            bg=COR_GRUPO,
            fg="#f0abfc",
            font=("Segoe UI", 7),
            wraplength=210,
            justify="left"
        ).grid(row=1, column=0, columnspan=3, sticky="ew", padx=7, pady=(1, 2))
        tk.Label(
            grupo,
            textvariable=self.var_interpretacao,
            bg=COR_GRUPO,
            fg=COR_TEXTO_SUAVE,
            font=("Segoe UI", 7),
            wraplength=210,
            justify="left"
        ).grid(row=2, column=0, columnspan=3, sticky="ew", padx=7, pady=(0, 6))

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

        if texto2:
            tk.Label(f2, text=texto2, bg=COR_GRUPO, fg=COR_TEXTO_SUAVE, font=("Segoe UI", 7)).grid(row=0, column=0, sticky="w")
            e2 = ttk.Entry(f2, textvariable=var2, font=("Segoe UI", 7), width=6)
            e2.grid(row=1, column=0, sticky="ew")
        else:
            e2 = None

        e1.bind("<FocusOut>", lambda event: self.configuracao_alterada())
        if e2 is not None:
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
        visual.rowconfigure(0, weight=9, minsize=0, uniform="visual_split")
        visual.rowconfigure(1, weight=11, minsize=0, uniform="visual_split")

        self.criar_cena(visual)
        self.criar_graficos(visual, row=1, column=0, padx=(0, 0))
        self.criar_tabela_e_leituras(area)

    def criar_cena(self, parent):
        card = tk.Frame(parent, bg=COR_CARD, bd=0, highlightthickness=1, highlightbackground=COR_CIANO)
        card.grid(row=0, column=0, sticky="nsew", pady=(0, 4))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=1)

        self.fig_cena = Figure(figsize=(8, 3.4), dpi=100, facecolor=COR_CENA)
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
            text="Mostrando x(t), v(t), a(t), F(t) e T(t).",
            bg="#f8fafc",
            fg="#475569",
            font=("Segoe UI", 7)
        )
        self.lbl_nota_grafico.grid(row=0, column=1, sticky="e")

        self.fig_graficos = Figure(figsize=(7.2, 4.0), dpi=100, facecolor="#ffffff")
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

    # -------------------------------------------------------------------------
    # CONFIGURAÇÃO DA TABELA
    # -------------------------------------------------------------------------
    def tabela_usa_dados_discretos(self):
        """Indica se a tabela deve mostrar ensaios discretos, e não série temporal."""
        return self.var_tipo_tabela.get() in self.tipos_tabela_discreta

    def obter_colunas_tabela(self):
        tipo = self.var_tipo_tabela.get()
        if tipo == "Velocidade × Tempo":
            return ["Tempo", "Velocidade"]
        if tipo == "Aceleração × Tempo":
            return ["Tempo", "Aceleração"]
        if tipo == "Força resultante × Tempo":
            return ["Tempo", "Força resultante"]
        if tipo == "Tensão × Tempo":
            return ["Tempo", "Tensão"]
        if tipo == "Tabela completa: t, x, v, a, F, T":
            return ["Tempo", "Posição", "Velocidade", "Aceleração", "Força resultante", "Tensão"]
        if tipo == "Massa total × Força resultante":
            return ["Massa total", "Força resultante"]
        if tipo == "Força resultante × Aceleração":
            return ["Força resultante", "Aceleração"]
        if tipo == "Massa total × Aceleração":
            return ["Massa total", "Aceleração"]
        if tipo == "Dados discretos: massas, força e aceleração":
            return ["Massa carrinho", "Massa bloco", "Massa total", "Força resultante", "Aceleração", "Atrito"]
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
        descricoes = {
            "Velocidade × Tempo": "Tabela ativa: v em função de t.",
            "Aceleração × Tempo": "Tabela ativa: a em função de t.",
            "Força resultante × Tempo": "Tabela ativa: F resultante em função de t.",
            "Tensão × Tempo": "Tabela ativa: tensão T em função de t.",
            "Tabela completa: t, x, v, a, F, T": "Tabela ativa: t, x, v, a, F e T.",
            "Massa total × Força resultante": "Dados discretos: massa 1 → força 1, massa 2 → força 2.",
            "Força resultante × Aceleração": "Dados discretos: força 1 → aceleração 1, força 2 → aceleração 2.",
            "Massa total × Aceleração": "Dados discretos: massa 1 → aceleração 1; permite ajuste hiperbólico a = K/M + b.",
            "Dados discretos: massas, força e aceleração": "Dados por ensaio: Mc, Mb, Mtotal, F, a e atrito."
        }
        self.var_descricao_tabela.set(descricoes.get(tipo, "Tabela ativa: x em função de t."))
        self.atualizar_tabela()

    # -------------------------------------------------------------------------
    # EVENTOS E VALIDAÇÃO
    # -------------------------------------------------------------------------
    def configurar_eventos(self):
        variaveis = [
            self.var_m_cart, self.var_m_block, self.var_mu, self.var_L, self.var_g,
            self.var_tmax, self.var_dt, self.var_ritmo, self.var_grafico,
            self.var_registro, self.var_tipo_tabela, self.var_intervalo_discreto,
            self.var_ajuste_discreto
        ]
        for var in variaveis:
            var.trace_add("write", lambda *args: self.configuracao_alterada(suave=True))
        self.root.protocol("WM_DELETE_WINDOW", self.fechar)

    def configuracao_alterada(self, suave=False):
        if self._suprimir_eventos:
            return
        if not self.validar_parametros(mostrar_erro=not suave):
            return
        if self.t == 0 and not self.rodando:
            self.atualizar_estado_dinamico()
            self.dados = []
            self.indice = 0
            self.proximo_t_discreto = 0.0
            self.registrar_ponto(forcar=True)
        self.atualizar_tudo()

    def validar_parametros(self, mostrar_erro=True):
        try:
            m_cart = converter_numero(self.var_m_cart.get())
            m_block = converter_numero(self.var_m_block.get())
            mu = converter_numero(self.var_mu.get())
            L = converter_numero(self.var_L.get())
            g = converter_numero(self.var_g.get())
            tmax = converter_numero(self.var_tmax.get())
            dt = converter_numero(self.var_dt.get())
            ritmo = converter_numero(self.var_ritmo.get())
            intervalo = converter_numero(self.var_intervalo_discreto.get())
        except (TypeError, ValueError):
            if mostrar_erro:
                messagebox.showerror("Erro nos parâmetros", "Verifique se todos os campos numéricos foram preenchidos corretamente.")
            return False

        mensagens = []
        if m_cart <= 0:
            mensagens.append("A massa do carrinho deve ser maior que zero.")
        if m_block < 0:
            mensagens.append("A massa do bloco suspenso não pode ser negativa.")
        if mu < 0:
            mensagens.append("O coeficiente de atrito μ não pode ser negativo.")
        if L <= 0:
            mensagens.append("O comprimento da mesa deve ser maior que zero.")
        if g <= 0:
            mensagens.append("A gravidade deve ser maior que zero.")
        if tmax <= 0:
            mensagens.append("O tempo máximo deve ser maior que zero.")
        if dt < DT_MIN:
            mensagens.append("O passo Δt deve ser maior ou igual a 0,001 s.")
        if dt > DT_MAX:
            mensagens.append("Para boa visualização, use Δt menor ou igual a 0,5 s.")
        if dt > tmax:
            mensagens.append("O passo Δt não deve ser maior que o tempo máximo.")
        if not RITMO_MIN <= ritmo <= RITMO_MAX:
            mensagens.append("O ritmo deve estar entre 0,05× e 16×.")
        if intervalo < INTERVALO_MIN:
            mensagens.append("O intervalo de coleta discreta deve ser maior ou igual a 0,001 s.")

        if mensagens:
            if mostrar_erro:
                messagebox.showerror("Parâmetros inválidos", "\n".join(mensagens))
            return False
        return True

    # -------------------------------------------------------------------------
    # FÍSICA DO SISTEMA
    # -------------------------------------------------------------------------
    def obter_config(self):
        m_cart = max(converter_numero(self.var_m_cart.get()), 1e-9)
        m_block = max(converter_numero(self.var_m_block.get()), 0.0)
        mu = max(converter_numero(self.var_mu.get()), 0.0)
        L = max(converter_numero(self.var_L.get()), 0.01)
        g = max(converter_numero(self.var_g.get()), 0.01)
        tmax = max(converter_numero(self.var_tmax.get()), 0.01)
        dt = min(max(converter_numero(self.var_dt.get()), DT_MIN), DT_MAX)
        ritmo = min(max(converter_numero(self.var_ritmo.get()), RITMO_MIN), RITMO_MAX)
        return m_cart, m_block, mu, L, g, tmax, dt, ritmo

    def calcular_dinamica(self, velocidade=None):
        m_cart, m_block, mu, L, g, tmax, dt, ritmo = self.obter_config()
        if velocidade is None:
            velocidade = self.v

        peso_bloco = m_block * g
        normal = m_cart * g
        atrito_max = mu * normal
        massa_total = m_cart + m_block

        if m_block <= 0:
            forca_resultante = 0.0
            atrito = 0.0
            a = 0.0
            tensao = 0.0
            regime = "Sem bloco suspenso: sistema sem tração."
        elif abs(velocidade) < 1e-10 and peso_bloco <= atrito_max:
            forca_resultante = 0.0
            atrito = peso_bloco
            a = 0.0
            tensao = peso_bloco
            regime = "Repouso: o atrito equilibra o peso do bloco."
        else:
            # O bloco suspenso tende a puxar o carrinho para a direita.
            atrito = atrito_max
            forca_resultante = peso_bloco - atrito
            a = forca_resultante / massa_total

            # Se a força resultante ficar contrária ao movimento e parar o carrinho,
            # a etapa temporal corrige a velocidade para não inverter artificialmente.
            tensao = m_block * (g - a)
            regime = "Movimento: F = m_b g − μ m_c g."

        return {
            "m_cart": m_cart,
            "m_block": m_block,
            "mu": mu,
            "L": L,
            "g": g,
            "tmax": tmax,
            "dt": dt,
            "ritmo": ritmo,
            "peso_bloco": arredondar_fisico(peso_bloco),
            "normal": arredondar_fisico(normal),
            "atrito": arredondar_fisico(atrito),
            "F": arredondar_fisico(forca_resultante),
            "a": arredondar_fisico(a),
            "T": arredondar_fisico(tensao),
            "Mtot": arredondar_fisico(massa_total),
            "regime": regime
        }

    def atualizar_estado_dinamico(self):
        din = self.calcular_dinamica()
        self.a = din["a"]
        self.forca_resultante = din["F"]
        self.tensao = din["T"]
        self.atrito = din["atrito"]
        self.peso_bloco = din["peso_bloco"]
        self.normal = din["normal"]
        self.var_interpretacao.set(din["regime"])
        return din

    def estado_atual(self):
        din = self.atualizar_estado_dinamico()
        return {
            "t": arredondar_fisico(self.t),
            "x": arredondar_fisico(self.x),
            "v": arredondar_fisico(self.v),
            "a": arredondar_fisico(self.a),
            "F": arredondar_fisico(self.forca_resultante),
            "T": arredondar_fisico(self.tensao),
            "fat": arredondar_fisico(self.atrito),
            "Mtot": arredondar_fisico(din["Mtot"]),
            "m_cart": din["m_cart"],
            "m_block": din["m_block"],
            "mu": din["mu"],
            "L": din["L"],
            "g": din["g"],
            "regime": din["regime"],
        }

    def tempo_atinge_fim(self, dt):
        """Calcula, quando possível, o instante dentro do passo em que x chega a L."""
        _, _, _, L, _, _, _, _ = self.obter_config()
        if self.x >= L:
            return 0.0
        a = float(self.a)
        v = float(self.v)
        C = self.x - L
        candidatos = []

        if abs(a) < 1e-12:
            if v > 1e-12:
                tau = -C / v
                if 0 <= tau <= dt:
                    candidatos.append(tau)
        else:
            A = 0.5 * a
            B = v
            delta = B * B - 4 * A * C
            if delta >= 0:
                raiz = math.sqrt(delta)
                for tau in [(-B - raiz) / (2 * A), (-B + raiz) / (2 * A)]:
                    if 0 <= tau <= dt:
                        candidatos.append(tau)
        if candidatos:
            return min(candidatos)
        return None

    # -------------------------------------------------------------------------
    # CONTROLE DA SIMULAÇÃO
    # -------------------------------------------------------------------------
    def iniciar(self):
        if not self.validar_parametros(mostrar_erro=True):
            return
        if self.limite_atingido:
            self.reiniciar_simulacao(limpar_tabela=False)
        if not self.rodando:
            self.rodando = True
            self.var_status.set("Simulação em execução.")
            self.executar_passo()

    def pausar(self):
        self.rodando = False
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except tk.TclError:
                pass
            self.after_id = None
        self.var_status.set("Simulação pausada.")
        self.atualizar_tudo()

    def passo(self):
        if not self.validar_parametros(mostrar_erro=True):
            return
        if self.limite_atingido:
            self.var_status.set("O carrinho chegou ao fim da mesa. Use Resetar para reiniciar.")
            return
        self.rodando = False
        self.avancar_um_passo()
        self.atualizar_tudo()

    def executar_passo(self):
        if not self.rodando:
            return
        self.avancar_um_passo()
        self.atualizar_tudo(animacao=True)
        if self.rodando:
            _, _, _, _, _, _, dt, ritmo = self.obter_config()
            atraso = max(10, int(1000 * dt / ritmo))
            self.after_id = self.root.after(atraso, self.executar_passo)

    def avancar_um_passo(self):
        m_cart, m_block, mu, L, g, tmax, dt, ritmo = self.obter_config()
        if self.t >= tmax:
            self.rodando = False
            self.var_status.set("Simulação concluída: tempo máximo atingido.")
            return

        self.atualizar_estado_dinamico()
        dt_real = min(dt, tmax - self.t)
        tau_fim = self.tempo_atinge_fim(dt_real)

        if tau_fim is not None:
            dt_real = tau_fim
            self.x = L
            self.v = max(0.0, self.v + self.a * dt_real)
            self.t += dt_real
            self.wheel_angle += (self.v * dt_real) / 0.055
            self.limite_atingido = True
            self.rodando = False
            self.registrar_conforme_modo(forcar=True)
            self.var_status.set("Simulação concluída: o carrinho chegou ao fim da mesa.")
            return

        v_novo = self.v + self.a * dt_real
        if self.v > 0 and v_novo < 0:
            # Correção: o carrinho para sem inverter o movimento por erro numérico.
            dt_parada = abs(self.v / self.a) if abs(self.a) > 1e-12 else dt_real
            self.x = self.x + self.v * dt_parada + 0.5 * self.a * dt_parada * dt_parada
            self.v = 0.0
            self.t += dt_parada
        else:
            self.x = self.x + self.v * dt_real + 0.5 * self.a * dt_real * dt_real
            self.v = v_novo
            self.t += dt_real

        self.x = min(max(self.x, 0.0), L)
        self.wheel_angle += (self.v * dt_real) / 0.055
        self.atualizar_estado_dinamico()
        self.registrar_conforme_modo()

        if self.t >= tmax:
            self.rodando = False
            self.var_status.set("Simulação concluída: tempo máximo atingido.")
        elif self.x >= L:
            self.limite_atingido = True
            self.rodando = False
            self.var_status.set("Simulação concluída: o carrinho chegou ao fim da mesa.")

    def reiniciar_simulacao(self, limpar_tabela=True):
        if not self.validar_parametros(mostrar_erro=False):
            self.var_status.set("Complete os parâmetros numéricos antes de resetar.")
            return
        self.rodando = False
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except tk.TclError:
                pass
            self.after_id = None

        self.t = 0.0
        self.x = 0.0
        self.v = 0.0
        self.a = 0.0
        self.forca_resultante = 0.0
        self.tensao = 0.0
        self.atrito = 0.0
        self.peso_bloco = 0.0
        self.normal = 0.0
        self.wheel_angle = 0.0
        self.limite_atingido = False
        self.proximo_t_discreto = 0.0

        if limpar_tabela:
            self.dados = []
            self.indice = 0
            self.historico_dinamica = []

        self.atualizar_estado_dinamico()
        self.registrar_ponto(forcar=True)
        self.var_status.set("Sistema resetado. Pronto para nova simulação.")
        self.atualizar_tudo()

    # -------------------------------------------------------------------------
    # REGISTRO DE DADOS
    # -------------------------------------------------------------------------
    def registrar_conforme_modo(self, forcar=False):
        modo = self.var_registro.get()
        if modo == "Manual" and not forcar:
            return
        if modo == "Discreta" and not forcar:
            intervalo = max(converter_numero(self.var_intervalo_discreto.get()), INTERVALO_MIN)
            if self.t + 1e-12 < self.proximo_t_discreto:
                return
            self.proximo_t_discreto += intervalo
        self.registrar_ponto(forcar=forcar)

    def registrar_ponto_manual(self):
        # Registro manual da série temporal, usado para x(t), v(t), a(t), F(t) e T(t).
        self.registrar_ponto(forcar=True)
        self.atualizar_tabela()
        self.var_status.set("Ponto temporal registrado manualmente na tabela.")

    def registrar_ponto(self, forcar=False):
        estado = self.estado_atual()
        if not forcar and self.dados:
            if abs(self.dados[-1]["t"] - estado["t"]) < 1e-12:
                return
        if forcar and self.dados:
            if abs(self.dados[-1]["t"] - estado["t"]) < 1e-12:
                self.dados[-1].update(estado)
                return
        self.indice += 1
        estado["n"] = self.indice
        self.dados.append(estado)
        if len(self.dados) > MAX_DADOS:
            del self.dados[:-MAX_DADOS]

    def limpar_tabela(self):
        self.dados = []
        self.indice = 0
        self.historico_dinamica = []
        self.proximo_t_discreto = 0.0
        self.registrar_ponto(forcar=True)
        self.var_status.set("Tabela temporal e medidas discretas foram limpas.")
        self.atualizar_tabela()
        self.atualizar_tudo()

    def obter_fonte_tabela(self):
        """Escolhe a fonte dos dados: série temporal ou ensaios discretos por configuração."""
        if self.tabela_usa_dados_discretos():
            return self.historico_dinamica
        return self.dados

    def atualizar_tabela(self):
        if not hasattr(self, "tabela"):
            return
        for item in self.tabela.get_children():
            self.tabela.delete(item)
        selecionadas = self.obter_colunas_tabela()
        chaves = [self.mapa_grandezas_tabela[g]["chave"] for g in selecionadas]
        fonte = self.obter_fonte_tabela()
        for i, dado in enumerate(fonte, start=1):
            valores = [str(i)]
            for grandeza, chave in zip(selecionadas, chaves):
                casas = self.mapa_grandezas_tabela[grandeza]["casas"]
                valores.append(formato_numero(dado.get(chave, 0.0), casas))
            tag = "par" if i % 2 == 0 else "impar"
            self.tabela.insert("", "end", values=valores, tags=(tag,))
        filhos = self.tabela.get_children()
        if filhos:
            self.tabela.see(filhos[-1])

    def salvar_ponto_dinamica(self):
        """Registra uma medida discreta do ensaio atual.

        Esta é a função correta para montar tabelas experimentais do tipo:
        massa 1 → força 1, massa 2 → força 2, força 1 → aceleração 1, etc.
        Ela não depende do tempo da animação; calcula F e a a partir dos parâmetros atuais.
        """
        estado = self.estado_atual()
        medida = {
            "m_cart": estado["m_cart"],
            "m_block": estado["m_block"],
            "Mtot": estado["Mtot"],
            "mu": estado["mu"],
            "a": estado["a"],
            "F": estado["F"],
            "T": estado["T"],
            "fat": estado["fat"],
        }
        self.historico_dinamica.append(medida)

        if not self.tabela_usa_dados_discretos():
            self.var_tipo_tabela.set("Dados discretos: massas, força e aceleração")
        else:
            self.atualizar_tabela()

        n = len(self.historico_dinamica)
        self.var_status.set(
            f"Medida discreta {n} salva: M = {estado['Mtot']:.3f} kg | "
            f"F = {estado['F']:.3f} N | a = {estado['a']:.3f} m/s²."
        )
        if hasattr(self, "fig_graficos"):
            self.atualizar_graficos()

    # -------------------------------------------------------------------------
    # DESENHO DA CENA
    # -------------------------------------------------------------------------
    def desenhar_cena(self):
        ax = self.ax_cena
        ax.clear()
        estado = self.estado_atual()
        L = estado["L"]
        x = estado["x"]

        # A queda é normalizada visualmente; os cálculos continuam usando x em metros.
        y_min = -1.05
        ax.set_xlim(-0.32, L + 0.62)
        ax.set_ylim(y_min, 0.82)
        ax.set_aspect("auto")
        ax.axis("off")
        ax.set_facecolor(COR_CENA)

        # Fundo do laboratório
        ax.add_patch(Rectangle((-0.32, y_min), L + 0.94, 0.82 - y_min, facecolor=COR_CENA, edgecolor="#67e8f9", linewidth=0.8, zorder=0))
        ax.add_patch(Rectangle((-0.32, y_min), L + 0.94, 0.18, facecolor="#cffafe", edgecolor="none", zorder=0))
        for nivel in np.linspace(y_min + 0.30, 0.64, 7):
            ax.plot([-0.28, L + 0.56], [nivel, nivel], color="#cffafe", lw=0.45, zorder=0)

        # Título interno
        ax.text(
            L / 2, 0.72,
            "Sistema carrinho–bloco: aplicação da Segunda Lei de Newton",
            ha="center", va="center", fontsize=9.5, fontweight="bold", color="#172033"
        )

        # Mesa / bancada experimental
        # A bancada visual começa antes do zero da régua para que o sensor fique
        # apoiado sobre a mesa, como no arranjo experimental real.
        mesa_y = 0.18
        mesa_inicio = -0.30
        mesa_fim = L + 0.08
        mesa_largura = mesa_fim - mesa_inicio

        ax.add_patch(Rectangle((mesa_inicio, mesa_y), mesa_largura, 0.08, facecolor="#0f766e", edgecolor="#134e4a", linewidth=1.3, zorder=2))
        ax.add_patch(Rectangle((mesa_inicio, mesa_y - 0.045), mesa_largura, 0.045, facecolor="#14b8a6", edgecolor="none", zorder=2))

        # Pés da mesa: um pé no lado do sensor e outro próximo à polia.
        for px in [mesa_inicio + 0.08, max(L - 0.18, mesa_inicio + 0.14)]:
            ax.add_patch(Rectangle((px, y_min + 0.18), 0.06, mesa_y - y_min - 0.18, facecolor="#115e59", edgecolor="none", zorder=1))

        # Pequena indicação do início da medida: a mesa existe antes de x = 0,
        # mas a escala experimental continua começando em 0 m.
        ax.plot([0, 0], [mesa_y + 0.085, mesa_y + 0.18], color="#164e63", lw=1.0, zorder=4)
        ax.text(0, mesa_y + 0.20, "x = 0", ha="center", va="bottom", fontsize=6.2, fontweight="bold", color="#164e63")

        # Régua graduada
        ruler_y = mesa_y - 0.12
        ax.plot([0, L], [ruler_y, ruler_y], color="#164e63", lw=1.0, zorder=3)
        n_ticks = max(2, int(round(L / 0.1)))
        for i in range(n_ticks + 1):
            tx = min(i * 0.1, L)
            if tx > L + 1e-9:
                continue
            maior = (i % 5 == 0)
            h = 0.055 if maior else 0.030
            ax.plot([tx, tx], [ruler_y, ruler_y - h], color="#164e63", lw=0.9 if maior else 0.55, zorder=3)
            if maior:
                ax.text(tx, ruler_y - h - 0.035, f"{tx:.1f}", ha="center", va="top", fontsize=6.5, color="#164e63")
        ax.text(L + 0.04, ruler_y - 0.075, "m", ha="left", va="top", fontsize=7, fontweight="bold", color="#164e63")

        # Sensor de movimento apoiado sobre a mesa
        # O sensor fica em uma extensão da bancada antes do ponto x = 0.
        # Assim ele mede o carrinho sem aparecer suspenso no ar.
        sensor_w = 0.13
        sensor_h = 0.15
        sensor_x = mesa_inicio + 0.055
        sensor_y = mesa_y + 0.08  # base exatamente sobre o tampo da mesa

        # base de borracha do sensor, apoiada no tampo
        ax.add_patch(Rectangle((sensor_x - 0.015, mesa_y + 0.078), sensor_w + 0.030, 0.014, facecolor="#1f2937", edgecolor="none", zorder=4))
        ax.add_patch(FancyBboxPatch((sensor_x, sensor_y), sensor_w, sensor_h, boxstyle="round,pad=0.01", facecolor="#facc15", edgecolor="#111827", linewidth=1.0, zorder=5))
        ax.add_patch(Circle((sensor_x + sensor_w * 0.68, sensor_y + sensor_h * 0.56), 0.022, facecolor="#111827", edgecolor="#020617", linewidth=0.8, zorder=6))
        ax.text(sensor_x + sensor_w / 2, sensor_y + sensor_h + 0.035, "Sensor", ha="center", va="bottom", fontsize=6.5, fontweight="bold", color="#111827")

        if self.rodando:
            origem_onda_x = sensor_x + sensor_w
            origem_onda_y = sensor_y + sensor_h * 0.56
            for k in range(3):
                raio = 0.08 + ((self.t * 0.65 + k * 0.10) % 0.32)
                ax.add_patch(Arc((origem_onda_x, origem_onda_y), 2 * raio, 2 * raio, angle=0, theta1=-32, theta2=32, color=COR_CIANO, lw=1.0, zorder=4))

        # Carrinho
        cart_y = mesa_y + 0.08
        cart_w = min(0.26, max(0.18, L * 0.12))
        cart_h = 0.13
        cart_x = min(max(x, 0.0), L)
        cart_left = min(max(cart_x - cart_w / 2, 0.01), max(L - cart_w - 0.01, 0.01)) if L > cart_w else 0.01
        ax.add_patch(FancyBboxPatch((cart_left, cart_y), cart_w, cart_h, boxstyle="round,pad=0.01", facecolor=COR_AZUL, edgecolor="#075985", linewidth=1.2, zorder=5))
        ax.add_patch(Rectangle((cart_left + cart_w * 0.25, cart_y + cart_h), cart_w * 0.50, 0.06, facecolor="#a5f3fc", edgecolor="#075985", linewidth=0.7, zorder=5))
        ax.text(cart_left + cart_w / 2, cart_y + cart_h + 0.085, "carrinho", ha="center", va="bottom", fontsize=6.5, fontweight="bold", color="#0f172a")

        wheel_r = 0.032
        for wx in [cart_left + cart_w * 0.25, cart_left + cart_w * 0.75]:
            wy = cart_y - 0.005
            ax.add_patch(Circle((wx, wy), wheel_r, facecolor="#1f2937", edgecolor="#020617", linewidth=0.8, zorder=6))
            ax.add_patch(Circle((wx, wy), wheel_r * 0.38, facecolor="#e5e7eb", edgecolor="none", zorder=7))
            ax.plot([wx, wx + wheel_r * math.cos(self.wheel_angle)], [wy, wy + wheel_r * math.sin(self.wheel_angle)], color="#ffffff", lw=1.0, zorder=8)

        # Polia, fio e bloco suspenso
        pulley_x = L + 0.10
        pulley_y = mesa_y + 0.08
        pulley_r = 0.055
        ax.plot([L, pulley_x], [cart_y + cart_h * 0.65, pulley_y + pulley_r], color="#111827", lw=1.2, zorder=4)
        ax.add_patch(Circle((pulley_x, pulley_y), pulley_r, facecolor="#94a3b8", edgecolor="#0f172a", linewidth=1.0, zorder=5))
        ax.add_patch(Circle((pulley_x, pulley_y), pulley_r * 0.25, facecolor="#334155", edgecolor="none", zorder=6))

        block_w, block_h = 0.14, 0.20
        queda_visual = 0.82 * min(max(x / L, 0.0), 1.0) if L > 0 else 0.0
        block_y = pulley_y - 0.22 - queda_visual
        block_y = max(block_y, y_min + 0.22)
        ax.plot([cart_left + cart_w, pulley_x], [cart_y + cart_h * 0.65, pulley_y + pulley_r], color="#111827", lw=1.2, zorder=4)
        ax.plot([pulley_x + pulley_r, pulley_x + pulley_r], [pulley_y, block_y + block_h], color="#111827", lw=1.2, zorder=4)
        ax.add_patch(FancyBboxPatch((pulley_x + pulley_r - block_w / 2, block_y), block_w, block_h, boxstyle="round,pad=0.01", facecolor=COR_VERMELHO, edgecolor="#9f1239", linewidth=1.1, zorder=5))
        ax.text(pulley_x + pulley_r, block_y + block_h / 2, "m_b", ha="center", va="center", fontsize=7, fontweight="bold", color="#ffffff", zorder=6)

        # Vetores didáticos
        if estado["v"] > 1e-5:
            self.desenhar_seta(ax, cart_left + cart_w + 0.02, cart_y + cart_h * 0.55, 0.22, 0, "v", COR_VERDE)
        if abs(estado["a"]) > 1e-5:
            cor_a = COR_LARANJA if estado["a"] >= 0 else "#c2410c"
            self.desenhar_seta(ax, cart_left + cart_w + 0.02, cart_y + cart_h * 0.30, 0.22 * np.sign(estado["a"]), 0, "a", cor_a)
        if estado["F"] > 1e-5:
            self.desenhar_seta(ax, cart_left + cart_w * 0.52, cart_y + cart_h + 0.02, 0.18, 0, "F", COR_ROXO)
        if estado["fat"] > 1e-5 and estado["F"] > 1e-5:
            self.desenhar_seta(ax, cart_left + cart_w * 0.48, cart_y + 0.03, -0.16, 0, "f", COR_MAGENTA)

        # Painel de leituras dentro da cena
        painel_largura = max(L * 0.78, 1.55)
        ax.add_patch(FancyBboxPatch((0.02, y_min + 0.04), painel_largura, 0.30, boxstyle="round,pad=0.02", facecolor="#ffffff", edgecolor="#67e8f9", linewidth=1.0, zorder=10))
        colunas_x = [0.06, 0.06 + painel_largura * 0.32, 0.06 + painel_largura * 0.64]
        ax.text(colunas_x[0], y_min + 0.27, f"t = {formato_numero(estado['t'], 2)} s", fontsize=6.8, fontweight="bold", color="#0369a1", zorder=11)
        ax.text(colunas_x[1], y_min + 0.27, f"x = {formato_numero(estado['x'], 3)} m", fontsize=6.8, fontweight="bold", color="#0891b2", zorder=11)
        ax.text(colunas_x[2], y_min + 0.27, f"v = {formato_numero(estado['v'], 3)} m/s", fontsize=6.8, fontweight="bold", color="#15803d", zorder=11)
        ax.text(colunas_x[0], y_min + 0.18, f"a = {formato_numero(estado['a'], 3)} m/s²", fontsize=6.8, fontweight="bold", color="#c2410c", zorder=11)
        ax.text(colunas_x[1], y_min + 0.18, f"F = {formato_numero(estado['F'], 3)} N", fontsize=6.8, fontweight="bold", color="#6d28d9", zorder=11)
        ax.text(colunas_x[2], y_min + 0.18, f"T = {formato_numero(estado['T'], 3)} N", fontsize=6.8, fontweight="bold", color="#0e7490", zorder=11)
        ax.text(0.06, y_min + 0.085, estado["regime"], ha="left", va="center", fontsize=6.5, color="#475569", zorder=11)

        self.fig_cena.tight_layout(pad=0.25)
        self.canvas_cena.draw_idle()

    def desenhar_seta(self, ax, x0, y0, dx, dy, label, cor):
        ax.arrow(x0, y0, dx, dy, head_width=0.035, head_length=0.035, length_includes_head=True, color=cor, linewidth=1.2, zorder=12)
        ax.text(x0 + dx + (0.025 if dx >= 0 else -0.025), y0 + dy + 0.015, label, ha="left" if dx >= 0 else "right", va="bottom", fontsize=7, fontweight="bold", color=cor, zorder=13)

    # -------------------------------------------------------------------------
    # GRÁFICOS
    # -------------------------------------------------------------------------
    def atualizar_graficos(self):
        self.fig_graficos.clear()
        modo = self.var_grafico.get()
        if modo == "Todos":
            grade = self.fig_graficos.add_gridspec(2, 3, hspace=0.58, wspace=0.42, top=0.91, bottom=0.14, left=0.07, right=0.98)
            eixos = [
                self.fig_graficos.add_subplot(grade[0, 0]),
                self.fig_graficos.add_subplot(grade[0, 1]),
                self.fig_graficos.add_subplot(grade[0, 2]),
                self.fig_graficos.add_subplot(grade[1, 0:2]),
                self.fig_graficos.add_subplot(grade[1, 2]),
            ]
            grandezas = ["x(t)", "v(t)", "a(t)", "F(t)", "T(t)"]
            self.lbl_nota_grafico.config(text="Mostrando movimento, força resultante e tensão.")
            for ax, grandeza in zip(eixos, grandezas):
                self.plotar_grandeza(ax, grandeza)
        elif modo == "Discretos":
            grade = self.fig_graficos.add_gridspec(1, 3, wspace=0.42, top=0.88, bottom=0.19, left=0.07, right=0.98)
            eixos = [self.fig_graficos.add_subplot(grade[0, i]) for i in range(3)]
            relacoes = ["F × a", "a × M", "F × M"]
            self.lbl_nota_grafico.config(text=f"Três relações discretas • {len(self.historico_dinamica)} medidas.")
            for ax, relacao in zip(eixos, relacoes):
                self.plotar_grafico_discreto(ax, relacao)
        elif modo in {"F × a", "a × M", "F × M"}:
            ax = self.fig_graficos.add_subplot(111)
            self.fig_graficos.subplots_adjust(top=0.89, bottom=0.17, left=0.11, right=0.96)
            self.lbl_nota_grafico.config(text=f"Relação discreta {modo} • {len(self.historico_dinamica)} medidas.")
            self.plotar_grafico_discreto(ax, modo)
        else:
            ax = self.fig_graficos.add_subplot(111)
            self.lbl_nota_grafico.config(text=f"Mostrando {modo}.")
            self.fig_graficos.subplots_adjust(top=0.89, bottom=0.17, left=0.11, right=0.96)
            self.plotar_grandeza(ax, modo)

        self.canvas_graficos.draw_idle()

    def plotar_grafico_discreto(self, ax, relacao):
        mapas = {
            "F × a": ("a", "F", "a (m/s²)", "F (N)", "Força × aceleração", COR_ROXO, "#faf5ff", "F=A·a+B", "F=K/a+B", "N"),
            "a × M": ("Mtot", "a", "M total (kg)", "a (m/s²)", "Aceleração × massa", COR_LARANJA, "#fff7ed", "a=A·M+B", "a=K/M+B", "m/s²"),
            "F × M": ("Mtot", "F", "M total (kg)", "F (N)", "Força × massa", COR_VERDE, "#f0fdf4", "F=A·M+B", "F=K/M+B", "N"),
        }
        chave_x, chave_y, xlabel, ylabel, titulo, cor, fundo, eq_linear, eq_hiper, unidade = mapas[relacao]
        formatar_eixo(ax, xlabel=xlabel, ylabel=ylabel, titulo=titulo, cor_fundo=fundo)

        xs = np.array([p.get(chave_x, np.nan) for p in self.historico_dinamica], dtype=float)
        ys = np.array([p.get(chave_y, np.nan) for p in self.historico_dinamica], dtype=float)
        mascara = np.isfinite(xs) & np.isfinite(ys)
        xs, ys = xs[mascara], ys[mascara]
        if len(xs) == 0:
            ax.text(0.5, 0.5, "Registre medidas por ensaio\ncom o botão Reg. medida.",
                    transform=ax.transAxes, ha="center", va="center", fontsize=8, color="#64748b")
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            return

        ordem = np.argsort(xs)
        ax.plot(xs[ordem], ys[ordem], color=cor, linewidth=1.2, alpha=0.45, zorder=2)
        ax.scatter(xs, ys, s=38, color=cor, edgecolor="#ffffff", linewidth=0.9, label="medidas", zorder=4)
        for indice, (x_valor, y_valor) in enumerate(zip(xs, ys), start=1):
            ax.annotate(str(indice), (x_valor, y_valor), xytext=(4, 4), textcoords="offset points",
                        fontsize=6, color="#334155")

        xmin, xmax = float(np.min(xs)), float(np.max(xs))
        x_curva = np.array([xmin]) if abs(xmax - xmin) < 1e-12 else np.linspace(xmin, xmax, 260)
        escolha_ajuste = self.var_ajuste_discreto.get()
        textos = []
        if escolha_ajuste in ("Linear", "Linear + hiperbólico"):
            fit = ajuste_linear(xs, ys)
            if fit is not None and len(x_curva) > 1:
                ax.plot(x_curva, fit["A"] * x_curva + fit["B"], color=COR_AZUL, linewidth=1.8, label="linear")
                textos.append(f"{eq_linear}\nA={fit['A']:.4f}  B={fit['B']:.4f}\nRMSE={fit['rmse']:.4f} {unidade}")

        if escolha_ajuste in ("Hiperbólico", "Linear + hiperbólico"):
            fit = ajuste_hiperbolico_inverso(xs, ys)
            x_hiper = x_curva[np.abs(x_curva) > 1e-12]
            if fit is not None and len(x_hiper) > 1:
                ax.plot(x_hiper, fit["K"] / x_hiper + fit["B"], color=COR_MAGENTA,
                        linewidth=1.8, linestyle="--", label="hiperbólico")
                textos.append(f"{eq_hiper}\nK={fit['K']:.4f}  B={fit['B']:.4f}\nRMSE={fit['rmse']:.4f} {unidade}")

        ajustar_limites_constantes(ax, xs, ys, margem_x=0.10, margem_y=0.16)
        if textos:
            colocar_equacao_interna(ax, "\n\n".join(textos), cor=cor, fontsize=5.8)
        ax.legend(fontsize=6, loc="best", frameon=True, framealpha=0.9)

    def plotar_grandeza(self, ax, grandeza):
        mapa = {
            "x(t)": ("x", "x (m)", "Posição x(t)", COR_AZUL, "#ecfeff"),
            "v(t)": ("v", "v (m/s)", "Velocidade v(t)", COR_VERDE, "#f0fdf4"),
            "a(t)": ("a", "a (m/s²)", "Aceleração a(t)", COR_LARANJA, "#fff7ed"),
            "F(t)": ("F", "F (N)", "Força resultante F(t)", COR_ROXO, "#faf5ff"),
            "T(t)": ("T", "T (N)", "Tensão T(t)", COR_CIANO, "#f0fdfa"),
        }
        chave, ylabel, titulo, cor, cor_fundo = mapa.get(grandeza, mapa["x(t)"])
        formatar_eixo(ax, xlabel="t (s)", ylabel=ylabel, titulo=titulo, cor_fundo=cor_fundo)

        tempos = np.array([d["t"] for d in self.dados], dtype=float)
        valores = np.array([d.get(chave, 0.0) for d in self.dados], dtype=float)

        if len(tempos) >= 1:
            ax.fill_between(tempos, 0, valores, color=cor, alpha=0.10)
            ax.plot(tempos, valores, color=cor, linewidth=1.8, marker="o", markerfacecolor="#ffffff",
                    markeredgecolor=cor, markeredgewidth=0.8, markersize=3.0)
            ax.scatter([tempos[-1]], [valores[-1]], s=26, color=COR_VERMELHO, edgecolor="#ffffff", linewidth=0.7, zorder=5)
            ajustar_limites_constantes(ax, tempos, valores)
        else:
            ax.plot([0], [0], color=cor, marker="o")

        texto = self.texto_equacao_grafico(grandeza, tempos, valores)
        colocar_equacao_interna(ax, texto, cor=cor, fontsize=6.2)

    def texto_equacao_grafico(self, grandeza, tempos, valores):
        estado = self.estado_atual()
        if len(tempos) < 2:
            if grandeza == "x(t)":
                return "x(t): aguardando dados"
            if grandeza == "v(t)":
                return "v(t): aguardando dados"
            if grandeza == "a(t)":
                return f"a = {estado['a']:.3f} m/s²"
            if grandeza == "F(t)":
                return f"F = {estado['F']:.3f} N"
            if grandeza == "T(t)":
                return f"T = {estado['T']:.3f} N"

        if grandeza == "x(t)" and len(tempos) >= 3:
            try:
                c = np.polyfit(tempos, valores, 2)
                return f"x(t) = {c[0]:.3f}t² + {c[1]:.3f}t + {c[2]:.3f}"
            except (TypeError, ValueError, np.linalg.LinAlgError):
                return "x(t): ajuste indisponível"
        if grandeza == "v(t)" and len(tempos) >= 2:
            try:
                c = np.polyfit(tempos, valores, 1)
                return f"v(t) = {c[0]:.3f}t + {c[1]:.3f}"
            except (TypeError, ValueError, np.linalg.LinAlgError):
                return "v(t): ajuste indisponível"
        if grandeza == "a(t)":
            return f"a médio = {float(np.mean(valores)):.3f} m/s²"
        if grandeza == "F(t)":
            return f"F = m·a ≈ {float(np.mean(valores)):.3f} N"
        if grandeza == "T(t)":
            return f"T médio = {float(np.mean(valores)):.3f} N"
        return "Dados experimentais"

    def atualizar_tudo(self, animacao=False):
        if not self.validar_parametros(mostrar_erro=False):
            return
        if hasattr(self, "ax_cena"):
            self.desenhar_cena()
        agora = time.monotonic()
        atualizar_grafico = not animacao or self.limite_atingido or agora - self._ultimo_redesenho_grafico >= INTERVALO_GRAFICO
        atualizar_tabela = not animacao or self.limite_atingido or agora - self._ultima_atualizacao_tabela >= INTERVALO_TABELA
        if hasattr(self, "fig_graficos") and atualizar_grafico:
            self.atualizar_graficos()
            self._ultimo_redesenho_grafico = agora
        if hasattr(self, "tabela") and atualizar_tabela:
            self.atualizar_tabela()
            self._ultima_atualizacao_tabela = agora

    # -------------------------------------------------------------------------
    # ANÁLISE DINÂMICA F × a
    # -------------------------------------------------------------------------
    def mostrar_analise_dinamica(self):
        """Abre uma janela de análise discreta com escolha de gráfico e ajuste de curva."""
        if len(self.historico_dinamica) < 2:
            messagebox.showwarning(
                "Dados insuficientes",
                "Registre ao menos 2 medidas discretas com o botão 'Reg. medida'.\n\n"
                "Exemplo: massa 1 → força 1 → aceleração 1; depois mude a massa e registre novamente."
            )
            return

        relacoes = {
            "Força resultante × Aceleração": {
                "x": "a", "y": "F",
                "xlabel": "Aceleração a (m/s²)",
                "ylabel": "Força resultante F (N)",
                "titulo": "Segunda Lei de Newton: F em função de a",
                "equacao_linear": "F = A·a + B",
                "equacao_hiperbolica": "F = K/a + B",
                "unidade_rmse": "N",
                "interpretacao": "Para a Segunda Lei de Newton, o ajuste linear é o mais indicado: F = M·a. O coeficiente angular representa a massa experimental."
            },
            "Massa total × Aceleração": {
                "x": "Mtot", "y": "a",
                "xlabel": "Massa total M (kg)",
                "ylabel": "Aceleração a (m/s²)",
                "titulo": "Proporcionalidade inversa: a em função de M",
                "equacao_linear": "a = A·M + B",
                "equacao_hiperbolica": "a = K/M + B",
                "unidade_rmse": "m/s²",
                "interpretacao": "Quando a força resultante é aproximadamente constante, o modelo físico esperado é hiperbólico: a = F/M."
            },
            "Massa total × Força resultante": {
                "x": "Mtot", "y": "F",
                "xlabel": "Massa total M (kg)",
                "ylabel": "Força resultante F (N)",
                "titulo": "Força resultante em função da massa total",
                "equacao_linear": "F = A·M + B",
                "equacao_hiperbolica": "F = K/M + B",
                "unidade_rmse": "N",
                "interpretacao": "Use este gráfico para observar como a força resultante calculada muda quando as massas do sistema são alteradas."
            },
            "Massa do carrinho × Aceleração": {
                "x": "m_cart", "y": "a",
                "xlabel": "Massa do carrinho Mc (kg)",
                "ylabel": "Aceleração a (m/s²)",
                "titulo": "Aceleração em função da massa do carrinho",
                "equacao_linear": "a = A·Mc + B",
                "equacao_hiperbolica": "a = K/Mc + B",
                "unidade_rmse": "m/s²",
                "interpretacao": "Ao aumentar a massa do carrinho, mantendo a força próxima de constante, a aceleração tende a diminuir."
            },
            "Massa do bloco suspenso × Força resultante": {
                "x": "m_block", "y": "F",
                "xlabel": "Massa suspensa Mb (kg)",
                "ylabel": "Força resultante F (N)",
                "titulo": "Força resultante em função da massa suspensa",
                "equacao_linear": "F = A·Mb + B",
                "equacao_hiperbolica": "F = K/Mb + B",
                "unidade_rmse": "N",
                "interpretacao": "Ao aumentar a massa suspensa, o peso que puxa o sistema aumenta; por isso o ajuste linear costuma ser didaticamente útil."
            },
            "Massa do bloco suspenso × Aceleração": {
                "x": "m_block", "y": "a",
                "xlabel": "Massa suspensa Mb (kg)",
                "ylabel": "Aceleração a (m/s²)",
                "titulo": "Aceleração em função da massa suspensa",
                "equacao_linear": "a = A·Mb + B",
                "equacao_hiperbolica": "a = K/Mb + B",
                "unidade_rmse": "m/s²",
                "interpretacao": "Este gráfico mostra como o aumento da massa suspensa altera simultaneamente a força motora e a massa total do sistema."
            },
            "Massa total × Atrito": {
                "x": "Mtot", "y": "fat",
                "xlabel": "Massa total M (kg)",
                "ylabel": "Força de atrito f (N)",
                "titulo": "Atrito em função da massa total",
                "equacao_linear": "f = A·M + B",
                "equacao_hiperbolica": "f = K/M + B",
                "unidade_rmse": "N",
                "interpretacao": "Este gráfico ajuda a discutir o papel do atrito no sistema carrinho–bloco."
            },
            "Tensão × Aceleração": {
                "x": "a", "y": "T",
                "xlabel": "Aceleração a (m/s²)",
                "ylabel": "Tensão T (N)",
                "titulo": "Tensão no fio em função da aceleração",
                "equacao_linear": "T = A·a + B",
                "equacao_hiperbolica": "T = K/a + B",
                "unidade_rmse": "N",
                "interpretacao": "A tensão no fio depende da massa suspensa e da aceleração do bloco: T = mb(g − a)."
            },
        }

        win = tk.Toplevel(self.root)
        win.title("Análise discreta — escolha do gráfico e do ajuste de curva")
        win.geometry("1120x680")
        win.minsize(960, 590)
        win.configure(bg=COR_FUNDO)

        win.columnconfigure(0, weight=0, minsize=270)
        win.columnconfigure(1, weight=1)
        win.rowconfigure(0, weight=1)

        painel = tk.Frame(win, bg=COR_PAINEL, bd=0, highlightthickness=1, highlightbackground=COR_CIANO)
        painel.grid(row=0, column=0, sticky="nsw", padx=(8, 5), pady=8)
        painel.grid_propagate(False)
        painel.configure(width=270)
        painel.columnconfigure(0, weight=1)

        tk.Label(
            painel,
            text="Análise dos dados discretos",
            bg=COR_PAINEL,
            fg=COR_TEXTO,
            font=("Segoe UI", 11, "bold")
        ).grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 2))

        tk.Label(
            painel,
            text="Escolha a relação experimental, o tipo visual do gráfico e o ajuste de curva.",
            bg=COR_PAINEL,
            fg=COR_TEXTO_SUAVE,
            font=("Segoe UI", 8),
            wraplength=245,
            justify="left"
        ).grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))

        var_relacao = tk.StringVar(value="Força resultante × Aceleração")
        var_tipo_grafico = tk.StringVar(value="Dispersão + linha")
        var_ajuste = tk.StringVar(value=self.var_ajuste_discreto.get() if self.var_ajuste_discreto.get() else "Linear")
        var_mostrar_equacao = tk.BooleanVar(value=True)

        def criar_combo_analise(row, titulo, variavel, opcoes):
            bloco = tk.Frame(painel, bg=COR_GRUPO, bd=0, highlightthickness=1, highlightbackground=COR_ROXO)
            bloco.grid(row=row, column=0, sticky="ew", padx=8, pady=4)
            bloco.columnconfigure(0, weight=1)
            tk.Label(
                bloco,
                text=titulo.upper(),
                bg=COR_GRUPO,
                fg="#c4b5fd",
                font=("Segoe UI", 7, "bold")
            ).grid(row=0, column=0, sticky="w", padx=6, pady=(5, 1))
            combo = ttk.Combobox(
                bloco,
                textvariable=variavel,
                values=opcoes,
                state="readonly",
                font=("Segoe UI", 8),
                width=26
            )
            combo.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 6))
            return combo

        combo_relacao = criar_combo_analise(2, "Tipo de gráfico físico", var_relacao, list(relacoes.keys()))
        combo_tipo = criar_combo_analise(3, "Representação visual", var_tipo_grafico, ["Dispersão", "Linha", "Dispersão + linha"])
        combo_ajuste = criar_combo_analise(4, "Ajuste de curva", var_ajuste, ["Sem ajuste", "Linear", "Hiperbólico", "Linear + hiperbólico"])

        chk_eq = tk.Checkbutton(
            painel,
            text="Mostrar equação e RMSE dentro do gráfico",
            variable=var_mostrar_equacao,
            command=lambda: atualizar_analise(),
            bg=COR_PAINEL,
            fg=COR_TEXTO,
            activebackground=COR_PAINEL,
            activeforeground="#ffffff",
            selectcolor="#151225",
            font=("Segoe UI", 8)
        )
        chk_eq.grid(row=5, column=0, sticky="w", padx=10, pady=(4, 2))

        texto_info = tk.Text(
            painel,
            height=11,
            wrap="word",
            bg="#151225",
            fg=COR_TEXTO,
            insertbackground=COR_AMARELO,
            relief="flat",
            font=("Segoe UI", 8)
        )
        texto_info.grid(row=7, column=0, sticky="nsew", padx=8, pady=(6, 8))
        painel.rowconfigure(7, weight=1)

        area_grafico = tk.Frame(win, bg=COR_CARD, bd=0, highlightthickness=1, highlightbackground=COR_LARANJA)
        area_grafico.grid(row=0, column=1, sticky="nsew", padx=(0, 8), pady=8)
        area_grafico.columnconfigure(0, weight=1)
        area_grafico.rowconfigure(1, weight=1)

        topo = tk.Frame(area_grafico, bg="#f8fafc")
        topo.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 0))
        topo.columnconfigure(0, weight=1)

        lbl_titulo_grafico = tk.Label(
            topo,
            text="Gráfico selecionado",
            bg="#f8fafc",
            fg="#0f172a",
            font=("Segoe UI", 10, "bold")
        )
        lbl_titulo_grafico.grid(row=0, column=0, sticky="w")

        lbl_quantidade = tk.Label(
            topo,
            text=f"Medidas registradas: {len(self.historico_dinamica)}",
            bg="#f8fafc",
            fg="#475569",
            font=("Segoe UI", 8, "bold")
        )
        lbl_quantidade.grid(row=0, column=1, sticky="e")

        fig = Figure(figsize=(8.2, 5.8), dpi=100, facecolor="#ffffff")
        ax = fig.add_subplot(111)
        canvas = FigureCanvasTkAgg(fig, master=area_grafico)
        canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=8, pady=8)

        def obter_vetor(chave):
            return np.array([p.get(chave, 0.0) for p in self.historico_dinamica], dtype=float)

        def desenhar_linha_dados(ax_local, xs_plot, ys_plot, cor="#475569"):
            if len(xs_plot) < 2:
                return
            ordem = np.argsort(xs_plot)
            ax_local.plot(xs_plot[ordem], ys_plot[ordem], color=cor, linewidth=1.4, alpha=0.75, label="Ligação dos pontos")

        def aplicar_ajuste(ax_local, xs_plot, ys_plot, meta, modo_ajuste):
            textos = []
            unidade = meta["unidade_rmse"]
            xmin = float(np.min(xs_plot))
            xmax = float(np.max(xs_plot))
            if abs(xmax - xmin) < 1e-12:
                x_curva = np.array([xmin])
            else:
                x_curva = np.linspace(xmin, xmax, 260)

            if modo_ajuste in ("Linear", "Linear + hiperbólico"):
                fit_lin = ajuste_linear(xs_plot, ys_plot)
                if fit_lin is not None and len(x_curva) > 1:
                    y_curva = fit_lin["A"] * x_curva + fit_lin["B"]
                    ax_local.plot(x_curva, y_curva, color=COR_AZUL, linewidth=2.2, label="Ajuste linear")
                    textos.append(
                        f"Linear:\n{meta['equacao_linear']}\n"
                        f"A = {fit_lin['A']:.4f}\nB = {fit_lin['B']:.4f}\nRMSE = {fit_lin['rmse']:.4f} {unidade}"
                    )
                else:
                    textos.append("Linear:\nvarie a grandeza do eixo X")

            if modo_ajuste in ("Hiperbólico", "Linear + hiperbólico"):
                fit_hip = ajuste_hiperbolico_inverso(xs_plot, ys_plot)
                x_hip = x_curva[np.abs(x_curva) > 1e-12]
                if fit_hip is not None and len(x_hip) > 1:
                    y_hip = fit_hip["K"] / x_hip + fit_hip["B"]
                    ax_local.plot(x_hip, y_hip, color=COR_MAGENTA, linewidth=2.2, linestyle="--", label="Ajuste hiperbólico")
                    textos.append(
                        f"Hiperbólico:\n{meta['equacao_hiperbolica']}\n"
                        f"K = {fit_hip['K']:.4f}\nB = {fit_hip['B']:.4f}\nRMSE = {fit_hip['rmse']:.4f} {unidade}"
                    )
                else:
                    textos.append("Hiperbólico:\nvarie a grandeza do eixo X\ne evite X = 0")

            return "\n\n".join(textos)

        def atualizar_texto_info(meta, texto_ajuste):
            texto_info.configure(state="normal")
            texto_info.delete("1.0", "end")
            texto = (
                f"Relação selecionada:\n{var_relacao.get()}\n\n"
                f"Interpretação física:\n{meta['interpretacao']}\n\n"
                f"Ajuste escolhido:\n{var_ajuste.get()}\n\n"
            )
            if texto_ajuste:
                texto += "Resultado do ajuste:\n" + texto_ajuste.replace("\n\n", "\n")
            else:
                texto += "Resultado do ajuste:\nSem ajuste aplicado."
            texto_info.insert("1.0", texto)
            texto_info.configure(state="disabled")

        def atualizar_analise(event=None):
            self.var_ajuste_discreto.set(var_ajuste.get())
            meta = relacoes[var_relacao.get()]
            xs = obter_vetor(meta["x"])
            ys = obter_vetor(meta["y"])
            mascara = np.isfinite(xs) & np.isfinite(ys)
            xs = xs[mascara]
            ys = ys[mascara]

            ax.clear()
            formatar_eixo(ax, xlabel=meta["xlabel"], ylabel=meta["ylabel"], titulo=meta["titulo"])
            lbl_titulo_grafico.configure(text=meta["titulo"])

            if len(xs) == 0:
                colocar_equacao_interna(ax, "Sem dados válidos para esta relação.", cor="#991b1b", fontsize=8)
                canvas.draw_idle()
                return

            tipo_visual = var_tipo_grafico.get()
            if tipo_visual in ("Dispersão", "Dispersão + linha"):
                ax.scatter(xs, ys, s=58, color=COR_VERDE, edgecolor="#166534", linewidth=0.9, label="Medidas discretas", zorder=5)
            if tipo_visual in ("Linha", "Dispersão + linha"):
                desenhar_linha_dados(ax, xs, ys)

            texto_ajuste = ""
            if var_ajuste.get() != "Sem ajuste":
                texto_ajuste = aplicar_ajuste(ax, xs, ys, meta, var_ajuste.get()) or ""

            if var_mostrar_equacao.get() and texto_ajuste:
                colocar_equacao_interna(ax, texto_ajuste, cor="#6d28d9", fontsize=7.2)
            elif var_mostrar_equacao.get() and var_ajuste.get() == "Sem ajuste":
                colocar_equacao_interna(ax, "Sem ajuste de curva.\nMostrando apenas os dados discretos.", cor="#475569", fontsize=7.4)

            ajustar_limites_constantes(ax, xs, ys)
            ax.legend(fontsize=7.5, loc="best", frameon=True)
            fig.tight_layout(pad=1.5)
            canvas.draw_idle()
            atualizar_texto_info(meta, texto_ajuste)

        def salvar_png():
            caminho = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("Imagem PNG", "*.png"), ("Todos os arquivos", "*.*")],
                initialfile=f"analise_segunda_lei_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )
            if not caminho:
                return
            try:
                fig.savefig(caminho, dpi=180, bbox_inches="tight")
                self.var_status.set("Gráfico de análise discreta exportado em PNG.")
                messagebox.showinfo("Exportação concluída", f"Gráfico salvo em:\n{caminho}")
            except OSError as erro:
                messagebox.showerror("Erro ao exportar gráfico", str(erro))

        botoes = tk.Frame(painel, bg=COR_PAINEL)
        botoes.grid(row=6, column=0, sticky="ew", padx=8, pady=(4, 2))
        botoes.columnconfigure(0, weight=1)
        botoes.columnconfigure(1, weight=1)
        ttk.Button(botoes, text="Atualizar", command=atualizar_analise, style="Accent.TButton").grid(row=0, column=0, sticky="ew", padx=(0, 3))
        ttk.Button(botoes, text="Salvar PNG", command=salvar_png).grid(row=0, column=1, sticky="ew", padx=(3, 0))

        for combo in (combo_relacao, combo_tipo, combo_ajuste):
            combo.bind("<<ComboboxSelected>>", atualizar_analise)

        atualizar_analise()

    # -------------------------------------------------------------------------
    # PRESETS E EXPORTAÇÃO
    # -------------------------------------------------------------------------
    def aplicar_preset(self, codigo):
        self.rodando = False
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except tk.TclError:
                pass
            self.after_id = None
        self._suprimir_eventos = True
        if codigo == 1:
            self.var_m_cart.set("0,50")
            self.var_m_block.set("0,20")
            self.var_mu.set("0,00")
            self.var_L.set("2,00")
            self.var_tmax.set("4,00")
            self.var_dt.set("0,05")
            mensagem = "Preset aplicado: sistema sem atrito."
        elif codigo == 2:
            self.var_m_cart.set("0,80")
            self.var_m_block.set("0,25")
            self.var_mu.set("0,12")
            self.var_L.set("2,00")
            self.var_tmax.set("5,00")
            self.var_dt.set("0,05")
            mensagem = "Preset aplicado: atrito médio."
        elif codigo == 3:
            self.var_m_cart.set("1,00")
            self.var_m_block.set("0,10")
            self.var_mu.set("0,12")
            self.var_L.set("2,00")
            self.var_tmax.set("5,00")
            self.var_dt.set("0,05")
            mensagem = "Preset aplicado: equilíbrio estático."
        self._suprimir_eventos = False
        self.reiniciar_simulacao(limpar_tabela=True)
        self.var_status.set(mensagem)

    def exportar_csv(self):
        if not self.validar_parametros(mostrar_erro=True):
            return
        exportando_discreto = self.tabela_usa_dados_discretos()
        fonte = self.historico_dinamica if exportando_discreto else self.dados
        if not fonte:
            messagebox.showwarning("Sem dados", "Não há dados para exportar na tabela ativa.")
            return

        prefixo = "dados_discretos" if exportando_discreto else "dados_temporais"
        nome_inicial = f"{prefixo}_segunda_lei_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        caminho = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Arquivo CSV", "*.csv"), ("Todos os arquivos", "*.*")],
            initialfile=nome_inicial
        )
        if not caminho:
            return

        campos = [
            "n", "tipo_dado", "tempo_s", "posicao_m", "velocidade_m_s",
            "aceleracao_m_s2", "forca_resultante_N", "tensao_N", "atrito_N",
            "massa_carrinho_kg", "massa_bloco_kg", "massa_total_kg", "mu"
        ]
        try:
            with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow([NOME_APLICATIVO])
                writer.writerow(["Versão", VERSAO_APLICATIVO])
                writer.writerow(["Autor", AUTOR])
                writer.writerow(["Exportado em", datetime.now().strftime("%d/%m/%Y %H:%M:%S")])
                writer.writerow([])
                writer.writerow(campos)
                for i, dado in enumerate(fonte, start=1):
                    writer.writerow([
                        dado.get("n", i),
                        "discreto_por_ensaio" if exportando_discreto else "temporal",
                        dado.get("t", ""),
                        dado.get("x", ""),
                        dado.get("v", ""),
                        dado.get("a", 0.0),
                        dado.get("F", 0.0),
                        dado.get("T", 0.0),
                        dado.get("fat", 0.0),
                        dado.get("m_cart", 0.0),
                        dado.get("m_block", 0.0),
                        dado.get("Mtot", 0.0),
                        dado.get("mu", 0.0),
                    ])
            self.var_status.set("Tabela ativa exportada em CSV com sucesso.")
            messagebox.showinfo("Exportação concluída", f"Arquivo salvo em:\n{caminho}")
        except OSError as erro:
            messagebox.showerror("Erro ao exportar", str(erro))

    def exportar_relatorio(self):
        if not self.validar_parametros(mostrar_erro=True):
            return
        caminho = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Arquivo TXT", "*.txt"), ("Todos os arquivos", "*.*")],
            initialfile=f"relatorio_segunda_lei_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if not caminho:
            return
        estado = self.estado_atual()
        try:
            with open(caminho, "w", encoding="utf-8-sig") as f:
                f.write("RELATÓRIO AUTOMÁTICO — LABORATÓRIO VIRTUAL: SEGUNDA LEI DE NEWTON\n")
                f.write("=" * 78 + "\n")
                f.write(f"Aplicação: {NOME_APLICATIVO} | versão {VERSAO_APLICATIVO}\n")
                f.write(f"Autor: {AUTOR}\n")
                f.write(f"Data e hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
                f.write("1. MODELO FÍSICO\n")
                f.write("Sistema carrinho–bloco em mesa horizontal, conectado por fio ideal e polia ideal.\n")
                f.write("Força resultante: F = m_b g − μ m_c g, quando há movimento.\n")
                f.write("Aceleração: a = F / (m_c + m_b).\n\n")
                f.write("2. PARÂMETROS\n")
                f.write(f"Massa do carrinho: {estado['m_cart']:.4f} kg\n")
                f.write(f"Massa do bloco suspenso: {estado['m_block']:.4f} kg\n")
                f.write(f"Massa total: {estado['Mtot']:.4f} kg\n")
                f.write(f"Coeficiente de atrito μ: {estado['mu']:.4f}\n")
                f.write(f"Gravidade: {estado['g']:.4f} m/s²\n")
                f.write(f"Comprimento da mesa: {estado['L']:.4f} m\n\n")
                f.write("3. RESULTADO FINAL DA SIMULAÇÃO\n")
                f.write(f"Tempo final: {estado['t']:.4f} s\n")
                f.write(f"Posição final: {estado['x']:.4f} m\n")
                f.write(f"Velocidade final: {estado['v']:.4f} m/s\n")
                f.write(f"Aceleração: {estado['a']:.4f} m/s²\n")
                f.write(f"Força resultante: {estado['F']:.4f} N\n")
                f.write(f"Tensão no fio: {estado['T']:.4f} N\n")
                f.write(f"Atrito: {estado['fat']:.4f} N\n")
                f.write(f"Interpretação: {estado['regime']}\n\n")
                f.write("4. DADOS TEMPORAIS COLETADOS\n")
                f.write("n; t(s); x(m); v(m/s); a(m/s²); F(N); T(N); f_atrito(N)\n")
                for dado in self.dados:
                    f.write(
                        f"{dado.get('n', '')}; {dado.get('t', 0):.4f}; {dado.get('x', 0):.4f}; "
                        f"{dado.get('v', 0):.4f}; {dado.get('a', 0):.4f}; {dado.get('F', 0):.4f}; "
                        f"{dado.get('T', 0):.4f}; {dado.get('fat', 0):.4f}\n"
                    )

                f.write("\n5. MEDIDAS DISCRETAS POR ENSAIO\n")
                f.write("n; Mc(kg); Mb(kg); Mtotal(kg); F(N); a(m/s²); T(N); f_atrito(N); mu\n")
                for i, dado in enumerate(self.historico_dinamica, start=1):
                    f.write(
                        f"{i}; {dado.get('m_cart', 0):.4f}; {dado.get('m_block', 0):.4f}; "
                        f"{dado.get('Mtot', 0):.4f}; {dado.get('F', 0):.4f}; {dado.get('a', 0):.4f}; "
                        f"{dado.get('T', 0):.4f}; {dado.get('fat', 0):.4f}; {dado.get('mu', 0):.4f}\n"
                    )
            self.var_status.set("Relatório TXT exportado com sucesso.")
            messagebox.showinfo("Relatório concluído", f"Arquivo salvo em:\n{caminho}")
        except OSError as erro:
            messagebox.showerror("Erro ao exportar", str(erro))

    def exportar_roteiro_pre_pos_teste(self):
        caminho = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Arquivo TXT", "*.txt"), ("Todos os arquivos", "*.*")],
            initialfile=f"roteiro_pre_pos_segunda_lei_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if not caminho:
            return
        texto = """ROTEIRO DE PRÉ-TESTE E PÓS-TESTE — SEGUNDA LEI DE NEWTON

Tema: Sistema carrinho–bloco e relação entre força resultante, massa e aceleração.

PRÉ-TESTE
1. O que acontece com a aceleração quando a força resultante aumenta?
2. O que acontece com a aceleração quando a massa total do sistema aumenta?
3. Qual é o papel do atrito no movimento do carrinho?
4. Em que condição o sistema permanece em repouso?
5. Como reconhecer, em um gráfico v(t), que a aceleração é constante?

ATIVIDADE COM O SIMULADOR
1. Escolha o preset "Sem atrito" e execute a simulação.
2. Registre um ponto F×a.
3. Aumente a massa do bloco suspenso e registre novo ponto.
4. Aumente a massa do carrinho e registre novo ponto.
5. Compare a tabela com os gráficos de x(t), v(t), a(t) e F(t).

PÓS-TESTE
1. Explique a equação F = m·a usando os dados coletados.
2. Por que a aceleração diminui quando a massa total aumenta?
3. Quando o atrito pode impedir o movimento?
4. O gráfico F×a obtido é coerente com a Segunda Lei de Newton? Justifique.
5. Que diferença existe entre força resultante e tensão no fio?
"""
        try:
            with open(caminho, "w", encoding="utf-8-sig") as f:
                f.write(texto)
            self.var_status.set("Roteiro pré/pós-teste exportado.")
            messagebox.showinfo("Roteiro concluído", f"Arquivo salvo em:\n{caminho}")
        except OSError as erro:
            messagebox.showerror("Erro ao exportar", str(erro))

    def fechar(self):
        self.pausar()
        self.root.destroy()


# =============================================================================
# EXECUÇÃO
# =============================================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = LaboratorioSegundaLeiNewton(root)
    root.mainloop()
