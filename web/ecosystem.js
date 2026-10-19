(function(){
'use strict';
var c=window.BrokerEcosystem,form=document.getElementById('businessTransfer'),status=document.getElementById('transferStatus');
if(!c||!form)return;
var sector=form.elements.sector;
c.sectors.forEach(function(name){var option=document.createElement('option');option.value=name;option.textContent=name;sector.appendChild(option);});
var incoming=c.parse(location.hash),box=document.getElementById('incomingBusiness');
if(location.hash.indexOf('#business=')===0){history.replaceState(null,'',location.pathname+location.search);}
if(incoming&&incoming.source==='ai-visibility'){
 box.hidden=false;document.getElementById('incomingName').textContent=incoming.business.businessName;
 document.getElementById('applyBusiness').addEventListener('click',function(){Object.keys(incoming.business).forEach(function(k){form.elements[k].value=incoming.business[k];});box.hidden=true;status.textContent='Firma bilgileri forma aktarıldı. Kontrol edip düzenleyebilirsiniz.';});
}
document.getElementById('transferFields').disabled=false;
form.addEventListener('submit',function(e){e.preventDefault();status.textContent='';try{var data={};['businessName','website','country','sector'].forEach(function(k){data[k]=form.elements[k].value;});location.assign(c.build(data,'visibility'));}catch(error){status.textContent=error.message;}});
})();
