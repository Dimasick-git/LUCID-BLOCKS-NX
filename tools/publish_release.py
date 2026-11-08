"""Upload one verified NSP, verify GitHub's copy, then publish the draft."""
from pathlib import Path
import argparse, hashlib, http.client, json, os, subprocess, urllib.parse, urllib.request

ROOT = Path(__file__).resolve().parents[1]

def credential():
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if token:
        return token
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='never')
    result = subprocess.run(['git','credential','fill'], cwd=ROOT,
        input='protocol=https\nhost=github.com\n\n', text=True,
        capture_output=True, env=env, timeout=30)
    fields = dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
    if result.returncode or not fields.get('password'):
        raise RuntimeError('GitHub credential unavailable; no release was published')
    return fields['password']

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-auth', action='store_true')
    parser.add_argument('--nsp',type=Path)
    parser.add_argument('--notes',type=Path)
    parser.add_argument('--tag')
    parser.add_argument('--title')
    parser.add_argument('--prerelease',action='store_true')
    parser.add_argument('--repo',default='Dimasick-git/LUCID-BLOCKS-NX')
    args=parser.parse_args()
    token=credential()
    headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json',
             'X-GitHub-Api-Version':'2022-11-28','User-Agent':'LucidBlocksNX-release'}
    def api(path, data=None, method=None):
        req=urllib.request.Request('https://api.github.com'+path,
            data=json.dumps(data).encode() if data is not None else None,
            headers=headers, method=method)
        with urllib.request.urlopen(req,timeout=60) as response:
            return json.load(response)
    user=api('/user')
    print('GitHub account:',user['login'],flush=True)
    assert user['login'].lower()==args.repo.split('/')[0].lower()
    if args.check_auth: return
    assert args.nsp and args.notes and args.tag and args.title
    report=json.loads(args.nsp.with_suffix('.verified.json').read_text())
    assert report['nca_ivfc_and_payload_verified'] and report['sha256']==digest(args.nsp)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    base='/repos/'+args.repo
    release=api(base+'/releases',{'tag_name':args.tag,'target_commitish':commit,
        'name':args.title,'body':args.notes.read_text(encoding='utf-8'),
        'draft':True,'prerelease':args.prerelease})
    print('Uploading to draft:',release['id'],flush=True)
    upload=urllib.parse.urlsplit(release['upload_url'].split('{')[0]+
        '?'+urllib.parse.urlencode({'name':args.nsp.name}))
    connection=http.client.HTTPSConnection(upload.netloc,timeout=600)
    try:
        connection.putrequest('POST',upload.path+'?'+upload.query)
        for key,value in headers.items(): connection.putheader(key,value)
        connection.putheader('Content-Type','application/octet-stream')
        connection.putheader('Content-Length',str(args.nsp.stat().st_size))
        connection.endheaders()
        count=0
        with args.nsp.open('rb') as stream:
            while block:=stream.read(1024*1024):
                connection.send(block)
                count+=len(block)
                if count%(128*1024**2)==0: print('Uploaded MiB:',count//1024**2,flush=True)
        response=connection.getresponse()
        if response.status!=201:
            raise RuntimeError('Asset upload failed, HTTP '+str(response.status))
        asset=json.loads(response.read())
    finally:
        connection.close()
    assert asset['size']==args.nsp.stat().st_size
    expected='sha256:'+report['sha256']
    if asset.get('digest'):
        assert asset['digest']==expected
    else:
        request=urllib.request.Request(asset['url'],headers={**headers,'Accept':'application/octet-stream'})
        with urllib.request.urlopen(request,timeout=600) as response:
            assert hashlib.file_digest(response,'sha256').hexdigest()==report['sha256']
    published=api(base+'/releases/'+str(release['id']),{'draft':False},method='PATCH')
    assert not published['draft']
    # A draft has an untagged download URL; take the final URL after publishing.
    final_asset=next(item for item in published['assets'] if item['id']==asset['id'])
    result={'release':published['html_url'],'asset':final_asset['browser_download_url'],
            'sha256':report['sha256'],'bytes':asset['size'],'commit':commit}
    args.nsp.with_suffix('.github.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Published verified NSP:',published['html_url'],flush=True)

if __name__=='__main__': main()
