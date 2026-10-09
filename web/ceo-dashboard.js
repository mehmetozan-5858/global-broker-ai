/* Global Broker: public-data-only CEO overview. Never exposes internal CEO reports. */
(function(){
"use strict";
function escapeText(v){return String(v==null?"":v).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]})}
function val(o,key){return o&&o[key]!=null?String(o[key]):""}
function route(o){
 var buyer=val(o,"buyer-country").toUpperCase(),supplier=val(o,"supplier-country").toUpperCase();
 var tr=function(s){return ["TR","TUR","TURKEY","TÜRKIYE","TÜRKİYE"].indexOf(s)>=0};
 if(!supplier||!buyer)return "Tedarik yönü belirsiz";
 if(tr(supplier)&&!tr(buyer))return "Türkiye ihracatı";
 if(tr(buyer)&&!tr(supplier))return "Türkiye ithalatı";
 if(tr(supplier)&&tr(buyer))return "Türkiye iç ticareti";
 return "Üçüncü ülke aracılığı";
}
function fresh(o){
 if(o.freshness_status)return o.freshness_status;
 var raw=o["deadline-receipt-tender-date-lot"]||o.deadline_date||"";
 if(!raw||typeof raw!=="string")return "deadline_unknown_review";
 var iso=raw.match(/^\d{4}-\d{2}-\d{2}/);
 if(!iso)return "deadline_unknown_review";
 var today=new Date(),day=new Date(today.getFullYear(),today.getMonth(),today.getDate());
 return new Date(iso[0]+"T00:00:00")<day?"expired":"open_by_date_only";
}
function dataRows(){return Array.isArray(window.FILTERED)?window.FILTERED:(window.DATA&&Array.isArray(window.DATA.opportunities)?window.DATA.opportunities:[])}
function panel(k){
 var rows=dataRows(),out=[],verified=0,expired=0,unknown=0,publicTenders=0,routeCounts={};
 rows.forEach(function(o){
  if(o.buyer_verified===true)verified++;
  if(fresh(o)==="expired")expired++;
  if(fresh(o)==="deadline_unknown_review")unknown++;
  if(["TED","WORLD_BANK","SAM_GOV","UNGM","UNDP"].indexOf(val(o,"source").toUpperCase())>=0)publicTenders++;
  var r=route(o);routeCounts[r]=(routeCounts[r]||0)+1;
 });
 out.push('<div class="note"><b>Gölge Mod — genel fırsat verileri</b><p>Bu görünüm yalnızca yayımlanan fırsat verilerinden hesaplanır. İç CEO dosyası, müşteri iletişim bilgileri ve sözleşme kayıtları burada gösterilmez.</p></div>');
 out.push('<div class="note"><b>Fırsat havuzu:</b> '+rows.length+' · <b>Alıcı doğrulaması işaretli:</b> '+verified+' · <b>Süresi dolan:</b> '+expired+' · <b>Son tarih incelemesi:</b> '+unknown+'</div>');
 if(k==="commission"||k==="pricing"){
  out.push('<div class="note"><b>Komisyon / satış takibi</b><p>Bu ekranda kanıtlanmış komisyon veya tahsilat tutarı bulunmuyor. İşlem bedeli, imzalı aracılık sözleşmesi, ödeme tetikleyicisi ve tahsilat belgesi olmadan gelir gösterilmez.</p><p>Teklif → Sözleşme → İşlem kanıtı → Ödeme şartı → Tahsilat kanıtı</p></div>');
 }else{
  out.push('<div class="note"><b>Resmî kamu alım kaynaklı kayıtlar:</b> '+publicTenders+'<p>İhale ilanı, doğrulanmış özel sektör alım talimatı veya tamamlanmış satış değildir.</p></div>');
  Object.keys(routeCounts).sort().forEach(function(r){out.push('<div class="item"><b>'+escapeText(r)+'</b><p>'+routeCounts[r]+' kayıt</p></div>')});
  if(!rows.length)out.push('<div class="item">Henüz yayımlanmış fırsat bulunamadı.</div>');
 }
 out.push('<div class="note">İletişim, teklif gönderimi, sözleşme imzası ve ödeme işlemleri bu ekranda kapalıdır.</div>');
 return out.join("");
}
var original=window.openTab;
if(typeof original!=="function")return;
window.openTab=function(k){
 original(k);
 if(["ceo","report","commission","pricing"].indexOf(k)<0)return;
 var node=document.getElementById("content");
 if(!node)return;
 var old=node.querySelector("[data-broker-overview]");
 if(old)old.remove();
 var wrap=document.createElement("div");wrap.setAttribute("data-broker-overview","1");
 wrap.innerHTML=panel(k);
 node.insertBefore(wrap,node.firstChild);
};
})();
