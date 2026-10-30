const test=require('node:test'),assert=require('node:assert/strict');
const modules=Promise.all([import('../scripts/broker-paddle-preflight.mjs'),import('../supabase/functions/broker-billing-sandbox/catalog.mjs')]);
const catalog=Object.fromEntries(['sector','multi','global'].map((plan,index)=>[plan,{price_id:'pri_'+String(index).repeat(26),product_id:'pro_'+String(index).repeat(26)}]));
const amounts={sector:8900,multi:17900,global:34900};
const env={GB_BROKER_SANDBOX_API_KEY:'pdl_sdbx_apikey_fixture',GB_BROKER_SANDBOX_PRICES:JSON.stringify(catalog),GB_BROKER_SANDBOX_CLIENT_TOKEN:'test_fixture',GB_BROKER_SANDBOX_WEBHOOK_SECRET:'private-fixture'};
function price(plan){return {...catalog[plan],id:catalog[plan].price_id,status:'active',unit_price:{amount:String(amounts[plan]),currency_code:'USD'},billing_cycle:{interval:'month',frequency:1},trial_period:null,unit_price_overrides:[],tax_mode:'internal',quantity:{minimum:1,maximum:100}};}

test('missing or production key stops before any provider request',async()=>{
 const [{preflight}]=await modules;
 for(const key of [undefined,'pdl_live_apikey_fixture']){
  const result=await preflight({env:{...env,GB_BROKER_SANDBOX_API_KEY:key},fetchImpl:()=>{throw Error('must not call provider')}});
  assert.equal(result.preflight_passed,false);assert.equal(result.provider_reads,0);
 }
});
test('sandbox preflight only reads dedicated prices and returns no credentials',async()=>{
 const [{preflight}]=await modules;const calls=[];
 const result=await preflight({env,fetchImpl:async(url,options)=>{
  calls.push(url);assert.equal(new URL(url).origin,'https://sandbox-api.paddle.com');assert.equal(options.method,'GET');assert.equal(options.redirect,'error');
  if(url.endsWith('/'))return Response.json({data:{api:{environment:'sandbox'},caller:{account:{id:'fixture'}}}});
  const plan=Object.keys(catalog).find(plan=>url.endsWith(catalog[plan].price_id));return Response.json({data:price(plan)});
 }});
 assert.equal(result.preflight_passed,true);assert.equal(calls.length,4);assert.equal(result.live_settings_changed,false);
 for(const secret of Object.values(env))assert.equal(JSON.stringify(result).includes(secret),false);
});
test('a production response cannot be accepted even with a sandbox-shaped key',async()=>{
 const [{preflight}]=await modules;let calls=0;
 const result=await preflight({env,fetchImpl:async()=>{calls++;return Response.json({data:{api:{environment:'production'},caller:{account:{id:'fixture'}}}})}});
 assert.equal(result.preflight_passed,false);assert.equal(calls,1);
});
test('overrides, trials, external tax, missing metadata and wrong price fail closed',async()=>{
 const [, {matchesSandboxPrice}]=await modules;
 const expected={...catalog.sector,amount_minor:8900};assert.equal(matchesSandboxPrice(price('sector'),expected),true);
 for(const mutate of [p=>p.trial_period={interval:'day',frequency:14},p=>p.unit_price_overrides=[{country_codes:['DE']}],p=>p.tax_mode='external',p=>delete p.trial_period,p=>delete p.unit_price_overrides,p=>p.unit_price.amount='1',p=>p.quantity.minimum=2]){
  const row=price('sector');mutate(row);assert.equal(matchesSandboxPrice(row,expected),false);
 }
});
