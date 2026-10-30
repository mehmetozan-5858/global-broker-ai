import {pathToFileURL} from 'node:url';
import {matchesSandboxPrice} from '../supabase/functions/broker-billing-sandbox/catalog.mjs';

const PLANS={sector:8900,multi:17900,global:34900};
const BASE='https://sandbox-api.paddle.com';
const id=(prefix,value)=>typeof value==='string'&&new RegExp('^'+prefix+'_[a-z0-9]{26}$').test(value);

export async function preflight({env=process.env,fetchImpl=fetch}={}){
  const key=env.GB_BROKER_SANDBOX_API_KEY;
  const report={environment:'sandbox',preflight_passed:false,provider_payment_tested:false,receiver_configuration_verified:false,live_settings_changed:false,
    missing:[],catalog_checks:{},provider_reads:0};
  if(!/^pdl_sdbx_apikey_[a-zA-Z0-9_]+$/.test(key||'')){
    report.missing.push(key?'sandbox_api_key_required':'GB_BROKER_SANDBOX_API_KEY');
    return report;
  }
  let catalog;try{catalog=JSON.parse(env.GB_BROKER_SANDBOX_PRICES||'null')}catch{}
  if(!catalog||typeof catalog!=='object'||Array.isArray(catalog)||Object.keys(catalog).length!==3
    ||!Object.keys(PLANS).every(plan=>id('pri',catalog[plan]?.price_id)&&id('pro',catalog[plan]?.product_id))
    ||new Set(Object.values(catalog).map(x=>x.price_id)).size!==3
    ||new Set(Object.values(catalog).map(x=>x.product_id)).size!==3){
    report.missing.push('GB_BROKER_SANDBOX_PRICES');return report;
  }
  async function read(path){
    report.provider_reads++;
    const response=await fetchImpl(BASE+path,{method:'GET',redirect:'error',
      headers:{Authorization:'Bearer '+key,'Paddle-Version':'1'},signal:AbortSignal.timeout(8000)});
    if(!response.ok)throw Error('sandbox_provider_read_failed');
    const body=await response.json();return body.data;
  }
  try{
    const root=await read('/');
    if(root?.api?.environment!=='sandbox'||!root.caller?.account){
      report.missing.push('authenticated_sandbox_account');return report;
    }
    for(const [plan,amount_minor] of Object.entries(PLANS)){
      const expected={...catalog[plan],amount_minor};
      report.catalog_checks[plan]=matchesSandboxPrice(await read('/prices/'+expected.price_id),expected);
    }
  }catch{
    report.missing.push('sandbox_provider_read_failed');return report;
  }
  if(!/^test_[a-zA-Z0-9]+$/.test(env.GB_BROKER_SANDBOX_CLIENT_TOKEN||''))report.missing.push('GB_BROKER_SANDBOX_CLIENT_TOKEN');
  if(!env.GB_BROKER_SANDBOX_WEBHOOK_SECRET)report.missing.push('GB_BROKER_SANDBOX_WEBHOOK_SECRET');
  if(Object.values(report.catalog_checks).some(value=>value!==true))report.missing.push('dedicated_broker_catalog_mismatch');
  report.preflight_passed=report.missing.length===0;
  // This command never enables the receiver, creates transactions or persists
  // credentials. Output deliberately excludes IDs, keys and provider payloads.
  return report;
}

if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
  const result=await preflight();console.log(JSON.stringify(result));
  if(!result.preflight_passed)process.exitCode=2;
}
