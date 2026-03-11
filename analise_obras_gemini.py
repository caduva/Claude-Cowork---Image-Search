"""
analise_obras_gemini.py
========================
Analisa obras de arte usando Gemini Vision e salva os resultados em JSON + Excel.

SETUP (1x):
  1. Pegue sua API key gratuita em: https://aistudio.google.com/app/apikey
  2. Instale as dependências:
       pip install google-generativeai pillow openpyxl

COMO USAR:
  1. Configure as variáveis na seção CONFIG abaixo
  2. Execute: python analise_obras_gemini.py

NOME DOS ARQUIVOS:
  O script extrai artista, nome da obra e ano diretamente do nome do arquivo.
  Formato esperado: "Artista - Nome da Obra - Ano.jpg"
  Exemplo:          "Leonardo da Vinci - Mona Lisa - 1503.jpg"
  (também funciona com apenas nome, ou nome + ano)
"""

import os
import json
import time
import base64
from pathlib import Path
from datetime import datetime

# ============================================================
#  CONFIG — EDITE AQUI
# ============================================================

API_KEY = os.environ.get("API_KEY_GEMINI_FUSE", "SUA_API_KEY_AQUI")

PASTA_IMAGENS = "/sessions/friendly-dreamy-archimedes/mnt/Artworks - atual 10_03_2026"   # Pasta com as imagens das obras

EXTENSOES = [".jpg", ".jpeg", ".png", ".webp", ".gif"]

# gemini-1.5-flash: mais rápido, mais barato (recomendado para uso único)
# gemini-1.5-pro:   mais preciso, pode ter custo se ultrapassar free tier
MODELO = "gemini-1.5-flash"

PROMPT_PADRAO = (
    "Please find interpretations of this artwork on the internet: {identificacao}. "
    "If you can't find the references for the work online, don't try to guess or make "
    "your own interpretation; simply report that you couldn't find them."
)

PAUSA_ENTRE_REQUISICOES = 2  # Segundos entre chamadas (evita rate limit)

# ============================================================
#  SCRIPT — não precisa editar abaixo daqui
# ============================================================

def extrair_identificacao(nome_arquivo):
    """
    Extrai a identificação da obra a partir do nome do arquivo.
    Retorna a string como está no nome (sem extensão), para usar no prompt.
    Exemplo: "Leonardo da Vinci - Mona Lisa - 1503" -> usado direto no prompt
    """
    return Path(nome_arquivo).stem


def configurar_gemini():
    try:
        import google.generativeai as genai
        genai.configure(api_key=API_KEY)
        return genai
    except ImportError:
        print("Biblioteca não instalada. Execute:")
        print("  pip install google-generativeai pillow openpyxl")
        exit(1)


def carregar_imagem_base64(caminho):
    with open(caminho, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def obter_mime_type(extensao):
    mapa = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    return mapa.get(extensao.lower(), "image/jpeg")


def analisar_obra(genai, caminho_imagem, identificacao):
    """Envia imagem + prompt para o Gemini e retorna a análise com formatação original."""
    model = genai.GenerativeModel(MODELO)

    extensao = Path(caminho_imagem).suffix.lower()
    mime_type = obter_mime_type(extensao)
    dados_imagem = carregar_imagem_base64(caminho_imagem)

    prompt = PROMPT_PADRAO.format(identificacao=identificacao)

    response = model.generate_content([
        {"mime_type": mime_type, "data": dados_imagem},
        prompt
    ])

    # Retorna o texto exatamente como o Gemini gerou (preserva indentação e formatação)
    return response.text


def salvar_json(resultados, caminho_saida):
    with open(caminho_saida, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print(f"JSON salvo: {caminho_saida}")


def salvar_excel(resultados, caminho_saida):
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter
    except ImportError:
        print("openpyxl não instalado. Pulando Excel. Execute: pip install openpyxl")
        return

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Análise de Obras"

    # Cabeçalho
    cabecalho = ["#", "Identificação da Obra", "Arquivo", "Análise Gemini", "Status", "Timestamp"]
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)

    for col, titulo in enumerate(cabecalho, 1):
        cell = ws.cell(row=1, column=col, value=titulo)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Dados
    alt_fill = PatternFill(start_color="DEEAF1", end_color="DEEAF1", fill_type="solid")

    for i, item in enumerate(resultados, 1):
        row = i + 1
        fill = alt_fill if i % 2 == 0 else PatternFill()

        # Preserva a formatação original do Gemini na célula Excel
        analise_texto = item.get("analise", item.get("erro", ""))

        valores = [
            i,
            item.get("identificacao", ""),
            item.get("arquivo", ""),
            analise_texto,
            item.get("status", ""),
            item.get("timestamp", ""),
        ]

        for col, valor in enumerate(valores, 1):
            cell = ws.cell(row=row, column=col, value=valor)
            cell.fill = fill
            # wrap_text=True preserva quebras de linha e indentação do Gemini
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    # Larguras das colunas
    larguras = [5, 40, 30, 100, 10, 20]
    for col, largura in enumerate(larguras, 1):
        ws.column_dimensions[get_column_letter(col)].width = largura

    # Altura das linhas de dados
    for row in range(2, len(resultados) + 2):
        ws.row_dimensions[row].height = 120

    wb.save(caminho_saida)
    print(f"Excel salvo: {caminho_saida}")


def main():
    print("=" * 60)
    print("  ANÁLISE DE OBRAS DE ARTE — GEMINI VISION")
    print("=" * 60)

    # Validações iniciais
    if API_KEY == "SUA_API_KEY_AQUI":
        print("\nERRO: Configure sua API key na variável API_KEY no início do script.")
        print("Obtenha gratuitamente em: https://aistudio.google.com/app/apikey")
        exit(1)

    pasta = Path(PASTA_IMAGENS)
    if not pasta.exists():
        print(f"\nERRO: Pasta não encontrada: {PASTA_IMAGENS}")
        print(f"Crie a pasta e coloque as imagens lá, ou ajuste PASTA_IMAGENS.")
        exit(1)

    # Listar imagens
    imagens = [
        f for f in pasta.iterdir()
        if f.is_file() and f.suffix.lower() in EXTENSOES
    ]

    if not imagens:
        print(f"\nERRO: Nenhuma imagem encontrada em: {PASTA_IMAGENS}")
        print(f"Formatos aceitos: {', '.join(EXTENSOES)}")
        exit(1)

    imagens.sort()
    print(f"\n{len(imagens)} imagens encontradas em '{PASTA_IMAGENS}'")
    print(f"Modelo: {MODELO}\n")

    # Configurar Gemini
    genai = configurar_gemini()

    # Processar obras
    resultados = []
    timestamp_inicio = datetime.now().strftime("%Y%m%d_%H%M%S")

    for idx, caminho in enumerate(imagens, 1):
        identificacao = extrair_identificacao(caminho.name)
        print(f"[{idx}/{len(imagens)}] {identificacao}...", end=" ", flush=True)

        try:
            analise = analisar_obra(genai, str(caminho), identificacao)

            resultados.append({
                "id": idx,
                "identificacao": identificacao,
                "arquivo": caminho.name,
                "analise": analise,
                "status": "sucesso",
                "timestamp": datetime.now().isoformat(),
            })
            print("OK")

        except Exception as e:
            erro = str(e)
            resultados.append({
                "id": idx,
                "identificacao": identificacao,
                "arquivo": caminho.name,
                "analise": "",
                "erro": erro,
                "status": "erro",
                "timestamp": datetime.now().isoformat(),
            })
            print(f"ERRO: {erro}")

        # Salva parcialmente a cada 5 obras (segurança contra interrupção)
        if idx % 5 == 0:
            _salvar_parcial(resultados, timestamp_inicio)

        if idx < len(imagens):
            time.sleep(PAUSA_ENTRE_REQUISICOES)

    # Salvar resultados finais
    print("\n" + "=" * 60)
    print("  SALVANDO RESULTADOS")
    print("=" * 60)

    saida_json = f"analise_obras_{timestamp_inicio}.json"
    saida_xlsx = f"analise_obras_{timestamp_inicio}.xlsx"

    salvar_json(resultados, saida_json)
    salvar_excel(resultados, saida_xlsx)

    # Resumo final
    sucessos = sum(1 for r in resultados if r["status"] == "sucesso")
    erros = len(resultados) - sucessos

    print(f"\nRESUMO:")
    print(f"  Total processado : {len(resultados)}")
    print(f"  Sucesso          : {sucessos}")
    print(f"  Erros            : {erros}")
    print(f"\nConcluído!")


def _salvar_parcial(resultados, ts):
    """Salva checkpoint parcial em caso de interrupção."""
    caminho = f"analise_obras_{ts}_parcial.json"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
