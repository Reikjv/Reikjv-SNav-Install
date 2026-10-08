"""Build the BlueOS catalog only after an anonymous GHCR pull is possible."""
import json
from pathlib import Path
import urllib.parse
import urllib.request

IMAGE = 'reikjv/reikjv-snav-install'
TAG = '0.3.0-beta.2-ui.1'
REPOSITORY = 'https://github.com/Reikjv/Reikjv-SNav-Install'


def public_image():
    query = urllib.parse.urlencode({'service': 'ghcr.io', 'scope': f'repository:{IMAGE}:pull'})
    # This token is anonymous, not a GitHub credential. Never use GH_TOKEN here:
    # the catalog must not be published if a ROV would need to log in.
    with urllib.request.urlopen('https://ghcr.io/token?' + query, timeout=30) as response:
        token = json.load(response)['token']
    request = urllib.request.Request(
        f'https://ghcr.io/v2/{IMAGE}/manifests/{TAG}',
        headers={'Authorization': 'Bearer ' + token,
                 'Accept': 'application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.manifest.v1+json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        manifest = json.load(response)
        digest = response.headers['Docker-Content-Digest']
    request = urllib.request.Request(
        f'https://ghcr.io/v2/{IMAGE}/blobs/{manifest["config"]["digest"]}',
        headers={'Authorization': 'Bearer ' + token})
    with urllib.request.urlopen(request, timeout=30) as response:
        config = json.load(response)
    assert config['architecture'] == 'arm' and config.get('variant') == 'v7', config
    assert config['config']['Cmd'][-2:] == ['--port', '8099']
    return digest


def catalog(digest):
    return [{
        'identifier': 'reikjv.snav', 'name': 'Reikjv-SNav',
        'website': REPOSITORY, 'docker': f'ghcr.io/{IMAGE}',
        'description': 'SPRINT-Nav Mini / Nortek Nucleus 1000 para ArduSub. Beta de bancada.',
        'extension_logo': 'https://raw.githubusercontent.com/Reikjv/Reikjv-SNav-Install/main/distribution/logo.png',
        'company_logo': 'https://raw.githubusercontent.com/Reikjv/Reikjv-SNav-Install/main/distribution/logo.png',
        'versions': {TAG: {
            'type': 'device-integration', 'tag': TAG, 'website': REPOSITORY,
            # Sum of uncompressed base layer archives. The wrapper adds config only.
            'images': [{'expanded_size': 244765696,
                        'platform': {'architecture': 'arm', 'variant': 'v7', 'os': 'linux'},
                        'digest': digest}],
            'authors': [{'name': 'Reikjv', 'email': '141414061+Reikjv@users.noreply.github.com'}],
            'filter_tags': ['navigation', 'dvl', 'ins'],
            'extra_links': {'documentation': REPOSITORY + '/blob/main/README.md'},
            'docs': REPOSITORY + '/blob/main/README.md',
            'readme': '<p>Beta ARMv7. Painel na porta 8099. Requer ArduSub 4.7+. Antes de migrar, restaure as fontes e pare a instalação pelo terminal. Não execute duas instâncias. Validar EKF e controle no ROV.</p>',
            'company': {'name': 'Reikjv', 'about': 'Navegação submarina'},
            'permissions': {'HostConfig': {
                'NetworkMode': 'host',
                'Binds': ['/usr/blueos/extensions/reikjv-snav:/data'],
                'RestartPolicy': {'Name': 'unless-stopped'}
            }}
        }}
    }]


if __name__ == '__main__':
    destination = Path(__file__).resolve().parents[1] / 'blueos-manifest.json'
    destination.write_text(json.dumps(catalog(public_image()), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Public ARMv7 image verified; catalog written:', destination.name)
