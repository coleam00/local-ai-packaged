# 📋 SPEC-KIT.md - Metodologia Spec-Driven Development para AI-Stack

**Complemento ao BMAD:** Framework alternativo e complementar focado em **especificação como fonte de verdade**, integrado ao GitHub, Claude Code, Copilot CLI e orquestração n8n.

---

## **1. Introdução: Spec-Driven vs. Vibe Coding**

O **Spec-Driven Development (SDD)** é uma metodologia que coloca **especificações formais, detalhadas e estruturadas** como o guia executável para geração de código por IA.

### Comparação: Vibe Coding vs. Spec-Driven

| Aspecto | Vibe Coding | Spec-Driven Development |
|---------|------------|------------------------|
| **Início** | Prompt vago → IA adivinha | Especificação clara → IA implementa |
| **Qualidade** | Inconsistente, ajustes frequentes | Consistente, previsível |
| **Documentação** | Fraca ou inexistente | Excelente (specs são docs) |
| **Escala** | Bom para POC/prototipagem | Produção, equipes, compliance |
| **Rastreabilidade** | Conversas perdidas em chat | Versionado no Git |
| **Governança** | Ad-hoc | Estruturado, auditável |
| **Integração com CI/CD** | Manual | Automática via webhooks |

**Verdade Fundamental:** Modelos de linguagem são excelentes em **completamento de padrões**, não em leitura mental. Uma especificação clara elimina 80% da renegociação.

---

## **2. Arquitetura de Spec-Kit: Quatro Fases**

O Spec-Kit organiza o desenvolvimento em **quatro fases sequenciais** com validação humana entre cada uma:

```
Constitution (Memória Permanente)
    ↓
[Fase 1: SPECIFY] → spec.md (O quê + Por quê)
    ↓ [Revisão]
[Fase 2: PLAN] → plan.md (Como + Tech Stack)
    ↓ [Revisão]
[Fase 3: TASKS] → tasks/*.md (Breakdown executável)
    ↓ [Revisão]
[Fase 4: IMPLEMENT] → Código + Testes + Docs
    ↓ [Validação]
Deploy → Sincroniza back ao spec.md
```

### **2.1 Constitution: Os Princípios Imutáveis**

O `constitution.md` é o **arquivo mais crítico**. Define diretrizes que se aplicam a **todas as mudanças futuras**, independente do projeto.

**Estrutura Base:**

```markdown
# 📋 Constitution

## 1. Princípios de Qualidade de Código
- Linguagem: TypeScript (strict mode obrigatório)
- Linting: ESLint + Prettier (config no repo)
- Cobertura de testes: Mínimo 80%
- Code review: 2 aprovações antes de merge

## 2. Padrões de Segurança
- Todas as credenciais via GitHub Secrets
- Sem hardcoding de APIs
- Validação de input em 100% dos endpoints
- Auditoria de acesso ao database

## 3. Requisitos de Performance
- APIs: Resposta < 200ms (p95)
- Frontend: Lighthouse score ≥ 90
- Database: Query timeout = 5s

## 4. Conformidade e Compliance
- LGPD: Dados pessoais encriptados em repouso
- SOC 2: Logs de auditoria por 90 dias
- Backup: Diário, testado a cada 30 dias

## 5. Padrões de Experiência de Usuário
- Acessibilidade: WCAG 2.1 AA mínimo
- Mobile-first: Funciona em telas de 320px+
- Loading: Indicadores visuais para > 1s

## 6. Integração com Stack Existente
- Usar Plane para gerenciamento de tarefas
- LightRAG para contexto de docs
- Webhooks GitHub → n8n para automação
- MCP servers para extensibilidade
```

**Geração Automática da Constitution:**

```bash
# Novo para Spec-Kit: análise de repo existente
specify generate-constitution --analyze-repo

# Isso varre:
# - README, docs/
# - .eslintrc, tsconfig.json (config existente)
# - AGENTS.md, claude.md (agentes definidos)
# - github-workflows (padrões CI/CD)
# E gera constitution.md inicial
```

---

### **2.2 Fase 1: SPECIFY - O Quê + Por Quê**

Você descreve em **alto nível** o que quer construir, focando em **problema de negócio**, não tecnologia.

**Comando:**

```bash
/specify Desenvolva um sistema de autenticação social (Google, GitHub) com multi-tenancy para SaaS.
```

**O Agente Gera: `specs/001-social-auth/spec.md`**

#### **2.2.2 Sincronização Automática Plane ↔ GitHub ↔ n8n**
# Especificação: Autenticação Social com Multi-Tenancy

## 1. Visão Geral
Sistema de autenticação OAuth 2.0 para múltiplos tenants, permitindo login via Google e GitHub.

## 2. Histórias de Usuário

### HU-1: Novo Usuário Faz Login via Google
**Como:** Usuário novo
**Quero:** Entrar na plataforma usando minha conta Google
**Para que:** Não precisar criar nova senha

**Critérios de Aceitação:**
- Redireciona para Google OAuth
- Retorna com email + foto de perfil
- Cria usuário com tenant padrão
- Redireciona ao dashboard

### HU-2: Gerenciar Identidades Sociais
**Como:** Usuário existente
**Quero:** Conectar/desconectar minha conta Google
**Para que:** Ter múltiplas opções de login

## 3. Requisitos Funcionais
- Suporte a Google e GitHub OAuth 2.0
- Sincronização automática de avatar + nome
- Desconexão de conta social sem afetar login
- Auditoria de cada login (IP, user-agent)

## 4. Requisitos Não-Funcionais
- Latência de login: < 500ms
- Disponibilidade: 99.9% (SLA)
- Encryption: TLS 1.3+, JWT com RS256

## 5. Riscos Identificados
- Token revocation delay do Google (até 1h)
- Múltiplos tenants com mesmo email
- Proteção contra account takeover

## 6. Sucesso Métrico
- Taxa de sucesso login: > 98%
- Tempo setup: < 5 min
- Suporte: < 2% de tickets relativos


**Validação pela Equipe:**
- Desenvolvedores revisam HUs (estão claras?)
- Product Owner aprova requisitos
- Arquiteto valida contra constitution

---

### **2.3 Fase 2: PLAN - Como + Tech Stack**

Você define **restrições técnicas** (stack, compliance, performance). O agente gera arquitetura e plano de implementação.

**Comando:**

```bash
/plan --tech-stack "Next.js, Prisma, PostgreSQL" --compliance "LGPD, SOC2" --performance-target "p95 < 200ms"
```

**O Agente Gera: `specs/001-social-auth/plan.md`**


# Plano Técnico: Autenticação Social com Multi-Tenancy

## 1. Arquitetura de Alto Nível

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Cliente   │ ──────▶ │  Next.js App │ ──────▶ │ PostgreSQL  │
│ (Next.js)   │         │  (Auth Logic)│         │ (Prisma)    │
└─────────────┘         └──────────────┘         └─────────────┘
                              │
                              ├─▶ Google OAuth
                              ├─▶ GitHub OAuth
                              └─▶ JWT Signing (RS256)
```

## 2. Stack Técnico Selecionado
- **Framework:** Next.js 14+ (App Router)
- **ORM:** Prisma 5+
- **Auth Library:** NextAuth.js 5 (ou Auth.js)
- **Database:** PostgreSQL 15+
- **JWT:** jsonwebtoken (RS256)
- **Testing:** Vitest + MSW (mocks)
- **CI/CD:** GitHub Actions

## 3. Schema de Banco de Dados

```prisma
model Tenant {
  id          String    @id @default(cuid())
  name        String
  subdomain   String    @unique
  createdAt   DateTime  @default(now())
  users       User[]
}

model User {
  id          String    @id @default(cuid())
  tenantId    String
  tenant      Tenant    @relation(fields: [tenantId], references: [id])
  email       String
  name        String?
  avatar      String?
  socialLinks SocialLink[]
  auditLogs   AuditLog[]
  createdAt   DateTime  @default(now())
}

model SocialLink {
  id          String    @id @default(cuid())
  userId      String
  user        User      @relation(fields: [userId], references: [id], onDelete: Cascade)
  provider    String    // "google" | "github"
  providerUserId String
  accessToken String?   @db.Text
  refreshToken String?  @db.Text
  expiresAt   DateTime?
  linkedAt    DateTime  @default(now())

  @@unique([userId, provider])
}

model AuditLog {
  id          String    @id @default(cuid())
  userId      String
  user        User      @relation(fields: [userId], references: [id])
  action      String    // "login", "link_social", "logout"
  ip          String
  userAgent   String
  timestamp   DateTime  @default(now())
}
```

## 4. Fluxo de Implementação

```
TASK 1: Setup Auth.js + OAuth Providers (GitHub, Google)
  ├─ Registrar apps em Google Cloud Console
  ├─ Registrar OAuth app no GitHub
  └─ Configurar callbacks

TASK 2: Modelo de Dados + Prisma
  ├─ Criar schema acima
  ├─ Migration e seed
  └─ Índices para performance

TASK 3: Endpoints de Autenticação
  ├─ GET /api/auth/signin → redirect OAuth
  ├─ GET /api/auth/callback/[provider]
  ├─ POST /api/auth/logout
  └─ GET /api/auth/session

TASK 4: Multi-Tenancy
  ├─ Middleware validar tenant
  ├─ Isolamento de dados por tenant
  └─ Subdomain routing

TASK 5: Auditoria + Segurança
  ├─ Log de cada login
  ├─ Rate limiting
  ├─ CSRF protection

TASK 6: Testes + Documentação
  ├─ Unit tests (providers, JWT)
  ├─ E2E tests (login flow)
  ├─ API docs (OpenAPI/Swagger)
```

## 5. Estimativa de Esforço
- Total: 21 story points (3 sprints de 7 pontos cada)
- Timeline: 3-4 semanas

## 6. Dependências Externas
- Google Cloud Console (setup)
- GitHub OAuth app
- PostgreSQL database (com pgcrypto extensão)


**Validação pela Equipe:**
- Arquiteto aprova design
- DevOps valida compliance
- Tech Lead revisa estoque de tasks

---

### **2.4 Fase 3: TASKS - Breakdown Executável**

Quebra-se o plano em **tarefas atômicas**, cada uma pronta para um agente implementar.

**Comando:**

```bash
/tasks --estimate-hours --assign-priorities
```

**O Sistema Gera: `specs/001-social-auth/tasks/`**

Exemplo: `001-setup-nextauth.md`


# Task: Setup Auth.js + Configurar Google OAuth

## Contexto
Primeira tarefa da implementação. Configura a biblioteca de autenticação e integra Google como provider.

## Objetivo
Usuário pode clicar "Login com Google", é redirecionado ao Google, e volta autenticado.

## Requisitos
- Auth.js v5 instalado
- .env.local com GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET
- Route handler `/api/auth/[...nextauth]` criado
- Session automaticamente acessível via `getSession()`

## Implementação Esperada

### 1. Instalar dependências
```bash
npm install next-auth@latest
```

### 2. Arquivo: `src/app/api/auth/[...nextauth]/route.ts`
```typescript
import NextAuth from "next-auth"
import GoogleProvider from "next-auth/providers/google"

export const authOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID || "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET || "",
    }),
  ],
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account?.provider === "google") {
        token.googleId = profile?.id
      }
      return token
    },
    async session({ session, token }) {
      if (session?.user) {
        session.user.googleId = token.googleId as string
      }
      return session
    },
  },
}

const handler = NextAuth(authOptions)
export { handler as GET, handler as POST }
```

### 3. Arquivo: `src/components/LoginButton.tsx`
```typescript
"use client"
import { signIn } from "next-auth/react"

export default function LoginButton() {
  return (
    <button onClick={() => signIn("google")}>
      Login com Google
    </button>
  )
}
```

## Testes
- [ ] Clicar botão → redireciona a Google
- [ ] Após login → retorna ao app autenticado
- [ ] Session acessível via `getSession()`
- [ ] Logout limpa session

## Critério de Aceite
- Nenhum erro no console
- Session persiste em refresh
- Logout funciona
- Token é assinado com RS256 (se usar JWT)

## Referências
- [Auth.js Docs](https://authjs.dev)
- [Google OAuth Setup](https://console.cloud.google.com)
- [Task anterior: PLAN.md](../plan.md)
- [Constitution.md](../../memory/constitution.md)


**Estrutura de Pastas de Tasks:**

```
specs/001-social-auth/tasks/
├── 001-setup-nextauth.md
├── 002-configure-github-oauth.md
├── 003-create-database-schema.md
├── 004-implement-multi-tenancy.md
├── 005-add-audit-logging.md
└── 006-write-tests.md
```

Cada task é **independente mas ordenada**, permitindo paralelização onde possível.

---

### **2.5 Fase 4: IMPLEMENT - Geração de Código**

Agora o agente implementa cada task sequencialmente, gerando código, testes e documentação.

**Comando:**

```bash
/implement --task 001-setup-nextauth --with-tests --follow-style-guide
```

O agente:
1. Lê `constitution.md` (restrições)
2. Lê `plan.md` (arquitetura)
3. Lê `tasks/001-setup-nextauth.md` (requição específica)
4. Gera código implementando
5. Gera testes (80%+ cobertura)
6. Abre PR automaticamente

**Output Esperado:**
- Código em `src/app/api/auth/...`
- Testes em `src/app/api/auth/[...nextauth].test.ts`
- PR comentado com checklist de revisão

---

## **3. Integração com AI-Stack Existente**

### **3.1 Estrutura de Pastas Spec-Kit Dentro do Repo**

```
my-project/
├── .specify/                    # Root de Spec-Kit
│   ├── memory/
│   │   ├── constitution.md      # Princípios imutáveis
│   │   └── claude.md            # Contexto permanente (integrado)
│   ├── scripts/
│   │   ├── create-new-feature.sh
│   │   ├── setup-plan.sh
│   │   ├── update-claude-md.sh
│   │   └── sync-to-plane.sh    # NEW: sincroniza com Plane
│   ├── specs/
│   │   ├── 001-social-auth/
│   │   │   ├── spec.md
│   │   │   ├── plan.md
│   │   │   ├── tasks/
│   │   │   │   ├── 001-setup-nextauth.md
│   │   │   │   ├── 002-configure-github-oauth.md
│   │   │   │   └── ...
│   │   │   ├── changelog.md     # Rastreamento de mudanças
│   │   │   └── status.md        # Status de implementação
│   │   └── 002-database-migrations/
│   │       ├── spec.md
│   │       ├── plan.md
│   │       └── tasks/
│   └── templates/
│       ├── spec-template.md
│       ├── plan-template.md
│       └── tasks-template.md
│
├── .github/
│   ├── workflows/
│   │   ├── spec-kit-sync.yml    # Sincroniza specs com Plane
│   │   └── ...
│   ├── mcp-config.json          # MCP servers para Spec-Kit
│   └── spec-kit-prompts/        # Prompts customizados
│
├── src/
├── tests/
└── docs/
```

---

### **3.2 Sincronização: Spec-Kit ↔ Plane ↔ GitHub**

**Novo Workflow n8n: `spec-kit-orchestration.json`**

```json
{
  "name": "Spec-Kit ↔ Plane ↔ GitHub Sync",
  "nodes": [
    {
      "id": "spec_kit_webhook",
      "type": "Webhook",
      "config": {
        "path": "spec-kit/new-task",
        "method": "POST"
      }
    },
    {
      "id": "parse_spec_task",
      "type": "Function",
      "code": "const task = $input.body.task; return { taskId: task.id, title: task.title, description: task.description };"
    },
    {
      "id": "create_plane_issue",
      "type": "HTTP Request",
      "config": {
        "url": "{{ env.PLANE_API }}/issues/",
        "method": "POST",
        "body": {
          "name": "{{ $node.parse_spec_task.json.title }}",
          "description": "[From Spec-Kit]\n{{ $node.parse_spec_task.json.description }}\n\n**Link:** [View Spec](...)",
          "priority": "{{ mapPriority(task.priority) }}",
          "estimate": "{{ task.estimateHours }}",
          "labels": ["spec-kit-task", "{{ task.specId }}"]
        }
      }
    },
    {
      "id": "create_github_issue",
      "type": "GitHub API",
      "config": {
        "action": "createIssue",
        "body": "## Spec-Kit Task\n\n{{ $node.parse_spec_task.json.description }}\n\n**Plane Issue:** {{ $node.create_plane_issue.json.html_url }}"
      }
    },
    {
      "id": "update_spec_status",
      "type": "Function",
      "code": "return { specId: $input.body.task.specId, planeIssueId: $node.create_plane_issue.json.id, githubIssueId: $node.create_github_issue.json.number, status: 'synced' };"
    }
  ]
}
```

---

### **3.3 MCP Server Customizado para Spec-Kit**

Novo MCP server que permite agentes acessar specs diretamente:

```python
# mcp-spec-kit-server/server.py

from mcp.server import Server
import json
from pathlib import Path

app = Server("spec-kit")

@app.tool()
def list_specs() -> list:
    """Lista todas as specs do projeto"""
    specs_dir = Path(".specify/specs")
    return [d.name for d in specs_dir.iterdir() if d.is_dir()]

@app.tool()
def read_spec(spec_id: str) -> dict:
    """Lê completo uma spec (especificação, plano, tasks)"""
    spec_path = Path(f".specify/specs/{spec_id}")
    return {
        "spec": (spec_path / "spec.md").read_text(),
        "plan": (spec_path / "plan.md").read_text(),
        "tasks": [
            f.read_text() 
            for f in (spec_path / "tasks").glob("*.md")
        ]
    }

@app.tool()
def get_constitution() -> str:
    """Retorna a constitution do projeto"""
    return Path(".specify/memory/constitution.md").read_text()

@app.tool()
def update_task_status(spec_id: str, task_id: str, status: str):
    """Atualiza status de uma task (in-progress, done, blocked)"""
    status_file = Path(f".specify/specs/{spec_id}/status.md")
    # Atualiza arquivo
    return {"updated": True, "timestamp": datetime.now().isoformat()}
```

**Registrado em `.github/mcp-config.json`:**

```json
{
  "mcp_servers": {
    "spec-kit": {
      "command": "python",
      "args": ["mcp-spec-kit-server/server.py"],
      "tools": [
        "list_specs",
        "read_spec",
        "get_constitution",
        "update_task_status"
      ]
    }
  }
}
```

---

## **4. Fluxo Completo: Do Conceito ao Deploy**

### **Cenário: Implementar "Two-Factor Authentication"**

**Passo 1: Iniciar nova spec no Copilot CLI**

```bash
cd my-project
copilot

# No Copilot CLI prompt:
/specify Adicione autenticação de dois fatores (2FA) via SMS e authenticator app, com backup codes
```

**O que acontece internamente:**
1. Claude Code lê `.specify/memory/constitution.md`
2. Lê specs anteriores (`001-social-auth/`) para contexto
3. Gera número automático: `002-two-factor-auth`
4. Cria branch: `002-two-factor-auth`
5. Gera `specs/002-two-factor-auth/spec.md`

**Passo 2: Revisar e Refinar Spec**

```bash
# Git diff mostra o novo spec.md
# Você comenta, pede ajustes via Claude Code:

/specify --refine "Adicione suporte a TOTP (RFC 6238) e HOTP padrão"

# Commit quando satisfeito
git add .specify/specs/002-two-factor-auth/spec.md
git commit -m "docs(spec): 2FA specification"
```

**Passo 3: Planejar Implementação**

```bash
/plan --tech-stack "speakeasy (TOTP), twilio (SMS)" --compliance "NIST SP 800-63B"

# Gera: specs/002-two-factor-auth/plan.md
# Você valida arquitetura, performance, etc.
```

**Passo 4: n8n Sincroniza Automaticamente**

Webhook detecta novo spec → n8n:
1. Cria 6 issues no Plane (uma por task)
2. Cria 6 issues no GitHub (com links para Plane)
3. Atualiza roadmap no Plane
4. Notifica Slack: "@dev-team 🎯 Nova spec: 2FA com SMS + App"

**Passo 5: Quebra em Tasks**

```bash
/tasks --estimate-hours --assign-priorities

# Gera tasks numeradas:
# - 001-setup-totp-library.md (2h)
# - 002-sms-verification-flow.md (4h)
# - 003-backup-codes-generation.md (3h)
# - 004-database-schema.md (2h)
# - 005-ui-components.md (5h)
# - 006-tests-and-docs.md (4h)
```

**Passo 6: Implementação Paralela**

```bash
# Copilot CLI + Claude Code trabalham em paralelo:
copilot /implement --task 001-setup-totp-library --with-tests
copilot /implement --task 002-sms-verification-flow --with-tests

# Cada uma:
# - Abre PR separada
# - Referencia a task
# - Inclui testes
# - Atualiza docs
```

**Passo 7: Pipeline de Review**

Cada PR:
1. Passa linter + tests automático (GitHub Actions)
2. Validada contra `constitution.md` (regras não violadas?)
3. Humano faz review semântico
4. Merge aprova + fecha task no Plane

**Passo 8: Síntese Final**

Quando todas as 6 tasks estão "done":
1. n8n script cria changelog automático
2. Atualiza `specs/002-two-factor-auth/status.md` → "Implemented"
3. Fecha todas as issues relacionadas
4. Notifica Slack: "✅ 2FA está pronto para staging"

---

## **5. Comparação: BMAD vs. Spec-Kit**

## 5. Comparação: BMAD vs. Spec-Kit

| Dimensão | BMAD | Spec-Kit |
|----------|------|----------|
| **Foco** | Ciclo ágil humano + IA | Especificação como fonte de verdade |
| **Ponto de Partida** | Ideias → Brief → PRD | Problema → Spec detalhada |
| **Validação** | Human-in-the-loop em cada fase | Baseada em checklist + constitution |
| **Documentação** | Artefatos separados | Specs = documentação |
| **Rastreabilidade** | Por sprint | Por feature/spec branch |
| **Escalabilidade** | Bom para pequenas equipes | Bom para équipes distribuídas + enterprise |
| **Integração GitHub** | Manual | Nativa (branchs, issues, PRs) |
| **Compliance** | Via políticas internas | Via `constitution.md` versionada |
| **Ideal para** | Exploração, MVPs, prototipagem rápida | Produção, conformidade, grandes projetos |

**Recomendação:** Use **BMAD para exploração inicial** (requisitos vagos, alta incerteza) e mude para **Spec-Kit para implementação em produção** (requisitos claros, precisão crítica). As duas metodologias podem coexistir no mesmo projeto, aplicadas a diferentes fases ou épicos.
---

## **6. Governança: Constitution como Policy as Code**

A `constitution.md` é mais que documentação — é **executável**:

```yaml
# .github/workflows/constitution-check.yml
name: Validate Against Constitution

on: [pull_request]

jobs:
  constitution-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Check Code Quality Against Constitution
        run: |
          # Lê constitution.md
          # Valida:
          # - Coverage ≥ 80%
          # - No secrets hardcoded
          # - TypeScript strict mode
          # - API latency < 200ms (via benchmark)
          npm run constitution:validate
      
      - name: Validate Compliance
        run: npm run compliance:check
        # Verifica LGPD, SOC2, etc.
      
      - name: Performance Check
        run: npm run benchmark
        # Garante Lighthouse ≥ 90, etc.
```

---

## **7. Checklist de Implementação para AI-Stack**

- [ ] Criar `.specify/` no root do repo
- [ ] Migrar `BMAD.md` → `.specify/memory/constitution.md`
- [ ] Customizar templates em `.specify/templates/`
- [ ] Criar MCP server customizado para Spec-Kit
- [ ] Setup webhook n8n para spec-kit → Plane ↔ GitHub
- [ ] Criar GitHub Action para validar contra constitution
- [ ] Documentar no `README.md` como usar Spec-Kit
- [ ] Treinar equipe: "Sempre comece com `/specify`"
- [ ] Configurar Power Prompts específicos para Spec-Kit (ver CLAUDE_CODE_GUIDE.md)
- [ ] Integrar ao AGENTS.md: definir "Spec-Kit Agent" role

---

## **8. Recursos Úteis**

- **GitHub Spec-Kit Oficial:** https://github.com/github/spec-kit
- **Specify CLI:** `uvx --from git+https://github.com/github/spec-kit.git specify init`
- **Documentação Oficial:** https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai/
- **Spec-Driven Development Guide:** https://www.softwareseni.com/spec-driven-development-in-2025/
- **Martin Fowler Analysis:** https://martinfowler.com/articles/exploring-gen-ai/

---

## **Próximos Passos**

1. **Semana 1:** Setup `.specify/` com constitution personalizada
2. **Semana 2:** Testar com novo feature usando `/specify` → `/plan` → `/tasks`
3. **Semana 3:** n8n sync workflow operacional
4. **Semana 4:** Constitution validação automática em GitHub Actions

