const {test}=require('node:test'),assert=require('node:assert/strict');
const {requestJSON}=require('../web/quote-evidence.js');
async function scenario(t,fetcher,check){
 let abortTimer,cleared=false;
 t.mock.method(global,'setTimeout',fn=>{abortTimer=fn;return 123});
 t.mock.method(global,'clearTimeout',id=>{assert.equal(id,123);cleared=true});
 t.mock.method(global,'fetch',fetcher);
 await check(()=>abortTimer());assert(cleared,'timer must be cleared');
}
test('quote RPC aborts stalled headers and preserves request body',async t=>{
 await scenario(t,async(url,options)=>{assert.equal(options.body,'{"p_request_id":"same-id"}');return new Promise((resolve,reject)=>options.signal.addEventListener('abort',()=>reject(Error('aborted'))))},async abort=>{const pending=requestJSON('/fixture',{body:'{"p_request_id":"same-id"}'});abort();await assert.rejects(pending,{message:'timeout'})});
});
test('quote RPC timeout includes stalled JSON body',async t=>{
 let bodyStarted;
 const started=new Promise(resolve=>bodyStarted=resolve);
 await scenario(t,async(url,options)=>({ok:true,status:200,json:()=>{bodyStarted();return new Promise((resolve,reject)=>options.signal.addEventListener('abort',()=>reject(Error('aborted'))))}}),async abort=>{const pending=requestJSON('/fixture',{});await started;abort();await assert.rejects(pending,{message:'timeout'})});
});
test('quote RPC returns JSON and clears timer',async t=>{
 await scenario(t,async()=>({ok:true,status:200,json:async()=>({status:'pending_review'})}),async()=>assert.deepEqual(await requestJSON('/fixture',{}),{status:'pending_review'}));
});
for(const [status,message] of [[401,'auth'],[403,'auth'],[409,'stale'],[503,'request']])test('quote RPC maps HTTP '+status+' before parsing body',async t=>{
 await scenario(t,async()=>({ok:false,status,json:()=>{throw Error('must not parse')}}),async()=>assert.rejects(requestJSON('/fixture',{}),{message}));
});
