(function(){
  'use strict';
  var originalFetch=window.fetch.bind(window);
  var endpoint='https://yhzdqrqzjruduohypvqf.supabase.co/functions/v1/broker-contact-unlock';
  window.fetch=function(input,init){
    var url=typeof input==='string'?input:(input&&input.url)||'';
    if(url==='/api/contact_unlock'||url.indexOf('/api/contact_unlock?')===0){
      var opts=Object.assign({},init||{}),headers=new Headers((init&&init.headers)||{}),token='';
      try{token=localStorage.getItem('gb_access_token')||''}catch(e){}
      if(token)headers.set('Authorization','Bearer '+token);
      headers.set('Content-Type','application/json');
      opts.headers=headers;opts.cache='no-store';
      return originalFetch(endpoint,opts);
    }
    return originalFetch(input,init);
  };
})();
