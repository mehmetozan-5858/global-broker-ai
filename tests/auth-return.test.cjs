const {test}=require('node:test'),assert=require('node:assert/strict');
const nav=require('../web/auth-return.js');
test('known destinations survive login and MFA links',()=>{for(const target of ['/app','/account','/quote-evidence']){assert.equal(nav.next('?next='+encodeURIComponent(target)),target);assert.equal(nav.next(new URL(nav.security(target),'https://example.invalid').search),target);assert.equal(nav.next(new URL(nav.account(target),'https://example.invalid').search),target)}});
test('external, encoded and malformed destinations are rejected',()=>{for(const value of ['https://evil.invalid','//evil.invalid','/\\evil.invalid','/quote-evidence?token=secret','/quote-evidence#access_token=secret','/quote-evidence/../app','/quote-evidence%00','%2Fquote-evidence','/unknown','javascript:alert(1)']){assert.equal(nav.next('?next='+encodeURIComponent(value)),null,value);assert.equal(nav.security(value),'/security');assert.equal(nav.account(value),'/account')}});
test('navigation without an explicit return destination stays put',()=>{assert.equal(nav.next(''),null);assert.equal(nav.next('?code=fixture'),null);assert.equal(nav.next('?next='),null)});
test('account waits for initialization before enabling login, then preserves the MFA destination',async()=>{
 const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
 const html=fs.readFileSync(path.join(__dirname,'../web/account.html'),'utf8');
 const code=html.match(/<script>\s*(const SB_URL[\s\S]*?)<\/script>/)[1],nodes={},stored=new Map(),assigned=[];
 function element(id){return nodes[id]||(nodes[id]={disabled:/\bdisabled\b/.test((html.match(new RegExp('<button id="'+id+'"[^>]*>'))||[''])[0]),value:'fixture',textContent:'',classList:{add(){},remove(){},toggle(){}},appendChild(){}})}
 let ready;const recoveryReady=new Promise(resolve=>ready=resolve);
 const context={window:{GBAuthReturn:nav,GlobalBrokerRecovery:{start:()=>recoveryReady},GlobalBrokerPricing:{plans:{},sectorClusters:{}}},GBAuthReturn:nav,GlobalBrokerRecovery:{start:()=>recoveryReady},localStorage:{getItem:k=>stored.get(k)||'',setItem:(k,v)=>stored.set(k,v),removeItem:k=>stored.delete(k)},document:{getElementById:element,querySelectorAll:()=>[],createElement:()=>({})},location:{search:'?next=/quote-evidence',assign:p=>assigned.push(p)},URLSearchParams,Set,fetch:async url=>({ok:true,json:async()=>String(url).includes('/token')?{access_token:'fixture',refresh_token:'fixture-refresh'}:String(url).includes('/user_roles')?[{role:'admin'}]:String(url).includes('/auth/v1/user')?{id:'fixture-user'}:{entitlement:{plan_id:'free'},preferences:{}}})};
 vm.createContext(context);vm.runInContext(code,context);
 for(const id of ['login','signup','reset'])assert.equal(element(id).disabled,true,id);
 ready(false);await new Promise(setImmediate);
 for(const id of ['login','signup','reset'])assert.equal(element(id).disabled,false,id);
 await element('login').onclick();assert.deepEqual(assigned,['/security?next=%2Fquote-evidence']);
});
