const {test}=require('node:test');
const assert=require('node:assert/strict');
const {validateQuote}=require('../web/quote-evidence.js');
const {requestedOpportunity}=require('../web/quote-evidence.js');
const today='2026-10-20';
const quote={counterparty:'Fixture only',reference:'TEST',price_unit:'piece',amount:'10.50',quantity:'25',currency:'usd',quote_date:'2026-10-19',valid_until:'2026-10-20',source_url:'https://example.invalid/quote'};
test('valid and expired evidence can enter review, without approving a quote',()=>{
 assert.deepEqual(validateQuote(quote,today),{});
 assert.deepEqual(validateQuote({...quote,valid_until:'2026-10-19'},today),{});
 assert.deepEqual(validateQuote({...quote,amount:'0.000001',quantity:'999999999999.999999'},today),{});
});
test('rejects invalid calendar dates, future quotes and inverted validity',()=>{
 for(const value of ['2026-02-30','2025-02-29','2026-13-01','0000-01-01','20/10/2026','2026-10-21',''])assert.ok(validateQuote({...quote,quote_date:value},today).quote_date,value);
 assert.ok(validateQuote({...quote,valid_until:'2026-10-18'},today).valid_until);
 assert.deepEqual(validateQuote({...quote,quote_date:'2024-02-29'},today),{});
});
test('rejects zero, negative, exponent, comma and oversized price or quantity',()=>{
 for(const name of ['amount','quantity'])for(const value of ['0','0.000000','-1','1e2','1,25','1000000000000','1.0000001',''])assert.ok(validateQuote({...quote,[name]:value},today)[name],name+': '+value);
});
test('rejects credentialed, insecure, malformed and whitespace document URLs',()=>{
 for(const source_url of ['http://example.invalid/a','https://user:password@example.invalid/a','https://example.invalid/a b','https://example.invalid:99999/a','javascript:alert(1)','https://',''])assert.ok(validateQuote({...quote,source_url},today).source_url,source_url);
 assert.deepEqual(validateQuote({...quote,source_url:'https://example.invalid:443/quote?id=5#page=2'},today),{});
});
test('requires nonblank metadata and a three-letter currency code',()=>{
 for(const name of ['counterparty','reference','price_unit'])assert.ok(validateQuote({...quote,[name]:'  '},today)[name]);
 for(const currency of ['US','123','USDT',''])assert.ok(validateQuote({...quote,currency},today).currency);
});
test('requested opportunity survives authentication only within its bounded lifetime',()=>{
 const now=1000000,saved=JSON.stringify({id:'gb_fixture',at:now-1000});
 assert.equal(requestedOpportunity('?opportunity=gb_new',saved,now),'gb_new');
 assert.equal(requestedOpportunity('',saved,now),'gb_fixture');
 for(const at of [now-900001,now+1,'1000000',null])assert.equal(requestedOpportunity('',JSON.stringify({id:'gb_fixture',at}),now),'');
});
test('malformed or duplicate opportunity identifiers cannot revive older context',()=>{
 const saved=JSON.stringify({id:'gb_old',at:1000});
 for(const search of ['?opportunity=','?opportunity=https://evil.invalid','?opportunity=a&opportunity=b','?opportunity=%3Cscript%3E','?opportunity='+('a'.repeat(201))])assert.equal(requestedOpportunity(search,saved,1001),'');
 for(const value of ['broken','null','{}','[]'])assert.equal(requestedOpportunity('',value,1001),'');
});

test('freight needs distinct endpoints and supported transport scope',()=>{
 const freight={...quote,party:'freight',origin:'Fixture A',destination:'Fixture B',incoterm:'DAP',transport_mode:'road',amount_basis:'shipment_total'};
 assert.deepEqual(validateQuote(freight,today),{});
 for(const name of ['origin','destination','incoterm','transport_mode'])assert.ok(validateQuote({...freight,[name]:''},today)[name]);
 assert.ok(Object.keys(validateQuote({...freight,destination:'fixture a'},today)).length);
 for(const [name,value] of [['incoterm','UNKNOWN'],['transport_mode','unknown']])assert.ok(validateQuote({...freight,[name]:value},today)[name]);
});
