# DashAgro — automação de dados via GitHub Actions

Este pacote automatiza a atualização de parte dos dados do DashAgro
(`index.html`), rodando semanalmente na nuvem (grátis) via GitHub Actions,
e publica o resultado como um link público fixo via GitHub Pages.

## O que já está automatizado nesta primeira versão

| Bloco | Fonte | Status |
|---|---|---|
| 1 · Clima | NOAA CPC (ONI) | ✅ Pronto e validado com chamada real — sem chave necessária |
| 4 · Hedge Funds | CFTC (Legacy COT) | ✅ Pronto e validado com chamada real — sem chave necessária |
| 3 · Oferta & Demanda | USDA/FAS PSD | ✅ Pronto e validado com chamada real — precisa da chave `USDA_PSD_API_KEY` (ver passo 4 do Setup) |
| 2 · Condições de lavoura | Conab, USDA/NASS, Bolsa de Cereales | ❌ Não incluído ainda (Conab e Bolsa de Cereales não têm API pública; NASS tem, pode ser adicionado depois) |
| 5 · Contratos & Câmbio | CBOT/ICE, USD/BRL | ❌ Não incluído ainda (preço de futuros geralmente é fonte paga) |

Ou seja: depois de configurado (e com a chave do Bloco 3 cadastrada), **os
Blocos 1, 3 e 4 se mantêm sempre atualizados sozinhos**. Blocos 2 e 5
continuam precisando de atualização manual (mesmo processo de hoje: você
exporta a planilha/CSV e me manda). O Bloco 3 atualiza por enquanto só as
safras fechadas (campo `world`); as colunas "correntes" e os recortes por
país/importador/esmagamento ficam para uma próxima iteração.

## Setup (uma vez só)

### 1. Criar o repositório
1. No GitHub, clique em **New repository**
2. Nome sugerido: `dashagro`
3. Marque como **Public** (necessário pro GitHub Pages gratuito)
4. Crie o repositório vazio (sem README, sem .gitignore)

### 2. Subir os arquivos
Suba todo o conteúdo desta pasta para o repositório, **e renomeie o arquivo
`dashagro_completo.html` para `index.html`** na raiz do repositório
(o GitHub Pages serve automaticamente o `index.html` da raiz como página
principal).

Estrutura final esperada no repositório:
```
seu-repo/
├── index.html                          ← o dashboard (renomeado)
├── requirements.txt
├── .github/
│   └── workflows/
│       └── update.yml
└── scripts/
    ├── inject_utils.py
    ├── fetch_clima.py
    ├── fetch_hedge_funds.py
    ├── fetch_oferta_demanda.py
    └── main.py
```

### 3. Ativar o GitHub Pages
1. No repositório, vá em **Settings → Pages**
2. Em "Source", escolha **Deploy from a branch**
3. Branch: `main`, pasta: `/ (root)`
4. Salve — em alguns minutos o link fica disponível em:
   `https://seu-usuario.github.io/dashagro/`

Esse link **nunca muda** — sempre mostra a versão mais recente do arquivo.

### 4. Chave da API do USDA/PSD (só se for ligar o Bloco 3)
1. Acesse https://apps.fas.usda.gov/opendataweb/home
2. Crie uma conta gratuita e gere uma API key
3. No repositório GitHub: **Settings → Secrets and variables → Actions →
   New repository secret**
4. Nome: `USDA_PSD_API_KEY` · Valor: cole a chave gerada

Sem esse passo, o script do Bloco 3 simplesmente não roda (os outros dois
continuam funcionando normalmente).

### 5. Testar
Em **Actions**, escolha o workflow "Atualizar DashAgro" e clique em **Run
workflow** para rodar manualmente uma vez e conferir se está tudo certo,
antes de esperar a próxima sexta-feira.

## Agendamento

Roda automaticamente toda **sexta-feira às 22h UTC** (~19h em Brasília) —
horário escolhido porque é depois do relatório semanal do CFTC (que sai
toda sexta por volta das 15h30 no horário de Nova York). Para mudar o
horário, edite a linha `cron` em `.github/workflows/update.yml`.

## Nota para quem for validar/ajustar isto (Claude Code)

Os três scripts em `scripts/fetch_*.py` já foram testados com chamadas
reais (via `workflow_dispatch` no GitHub Actions, que tem internet
plena — sandboxes de desenvolvimento costumam bloquear esses domínios):

- **`fetch_clima.py`** — validado. Fonte é um arquivo texto simples e
  estável do NOAA.
- **`fetch_hedge_funds.py`** — validado, incluindo os parâmetros SoQL
  (`$where`/`$order`/`$limit`) contra a API Socrata do CFTC, que
  funcionam normalmente com `requests` puro.
- **`fetch_oferta_demanda.py`** — validado em 2026-08-10. A API legada
  documentada originalmente (`apps.fas.usda.gov/PSDOnlineDataServices`)
  está **descontinuada** — responde 403 "Bad API Key" mesmo com uma
  chave válida. A API ativa é `https://api.fas.usda.gov/api/psd/...`
  com header `X-Api-Key` (não `API_KEY`). O endpoint
  `/psd/commodity/{code}/world/year/{year}` devolve todos os atributos
  de uma vez, identificados por `attributeId` numérico — os nomes vêm
  de `/psd/commodityAttributes`. IDs confirmados: Beginning Stocks=20,
  Production=28, Domestic Consumption=125, Ending Stocks=176. Os
  códigos de commodity (soja=2222000, milho=0440000 — zero à esquerda
  obrigatório, algodao=2631000) foram confirmados contra dados reais.

Todos os scripts usam `scripts/inject_utils.py` para gravar o resultado de
volta no `index.html`, substituindo o `const NOME_DA_VARIAVEL = {...}`
correspondente sem tocar no resto do arquivo. Importante: o arquivo tem
**duas variáveis chamadas `DATA`** (uma no Bloco 4, outra no Bloco 5) — use
o parâmetro `occurrence` (`occurrence=1` para Bloco 4, `occurrence=2` para
Bloco 5) para não confundir uma com a outra.
