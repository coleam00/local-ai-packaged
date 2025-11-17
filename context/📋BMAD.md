# **Metodologia BMAD: Build with AI, Develop with Agile**

O BMAD é um framework que estrutura o desenvolvimento de software, integrando agentes de IA em um ciclo ágil profissional. Ele serve como a filosofia central que guia a interação entre humanos e IA desde a concepção até a entrega.

## **1. Princípios Fundamentais**

*   **Desenvolvimento Orientado por Especificações:** Transforma ideias em documentos robustos (Brief, PRD, Arquitetura) que se tornam a fonte da verdade para os agentes de IA.
*   **Ciclos Ágeis Curtos:** Sprints de 1-2 semanas para construção e refinamento iterativo, gerenciados na plataforma **Plane**.
*   **Agentes Especializados:** Utilização de um time de agentes de IA, cada um com um papel definido (Analista, PM, Arquiteto, Desenvolvedor), para garantir expertise em cada etapa.
*   **Human-in-the-Loop:** Supervisão humana em pontos de decisão críticos, como aprovação de PRDs, arquiteturas e pull requests.
*   **Otimização de Contexto:** Uso estratégico de **Document Sharding** para alimentar os agentes com informações precisas e relevantes, maximizando a performance e reduzindo custos.

## **2. O Ciclo de Vida BMAD**

O desenvolvimento é dividido em duas fases macro, interligadas por um sistema de gerenciamento de contexto.

> **🔗 Arquitetura Completa:** Para um diagrama detalhado de como os componentes se conectam, consulte [`📄CONTEXT.md`](CONTEXT.md).

### **Fase 1: Planejamento Estratégico (Assistido por IA)**

Nesta fase, os agentes de IA transformam uma ideia em um plano de projeto executável. O processo é iniciado no Claude Code (ou outra UI) e gerenciado no Plane.

1.  **Iniciação (Agente Analista):** Cria o **Project Brief** a partir de brainstorming e pesquisa.
2.  **Especificação (Agente PM):** Desenvolve o **PRD (Product Requirements Document)**, detalhando histórias de usuário e requisitos.
3.  **Design (Agente Arquiteto & UX):** Produz o **Documento de Arquitetura** (stack tecnológico, schemas) e as **Especificações de UI/UX** (wireframes, componentes).
4.  **Sincronização com Plane:** Os épicos e histórias de usuário gerados são automaticamente criados como issues no **Plane**, formando o backlog do projeto.

### **Fase 2: Desenvolvimento Iterativo (Executado por IA)**

Com o backlog definido no Plane, o ciclo de desenvolvimento ágil começa.

1.  **Document Sharding (Fragmentação):** Documentos de planejamento (PRD, Arquitetura) são fragmentados em pedaços contextuais menores. Este processo é automatizado via **n8n** e alimenta nosso sistema RAG, garantindo que os agentes sempre tenham o contexto mais relevante.
2.  **Geração de Histórias (Agente Scrum Master):** O Agente SM consome os épicos fragmentados e gera histórias de desenvolvimento detalhadas, prontas para implementação. Exemplo:

    ```markdown
    # Story 1.2: User Authentication API Integration

    ## Architecture Context
    - Utiliza a autenticação via JWT do Supabase.
    - Deve se integrar com a tabela `profiles` existente.
    - Referência: `docs/arquitetura/auth-flow.md`

    ## Implementation Details
    - Endpoints: `/auth/login`, `/auth/refresh`, `/auth/logout`
    - Error handling: Credenciais inválidas, token expirado.
    - Testes: Unitários para todos os endpoints e de integração com o frontend.
    ```
3.  **Implementação (Agente Desenvolvedor):** O Agente Dev implementa as histórias, utilizando hooks do Claude Code para garantir qualidade (linting, testes, segurança) a cada passo. O desenvolvimento pode ocorrer em paralelo usando Git Worktrees para explorar múltiplas soluções.
4.  **Revisão e QA (Humano + Agente QA):** O código é revisado por um humano, enquanto o Agente QA pode executar testes automatizados e validações.

> **🛠️ Implementação Detalhada:** Para comandos, scripts e configurações, consulte [`⚙️SYSTEM_WORKFLOWS.md`](../workflows/SYSTEM_WORKFLOWS.md).

### **2.1 O Ciclo Tático do Desenvolvedor: Explorar, Planejar, Executar**

Enquanto o ciclo de vida BMAD organiza o projeto em um nível macro, o ciclo "Explorar, Planejar, Executar" guia a implementação tática de cada história de usuário pelo desenvolvedor (humano ou IA). Ignorar este ciclo é a principal causa de resultados de baixa qualidade.

1.  **Explorar:** A primeira fase é dedicada a construir um contexto robusto. O agente é instruído a ler e analisar a documentação relevante, o código existente e os requisitos, mas explicitamente proibido de escrever código de implementação. O objetivo é garantir que o agente esteja "inteligente" antes de agir.
2.  **Planejar:** Com o contexto estabelecido, o agente gera um plano de implementação detalhado. Este plano é revisado e iterado. Técnicas como o prompt "My Developer" são usadas aqui para obter uma avaliação crítica e objetiva do plano proposto pela IA.
3.  **Executar:** Apenas com um contexto rico e um plano validado o agente recebe a instrução para implementar o código. Esta abordagem sequencial garante que a execução seja guiada por uma compreensão profunda do problema, resultando em código mais preciso, robusto e alinhado à arquitetura.


### **Fase 2 Expandida: Desenvolvimento Iterativo com Multi-Agent Orchestration**

Com o lançamento do GitHub Agent HQ e Copilot CLI, o ciclo de desenvolvimento BMAD incorpora orquestração nativa de múltiplos agentes paralelos:

#### **2.2.1 Seleção Estratégica de Agentes por Tarefa**

```
Épico (Plane)
    ↓
Mission Control (Agent HQ)
    ├→ [Analyzer Agent: Claude Code]
    │   └→ Mapeia requisitos + dependências
    │
    ├→ [Planner Agent: Copilot CLI]
    │   └→ Cria plano detalhado (paralelo com Analyzer)
    │
    ├→ [Implementer Agent: Claude Code]
    │   └→ Executa conforme plano
    │
    └→ [Reviewer Agent: Copilot CLI]
        └→ Valida qualidade + alinhamento
```

#### **2.2.2 Sincronização Automática Plane ↔ GitHub ↔ n8n**

O ciclo BMAD agora inclui gatilhos automáticos que mantêm todas as plataformas sincronizadas:

1. **Issue Criada no Plane** →
2. **n8n Webhook** analisa com MCP →
3. **GitHub Issue Criada** (link bidirecional) →
4. **Claude Code Detecta** via `/install-github-app` →
5. **Implementação Paralela** com Copilot CLI como reviewer →
6. **Status Sincronizados** back to Plane → Notificação Slack

#### **2.2.3 Human-in-the-Loop Otimizado**

Em vez de aprovações em cada passo (congestionamento), as decisões críticas são agrupadas:

**Auto-aprovável:**
- Refatoração de código (conforme linter + testes)
- Documentação de APIs
- Atualização de dependências menor

**Requer Aprovação Humana:**
- Mudanças arquiteturais
- Alterações de segurança
- Deploys em produção
- Remoção de features

Isso **reduz decisões humanas em 70%** enquanto mantém governança.

## **3. Gestão de Memória e Contexto**

A eficácia do BMAD depende de uma gestão de contexto impecável. Utilizamos uma abordagem complementar:

*   **Memory Bank (`/memory-bank`):** A base de conhecimento de longo prazo do projeto. Contém documentos estruturados (brief, arquitetura, padrões) que são a fonte principal para o RAG. É curado por humanos com a ajuda da IA.
*   **Workspace do Agente (`.agent/`):** A memória de trabalho de curto prazo do Claude Code. Contém planos de tarefa, SOPs (Procedimentos Operacionais Padrão) e resumos gerados por subagentes para otimizar o contexto da sessão atual.

### **Subagentes como Pesquisadores e Planejadores**

A prática mais eficaz é usar subagentes para tarefas que consomem muito contexto, como pesquisa ou planejamento detalhado.
*   **Fluxo:** O agente principal ativa um subagente especializado (ex: "especialista em API do Stripe").
*   **Resultado:** O subagente pesquisa, analisa e retorna um plano de implementação conciso ou um resumo, que é salvo na pasta `.agent/task`.
*   **Benefício:** O agente principal mantém seu contexto limpo para focar na implementação, economizando tokens e evitando "context rot" (apodrecimento de contexto).

## **4. Benefícios da Metodologia**

*   **Qualidade de Produção:** A estrutura e os checkpoints garantem um software robusto.
*   **Eficiência de Custo:** O Document Sharding e a gestão de contexto reduzem drasticamente o consumo de tokens.
*   **Consistência:** A documentação como fonte da verdade alinha todos os agentes (humanos e IA).
*   **Automação:** Integração nativa com ferramentas como Plane, n8n e Claude Code automatiza o gerenciamento e o desenvolvimento.

## 5. Metodologia Complementar: Spec-Driven Development

Para projetos que exigem alta precisão, conformidade e uma fonte de verdade auditável, a metodologia **Spec-Kit** é utilizada como um complemento ao BMAD. Enquanto o BMAD é ideal para exploração e prototipagem rápida, o Spec-Kit é projetado para o desenvolvimento robusto em produção.

> **Guia Completo:** Para entender a arquitetura e o fluxo do Spec-Kit, consulte [`SPEC_KIT.md`](methodology/SPEC_KIT.md).

