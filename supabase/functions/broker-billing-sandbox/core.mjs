const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const id=(prefix,value)=>typeof value==='string'&&new RegExp('^'+prefix+'_[a-z0-9]{26}$').test(value);
const PLANS={sector:8900,multi:17900,global:34900};
const ORIGIN='https://broker.aivisibilityworks.com';
const enc=new TextEncoder();
export function configuration(env){
 let catalog={};try{catalog=JSON.parse(env.GB_BROKER_SANDBOX_PRICES||'{}')}catch{}
 const prices=Object.values(catalog);
 const valid=Object.keys(catalog).length===3&&Object.keys(PLANS).every(k=>id('pri',catalog[k]?.price_id)&&id('pro',catalog[k]?.product_id))
 &&new Set(prices.map(x=>x.price_id)).size===3&&new Set(prices.map(x=>x.product_id)).size===3;
 const enabled=env.GB_BROKER_SANDBOX_ENABLED==='true'&&valid
 &&/^pdl_sdbx_apikey_[a-zA-Z0-9_]+$/.test(env.GB_BROKER_SANDBOX_API_KEY||'')
 &&/^test_[a-zA-Z0-9]+$/.test(env.GB_BROKER_SANDBOX_CLIENT_TOKEN||'')
 &&Boolean(env.GB_BROKER_SANDBOX_WEBHOOK_SECRET&&env.SUPABASE_SERVICE_ROLE_KEY&&env.SUPABASE_URL&&env.SUPABASE_ANON_KEY);
 return {enabled,catalog:valid?catalog:{}};
}
export async function verifySignature(raw,header,secret,now=Date.now()){
 if(!secret||typeof header!=='string'||header.length>2048)return false;
 const fields=header.split(';').map(x=>x.trim().split('='));
 const timestamps=fields.filter(x=>x[0]==='ts');
 if(timestamps.length!==1||!/^\d{1,12}$/.test(timestamps[0][1]||''))return false;
 const ts=timestamps[0][1];if(!Number.isSafeInteger(Number(ts))||Math.abs(now/1000-Number(ts))>5)return false;
 const payload=new Uint8Array(enc.encode(ts+':').length+raw.length);payload.set(enc.encode(ts+':'));payload.set(raw,enc.encode(ts+':').length);
 const key=await crypto.subtle.importKey('raw',enc.encode(secret),{name:'HMAC',hash:'SHA-256'},false,['verify']);
 for(const [,value] of fields.filter(x=>x[0]==='h1')){
  if(!/^[a-f0-9]{64}$/i.test(value||''))continue;
  const bytes=Uint8Array.from(value.match(/../g),x=>parseInt(x,16));
  if(await crypto.subtle.verify('HMAC',key,bytes,payload))return true;
 }
 return false;
}
export async function receiptProjection(event,now=Date.now()){
 if(!id('evt',event?.event_id)||!Number.isFinite(Date.parse(event?.occurred_at))||Date.parse(event.occurred_at)>now+300000)throw Error('invalid_event');
 if(event.event_type!=='transaction.completed')return null;
 const d=event.data,m=d?.custom_data;
 if(m?.source!=='global-broker-sandbox'||!UUID.test(m.intent_id||'')||d.status!=='completed'||!id('txn',d.id)||d.currency_code!=='USD')throw Error('invalid_context');
 if(!Array.isArray(d.items)||d.items.length!==1)throw Error('invalid_items');
 const item=d.items[0],price=item.price,amount=d.details?.totals?.total;
 if(item.quantity!==1||!id('pri',price?.id)||!id('pro',price.product_id)||price.billing_cycle?.interval!=='month'||price.billing_cycle?.frequency!==1
 ||price.unit_price?.currency_code!=='USD'||typeof amount!=='string'||!/^\d{1,9}$/.test(amount)||!Object.values(PLANS).includes(Number(amount))
 ||price.unit_price.amount!==amount)throw Error('invalid_amount_or_price');
 const receipt={environment:'sandbox',event_type:event.event_type,event_id:event.event_id,event_at:new Date(event.occurred_at).toISOString(),intent_id:m.intent_id,
 transaction_id:d.id,price_id:price.id,product_id:price.product_id,amount_minor:Number(amount),currency:'USD'};
 const digest=await crypto.subtle.digest('SHA-256',enc.encode(JSON.stringify(receipt)));
 receipt.projection_hash=Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
 return receipt;
}
async function boundedBody(req,limit){
 if(Number(req.headers.get('content-length'))>limit)throw Error('payload_too_large');
 const reader=req.body?.getReader();if(!reader)return new Uint8Array();
 const parts=[];let size=0;
 try{while(true){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>limit){await reader.cancel();throw Error('payload_too_large')}parts.push(value)}}finally{reader.releaseLock()}
 const bytes=new Uint8Array(size);let offset=0;for(const p of parts){bytes.set(p,offset);offset+=p.length}return bytes;
}
export function createHandler({env,fetchImpl=fetch,now=Date.now}={}){
 return async function handle(req){
  const path=new URL(req.url).pathname.split('/').pop(),origin=req.headers.get('origin');
  const cors=origin===ORIGIN?{'Access-Control-Allow-Origin':ORIGIN,'Access-Control-Allow-Headers':'authorization,content-type','Access-Control-Allow-Methods':'POST,OPTIONS','Vary':'Origin'}:{};
  const json=(status,body)=>Response.json(body,{status,headers:{'Cache-Control':'private, no-store','Referrer-Policy':'no-referrer',...cors}});
  if(req.method==='OPTIONS')return origin===ORIGIN?new Response(null,{status:204,headers:cors}):json(403,{error:'origin_denied'});
  if(req.method!=='POST')return json(405,{error:'method_not_allowed'});
  const conf=configuration(env);
  if(!conf.enabled)return json(404,{error:'sandbox_unavailable'});
  async function call(url,options={}){return fetchImpl(url,{...options,signal:AbortSignal.timeout(8000)})}
  async function rpc(name,body,token=env.SUPABASE_SERVICE_ROLE_KEY){
   const r=await call(env.SUPABASE_URL+'/rest/v1/rpc/'+name,{method:'POST',headers:{apikey:token===env.SUPABASE_SERVICE_ROLE_KEY?env.SUPABASE_SERVICE_ROLE_KEY:env.SUPABASE_ANON_KEY,Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify(body)});
   if(!r.ok)throw Error('storage_unavailable');return r.json();
  }
  if(path==='webhook'){
   try{
    const raw=await boundedBody(req,262144);
    if(!await verifySignature(raw,req.headers.get('paddle-signature'),env.GB_BROKER_SANDBOX_WEBHOOK_SECRET,now()))return json(401,{error:'signature_invalid'});
    let event;try{event=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(raw))}catch{return json(400,{error:'invalid_json'})}
    let receipt;try{receipt=await receiptProjection(event,now())}catch{return json(400,{error:'receipt_invalid'})}
    if(!receipt)return json(200,{ignored:true});
    return json(200,await rpc('gb_record_sandbox_billing',{p_receipt:receipt}));
   }catch(error){return json(error.message==='payload_too_large'?413:503,{error:'receipt_not_recorded'})}
  }
  if(!['checkout','workspace'].includes(path))return json(404,{error:'not_found'});
  if(origin!==ORIGIN)return json(403,{error:'origin_denied'});
  const auth=req.headers.get('authorization')||'';if(!/^Bearer [^\s]+$/.test(auth)||auth.length>12000)return json(401,{error:'verified_account_required'});
  const token=auth.slice(7);let intent,claim;
  try{
   const session=await call(env.SUPABASE_URL+'/auth/v1/user',{headers:{apikey:env.SUPABASE_ANON_KEY,Authorization:auth}});
   if(!session.ok)return json(401,{error:'verified_account_required'});
   const user=await session.json();if(!UUID.test(user.id||'')||!user.email_confirmed_at)return json(401,{error:'verified_account_required'});
   if(path==='workspace')return json(200,{...await rpc('gb_sandbox_billing_workspace',{},token),checkout_enabled:true});
   let body;try{body=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(await boundedBody(req,4096)))}catch(e){return json(e.message==='payload_too_large'?413:400,{error:'invalid_request'})}
   if(!UUID.test(body?.request_id||'')||Object.keys(body).length!==1)return json(400,{error:'invalid_request'});
   intent=await rpc('gb_prepare_sandbox_billing',{p_request_id:body.request_id},token);
   if(!UUID.test(intent.intent_id||'')||!Object.hasOwn(PLANS,intent.plan_id)||intent.amount_minor!==PLANS[intent.plan_id]||intent.currency!=='USD')throw Error('context_mismatch');
   const price=conf.catalog[intent.plan_id];
   const catalogResponse=await call('https://sandbox-api.paddle.com/prices/'+price.price_id,{headers:{Authorization:'Bearer '+env.GB_BROKER_SANDBOX_API_KEY,'Paddle-Version':'1'}});
   const catalogData=(await catalogResponse.json())?.data;
   if(!catalogResponse.ok||catalogData?.id!==price.price_id||catalogData.product_id!==price.product_id||catalogData.status!=='active'||catalogData.unit_price?.amount!==String(intent.amount_minor)||catalogData.unit_price?.currency_code!=='USD'||catalogData.billing_cycle?.interval!=='month'||catalogData.billing_cycle?.frequency!==1)throw Error('provider_catalog_mismatch');
   claim=await rpc('gb_claim_sandbox_billing',{p_intent_id:intent.intent_id,p_price_id:price.price_id,p_product_id:price.product_id});
   const result=transactionId=>json(200,{environment:'sandbox',transaction_id:transactionId,client_token:env.GB_BROKER_SANDBOX_CLIENT_TOKEN,production_access_changed:false});
   if(claim.claimed!==true)return claim.state==='created'&&id('txn',claim.transaction_id)?result(claim.transaction_id):json(409,{error:'creation_requires_review'});
   if(!UUID.test(claim.claim_id||''))throw Error('claim_missing');
   const response=await call('https://sandbox-api.paddle.com/transactions',{method:'POST',headers:{Authorization:'Bearer '+env.GB_BROKER_SANDBOX_API_KEY,'Content-Type':'application/json','Paddle-Version':'1'},body:JSON.stringify({items:[{price_id:price.price_id,quantity:1}],currency_code:'USD',collection_mode:'automatic',custom_data:{source:'global-broker-sandbox',intent_id:intent.intent_id}})});
   const payload=await response.json();if(!response.ok||!id('txn',payload?.data?.id))throw Error('provider_unavailable');
   const stored=await rpc('gb_finish_sandbox_billing',{p_intent_id:intent.intent_id,p_claim_id:claim.claim_id,p_transaction_id:payload.data.id});
   if(stored.stored!==true)throw Error('binding_failed');return result(payload.data.id);
  }catch(error){
   if(intent&&claim?.claimed===true&&UUID.test(claim.claim_id||'')){try{await rpc('gb_finish_sandbox_billing',{p_intent_id:intent.intent_id,p_claim_id:claim.claim_id,p_transaction_id:null})}catch{}}
   return json(503,{error:'sandbox_temporarily_unavailable'});
  }
 };
}
