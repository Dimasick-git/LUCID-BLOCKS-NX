"""Assemble temporary upload pieces on GitHub, verify, then publish one NSP.

Used only by workflow_dispatch. No game building or keys run in Actions.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.parse
import urllib.request

REPO = os.environ['GITHUB_REPOSITORY']
TOKEN = os.environ['GH_TOKEN']
RELEASE = os.environ['RELEASE_ID']
assert RELEASE.isdigit()
BASE = 'https://api.github.com/repos/'+REPO

class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, target):
        result = super().redirect_request(request, fp, code, msg, headers, target)
        if result and urllib.parse.urlsplit(request.full_url).netloc != urllib.parse.urlsplit(target).netloc:
            result.remove_header('Authorization')
        return result

opener = urllib.request.build_opener(Redirect())
def request(url, method='GET', data=None, headers=None):
    opts = {'Authorization': 'Bearer '+TOKEN, 'Accept': 'application/vnd.github+json',
            'User-Agent': 'Lucid-Blocks-NX-release', 'X-GitHub-Api-Version': '2022-11-28'}
    opts.update(headers or {})
    return opener.open(urllib.request.Request(url, data=data, headers=opts, method=method), timeout=600)

def api(path):
    with request(BASE+path) as response:
        return json.load(response)

def download(asset, target):
    checksum = hashlib.sha256()
    with request(BASE+'/releases/assets/'+str(asset['id']), headers={'Accept': 'application/octet-stream'}) as response, target.open('wb') as out:
        while block := response.read(1024*1024):
            checksum.update(block); out.write(block)
    assert target.stat().st_size == asset['size']
    return checksum.hexdigest()

release = api('/releases/'+RELEASE)
assert release['draft'] and release['prerelease'], 'Only draft prereleases may be assembled'
assets = {a['name']: a for a in api('/releases/'+RELEASE+'/assets?per_page=100')}
with tempfile.TemporaryDirectory() as work:
    work = Path(work)
    manifest_asset = assets['nsp01-upload-manifest.json']
    manifest_path = work/'manifest.json'
    download(manifest_asset, manifest_path)
    manifest = json.loads(manifest_path.read_text())
    assert manifest['tag'] == release['tag_name']
    assert re.fullmatch(r'LUCID_BLOCKS_NX_FULL_[A-Z0-9]+\.nsp', manifest['name'])
    output = work/manifest['name']
    checksum = hashlib.sha256()
    with output.open('wb') as out:
        for piece in manifest['parts']:
            assert re.fullmatch(r'NSP01_UPLOAD_\d\d\.bin', piece['name'])
            asset = assets[piece['name']]
            assert asset['state'] == 'uploaded' and asset['size'] == piece['bytes']
            part = work/piece['name']
            assert download(asset, part) == piece['sha256'], piece['name']
            with part.open('rb') as source:
                while block := source.read(1024*1024):
                    checksum.update(block); out.write(block)
            part.unlink()
    assert output.stat().st_size == manifest['bytes']
    assert checksum.hexdigest() == manifest['sha256']
    existing = assets.get(manifest['name'])
    if existing:
        assert existing['state'] != 'uploaded', 'A complete installer already exists'
        request(BASE+'/releases/assets/'+str(existing['id']), method='DELETE').close()
    url = 'https://uploads.github.com/repos/'+REPO+'/releases/'+RELEASE+'/assets?name='+urllib.parse.quote(output.name)
    with output.open('rb') as source, request(url, method='POST', data=source,
            headers={'Content-Type': 'application/octet-stream', 'Content-Length': str(output.stat().st_size)}) as response:
        uploaded = json.load(response)
    assert uploaded['size'] == manifest['bytes'] and uploaded['state'] == 'uploaded'
    if uploaded.get('digest'):
        assert uploaded['digest'] == 'sha256:'+manifest['sha256']
    # Delete only the pieces listed in this validated transfer manifest.
    for asset in [assets[p['name']] for p in manifest['parts']]+[manifest_asset]:
        request(BASE+'/releases/assets/'+str(asset['id']), method='DELETE').close()
    body = json.dumps({'draft': False, 'prerelease': True, 'target_commitish': os.environ['GITHUB_SHA']}).encode()
    with request(BASE+'/releases/'+RELEASE, method='PATCH', data=body,
                 headers={'Content-Type': 'application/json'}) as response:
        published = json.load(response)
    assert published['prerelease'] and not published['draft']
    print('Published verified single-file NSP:', published['html_url'])
