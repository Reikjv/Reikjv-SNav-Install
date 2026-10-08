# Reikjv-SNav — instalação no BlueOS

Distribuição pública para **ARMv7** (`arm` no Docker), versão **0.3.0-beta.2**.
Integra SPRINT-Nav Mini ou Nortek Nucleus 1000 ao ArduSub. Esta versão é beta
e ainda requer validação da fusão EKF e do controle no equipamento real.

## Instalar pela internet

O BlueOS precisa estar conectado à internet. Mantenha o ROV desarmado.
No BlueOS, habilite Pirate Mode, abra **Ferramentas → Terminal** e execute:

```bash
red-pill
```

Depois, copie o bloco completo:

```bash
curl -fL https://github.com/Reikjv/Reikjv-SNav-Install/releases/download/v0.3.0-beta.2-install.1/install.sh -o /tmp/reikjv-snav-install.sh && sudo bash /tmp/reikjv-snav-install.sh
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
correspondentes. Para Nucleus a entrada padrão é TCP 9002 e a medição precisa
estar iniciada pelo software Nortek. Requisitos do projeto: ArduSub 4.7+,
conjunto 1 do EKF. Confirmar comunicação não comprova fusão EKF ou Position Hold.

## Instalação existente e dados

O instalador conserva `/usr/blueos/extensions/reikjv-snav`. Para atualizar,
primeiro restaure as fontes no painel, desconecte a extensão e mantenha o ROV
desarmado. A instalação é bloqueada quando existem fontes selecionadas ou
transação pendente. O contêiner anterior é preservado parado; se a nova
instância falhar, o instalador tenta restaurar o anterior.

Use dados próprios para cada ROV: não copie backups de parâmetros entre veículos.
O instalador não arma o ROV, não seleciona fontes e não escreve parâmetros do
autopiloto. Esta instalação usa Docker diretamente; não faz cadastro no Bazaar.

## Instalação sem internet no BlueOS

Baixe `install.sh` e `reikjv-snav-0.3.0-beta.2-armv7.tar.gz` nos
[arquivos da release](https://github.com/Reikjv/Reikjv-SNav-Install/releases/tag/v0.3.0-beta.2-install.1)
e envie os dois para a pasta inicial do File Browser do BlueOS.
No terminal, depois de `red-pill`:

```bash
cd /usr/blueos/userdata
sudo bash install.sh --archive reikjv-snav-0.3.0-beta.2-armv7.tar.gz
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
`aa83576e2a4025031334dae5c5051c1430dea9a0`, sem alteração do código de navegação.
O instalador desta distribuição inicia essa imagem na porta 8099.
O controle de instalação é verificado localmente com Docker/rede simulados
em `tests/test_installer.py`. O roteiro `tests/verify-install.sh` permite
verificar com Docker ARM/QEMU num runner Linux descartável; esse novo roteiro
ainda não foi executado. A imagem da aplicação já havia passado por ensaios
ARM sob emulação em sua origem. Nenhum desses ensaios substitui testes no
BlueOS/Navigator real. O exemplo de workflow em `tests/` não está ativado.
