# **🧠 Princípios de Engenharia de Contexto**

O sucesso da IA depende fundamentalmente de fornecer o contexto certo, no formato certo, no momento certo. Este documento descreve as estratégias e metodologias que usamos para gerenciar a "memória" de nossos agentes de IA, garantindo respostas precisas e evitando alucinações.

## **1. A Anatomia da Janela de Contexto**

Integrações operacionais atuais que impactam contexto:
- Documentação canônica: `RAG_STACK_RUNBOOK.md`, `EXECUTING_STACK_RUNBOOK.md`, `CLAUDE.md`
- Fonte de verdade da stack: `docker-compose.yml`, `start_services.py`
- Distribuição por proxy: Caddy (hostnames do `.env`), Portainer para inspeção/saúde
- LLM via LiteLLM (externo): normalize headers e chaves no ponto único (`LLM_BASE_URL`), reduzindo variação entre agentes


A janela de contexto de um agente (ex: 200k tokens do Claude) é sua memória de trabalho. O objetivo não é preenchê-la, mas sim otimizá-la com informações de alta relevância. Um contexto menor e focado supera um contexto grande e ruidoso.

**Componentes Otimizáveis:**
*   **MCPs (Ferramentas):** Podem ser removidos quando não estão em uso.
*   **Arquivos de Memória (`claude.md`):** Devem ser curados para evitar acúmulo de informações desnecessárias.
*   **Histórico da Conversa:** O componente mais volátil, onde o "ruído" se acumula.

## **2. Estratégia de Memória Dual: Longo e Curto Prazo**

Adotamos uma abordagem de memória complementar para dar aos nossos agentes persistência e agilidade.

### **2.1. Memória de Longo Prazo: O Cline Memory Bank (`/memory-bank`)**

Esta é a base de conhecimento canônica e persistente do projeto, curada por humanos e assistida por IA.

*   **Estrutura:** Organizada em arquivos Markdown hierárquicos que formam a fonte da verdade para o nosso sistema RAG.
    ```
    memory-bank/
    ├── project_brief.md       # Visão de alto nível, requisitos e objetivos
    ├── system_patterns.md     # Arquitetura, decisões técnicas, padrões
    ├── tech_stack.md          # Tecnologias, configuração, dependências
    └── ...                    # Outros documentos canônicos
    ```
*   **Função:** Fornece a documentação estruturada que é processada, fragmentada (sharded) e ingerida pelo nosso pipeline RAG (`LightRAG`), alimentando o conhecimento de fundo de todos os agentes.

### **2.2. Memória de Curto Prazo: O Workspace do Agente (`.agent/`)**

Este é o "bloco de notas" tático e dinâmico do agente durante uma sessão de desenvolvimento.

*   **Estrutura:** Contém artefatos gerados por subagentes para a tarefa atual.
    ```
    .agent/
    ├── task/           # Planos de implementação detalhados
    ├── SOPs/           # Procedimentos Operacionais Padrão para tarefas recorrentes
    └── readme.md       # Índice para o agente sobre o conteúdo do workspace
    ```
*   **Função:** Otimiza a janela de contexto da sessão ativa. Por exemplo, um subagente de pesquisa pode condensar 50.000 tokens de documentação em um plano de 2.000 tokens na pasta `task/`, que é tudo que o agente principal precisa para a implementação.

### **2.3. Arquivos de Contexto Tático para Tarefas Específicas**

Além das memórias de longo e curto prazo, o desenvolvedor pode fornecer arquivos de contexto tático para guiar o agente em tarefas específicas, melhorando ainda mais a precisão.

*   **`plan.md`:** Um documento que descreve os objetivos e os passos para uma nova feature ou tarefa. Serve como um "mini-brief" para o agente, garantindo alinhamento antes da execução.
*   **`changelog.md`:** Fornece ao agente um histórico das decisões e mudanças no projeto. Isso o ajuda a entender "por que" o código está como está, evitando a repetição de erros passados ou a reintrodução de padrões obsoletos.

Esses arquivos são exemplos práticos de engenharia de contexto ativa, onde o desenvolvedor enriquece o ambiente do agente com informações de alta relevância para a tarefa em questão.

> **🛠️ Guia de Implementação:** Para detalhes sobre como usar esses e outros arquivos de contexto, consulte o [`💻CLAUDE_CODE_GUIDE.md`](../guides/CLAUDE_CODE_GUIDE.md).


### 2.4. Memória Estruturada e Executável: A Constituição do Spec-Kit

Quando um projeto utiliza a metodologia Spec-Kit, introduzimos uma camada adicional e mais poderosa de memória de longo prazo:

*   **A Constituição (`.specify/memory/constitution.md`):** Este arquivo transcende a documentação tradicional. Ele serve como uma **memória de longo prazo executável e com regras**, contendo diretrizes de qualidade, segurança e compliance que são validadas automaticamente por pipelines de CI/CD. É a memória canônica que governa *todas* as ações dos agentes.
*   **Especificações (`spec.md`, `plan.md`, `tasks/*.md`):** Estes arquivos formam uma **memória de curto prazo altamente estruturada** para uma tarefa específica. Eles substituem o workspace `.agent/` por um fluxo de trabalho formal, garantindo que o agente siga um plano pré-aprovado e detalhado, minimizando desvios e maximizando a previsibilidade.

## **3. Técnicas de Otimização Ativa**

*   **Fragmentação de Documentos (Sharding):** A prática de quebrar documentos grandes do `memory-bank` em pedaços menores e semanticamente coesos antes da ingestão no RAG. Isso é crucial para:
    *   Maximizar a eficiência da janela de contexto.
    *   Melhorar a precisão da recuperação de informações.
    *   Reduzir drasticamente o consumo de tokens.
*   **Isolamento com Subagentes:** Delegar tarefas que consomem muitos tokens (pesquisa, planejamento) para subagentes que operam em um contexto isolado e retornam apenas um resumo conciso.
*   **Limpeza de Contexto:** Usar comandos como `/clear` (Claude Code) ou iniciar novas conversas entre tarefas distintas para combater o "apodrecimento de contexto" (Context Rot).
*   **Curadoria Ativa:** O desenvolvedor atua como um "Arquiteto de Contexto", garantindo que a memória do agente (tanto de longo quanto de curto prazo) seja relevante e de alta qualidade.
