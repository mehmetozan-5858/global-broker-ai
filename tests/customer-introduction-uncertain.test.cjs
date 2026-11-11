const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../web/customer-portal.js'),'utf8');
const begin=source.indexOf('async function requestIntroduction('),end=source.indexOf('\nfunction mount(',begin);
assert.ok(begin>=0&&end>begin,'requestIntroduction function found');
const fn=source.slice(begin,end);
async function run({response,throws=false}={}){
 let calls=0;
 const credit={textContent:'unchanged'};
 const state={};
 const context={requestState:state,accessState:{entitlement:{contact_credits_remaining:3}},token:()=> 'fixture-token',
  document:{getElementById:id=>id==='cpCredits'?credit:null},
  statusLabel:status=>status,
  fetch:async()=>{calls++;if(throws)throw Error('fixture network');return {ok:true,json:async()=>response}}};
 vm.runInNewContext(fn+'\nthis.execute=requestIntroduction;',context);
 const button={disabled:false,textContent:'start'},box={textContent:''};
 await context.execute({opportunity_id:'fixture-opportunity'},button,box);
 return {state,credit,button,box,calls,access:context.accessState};
}
test('confirmed response records request and new remaining credits',async()=>{
 const x=await run({response:{status:'INTRODUCTION_REQUESTED',request_id:'req-good',opportunity_id:'fixture-opportunity',request_status:'requested',credits_remaining:2}});
 assert.equal(x.state['fixture-opportunity'].request_id,'req-good');
 assert.equal(x.credit.textContent,'2');
 assert.equal(x.button.disabled,true);
});
for(const [name,response] of Object.entries({
 missing_id:{status:'INTRODUCTION_REQUESTED',opportunity_id:'fixture-opportunity',request_status:'requested',credits_remaining:2},
 wrong_opportunity:{status:'INTRODUCTION_REQUESTED',request_id:'req',opportunity_id:'other',request_status:'requested',credits_remaining:2},
 wrong_status:{status:'FAILED',request_id:'req',opportunity_id:'fixture-opportunity',request_status:'requested',credits_remaining:2},
 unknown_state:{status:'INTRODUCTION_REQUESTED',request_id:'req',opportunity_id:'fixture-opportunity',request_status:'mystery',credits_remaining:2},
 bad_credits:{status:'INTRODUCTION_REQUESTED',request_id:'req',opportunity_id:'fixture-opportunity',request_status:'requested',credits_remaining:-1}
})){
 test('unconfirmed '+name+' never creates success or enables duplicate submission',async()=>{
  const x=await run({response});
  assert.deepEqual(Object.keys(x.state),[]);
  assert.equal(x.access.entitlement.contact_credits_remaining,3);
  assert.equal(x.credit.textContent,'unchanged');
  assert.equal(x.button.disabled,true);
  assert.match(x.box.textContent,/sonucu doğrulanamadı/);
 });
}
test('network uncertainty does not enable duplicate credit spending',async()=>{
 const x=await run({throws:true});
 assert.deepEqual(Object.keys(x.state),[]);
 assert.equal(x.button.disabled,true);
 assert.match(x.box.textContent,/ulaşıp ulaşmadığı bilinmiyor/);
});
