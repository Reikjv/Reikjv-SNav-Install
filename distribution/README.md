# Preparação da instalação pela interface BlueOS

Status: imagem GHCR e catálogo publicados e acessíveis sem login.
O instalador por terminal da release continua disponível e funcional.
[Testes ARM/QEMU aprovados](https://github.com/Reikjv/Reikjv-SNav-Install/actions/runs/37792781298).
[Catálogo publicado](https://github.com/Reikjv/Reikjv-SNav-Install/actions/runs/37793217851).

`publish.yml` está ativado como `.github/workflows/publish.yml`.
A autenticação usada para enviar commits precisa da permissão `workflow`.
O workflow usa o token temporário do próprio GitHub Actions para publicar
o pacote; não exige colocar uma senha/token pessoal neste repositório.

1. Ativar o workflow e executar a fase `publish-image`.
2. A imagem só é enviada após testar o instalador com Docker real/QEMU e
   testar a imagem de interface ARMv7, com porta padrão 8099.
3. Conferir que a imagem permite acesso público. Se necessário, no GitHub →
   Packages → reikjv-snav-install → Package settings, mudar a visibilidade
   do pacote para **Public**. Nesta publicação o acesso anônimo já funcionou.
4. Executar a fase `publish-catalog`. Ela verifica acesso anônimo ao GHCR,
   arquitetura e comando da imagem antes de gerar `blueos-manifest.json`.
5. Após verificar o catálogo publicado, no BlueOS → Extensions → engrenagem
   → **+**, cadastrar um manifesto com nome Reikjv e URL:

```text
https://raw.githubusercontent.com/Reikjv/Reikjv-SNav-Install/main/blueos-manifest.json
```

Essa URL foi verificada após a fase `publish-catalog` bem-sucedida.
Mantenha o catálogo oficial e aplique a nova fonte. Pesquise Reikjv-SNav;
a versão é beta, então pode ser necessário habilitar versões de pré-lançamento.

Antes de migrar uma instalação feita por terminal, com ROV desarmado restaure
as fontes no painel, desconecte e pare o contêiner `reikjv-snav`. A instalação
pela interface e a instalação por terminal não podem rodar simultaneamente:
usam a mesma porta e os mesmos dados. O gerenciador BlueOS não executa as
guardas de atualização do nosso `install.sh`; restaure/desconecte antes de
atualizar ou remover a extensão pela interface.

O wrapper Docker altera apenas metadados e a porta padrão. A versão interna
da aplicação permanece 0.3.0-beta.3 e ainda exige validação de EKF/controle
no equipamento real.
