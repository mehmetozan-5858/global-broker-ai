const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../web/customer-tab-readiness.js'),'utf8');
function node(tag){
 return {tag,children:[],attributes:{},textContent:'',className:'',style:{},parent:null,
  setAttribute(k,v){this.attributes[k]=v},appendChild(child){child.parent=this;this.children.push(child);return child},
  remove(){if(this.parent)this.parent.children=this.parent.children.filter(x=>x!==this)},
  querySelector(selector){return selector==='.gb-customer-readiness'?this.children.find(x=>x.className==='gb-customer-readiness')||null:null}};
}
function harness(){
 const host=node('div'),head=node('head'),visited=[];
 const win={openCard(key){visited.push(key);host.children=[];return key}};
 const doc={head,createElement:node,getElementById:id=>id==='pc'?host:null};
 vm.runInNewContext(source,{window:win,document:doc,setTimeout(){}});
 return {win,host,visited};
}
const sections=['agents','opps','report','settings','markets','buyers','suppliers','pricing','logistics','trade','risk','communication','negotiation','contract','commission','payments'];
test('every commercial tab has honest guidance and exactly one card',()=>{
 const h=harness();
 for(const key of sections){
  h.win.openCard(key,'Fixture');
  const c=h.host.querySelector('.gb-customer-readiness');
  assert.ok(c,'missing '+key);
  assert.equal(h.host.children.length,1);
  assert.match(c.children.at(-1).textContent,/gerçek fırsat/);
  assert.equal(c.children[3].children.length,3);
 }
 assert.deepEqual(h.visited,sections);
});
test('navigation actions route to opportunities or account without writes',()=>{
 const h=harness();
 h.win.openCard('agents');
 const c=h.host.querySelector('.gb-customer-readiness');
 const action=c.children[4];
 assert.equal(action.tag,'button');action.onclick();
 assert.equal(h.visited.at(-1),'opps');
 h.win.openCard('payments');
 const link=h.host.querySelector('.gb-customer-readiness').children[4];
 assert.equal(link.tag,'a');assert.equal(link.href,'/account');assert.equal(link.target,'_top');
});
