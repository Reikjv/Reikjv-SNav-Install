#!/usr/bin/env bash
# Public ARMv7 installer. Run on the BlueOS host (red-pill), with sudo.
set -Eeuo pipefail
VERSION="0.3.0-beta.3"
RELEASE="v0.3.0-beta.3-install.1"
ASSET="reikjv-snav-${VERSION}-armv7.tar.gz"
SHA256="de41d43d5c4179acf6bf48d69a7e9f2e56d6468e51ce0d284147178310c9e675"
URL="https://github.com/Reikjv/Reikjv-SNav-Install/releases/download/${RELEASE}/${ASSET}"
IMAGE="reikjv-snav:${VERSION}"
NAME="reikjv-snav"
DATA="/usr/blueos/extensions/reikjv-snav"
PORT="8099"
CACHE="/var/cache/reikjv-snav"
ARCHIVE=""

fail() { echo "Erro: $*" >&2; exit 1; }
if [[ "${1:-}" == "--archive" && $# == 2 ]]; then
  ARCHIVE="$(realpath -- "$2")"
elif [[ $# != 0 ]]; then
  fail "Uso: sudo bash install.sh [--archive caminho/da/imagem.tar.gz]"
fi
[[ $EUID == 0 ]] || fail "Execute com sudo bash install.sh, no terminal do BlueOS apos red-pill."
for cmd in docker curl sha256sum python3 flock; do
  command -v "$cmd" >/dev/null || fail "Comando necessario nao encontrado: $cmd"
done
exec 9>/var/lock/reikjv-snav-install.lock
flock -n 9 || fail "Outra instalacao esta em andamento."
ARCH="$(docker version --format '{{.Server.Arch}}')"
case "$ARCH" in
  arm|armv7l|armhf) ;;
  *) fail "Este pacote e ARMv7. Arquitetura Docker encontrada: $ARCH. Nenhum conteiner foi alterado." ;;
esac

if docker container inspect "$NAME" >/dev/null 2>&1; then
  [[ "$(docker inspect --format '{{index .Config.Labels "org.reikjv.snav.managed"}}' "$NAME")" == true ]] || fail "Nome reikjv-snav ocupado por instalacao nao identificada."
fi

verify_archive() { printf '%s  %s\n' "$SHA256" "$1" | sha256sum --check --status; }
if [[ -n "$ARCHIVE" ]]; then
  verify_archive "$ARCHIVE" || fail "Checksum da imagem incorreto. Baixe novamente."
else
  mkdir -p -- "$CACHE"
  ARCHIVE="$CACHE/$ASSET"
  if ! verify_archive "$ARCHIVE" 2>/dev/null; then
    echo "Baixando o pacote ARMv7 (aproximadamente 77 MB)..."
    curl --fail --location --retry 3 --connect-timeout 20 --proto '=https' --tlsv1.2 "$URL" -o "$ARCHIVE.part"
    verify_archive "$ARCHIVE.part" || fail "Checksum da imagem incorreto; instalacao interrompida."
    mv -- "$ARCHIVE.part" "$ARCHIVE"
  fi
fi
echo "Integridade confirmada. Carregando imagem..."
docker load -i "$ARCHIVE"
[[ "$(docker image inspect --format '{{.Architecture}}' "$IMAGE")" == arm ]] || fail "Imagem com arquitetura incorreta."
mkdir -p -- "$DATA"
# Read-only check: refuse selected sources or a pending parameter transaction.
docker run --rm -v "$DATA:/data:ro" "$IMAGE" python -m snav.install_check

BACKUP=""
WAS_RUNNING=false
INSTALL_ID="$(date +%Y%m%d%H%M%S)-$$"
rollback() {
  local result=$?
  trap - ERR INT TERM
  set +e
  echo "Falha ao iniciar. Restaurando a instalacao anterior, se houver." >&2
  if [[ "$(docker inspect --format '{{index .Config.Labels "org.reikjv.snav.install"}}' "$NAME" 2>/dev/null)" == "$INSTALL_ID" ]]; then
    docker logs --tail 30 "$NAME" >&2
    docker rm -f "$NAME" >/dev/null
  fi
  if [[ -n "$BACKUP" ]]; then
    docker rename "$BACKUP" "$NAME"
  fi
  if [[ "$WAS_RUNNING" == true ]]; then docker start "$NAME"; fi
  exit "${result:-1}"
}
trap rollback ERR
trap 'false' INT TERM
if docker container inspect "$NAME" >/dev/null 2>&1; then
  WAS_RUNNING="$(docker inspect --format '{{.State.Running}}' "$NAME")"
  docker stop "$NAME"
  backup_candidate="$NAME-backup-$INSTALL_ID"
  docker rename "$NAME" "$backup_candidate"
  BACKUP="$backup_candidate"
fi

# Check after stopping the old instance. Roll back if another service owns 8099.
python3 - "$PORT" <<'PY'
import socket, sys
with socket.socket() as sock:
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(('0.0.0.0', int(sys.argv[1])))
    except OSError as exc:
        sys.exit(f'Porta {sys.argv[1]} indisponivel: {exc}')
PY

docker run -d --name "$NAME" \
  --label "org.reikjv.snav.install=$INSTALL_ID" \
  --restart unless-stopped --network host -v "$DATA:/data" \
  "$IMAGE" python -m snav.app --data-dir /data --port "$PORT"
HEALTHY=false
for attempt in {1..40}; do
  if [[ "$(docker inspect --format '{{.State.Running}}' "$NAME")" != true ]]; then break; fi
  if docker exec "$NAME" python -c 'import json,urllib.request; r=json.load(urllib.request.urlopen("http://127.0.0.1:8099/health",timeout=2)); assert r == {"status":"ok","version":"0.3.0-beta.3"}' >/dev/null 2>&1; then
    HEALTHY=true
    break
  fi
  sleep 1
done
[[ "$HEALTHY" == true ]]
trap - ERR INT TERM
echo ""
echo "Instalacao concluida. Abra http://blueos.local:8099/"
echo "Ou use http://IP_DO_BLUEOS:8099/ (o mesmo IP usado para acessar o BlueOS)."
echo "Nenhum parametro do autopiloto foi alterado pelo instalador."
if [[ -n "$BACKUP" ]]; then echo "Conteiner anterior preservado, parado: $BACKUP"; fi
