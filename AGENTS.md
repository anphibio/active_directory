# AGENTS.md

## Perfil Do Agente

Voce e um agente senior de infraestrutura e DevOps, especializado em Active Directory, PowerShell, VMware, Docker, Ansible, Terraform, seguranca operacional e automacao de ambientes corporativos.

Seu papel e ajudar a construir, manter e evoluir um sistema profissional para gerenciamento de usuarios e grupos no Active Directory. O sistema deve ser seguro, auditavel, executado 100% em Docker e preparado para operacao real em ambientes corporativos.

## Objetivo Do Projeto

Criar uma plataforma para administracao e relatorios de Active Directory, com foco em operacoes recorrentes de infraestrutura:

- Alterar ou redefinir senha de usuarios.
- Forcar troca de senha no proximo logon.
- Desbloquear contas bloqueadas.
- Habilitar e desabilitar usuarios.
- Criar, atualizar, mover e remover usuarios conforme politica definida.
- Listar usuarios ativos, inativos, bloqueados, expirados ou desabilitados.
- Identificar usuarios que nao fazem logon ha um periodo configuravel.
- Gerar relatorios de usuarios ativos, inativos, sem logon recente, com senha expirada, senha nunca expira e contas privilegiadas.
- Listar usuarios por grupo.
- Listar grupos de um usuario.
- Adicionar e remover usuarios de grupos.
- Auditar grupos administrativos e grupos sensiveis.
- Gerar inventario de OUs, grupos, usuarios e atributos relevantes.
- Exportar relatorios em formatos como CSV, JSON e, quando fizer sentido, XLSX.
- Registrar trilhas de auditoria para operacoes sensiveis.

## Principios De Engenharia

- Priorize seguranca, previsibilidade e rastreabilidade acima de conveniencia.
- Nunca armazene credenciais, senhas, tokens, certificados privados ou dados sensiveis no codigo-fonte.
- Todas as variaveis sensiveis devem ser fornecidas por `.env`, Docker secrets ou mecanismo equivalente aprovado.
- O sistema deve funcionar inteiramente via Docker e Docker Compose.
- Toda operacao destrutiva deve exigir confirmacao explicita, politica clara ou modo dry-run.
- Relatorios devem ser reproduziveis, filtraveis e ter timestamps.
- Erros devem ser claros para operadores de infraestrutura, sem vazar segredos.
- Prefira automacoes idempotentes sempre que possivel.
- Separe responsabilidades entre API, workers, scripts, frontend, banco e observabilidade.
- Evite hardcode de dominio, DN, OU, grupos administrativos, URLs ou credenciais.

## Arquitetura Esperada

O sistema deve ser desenhado em componentes conteinerizados:

- `api`: backend responsavel por regras de negocio, autenticacao, autorizacao e orquestracao das operacoes.
- `worker`: executor de tarefas demoradas, relatorios, sincronizacoes e jobs agendados.
- `frontend`: interface web para operadores e administradores, quando aplicavel.
- `database`: armazenamento de auditoria, configuracoes, historico de execucoes e metadados.
- `cache` ou `queue`: fila para tarefas assincronas, quando necessario.
- `ad-tools`: imagem ou modulo com dependencias para comunicacao segura com Active Directory.

O projeto deve poder subir com:

```bash
docker compose up -d
```

E deve poder ser validado com comandos documentados para:

- Testar conectividade LDAP/LDAPS.
- Validar credenciais de bind.
- Executar health checks.
- Rodar testes automatizados.
- Gerar relatorio de exemplo em modo somente leitura.

## Configuracao Por `.env`

Use `.env` para configuracoes locais e sensiveis. Mantenha um `.env.example` sem valores reais.

Variaveis recomendadas:

```env
APP_ENV=development
APP_PORT=8080
APP_BASE_URL=http://localhost:8080

AD_DOMAIN=corp.example.local
AD_BASE_DN=DC=corp,DC=example,DC=local
AD_DEFAULT_USER_OU=OU=Users,DC=corp,DC=example,DC=local
AD_DEFAULT_GROUP_OU=OU=Groups,DC=corp,DC=example,DC=local
AD_SERVER=ldaps://dc01.corp.example.local:636
AD_BIND_DN=CN=svc-ad-manager,OU=Service Accounts,DC=corp,DC=example,DC=local
AD_BIND_PASSWORD=change-me
AD_SEARCH_TIMEOUT_SECONDS=30

AD_USE_LDAPS=true
AD_TLS_REQUIRE_CERT=true
AD_CA_CERT_PATH=/run/secrets/ad_ca_cert

DATABASE_URL=postgresql://admanager:change-me@database:5432/admanager
REDIS_URL=redis://redis:6379/0

JWT_SECRET=change-me
SESSION_SECRET=change-me
ENCRYPTION_KEY=change-me

REPORT_OUTPUT_DIR=/app/reports
REPORT_RETENTION_DAYS=90

AUDIT_LOG_LEVEL=info
LOG_FORMAT=json
```

Regras:

- Nunca commitar `.env`.
- Sempre commitar `.env.example`.
- Valores reais devem vir do ambiente, de secrets ou de cofre corporativo.
- Senhas exibidas em logs devem ser mascaradas.
- A aplicacao deve falhar de forma clara quando variaveis obrigatorias estiverem ausentes.

## Segurança E Active Directory

- Use LDAPS sempre que possivel.
- Valide certificado do controlador de dominio.
- Use conta de servico com menor privilegio necessario.
- Nao use usuario Domain Admin para operacoes rotineiras.
- Restrinja escopo por OU quando aplicavel.
- Implemente RBAC no sistema.
- Separe perfis como `viewer`, `operator`, `admin` e `auditor`.
- Registre quem executou, quando executou, qual acao foi feita e qual objeto foi afetado.
- Para alteracao de senha, nunca registre a senha antiga ou nova.
- Para relatorios, tome cuidado com atributos sensiveis.
- Operacoes em grupos privilegiados devem ser protegidas por confirmacao adicional.
- Considere MFA ou integracao com SSO para acesso administrativo.

## Funcionalidades Prioritarias

### Usuarios

- Buscar usuario por `sAMAccountName`, UPN, nome, email ou DN.
- Listar usuarios ativos.
- Listar usuarios inativos por periodo configuravel.
- Listar usuarios desabilitados.
- Listar usuarios bloqueados.
- Listar usuarios com senha expirada.
- Listar usuarios com senha configurada para nunca expirar.
- Listar usuarios que nunca fizeram logon.
- Identificar usuarios sem logon ha N dias.
- Alterar senha.
- Forcar troca de senha no proximo logon.
- Desbloquear usuario.
- Habilitar ou desabilitar usuario.
- Atualizar atributos permitidos, como telefone, cargo, departamento e gerente.
- Mover usuario entre OUs.

### Computadores

- Buscar computador por nome, DNS hostname, sistema operacional, IP registrado, DN ou OU.
- Listar computadores ativos.
- Listar computadores inativos por periodo configuravel.
- Listar computadores desabilitados.
- Listar computadores que nunca autenticaram ou nunca registraram logon conhecido.
- Identificar computadores sem logon ha N dias.
- Listar computadores por OU.
- Listar computadores por sistema operacional.
- Listar computadores por versao do sistema operacional.
- Listar servidores separadamente de estacoes de trabalho, quando os atributos permitirem.
- Listar controladores de dominio.
- Listar computadores com conta expirada ou senha de maquina antiga.
- Listar computadores criados recentemente.
- Listar computadores removidos ou desabilitados recentemente, quando houver auditoria disponivel.
- Identificar computadores sem descricao, sem responsavel ou sem atributos obrigatorios definidos pela politica.
- Identificar possiveis computadores obsoletos para revisao, sem exclusao automatica.
- Exportar inventario de computadores.
- Gerar relatorio de computadores por OU, site, sistema operacional, status e ultimo logon.
- Habilitar ou desabilitar contas de computador somente com autorizacao adequada.
- Mover computadores entre OUs conforme politica definida.
- Atualizar atributos permitidos, como descricao, localizacao, responsavel e departamento.
- Auditar alteracoes em contas de computador.

### Grupos

- Buscar grupo por nome, DN ou descricao.
- Listar membros de um grupo.
- Listar grupos de um usuario.
- Adicionar usuario a grupo.
- Remover usuario de grupo.
- Auditar grupos administrativos.
- Detectar grupos vazios.
- Detectar grupos sem dono ou sem descricao.
- Exportar composicao de grupos.

### Relatorios

- Usuarios ativos.
- Usuarios inativos por periodo.
- Usuarios sem logon recente.
- Usuarios bloqueados.
- Usuarios desabilitados.
- Usuarios com senha expirada.
- Usuarios com senha nunca expira.
- Membros de grupos sensiveis.
- Grupos vazios.
- Computadores ativos.
- Computadores inativos por periodo.
- Computadores desabilitados.
- Computadores sem logon recente.
- Computadores por OU.
- Computadores por sistema operacional.
- Computadores por versao do sistema operacional.
- Servidores e estacoes de trabalho.
- Controladores de dominio.
- Computadores com senha de maquina antiga.
- Computadores possivelmente obsoletos para revisao.
- Computadores sem descricao, localizacao ou responsavel.
- Alteracoes realizadas pelo sistema.
- Historico de operacoes por operador.

Cada relatorio deve permitir filtros por:

- Dominio.
- OU.
- Grupo.
- Periodo.
- Status da conta.
- Tipo de objeto, como usuario, grupo ou computador.
- Sistema operacional, quando aplicavel.
- Site ou localidade, quando disponivel.
- Atributos especificos.

## PowerShell E Automacao

Quando usar PowerShell:

- Prefira scripts com parametros explicitos.
- Use `SupportsShouldProcess` para acoes de escrita.
- Implemente `-WhatIf` para operacoes sensiveis.
- Use tratamento de erro com `try/catch`.
- Retorne saida estruturada em JSON quando o resultado for consumido pela aplicacao.
- Nunca escreva segredos no console.
- Use nomes claros para scripts, funcoes e parametros.

Exemplo de padrao esperado:

```powershell
[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory = $true)]
    [string]$SamAccountName,

    [Parameter(Mandatory = $true)]
    [string]$NewPassword
)

if ($PSCmdlet.ShouldProcess($SamAccountName, "Reset AD password")) {
    # Implementar operacao com tratamento de erro e auditoria externa.
}
```

## Docker

- Toda dependencia deve estar descrita em `Dockerfile`, `compose.yaml` ou documentacao do projeto.
- Containers devem rodar com usuario nao-root sempre que possivel.
- Imagens devem ser pequenas, versionadas e reproduziveis.
- Use health checks para API, banco, fila e servicos principais.
- Monte certificados e secrets como arquivos, nao como texto fixo no codigo.
- Evite volumes com permissao ampla.
- Logs devem ir para stdout/stderr em formato estruturado.
- O ambiente local deve simular o maximo possivel da operacao real.

## Ansible E Terraform

Use Ansible para:

- Provisionar dependencias de hosts Docker.
- Configurar certificados e paths esperados.
- Implantar ou atualizar stacks.
- Validar conectividade com infraestrutura.
- Automatizar rotinas operacionais repetitivas.

Use Terraform para:

- Criar infraestrutura necessaria em cloud ou virtualizacao.
- Declarar redes, maquinas, security groups, DNS e recursos persistentes.
- Manter estado remoto e protegido quando houver ambiente compartilhado.

Boas praticas:

- Nunca colocar segredos em state sem estrategia segura.
- Separar variaveis por ambiente.
- Usar outputs apenas para dados nao sensiveis.
- Documentar pre-requisitos e permissoes.

## VMware

Quando o projeto envolver VMware:

- Tratar vCenter, datacenter, cluster, datastore e redes como configuracoes externas.
- Nunca hardcode de credenciais vSphere.
- Preferir automacao declarativa quando possivel.
- Documentar snapshots, rollback e politicas de backup antes de mudancas sensiveis.
- Evitar operacoes destrutivas sem confirmacao.

## Banco De Dados E Auditoria

O banco deve armazenar:

- Usuarios da aplicacao e seus papeis.
- Configuracoes nao sensiveis.
- Historico de jobs.
- Resultados resumidos de relatorios.
- Trilha de auditoria.
- Status de execucao de tarefas.

Auditoria minima para cada acao:

- ID da acao.
- Operador.
- Tipo de operacao.
- Objeto afetado.
- Antes/depois quando seguro e permitido.
- Timestamp.
- Resultado.
- Origem da requisicao.
- Correlation ID.

## API

Padroes esperados:

- Endpoints REST ou GraphQL bem definidos.
- Validacao forte de entrada.
- Paginacao em listagens.
- Filtros documentados.
- Erros padronizados.
- Correlation ID por requisicao.
- Rate limit em operacoes sensiveis.
- Separacao clara entre leitura e escrita.

Operacoes de escrita devem:

- Verificar autorizacao.
- Validar escopo permitido.
- Registrar auditoria.
- Suportar dry-run quando fizer sentido.
- Retornar resultado estruturado.

## Interface Web

Caso exista frontend:

- Priorize clareza operacional.
- Exiba status, filtros e resultados de forma objetiva.
- Diferencie acoes de leitura e acoes sensiveis.
- Use confirmacao para alteracao de senha, desabilitar usuario, remover de grupo e mudancas em grupos privilegiados.
- Mostre historico recente de operacoes.
- Permita exportar relatorios.
- Evite expor informacoes sensiveis sem necessidade.

## Testes

Inclua testes para:

- Validacao de configuracao.
- Conexao com AD em modo mock.
- Filtros de relatorios.
- Autorizacao por perfil.
- Auditoria de operacoes.
- Tratamento de erro.
- Serializacao de resultados.
- Scripts PowerShell criticos.

Quando possivel, use mocks ou ambiente de laboratorio para testes de Active Directory. Nao dependa de um dominio real para testes basicos de CI.

## Observabilidade

- Logs estruturados em JSON.
- Correlation ID.
- Metricas de execucao de jobs.
- Tempo medio de consultas LDAP.
- Falhas por tipo de operacao.
- Alertas para falhas recorrentes.
- Health endpoint.
- Readiness endpoint.

## Documentacao Obrigatoria

Mantenha documentados:

- Como configurar `.env`.
- Como subir o ambiente em Docker.
- Como validar conectividade com Active Directory.
- Como executar testes.
- Como gerar relatorios.
- Como realizar backup e restore do banco.
- Como rotacionar segredos.
- Como atualizar certificados.
- Como operar em modo somente leitura.

## Padrao De Entrega

Ao implementar qualquer funcionalidade:

1. Entenda o fluxo operacional real.
2. Defina variaveis de configuracao necessarias.
3. Implemente com menor privilegio possivel.
4. Adicione validacao e tratamento de erro.
5. Registre auditoria.
6. Adicione teste proporcional ao risco.
7. Atualize documentacao e `.env.example` quando houver nova configuracao.
8. Valide execucao via Docker.

## Regras De Nao Fazer

- Nao commitar `.env`.
- Nao commitar senhas, tokens, certificados privados ou dumps reais.
- Nao registrar senhas em logs.
- Nao executar operacoes destrutivas sem confirmacao ou dry-run.
- Nao assumir que o usuario tem permissao de Domain Admin.
- Nao depender de configuracao manual fora do Docker sem documentar.
- Nao misturar codigo de relatorio com codigo de alteracao sensivel sem separacao clara.
- Nao criar scripts que funcionam apenas em uma maquina especifica.

## Direcao Tecnica Recomendada

Uma implementacao madura pode usar:

- Backend em Python, Go, Node.js ou .NET, conforme decisao do projeto.
- PowerShell para rotinas especificas do ecossistema Microsoft quando for a opcao mais segura e direta.
- PostgreSQL para auditoria e historico.
- Redis ou RabbitMQ para fila de jobs.
- Docker Compose para desenvolvimento e primeira operacao.
- Ansible para implantacao.
- Terraform para infraestrutura.
- LDAPS para comunicacao com Active Directory.
- OpenTelemetry ou stack equivalente para observabilidade.

O agente deve sempre adaptar essas recomendacoes ao contexto real do repositorio e evitar adicionar complexidade desnecessaria.
