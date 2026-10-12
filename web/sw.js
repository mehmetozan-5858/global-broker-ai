const CACHE='global-broker-shell-v1';
const SHELL=['/launch.html','/icon.svg','/manifest.webmanifest'];

self.addEventListener('install',event=>{
  event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL)).then(()=>self.skipWaiting()));
});

self.addEventListener('activate',event=>{
  event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));
});

async function navigationResponse(request){
  const url=new URL(request.url);
  if(url.searchParams.get('boot')==='1') return fetch(request,{cache:'no-store'});
  try{
    const network=fetch(request,{cache:'no-store'});
    const timeout=new Promise((_,reject)=>setTimeout(()=>reject(new Error('cold-start-timeout')),900));
    return await Promise.race([network,timeout]);
  }catch(e){
    const cached=await caches.match('/launch.html');
    return cached || fetch(request);
  }
}

self.addEventListener('fetch',event=>{
  const request=event.request;
  if(request.mode==='navigate'){
    const url=new URL(request.url);
    if(url.origin===self.location.origin && (url.pathname==='/' || url.pathname==='/app')){
      event.respondWith(navigationResponse(request));
      return;
    }
  }
  if(request.method==='GET'){
    event.respondWith(fetch(request).catch(()=>caches.match(request)));
  }
});
