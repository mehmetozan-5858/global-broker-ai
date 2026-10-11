(function(){
  'use strict';
  var originalFetch=window.fetch.bind(window);
  var SB_URL='https://yhzdqrqzjruduohypvqf.supabase.co';
  var SB_KEY='sb_publishable_fFtN0JmDBp8TP01lKJhTFQ_sx6mkt-w';

  function tokenFrom(init){
    try{
      var h=new Headers((init&&init.headers)||{});
      var auth=h.get('Authorization')||'';
      if(auth.indexOf('Bearer ')===0)return auth.slice(7).trim();
      return localStorage.getItem('gb_access_token')||'';
    }catch(e){return ''}
  }
  function jsonResponse(status,payload){
    return new Response(JSON.stringify(payload),{status:status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'private, no-store, max-age=0','Pragma':'no-cache'}});
  }
  async function post(url,token,payload){
    var r=await originalFetch(url,{method:'POST',headers:{apikey:SB_KEY,Authorization:'Bearer '+token,'Content-Type':'application/json',Accept:'application/json'},body:JSON.stringify(payload||{}),cache:'no-store'});
    var data=await r.json().catch(function(){return {}});
    return {ok:r.ok,status:r.status,data:data};
  }
  function errorCode(data,status){
    var msg=String((data&&data.message)||(data&&data.details)||'').toLowerCase();
    var map=[
      ['authentication_required','AUTHENTICATION_REQUIRED',401],
      ['active_plan_required','ACTIVE_PLAN_REQUIRED',403],
      ['invalid_opportunity_id','INVALID_OPPORTUNITY_ID',400],
      ['opportunity_not_found','OPPORTUNITY_NOT_FOUND',404],
      ['sector_not_in_plan','SECTOR_NOT_IN_PLAN',403],
      ['country_not_selected','COUNTRY_NOT_SELECTED',403],
      ['introduction_credit_required','INTRODUCTION_CREDIT_REQUIRED',402]
    ];
    for(var i=0;i<map.length;i++)if(msg.indexOf(map[i][0])>=0)return {code:map[i][1],status:map[i][2]};
    return {code:'INTRODUCTION_REQUEST_DENIED',status:status||403};
  }

  window.fetch=async function(input,init){
    var url=typeof input==='string'?input:(input&&input.url)||'';
    if(!(url==='/api/introduction'||url.indexOf('/api/introduction?')===0))return originalFetch(input,init);
    var token=tokenFrom(init);
    if(!token)return jsonResponse(401,{status:'AUTHENTICATION_REQUIRED'});
    var method=String((init&&init.method)||'GET').toUpperCase();
    try{
      if(method==='GET'){
        var list=await post(SB_URL+'/rest/v1/rpc/my_introduction_requests',token,{});
        if(!list.ok)return jsonResponse(list.status,{status:'INTRODUCTION_REQUEST_DENIED'});
        return jsonResponse(200,Array.isArray(list.data)?list.data:[]);
      }
      if(method!=='POST')return jsonResponse(405,{status:'METHOD_NOT_ALLOWED'});
      var body={};
      try{body=JSON.parse((init&&init.body)||'{}')}catch(e){return jsonResponse(400,{status:'INVALID_JSON'})}
      var opportunityId=String(body.opportunity_id||'').trim();
      if(opportunityId.length<8||opportunityId.length>200)return jsonResponse(400,{status:'INVALID_OPPORTUNITY_ID'});
      var req=await post(SB_URL+'/rest/v1/rpc/request_introduction',token,{p_opportunity_id:opportunityId});
      if(!req.ok||!req.data||req.data.ok!==true){var mapped=errorCode(req.data,req.status);return jsonResponse(mapped.status,{status:mapped.code})}
      var requestStatus=req.data.status||'requested',verification=null;
      if(req.data.request_id){
        var ver=await post(SB_URL+'/functions/v1/broker-introduction-verify',token,{request_id:req.data.request_id});
        if(ver.ok&&ver.data&&ver.data.status==='OK'){
          requestStatus=ver.data.request_status||requestStatus;
          verification={route_type:ver.data.route_type||null,verification_score:ver.data.verification_score||null,reason:ver.data.reason||null,credit_refunded:!!ver.data.credit_refunded};
        }
      }
      return jsonResponse(200,{status:'INTRODUCTION_REQUESTED',opportunity_id:opportunityId,request_id:req.data.request_id,request_status:requestStatus,already_requested:!!req.data.already_requested,credits_remaining:req.data.credits_remaining,verification:verification});
    }catch(e){return jsonResponse(503,{status:'INTRODUCTION_SERVICE_UNAVAILABLE'})}
  };
})();
