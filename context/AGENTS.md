# 🤖 AGENTS.md - Registro de Agentes Operacionais

Este documento serve como a fonte da verdade para a definição, responsabilidades, permissões e interações de todos os agentes de IA operacionais no nosso ecossistema.

## 1. Agente: Claude Code (Desenvolvedor Principal)

**Endpoint:** Terminal Claude Code
**Modelos:** Claude 3.5 Sonnet (default), Opus (para complexidade)
**Funções:**
- Implementação de features de alto nível a partir de especificações.
- Refatoração de código complexo.
- Escrita de testes unitários e de integração.
- Revisão de Pull Requests (análise automática).

**Restrições:**
- Não pode fazer deploy em produção sem aprovação humana.
- Não pode modificar secrets ou configurações críticas de segurança.
- Limitado a 5 PRs simultâneos para evitar sobrecarga de revisão.

**Contexto Obrigatório:**
- `claude.md` (contexto específico do projeto)
- `ARCHITECTURE.md` (referência arquitetural)
- `AGENTS.md` (este arquivo, para autoconsciência de seu papel)

**Integração:**
- GitHub App instalado via `/install-github-app`.
- MCP Server do Plane para acesso a tarefas.
- Webhooks n8n para sincronização de status.

---

## 2. Agente: GitHub Copilot CLI (Agente de Terminal)

**Endpoint:** Comando `copilot` na CLI
**Modelos:** Claude 3.5 Sonnet (default, via `COPILOT_MODEL`), alternáveis.
**Funções:**
- Exploração interativa de codebase.
- Análise de issues e geração de planos de implementação.
- Debugging colaborativo em tempo real.
- Execução de tarefas definidas pelo Mission Control.

**Restrições:**
- Todas as ações de escrita de código requerem preview e aprovação explícita.
- Sem acesso a repositórios privados sem autenticação OAuth.
- Rate-limited pela subscrição do GitHub Copilot.

**Contexto Disponível:**
- Acesso nativo ao contexto de issues, PRs e branches do GitHub.
- Histórico de commits e discussões.

**Integração:**
- Servidores MCP customizados via flag `--mcp-config`.
- Plane via MCP Server customizado.
- Acionado por n8n via webhooks para tarefas automatizadas.

---

## 3. Agente: n8n (Orquestrador de Workflows)

**Endpoint:** n8n Web UI + Webhooks
**Modelos:** Acessa múltiplos modelos via LiteLLM Proxy.
**Funções:**
- Orquestração de eventos entre GitHub ↔ Plane.
- Ingestão automatizada de documentos para o sistema RAG.
- Sincronização de status bidirecional.
- Notificações e alertas para a equipe.

**Restrições:**
- Executa apenas workflows versionados no repositório.
- Logs de auditoria completos para todas as ações.
- Timeout de 10 minutos por execução de workflow.

**Integração:**
- GitHub Webhooks.
- Plane API (autenticação via token).
- LightRAG API para ingestão de documentos.

---
## (O restante dos agentes como LiteLLM Router, etc., seguiriam este padrão)

## 6. Governança e Auditoria

**Quando um agente interage com um sistema crítico (deploy, deleção de dados):**
1. Requer aprovação explícita human-in-the-loop via Slack ou notificação no GitHub.
2. A ação é registrada em `audit.log` com timestamp, agente executor e contexto completo.
3. A ação é revertível dentro de 1 hora (ex: `git revert` automático).

**Escalação Automática:**
- Se um agente encontra o mesmo erro 3x seguidas em uma tarefa → alerta é enviado para o humano responsável.
- Se um agente supera o budget de tokens para uma tarefa → a execução é pausada e um resumo é gerado.
- Se a taxa de falha de um workflow > 20% em 24h → o workflow é desativado até revisão manual.