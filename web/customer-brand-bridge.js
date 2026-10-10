(function(){
  var root=document.documentElement;
  root.style.setProperty('--gb-orange','#f3923c');
  var header=document.querySelector('.top');
  var brand=document.querySelector('.brand');
  if(brand){brand.style.fontFamily='system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif';brand.style.fontWeight='900';brand.style.letterSpacing='-.03em';var span=brand.querySelector('span');if(span)span.style.color='#f3923c';}
  if(header)header.style.boxShadow='0 5px 22px rgba(0,0,0,.16)';
  var back=document.querySelector('a[href="website.html"]');
  if(back){back.textContent='← GLOBAL BROKER kurumsal sitesi';back.setAttribute('href','/');}
})();