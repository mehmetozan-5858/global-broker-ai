(function(global){
  const POLICY_VERSION='2026-10-10-v1';

  const plans={
    free:{
      id:'free',name:'Free',monthlyUsd:0,sectors:1,countries:3,contactCredits:0,allSectors:false,
      features:['1 sektör kümesi','3 ülkeye kadar fırsat özeti','Ürün, ülke, yaklaşık miktar ve tarih görünümü','Firma ve doğrudan kontak bilgileri maskeli','Toplu dışa aktarma yok'],
      successCommissionMultiplier:1
    },
    sector:{
      id:'sector',name:'Sector Access',monthlyUsd:89,sectors:1,countries:15,contactCredits:10,allSectors:false,
      features:['1 ana sektör + yakın alt kategoriler','15 ülkeye kadar erişim','10 doğrulanmış kontak açma kredisi / ay','Fiyat, risk ve kaynak doğrulama katmanı','Platform içi iletişim'],
      successCommissionMultiplier:1
    },
    multi:{
      id:'multi',name:'Multi-Sector',monthlyUsd:179,sectors:4,countries:40,contactCredits:35,allSectors:false,
      features:['4 sektör kümesine kadar erişim','40 ülkeye kadar erişim','35 doğrulanmış kontak açma kredisi / ay','Öncelikli fırsat uyarıları','Gelişmiş fiyat / marj ve tedarik analizi'],
      successCommissionMultiplier:0.9
    },
    global:{
      id:'global',name:'Global Access',monthlyUsd:349,sectors:null,countries:null,contactCredits:100,allSectors:true,
      features:['Tüm sektör ve ülke fırsatları','100 doğrulanmış kontak açma kredisi / ay','Özel alıcı / tedarikçi radarları','Öncelikli eşleştirme','Gelişmiş pazar ve rakip istihbaratı'],
      successCommissionMultiplier:0.8
    },
    enterprise:{
      id:'enterprise',name:'Enterprise',monthlyUsd:null,sectors:null,countries:null,contactCredits:null,allSectors:true,
      features:['Özel sektör ve ülke kapsamı','Yüksek hacimli ekip kullanımı','Özel ajan taramaları','Özel veri entegrasyonu ve raporlama','Özel başarı komisyonu'],
      successCommissionMultiplier:null
    }
  };

  const sectorClusters={
    furniture:{name:'Mobilya & İç Mekân',includes:['Mobilya','Ofis mobilyası','Otel ve restoran mobilyası','Ahşap ürünler','İç mekân / dekorasyon','Kontrat üretimi']},
    machinery:{name:'Makine & CNC',includes:['CNC makineleri','Metal işleme','Endüstriyel makine','Yedek parça','Fason imalat','Otomasyon ekipmanları']},
    textile:{name:'Tekstil & Giyim',includes:['Kumaş','Hazır giyim','Ev tekstili','Teknik tekstil','Aksesuar','Özel üretim']},
    automotive:{name:'Otomotiv & Yedek Parça',includes:['OEM / Tier tedarik','Otomotiv parçası','Filtre / fren / süspansiyon','Kauçuk ve plastik parçalar','Elektrik-elektronik aksam']},
    packaging:{name:'Ambalaj & Baskı',includes:['Karton / oluklu mukavva','Esnek ambalaj','Plastik ambalaj','Etiket','Endüstriyel ambalaj','Baskı']},
    construction:{name:'Yapı & Yapı Malzemeleri',includes:['Kapı / pencere','Seramik / taş','Yalıtım','Metal yapı elemanları','Banyo / mutfak','İnşaat sarf malzemeleri']},
    food:{name:'Gıda & Tarım Ürünleri',includes:['İşlenmiş gıda','Bakliyat / tahıl','Kuru meyve','Kuruyemiş','Gıda hammaddeleri','Ambalajlı tüketim ürünleri']},
    chemicals:{name:'Kimya & Endüstriyel Hammaddeler',includes:['Endüstriyel kimyasallar','Plastik hammaddeler','Boya / kaplama','Temizlik kimyasalları','Gübre / tarım girdileri']},
    electronics:{name:'Elektrik & Elektronik',includes:['Elektrik ekipmanı','Kablo','Pano','Endüstriyel elektronik','Aydınlatma','Enerji ekipmanı']},
    medical:{name:'Medikal & Laboratuvar',includes:['Tıbbi sarf','Laboratuvar ekipmanı','Test / ölçüm','Sterilizasyon','Hastane ekipmanı']}
  };

  const successCommissionBands=[
    {max:25000,rate:0.04,label:'$0–$25K'},
    {max:100000,rate:0.03,label:'$25K–$100K'},
    {max:500000,rate:0.02,label:'$100K–$500K'},
    {max:2000000,rate:0.0125,label:'$500K–$2M'},
    {max:10000000,rate:0.0075,label:'$2M–$10M'},
    {max:Infinity,rate:0.004,label:'$10M+'}
  ];

  function baseCommissionRate(amount){
    const n=Math.max(0,Number(amount)||0);
    return (successCommissionBands.find(b=>n<=b.max)||successCommissionBands[successCommissionBands.length-1]).rate;
  }

  function commissionRate(amount,planId){
    const plan=plans[planId]||plans.free;
    const base=baseCommissionRate(amount);
    return plan.successCommissionMultiplier==null?base:base*plan.successCommissionMultiplier;
  }

  function commissionAmount(amount,planId){
    const n=Math.max(0,Number(amount)||0);
    return n*commissionRate(n,planId);
  }

  function canSeeDirectContact(planId,creditsLeft){
    const plan=plans[planId]||plans.free;
    return plan.contactCredits!==0&&Number(creditsLeft)>0;
  }

  function shouldMaskContact(planId,creditsLeft){
    return !canSeeDirectContact(planId,creditsLeft);
  }

  function canAccessSector(planId,selectedSectorIds,targetSectorId){
    const plan=plans[planId]||plans.free;
    if(plan.allSectors)return true;
    const selected=Array.isArray(selectedSectorIds)?selectedSectorIds:[];
    return selected.includes(targetSectorId)&&selected.length<=plan.sectors;
  }

  global.GlobalBrokerPricing={POLICY_VERSION,plans,sectorClusters,successCommissionBands,baseCommissionRate,commissionRate,commissionAmount,canSeeDirectContact,shouldMaskContact,canAccessSector};
})(window);
