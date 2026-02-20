# Contrato de Dados Excel (schema_version=1)

Este documento "trava" o contrato atual de importacao dos arquivos Excel.
Qualquer mudanca de aba, nome de coluna, tipo ou semantica exige criar uma
nova versao do contrato (ex.: schema_version=2) e atualizar o backend.

Data da versao: 2026-01-23

## Regras gerais
- Abas: todas as planilhas usam a aba "Sheet1".
- Colunas: nomes sao case-insensitive, mas a grafia deve bater (sem espacos extras).
- Listas em texto usam separador ";". Espacos ao redor sao ignorados.
- Mudancas de nomes/colunas exigem bump de versao.
- Colunas extras nao sao aceitas neste schema_version.

## 1) epis_apr_modelo_validado.xlsx
### Colunas (Sheet1)
- id (int, required, unico no arquivo)
- epi (str, required, unico no arquivo)
- descricao (str, optional)
- normas (str, optional)

### Mapeamento no sistema
- Entidade: EPI
- models.EPI.epi        <- epi
- models.EPI.descricao  <- descricao
- models.EPI.normas     <- normas
- Observacao: o campo "id" eh usado como chave externa no contrato, mas hoje
  nao e persistido no banco (o banco gera o proprio id).

## 2) perigos_apr_modelo_validado.xlsx
### Colunas (Sheet1)
- id (int, required, unico no arquivo)
- perigo (str, required, unico no arquivo)
- consequencias (str, optional; lista com ";")
- salvaguardas (str, optional; lista com ";")

### Mapeamento no sistema
- Entidade: Perigo
- models.Perigo.perigo         <- perigo
- models.Perigo.consequencias  <- consequencias
- models.Perigo.salvaguardas   <- salvaguardas
- Observacao: o campo "id" eh usado como chave externa no contrato, mas hoje
  nao e persistido no banco (o banco gera o proprio id).

## 3) atividades_passos_apr_modelo_validado.xlsx
### Colunas (Sheet1)
- atividade_id (int, required)
- atividade (str, required)
- local (str, optional)
- funcao (str, optional)
- ordem_passo (int, required; sequencial por atividade_id: 1..N)
- descricao_passo (str, required)
- perigos (str, optional; lista com ";")
- riscos (str, optional; lista com ";")
- medidas_controle (str, optional; lista com ";")
- epis (str, optional; lista com ";")
- normas (str, optional; lista com ";")

### Mapeamento no sistema (planejado)
- Entidades: APR + Passo
- Agrupamento: cada atividade_id gera 1 APR; cada linha gera 1 Passo.
- APR.titulo      <- atividade
- APR.descricao   <- "local=<local>; funcao=<funcao>" (se aplicavel)
- APR.risco       <- nao definido no Excel (deve vir de outra fonte ou padrao)
- Passo.ordem            <- ordem_passo
- Passo.descricao        <- descricao_passo
- Passo.perigos          <- perigos
- Passo.riscos           <- riscos
- Passo.medidas_controle <- medidas_controle
- Passo.epis             <- epis
- Passo.normas           <- normas
Observacao: "riscos" e "medidas_controle" sao textos livres, nao entidades
separadas no banco nesta versao.

Observacao: neste contrato, "perigos" e "epis" sao nomes livres (texto),
nao IDs. Se no futuro forem IDs, isso exige nova versao do contrato.

## Mudancas que exigem nova versao
- Renomear/removert/adicionar colunas
- Mudar o separador de listas
- Mudar o significado de qualquer coluna (ex.: "perigos" virar ID)
- Mudar a estrutura de abas
