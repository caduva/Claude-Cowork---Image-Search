# Claude Cowork — Image Search (Fuse)

## Contexto do Projeto

Projeto de extração e curadoria de descrições de obras de arte para o banco de dados de produção do site da Fuse. O Gemini analisa imagens de obras e busca referências na internet (grounding). Os resultados passam por revisão de qualidade antes de subir ao banco.

## Estrutura de Pastas

```
Claude Cowork - Image Search/
├── Output Gemini Description/          # Outputs processados
│   └── Revisado_14_04_2026/            # Dataset revisado e curado (pasta de trabalho atual)
│       ├── batch1.json / .xlsx         # Additional artworks Beta 2 (batch 1) — lotes 1-5 unificados
│       ├── batch1_Obras_Sem_Referencia.json
│       ├── batch2.json / .xlsx         # Additional artworks Beta 2 (batch 2)
│       ├── batch2_Obras_Sem_Referencia.json
│       ├── batch3.json / .xlsx         # Additional artworks Beta 2 (batch 3)
│       ├── batch3_Obras_Sem_Referencia.json
│       ├── beta1.json / .xlsx          # Artworks Beta 1
│       └── beta1_Obras_Sem_Referencia.json
├── banksy/                             # Imagens do Banksy processadas separadamente
├── processar_lote.py                   # Script principal de extração via Gemini Flash
├── processar_banksy.py                 # Script especifico para obras do Banksy
├── melhorar_descricoes.py              # Script de melhoria via Groq (legado)
├── melhorar_heuristica.py              # Script de classificacao por heuristica
├── melhorar_worker.py                  # Worker paralelo Groq (legado)
└── melhorar_descricoes_checkpoint.json # Checkpoint do processamento Groq
```

## Variáveis de Ambiente Necessárias

- `API_KEY_GEMINI_FUSE` — chave da API do Google Gemini (projeto Fuse no GCP)
- `API_KEY_GROQ` — chave da API do Groq (opcional, para scripts de melhoria)

## Modelo Utilizado

- **Gemini Flash** (`gemini-3-flash-preview`) com Google Search Grounding
- Sem grounding = sem custo de tokens de busca

## Limites de Custo (IMPORTANTE)

- O grounding faz ~4 queries por obra (não 1)
- Free tier real: ~375 obras/dia (não 1.500)
- Limite conservador seguro: **300 obras/dia**
- Custo acima do free tier: ~R$0,33/obra
- Reset da cota: meia-noite UTC = 21h Brasília

## Estrutura dos JSONs de Output

Cada registro contém:
- `identificacao` — nome da obra (artista + título)
- `arquivo` — nome do arquivo de imagem
- `analise` — descrição extraída pelo Gemini
- `sucesso_revisado` — `sim` / `parcial` / `nao` (qualidade da referência encontrada)
- `modelo_usado`, `status`, `timestamp`, `fonte_dado`, `fonte_json`

## Regra dos Arquivos de Output

- `batch*.json` — obras com `sucesso_revisado = sim` (dataset principal)
- `batch*_Obras_Sem_Referencia.json` — obras com `parcial` ou `nao`
- **Nunca modificar os arquivos de output sem autorização do usuário** — são parte do dataset de produção

## Estado Atual do Dataset (15/04/2026)

| Arquivo | Obras (sim) | Sem referência |
|---------|-------------|----------------|
| batch1  | 2.095       | 187            |
| batch2  | 750         | 70             |
| batch3  | 685         | 61             |
| beta1   | 2.250       | 418            |

## Pastas de Imagens

```
C:\Users\ctucunduva\fontes fuse\images\
├── Additional artworks for Beta 2 (batch 1)/   # Lotes 1-5
├── Additional artworks for Beta 2 (batch 2)/   # batch2
├── Additional artworks for Beta 2 (batch 3)/   # batch3
└── Artworks Beta 1/                            # beta1
```

## Como Rodar um Novo Lote

1. Atualizar `PASTA_LOTE` e prefixos (`batch3_` etc.) em `processar_lote.py`
2. Definir `LIMITE_DIARIO = 300` para não estourar o free tier
3. Rodar: `python processar_lote.py`
4. O script retoma automaticamente de checkpoint se interrompido

## Repositório Git

- Remote: `https://github.com/caduva/Claude-Cowork---Image-Search.git`
- Branch: `master`
