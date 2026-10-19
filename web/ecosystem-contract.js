(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.BrokerEcosystem=factory();})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
var sectors=['Otel / Konaklama','Restoran / Kafe','Sağlık','Hukuk','Emlak','Otomotiv','E-ticaret','Tekstil / Giyim','Eğitim','Turizm','B2B / Sanayi','Diğer'];
var destinations={visibility:'https://www.aivisibilityworks.com/yeni-musteri',broker:'https://global-broker-ai-visibility2.vercel.app/web/ecosystem.html'};
function text(v,max){return typeof v==='string'?v.replace(/[\u0000-\u001f\u007f]/g,'').trim().slice(0,max):'';}
function website(v){var raw=text(v,300);if(!raw)return '';try{var u=new URL(raw);if(!/^https?:$/.test(u.protocol)||u.username||u.password||!u.hostname.includes('.')||/^(localhost|127\.|0\.|10\.|192\.168\.|169\.254\.)/.test(u.hostname)||/\.(local|internal)$/.test(u.hostname))return '';u.hash='';u.search='';return u.href;}catch(e){return '';}}
function clean(v){v=v&&typeof v==='object'&&!Array.isArray(v)?v:{};return {businessName:text(v.businessName,160),website:website(v.website),country:text(v.country,120),sector:sectors.indexOf(v.sector)!==-1?v.sector:''};}
function build(fields,destination){if(!Object.prototype.hasOwnProperty.call(destinations,destination))throw Error('Geçersiz hedef');var data=clean(fields);if(!data.businessName)throw Error('İşletme adını girin.');if(text(fields.website,300)&&!data.website)throw Error('Geçerli bir http/https işletme sitesi girin.');var u=new URL(destinations[destination]);u.hash='business='+encodeURIComponent(JSON.stringify({version:1,source:destination==='visibility'?'global-broker':'ai-visibility',business:data}));return u.href;}
function parse(hash){if(typeof hash!=='string'||hash.length>6000||hash.indexOf('#business=')!==0)return null;try{var v=JSON.parse(decodeURIComponent(hash.slice(10)));if(v.version!==1||['global-broker','ai-visibility'].indexOf(v.source)===-1)return null;var data=clean(v.business);return data.businessName?{source:v.source,business:data}:null;}catch(e){return null;}}
return {sectors:sectors,clean:clean,build:build,parse:parse};
});
