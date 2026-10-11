(function(){
  'use strict';
  var OLD=[
    '🔒 Doğrulanmış alıcı — kontrollü tanıştırma ile erişilir',
    'Doğrulanmış alıcı — kontrollü tanıştırma ile erişilir',
    'Doğrulanmış alıcı — üyelik erişim kurallarına tabi'
  ];
  var SAFE='🔒 Alıcı kimliği kontrollü tanıştırma ile paylaşılır';
  function clean(root){
    if(!root)return;
    var walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
    var node;
    while((node=walker.nextNode())){
      var v=node.nodeValue||'';
      for(var i=0;i<OLD.length;i++){
        if(v.indexOf(OLD[i])>=0)v=v.split(OLD[i]).join(SAFE);
      }
      if(v!==node.nodeValue)node.nodeValue=v;
    }
  }
  clean(document.body);
  var obs=new MutationObserver(function(records){
    records.forEach(function(r){
      Array.prototype.forEach.call(r.addedNodes||[],function(n){if(n.nodeType===1||n.nodeType===3)clean(n)});
    });
  });
  if(document.body)obs.observe(document.body,{childList:true,subtree:true});
})();
