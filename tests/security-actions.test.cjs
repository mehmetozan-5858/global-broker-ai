const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../web/security.html'),'utf8');
const script=html.match(/<script>\s*(const SB_URL[\s\S]*?)<\/script>/)[1];
function harness(options={}){
 const nodes={},stored=new Map([['gb_access_token','fixture-aal1'],['gb_refresh_token','fixture-refresh']]),calls={challenge:0,verify:0,enroll:0};
 function node(id){return nodes[id]||(nodes[id]={disabled:/\bdisabled\b/.test((html.match(new RegExp('<button id="'+id+'"[^>]*>'))||[''])[0]),value:'',textContent:'',classList:{add(){},remove(){},toggle(){}},removeAttribute(name){delete this[name]}})}
 const mfa={getAuthenticatorAssuranceLevel:async()=>({data:{currentLevel:'aal1'}}),listFactors:async()=>({data:{totp:options.setup?[]:[{id:'fixture-factor',status:'verified'}]}}),challenge:async()=>{calls.challenge++;if(options.challenge)return options.challenge();return {data:{id:'fixture-challenge'}}},verify:async()=>{calls.verify++;if(options.verify)return options.verify();return {data:{access_token:'fixture-aal2',refresh_token:'fixture-refresh'}}},enroll:async()=>{calls.enroll++;if(options.enroll)return options.enroll();return {data:{id:'fixture-new-factor',totp:{qr_code:'data:image/svg+xml,fixture',secret:'SYNTHETIC-SECRET'}}}}};
 const context={supabase:{createClient:()=>({auth:{setSession:async s=>({data:{session:s}}),mfa}})},window:{},localStorage:{getItem:k=>stored.get(k)||'',setItem:(k,v)=>stored.set(k,v)},document:{getElementById:node},location:{search:'',reload(){}},fetch:async()=>({ok:options.valid!==false,json:async()=>({id:'fixture-user'})}),setTimeout(){}};
 vm.createContext(context);vm.runInContext(script,context);
 return {node,calls,stored,ready:()=>new Promise(setImmediate)};
}
test('MFA actions wait for verified server session and factor discovery',async()=>{
 const h=harness();for(const id of ['enroll','verifyEnroll','verifyExisting'])assert.equal(h.node(id).disabled,true);
 await h.ready();assert.equal(h.node('verifyExisting').disabled,false);assert.equal(h.node('verifyEnroll').disabled,true);
 const denied=harness({valid:false});await denied.ready();for(const id of ['enroll','verifyEnroll','verifyExisting'])assert.equal(denied.node(id).disabled,true);
});
test('malformed TOTP code cannot create a challenge or verify request',async()=>{
 const h=harness();await h.ready();for(const code of ['','12345','1234567','abcdef','12 345']){h.node('challengeCode').value=code;await h.node('verifyExisting').onclick();assert.match(h.node('status').textContent,/6 haneli/)}assert.equal(h.calls.challenge,0);assert.equal(h.calls.verify,0);
});
test('double activation creates only one MFA challenge and restores retry after rejection',async()=>{
 let finish;const h=harness({challenge:()=>new Promise(resolve=>finish=resolve),verify:()=>({error:{message:'fixture rejected'}})});await h.ready();h.node('challengeCode').value='123456';
 const first=h.node('verifyExisting').onclick();await h.node('verifyExisting').onclick();assert.equal(h.calls.challenge,1);assert.equal(h.node('verifyExisting').disabled,true);
 finish({data:{id:'fixture-challenge'}});await first;assert.equal(h.calls.verify,1);assert.equal(h.node('verifyExisting').disabled,false);assert.equal(h.stored.get('gb_access_token'),'fixture-aal1');
});
test('network failures show a retry message and never elevate the session',async()=>{
 const h=harness({challenge:()=>{throw Error('synthetic offline')}});await h.ready();h.node('challengeCode').value='123456';await h.node('verifyExisting').onclick();assert.match(h.node('status').textContent,/Bağlantı kurulamadı/);assert.equal(h.node('verifyExisting').disabled,false);assert.equal(h.calls.verify,0);assert.equal(h.stored.get('gb_access_token'),'fixture-aal1');
});
test('enrollment is single flight and successful verification removes codes, QR and secret',async()=>{
 let finish;const h=harness({setup:true,enroll:()=>new Promise(resolve=>finish=resolve)});await h.ready();const first=h.node('enroll').onclick();await h.node('enroll').onclick();assert.equal(h.calls.enroll,1);
 finish({data:{id:'fixture-new-factor',totp:{qr_code:'data:image/svg+xml,fixture',secret:'SYNTHETIC-SECRET'}}});await first;await h.node('enroll').onclick();assert.equal(h.calls.enroll,1);assert.equal(h.node('enroll').disabled,true);assert.equal(h.node('verifyEnroll').disabled,false);
 h.node('code').value='123456';await h.node('verifyEnroll').onclick();assert.equal(h.node('secret').textContent,'');assert.equal(h.node('qr').src,undefined);assert.equal(h.node('code').value,'');assert.equal(h.stored.get('gb_access_token'),'fixture-aal2');assert.equal(h.node('verifyEnroll').disabled,true);
});
