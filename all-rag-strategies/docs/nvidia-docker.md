<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# explore mais o conteudo, mas agora focando nas estrategias PRIME/prime-run que eu acredito que ja esta configurado em minha maquina, e explore mais sobre as estrategias com o docker

O PRIME/prime-run permite renderizar na dGPU NVIDIA e exibir na iGPU Intel, economizando energia e liberando a dGPU para workloads pesados quando você decide, o que é ideal em notebooks Optimus como o E470. Em geral, usa-se a variável de ambiente para “offload” e, em distros que fornecem o wrapper, o comando prime-run já injeta as variáveis corretas para OpenGL/GLX e Vulkan/EGL.[^1][^2][^3]

### PRIME/prime-run na prática

- Comando direto via variáveis (OpenGL/GLX):
`__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia <app>`.[^4][^5]
- Para Vulkan/EGL, normalmente apenas `__NV_PRIME_RENDER_OFFLOAD=1` já ativa o layer VK_LAYER_NV_optimus e a offload ocorre na dGPU.[^5]
- Wrapper “prime-run” (se não existir, crie):
Crie /usr/local/bin/prime-run com `__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia exec "$@"` e torne executável; daí use `prime-run <app>`.[^6][^2]
- Em launchers (Steam/Lutris), use a linha de comando: `__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia %command%` para forçar a dGPU por jogo/app.[^7][^1]
- Observações de compatibilidade: em composições Wayland + GDM, há relatos de intermitência e regressões no PRIME offload, sendo Xorg mais previsível em alguns cenários; se notar falhas, teste sessão Xorg ou revise o provider `__NV_PRIME_RENDER_OFFLOAD_PROVIDER`.[^8][^9][^4]


### Variáveis úteis e seleção fina

- Básicas: `__NV_PRIME_RENDER_OFFLOAD=1` liga o offload para a primeira tela NVIDIA; `__GLX_VENDOR_LIBRARY_NAME=nvidia` garante GLX via NVIDIA no caminho OpenGL.[^4][^5]
- Controle de provider: `__NV_PRIME_RENDER_OFFLOAD_PROVIDER=NVIDIA-G0` pode especificar o provider correto quando o nome não é o padrão esperado, útil em setups com múltiplos providers.[^5][^4]
- DRI_PRIME: em alguns stacks Mesa/DRI3, `DRI_PRIME=1 <app>` também pode direcionar para a dGPU (especialmente AMD/Intel), mas no caso NVIDIA o caminho suportado é o de variáveis acima/prime-run.[^1]


### Estratégias com Docker + PRIME

- Objetivo: o container enxergar a GPU NVIDIA para CUDA/cuDNN e afins, enquanto o host continua exibindo via iGPU. Para isso, o essencial é: driver NVIDIA no host funcional, /dev/nvidia* presentes, e NVIDIA Container Toolkit instalado para habilitar `--gpus` no Docker.[^10][^4]
- Teste básico: `docker run --rm --gpus all nvidia/cuda:12.9.0-base-ubuntu22.04 nvidia-smi` deve listar a GPU e drivers, confirmando que o runtime NVIDIA está passando a dGPU ao container.[^10]
- Compose com GPU (sintaxe atual):

```
services:
  app:
    image: nvidia/cuda:12.9.0-runtime-ubuntu22.04
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

Isso pede 1 GPU com driver nvidia e capability gpu, permitindo CUDA no container sem mexer no display do host, o que combina bem com PRIME offload no desktop.[^11]

- Seleção de GPU específica: se houver mais de uma GPU, use `device_ids: ['0']` no bloco de devices para fixar qual dGPU o container usará.[^12]
- GUI/OpenGL dentro do container: se quiser rodar apps gráficos dentro do container aproveitando PRIME (render na dGPU, exibir na iGPU), exporte o DISPLAY/X11/Wayland e mapeie o socket de exibição; ainda assim, as variáveis de PRIME podem ser necessárias dentro do container para GLX/Vulkan conforme o app:
    - X11: volume de /tmp/.X11-unix e `-e DISPLAY=:0`, além de `__NV_PRIME_RENDER_OFFLOAD=1` e `__GLX_VENDOR_LIBRARY_NAME=nvidia` no ambiente do container.[^4][^5]
    - Wayland: mapeie o socket do compositor e variáveis XDG, mas atenção a limitações de PRIME em Wayland relatadas por alguns usuários; Xorg tende a ser mais direto para GLX.[^9][^8]


### Boas práticas e troubleshooting

- Garanta que `nvidia-smi` no host funciona antes do Docker; isso confirma driver, módulo e device files prontos para o runtime.[^4]
- Se o app no container usa OpenGL/GLX e renderização offloaded, exporte as variáveis de PRIME dentro do container (ou crie um wrapper tipo prime-run no container) para garantir o path correto de GLX.[^5][^4]
- Se aparecer erro de seleção de driver “could not select device driver "nvidia" with capabilities: [[gpu]]”, revise a instalação do NVIDIA Container Toolkit e a sintaxe do Compose, ou tente `docker run --gpus all` para isolar o problema do Compose.[^11][^12]
- Em casos de falha de inicialização da dGPU reportada no log do X (NVIDIA(G0) init fail), revise journal/dmesg e as opções de sessão (testar Xorg), pois impactos no PRIME podem impedir o offload de GLX/GUI, embora CUDA headless geralmente funcione independente do display.[^8][^4]


### Fluxos recomendados

- Desktop + apps nativos: usar `prime-run <app>` para jogos, render e benchmarks, mantendo a sessão no iGPU por padrão para economia de energia.[^2][^1]
- Workloads CUDA em containers: manter a sessão gráfica no iGPU, e passar a dGPU ao container via `--gpus all` ou Compose devices; se o container também exibir janelas, aplicar as variáveis PRIME dentro do container para GLX/Vulkan conforme necessário.[^11][^4]
<span style="display:none">[^13][^14][^15][^16][^17][^18][^19][^20][^21][^22]</span>

<div align="center">⁂</div>

[^1]: https://wiki.archlinux.org/title/PRIME

[^2]: https://bbs.archlinux.org/viewtopic.php?id=260172

[^3]: https://wiki.debian.org/NVIDIA_Optimus

[^4]: https://download.nvidia.com/XFree86/Linux-x86_64/435.17/README/primerenderoffload.html

[^5]: https://download.nvidia.com/XFree86/Linux-x86_64/440.31/README/primerenderoffload.html

[^6]: https://www.siberoloji.com/how-to-use-prime-for-hybrid-graphics-nvidia-optimus-on-arch-linux/

[^7]: https://www.tuxedocomputers.com/en/PRIME-GPU-Render-Offloading/GPU-on-demand-Mode-Guide.tuxedo

[^8]: https://github.com/NixOS/nixpkgs/issues/90152

[^9]: https://forums.developer.nvidia.com/t/issue-with-prime-render-offload-on-wayland/174993

[^10]: https://forums.opensuse.org/t/howto-tumbleweed-desktop-nvidia-prime-render-offload/165723

[^11]: https://docs.docker.com/compose/how-tos/gpu-support/

[^12]: https://github.com/blakeblackshear/frigate/discussions/16052

[^13]: https://www.reddit.com/r/linuxmasterrace/comments/garoie/what_is_nvidia_prime_render_offloading_and_which/

[^14]: https://www.youtube.com/watch?v=xcRqQwIWZ_0

[^15]: https://forums.freebsd.org/threads/prime-render-offload-on-nvidia.82561/

[^16]: https://www.reddit.com/r/linux4noobs/comments/16qpggj/proper_nvidia_prime_setup_under_wayland/

[^17]: https://www.reddit.com/r/hyprland/comments/1e03ttb/nvidiaprime_package_outdated/

[^18]: https://github.com/lutris/lutris/issues/4237

[^19]: https://bbs.archlinux.org/viewtopic.php?id=303787

[^20]: https://forum.manjaro.org/t/setting-up-prime/35365

[^21]: https://forums.balena.io/t/jetson-orin-nano-x11-server/374244

[^22]: https://forums.developer.nvidia.com/t/prime-no-offloading-required-prime-is-it-supported/154181

