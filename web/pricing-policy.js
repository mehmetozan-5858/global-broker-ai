(function(global){
  const POLICY_VERSION='2026-10-10-v2';

  const plans={
    free:{id:'free',name:'Free',monthlyUsd:0,sectors:1,countries:3,contactCredits:0,allSectors:false,features:['1 sektör kümesi','3 ülkeye kadar fırsat özeti','Ürün, ülke, yaklaşık miktar ve tarih görünümü','Firma ve doğrudan kontak bilgileri maskeli','Toplu dışa aktarma yok'],successCommissionMultiplier:1},
    sector:{id:'sector',name:'Sector Access',monthlyUsd:89,sectors:1,countries:15,contactCredits:10,allSectors:false,features:['1 ana sektör + yakın alt kategoriler','15 ülkeye kadar erişim','10 doğrulanmış kontak açma kredisi / ay','Fiyat, risk ve kaynak doğrulama katmanı','Platform içi iletişim'],successCommissionMultiplier:1},
    multi:{id:'multi',name:'Multi-Sector',monthlyUsd:179,sectors:4,countries:40,contactCredits:35,allSectors:false,features:['4 sektör kümesine kadar erişim','40 ülkeye kadar erişim','35 doğrulanmış kontak açma kredisi / ay','Öncelikli fırsat uyarıları','Gelişmiş fiyat / marj ve tedarik analizi'],successCommissionMultiplier:0.9},
    global:{id:'global',name:'Global Access',monthlyUsd:349,sectors:null,countries:null,contactCredits:100,allSectors:true,features:['Tüm sektör ve ülke fırsatları','100 doğrulanmış kontak açma kredisi / ay','Özel alıcı / tedarikçi radarları','Öncelikli eşleştirme','Gelişmiş pazar ve rakip istihbaratı'],successCommissionMultiplier:0.8},
    enterprise:{id:'enterprise',name:'Enterprise',monthlyUsd:null,sectors:null,countries:null,contactCredits:null,allSectors:true,features:['Özel sektör ve ülke kapsamı','Yüksek hacimli ekip kullanımı','Özel ajan taramaları','Özel veri entegrasyonu ve raporlama','Özel başarı komisyonu'],successCommissionMultiplier:null}
  };

  const sectorClusters={
    furniture:{name:'Mobilya & İç Mekân',includes:['Mobilya','Ofis mobilyası','Otel ve restoran mobilyası','Ahşap ürünler','İç mekân / dekorasyon','Kontrat üretimi'],keywords:['furniture','mobilya','chair','table','desk','cabinet','wooden','wood','interior','decor','hotel furniture','office furniture']},
    machinery:{name:'Makine & CNC',includes:['CNC makineleri','Metal işleme','Endüstriyel makine','Yedek parça','Fason imalat','Otomasyon ekipmanları'],keywords:['machine','machinery','cnc','lathe','milling','industrial equipment','pump','compressor','valve','metalworking','automation']},
    textile:{name:'Tekstil & Giyim',includes:['Kumaş','Hazır giyim','Ev tekstili','Teknik tekstil','Aksesuar','Özel üretim'],keywords:['textile','fabric','garment','clothing','apparel','uniform','cotton','yarn','tekstil','giyim','kumaş']},
    automotive:{name:'Otomotiv & Yedek Parça',includes:['OEM / Tier tedarik','Otomotiv parçası','Filtre / fren / süspansiyon','Kauçuk ve plastik parçalar','Elektrik-elektronik aksam'],keywords:['automotive','vehicle','car ','truck','bus ','spare part','brake','suspension','filter','otomotiv','yedek parça']},
    packaging:{name:'Ambalaj & Baskı',includes:['Karton / oluklu mukavva','Esnek ambalaj','Plastik ambalaj','Etiket','Endüstriyel ambalaj','Baskı'],keywords:['packaging','package','carton','corrugated','label','printing','printed','ambalaj','etiket','kutu']},
    construction:{name:'Yapı & Yapı Malzemeleri',includes:['Kapı / pencere','Seramik / taş','Yalıtım','Metal yapı elemanları','Banyo / mutfak','İnşaat sarf malzemeleri'],keywords:['construction','building material','door','window','ceramic','tile','stone','insulation','cement','steel structure','inşaat','yapı']},
    food:{name:'Gıda & Tarım Ürünleri',includes:['İşlenmiş gıda','Bakliyat / tahıl','Kuru meyve','Kuruyemiş','Gıda hammaddeleri','Ambalajlı tüketim ürünleri'],keywords:['food','grain','wheat','rice','lentil','fruit','nuts','edible','agricultural product','gıda','tarım','bakliyat']},
    chemicals:{name:'Kimya & Endüstriyel Hammaddeler',includes:['Endüstriyel kimyasallar','Plastik hammaddeler','Boya / kaplama','Temizlik kimyasalları','Gübre / tarım girdileri'],keywords:['chemical','polymer','resin','fertilizer','paint','coating','detergent','urea','kimya','gübre']},
    electronics:{name:'Elektrik & Elektronik',includes:['Elektrik ekipmanı','Kablo','Pano','Endüstriyel elektronik','Aydınlatma','Enerji ekipmanı'],keywords:['electrical','electronic','cable','switchgear','transformer','lighting','battery','solar','elektrik','elektronik']},
    medical:{name:'Medikal & Laboratuvar',includes:['Tıbbi sarf','Laboratuvar ekipmanı','Test / ölçüm','Sterilizasyon','Hastane ekipmanı'],keywords:['medical','hospital','laboratory','lab equipment','surgical','diagnostic','steril','medikal','laboratuvar']}
  };

  const successCommissionBands=[{max:25000,rate:0.04,label:'$0–$25K'},{max:100000,rate:0.03,label:'$25K–$100K'},{max:500000,rate:0.02,label:'$100K–$500K'},{max:2000000,rate:0.0125,label:'$500K–$2M'},{max:10000000,rate:0.0075,label:'$2M–$10M'},{max:Infinity,rate:0.004,label:'$10M+'}];
  function baseCommissionRate(amount){const n=Math.max(0,Number(amount)||0);return (successCommissionBands.find(b=>n<=b.max)||successCommissionBands[successCommissionBands.length-1]).rate;}
  function commissionRate(amount,planId){const plan=plans[planId]||plans.free,base=baseCommissionRate(amount);return plan.successCommissionMultiplier==null?base:base*plan.successCommissionMultiplier;}
  function commissionAmount(amount,planId){const n=Math.max(0,Number(amount)||0);return n*commissionRate(n,planId);}
  function canSeeDirectContact(planId,creditsLeft){const plan=plans[planId]||plans.free;return plan.contactCredits!==0&&(creditsLeft==null||Number(creditsLeft)>0);}
  function shouldMaskContact(planId,creditsLeft){return !canSeeDirectContact(planId,creditsLeft);}
  function canAccessSector(planId,selectedSectorIds,targetSectorId){const plan=plans[planId]||plans.free;if(plan.allSectors)return true;const selected=Array.isArray(selectedSectorIds)?selectedSectorIds:[];return selected.includes(targetSectorId)&&selected.length<=plan.sectors;}
  function opportunityText(o){if(!o||typeof o!=='object')return '';const keys=['sector_id','sector','product_name','product','title_tr','title_original','bid_description','notice-title','title','demand_summary_tr','detail_tr'];return keys.map(k=>{const v=o[k];return Array.isArray(v)?v.join(' '):typeof v==='object'?'':String(v||'')}).join(' ').toLocaleLowerCase('en');}
  function inferSector(o){const explicit=String((o&&o.sector_id)||'').trim();if(sectorClusters[explicit])return explicit;const hay=opportunityText(o);let best='',score=0;Object.entries(sectorClusters).forEach(([id,s])=>{let n=0;s.keywords.forEach(k=>{if(hay.includes(String(k).toLowerCase()))n++});if(n>score){best=id;score=n}});return best;}
  function opportunityCountryCode(o){return String((o&&((o.country_code)||(o.buyer_country_code)||(o['buyer-country-code'])))||'').trim().toUpperCase();}

  global.GlobalBrokerPricing={POLICY_VERSION,plans,sectorClusters,successCommissionBands,baseCommissionRate,commissionRate,commissionAmount,canSeeDirectContact,shouldMaskContact,canAccessSector,inferSector,opportunityCountryCode};
})(window);
