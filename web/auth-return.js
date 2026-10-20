(function(root){'use strict';
var allowed=['/account','/app','/quote-evidence'];
function safe(value){return allowed.indexOf(value)>=0?value:null}
function next(search){return safe(new URLSearchParams(search||'').get('next'))}
function path(base,target){target=safe(target);return target?base+'?next='+encodeURIComponent(target):base}
var api={next:next,account:function(target){return path('/account',target)},security:function(target){return path('/security',target)}};
root.GBAuthReturn=api;if(typeof module==='object'&&module.exports)module.exports=api;
})(typeof window==='object'?window:globalThis);
