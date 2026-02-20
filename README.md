# backend-apr

## Centro de ativação

Fluxo do centro de ativação centraliza a entrega completa da APR: o usuário cria um novo rascunho, ajusta os dados mínimos (empresa, obra/local, atividade, responsável, data) e abre a tela de checklist. Cada etapa é normalizada e validada (sem duplicações e sem caracteres `�`), garantindo que o score automático (probabilidade × severidade) seja recalculado antes de qualquer finalização. O estado padrão é `draft`; somente `final` gera o PDF oficial e fica imutável, então o fluxo passa por etapas bem definidas (criação → passos → riscos → matriz → revisão → finalização → PDF), com logs e versão de contrato rastreáveis.

Atualizações nos itens de risco (`PATCH /v1/aprs/{apr_id}/risk-items/{risk_item_id}`) recalculam imediatamente `probability × severity` e só aceitam valores entre 1 e 5; tentativas fora da matriz retornam `risk_score_invalid` com mensagem de rastreabilidade. O mesmo código `risk_score_invalid` também aparece no `POST /v1/aprs/{apr_id}/finalize` sempre que a matriz estiver violada (probabilidade ou severidade iguais a zero ou acima de 5), evitando que o PDF seja gerado com dados inconsistentes.

As normalizações seguem dois pilares: o `text_normalizer.normalize_text` higieniza todos os campos (sem `ï¿½`, sem linhas duplicadas e com espaços consolidados) e o novo módulo `entity_normalizer` cria um lookup contra o catálogo `Perigo`, deduplica nomes de perigo nos passos e força o uso do nome canônico antes de alimentar a matriz de risco. Além dos testes já existentes (`tests/test_no_replacement_char.py`), `tests/test_text_normalizer_contract.py` parametriza vários fluxos de normalização para garantir que o retorno não contenha `�`, séries de três quebras de linha ou espaços duplos.

## Como testar pendências

- **Sem CEP**: envie um payload de ativação falso sem o campo de localização ou com o valor vazio; o centro de ativação deve manter o checklist em “pending” e retornar a mensagem “Checklist ainda não iniciado — revise pendências como sem CEP, sem Stripe e demais dados obrigatórios.”.
- **Sem Stripe**: simule a ausência de cadastro Stripe ou de token de pagamento e verifique que o endpoint continua operando, apenas marcando a pendência no texto retornado (com “sem Stripe” explícito) e sem bloquear o estado `draft`.
- **Outros itens**: limpe qualquer checklist parcial para ver o texto “Pendências detectadas: ...” enumerando apenas os labels pendentes; quando o checklist estiver completo, a mensagem deve ser “Checklist completo: todas as etapas foram concluídas.”.

Execute os testes com `py -m pytest` sempre que mexer em lógica de normalização, checklist ou score para certificar que não há caracteres inválidos nem regressões na API.

## Novo endpoint `/api/seller/activation-status`

- **Payload esperado**:  
  ```json
  {
    "seller_id": "123",
    "checklist": [
      { "label": "Documento enviado", "completed": true },
      { "label": "Termo assinado", "completed": false }
    ]
  }
  ```
  O payload exige que `checklist` seja uma lista com pelo menos um item; cada item normaliza `label` e `completed` antes de processar.
- **Resposta**:
  ```json
  {
    "seller_id": "123",
    "status": "pending",
    "total_items": 2,
    "completed_items": 1,
    "progress_percent": 50,
    "pending_items": ["Termo assinado"],
    "checklist": [...],
    "message": "Pendências detectadas: Termo assinado."
  }
  ```
  A resposta inclui `status` (`ready` quando 100%, `pending` caso contrário), `progress_percent`, a lista de pendências e a mensagem apropriada (Todas as frases acima aparecem em execução real). Os itens continuam normalizados e podem alimentar o fluxo de ativação sem bloquear estados `draft`.

Documente também no `CONTRATO_EXCEL_V1.md` qualquer mudança de schema ou checklist que impacte a carga de dados.
