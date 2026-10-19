(function(root,factory){var api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.GlobalBrokerRecovery=api})(typeof window==='object'?window:globalThis,function(){
'use strict';
function parse(hash,search){
 var h=new URLSearchParams(String(hash||'').replace(/^#/,'')),q=new URLSearchParams(String(search||'').replace(/^\?/,''));
 if(h.has('error')||q.has('error')||h.has('error_code')||q.has('error_code'))return {kind:'expired'};
 if(q.has('code'))return {kind:'expired'};
 if(h.get('type')!=='recovery')return {kind:'none'};
 var at=h.get('access_token')||'',rt=h.get('refresh_token')||'';
 if(!at||!rt||at.length>8192||rt.length>8192||/\s/.test(at+rt))return {kind:'expired'};
 return {kind:'session',access_token:at,refresh_token:rt};
}
function passwordError(password,confirmation){
 if(password.length<12)return 'Yeni şifre en az 12 karakter olmalı.';
 if(password!==confirmation)return 'Şifreler eşleşmiyor.';
 return '';
}
async function start(config){
 var $=function(id){return document.getElementById(id)},pending='gb_password_recovery_pending';
 var parsed=parse(location.hash,location.search),params=new URLSearchParams(location.hash.slice(1)),query=new URLSearchParams(location.search);
 // Remove credentials before any request, analytics or navigation can copy them.
 if(parsed.kind!=='none'||params.has('access_token')||params.has('refresh_token')||query.has('access_token')||query.has('refresh_token'))history.replaceState(null,'',location.pathname);
 var active=parsed.kind!=='none'||sessionStorage.getItem(pending)==='1';
 if(!active)return false;
 $('status').textContent='Şifre yenileme modu.';
 $('recovery').classList.remove('hidden');$('authFields').classList.add('hidden');$('authActions').classList.add('hidden');
 var status=$('recoveryStatus');function message(text,ok){status.textContent=text;status.className='status '+(ok?'ok':'bad')}
 $('cancelRecovery').onclick=function(){sessionStorage.removeItem(pending);$('newPassword').value='';$('confirmPassword').value='';$('status').textContent='Giriş yapabilir veya yeni şifre sıfırlama bağlantısı isteyebilirsiniz.';$('recovery').classList.add('hidden');$('authFields').classList.remove('hidden');$('authActions').classList.remove('hidden')};
 if(parsed.kind==='expired'){sessionStorage.removeItem(pending);message('Bağlantı geçersiz veya süresi dolmuş. Yeni bir şifre sıfırlama bağlantısı isteyin.');return true}
 var saved=config.getSession(),session=parsed.kind==='session'?parsed:{access_token:saved.token,refresh_token:saved.refresh};
 if(!session.access_token){sessionStorage.removeItem(pending);message('Şifre yenileme oturumu bulunamadı. Yeni bağlantı isteyin.');return true}
 async function request(method,body){return fetch(config.baseUrl+'/auth/v1/user',{method:method,cache:'no-store',headers:{apikey:config.key,Authorization:'Bearer '+session.access_token,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined})}
 status.textContent='Şifre yenileme oturumu doğrulanıyor…';
 try{
  var response=await request('GET');var user=await response.json();
  if(!response.ok||!user.id)throw Error('session');
 }catch(e){sessionStorage.removeItem(pending);message('Şifre yenileme oturumu doğrulanamadı. Yeni bağlantı isteyin.');return true}
 config.onSession(session);sessionStorage.setItem(pending,'1');$('recoveryForm').classList.remove('hidden');
 status.textContent='Yeni şifrenizi iki kez girin. Yönetici hesabında kayıtlı MFA şartı korunur.';status.className='status';
 $('recoveryForm').onsubmit=async function(event){
  event.preventDefault();var password=$('newPassword').value,confirmation=$('confirmPassword').value,error=passwordError(password,confirmation);
  if(error){message(error);return}
  var button=$('updatePassword');button.disabled=true;
  try{
   var result=await request('PUT',{password:password});
   if(!result.ok){
    if(result.status===401||result.status===403)message('Güvenlik doğrulaması gerekli. MFA ekranında doğrulayıp bu sayfaya dönün; şifre değiştirilmedi.');
    else message('Şifre kaydedilemedi. Bağlantıyı ve şifre koşullarını kontrol edip tekrar deneyin.');
    return;
   }
   sessionStorage.removeItem(pending);$('newPassword').value='';$('confirmPassword').value='';$('password').value='';
   $('recoveryForm').classList.add('hidden');$('authFields').classList.remove('hidden');$('authActions').classList.remove('hidden');
   message('Yeni şifreniz kaydedildi.',true);if(config.onComplete)await config.onComplete();
  }catch(e){message('Bağlantı kurulamadı. Şifre değişikliği doğrulanmadı; tekrar deneyin.')}finally{button.disabled=false}
 };
 return true;
}
return {parse:parse,passwordError:passwordError,start:start};
});
