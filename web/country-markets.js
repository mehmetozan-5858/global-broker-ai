/* Country-first procurement navigation. No fabricated product, quantity or eligibility. */
(function(){
"use strict";
var gulf=["Suudi Arabistan","Birleşik Arap Emirlikleri","Katar","Kuveyt","Umman","Bahreyn","Yemen"];
var aliases={
"SA":"Suudi Arabistan","SAU":"Suudi Arabistan","Saudi Arabia":"Suudi Arabistan","Kingdom of Saudi Arabia":"Suudi Arabistan",
"AE":"Birleşik Arap Emirlikleri","ARE":"Birleşik Arap Emirlikleri","United Arab Emirates":"Birleşik Arap Emirlikleri","UAE":"Birleşik Arap Emirlikleri",
"QA":"Katar","QAT":"Katar","Qatar":"Katar","KW":"Kuveyt","KWT":"Kuveyt","Kuwait":"Kuveyt",
"OM":"Umman","OMN":"Umman","Oman":"Umman","BH":"Bahreyn","BHR":"Bahreyn","Bahrain":"Bahreyn",
"YE":"Yemen","YEM":"Yemen","Yemen":"Yemen",
"TR":"Türkiye","TUR":"Türkiye","Turkey":"Türkiye","Türkiye":"Türkiye",
"CN":"Çin","CHN":"Çin","China":"Çin","GH":"Gana","GHA":"Gana","Ghana":"Gana",
"BE":"Belçika","BEL":"Belçika","Belgium":"Belçika",
"MK":"Kuzey Makedonya","MKD":"Kuzey Makedonya","North Macedonia":"Kuzey Makedonya"
};
function normalized(c){return aliases[String(c||"").trim()]||String(c||"Bilinmiyor").trim();}
function cityOf(o){var x=pick(o,["place-of-performance-city-lot","place_of_performance_city","buyer_city","delivery_city","city","project_city","delivery_location","region","project_location"]);return txt(x).trim()||"Şehir belirtilmemiş";}
function classification(o){
 var x=txt(pick(o,["procurement_type","contract_type","notice-type","category","procurement_category","type"])).toLowerCase();
 if(/service|consult|works|construction|hizmet|danışman|işçilik|personnel/.test(x))return "Hizmet / yapım";
 if(/goods|supply|supplies|mal alımı|equipment|ürün|tedarik/.test(x))return "Mal alımı";
 var t=(title(o)+" "+productText(o)).toLowerCase();
 if(/consultant|consultancy|engineer|mühendis|danışmanlık|personel|service|hizmet alımı|construction|inşaat işi/.test(t))return "Hizmet / yapım";
 return "Tür doğrulanmalı";
}
function card(o){
 var idx=(DATA.opportunities||[]).indexOf(o),st=status(o);
 var p=productText(o)||title(o);
 return '<button type="button" class="market-item" onclick="openOpp('+idx+')">'+
 '<span class="market-item-title">'+esc(p.slice(0,170))+'</span>'+
 '<span class="market-meta">'+esc(classification(o))+' · '+esc(source(o))+'</span>'+
 '<span class="market-facts"><b>Miktar:</b> '+esc(quantity(o)||"İlanda belirtilmemiş")+
 ' <b>Son tarih:</b> '+esc(deadline(o)||"Belirtilmemiş")+'</span>'+
 '<span class="market-meta">Dosya '+st.score+'/6 · '+(hasDocs(o)?"Kaynak bağlantısı var":"Belge bağlantısı yok")+'</span></button>';
}
function countryBlock(c,rows,open){
 var cities={};rows.forEach(function(o){var name=cityOf(o);(cities[name]||(cities[name]=[])).push(o)});
 var keys=Object.keys(cities).sort(function(a,b){return a.localeCompare(b,"tr")});
 var content=keys.map(function(name){return '<details class="market-city" '+(keys.length===1&&open?'open':'')+'><summary>'+esc(name)+' <small>'+cities[name].length+' talep</small></summary><div class="market-items">'+cities[name].map(card).join("")+'</div></details>'}).join("");
 return '<details class="market-country" data-market-country="'+esc(c)+'" '+(open?'open':'')+'><summary>'+esc(c)+' <small>'+rows.length+' talep</small></summary>'+ (content||'<div class="market-empty">Bu ülkeden doğrulanmış yeni talep henüz bulunmadı.</div>')+'</details>';
}
function renderCountryList(){
 var rows=filtered(),box=document.getElementById("list");if(!box)return;
 document.getElementById("resultCount").textContent=rows.length+" fırsat · Ülke → şehir → alım talebi";
 var previouslyOpen={};box.querySelectorAll("details.market-country[open]").forEach(function(d){previouslyOpen[d.getAttribute("data-market-country")]=true});
 var groups={};rows.forEach(function(o){var c=normalized(country(o));(groups[c]||(groups[c]=[])).push(o)});
 var hasActiveFilters=!!(document.getElementById("q").value||document.getElementById("country").value||document.getElementById("source").value||document.getElementById("quality").value||quick!=="all");
 var gulfRows=gulf.map(function(c){return countryBlock(c,groups[c]||[],!!previouslyOpen[c])}).join("");
 var rest=Object.keys(groups).filter(function(c){return gulf.indexOf(c)<0}).sort(function(a,b){return a.localeCompare(b,"tr")});
 var other=rest.map(function(c){return countryBlock(c,groups[c],!!previouslyOpen[c])}).join("");
 box.innerHTML='<div class="market-region"><h3>Arap Yarımadası ve Körfez</h3><p>Ülkeyi, ardından şehri açarak gerçek talepleri incele.</p>'+gulfRows+'</div>'+
 '<div class="market-region"><h3>Diğer Ülkeler</h3>'+(other||'<div class="market-empty">'+(hasActiveFilters?"Filtreye uygun kayıt yok.":"Henüz kayıt yok.")+'</div>')+'</div>';
}
var style=document.createElement("style");style.textContent=
".market-region{background:#0b2233;border:1px solid #31536a;border-radius:14px;padding:12px;margin-bottom:12px}"+
".market-region h3{font-size:16px;margin:2px 0 6px;color:#e6b45b}.market-region p{font-size:12px;color:#a9bfcc;margin:0 0 12px}"+
".market-country,.market-city{border:1px solid #31536a;border-radius:10px;margin:8px 0;overflow:hidden}"+
".market-country>summary,.market-city>summary{cursor:pointer;padding:12px;background:#123247;font-weight:750;list-style:none;display:flex;justify-content:space-between;gap:8px}"+
".market-city>summary{background:#0b293b;font-size:13px}.market-country summary::-webkit-details-marker,.market-city summary::-webkit-details-marker{display:none}"+
".market-country summary small,.market-city summary small{font-size:11px;color:#a9bfcc;white-space:nowrap}"+
".market-city{margin:8px}.market-items{padding:8px}.market-item{display:block;width:100%;text-align:left;border:1px solid #31536a;background:#102c40;color:#f5f7fa;border-radius:10px;padding:11px;margin-bottom:8px;cursor:pointer}"+
".market-item-title{display:block;font-weight:750;line-height:1.4;margin-bottom:5px}.market-meta,.market-facts{display:block;font-size:12px;color:#b7cad6;line-height:1.6}.market-facts b{color:#e6b45b}.market-empty{padding:12px;color:#a9bfcc;font-size:12px}";
document.head.appendChild(style);
window.renderList=renderCountryList;
})();