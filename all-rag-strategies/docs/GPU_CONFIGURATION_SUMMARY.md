# Resumo da Configuração de GPU e Melhorias no Script de Inicialização

Este documento resume as discussões e ações tomadas para configurar o acesso à GPU NVIDIA para serviços Docker e aprimorar o script `start_services.py` neste projeto.

## 1. Verificação da GPU no Host

Confirmamos que os drivers NVIDIA estão corretamente instalados e funcionando no sistema host.

*   **Comando de Verificação:**
    ```bash
    nvidia-smi
    ```
    A saída deve mostrar informações detalhadas sobre a GPU, como versão do driver e uso.

*   **Teste de Uso da dGPU/iGPU:**
    Para verificar qual GPU está sendo usada por aplicativos gráficos:
    *   **Na dGPU (NVIDIA):**
        ```bash
        __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia glxgears
        ```
        Monitore com `watch -n 1 nvidia-smi` em outro terminal para ver a atividade da GPU NVIDIA.
    *   **Na iGPU (Integrada):**
        ```bash
        glxgears
        ```
        Monitore com `watch -n 1 nvidia-smi`; não deve haver atividade significativa na GPU NVIDIA.

## 2. Estratégia Docker + PRIME para Aceleração de GPU

A estratégia adotada visa utilizar a iGPU para a exibição do desktop do host (economizando energia) e dedicar a dGPU NVIDIA para cargas de trabalho computacionais intensivas dentro dos contêineres Docker (como o `ollama`).

*   **Configuração no `docker-compose.yml`:**
    O projeto já possui uma configuração elegante para isso, utilizando perfis e a seção `deploy.resources` para alocar a GPU. O serviço `ollama-gpu` é configurado para usar a GPU NVIDIA quando o perfil `gpu-nvidia` está ativo.

    Exemplo da configuração existente para `ollama-gpu`:
    ```yaml
    ollama-gpu:
      profiles: ["gpu-nvidia"]
      <<: *service-ollama
      deploy:
        resources:
          reservations:
            devices:
              - driver: nvidia
                count: 1 # ou 'all' para todas as GPUs
                capabilities: [gpu]
    ```
    *   **Observação:** Para cargas de trabalho de computação (CUDA/ML) dentro do Docker, as variáveis de ambiente `PRIME` (ex: `__NV_PRIME_RENDER_OFFLOAD`) não são necessárias dentro do contêiner, pois o NVIDIA Container Toolkit gerencia o acesso direto à GPU.

## 3. Melhorias no Script `start_services.py`

Identificamos e corrigimos um problema de robustez no script `start_services.py` relacionado ao uso de nomes de contêineres "hardcoded".

*   **Problema Original:** As funções `wait_for_database` e `initialize_rag_schema_runtime` utilizavam o nome fixo `supabase-db` para interagir com o contêiner do banco de dados. Isso poderia causar falhas se o Docker Compose gerasse um nome de contêiner diferente (ex: `localai-db-1`).

*   **Solução Implementada:** Ambas as funções foram modificadas para encontrar dinamicamente o ID do contêiner do banco de dados usando o comando `docker compose ps -q db`. Isso garante que o script sempre se conecte ao contêiner correto, independentemente do nome gerado pelo Docker.

*   **Impacto:** O script `start_services.py` agora é mais robusto e confiável para iniciar e gerenciar os serviços, especialmente em ambientes onde os nomes dos contêineres podem variar.

## 4. Como Iniciar os Serviços com Suporte à GPU

Para iniciar todo o stack, incluindo o serviço `ollama` com aceleração de GPU NVIDIA, utilize o seguinte comando:

```bash
python start_services.py --profile gpu-nvidia
```

## 5. Verificação Final da Integração da GPU

Após iniciar os serviços, você pode verificar se o contêiner `ollama` está utilizando a GPU:

1.  **Verifique a atividade geral da GPU no host:**
    ```bash
    watch -n 1 nvidia-smi
    ```
    Você deve ver alguma atividade na GPU NVIDIA, indicando que ela está sendo utilizada.

2.  **Verifique o uso da GPU *dentro* do contêiner `ollama`:**
    ```bash
    docker exec ollama nvidia-smi
    ```
    Este comando deve mostrar a saída do `nvidia-smi` diretamente do ambiente do contêiner `ollama`, confirmando que ele tem acesso e está utilizando a GPU.
