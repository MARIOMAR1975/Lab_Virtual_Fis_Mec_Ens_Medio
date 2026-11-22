# -*- coding: utf-8 -*-
"""
LABORATÓRIO VIRTUAL OFFLINE: Coeficiente de Restituição — Tkinter + Matplotlib

Aplicação Python nativa com interface responsiva, cena experimental, gráficos em
tempo real, tabela de dados e exportação, sem navegador ou servidor local.

Autor: Mario Omar Calla Salcedo / Mestrado em Ensino Profissional em Física

Como executar:
    python 06_coeficiente_restituicao.py

Recursos principais:
- Simulação animada de uma bolinha vermelha em queda e quique sobre a mesa.
- Sensor de movimento em suporte universal, régua métrica e vetor velocidade.
- Gráficos em tempo real de h(t), v(t) e energia mecânica relativa.
- Tabela vertical de alturas máximas H0, H1, H2... e estimativa e = sqrt(H_i/H_{i-1}).
- Tabela opcional de impactos, trajetória completa ou energia por pico.
- Estimativa do coeficiente de restituição por alturas e por velocidades.
- Exportação CSV, relatório TXT e roteiro de pré-teste/pós-teste.
- Interface adaptável para manter controles, simulação, gráficos e tabela visíveis.
"""

import csv
import math
import random
import time
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch, Arc
from matplotlib.ticker import AutoMinorLocator


# Paleta visual: alto contraste, leitura confortável e cores distintas por grandeza.
COR_FUNDO = "#0b1220"
COR_PAINEL = "#111827"
COR_PAINEL_2 = "#182235"
COR_SUPERFICIE = "#f8fafc"
COR_TEXTO = "#0f172a"
COR_TEXTO_SUAVE = "#475569"
COR_AZUL = "#2563eb"
COR_CIANO = "#0891b2"
COR_VERDE = "#10b981"
COR_LARANJA = "#f97316"
COR_VERMELHO = "#ef4444"
COR_ROXO = "#8b5cf6"
COR_AMARELO = "#facc15"


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def clamp(valor, minimo, maximo):
    """Limita valor ao intervalo [minimo, maximo]."""
    return max(minimo, min(maximo, valor))


def formato_numero(valor, casas=3):
    """Formata número com vírgula decimal, preservando arredondamento físico."""
    try:
        if not math.isfinite(float(valor)):
            return "—"
        quantizador = Decimal("1").scaleb(-int(casas))
        numero = Decimal(str(float(valor))).quantize(quantizador, rounding=ROUND_HALF_UP)
        return f"{numero:.{int(casas)}f}".replace(".", ",")
    except Exception:
        return str(valor)


def media(valores):
    """Média aritmética ignorando valores não finitos."""
    filtrados = [float(v) for v in valores if isinstance(v, (int, float)) and math.isfinite(v)]
    return sum(filtrados) / len(filtrados) if filtrados else float("nan")


def desvio_padrao_amostral(valores):
    """Desvio padrão amostral, útil para discutir dispersão experimental."""
    filtrados = [float(v) for v in valores if isinstance(v, (int, float)) and math.isfinite(v)]
    if len(filtrados) < 2:
        return float("nan")
    m = sum(filtrados) / len(filtrados)
    return math.sqrt(sum((x - m) ** 2 for x in filtrados) / (len(filtrados) - 1))


def ler_numero(variavel):
    """Converte entradas com vírgula ou ponto decimal para float."""
    texto = str(variavel.get()).strip().replace(" ", "")
    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    else:
        texto = texto.replace(",", ".")
    return float(texto)


# =============================================================================
# CLASSE PRINCIPAL DA APLICAÇÃO
# =============================================================================

class LaboratorioCoeficienteRestituicao:
    def __init__(self, root):
        self.root = root
        self.root.title("Laboratório Virtual Offline — Coeficiente de Restituição | Tkinter + Matplotlib")
        self.configurar_janela()

        # Estado dinâmico da simulação
        self.rodando = False
        self.after_id = None
        self.t = 0.0
        self.y = 0.0          # altura do centro da bolinha em relação à mesa
        self.v = 0.0          # velocidade vertical: positiva para cima
        self.em_repouso = False
        self.ja_quicou = False
        self.dados = []
        self.impactos = []
        self.picos = []

        # Relógio interno da animação.
        # Correção importante: a física agora acompanha o tempo real.
        # Antes, a simulação avançava apenas Δt=0,01 s a cada 30 ms de relógio,
        # o que deixava a queda aproximadamente três vezes mais lenta.
        self._loop_clock = None
        self._acumulador_fisico = 0.0
        self._tempo_grafico_anterior = 0.0
        self.intervalo_frame_ms = 16       # alvo visual próximo de 60 fps
        self.intervalo_graficos_s = 0.08   # gráficos/tabela redesenhados sem travar a bolinha

        # Variáveis físicas e didáticas
        self.var_h0 = tk.StringVar(value="1,20")
        self.var_sensor_h = tk.StringVar(value="1,80")
        self.var_tmax = tk.StringVar(value="6,00")
        self.var_dt = tk.StringVar(value="0,01")
        self.var_ritmo = tk.StringVar(value="1,00")
        self.var_raio = tk.StringVar(value="0,035")
        self.var_g = tk.StringVar(value="9,81")
        self.var_e = tk.StringVar(value="0,82")
        self.var_ruido = tk.StringVar(value="0,000")
        self.var_grafico = tk.StringVar(value="Todos")
        self.var_tipo_tabela = tk.StringVar(value="Alturas máximas")
        self.var_status = tk.StringVar(value="Pronto para iniciar.")
        self.var_descricao_tabela = tk.StringVar(value="Tabela ativa: H0, H1, H2... e coeficiente e por alturas sucessivas.")

        # Leituras em tempo real
        self.var_leitura_t = tk.StringVar(value="0,000 s")
        self.var_leitura_h = tk.StringVar(value="0,000 m")
        self.var_leitura_v = tk.StringVar(value="0,000 m/s")
        self.var_leitura_impactos = tk.StringVar(value="0")
        self.var_analise_eh = tk.StringVar(value="—")
        self.var_analise_ev = tk.StringVar(value="—")
        self.var_analise_picos = tk.StringVar(value="0")
        self.var_analise_perda = tk.StringVar(value="—")

        self.opcoes_tipo_tabela = [
            "Alturas máximas",
            "Impactos",
            "Trajetória completa",
            "Energia por pico",
        ]

        self.configurar_estilo()
        self.criar_interface()
        self.configurar_eventos()
        self.reiniciar_simulacao(limpar_tabela=True)

    def configurar_janela(self):
        """Dimensiona a janela sem esconder a região inferior atrás da barra do sistema."""
        largura_tela = self.root.winfo_screenwidth()
        altura_tela = self.root.winfo_screenheight()
        largura = max(1040, min(1400, largura_tela - 36))
        altura = max(620, min(760, altura_tela - 90))
        x = max(0, (largura_tela - largura) // 2)
        y = max(0, min(20, (altura_tela - altura) // 3))
        self.root.geometry(f"{largura}x{altura}+{x}+{y}")
        self.root.minsize(min(1040, largura), min(620, altura))

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
        estilo.configure("Card.TFrame", background=COR_SUPERFICIE, relief="flat")
        estilo.configure("TLabel", background=COR_PAINEL, foreground="#e5e7eb", font=("Segoe UI", 8))
        estilo.configure("Title.TLabel", background=COR_FUNDO, foreground="#f8fafc", font=("Segoe UI Semibold", 14, "bold"))
        estilo.configure("SubTitle.TLabel", background=COR_FUNDO, foreground="#a5b4fc", font=("Segoe UI", 8))
        estilo.configure("TButton", font=("Segoe UI", 7, "bold"), padding=(5, 3))
        estilo.configure("Accent.TButton", font=("Segoe UI", 7, "bold"), padding=(5, 3), foreground="white", background=COR_AZUL)
        estilo.configure("Success.TButton", font=("Segoe UI", 7, "bold"), padding=(5, 3), foreground="white", background=COR_VERDE)
        estilo.configure("Warning.TButton", font=("Segoe UI", 7, "bold"), padding=(5, 3), foreground="#3b1d05", background=COR_AMARELO)
        estilo.configure("Danger.TButton", font=("Segoe UI", 7, "bold"), padding=(5, 3), foreground="white", background=COR_VERMELHO)
        estilo.map("Success.TButton", background=[("active", "#059669")])
        estilo.map("Warning.TButton", background=[("active", "#eab308")])
        estilo.map("Danger.TButton", background=[("active", "#dc2626")])
        estilo.configure("TEntry", fieldbackground="#020617", foreground="#e5e7eb", insertcolor="#e5e7eb")
        estilo.configure("TCombobox", fieldbackground="#020617", foreground="#e5e7eb")
        estilo.configure("Treeview", font=("Segoe UI", 7), rowheight=20, background="#ffffff", fieldbackground="#ffffff", foreground=COR_TEXTO)
        estilo.configure("Treeview.Heading", font=("Segoe UI", 7, "bold"), background="#cffafe", foreground=COR_TEXTO, padding=(2, 3))
        estilo.map("Treeview", background=[("selected", COR_AZUL)], foreground=[("selected", "#ffffff")])

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

        titulo = ttk.Label(
            cabecalho,
            text="Laboratório Virtual Offline — Coeficiente de Restituição",
            style="Title.TLabel",
        )
        titulo.grid(row=0, column=0, sticky="w")

        subtitulo = ttk.Label(
            cabecalho,
            text="Simulação didática em Python nativo: bolinha, mesa de impacto, sensor, gráficos, tabela e exportação CSV — sem navegador e sem internet.",
            style="SubTitle.TLabel",
        )
        subtitulo.grid(row=1, column=0, sticky="w", pady=(1, 0))

        selo = tk.Label(
            cabecalho,
            text="Tkinter • Matplotlib • Offline",
            bg="#164e63",
            fg="#cffafe",
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

        corpo.columnconfigure(0, minsize=225, weight=0)
        corpo.columnconfigure(1, weight=1)
        corpo.rowconfigure(0, weight=1)

        self.criar_painel_controle(corpo)
        self.criar_area_trabalho(corpo)

    def criar_painel_controle(self, parent):
        painel = tk.Frame(parent, bg=COR_PAINEL, bd=0, highlightthickness=1, highlightbackground="#334155")
        painel.grid(row=0, column=0, sticky="nsw", padx=(0, 5))
        painel.grid_propagate(False)
        painel.configure(width=225)
        painel.columnconfigure(0, weight=1)

        titulo = tk.Label(
            painel,
            text="Painel de comando",
            bg=COR_PAINEL,
            fg="#f8fafc",
            font=("Segoe UI", 10, "bold"),
        )
        titulo.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 2))

        self.criar_grupo_modelo(painel, 1)
        self.criar_grupo_visualizacao(painel, 2)
        self.criar_grupo_botoes(painel, 3)
        self.criar_grupo_presets(painel, 4)
        self.criar_grupo_analise(painel, 5)

    def criar_grupo(self, parent, row, titulo):
        grupo = tk.Frame(parent, bg=COR_PAINEL_2, bd=0, highlightthickness=1, highlightbackground="#334155")
        grupo.grid(row=row, column=0, sticky="ew", padx=5, pady=2)
        for c in range(3):
            grupo.columnconfigure(c, weight=1)

        lbl = tk.Label(
            grupo,
            text=titulo.upper(),
            bg=COR_PAINEL_2,
            fg="#67e8f9",
            font=("Segoe UI", 7, "bold"),
        )
        lbl.grid(row=0, column=0, columnspan=3, sticky="w", padx=5, pady=(4, 1))
        return grupo

    def criar_grupo_modelo(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Modelo físico")
        self.criar_linha_entradas(grupo, 1, "H₀ (m)", self.var_h0, "sensor (m)", self.var_sensor_h)
        self.criar_linha_entradas(grupo, 2, "e simulado", self.var_e, "g (m/s²)", self.var_g)
        self.criar_linha_entradas(grupo, 3, "raio (m)", self.var_raio, "ruído (m)", self.var_ruido)
        self.criar_linha_entradas(grupo, 4, "t máx (s)", self.var_tmax, "Δt (s)", self.var_dt)

    def criar_grupo_visualizacao(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Visualização e coleta")
        self.criar_label_combo(grupo, 1, "Gráficos", self.var_grafico, ["Todos", "h(t)", "v(t)", "Energia"])
        self.criar_label_combo(grupo, 2, "Tabela", self.var_tipo_tabela, self.opcoes_tipo_tabela)
        self.criar_label_combo(grupo, 3, "Ritmo", self.var_ritmo, ["0,25", "0,50", "1,00", "2,00", "4,00"])

        nota = tk.Label(
            grupo,
            text="A tabela principal registra somente as alturas máximas H₀, H₁, H₂...",
            bg=COR_PAINEL_2,
            fg="#e0f2fe",
            font=("Segoe UI", 7),
            wraplength=205,
            justify="left",
        )
        nota.grid(row=4, column=0, columnspan=3, sticky="ew", padx=5, pady=(2, 5))

    def criar_grupo_botoes(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Controle da simulação")

        self.btn_iniciar = ttk.Button(grupo, text="Iniciar", style="Success.TButton", command=self.iniciar)
        self.btn_pausar = ttk.Button(grupo, text="Pausar", style="Warning.TButton", command=self.pausar)
        self.btn_passo = ttk.Button(grupo, text="Passo", command=self.passo)
        self.btn_reset = ttk.Button(grupo, text="Resetar", style="Danger.TButton", command=lambda: self.reiniciar_simulacao(limpar_tabela=True))
        self.btn_csv = ttk.Button(grupo, text="CSV", command=self.exportar_csv)
        self.btn_relatorio = ttk.Button(grupo, text="Relatório", command=self.exportar_relatorio)
        self.btn_prepos = ttk.Button(grupo, text="Pré/Pós", command=self.exportar_roteiro_pre_pos_teste)
        self.btn_limpar = ttk.Button(grupo, text="Limpar", command=self.limpar_dados)

        botoes = [
            (self.btn_iniciar, 1, 0), (self.btn_pausar, 1, 1), (self.btn_passo, 1, 2),
            (self.btn_reset, 2, 0), (self.btn_limpar, 2, 1), (self.btn_csv, 2, 2),
            (self.btn_relatorio, 3, 0), (self.btn_prepos, 3, 1),
        ]
        for botao, r, c in botoes:
            botao.grid(row=r, column=c, sticky="ew", padx=2, pady=2)

        lbl_status = tk.Label(
            grupo,
            textvariable=self.var_status,
            bg=COR_PAINEL_2,
            fg="#67e8f9",
            font=("Segoe UI", 7),
            wraplength=205,
            justify="left",
        )
        lbl_status.grid(row=4, column=0, columnspan=3, sticky="ew", padx=5, pady=(1, 4))

    def criar_grupo_presets(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Situações prontas")
        b1 = ttk.Button(grupo, text="Borracha", command=lambda: self.aplicar_preset(1))
        b2 = ttk.Button(grupo, text="Tênis", command=lambda: self.aplicar_preset(2))
        b3 = ttk.Button(grupo, text="Quase elástico", command=lambda: self.aplicar_preset(3))
        b1.grid(row=1, column=0, sticky="ew", padx=2, pady=2)
        b2.grid(row=1, column=1, sticky="ew", padx=2, pady=2)
        b3.grid(row=1, column=2, sticky="ew", padx=2, pady=2)

    def criar_grupo_analise(self, parent, row):
        grupo = self.criar_grupo(parent, row, "Leituras e análise")
        itens = [
            ("Tempo", self.var_leitura_t),
            ("Altura", self.var_leitura_h),
            ("Velocidade", self.var_leitura_v),
            ("Impactos", self.var_leitura_impactos),
            ("e alturas", self.var_analise_eh),
            ("e velocidades", self.var_analise_ev),
            ("Picos", self.var_analise_picos),
            ("Perda 1º", self.var_analise_perda),
        ]
        for i, (rotulo, var) in enumerate(itens):
            r = 1 + i // 2
            c = (i % 2) * 2
            caixa = tk.Frame(grupo, bg="#ecfeff", bd=0, highlightthickness=1, highlightbackground="#a5f3fc")
            caixa.grid(row=r, column=c, columnspan=2, sticky="ew", padx=3, pady=2)
            caixa.columnconfigure(0, weight=1)
            tk.Label(caixa, text=rotulo, bg="#ecfeff", fg=COR_TEXTO_SUAVE, font=("Segoe UI", 6)).grid(row=0, column=0, sticky="w", padx=4)
            tk.Label(caixa, textvariable=var, bg="#ecfeff", fg=COR_TEXTO, font=("Segoe UI", 8, "bold")).grid(row=1, column=0, sticky="w", padx=4)

    def criar_label_combo(self, parent, row, texto, variavel, opcoes):
        lbl = tk.Label(parent, text=texto, bg=COR_PAINEL_2, fg="#e0f2fe", font=("Segoe UI", 7))
        lbl.grid(row=row, column=0, sticky="w", padx=5, pady=(1, 0))
        combo = ttk.Combobox(parent, textvariable=variavel, values=opcoes, state="readonly", font=("Segoe UI", 7), width=9)
        combo.grid(row=row, column=1, columnspan=2, sticky="ew", padx=5, pady=(1, 0))
        combo.bind("<<ComboboxSelected>>", lambda event: self.configuracao_alterada())
        return combo

    def criar_linha_entradas(self, parent, row, texto1, var1, texto2, var2):
        frame = tk.Frame(parent, bg=COR_PAINEL_2)
        frame.grid(row=row, column=0, columnspan=3, sticky="ew", padx=5, pady=1)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        f1 = tk.Frame(frame, bg=COR_PAINEL_2)
        f2 = tk.Frame(frame, bg=COR_PAINEL_2)
        f1.grid(row=0, column=0, sticky="ew", padx=(0, 3))
        f2.grid(row=0, column=1, sticky="ew", padx=(3, 0))
        f1.columnconfigure(0, weight=1)
        f2.columnconfigure(0, weight=1)

        tk.Label(f1, text=texto1, bg=COR_PAINEL_2, fg="#e0f2fe", font=("Segoe UI", 7)).grid(row=0, column=0, sticky="w")
        e1 = ttk.Entry(f1, textvariable=var1, font=("Segoe UI", 7), width=6)
        e1.grid(row=1, column=0, sticky="ew")

        tk.Label(f2, text=texto2, bg=COR_PAINEL_2, fg="#e0f2fe", font=("Segoe UI", 7)).grid(row=0, column=0, sticky="w")
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
        area.columnconfigure(1, weight=0, minsize=225)
        area.rowconfigure(0, weight=1)

        visual = tk.Frame(area, bg=COR_FUNDO)
        visual.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        visual.columnconfigure(0, weight=1)
        visual.rowconfigure(0, weight=42, minsize=225)
        visual.rowconfigure(1, weight=58, minsize=285)

        self.criar_cena(visual)
        self.criar_graficos(visual, row=1, column=0)
        self.criar_tabela_e_leituras(area)

    def criar_cena(self, parent):
        card = tk.Frame(parent, bg=COR_SUPERFICIE, bd=0, highlightthickness=1, highlightbackground="#cbd5e1")
        card.grid(row=0, column=0, sticky="nsew", pady=(0, 4))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=1)

        self.fig_cena = Figure(figsize=(8, 3.4), dpi=100, facecolor=COR_SUPERFICIE)
        self.ax_cena = self.fig_cena.add_subplot(111)
        self.canvas_cena = FigureCanvasTkAgg(self.fig_cena, master=card)
        self.canvas_cena.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=4)

    def criar_graficos(self, parent, row=0, column=0):
        card = tk.Frame(parent, bg=COR_SUPERFICIE, bd=0, highlightthickness=1, highlightbackground="#cbd5e1")
        card.grid(row=row, column=column, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=0)
        card.rowconfigure(1, weight=1)

        topo = tk.Frame(card, bg=COR_SUPERFICIE)
        topo.grid(row=0, column=0, sticky="ew", padx=6, pady=(3, 0))
        topo.columnconfigure(0, weight=1)
        tk.Label(topo, text="Gráficos em tempo real", bg=COR_SUPERFICIE, fg=COR_TEXTO, font=("Segoe UI Semibold", 9, "bold")).grid(row=0, column=0, sticky="w")
        self.lbl_nota_grafico = tk.Label(topo, text="Mostrando h(t), v(t) e energia.", bg=COR_SUPERFICIE, fg=COR_TEXTO_SUAVE, font=("Segoe UI", 7))
        self.lbl_nota_grafico.grid(row=0, column=1, sticky="e")

        self.fig_graficos = Figure(figsize=(8.4, 3.5), dpi=100, facecolor=COR_SUPERFICIE)
        self.canvas_graficos = FigureCanvasTkAgg(self.fig_graficos, master=card)
        self.canvas_graficos.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=5, pady=(2, 5))

    def criar_tabela_e_leituras(self, parent):
        card = tk.Frame(parent, bg=COR_SUPERFICIE, bd=0, highlightthickness=1, highlightbackground="#cbd5e1", width=225)
        card.grid(row=0, column=1, sticky="nsew")
        card.grid_propagate(False)
        card.columnconfigure(0, weight=1)
        card.rowconfigure(2, weight=1)

        topo = tk.Frame(card, bg=COR_SUPERFICIE)
        topo.grid(row=0, column=0, sticky="ew", padx=8, pady=(7, 4))
        topo.columnconfigure(0, weight=1)
        tk.Label(topo, text="Tabela experimental", bg=COR_SUPERFICIE, fg=COR_TEXTO, font=("Segoe UI Semibold", 10, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(topo, text="dados", bg=COR_SUPERFICIE, fg=COR_CIANO, font=("Segoe UI", 8, "bold")).grid(row=0, column=1, sticky="e")

        painel_tabela = tk.Frame(card, bg="#ecfeff", bd=0, highlightthickness=1, highlightbackground="#a5f3fc")
        painel_tabela.grid(row=1, column=0, sticky="ew", padx=7, pady=(0, 6))
        painel_tabela.columnconfigure(1, weight=1)
        tk.Label(painel_tabela, text="Dados", bg="#ecfeff", fg=COR_TEXTO, font=("Segoe UI", 8, "bold")).grid(row=0, column=0, sticky="w", padx=8, pady=(7, 3))
        combo_tipo = ttk.Combobox(painel_tabela, textvariable=self.var_tipo_tabela, values=self.opcoes_tipo_tabela, state="readonly", width=17, font=("Segoe UI", 8))
        combo_tipo.grid(row=0, column=1, sticky="ew", padx=8, pady=(7, 3))
        combo_tipo.bind("<<ComboboxSelected>>", lambda event: self.aplicar_configuracao_tabela())
        tk.Label(
            painel_tabela,
            textvariable=self.var_descricao_tabela,
            bg="#ecfeff",
            fg=COR_TEXTO_SUAVE,
            font=("Segoe UI", 8),
            justify="left",
            wraplength=205,
        ).grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(2, 7))

        frame_tabela = tk.Frame(card, bg=COR_SUPERFICIE)
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
    # TABELA
    # -------------------------------------------------------------------------
    def obter_configuracao_colunas(self):
        tipo = self.var_tipo_tabela.get()
        if tipo == "Impactos":
            return [
                ("n", "I", 30),
                ("t", "t", 55),
                ("vb", "v₋", 56),
                ("va", "v₊", 56),
                ("e", "eᵥ", 48),
            ]
        if tipo == "Trajetória completa":
            return [
                ("n", "#", 30),
                ("t", "t", 50),
                ("h", "h", 58),
                ("v", "v", 58),
                ("a", "a", 58),
            ]
        if tipo == "Energia por pico":
            return [
                ("n", "H", 30),
                ("t", "t", 55),
                ("h", "H", 58),
                ("ep", "Eₚ", 58),
                ("perda", "%", 45),
            ]
        return [
            ("n", "H", 30),
            ("t", "t máx", 58),
            ("h", "Hₘₐₓ", 66),
            ("e", "eᵢ", 55),
        ]

    def aplicar_configuracao_tabela(self):
        if not hasattr(self, "tabela"):
            return
        colunas = self.obter_configuracao_colunas()
        ids = [c[0] for c in colunas]
        self.tabela.configure(columns=ids)
        for chave, titulo, largura in colunas:
            self.tabela.heading(chave, text=titulo)
            self.tabela.column(chave, width=largura, anchor="center", stretch=False)

        tipo = self.var_tipo_tabela.get()
        descricoes = {
            "Alturas máximas": "Tabela ativa: H0, H1, H2... e coeficiente e por alturas sucessivas.",
            "Impactos": "Tabela ativa: velocidade antes/depois do impacto e e = |v₊/v₋|.",
            "Trajetória completa": "Tabela ativa: dados completos de t, h, v e a. Use para análise temporal.",
            "Energia por pico": "Tabela ativa: energia potencial relativa nos picos e perda acumulada.",
        }
        self.var_descricao_tabela.set(descricoes.get(tipo, descricoes["Alturas máximas"]))
        self.atualizar_tabela()

    def atualizar_tabela(self):
        if not hasattr(self, "tabela"):
            return
        for item in self.tabela.get_children():
            self.tabela.delete(item)

        tipo = self.var_tipo_tabela.get()
        if tipo == "Impactos":
            for i, im in enumerate(self.impactos, start=1):
                self.tabela.insert("", "end", tags=("par" if i % 2 == 0 else "impar",), values=(
                    f"I{i}",
                    formato_numero(im["t"], 3),
                    formato_numero(im["v_antes"], 3),
                    formato_numero(im["v_depois"], 3),
                    formato_numero(im["e_v"], 4),
                ))
            return

        if tipo == "Trajetória completa":
            # Mostra amostra compacta para manter a tela responsiva.
            max_linhas = 220
            passo = max(1, len(self.dados) // max_linhas)
            for i, d in enumerate(self.dados[::passo], start=1):
                self.tabela.insert("", "end", tags=("par" if i % 2 == 0 else "impar",), values=(
                    i,
                    formato_numero(d["t"], 3),
                    formato_numero(d["h"], 3),
                    formato_numero(d["v"], 3),
                    formato_numero(d["a"], 2),
                ))
            return

        if tipo == "Energia por pico":
            h0 = self.picos[0]["h"] if self.picos else float("nan")
            for i, pk in enumerate(self.picos):
                perda = 100.0 * (1.0 - pk["h"] / h0) if h0 > 1e-12 else float("nan")
                ep = self.parametros()["g"] * pk["h"]
                self.tabela.insert("", "end", tags=("par" if i % 2 == 0 else "impar",), values=(
                    f"H{i}",
                    formato_numero(pk["t"], 3),
                    formato_numero(pk["h"], 4),
                    formato_numero(ep, 3),
                    formato_numero(perda, 1),
                ))
            return

        for i, pk in enumerate(self.picos):
            if i == 0:
                e_altura = float("nan")
            else:
                h_ant = self.picos[i - 1]["h"]
                e_altura = math.sqrt(pk["h"] / h_ant) if h_ant > 1e-12 else float("nan")
            self.tabela.insert("", "end", tags=("par" if i % 2 == 0 else "impar",), values=(
                f"H{i}",
                formato_numero(pk["t"], 3),
                formato_numero(pk["h"], 4),
                formato_numero(e_altura, 4),
            ))

    # -------------------------------------------------------------------------
    # EVENTOS E VALIDAÇÃO
    # -------------------------------------------------------------------------
    def configurar_eventos(self):
        self.root.protocol("WM_DELETE_WINDOW", self.fechar)

    def configuracao_alterada(self):
        if not self.validar_parametros(mostrar_erro=False):
            self.var_status.set("Revise os parâmetros: há um valor inválido ou fora do intervalo permitido.")
            return
        if not self.rodando:
            self.reiniciar_simulacao(limpar_tabela=True)
        else:
            self.atualizar_tudo()

    def parametros(self):
        """Lê parâmetros da interface, aplicando limites seguros."""
        h0 = ler_numero(self.var_h0)
        raio = ler_numero(self.var_raio)
        sensor_h = ler_numero(self.var_sensor_h)
        return {
            "h0": h0,
            "sensor_h": sensor_h,
            "tmax": ler_numero(self.var_tmax),
            "dt": ler_numero(self.var_dt),
            "ritmo": clamp(ler_numero(self.var_ritmo), 0.25, 4.0),
            "raio": raio,
            "g": ler_numero(self.var_g),
            "e": ler_numero(self.var_e),
            "ruido": ler_numero(self.var_ruido),
        }

    def validar_parametros(self, mostrar_erro=True):
        try:
            p = self.parametros()
        except Exception:
            if mostrar_erro:
                messagebox.showerror("Erro nos parâmetros", "Verifique se todos os campos numéricos foram preenchidos corretamente.")
            return False

        mensagens = []
        if p["h0"] <= 0:
            mensagens.append("A altura inicial H₀ deve ser maior que zero.")
        if p["raio"] <= 0:
            mensagens.append("O raio da bolinha deve ser maior que zero.")
        if p["tmax"] <= 0:
            mensagens.append("O tempo máximo deve ser maior que zero.")
        if p["dt"] <= 0:
            mensagens.append("O passo Δt deve ser maior que zero.")
        if p["dt"] > 0.05:
            mensagens.append("O passo Δt deve ser menor ou igual a 0,05 s.")
        if p["dt"] > p["tmax"]:
            mensagens.append("O passo Δt não deve ser maior que o tempo máximo.")
        if p["g"] <= 0:
            mensagens.append("A gravidade g deve ser maior que zero.")
        if not (0 <= p["e"] <= 1):
            mensagens.append("O coeficiente de restituição deve estar entre 0 e 1.")
        if p["sensor_h"] <= p["h0"] + 2 * p["raio"]:
            mensagens.append("A altura do sensor deve ficar acima da bolinha na posição inicial.")
        if p["ruido"] < 0:
            mensagens.append("O ruído do sensor não pode ser negativo.")

        if mensagens:
            if mostrar_erro:
                messagebox.showerror("Erro nos parâmetros", "\n".join(mensagens))
            return False
        return True

    # -------------------------------------------------------------------------
    # CONTROLE DA SIMULAÇÃO
    # -------------------------------------------------------------------------
    def iniciar(self):
        if not self.validar_parametros(mostrar_erro=True):
            return
        p = self.parametros()
        if self.t >= p["tmax"] or self.em_repouso:
            self.reiniciar_simulacao(limpar_tabela=True)

        # Evita criar dois loops se o botão for pressionado repetidamente.
        if self.rodando:
            return

        self.rodando = True
        agora = time.perf_counter()
        self._loop_clock = agora
        self._acumulador_fisico = 0.0
        self._tempo_grafico_anterior = agora
        self.var_status.set("Simulação em andamento em tempo real. Use Ritmo = 1 para movimento físico real.")
        self.loop()

    def pausar(self):
        self.rodando = False
        self._loop_clock = None
        self._acumulador_fisico = 0.0
        self.var_status.set("Simulação pausada.")
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None

    def passo(self):
        if not self.validar_parametros(mostrar_erro=True):
            return
        self.rodando = False
        p = self.parametros()
        self.passo_fisico(p["dt"])
        self.atualizar_tudo()
        self.var_status.set("Avanço manual de um passo Δt realizado.")

    def reiniciar_simulacao(self, limpar_tabela=True):
        self.pausar()
        if not self.validar_parametros(mostrar_erro=False):
            return
        p = self.parametros()
        self.t = 0.0
        self.y = p["h0"] + p["raio"]
        self.v = 0.0
        self.em_repouso = False
        self.ja_quicou = False
        self._loop_clock = None
        self._acumulador_fisico = 0.0
        self._tempo_grafico_anterior = time.perf_counter()
        if limpar_tabela:
            self.dados = []
            self.impactos = []
            self.picos = [{"t": 0.0, "h": p["h0"], "tipo": "altura inicial"}]
        self.adicionar_ponto("início")
        self.var_status.set("Pronto para iniciar.")
        self.atualizar_tudo()

    def limpar_dados(self):
        self.dados = []
        self.impactos = []
        p = self.parametros()
        self.picos = [{"t": self.t, "h": max(0.0, self.y - p["raio"]), "tipo": "estado atual"}]
        self.adicionar_ponto("limpeza")
        self.atualizar_tudo()
        self.var_status.set("Tabela e dados experimentais foram limpos.")

    def aplicar_preset(self, codigo):
        if codigo == 1:
            # Material com perda significativa de energia.
            self.var_h0.set(1.20)
            self.var_sensor_h.set(1.80)
            self.var_e.set(0.62)
            self.var_tmax.set(5.00)
            self.var_dt.set(0.01)
            self.var_ruido.set(0.002)
            nome = "Preset: borracha/impacto com maior dissipação."
        elif codigo == 2:
            # Bola comum com restituição intermediária.
            self.var_h0.set(1.20)
            self.var_sensor_h.set(1.80)
            self.var_e.set(0.82)
            self.var_tmax.set(6.00)
            self.var_dt.set(0.01)
            self.var_ruido.set(0.001)
            nome = "Preset: bola de tênis, restituição intermediária."
        else:
            # Colisão quase elástica.
            self.var_h0.set(1.20)
            self.var_sensor_h.set(1.80)
            self.var_e.set(0.95)
            self.var_tmax.set(8.00)
            self.var_dt.set(0.01)
            self.var_ruido.set(0.000)
            nome = "Preset: colisão quase elástica."
        self.reiniciar_simulacao(limpar_tabela=True)
        self.var_status.set(nome)

    def loop(self):
        if not self.rodando:
            return
        try:
            p = self.parametros()
            agora = time.perf_counter()

            if self._loop_clock is None:
                self._loop_clock = agora

            # Tempo real decorrido desde o último quadro.
            # O limite evita saltos muito grandes se o sistema operacional atrasar a janela.
            dt_real = clamp(agora - self._loop_clock, 0.0, 0.10)
            self._loop_clock = agora

            dt_base = p["dt"]
            ritmo = p["ritmo"]

            # Ritmo = 1,0 agora significa aproximadamente 1 segundo de simulação
            # para 1 segundo real. Ritmos maiores aceleram; menores deixam em câmera lenta.
            self._acumulador_fisico += dt_real * ritmo

            max_subpassos = 120
            subpassos = 0

            while (
                self.rodando
                and not self.em_repouso
                and self.t < p["tmax"]
                and self._acumulador_fisico >= dt_base
                and subpassos < max_subpassos
            ):
                self.passo_fisico(dt_base)
                self._acumulador_fisico -= dt_base
                subpassos += 1

            # Se houver atraso extremo, descarta o excesso acumulado para preservar a estabilidade visual.
            if subpassos >= max_subpassos:
                self._acumulador_fisico = 0.0

            # A cena da bolinha é atualizada em todos os quadros.
            self.atualizar_leituras()
            self.atualizar_cena()

            # Gráficos e tabela são mais pesados; por isso são atualizados com menor frequência.
            # Isso deixa o movimento da bolinha mais fluido e fisicamente mais realista.
            if agora - self._tempo_grafico_anterior >= self.intervalo_graficos_s:
                self.atualizar_tabela()
                self.atualizar_graficos()
                self._tempo_grafico_anterior = agora

            if self.t >= p["tmax"] or self.em_repouso:
                self.rodando = False
                self.atualizar_tudo()
                self.var_status.set("Simulação finalizada. Analise a tabela de picos e compare e por alturas e por velocidades.")
                return

            self.after_id = self.root.after(self.intervalo_frame_ms, self.loop)
        except Exception as erro:
            self.rodando = False
            messagebox.showerror("Erro durante a simulação", str(erro))

    # -------------------------------------------------------------------------
    # MOTOR FÍSICO
    # -------------------------------------------------------------------------
    def passo_fisico(self, dt):
        p = self.parametros()
        g = p["g"]
        raio = p["raio"]
        tmax = p["tmax"]
        dt = min(float(dt), max(0.0, tmax - self.t))
        if dt <= 0:
            self.rodando = False
            return

        if self.em_repouso:
            self.t += dt
            self.y = raio
            self.v = 0.0
            self.adicionar_ponto("repouso")
            return

        t_inicio = self.t
        y_ant = self.y
        v_ant = self.v
        evento = ""

        y_prox = self.y + self.v * dt - 0.5 * g * dt * dt
        v_prox = self.v - g * dt

        # Impacto: o centro da bolinha não pode ficar abaixo do raio.
        if y_prox < raio:
            A = 0.5 * g
            B = -self.v
            C = raio - self.y
            tau = dt
            discriminante = B * B - 4 * A * C
            if discriminante >= 0:
                raiz = math.sqrt(discriminante)
                candidatos = [(-B - raiz) / (2 * A), (-B + raiz) / (2 * A)]
                candidatos = [z for z in candidatos if 0 <= z <= dt]
                if candidatos:
                    tau = min(candidatos)

            v_impacto = self.v - g * tau
            v_depois = -p["e"] * v_impacto
            e_v = abs(v_depois / v_impacto) if abs(v_impacto) > 1e-12 else float("nan")
            self.impactos.append({
                "t": t_inicio + tau,
                "v_antes": v_impacto,
                "v_depois": v_depois,
                "e_v": e_v,
            })
            self.ja_quicou = True
            evento = "impacto"

            resto = dt - tau
            y_prox = raio + v_depois * resto - 0.5 * g * resto * resto
            v_prox = v_depois - g * resto

            # Evita microquiques numéricos quando a energia se torna muito pequena.
            h_quique_prevista = (v_depois ** 2) / (2 * g) if g > 0 else 0.0
            if h_quique_prevista < 0.001 or p["e"] <= 0.0:
                y_prox = raio
                v_prox = 0.0
                self.em_repouso = True

            if y_prox < raio:
                y_prox = raio
                v_prox = 0.0
                self.em_repouso = True

        # Detecção de pico: depois do quique, v passa de positiva para negativa.
        if self.ja_quicou and v_ant > 0 and v_prox <= 0:
            tau_pico = clamp(v_ant / g, 0.0, dt)
            y_pico = y_ant + v_ant * tau_pico - 0.5 * g * tau_pico * tau_pico
            h_pico = max(0.0, y_pico - raio)
            t_pico = t_inicio + tau_pico
            if h_pico > 0.001 and (not self.picos or abs(t_pico - self.picos[-1]["t"]) > 1e-6):
                self.picos.append({"t": t_pico, "h": h_pico, "tipo": "pico de quique"})
                evento = evento + "+pico" if evento else "pico"

        self.y = y_prox
        self.v = v_prox
        self.t += dt
        self.adicionar_ponto(evento)
        if "pico" in evento or "impacto" in evento:
            self.atualizar_tabela()

    def adicionar_ponto(self, evento=""):
        p = self.parametros()
        h_real = max(0.0, self.y - p["raio"])
        ruido = random.uniform(-p["ruido"], p["ruido"]) if p["ruido"] > 0 else 0.0
        h_medida = max(0.0, h_real + ruido)
        distancia_sensor = max(0.0, p["sensor_h"] - (self.y + p["raio"]))
        a = 0.0 if self.em_repouso else -p["g"]
        ec = 0.5 * self.v * self.v
        ep = p["g"] * h_real
        em = ec + ep
        self.dados.append({
            "t": self.t,
            "h": h_medida,
            "h_real": h_real,
            "v": self.v,
            "a": a,
            "d_sensor": distancia_sensor,
            "ec": ec,
            "ep": ep,
            "em": em,
            "evento": evento,
        })
        # Limite de segurança para não deixar a interface pesada em tempos longos.
        if len(self.dados) > 6000:
            self.dados = self.dados[-6000:]

    # -------------------------------------------------------------------------
    # ATUALIZAÇÕES VISUAIS
    # -------------------------------------------------------------------------
    def atualizar_tudo(self):
        self.atualizar_leituras()
        self.atualizar_tabela()
        self.atualizar_cena()
        self.atualizar_graficos()

    def atualizar_leituras(self):
        p = self.parametros()
        d = self.dados[-1] if self.dados else {"h": 0.0, "v": 0.0}
        self.var_leitura_t.set(f"{formato_numero(self.t, 3)} s")
        self.var_leitura_h.set(f"{formato_numero(d['h'], 3)} m")
        self.var_leitura_v.set(f"{formato_numero(self.v, 3)} m/s")
        self.var_leitura_impactos.set(str(len(self.impactos)))

        e_alturas = self.estimar_e_por_alturas()
        e_vels = self.estimar_e_por_velocidades()
        eh = media(e_alturas)
        ev = media(e_vels)
        sd_h = desvio_padrao_amostral(e_alturas)
        sd_v = desvio_padrao_amostral(e_vels)
        self.var_analise_eh.set(formato_numero(eh, 4) if math.isfinite(eh) else "—")
        self.var_analise_ev.set(formato_numero(ev, 4) if math.isfinite(ev) else "—")
        if math.isfinite(sd_h) and len(e_alturas) >= 2:
            self.var_analise_eh.set(f"{formato_numero(eh, 4)} ± {formato_numero(sd_h, 4)}")
        if math.isfinite(sd_v) and len(e_vels) >= 2:
            self.var_analise_ev.set(f"{formato_numero(ev, 4)} ± {formato_numero(sd_v, 4)}")
        self.var_analise_picos.set(str(max(0, len(self.picos) - 1)))

        if len(self.picos) >= 2 and self.picos[0]["h"] > 1e-12:
            perda = 100.0 * (1.0 - self.picos[1]["h"] / self.picos[0]["h"])
            self.var_analise_perda.set(f"{formato_numero(perda, 2)} %")
        else:
            self.var_analise_perda.set("—")

    def estimar_e_por_alturas(self):
        valores = []
        for i in range(1, len(self.picos)):
            h_ant = self.picos[i - 1]["h"]
            h_atual = self.picos[i]["h"]
            if h_ant > 1e-12 and h_atual >= 0:
                valores.append(math.sqrt(h_atual / h_ant))
        return valores

    def estimar_e_por_velocidades(self):
        return [im["e_v"] for im in self.impactos if math.isfinite(im.get("e_v", float("nan")))]

    def atualizar_cena(self):
        p = self.parametros()
        ax = self.ax_cena
        ax.clear()
        sensor_h = p["sensor_h"]
        h0 = p["h0"]
        raio_fisico = p["raio"]
        ymax = max(sensor_h + 0.45, h0 + 0.45, 1.0)

        ax.set_xlim(0, 10)
        ax.set_ylim(-0.35, ymax)
        ax.set_facecolor("#ecfeff")
        ax.axis("off")

        # Fundo didático.
        ax.add_patch(Rectangle((0, -0.35), 10, ymax + 0.35, facecolor="#ecfeff", edgecolor="none", zorder=0))
        ax.add_patch(Rectangle((0, -0.35), 10, 0.23, facecolor="#d1fae5", edgecolor="none", zorder=1))

        # Mesa de impacto.
        mesa_y = 0.0
        ax.add_patch(FancyBboxPatch((0.7, mesa_y - 0.12), 8.6, 0.12, boxstyle="round,pad=0.02,rounding_size=0.05",
                                    facecolor=COR_LARANJA, edgecolor="#9a3412", linewidth=1.4, zorder=2))
        ax.add_patch(Rectangle((1.0, -0.35), 0.25, 0.25, facecolor="#9a3412", edgecolor="#7c2d12", zorder=1))
        ax.add_patch(Rectangle((8.75, -0.35), 0.25, 0.25, facecolor="#9a3412", edgecolor="#7c2d12", zorder=1))
        ax.text(4.35, -0.22, "mesa de impacto", fontsize=8, color="#7c2d12", weight="bold")

        # Suporte universal.
        pole_x = 1.35
        rod_y = min(ymax - 0.12, sensor_h + 0.08)
        ball_x = 5.45
        ax.plot([pole_x, pole_x], [-0.12, ymax - 0.08], color="#334155", linewidth=4, zorder=3)
        ax.plot([pole_x - 0.65, pole_x + 0.85], [-0.28, -0.28], color="#334155", linewidth=5, zorder=3)
        ax.plot([pole_x, ball_x + 0.95], [rod_y, rod_y], color="#334155", linewidth=3.5, zorder=3)
        ax.add_patch(Rectangle((pole_x - 0.15, rod_y - 0.07), 0.30, 0.14, facecolor="#374151", edgecolor="#111827", zorder=4))
        ax.text(0.55, 0.08, "suporte\nuniversal", fontsize=7, color="#111827", ha="left", va="bottom")

        # Sensor.
        sensor_w = 1.05
        sensor_h_box = 0.17 * ymax
        sensor_h_box = clamp(sensor_h_box, 0.12, 0.28)
        sensor_y = sensor_h
        ax.add_patch(FancyBboxPatch((ball_x - sensor_w / 2, sensor_y), sensor_w, sensor_h_box,
                                    boxstyle="round,pad=0.03,rounding_size=0.07",
                                    facecolor=COR_ROXO, edgecolor="#6d28d9", linewidth=1.5, zorder=5))
        ax.text(ball_x + 0.72, sensor_y + sensor_h_box * 0.52, "Sensor de\nmovimento", fontsize=7, color="#6d28d9", weight="bold", va="center")
        ax.plot([ball_x, ball_x], [sensor_y, sensor_y - 0.10], color="#6d28d9", linewidth=2, zorder=5)

        # Régua métrica.
        ruler_x = 8.55
        ax.plot([ruler_x, ruler_x], [0, sensor_h], color=COR_AZUL, linewidth=2, zorder=4)
        for i in range(11):
            yy = sensor_h * i / 10
            tick_len = 0.28 if i % 5 == 0 else 0.16
            ax.plot([ruler_x, ruler_x + tick_len], [yy, yy], color=COR_AZUL, linewidth=1.2, zorder=4)
            if i % 2 == 0:
                ax.text(ruler_x + 0.35, yy, f"{sensor_h * i / 10:.2f} m", fontsize=7, color="#1e3a8a", va="center")

        # Bola e feixe do sensor.
        h_real = max(0.0, self.y - raio_fisico)
        y_centro = max(raio_fisico, self.y)
        raio_desenho = clamp(raio_fisico * 2.8, 0.10, 0.20)
        ax.plot([ball_x, ball_x], [sensor_y, y_centro + raio_desenho], color=COR_VERDE, linewidth=1.5, linestyle=(0, (4, 3)), alpha=0.8, zorder=3)
        for k in range(4):
            arc_h = 0.18 + 0.12 * k
            ax.add_patch(Arc((ball_x, sensor_y), width=0.45 + 0.25 * k, height=arc_h, theta1=200, theta2=340,
                             color=COR_ROXO, linewidth=1.2, alpha=0.34, zorder=4))

        bola = Circle((ball_x, y_centro), raio_desenho, facecolor=COR_VERMELHO, edgecolor="#991b1b", linewidth=1.5, zorder=8)
        ax.add_patch(bola)
        brilho = Circle((ball_x - raio_desenho * 0.35, y_centro + raio_desenho * 0.35), raio_desenho * 0.28,
                        facecolor="#fee2e2", edgecolor="none", alpha=0.85, zorder=9)
        ax.add_patch(brilho)
        ax.text(ball_x + 0.32, y_centro, "bolinha\nvermelha", fontsize=7, color="#1f2937", weight="bold", va="center")

        # Vetor velocidade.
        if abs(self.v) > 0.03:
            seta = clamp(abs(self.v) * 0.045, 0.08, 0.45)
            dy = seta if self.v > 0 else -seta
            cor = COR_AZUL if self.v > 0 else COR_VERMELHO
            ax.annotate("", xy=(ball_x - 0.55, y_centro + dy), xytext=(ball_x - 0.55, y_centro),
                        arrowprops=dict(arrowstyle="-|>", color=cor, lw=2.2), zorder=10)
            ax.text(ball_x - 0.78, y_centro + dy, "v", fontsize=8, color=cor, weight="bold", va="center")

        # Leituras dentro da cena.
        caixa = FancyBboxPatch((0.70, ymax - 0.32), 3.05, 0.24, boxstyle="round,pad=0.03,rounding_size=0.06",
                               facecolor="#fef9c3", edgecolor=COR_AMARELO, zorder=10)
        ax.add_patch(caixa)
        ax.text(0.84, ymax - 0.20,
                f"h = {h_real:.3f} m   v = {self.v:.3f} m/s   impactos = {len(self.impactos)}",
                fontsize=7, color="#0f172a", va="center", zorder=11)

        self.fig_cena.subplots_adjust(left=0.015, right=0.985, top=0.98, bottom=0.04)
        self.canvas_cena.draw_idle()

    def atualizar_graficos(self):
        self.fig_graficos.clear()
        p = self.parametros()
        grafico = self.var_grafico.get()
        dados = self.dados if self.dados else [{"t": 0, "h": p["h0"], "h_real": p["h0"], "v": 0, "em": p["g"] * p["h0"]}]
        t = np.array([d["t"] for d in dados], dtype=float)
        h = np.array([d["h"] for d in dados], dtype=float)
        v = np.array([d["v"] for d in dados], dtype=float)
        em = np.array([d["em"] for d in dados], dtype=float)
        em0 = p["g"] * max(p["h0"], 1e-12)
        em_rel = em / em0

        if grafico == "Todos":
            axes = np.atleast_1d(self.fig_graficos.subplots(1, 3, sharex=True))
            self.lbl_nota_grafico.configure(text="Visão conjunta com o eixo do tempo sempre visível.")
            self.plotar_serie(axes[0], t, h, "Altura h(t)", "h (m)", COR_VERMELHO)
            self.plotar_serie(axes[1], t, v, "Velocidade v(t)", "v (m/s)", COR_AZUL)
            self.plotar_serie(axes[2], t, em_rel, "Energia E/E₀", "E/E₀", COR_VERDE)
            for ax in axes:
                ax.set_xlabel("tempo t (s)", fontsize=7.5, labelpad=3)
                self.marcar_eventos_no_grafico(ax, p["tmax"])
            self.fig_graficos.subplots_adjust(left=0.065, right=0.985, top=0.86, bottom=0.24, wspace=0.40)
        else:
            ax = self.fig_graficos.add_subplot(111)
            if grafico == "h(t)":
                self.lbl_nota_grafico.configure(text="Mostrando h(t) com picos e impactos.")
                self.plotar_serie(ax, t, h, "Altura da bolinha em função do tempo", "h (m)", COR_VERMELHO)
                self.marcar_picos(ax)
            elif grafico == "v(t)":
                self.lbl_nota_grafico.configure(text="Mostrando v(t), antes e depois dos impactos.")
                self.plotar_serie(ax, t, v, "Velocidade vertical em função do tempo", "v (m/s)", COR_AZUL)
                ax.axhline(0, color="#64748b", linewidth=0.8)
            else:
                self.lbl_nota_grafico.configure(text="Mostrando energia mecânica relativa E/E₀.")
                self.plotar_serie(ax, t, em_rel, "Energia mecânica relativa em função do tempo", "E/E₀", COR_VERDE)
            ax.set_xlabel("tempo t (s)", fontsize=8, labelpad=4)
            self.marcar_eventos_no_grafico(ax, p["tmax"])
            self.fig_graficos.subplots_adjust(left=0.10, right=0.985, top=0.86, bottom=0.22)
        self.canvas_graficos.draw_idle()

    def plotar_serie(self, ax, x, y, titulo, ylabel, cor):
        ax.plot(x, y, color=cor, linewidth=2.0, solid_capstyle="round")
        if len(x) > 1:
            ax.fill_between(x, y, 0.0, color=cor, alpha=0.08)
        if len(x) > 0:
            ax.scatter([x[-1]], [y[-1]], s=24, color=cor, edgecolors="white", linewidths=0.8, zorder=6)
        ax.set_title(titulo, fontsize=8.5, weight="bold", color=COR_TEXTO, pad=5)
        ax.set_ylabel(ylabel, fontsize=8)
        ax.grid(True, which="major", linestyle="-", linewidth=0.55, color="#cbd5e1", alpha=0.75)
        ax.grid(True, which="minor", linestyle=":", linewidth=0.4, color="#cbd5e1", alpha=0.45)
        ax.xaxis.set_minor_locator(AutoMinorLocator())
        ax.yaxis.set_minor_locator(AutoMinorLocator())
        ax.tick_params(axis="both", labelsize=7)
        ax.set_facecolor("#ffffff")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#94a3b8")
        ax.spines["bottom"].set_color("#94a3b8")
        if len(x) > 0:
            ax.set_xlim(0, max(self.parametros()["tmax"], float(np.nanmax(x)), 1.0))
        if len(y) > 0 and np.isfinite(y).any():
            ymin = float(np.nanmin(y))
            ymax = float(np.nanmax(y))
            if abs(ymax - ymin) < 1e-9:
                margem = 0.1 if abs(ymax) < 1 else abs(ymax) * 0.1
                ymin -= margem
                ymax += margem
            else:
                margem = 0.12 * (ymax - ymin)
                ymin -= margem
                ymax += margem
            ax.set_ylim(ymin, ymax)

    def marcar_eventos_no_grafico(self, ax, tmax):
        total = len(self.impactos)
        for i, im in enumerate(self.impactos, start=1):
            ax.axvline(im["t"], color=COR_LARANJA, linestyle="--", linewidth=0.8, alpha=0.38)
            if i <= 6 or i == total:
                ylim = ax.get_ylim()
                ax.text(im["t"], ylim[1], f"I{i}", fontsize=6, color="#9a3412", ha="center", va="top")
        if ax.get_ylabel() == "h (m)":
            self.marcar_picos(ax)

    def marcar_picos(self, ax):
        if len(self.picos) <= 1:
            return
        tempos = [pk["t"] for pk in self.picos[1:]]
        alturas = [pk["h"] for pk in self.picos[1:]]
        ax.scatter(tempos, alturas, s=26, color=COR_ROXO, edgecolors="white", linewidths=0.7, zorder=5)
        total = len(self.picos) - 1
        for i, pk in enumerate(self.picos[1:], start=1):
            if i <= 6 or i == total:
                ax.text(pk["t"], pk["h"], f"H{i}", fontsize=7, color="#6d28d9", ha="left", va="bottom")

    # -------------------------------------------------------------------------
    # EXPORTAÇÃO E MATERIAL DIDÁTICO
    # -------------------------------------------------------------------------
    def exportar_csv(self):
        if not self.picos and not self.dados:
            messagebox.showwarning("Sem dados", "Não há dados para exportar.")
            return
        nome = f"dados_coeficiente_restituicao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        caminho = filedialog.asksaveasfilename(
            title="Salvar dados CSV",
            defaultextension=".csv",
            initialfile=nome,
            filetypes=[("CSV", "*.csv"), ("Todos os arquivos", "*.*")],
        )
        if not caminho:
            return
        try:
            with open(caminho, "w", encoding="utf-8-sig", newline="") as arq:
                writer = csv.writer(arq, delimiter=";")
                writer.writerow(["LABORATÓRIO VIRTUAL OFFLINE - COEFICIENTE DE RESTITUIÇÃO"])
                writer.writerow(["data_hora", datetime.now().strftime("%d/%m/%Y %H:%M:%S")])
                p = self.parametros()
                writer.writerow(["H0_m", p["h0"]])
                writer.writerow(["sensor_m", p["sensor_h"]])
                writer.writerow(["g_m_s2", p["g"]])
                writer.writerow(["e_simulado", p["e"]])
                writer.writerow([])

                writer.writerow(["PICOS"])
                writer.writerow(["indice", "tempo_maximo_s", "altura_maxima_m", "e_por_alturas"])
                for i, pk in enumerate(self.picos):
                    e_alt = ""
                    if i > 0 and self.picos[i - 1]["h"] > 1e-12:
                        e_alt = math.sqrt(pk["h"] / self.picos[i - 1]["h"])
                    writer.writerow([f"H{i}", f"{pk['t']:.6f}", f"{pk['h']:.6f}", f"{e_alt:.6f}" if e_alt != "" else ""])

                writer.writerow([])
                writer.writerow(["IMPACTOS"])
                writer.writerow(["indice", "tempo_s", "v_antes_m_s", "v_depois_m_s", "e_por_velocidade"])
                for i, im in enumerate(self.impactos, start=1):
                    writer.writerow([f"I{i}", f"{im['t']:.6f}", f"{im['v_antes']:.6f}", f"{im['v_depois']:.6f}", f"{im['e_v']:.6f}"])

                writer.writerow([])
                writer.writerow(["TRAJETORIA"])
                writer.writerow(["tempo_s", "altura_medida_m", "altura_real_m", "velocidade_m_s", "aceleracao_m_s2", "energia_cinetica_rel", "energia_potencial_rel", "energia_mecanica_rel", "evento"])
                em0 = p["g"] * max(p["h0"], 1e-12)
                for d in self.dados:
                    writer.writerow([
                        f"{d['t']:.6f}",
                        f"{d['h']:.6f}",
                        f"{d['h_real']:.6f}",
                        f"{d['v']:.6f}",
                        f"{d['a']:.6f}",
                        f"{d['ec'] / em0:.6f}",
                        f"{d['ep'] / em0:.6f}",
                        f"{d['em'] / em0:.6f}",
                        d["evento"],
                    ])

                writer.writerow([])
                writer.writerow(["ANALISE"])
                writer.writerow(["e_medio_alturas", media(self.estimar_e_por_alturas())])
                writer.writerow(["e_medio_velocidades", media(self.estimar_e_por_velocidades())])
                writer.writerow(["numero_impactos", len(self.impactos)])
                writer.writerow(["numero_picos_quique", max(0, len(self.picos) - 1)])
            messagebox.showinfo("Exportação concluída", f"Arquivo salvo em:\n{caminho}")
        except Exception as erro:
            messagebox.showerror("Erro ao exportar", str(erro))

    def exportar_relatorio(self):
        nome = f"relatorio_coeficiente_restituicao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        caminho = filedialog.asksaveasfilename(
            title="Salvar relatório TXT",
            defaultextension=".txt",
            initialfile=nome,
            filetypes=[("Texto", "*.txt"), ("Todos os arquivos", "*.*")],
        )
        if not caminho:
            return
        p = self.parametros()
        e_alturas = self.estimar_e_por_alturas()
        e_vels = self.estimar_e_por_velocidades()
        texto = []
        texto.append("RELATÓRIO AUTOMÁTICO - COEFICIENTE DE RESTITUIÇÃO")
        texto.append("=" * 68)
        texto.append(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        texto.append("")
        texto.append("1. OBJETIVO")
        texto.append("Determinar o coeficiente de restituição de uma bolinha a partir das alturas máximas sucessivas e das velocidades antes/depois dos impactos.")
        texto.append("")
        texto.append("2. PARÂMETROS")
        texto.append(f"Altura inicial H0 = {p['h0']:.4f} m")
        texto.append(f"Coeficiente simulado e = {p['e']:.4f}")
        texto.append(f"Gravidade g = {p['g']:.4f} m/s²")
        texto.append(f"Raio da bolinha = {p['raio']:.4f} m")
        texto.append(f"Ruído do sensor = {p['ruido']:.4f} m")
        texto.append("")
        texto.append("3. FUNDAMENTAÇÃO")
        texto.append("Para picos sucessivos de altura H_{i-1} e H_i, considera-se:")
        texto.append("    e_i = sqrt(H_i / H_{i-1})")
        texto.append("Também pode ser estimado pela razão entre os módulos das velocidades imediatamente após e antes do impacto:")
        texto.append("    e_i = |v_depois / v_antes|")
        texto.append("")
        texto.append("4. RESULTADOS")
        texto.append(f"Número de impactos detectados: {len(self.impactos)}")
        texto.append(f"Número de picos de quique detectados: {max(0, len(self.picos) - 1)}")
        texto.append(f"e médio por alturas = {media(e_alturas):.6f}" if e_alturas else "e médio por alturas = —")
        texto.append(f"e médio por velocidades = {media(e_vels):.6f}" if e_vels else "e médio por velocidades = —")
        if len(self.picos) >= 2:
            perda = 100.0 * (1.0 - self.picos[1]["h"] / self.picos[0]["h"])
            texto.append(f"Energia dissipada no primeiro impacto ≈ {perda:.2f} %")
        texto.append("")
        texto.append("5. TABELA DE ALTURAS MÁXIMAS")
        texto.append("H; tempo máximo (s); altura máxima (m); e_i")
        for i, pk in enumerate(self.picos):
            e_alt = "—"
            if i > 0 and self.picos[i - 1]["h"] > 1e-12:
                e_alt = f"{math.sqrt(pk['h'] / self.picos[i - 1]['h']):.6f}"
            texto.append(f"H{i}; {pk['t']:.6f}; {pk['h']:.6f}; {e_alt}")
        texto.append("")
        texto.append("6. INTERPRETAÇÃO DIDÁTICA")
        texto.append("Quanto menor o coeficiente de restituição, maior a perda de energia mecânica a cada impacto. Para e = 1, o choque é idealmente elástico; para e = 0, a bolinha não retorna após o impacto.")
        try:
            with open(caminho, "w", encoding="utf-8") as arq:
                arq.write("\n".join(texto))
            messagebox.showinfo("Relatório salvo", f"Arquivo salvo em:\n{caminho}")
        except Exception as erro:
            messagebox.showerror("Erro ao salvar relatório", str(erro))

    def exportar_roteiro_pre_pos_teste(self):
        nome = f"roteiro_pre_pos_teste_restituicao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        caminho = filedialog.asksaveasfilename(
            title="Salvar roteiro de pré-teste/pós-teste",
            defaultextension=".txt",
            initialfile=nome,
            filetypes=[("Texto", "*.txt"), ("Todos os arquivos", "*.*")],
        )
        if not caminho:
            return
        texto = """ROTEIRO DE PRÉ-TESTE E PÓS-TESTE — COEFICIENTE DE RESTITUIÇÃO

Público-alvo: Ensino Médio
Tema: colisões verticais, energia mecânica e coeficiente de restituição

PRÉ-TESTE
1. O que acontece com a energia mecânica da bolinha quando ela bate na mesa?
2. Uma bolinha que retorna a uma altura menor perdeu energia? Explique.
3. O coeficiente de restituição pode ser maior que 1 em uma colisão comum? Justifique.
4. Se H1 é a altura após o primeiro quique e H0 é a altura inicial, como poderíamos estimar e?
5. Qual gráfico você espera para a altura da bolinha em função do tempo?

ATIVIDADE COM O SIMULADOR
1. Escolha H0 = 1,20 m e e = 0,82.
2. Inicie a simulação e registre H0, H1, H2 e H3.
3. Calcule e = sqrt(H_i/H_{i-1}) para dois intervalos sucessivos.
4. Compare o valor calculado com o valor simulado no painel.
5. Repita para e = 0,62 e e = 0,95.

PÓS-TESTE
1. Como o coeficiente de restituição afeta a altura dos quiques sucessivos?
2. Por que a bolinha não alcança novamente a altura inicial quando e < 1?
3. Qual relação matemática liga alturas sucessivas e coeficiente de restituição?
4. O que representa a energia dissipada no primeiro impacto?
5. Como o sensor e a tabela ajudam a transformar observação visual em dado experimental?
"""
        try:
            with open(caminho, "w", encoding="utf-8") as arq:
                arq.write(texto)
            messagebox.showinfo("Roteiro salvo", f"Arquivo salvo em:\n{caminho}")
        except Exception as erro:
            messagebox.showerror("Erro ao salvar roteiro", str(erro))

    # -------------------------------------------------------------------------
    # FECHAMENTO
    # -------------------------------------------------------------------------
    def fechar(self):
        self.pausar()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = LaboratorioCoeficienteRestituicao(root)
    root.mainloop()


if __name__ == "__main__":
    main()

