const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../web/customer-portal.js'),'utf8');
const flush=async()=>{for(let i=0;i<8;i++)await new Promise(r=>setImmediate(r))};
function harness({status=503,payload={},noToken=false,network=false,hung=false,invalidJSON=false}={}){
 const ids=new Map(),all=[],timers=new Map();let timerId=0,feedCalls=0,rpcCalls=0;
 function element(tag){const node={tag,children:[],textContent:'',setAttribute(){},appendChild(child){this.children.push(child)},remove(){ids.delete(this.id)}};Object.defineProperty(node,'id',{get(){return this._id},set(id){this._id=id;ids.set(id,this)}});all.push(node);return node}
 const parent={insertBefore(node){ids.set(node.id,node)}},cards=element('section');cards.id='cards';cards.parentNode=parent;
 const response=(code,data)=>({ok:code>=200&&code<300,status:code,json:async()=>{if(invalidJSON&&code===status)throw Error('PRIVATE SERVER TRACE');return data}});
 const fetch=async(url,opts)=>{
  if(hung)return new Promise((resolve,reject)=>opts.signal.addEventListener('abort',()=>reject(Error('aborted'))));
  if(url.includes('/rpc/')){rpcCalls++;return response(200,url.includes('my_broker_access')?{entitlement:{all_sectors:true},preferences:{}}:[])}
  feedCalls++;if(network)throw Error('PRIVATE NETWORK ERROR');return response(status,payload);
 };
 const context={window:{},document:{getElementById:id=>ids.get(id)||null,createElement:element,head:{appendChild(){}}},localStorage:{getItem:()=>noToken?'':'synthetic-fixture'},fetch,AbortController,setTimeout:(fn,ms)=>{timers.set(++timerId,{fn,ms});return timerId},clearTimeout:id=>timers.delete(id),console};
 vm.runInNewContext(source,context);
 return {ids,all,timers,text:()=>{const walk=n=>n.textContent+' '+n.children.map(walk).join(' ');return walk(ids.get('customerSearch'))},feedCalls:()=>feedCalls,rpcCalls:()=>rpcCalls};
}
for(const [status,label] of [[401,'Yeniden giriş yapın'],[403,'Hesap erişiminizi kontrol edin'],[429,'İstek sınırına ulaşıldı'],[503,'Fırsatlar yüklenemedi']]){
 test('feed status '+status+' is distinct from an empty result',async()=>{const h=harness({status});await flush();assert.match(h.text(),new RegExp(label));assert.doesNotMatch(h.text(),/eşleşen fırsat yok|PRIVATE/);assert.equal(h.timers.size,0);assert.equal(h.feedCalls(),1)});
}
test('missing session prompts login without network calls',async()=>{const h=harness({noToken:true});await flush();assert.match(h.text(),/Yeniden giriş yapın/);assert.equal(h.feedCalls()+h.rpcCalls(),0);assert.equal(h.all.find(n=>n.tag==='a').href,'/account?next=%2Fcustomer')});
test('network errors and malformed successful payloads never become empty lists',async()=>{for(const options of [{network:true},{status:200,payload:{}},{status:200,payload:{opportunities:[null]}},{status:200,invalidJSON:true}]){const h=harness(options);await flush();assert.match(h.text(),/Fırsatlar yüklenemedi/);assert.doesNotMatch(h.text(),/PRIVATE/);assert.equal(h.timers.size,0)}});
test('non-JSON unauthorized response still prompts login',async()=>{const h=harness({status:401,invalidJSON:true});await flush();assert.match(h.text(),/Yeniden giriş yapın/)});
test('bounded access requests abort and release all timers',async()=>{const h=harness({hung:true});assert.ok(h.timers.size>0);for(const timer of [...h.timers.values()]){assert.equal(timer.ms,15000);timer.fn()}await flush();assert.match(h.text(),/Fırsatlar yüklenemedi/);assert.equal(h.timers.size,0)});
test('rapid retry clicks start one additional read and no writes',async()=>{const h=harness();await flush();const retry=h.all.find(n=>n.tag==='button');retry.onclick();retry.onclick();await flush();assert.equal(h.feedCalls(),2);assert.equal(h.rpcCalls(),4);assert.equal(h.timers.size,0);assert.match(h.text(),/Fırsatlar yüklenemedi/)});
