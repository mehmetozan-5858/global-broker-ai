const CACHE='global-broker-shell-v2';
const SHELL=['/launch.html','/icon.svg','/manifest.webmanifest'];

self.addEventListener('install',event=>{
  event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL)).then(()=>self.skipWaiting()));
});

self.addEventListener('activate',event=>{
  event.waitUntil(
    caches.keys()
      .then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))))
      .then(()=>self.clients.claim())
  );
});

async function rootNavigation(request){
  const url=new URL(request.url);
  if(url.searchParams.get('boot')==='1') return fetch(request,{cache:'no-store'});
  try{
    const network=fetch(request,{cache:'no-store'});
    const timeout=new Promise((_,reject)=>setTimeout(()=>reject(new Error('cold-start-timeout')),900));
    return await Promise.race([network,timeout]);
  }catch(e){
    const cached=await caches.match('/launch.html');
    return cached || fetch(request,{cache:'no-store'});
  }
}

self.addEventListener('fetch',event=>{
  const request=event.request;
  const url=new URL(request.url);

  if(request.mode==='navigate' && url.origin===self.location.origin){
    if(url.pathname==='/'){
      event.respondWith(rootNavigation(request));
      return;
    }
    if(url.pathname==='/app' || url.pathname==='/account' || url.pathname==='/security' || url.pathname.startsWith('/web/')){
      event.respondWith(fetch(request,{cache:'no-store'}));
      return;
    }
  }

  if(request.method==='GET' && url.origin===self.location.origin){
    if(url.pathname.startsWith('/web/') || url.pathname.startsWith('/api/') || url.pathname.startsWith('/data/')){
      event.respondWith(fetch(request,{cache:'no-store'}));
      return;
    }
    event.respondWith(fetch(request).catch(()=>caches.match(request)));
  }
});
