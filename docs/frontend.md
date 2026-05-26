# Interface Web Protegida

Esta etapa adiciona uma interface web operacional para consumir a API protegida.

## Funcionalidades

- Login operacional usando credenciais do Active Directory.
- Perfis definidos por grupos do AD.
- Armazenamento local da sessao no navegador.
- Painel operacional com saude da API, metricas basicas, inventario AD, prontidao de configuracao e auditoria recente.
- Status do worker, total de execucoes, falhas e ultimos jobs.
- Consulta de usuarios.
- Consulta de grupos.
- Consulta de computadores.
- Geração de relatorios JSON, CSV e PDF.
- Filtros avancados por OU, grupo, sistema operacional, periodo e limite.
- Dry-run guiado de operacoes sensiveis em usuarios e computadores.
- Guia de logs com busca, rolagem e contexto de auditoria.
- Mensagens especificas para token ausente, permissao negada e servico indisponivel.

## Execucao

```bash
docker compose up -d frontend api
```

Frontend:

```text
http://localhost:3000
```

API:

```text
http://localhost:8080
```

## Configuracao Da API

O frontend usa:

```env
VITE_API_BASE_URL=http://localhost:8080
```

No Compose, esse valor vem de:

```env
APP_BASE_URL=http://localhost:8080
```

A API deve permitir a origem do frontend:

```env
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:4173,http://127.0.0.1:4173
```

## Fluxo

1. Informe a URL da API.
2. Informe usuario e senha do Active Directory.
3. A API autentica no AD e atribui perfil pelos grupos mapeados.
4. Revise o painel operacional.
5. Use as abas para consultar, gerar relatorios ou executar dry-runs.

O fluxo manual de bootstrap/token fica reservado para operacao tecnica da API e nao e usado pela interface normal.

Na aba de relatorios, o formato `PDF` abre uma versao imprimivel do relatorio para salvar como PDF pelo navegador.

## Filtros Avancados

As telas de usuarios, grupos, computadores e relatorios aceitam filtros operacionais conforme o tipo de objeto:

- Usuarios: status, busca textual, OU DN, grupo DN, dias de inatividade e limite.
- Grupos: status, busca textual, OU DN e limite.
- Computadores: status, busca textual, OU DN, sistema operacional, dias de inatividade, idade da senha de maquina e limite.
- Logs: busca por usuario, perfil, grupo, acao, alvo, origem ou payload de auditoria.

O campo de busca textual exige pelo menos 2 caracteres quando preenchido.

## Logs

A guia `Logs` consome `/audit/events` e mostra:

- Usuario autenticado do AD.
- Perfil atribuido.
- Grupos usados para autorizacao, quando disponiveis.
- Acao executada.
- Alvo.
- Data/hora.
- Origem da requisicao.

A tabela tem rolagem interna para manter a pagina estavel e aceita limite de linhas.

## Operacoes Sensiveis

A aba de operacoes permite selecionar o modo antes do envio:

- `Simular`: modo padrao, envia `dry_run=true` e nao altera o Active Directory.
- `Executar no AD`: envia `dry_run=false` e executa a alteracao real, desde que o usuario tenha permissao e a API esteja com transporte seguro para escrita.

Qualquer modo exige confirmacao explicita antes do envio. No modo real, a interface mostra alerta adicional e o botao de execucao fica destacado.

Fluxos disponiveis:

- Usuarios: desbloquear, habilitar, desabilitar, forcar troca de senha, resetar senha, alterar expiracao da conta, adicionar a grupo e remover de grupo.
- Computadores: habilitar, desabilitar e atualizar metadados.

Antes da chamada, a interface mostra:

- Tipo do objeto e alvo.
- Acao selecionada e impacto esperado.
- Modo de execucao.
- Justificativa informada.
- Campos adicionais, como senha temporaria, grupo carregado ou metadados.

Depois da operacao, a interface destaca se houve apenas validacao em dry-run ou alteracao real no AD. Quando ha mudanca real, tambem exibe o estado posterior retornado pela API. Senhas temporarias nunca sao exibidas no resultado.

## Painel Operacional

O painel inicial consolida:

- Status da API e uptime.
- Operador autenticado e perfil.
- Totais do ultimo snapshot de inventario do AD.
- Execucoes recentes do worker.
- Indicadores de revisao, como usuarios inativos, grupos sem responsavel e computadores sem metadados.
- Prontidao de configuracao para AD/LDAPS.
- Ultimos eventos de auditoria.

Os totais de inventario usam o arquivo `inventory-snapshot-latest.json`, gerado pelo worker em `REPORT_OUTPUT_DIR` e exposto pela API em:

```text
GET /reports/inventory-snapshot
```

O status do worker usa os arquivos `worker-metrics.json` e `worker-jobs.jsonl`, tambem em `REPORT_OUTPUT_DIR`, expostos pela API em:

```text
GET /reports/worker-status
```

## Cuidados

- O token fica no armazenamento local do navegador.
- Nao use bootstrap token em maquina compartilhada.
- Use `Simular` antes de qualquer acao sensivel.
- Quando `APP_ENV=production`, a guia **Operacoes** remove a opcao `Simular` e mantem apenas execucao real no AD.
- Escrita real deve ser executada apenas com `AD_USE_LDAPS=true`, `AD_TLS_REQUIRE_CERT=true` e autorizacao operacional.
- O teste de conexao AD no painel executa bind de validacao e deve ser usado com credenciais de menor privilegio.

## Estados De Erro

A interface diferencia erros comuns para operadores:

- Token ausente ou expirado.
- Perfil sem permissao para a tela ou acao.
- API indisponivel, incluindo URL incorreta ou CORS.
- Recurso ainda nao gerado, como snapshot de inventario ou historico do worker.
