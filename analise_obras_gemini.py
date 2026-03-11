"""
analise_obras_gemini.py
========================
Analisa obras de arte usando Gemini com Google Search Grounding.
O resultado é equivalente ao que você obtém no browser do Gemini:
o modelo busca na internet em tempo real antes de responder.

SETUP (1x — rode no terminal do Windows):
  pip install google-generativeai pillow openpyxl

COMO USAR:
  1. Cole sua API key abaixo (https://aistudio.google.com/app/apikey)
  2. Execute: python analise_obras_gemini.py

NOME DOS ARQUIVOS:
  O script usa o nome do arquivo como identificação da obra no prompt.
  Exemplo: "Adriana Varejão_Açougue song_2000_(1).jpg"
           → prompt enviado com "Adriana Varejão_Açougue song_2000"
"""

import os
import re
import json
import time
import base64
from pathlib import Path
from datetime import datetime

# ============================================================
#  CONFIG — EDITE AQUI
# ============================================================

API_KEY = os.environ.get("API_KEY_GEMINI_FUSE", "SUA_API_KEY_AQUI")

PASTA_IMAGENS = r"C:\Users\ctucunduva\fontes fuse\Artworks - atual 10_03_2026"

EXTENSOES = [".jpg", ".jpeg", ".png", ".webp", ".gif", ".JPG", ".PNG", ".JPEG"]

# gemini-2.0-flash: modelo atual com suporte a Google Search Grounding
# (equivalente ao que você usa no browser do Gemini)
MODELO = "gemini-2.0-flash"

PROMPT_PADRAO = (
    "Please find interpretations of this artwork on the internet: {identificacao}. "
    "If you can't find the references for the work online, don't try to guess or make "
    "your own interpretation; simply report that you couldn't find them."
)

PAUSA_ENTRE_REQUISICOES = 3  # Segundos entre chamadas

# ============================================================
#  SCRIPT
# ============================================================

def extrair_identificacao(nome_arquivo):
    """
    Remove prefixo A_ e sufixos numéricos _(1), _1, _text do nome do arquivo.
    Retorna a identificação limpa para o prompt.
    """
    stem = Path(nome_arquivo).stem
    # Remove prefixo A_ ou A com espaço
    stem = re.sub(r'^A_\s*', '', stem)
    stem = re.sub(r'^A\s+', '', stem)
    # Remove sufixos _text, _(1), _(2), _1, _2 no final
    stem = re.sub(r'[_\s]+text\s*$', '', stem, flags=re.IGNORECASE)
    stem = re.sub(r'[_\s]+[\(\[]?\d+[\)\]]?\s*$', '', stem)
    return stem.strip()


def agrupar_obras(pasta):
    """
    Agrupa imagens por obra (ignora duplicatas _1, _2, _text).
    Retorna lista de (identificacao, caminho_imagem_representativa).
    """
    arquivos = [
        f for f in Path(pasta).iterdir()
        if f.is_file() and f.suffix in EXTENSOES
    ]
    arquivos.sort()

    grupos = {}
    for f in arquivos:
        if 'text' in f.stem.lower() and f.stem.lower().endswith('text'):
            continue  # pula arquivos _text (são fotos do label)
        chave = extrair_identificacao(f.name)
        if chave not in grupos:
            grupos[chave] = f  # usa primeira imagem como representativa

    return list(grupos.items())


def configurar_gemini():
    try:
        import google.generativeai as genai
        genai.configure(api_key=API_KEY)
        return genai
    except ImportError:
        print("Biblioteca nao instalada. Execute:")
        print("  pip install google-generativeai pillow openpyxl")
        input("Pressione Enter para sair...")
        exit(1)


def analisar_obra(genai, caminho_imagem, identificacao):
    """
    Envia imagem + prompt para o Gemini com Google Search Grounding ativado.
    O modelo busca na internet antes de responder — igual ao browser.
    """
    from google.generativeai import types

    model = genai.GenerativeModel(
        model_name=MODELO,
        tools=[types.Tool(google_search=types.GoogleSearch())]  # <-- Search Grounding
    )

    # Carregar imagem
    with open(caminho_imagem, "rb") as f:
        dados_imagem = base64.b64encode(f.read()).decode("utf-8")

    ext = Path(caminho_imagem).suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".webp": "image/webp",
                ".gif": "image/gif"}
    mime_type = mime_map.get(ext, "image/jpeg")

    prompt = PROMPT_PADRAO.format(identificacao=identificacao)

    response = model.generate_content([
        {"mime_type": mime_type, "data": dados_imagem},
        prompt
    ])

    # Retorna texto exatamente como o Gemini gerou (preserva formatação)
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
        print("openpyxl nao instalado. Execute: pip install openpyxl")
        return

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Analise de Obras"

    cabecalho = ["#", "Identificacao da Obra", "Arquivo", "Analise Gemini", "Status", "Timestamp"]
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)

    for col, titulo in enumerate(cabecalho, 1):
        cell = ws.cell(row=1, column=col, value=titulo)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    alt_fill = PatternFill(start_color="DEEAF1", end_color="DEEAF1", fill_type="solid")

    for i, item in enumerate(resultados, 1):
        row = i + 1
        fill = alt_fill if i % 2 == 0 else PatternFill()

        valores = [
            i,
            item.get("identificacao", ""),
            item.get("arquivo", ""),
            item.get("analise", item.get("erro", "")),
            item.get("status", ""),
            item.get("timestamp", ""),
        ]

        for col, valor in enumerate(valores, 1):
            cell = ws.cell(row=row, column=col, value=valor)
            cell.fill = fill
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    larguras = [5, 45, 35, 100, 10, 20]
    for col, largura in enumerate(larguras, 1):
        ws.column_dimensions[get_column_letter(col)].width = largura

    for row in range(2, len(resultados) + 2):
        ws.row_dimensions[row].height = 120

    wb.save(caminho_saida)
    print(f"Excel salvo: {caminho_saida}")


def main():
    print("=" * 60)
    print("  ANALISE DE OBRAS — GEMINI + GOOGLE SEARCH GROUNDING")
    print("=" * 60)

    if API_KEY == "SUA_API_KEY_AQUI":
        print("\nERRO: Configure sua API key no inicio do script.")
        print("Obtenha gratuitamente em: https://aistudio.google.com/app/apikey")
        input("Pressione Enter para sair...")
        exit(1)

    pasta = Path(PASTA_IMAGENS)
    if not pasta.exists():
        print(f"\nERRO: Pasta nao encontrada: {PASTA_IMAGENS}")
        input("Pressione Enter para sair...")
        exit(1)

    obras = agrupar_obras(PASTA_IMAGENS)
    if not obras:
        print(f"\nERRO: Nenhuma imagem encontrada em: {PASTA_IMAGENS}")
        input("Pressione Enter para sair...")
        exit(1)

    print(f"\n{len(obras)} obras unicas encontradas")
    print(f"Modelo: {MODELO} com Google Search Grounding\n")

    genai = configurar_gemini()
    resultados = []
    timestamp_inicio = datetime.now().strftime("%Y%m%d_%H%M%S")
    pasta_script = Path(__file__).parent

    for idx, (identificacao, caminho) in enumerate(obras, 1):
        print(f"[{idx}/{len(obras)}] {identificacao[:70]}...", end=" ", flush=True)

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
            resultados.append({
                "id": idx,
                "identificacao": identificacao,
                "arquivo": caminho.name,
                "analise": "",
                "erro": str(e),
                "status": "erro",
                "timestamp": datetime.now().isoformat(),
            })
            print(f"ERRO: {e}")

        # Checkpoint a cada 5 obras
        if idx % 5 == 0:
            cp = pasta_script / f"analise_obras_{timestamp_inicio}_parcial.json"
            with open(cp, "w", encoding="utf-8") as f:
                json.dump(resultados, f, ensure_ascii=False, indent=2)
            print(f"  >> Checkpoint salvo ({idx} obras)")

        if idx < len(obras):
            time.sleep(PAUSA_ENTRE_REQUISICOES)

    # Salvar resultados finais
    print("\n" + "=" * 60)
    saida_json = pasta_script / f"analise_obras_{timestamp_inicio}.json"
    saida_xlsx = pasta_script / f"analise_obras_{timestamp_inicio}.xlsx"

    salvar_json(resultados, str(saida_json))
    salvar_excel(resultados, str(saida_xlsx))

    sucessos = sum(1 for r in resultados if r["status"] == "sucesso")
    print(f"\nRESUMO: {sucessos}/{len(resultados)} obras processadas com sucesso")
    print(f"Arquivos salvos em: {pasta_script}")
    input("\nPressione Enter para fechar...")


if __name__ == "__main__":
    main()
