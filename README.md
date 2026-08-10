# DashAgro — automação de dados via GitHub Actions

Este pacote automatiza a atualização de parte dos dados do DashAgro
(`index.html`), rodando semanalmente na nuvem (grátis) via GitHub Actions,
e publica o resultado como um link público fixo via GitHub Pages.

## O que já está automatizado nesta primeira versão

| Bloco | Fonte | Status |
|---|---|---|
| 1 · Clima | NOAA CPC (ONI) | ✅ Pronto — sem chave necessária |
| 4 · Hedge Funds | CFTC (Legacy COT) | ✅ Pronto — sem chave necessária |
| 3 · Oferta & Demanda | USDA/FAS PSD Online | ⚠️ Esqueleto — precisa de chave grátis + validação do endpoint (ver `scripts/fetch_oferta_demanda.py`) |
| 2 · Condições de lavoura | Conab, USDA/NASS, Bolsa de Cereales | ❌ Não incluído ainda (Conab e Bolsa de Cereales não têm API pública; NASS tem, pode ser adicionado depois) |
| 5 · Contratos & Câmbio | CBOT/ICE, USD/BRL | ❌ Não incluído ainda (preço de futuros geralmente é fonte paga) |

Ou seja: depois de configurado, **os Blocos 1 e 4 vão se manter sempre
atualizados sozinhos**. O Bloco 3 fica pronto pra ligar assim que alguém
validar o endpoint da API do USDA (o script já está escrito, só precisa de
um teste real com internet de verdade — o Claude Code consegue fazer isso).
Blocos 2 e 5 continuam precisando de atualização manual (mesmo processo de
hoje: você exporta a planilha/CSV e me manda).

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
1. Acesse https://apps.fas.usda.gov/psdonline/
2. Crie uma conta gratuita e gere uma API key (menu "API")
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

Os três scripts em `scripts/fetch_*.py` foram escritos com bases de
conhecimento diferentes de confiança:

- **`fetch_clima.py`** — fonte é um arquivo texto simples e estável do
  NOAA, formato bem conhecido. Confiança alta, mas nunca testado com
  chamada real nesta conversa — validar mesmo assim.
- **`fetch_hedge_funds.py`** — a API (Socrata, CFTC) foi explorada durante
  o desenvolvimento do dashboard original, então a estrutura de campos é
  conhecida (`report_date_as_yyyy_mm_dd`, `noncomm_positions_long_all`,
  `noncomm_positions_short_all`, `market_and_exchange_names`). O que não
  pôde ser validado foi passar parâmetros `$where`/`$order`/`$limit` na
  prática (a ferramenta de fetch do Claude.ai ignorava esses parâmetros —
  ver conversa original). Com `requests` puro isso deve funcionar
  normalmente, mas é o primeiro ponto a testar.
- **`fetch_oferta_demanda.py`** — confiança mais baixa. O endpoint e o
  formato de resposta da API do PSD Online **não foram testados**, foram
  montados a partir de conhecimento geral sobre a API. Tratar como um
  rascunho: rodar, ver o erro real, ajustar contra a documentação oficial
  (https://apps.fas.usda.gov/psdonline/app/index.html#/app/about).

Todos os scripts usam `scripts/inject_utils.py` para gravar o resultado de
volta no `index.html`, substituindo o `const NOME_DA_VARIAVEL = {...}`
correspondente sem tocar no resto do arquivo. Importante: o arquivo tem
**duas variáveis chamadas `DATA`** (uma no Bloco 4, outra no Bloco 5) — use
o parâmetro `occurrence` (`occurrence=1` para Bloco 4, `occurrence=2` para
Bloco 5) para não confundir uma com a outra.
