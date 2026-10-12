(function(){
  'use strict';

  function token(){
    try{return localStorage.getItem('gb_access_token')||''}catch(e){return ''}
  }
  function isFeed(url){
    url=String(url||'');
    return url.indexOf('/data/latest-opportunities.json')>=0 ||
           url.indexOf('data/latest-opportunities.json')===0 ||
           url.indexOf('/api/opportunities')>=0;
  }

  // fetch kullanan yeni ekranlar
  var originalFetch=window.fetch.bind(window);
  window.fetch=function(input,init){
    var url=typeof input==='string'?input:(input&&input.url)||'';
    if(isFeed(url)){
      var opts=Object.assign({},init||{}),headers=new Headers((init&&init.headers)||{});
      var t=token();
      if(t)headers.set('Authorization','Bearer '+t);
      opts.headers=headers;
      opts.cache='no-store';
      return originalFetch('/api/opportunities?t='+Date.now(),opts);
    }
    return originalFetch(input,init);
  };

  // Eski portal XMLHttpRequest kullanıyor. Onu da aynı güvenli feed'e yönlendir.
  var NativeXHR=window.XMLHttpRequest;
  function SecureXHR(){
    var xhr=new NativeXHR(),target='';
    var nativeOpen=xhr.open;
    var nativeSend=xhr.send;
    xhr.open=function(method,url){
      target=String(url||'');
      var args=[].slice.call(arguments);
      if(isFeed(target)) args[1]='/api/opportunities?t='+Date.now();
      return nativeOpen.apply(xhr,args);
    };
    xhr.send=function(body){
      if(isFeed(target)){
        var t=token();
        if(t){try{xhr.setRequestHeader('Authorization','Bearer '+t)}catch(e){}}
        try{xhr.setRequestHeader('Cache-Control','no-cache')}catch(e){}
      }
      return nativeSend.call(xhr,body);
    };
    return xhr;
  }
  SecureXHR.prototype=NativeXHR.prototype;
  window.XMLHttpRequest=SecureXHR;
})();
