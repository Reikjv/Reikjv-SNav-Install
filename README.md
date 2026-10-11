# Reikjv-SNav — instalação no BlueOS

Distribuição pública para **ARMv7** (`arm` no Docker), versão **0.3.0-beta.5**.
Integra SPRINT-Nav Mini ou Nortek Nucleus 1000 ao ArduSub. Esta versão é beta
e ainda requer validação da fusão EKF e do controle no equipamento real.

## Instalar pela interface do BlueOS

Com o BlueOS conectado à internet, abra **Extensions → engrenagem → +**.
Mantenha o catálogo oficial e adicione uma fonte com nome **Reikjv** e URL:

```text
https://raw.githubusercontent.com/Reikjv/Reikjv-SNav-Install/main/blueos-manifest.json
```

Salve, clique **APPLY**, pesquise **Reikjv-SNav** e clique **GET**.
Escolha `0.3.0-beta.5-ui.1`, a distribuição ARMv7 para a interface. As versões anteriores continuam no catálogo para referência.
Se necessário, habilite a exibição de versões beta/pré-lançamento.
O programa é baixado do GitHub Container Registry sem login.
O painel fica disponível em **http://blueos.local:8099/**. Se a versão nova não aparecer, atualize a fonte de manifesto na engrenagem de Extensions e recarregue a página.

Se já instalou por terminal neste ROV: desarme, clique **Desativar SNav e restaurar**
no painel e pare o contêiner antigo antes de instalar pela interface.
Não execute duas instâncias juntas. O gerenciador do BlueOS não executa as
guardas do nosso instalador: use **Desativar SNav e restaurar** antes de atualizar
ou remover pela interface. Preserve os dados do veículo.

## Alternativa: instalar pelo terminal

O BlueOS precisa estar conectado à internet. Mantenha o ROV desarmado.
No BlueOS, habilite Pirate Mode, abra **Ferramentas → Terminal** e execute:

```bash
red-pill
```

Depois, copie o bloco completo:

```bash
curl -fL https://github.com/Reikjv/Reikjv-SNav-Install/releases/download/v0.3.0-beta.5-install.1/install.sh -o /tmp/reikjv-snav-install.sh && sudo bash /tmp/reikjv-snav-install.sh
```

O instalador identifica a arquitetura, baixa a imagem pronta (aproximadamente
77 MB), verifica SHA-256 e inicia o programa. Não precisa de GitHub login,
pendrive, Python instalado pelo operador ou compilação. ARM64 não está incluído
nesta distribuição inicial; o instalador recusa arquiteturas diferentes.

Ao ver **Instalacao concluida**, abra:

**http://blueos.local:8099/**

Se acessa o BlueOS por IP, use esse mesmo IP seguido de `:8099`, por exemplo
`http://192.168.2.2:8099/`. A porta 8088 permanece disponível para o terminal
do BlueOS. A extensão reinicia automaticamente junto com o computador do ROV.

## Conectar ao ArduSub

No BlueOS → **MAVLink Endpoints**, crie ou confira:

| Campo | Valor |
| --- | --- |
| Nome | Reikjv-SNav |
| Tipo | UDP Server |
| IP/Device | 0.0.0.0 |
| Porta | 14555 |
| Salvar entre sessões | Sim |

Deixe o endpoint habilitado. No painel Reikjv-SNav use
`udpout:127.0.0.1:14555`. Escolha SPRINT ou Nucleus, configure o IP/porta real
do sensor, salve e conecte. Primeiro confirme heartbeat do ArduSub e dados do
sensor com os três seletores de fontes desligados. A ausência de velocidade
DVL válida em bancada seca não é um teste de navegação.

Para SPRINT use saída HNav configurada no equipamento, com protocolo/porta
correspondentes. Para o Nucleus desta bancada, configure dados e comandos TCP
em `9000` (a porta 9002 recusou a conexão), salve e clique Conectar. Com a
medição parada, clique **Iniciar medição** no SNav; aguarde a confirmação START
e os contadores AHRS/BT. Clique **Parar medição** para confirmar STOP. Ao usar
**Desativar e restaurar**, o SNav envia STOP somente se ele próprio confirmou
START nesta conexão. Caso a rede caia, confira no software Nortek se a medição
continua. Em teste fora d'água, acompanhe a temperatura. Requisitos do projeto: ArduSub 4.7+,
conjunto 1 do EKF. Confirmar comunicação não comprova fusão EKF ou Position Hold.

## Instalação existente e dados

O instalador conserva `/usr/blueos/extensions/reikjv-snav`. Para atualizar,
primeiro use **Desativar SNav e restaurar** no painel e mantenha o ROV
desarmado. A instalação é bloqueada quando existem fontes selecionadas ou
transação pendente. O contêiner anterior é preservado parado; se a nova
instância falhar, o instalador tenta restaurar o anterior.

Use dados próprios para cada ROV: não copie backups de parâmetros entre veículos.
O instalador não arma o ROV, não seleciona fontes e não escreve parâmetros do
autopiloto. Esta instalação usa Docker diretamente; não faz cadastro no Bazaar.

## Instalação sem internet no BlueOS

Baixe `install.sh` e `reikjv-snav-0.3.0-beta.5-armv7.tar.gz` nos
[arquivos da release](https://github.com/Reikjv/Reikjv-SNav-Install/releases/tag/v0.3.0-beta.5-install.1)
e envie os dois para a pasta inicial do File Browser do BlueOS.
No terminal, depois de `red-pill`:

```bash
cd /usr/blueos/userdata
sudo bash install.sh --archive reikjv-snav-0.3.0-beta.5-armv7.tar.gz
```

## Diagnóstico

Se houver erro, guarde a mensagem. Para consultar o estado e os registros:

```bash
sudo docker ps -a --filter name=reikjv-snav
sudo docker logs --tail 80 reikjv-snav
```

Se a porta 8099 estiver ocupada, o instalador interrompe e tenta restaurar a
instalação anterior. Não encerre outros serviços sem identificar sua função.

## Conteúdo da distribuição

Este repositório contém o instalador, instruções e licenças de terceiros.
A imagem de execução é distribuída nas releases e contém o código Python,
painel web, identidade visual e dependências necessários à aplicação.
Histórico de desenvolvimento, dados de veículos e backups não fazem parte
desta distribuição. Não há uma licença geral de código aberto concedida por
este repositório; as licenças de terceiros estão em `licenses/` e na imagem.

A imagem ARMv7 foi produzida a partir do commit
`7a93bf207d3521e2eadab8f9dc8c0ea99f5c3bc2`.
O instalador desta distribuição inicia essa imagem na porta 8099.
O controle de instalação passou por oito testes locais com Docker/rede
simulados em `tests/test_installer.py`. O roteiro `tests/verify-install.sh`
também passou com Docker real e ARM/QEMU: instalação com 8088 ocupada,
checksum/arquitetura, bloqueio de fontes/transações pendentes, atualização,
preservação de dados e rollback. A imagem para a interface passou pelo teste
HTTP na porta 8099, iniciando sem conexão e sem fontes selecionadas.
[Execuções de verificação e publicação](https://github.com/Reikjv/Reikjv-SNav-Install/actions).

O catálogo só foi publicado após verificar acesso anônimo à imagem, arquitetura
ARMv7 e porta 8099. A instalação pelo gerenciador do BlueOS e a fusão EKF/controle
ainda requerem validação no veículo real. O workflow ativo está em
`.github/workflows/publish.yml`; o exemplo em `tests/` não está ativado.
