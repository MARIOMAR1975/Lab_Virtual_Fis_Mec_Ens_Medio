# Instalação detalhada

Os laboratórios precisam de **Python 3.10 ou superior (testado apenas na 3.12)** com **tkinter**, mais três pacotes
(numpy, matplotlib e scipy). Depois de instalados, **funcionam sem internet**.

> Observação: com versões muito novas do Python (por exemplo 3.14), alguns pacotes podem ainda
> não ter instalador pronto. Se `pip install` falhar, use o Python **3.12 ou 3.13**.
> A verificação das bibliotecas e da sintaxe em 25/11/2026 usou Python 3.12.14.

## Windows

1. Baixe o Python em https://www.python.org/downloads/ e, no instalador, marque
   **"Add python.exe to PATH"**. O tkinter já vem incluído.
2. Baixe este repositório (**Code → Download ZIP**) e extraia a pasta.
3. Abra o **Prompt de Comando** dentro da pasta extraída (digite `cmd` na barra de endereços do Explorador).
4. Execute:
   ```bat
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   python verificar_instalacao.py
   python 01_mru_mruv.py
   ```

## Linux (Debian/Ubuntu)

```bash
sudo apt install python3 python3-venv python3-tk
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python verificar_instalacao.py
python 01_mru_mruv.py
```

## macOS

```bash
# Python do python.org já inclui tkinter; com Homebrew: brew install python-tk
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python verificar_instalacao.py
python 01_mru_mruv.py
```

## Executar cada módulo

```bash
python 01_mru_mruv.py
python 02_queda_livre.py
python 03_movimento_parabolico.py
python 04_segunda_lei_newton.py
python 05_conservacao_energia_mecanica.py
python 06_coeficiente_restituicao.py
```

## Problemas comuns

| Mensagem | Causa e solução |
|---|---|
| `ModuleNotFoundError: No module named 'tkinter'` | Linux: `sudo apt install python3-tk`. Windows: reinstale o Python marcando "tcl/tk and IDLE". |
| `ModuleNotFoundError: numpy` (ou matplotlib, scipy) | Ative o ambiente virtual e rode `pip install -r requirements.txt`. |
| `pip` não encontrado | Use `python -m pip install -r requirements.txt`. |
| Janela cortada em tela pequena | Maximize a janela; os módulos adaptam o layout ao tamanho. |
