"""Transfer a verified NSP to an existing draft, then assemble one asset in Actions."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse, hashlib, http.client, json, socket, tempfile, threading, time, urllib.parse, urllib.request
from publish_release import credential, digest, ROOT

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--nsp',type=Path,required=True)
    parser.add_argument('--draft',type=int,required=True)
    parser.add_argument('--workers',type=int,default=8,choices=range(1,9))
    args=parser.parse_args()
    report=json.loads(args.nsp.with_suffix('.verified.json').read_text())
    assert report['nca_ivfc_and_payload_verified'] and digest(args.nsp)==report['sha256']
    base='https://api.github.com/repos/Dimasick-git/LUCID-BLOCKS-NX'
    token=credential()
    headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','User-Agent':'LucidBlocksNX-transfer'}
    def api(path,data=None,method=None):
        request=urllib.request.Request(base+path,data=json.dumps(data).encode() if data is not None else None,headers=headers,method=method)
        with urllib.request.urlopen(request,timeout=60) as response:
            return json.load(response) if response.status!=204 else None
    release=api('/releases/'+str(args.draft))
    assert release['draft'] and release['prerelease'] and release['tag_name']=='v0.1.0-'+report['build'].lower()
    workflow=api('/actions/workflows/assemble-test-nsp.yml')
    assert workflow['state']=='active'
    assets={a['name']:a for a in api('/releases/'+str(args.draft)+'/assets?per_page=100')}
    transferred=0
    shown=0
    lock=threading.Lock()
    def upload(path,name,sha):
        nonlocal transferred,shown
        existing=assets.get(name)
        if existing:
            if existing.get('digest')=='sha256:'+sha and existing['size']==path.stat().st_size:
                print('Reusing checked transfer part:',name,flush=True)
                return existing
            assert existing['state']!='uploaded','Refusing to replace a completed asset with different content'
            api('/releases/assets/'+str(existing['id']),method='DELETE')
        url=urllib.parse.urlsplit(release['upload_url'].split('{')[0]+'?'+urllib.parse.urlencode({'name':name}))
        connection=http.client.HTTPSConnection(url.netloc,timeout=600)
        try:
            connection.connect()
            connection.sock.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,4*1024*1024)
            connection.putrequest('POST',url.path+'?'+url.query)
            for key,value in headers.items(): connection.putheader(key,value)
            connection.putheader('Content-Type','application/octet-stream')
            connection.putheader('Content-Length',str(path.stat().st_size))
            connection.endheaders()
            with path.open('rb') as source:
                while block:=source.read(1024*1024):
                    connection.send(block)
                    with lock:
                        transferred+=len(block)
                        if transferred-shown>=64*1024**2:
                            shown=transferred
                            print('Transfer MiB:',transferred//1024**2,'/',report['bytes']//1024**2,flush=True)
            response=connection.getresponse()
            if response.status!=201: raise RuntimeError('Part upload HTTP '+str(response.status))
            asset=json.loads(response.read())
            assert asset['state']=='uploaded' and asset['size']==path.stat().st_size
            assert asset.get('digest')=='sha256:'+sha,'GitHub part checksum differs'
            print('Verified transfer part:',name,flush=True)
            return asset
        finally: connection.close()
    with tempfile.TemporaryDirectory(prefix='nsp-transfer-',dir=args.nsp.parent.parent) as directory:
        directory=Path(directory)
        manifest={'tag':release['tag_name'],'name':args.nsp.name,'bytes':report['bytes'],'sha256':report['sha256'],'parts':[]}
        size=(report['bytes']+args.workers-1)//args.workers
        with args.nsp.open('rb') as source:
            for index in range(args.workers):
                path=directory/('NSP01_UPLOAD_%02d.bin'%index)
                remaining=min(size,report['bytes']-source.tell())
                with path.open('wb') as output:
                    while remaining:
                        block=source.read(min(1024*1024,remaining)); assert block
                        output.write(block); remaining-=len(block)
                manifest['parts'].append({'name':path.name,'bytes':path.stat().st_size,'sha256':digest(path)})
        assert sum(p['bytes'] for p in manifest['parts'])==report['bytes']
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures=[pool.submit(upload,directory/p['name'],p['name'],p['sha256']) for p in manifest['parts']]
            for future in as_completed(futures): future.result()
        path=directory/'nsp01-upload-manifest.json'
        path.write_text(json.dumps(manifest,indent=2)+'\n')
        upload(path,path.name,digest(path))
    previous={run['id'] for run in api('/actions/workflows/assemble-test-nsp.yml/runs?per_page=5')['workflow_runs']}
    api('/actions/workflows/assemble-test-nsp.yml/dispatches',{'ref':'main','inputs':{'release_id':str(args.draft)}},method='POST')
    print('Assembly dispatched; waiting for verified single-file release',flush=True)
    run_id=None
    for attempt in range(180):
        runs=api('/actions/workflows/assemble-test-nsp.yml/runs?per_page=5')['workflow_runs']
        if run_id is None:
            candidates=[run for run in runs if run['id'] not in previous and run['event']=='workflow_dispatch']
            if candidates: run_id=candidates[0]['id']; print('Actions run:',candidates[0]['html_url'],flush=True)
        run=next((r for r in runs if r['id']==run_id),None)
        if run and run['status']=='completed':
            assert run['conclusion']=='success','Assembly failed: '+run['html_url']
            break
        time.sleep(10)
    else: raise RuntimeError('Assembly did not finish; draft preserved')
    published=api('/releases/'+str(args.draft))
    assert not published['draft'] and published['prerelease']
    assert len(published['assets'])==1,'Temporary transfer assets were not removed'
    asset=published['assets'][0]
    assert asset['name']==args.nsp.name and asset['size']==report['bytes'] and asset.get('digest')=='sha256:'+report['sha256']
    result={'release':published['html_url'],'asset':asset['browser_download_url'],'sha256':report['sha256'],'bytes':asset['size'],'workflow_run':run_id}
    args.nsp.with_suffix('.github.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Published verified NSP:',published['html_url'],flush=True)

if __name__=='__main__': main()
