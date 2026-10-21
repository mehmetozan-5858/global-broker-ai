const test=require('node:test');
const assert=require('node:assert/strict');
const contract=require('../web/ecosystem-contract.js');
const fields={businessName:'Örnek & <Firma>',website:'https://example.com/?token=private#secret',country:'Türkiye',sector:'B2B / Sanayi',email:'private@example.com',access_token:'secret'};
test('round trip transfers only four reviewed fields, never tokens or contacts',()=>{
 const url=new URL(contract.build(fields,'visibility'));
 assert.equal(url.origin,'https://www.aivisibilityworks.com');assert.equal(url.search,'');
 const data=contract.parse(url.hash);
 assert.equal(data.source,'global-broker');assert.equal(data.business.website,'https://example.com/');
 assert.deepEqual(Object.keys(data.business).sort(),['businessName','country','sector','website']);
 assert.equal(data.business.businessName,fields.businessName);
 const back=new URL(contract.build(data.business,'broker'));
 assert.equal(back.origin,'https://broker.aivisibilityworks.com');
 assert.equal(contract.parse(back.hash).source,'ai-visibility');
});
test('invalid protocol, credentials, target and malformed fragments fail closed',()=>{
 for(const website of ['javascript:alert(1)','data:text/html,x','https://user:pass@example.com','http://127.0.0.1']){
  assert.throws(()=>contract.build({...fields,website},'visibility'));
 }
 assert.throws(()=>contract.build(fields,'https://evil.example'));
 assert.throws(()=>contract.build({businessName:''},'broker'));
 for(const hash of ['#business=%','', '#business='+encodeURIComponent('{"version":2}'),'#business='+('x'.repeat(6001))])assert.equal(contract.parse(hash),null);
});
test('untrusted object types and unexpected fields cannot enter the profile',()=>{
 const hash='#business='+encodeURIComponent(JSON.stringify({version:1,source:'global-broker',returnUrl:'https://evil.example',business:{businessName:'ACME',website:'javascript:alert(1)',country:{x:'DE'},sector:'malicious'}}));
 assert.deepEqual(contract.parse(hash).business,{businessName:'ACME',website:'',country:'',sector:''});
});

test('shared workspace links use fixed official hosts and preserve role boundaries',()=>{
 assert.equal(contract.links.visibilityPortal,'https://www.aivisibilityworks.com/musteri-panel');
 assert.equal(contract.links.visibilityAdmin,'https://www.aivisibilityworks.com/admin');
 assert.equal(contract.links.brokerPortal,'https://broker.aivisibilityworks.com/customer');
 assert.equal(contract.links.brokerAdmin,'https://broker.aivisibilityworks.com/app');
 for(const value of Object.values(contract.links)){
  const url=new URL(value);assert.equal(url.protocol,'https:');assert.equal(url.search,'');assert.equal(url.hash,'');
 }
 assert.equal(new URL(contract.build(fields,'broker')).pathname,'/web/ecosystem.html');
});
