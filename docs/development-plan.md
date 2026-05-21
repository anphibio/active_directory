# Plano De Desenvolvimento

## Etapa 1: Fundacao Do Projeto

Status: concluida.

Entregas:

- Estrutura inicial do repositorio.
- Docker Compose.
- `.env.example`.
- Documentacao inicial.
- Padrao inicial de logs.
- Health check basico.

## Etapa 2: Configuracao E Conectividade AD

Status: concluida.

Entregas planejadas:

- Validacao obrigatoria das variaveis de ambiente.
- Teste de conectividade LDAP/LDAPS.
- Bind seguro com conta de servico.
- Health check de conectividade AD.
- Tratamento de erro sem exposicao de credenciais.

## Etapa 3: Modelo De Seguranca

Status: concluida.

Entregas planejadas:

- Perfis `viewer`, `operator`, `admin` e `auditor`.
- Controle de acesso por funcionalidade.
- Auditoria de operacoes.
- Correlation ID.
- Mascaramento de dados sensiveis.

## Etapa 4: Consultas De Usuarios

Status: concluida.

Entregas:

- Buscar usuario por `sAMAccountName`.
- Listar usuarios por status.
- Listar usuarios ativos.
- Listar usuarios desabilitados.
- Listar usuarios bloqueados.
- Listar usuarios inativos.
- Listar usuarios que nunca fizeram logon.
- Listar usuarios com senha nunca expira.
- Filtrar por grupo, texto livre, periodo de inatividade e limite.
- Registrar auditoria da consulta.

## Etapa 5: Consultas De Grupos

Status: concluida.

Entregas:

- Buscar grupo por nome, `sAMAccountName`, CN ou DN.
- Listar grupos.
- Filtrar grupos vazios.
- Filtrar grupos com membros.
- Filtrar grupos sem descricao.
- Filtrar grupos sem responsavel.
- Listar membros de um grupo.
- Listar grupos de um usuario.
- Registrar auditoria da consulta.

## Etapa 6: Consultas De Computadores

Status: concluida.

Entregas:

- Buscar computador por CN, nome, DNS hostname, `sAMAccountName` ou DN.
- Listar computadores por status.
- Listar computadores ativos.
- Listar computadores desabilitados.
- Listar computadores inativos.
- Listar computadores que nunca fizeram logon.
- Listar servidores.
- Listar workstations.
- Listar controladores de dominio.
- Listar computadores com senha de maquina antiga.
- Listar computadores sem metadados obrigatorios.
- Filtrar por OU, sistema operacional, texto livre, periodo de inatividade e limite.
- Registrar auditoria da consulta.

## Etapa 7: Relatorios

Status: concluida.

Entregas:

- Relatorios de usuarios em JSON e CSV.
- Relatorios de grupos em JSON e CSV.
- Relatorios de computadores em JSON e CSV.
- Historico em `reports/report-history.jsonl`.
- Gravacao de arquivos CSV em `REPORT_OUTPUT_DIR`.
- Auditoria da geracao de relatorios.

## Etapa 8: Operacoes Sensíveis Em Usuarios

Status: concluida.

Entregas:

- Habilitar usuario.
- Desabilitar usuario.
- Desbloquear usuario.
- Forcar troca de senha no proximo logon.
- Resetar senha com bloqueio de seguranca para execucao real sem LDAPS.
- Exigir `confirm=true`.
- Usar `dry_run=true` por padrao.
- Exigir justificativa.
- Registrar auditoria da operacao.
- Retornar estado anterior e posterior quando houver alteracao real.

## Etapa 9: Operacoes Controladas Em Grupos

Status: concluida.

Entregas:

- Adicionar usuario a grupo.
- Remover usuario de grupo.
- Proteger grupos sensiveis.
- Exigir `confirm=true`.
- Usar `dry_run=true` por padrao.
- Exigir justificativa.
- Exigir confirmacao extra em grupo protegido.
- Registrar auditoria da operacao.

## Etapa 10: Operacoes Controladas Em Computadores

Status: concluida.

Entregas:

- Habilitar computador.
- Desabilitar computador.
- Atualizar metadados permitidos.
- Exigir `confirm=true`.
- Usar `dry_run=true` por padrao.
- Exigir justificativa.
- Registrar auditoria da operacao.

## Etapa 11: Interface Web Protegida

Status: concluida.

Entregas:

- Login ou entrada de token.
- Consumo dos endpoints protegidos.
- Telas de usuarios, grupos, computadores e relatorios.
- Fluxos de dry-run e confirmacao para operacoes sensiveis.

## Etapa 12: Auditoria Persistente

Status: concluida.

Entregas:

- Persistir auditoria em banco.
- Consultar historico pela API.
- Filtrar por operador, alvo, acao e periodo.
- Criar tabela automaticamente na inicializacao da API.
- Manter fallback para logs quando banco estiver indisponivel.

## Etapa 13: Jobs Agendados No Worker

Status: concluida.

Entregas:

- Jobs de relatorio recorrente.
- Limpeza de relatorios antigos.
- Registro de execucao de jobs.
- Scheduler simples por intervalo.
- Heartbeat estruturado.
- Historico em `reports/worker-jobs.jsonl`.
- Snapshot operacional de inventario como ponto de extensao.

## Etapa 14: Migracoes Formais De Banco

Status: concluida.

Entregas:

- Versionar schema.
- Aplicar migracoes no startup ou via comando operacional.
- Criar tabela `schema_migrations`.
- Migrar auditoria para arquivo SQL versionado.
- Adicionar comando `python -m app.migrate`.

## Etapa 15: Testes De Integracao E Checklist De Producao

Status: concluida.

Entregas:

- Testes de integracao contra AD de laboratorio.
- Checklist de LDAPS.
- Checklist de permissao da conta de servico.
- Checklist de backup e restore.
- Scripts de validacao de `.env`, LDAP e API.
- Guia de testes de leitura e escrita em laboratorio.

## Etapa 16: CI E Deploy

Status: concluida.

Entregas:

- Pipeline de testes.
- Build de imagens.
- Publicacao versionada.
- Deploy controlado por ambiente.
- Script local equivalente ao CI.
- Compose de producao com imagens versionadas.
- Guia de deploy e rollback.

## Etapa 17: Observabilidade E Testes End-To-End

Status: concluida.

Entregas:

- Metricas de API, jobs e LDAP.
- Testes end-to-end em AD de laboratorio.
- Endpoint `/metrics` em formato Prometheus.
- Métricas do worker em `reports/worker-metrics.json`.
- Script `scripts/e2e-lab.sh`.
- Documentacao de observabilidade.

## Etapa 18: Hardening De Producao

Status: concluida.

Entregas:

- Corrigir LDAPS e exigir TLS.
- Configurar proxy reverso.
- Adicionar dashboard Prometheus/Grafana.
- Definir politica de retencao de auditoria.
- Bloquear escrita real sem LDAPS.
- Validar prontidao de producao.
- Exemplo de proxy Nginx com `/metrics` restrito.
- Documentacao de hardening.

## Etapa 19: Retencao E Dashboards

Status: concluida.

Entregas:

- Retencao automatica em `audit_events`.
- Dashboard Prometheus/Grafana.
- Alertas de falha LDAP, erro HTTP e jobs com falha.
- Job `audit_retention` no worker.
- Configuracao inicial de Prometheus.
- Regras iniciais de alerta.
- Dashboard Grafana inicial.

## Etapa 20: Stack De Monitoramento

Status: concluida.

Entregas:

- Adicionar Prometheus ao Compose.
- Adicionar Grafana ao Compose.
- Provisionar dashboard automaticamente.
- Exportar metricas do worker em formato Prometheus.
- Provisionar datasource Prometheus no Grafana.
- Adicionar perfil `monitoring`.
- Adicionar `compose.monitoring.yaml` para subir monitoramento sem profile.

## Etapa 21: Metricas Prometheus Do Worker E Alertmanager

Status: concluida.

Entregas:

- Expor metricas do worker via HTTP.
- Coletar worker no Prometheus.
- Adicionar Alertmanager.
- Adicionar alertas de API indisponivel, worker indisponivel e falha em job.
- Atualizar dashboard Grafana com metricas do worker.
- Documentar validacao da stack de monitoramento.

## Etapa 22: Integracoes Corporativas De Alertas

Status: concluida.

Entregas:

- Integrar Alertmanager com e-mail, Teams, Slack ou webhook corporativo.
- Definir severidades por ambiente.
- Documentar escala e responsaveis por tipo de alerta.
- Criar templates de mensagem para incidentes AD.

## Etapa 23: Inventario Real Agendado No Worker

Status: concluida.

Entregas:

- Substituir snapshot placeholder por coleta real de usuarios, grupos e computadores.
- Salvar snapshots versionados em JSON.
- Gerar resumo diario de ativos, inativos e objetos criticos.
- Expor metricas agregadas de inventario para Prometheus.

## Etapa 24: Testes Automatizados De Regressao

Status: concluida.

Entregas:

- Criar testes unitarios para filtros e seguranca.
- Criar testes de contrato dos endpoints principais.
- Criar testes para operacoes sensiveis em modo dry-run.
- Integrar testes ao CI local e GitHub Actions.

## Etapa 25: Inventario Segmentado Para Ambientes Grandes

Status: concluida.

Entregas:

- Permitir segmentar inventario por OU.
- Reduzir consultas amplas em ambientes grandes.
- Adicionar relatorio comparativo entre snapshots.
- Adicionar alertas de variacao anormal de objetos.

## Etapa 26: Paginacao E Range Retrieval LDAP

Status: concluida.

Entregas:

- Adicionar paginacao LDAP para consultas acima do limite atual.
- Tratar `member;range=` em grupos muito grandes.
- Expor informacao de consulta parcial nos endpoints.
- Ajustar inventario para coletar totais completos em bases grandes.

## Etapa 27: Experiencia Web Operacional

Status: concluida.

Entregas planejadas:

- Refinar interface para operadores de infraestrutura.
- Adicionar dashboard visual de inventario, alertas e jobs.
- Melhorar filtros avancados e estado de erro.
- Guiar operacoes sensiveis com confirmacoes claras.

Entregas realizadas:

- Painel operacional inicial com saude da API, metricas, prontidao de configuracao e auditoria recente.
- Botao explicito para teste de conexao AD.
- CORS configuravel para acesso do frontend a API em ambiente local.
- Endpoint protegido para consultar o ultimo snapshot de inventario.
- Cards de inventario e indicadores de revisao no painel web.
- Filtros avancados nas listagens e relatorios por OU, grupo, sistema operacional, periodo e limite.
- Fluxo guiado de dry-run para operacoes sensiveis de usuarios e computadores.
- Endpoint e painel web para status de jobs do worker.
- Estados de erro e permissao mais claros na interface web.

## Etapa 28: Validacao Integrada E Preparacao De Operacao

Status: concluida.

Entregas planejadas:

- Criar comando unico de validacao operacional.
- Validar sintaxe, frontend, Compose, API, worker e endpoints protegidos.
- Suportar checks opcionais de LDAP/LDAPS e dry-run em laboratorio.
- Documentar fluxo de prontidao para operadores.

Entregas realizadas:

- Script `scripts/operational-readiness.sh` com checks locais, Docker, API, worker, frontend e dry-run opcional.
- Runbook operacional em `docs/operations-runbook.md`.
- README atualizado com o estado real do projeto e link para prontidao operacional.
- `scripts/ci-local.sh` integrado ao smoke check de prontidao.

## Etapa 29: Backup, Restore E Retencao Operacional

Status: concluida.

Entregas planejadas:

- Criar scripts para backup e restore do PostgreSQL.
- Exigir confirmacao explicita para restore.
- Gerar checksum para backups.
- Documentar validacao de restore em laboratorio.
- Documentar retencao de backups, relatorios, snapshots e auditoria.

Entregas realizadas:

- Script `scripts/backup-postgres.sh`.
- Script `scripts/restore-postgres.sh`.
- Guia `docs/backup-restore.md`.
- Runbook operacional atualizado com criterio de backup.

## Etapa 30: Coletor De Logon Das Estacoes

Status: concluida.

Entregas planejadas:

- Receber status de estacoes via script distribuido por GPO.
- Registrar computador, usuario, IP e horario informado.
- Proteger ingestao com token dedicado.
- Exibir na tela de usuarios o computador de logon mais recente quando disponivel.
- Documentar agendamento por Scheduled Task.

Entregas realizadas:

- Endpoint `POST /api/status` e `POST /workstation-status`.
- Migracao `002_workstation_status.sql` com historico em `workstation_status_events`.
- Configuracoes `WORKSTATION_STATUS_ENABLED` e `WORKSTATION_STATUS_TOKEN`.
- Enriquecimento da listagem de usuarios com `Computador do logon`, `IP` e horario recebido.
- Guia `docs/workstation-logon-collector.md` com script PowerShell e orientacao de GPO.

## Etapa 31: Login AD E RBAC Por Grupos

Status: concluida.

Entregas planejadas:

- Criar tela de login personalizada para operacao TCE-AL.
- Autenticar operadores no Active Directory.
- Mapear grupos do AD para perfis da aplicacao.
- Remover dependencia de token manual no fluxo normal do frontend.
- Registrar auditoria de login permitido e negado.

Entregas realizadas:

- Endpoint `POST /auth/ad-login`.
- Configuracoes `AD_LOGIN_DOMAIN` e `AD_ROLE_*_GROUP_DN`.
- Emissao de JWT com perfis derivados dos grupos do AD.
- Tela de login TCE-AL na interface web.
- Documentacao em `docs/security-model.md`, `docs/frontend.md` e `docs/environment.md`.
