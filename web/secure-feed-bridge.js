(function(){
  'use strict';
  var originalFetch=window.fetch.bind(window);
  window.fetch=function(input,init){
    var url=typeof input==='string'?input:(input&&input.url)||'';
    if(url.indexOf('/data/latest-opportunities.json')>=0||url.indexOf('data/latest-opportunities.json')===0){
      var token='';try{token=localStorage.getItem('gb_access_token')||''}catch(e){}
      var opts=Object.assign({},init||{}),headers=new Headers((init&&init.headers)||{});
      if(token)headers.set('Authorization','Bearer '+token);
      opts.headers=headers;opts.cache='no-store';
      return originalFetch('/api/opportunities',opts);
    }
    return originalFetch(input,init);
  };
})();
