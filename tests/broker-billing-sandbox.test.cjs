const test=require('node:test'),assert=require('node:assert/strict'),{createHmac}=require('node:crypto');
const mod=import('../supabase/functions/broker-billing-sandbox/core.mjs');
const user='11111111-1111-4111-8111-111111111111',intent='22222222-2222-4222-8222-222222222222',request='33333333-3333-4333-8333-333333333333',claim='44444444-4444-4444-8444-444444444444',suffix='0'.repeat(26),now=1760000000000;
const env={GB_BROKER_SANDBOX_ENABLED:'true',GB_BROKER_SANDBOX_API_KEY:'pdl_sdbx_apikey_fixture',GB_BROKER_SANDBOX_CLIENT_TOKEN:'test_fixture',GB_BROKER_SANDBOX_WEBHOOK_SECRET:'synthetic-endpoint-secret',SUPABASE_URL:'https://example.supabase.co',SUPABASE_ANON_KEY:'public-fixture',SUPABASE_SERVICE_ROLE_KEY:'service-fixture',GB_BROKER_SANDBOX_PRICES:JSON.stringify(Object.fromEntries(['sector','multi','global'].map((p,i)=>[p,{price_id:'pri_'+String(i).repeat(26),product_id:'pro_'+String(i).repeat(26)}])))};
function event(){return {event_id:'evt_'+suffix,event_type:'transaction.completed',occurred_at:new Date(now).toISOString(),data:{id:'txn_'+suffix,status:'completed',currency_code:'USD',custom_data:{source:'global-broker-sandbox',intent_id:intent},items:[{quantity:1,price:{id:'pri_'+suffix,product_id:'pro_'+suffix,billing_cycle:{interval:'month',frequency:1},unit_price:{amount:'8900',currency_code:'USD'}}}],details:{totals:{total:'8900'}}}}}
function signature(raw,ts=now/1000){return 'ts='+ts+';h1='+createHmac('sha256',env.GB_BROKER_SANDBOX_WEBHOOK_SECRET).update(ts+':'+raw).digest('hex')}
function req(path,body={},headers={}){return new Request('https://example.supabase.co/functions/v1/broker-billing-sandbox/'+path,{method:'POST',headers:{origin:'https://broker.aivisibilityworks.com',authorization:'Bearer owner-fixture','content-type':'application/json',...headers},body:typeof body==='string'?body:JSON.stringify(body)})}
function fixture({failProvider=false,failBinding=false,claimLost=false}={}){
 const calls=[];let state='prepared',providerCalls=0;
 const fetchImpl=async(url,options={})=>{
  calls.push({url,body:options.body?JSON.parse(options.body):null,headers:options.headers});
  if(url.endsWith('/auth/v1/user'))return Response.json({id:user,email_confirmed_at:'2026-01-01'});
  if(url.includes('gb_prepare_sandbox_billing'))return Response.json({intent_id:intent,plan_id:'sector',amount_minor:8900,currency:'USD',state});
  if(url.includes('gb_claim_sandbox_billing')){if(state!=='prepared')return Response.json({claimed:false,state,transaction_id:state==='created'?'txn_'+suffix:null});state='creating';if(claimLost)throw Error('ambiguous_claim');return Response.json({claimed:true,claim_id:claim});}
  if(url.startsWith('https://sandbox-api.paddle.com/prices/'))return Response.json({data:{id:'pri_'+suffix,product_id:'pro_'+suffix,status:'active',unit_price:{amount:'8900',currency_code:'USD'},billing_cycle:{interval:'month',frequency:1},trial_period:null,unit_price_overrides:[],tax_mode:'internal',quantity:{minimum:1,maximum:100}}});
  if(url==='https://sandbox-api.paddle.com/transactions'){providerCalls++;if(failProvider)throw Error('ambiguous_provider');return Response.json({data:{id:'txn_'+suffix}})}
  if(url.includes('gb_finish_sandbox_billing')){const body=JSON.parse(options.body);if(failBinding&&body.p_transaction_id)throw Error('binding_unavailable');if(state!=='creating')return Response.json({}, {status:409});state=body.p_transaction_id?'created':'uncertain';return Response.json({stored:true})}
  if(url.includes('gb_record_sandbox_billing'))return Response.json({recorded:true,production_access_changed:false});
  if(url.includes('gb_sandbox_billing_workspace'))return Response.json({environment:'sandbox',production_access_changed:false,records:[]});
  throw Error('unexpected URL');
 };
 return {fetchImpl,calls,get providerCalls(){return providerCalls}};
}
test('sandbox requires explicit enablement, dedicated catalog and sandbox-only credentials',async()=>{
 const {configuration}=await mod;assert.equal(configuration(env).enabled,true);
 for(const changed of [{GB_BROKER_SANDBOX_ENABLED:'false'},{GB_BROKER_SANDBOX_API_KEY:'pdl_live_apikey_fixture'},{GB_BROKER_SANDBOX_CLIENT_TOKEN:'live_fixture'},{GB_BROKER_SANDBOX_PRICES:'{}'},{GB_BROKER_SANDBOX_WEBHOOK_SECRET:''}])assert.equal(configuration({...env,...changed}).enabled,false);
 const catalog=JSON.parse(env.GB_BROKER_SANDBOX_PRICES);catalog.multi=catalog.sector;assert.equal(configuration({...env,GB_BROKER_SANDBOX_PRICES:JSON.stringify(catalog)}).enabled,false);
});
test('raw-byte HMAC verifies timestamp, rotating signatures and mutation rejection',async()=>{
 const {verifySignature}=await mod,raw=JSON.stringify(event()),bytes=new TextEncoder().encode(raw),sig=signature(raw);
 assert.equal(await verifySignature(bytes,sig,env.GB_BROKER_SANDBOX_WEBHOOK_SECRET,now),true);
 assert.equal(await verifySignature(bytes,sig+';h1='+'f'.repeat(64),env.GB_BROKER_SANDBOX_WEBHOOK_SECRET,now),true);
 for(const [body,header] of [[new TextEncoder().encode(raw+' '),sig],[bytes,signature(raw,now/1000-6)],[bytes,sig+';ts='+now/1000],[bytes,sig.replace(/h1=.*/,'h1=bad')]])assert.equal(await verifySignature(body,header,env.GB_BROKER_SANDBOX_WEBHOOK_SECRET,now),false);
});
test('receipt projection checks exact test source, price, quantity, cycle and amount',async()=>{
 const {receiptProjection}=await mod;const receipt=await receiptProjection(event(),now);assert.equal(receipt.amount_minor,8900);assert.match(receipt.projection_hash,/^[a-f0-9]{64}$/);assert.equal(Object.keys(receipt).some(k=>/email|user|invoice/.test(k)),false);
 for(const mutate of [e=>e.data.custom_data.source='ai-visibility-production',e=>e.data.items[0].quantity=2,e=>e.data.currency_code='EUR',e=>e.data.details.totals.total='0',e=>e.data.details.totals.total='8900.00',e=>e.data.items[0].price.unit_price.amount='17900',e=>e.data.items.push(e.data.items[0]),e=>e.data.items[0].price.billing_cycle=null,e=>e.data.status='paid',e=>e.occurred_at=new Date(now+600000).toISOString()]){const e=event();mutate(e);await assert.rejects(receiptProjection(e,now));}
 const other=event();other.event_type='subscription.activated';assert.equal(await receiptProjection(other,now),null);
});
test('disabled endpoint and untrusted origin do not read storage or contact provider',async()=>{
 const {createHandler}=await mod;let calls=0;const fetchImpl=async()=>{calls++;throw Error('unreachable')};
 assert.equal((await createHandler({env:{},fetchImpl})(req('checkout'))).status,404);
 assert.equal((await createHandler({env,fetchImpl})(req('checkout',{}, {origin:'https://evil.example'}))).status,403);
 assert.equal((await createHandler({env,fetchImpl})(req('checkout',{}, {authorization:''}))).status,401);assert.equal(calls,0);
});
test('server-bound transaction is reused and client never supplies price or owner',async()=>{
 const {createHandler}=await mod,f=fixture(),handle=createHandler({env,fetchImpl:f.fetchImpl});
 const first=await (await handle(req('checkout',{request_id:request}))).json();assert.equal(first.environment,'sandbox');assert.equal(first.production_access_changed,false);
 const second=await (await handle(req('checkout',{request_id:request}))).json();assert.equal(second.transaction_id,first.transaction_id);assert.equal(f.providerCalls,1);
 const payload=f.calls.find(c=>c.url==='https://sandbox-api.paddle.com/transactions').body;
 assert.deepEqual(payload.custom_data,{source:'global-broker-sandbox',intent_id:intent});assert.deepEqual(payload.items,[{price_id:'pri_'+suffix,quantity:1}]);
 assert.equal((await handle(req('checkout',{request_id:request,amount_minor:1}))).status,400);assert.equal(f.providerCalls,1);
});
test('ambiguous provider, claim or binding failure cannot create a second transaction',async()=>{
 const {createHandler}=await mod;
 for(const failure of [{failProvider:true},{failBinding:true},{claimLost:true}]){
  const f=fixture(failure),handle=createHandler({env,fetchImpl:f.fetchImpl});assert.equal((await handle(req('checkout',{request_id:request}))).status,503);
  assert.equal((await handle(req('checkout',{request_id:request}))).status,409);assert.equal(f.providerCalls,failure.claimLost?0:1);
 }
});
test('unverified owner and altered server context stop before a provider request',async()=>{
 const {createHandler}=await mod;
 for(const invalid of ['owner','context']){
  const f=fixture(),handle=createHandler({env,fetchImpl:async(url,options)=>url.endsWith('/auth/v1/user')&&invalid==='owner'?Response.json({id:user,email_confirmed_at:null}):url.includes('gb_prepare_sandbox_billing')&&invalid==='context'?Response.json({intent_id:intent,plan_id:'sector',amount_minor:1,currency:'USD'}):f.fetchImpl(url,options)});
  assert.equal((await handle(req('checkout',{request_id:request}))).status,invalid==='owner'?401:503);assert.equal(f.providerCalls,0);
 }
});
test('webhook records only verified projections and returns retry on storage rejection',async()=>{
 const {createHandler}=await mod,raw=JSON.stringify(event()),f=fixture(),handle=createHandler({env,fetchImpl:f.fetchImpl,now:()=>now});
 assert.equal((await handle(req('webhook',raw,{'paddle-signature':signature(raw)}))).status,200);
 const stored=f.calls.find(c=>c.url.includes('gb_record_sandbox_billing')).body.p_receipt;assert.equal(stored.transaction_id,'txn_'+suffix);assert.equal(stored.environment,'sandbox');
 const calls=f.calls.length;assert.equal((await handle(req('webhook',raw,{'paddle-signature':'bad'}))).status,401);assert.equal(f.calls.length,calls);
 const fail=createHandler({env,now:()=>now,fetchImpl:async()=>Response.json({}, {status:409})});assert.equal((await fail(req('webhook',raw,{'paddle-signature':signature(raw)}))).status,503);
});
test('oversized and unsupported requests cannot start checkout',async()=>{
 const {createHandler}=await mod,f=fixture(),handle=createHandler({env,fetchImpl:f.fetchImpl});
 assert.equal((await handle(req('checkout','x'.repeat(4097)))).status,413);assert.equal((await handle(req('unknown'))).status,404);
 assert.equal((await handle(new Request('https://example.supabase.co/workspace'))).status,405);assert.equal(f.providerCalls,0);
});

test('provider price metadata is checked before creating a transaction',async()=>{
 const {createHandler}=await mod,f=fixture();
 const handle=createHandler({env,fetchImpl:async(url,options)=>url.startsWith('https://sandbox-api.paddle.com/prices/')?Response.json({data:{id:'pri_'+suffix,product_id:'pro_'+suffix,status:'active',unit_price:{amount:'1',currency_code:'USD'},billing_cycle:{interval:'month',frequency:1}}}):f.fetchImpl(url,options)});
 assert.equal((await handle(req('checkout',{request_id:request}))).status,503);assert.equal(f.providerCalls,0);assert.equal(f.calls.some(c=>c.url.includes('gb_claim_sandbox_billing')),false);
});

test('trial, country override and uncertain tax totals stop before claim or transaction',async()=>{
 const {createHandler}=await mod;
 for(const mutate of [p=>p.trial_period={interval:'day',frequency:14},p=>p.unit_price_overrides=[{country_codes:['DE'],unit_price:{amount:'1',currency_code:'EUR'}}],p=>p.tax_mode='external',p=>delete p.trial_period]){
  const f=fixture();
  const value={id:'pri_'+suffix,product_id:'pro_'+suffix,status:'active',unit_price:{amount:'8900',currency_code:'USD'},billing_cycle:{interval:'month',frequency:1},trial_period:null,unit_price_overrides:[],tax_mode:'internal',quantity:{minimum:1,maximum:100}};
  mutate(value);
  const handle=createHandler({env,fetchImpl:(url,options)=>url.startsWith('https://sandbox-api.paddle.com/prices/')?Promise.resolve(Response.json({data:value})):f.fetchImpl(url,options)});
  assert.equal((await handle(req('checkout',{request_id:request}))).status,503);
  assert.equal(f.providerCalls,0);assert.equal(f.calls.some(c=>c.url.includes('gb_claim_sandbox_billing')),false);
 }
});
