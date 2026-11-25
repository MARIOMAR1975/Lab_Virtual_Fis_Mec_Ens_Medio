# -*- coding: utf-8 -*-
"""Verifica se o ambiente está pronto para rodar os seis laboratórios.

Uso:  python verificar_instalacao.py

Confere: versão do Python, tkinter, numpy, matplotlib, scipy e se os seis
arquivos da pasta principal têm sintaxe válida. Não abre nenhuma janela.
"""
import importlib
import pathlib
import py_compile
import sys

pasta = pathlib.Path(__file__).resolve().parent
falhas = 0

print(f"Python {sys.version.split()[0]}")
for modulo in ("tkinter", "numpy", "matplotlib", "scipy"):
    try:
        m = importlib.import_module(modulo)
        versao = getattr(m, "__version__", None) or getattr(m, "TkVersion", "ok")
        print(f"  [ok]   {modulo} {versao}")
    except ImportError as erro:
        falhas += 1
        print(f"  [FALTA] {modulo}  ({erro})")
        if modulo == "tkinter":
            print("          No Linux: sudo apt install python3-tk")
        else:
            print("          Instale com: pip install -r requirements.txt")

arquivos = sorted(pasta.glob("0*.py"))
print(f"\nLaboratórios encontrados: {len(arquivos)} (esperado: 6)")
if len(arquivos) != 6:
    falhas += 1
for arq in arquivos:
    try:
        py_compile.compile(str(arq), doraise=True, cfile=str(pathlib.Path(__file__).with_suffix(".tmpc")))
        print(f"  [ok]   {arq.name}")
    except py_compile.PyCompileError as erro:
        falhas += 1
        print(f"  [ERRO] {arq.name}: {erro.msg}")
try:
    pathlib.Path(__file__).with_suffix(".tmpc").unlink()
except OSError:
    pass

print("\nTudo pronto." if falhas == 0 else f"\n{falhas} problema(s) encontrado(s).")
sys.exit(1 if falhas else 0)
