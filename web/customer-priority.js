(function(){
"use strict";
function byId(id){return document.getElementById(id)}
function clickQuality(value){
  var select=byId("cpQuality");
  if(!select)return;
  select.value=String(value);
  select.dispatchEvent(new Event("change",{bubbles:true}));
}
function mount(){
  var panel=byId("customerSearch");
  if(!panel||byId("cpQuickViews"))return false;
  var filters=panel.querySelector(".cp-filters");
  if(!filters)return false;
  var wrap=document.createElement("div");
  wrap.id="cpQuickViews";wrap.className="cp-quick";
  wrap.innerHTML='<span>Hızlı görünüm</span><button type="button" data-q="0">Tüm fırsatlar</button><button type="button" data-q="5">En güçlü</button><button type="button" data-q="6">6/6 tam veri</button>';
  wrap.addEventListener("click",function(e){
    var b=e.target.closest("button[data-q]");if(!b)return;
    Array.prototype.forEach.call(wrap.querySelectorAll("button"),function(x){x.classList.toggle("active",x===b)});
    clickQuality(b.getAttribute("data-q"));
  });
  filters.parentNode.insertBefore(wrap,filters);
  var css=document.createElement("style");
  css.textContent='.cp-quick{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:14px 0 4px}.cp-quick span{font-size:11px;color:#9fb4c1;font-weight:800;margin-right:2px}.cp-quick button{border:1px solid #38627b;background:#0a2234;color:#dbe9f2;border-radius:999px;padding:8px 11px;font:inherit;font-size:11px;font-weight:700;cursor:pointer}.cp-quick button:hover,.cp-quick button.active{background:#d3a04e;color:#081521;border-color:#d3a04e}';
  document.head.appendChild(css);
  var first=wrap.querySelector('button[data-q="0"]');if(first)first.classList.add("active");
  return true;
}
var tries=0,timer=setInterval(function(){tries++;if(mount()||tries>80)clearInterval(timer)},100);
})();
