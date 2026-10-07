const DATASETS = {
  vacuum: {
    match: /пылесос/i,
    query: "Вертикальные пылесосы",
    subtitle: "Исследуем category space, ищем продуктовые архетипы и cross-market gap.",
    stats: {queries:43,pages:728,records:214,archetypes:37,candidates:20,suppliers:63,cost:0.74},
    scouts: {
      wb:{records:42,queries:9,pages:138},
      ozon:{records:49,queries:10,pages:154},
      amazon:{records:68,queries:13,pages:247},
      lazada:{records:55,queries:11,pages:189}
    },
    insight: {
      title:"Зарубежный тренд уже заметен, а предложение в РФ пока отстаёт",
      text:"Складная труба и подсветка зоны уборки стабильно встречаются у сильных Amazon/Lazada предложений, но заметно реже представлены на WB/Ozon. Product Hunter считает это потенциальным Trend Transfer.",
      transfer:94
    },
    opportunities:[
      {
        title:"Складная труба + LED‑подсветка",
        desc:"Cordless stick vacuum · 450–550 Вт · bendable tube · green LED",
        score:91,transfer:94,gap:91,supplier:84,margin:"31–38%",retail:"₽8 500–11 500",supplierPrice:"$27–34",
        markets:{WB:38,Ozon:44,Amazon:92,Lazada:81},
        tags:["зарубежный тренд","низкая насыщенность РФ","17 supplier matches"],
        reasons:[
          ["Сильный cross-market signal","Архетип широко представлен на Amazon и Lazada, но слабее на WB/Ozon."],
          ["Функция уже доказана рынком","Складная труба повторяется у нескольких независимых брендов и ценовых сегментов."],
          ["Russia Gap высокий","На российских площадках предложение заметно менее плотное, чем на зарубежных."],
          ["Производство доступно","Supplier Probe нашёл 17 похожих OEM/ODM-предложений."]
        ],
        evidence:["Amazon · 41 найденная карточка","Lazada · 28 найденных карточек","WB · 9 близких предложений","Ozon · 11 близких предложений"]
      },
      {
        title:"Лёгкий пылесос для шерсти животных",
        desc:"Lightweight cordless · pet brush · anti-tangle · 2–2.5 кг",
        score:86,transfer:84,gap:79,supplier:90,margin:"29–36%",retail:"₽7 900–10 900",supplierPrice:"$24–31",
        markets:{WB:52,Ozon:57,Amazon:88,Lazada:74},
        tags:["pet hair","anti-tangle","сильный supplier signal"],
        reasons:[
          ["Устойчивая проблема пользователя","Pet hair и anti-tangle повторяются в запросах и feature-наборах."],
          ["Предложение РФ уже есть, но не насыщено","WB/Ozon signal средний, без явной доминации архетипа."],
          ["Хорошая доступность производства","OEM-предложений больше, чем у большинства кандидатов."],
          ["Экономика проходит фильтр","Модельная маржа остаётся выше 29% в базовом сценарии."]
        ],
        evidence:["Amazon · pet hair query cluster","Lazada · lightweight cluster","WB · 14 близких предложений","Supplier Probe · 21 match"]
      },
      {
        title:"Wet & Dry с самоочисткой",
        desc:"Wet/dry stick vacuum · self-clean cycle · dual tank",
        score:82,transfer:87,gap:74,supplier:72,margin:"25–32%",retail:"₽18 900–27 000",supplierPrice:"$62–84",
        markets:{WB:61,Ozon:64,Amazon:89,Lazada:86},
        tags:["wet & dry","self-clean","выше средний чек"],
        reasons:[
          ["Сильный азиатский сигнал","Архетип особенно заметен на Lazada."],
          ["Высокий средний чек","Даёт пространство для маржи, но повышает логистический риск."],
          ["Россия уже догоняет","Gap ниже, чем у TOP‑2: предложение WB/Ozon растёт."],
          ["Sourcing сложнее","Supplier price и вес продукта уменьшают запас экономики."]
        ],
        evidence:["Lazada · 36 близких карточек","Amazon · 29 близких карточек","WB/Ozon · growing presence","Supplier Probe · 11 matches"]
      },
      {
        title:"Self‑standing + съёмный аккумулятор",
        desc:"Cordless stick vacuum · self-standing · removable battery",
        score:78,transfer:76,gap:72,supplier:88,margin:"28–34%",retail:"₽8 000–12 000",supplierPrice:"$26–33",
        markets:{WB:55,Ozon:58,Amazon:78,Lazada:73},
        tags:["self-standing","removable battery","простая кастомизация"],
        reasons:[
          ["Понятное функциональное отличие","Self-standing легко объясняется покупателю и заметно визуально."],
          ["Supplier signal сильный","Много похожих OEM-моделей и вариантов private label."],
          ["Cross-market gap умеренный","Российские площадки уже имеют заметное предложение."],
          ["Низкая сложность модификации","Батарея и стойка доступны в нескольких готовых конфигурациях."]
        ],
        evidence:["Amazon · 22 карточки","WB · 15 карточек","Ozon · 17 карточек","Supplier Probe · 19 matches"]
      },
      {
        title:"Док‑станция с автоочисткой контейнера",
        desc:"Cordless vacuum · auto-empty dock · premium segment",
        score:73,transfer:89,gap:85,supplier:48,margin:"20–29%",retail:"₽24 000–38 000",supplierPrice:"$110–145",
        markets:{WB:27,Ozon:31,Amazon:86,Lazada:69},
        tags:["очень высокий gap","premium","сложный sourcing"],
        reasons:[
          ["Очень высокий Russia Gap","На Amazon архетип заметен, на WB/Ozon пока редок."],
          ["Transfer signal высокий","Может быть ранним трендом, но evidence меньше, чем у TOP‑1."],
          ["Supplier Availability слабее","Мало подходящих OEM-конфигураций в доступной выборке."],
          ["Экономика чувствительная","Высокая закупка и логистика снижают итоговый score."]
        ],
        evidence:["Amazon · premium cluster","WB/Ozon · low presence","Lazada · early presence","Supplier Probe · 6 matches"]
      }
    ]
  },
  bath: {
    match: /коврик|bath mat|каменн/i,
    query:"Коврики для ванной",
    subtitle:"Ищем материалы, форм-факторы и cross-market gap внутри категории.",
    stats:{queries:37,pages:604,records:188,archetypes:31,candidates:18,suppliers:54,cost:0.63},
    scouts:{wb:{records:44,queries:8,pages:127},ozon:{records:46,queries:9,pages:139},amazon:{records:53,queries:11,pages:181},lazada:{records:45,queries:9,pages:157}},
    insight:{title:"Материалы нового поколения дают более сильный сигнал, чем дизайн",text:"Stone/diatomite и quick-dry multilayer архетипы заметнее на зарубежных рынках, тогда как российская выдача сильнее сконцентрирована на классическом текстиле.",transfer:90},
    opportunities:[
      {title:"Каменный быстросохнущий коврик",desc:"Diatomite / stone bath mat · anti-slip base",score:89,transfer:90,gap:88,supplier:86,margin:"34–43%",retail:"₽2 900–4 900",supplierPrice:"$5.8–8.4",markets:{WB:35,Ozon:39,Amazon:86,Lazada:82},tags:["material shift","высокий Russia Gap","дешёвый sourcing"],reasons:[["Material trend","Stone/diatomite стабильно встречается на Amazon/Lazada."],["Россия отстаёт","На WB/Ozon классический текстиль доминирует сильнее."],["Простая логистика","Товар компактный, но требует контроля боя."],["Много поставщиков","Supplier Probe нашёл широкий диапазон OEM." ]],evidence:["Amazon · stone bath mat cluster","Lazada · diatomite cluster","WB/Ozon · lower presence","Supplier Probe · 23 matches"]},
      {title:"Многослойный quick‑dry коврик",desc:"Soft surface · absorbent core · rubber base",score:84,transfer:82,gap:73,supplier:92,margin:"38–47%",retail:"₽1 900–3 200",supplierPrice:"$2.7–4.6",markets:{WB:57,Ozon:61,Amazon:82,Lazada:76},tags:["quick-dry","дешёвый sourcing","легко брендировать"],reasons:[["Хороший supplier signal","Очень много OEM-вариантов."],["Маржа привлекательна","Низкая закупка и компактная логистика."],["Gap умеренный","Архетип уже заметен в РФ."],["Дифференциация через дизайн","Материал не уникален, важны принты и размерная сетка."]],evidence:["WB/Ozon · medium presence","Amazon · strong review mass","Lazada · broad offer density","Supplier Probe · 31 matches"]},
      {title:"Ребристый коврик для душевой зоны",desc:"Raised rib · fast drainage · anti-slip",score:79,transfer:77,gap:71,supplier:83,margin:"31–40%",retail:"₽2 200–3 600",supplierPrice:"$3.9–6.2",markets:{WB:48,Ozon:54,Amazon:78,Lazada:72},tags:["drainage","anti-slip","medium gap"],reasons:[["Функциональный архетип","Основной value — быстрое стекание воды."],["Стабильный cross-market presence","Есть на всех четырёх рынках."],["Средняя конкуренция","Нет явного пустого рынка."],["Поставщики доступны","Несколько типовых форматов OEM."]],evidence:["4-market presence","Supplier Probe · 16 matches","Review themes · drainage","RF offer density medium"]},
      {title:"Коврик с эффектом memory foam",desc:"Soft memory foam · washable · non-slip",score:74,transfer:65,gap:52,supplier:95,margin:"36–45%",retail:"₽1 500–2 700",supplierPrice:"$2.2–3.8",markets:{WB:71,Ozon:73,Amazon:76,Lazada:68},tags:["зрелый рынок","supplier rich","низкий gap"],reasons:[["Рынок зрелый","Архетип уже хорошо представлен в РФ."],["Supplier Availability высокий","Производство максимально доступно."],["Экономика хорошая","Но commodity-risk снижает score."],["Низкий Trend Transfer","Нет сильного рыночного расхождения."]],evidence:["WB/Ozon · high density","Amazon · mature cluster","Supplier Probe · 39 matches","Russia Gap low"]},
      {title:"Модульный коврик EVA",desc:"Interlocking EVA · wet zone · modular tiles",score:70,transfer:74,gap:69,supplier:89,margin:"33–42%",retail:"₽1 800–3 500",supplierPrice:"$2.9–5.1",markets:{WB:46,Ozon:49,Amazon:71,Lazada:79},tags:["modular","Lazada signal","niche"],reasons:[["Сильнее в Азии","Lazada signal выше остальных рынков."],["Нишевое применение","Не всегда воспринимается как домашний bath mat."],["Поставщики доступны","Много EVA factories."],["Потребуется точное позиционирование","Иначе товар смешивается с промышленными покрытиями."]],evidence:["Lazada · strong signal","Supplier Probe · 27 matches","WB/Ozon · niche presence","Category ambiguity"]},
    ]
  },
  led: {
    match: /лент|rgb|led|matter/i,
    query:"Светодиодные ленты",
    subtitle:"Ищем feature-комбинации, которые уже доказаны на зарубежных рынках, но не перегреты в РФ.",
    stats:{queries:48,pages:812,records:246,archetypes:42,candidates:20,suppliers:71,cost:0.81},
    scouts:{wb:{records:58,queries:11,pages:164},ozon:{records:61,queries:12,pages:178},amazon:{records:72,queries:14,pages:267},lazada:{records:55,queries:11,pages:203}},
    insight:{title:"Не сама RGB-лента, а комбинация Matter + адресные сегменты формирует новый gap",text:"Базовые RGBIC-ленты уже насыщены на всех рынках. Более интересный сигнал дают модели с Matter/Thread, зональным управлением и готовыми desktop/TV сценариями.",transfer:92},
    opportunities:[
      {title:"RGBIC + Matter / Thread",desc:"Addressable LED strip · Matter · smart home",score:90,transfer:92,gap:87,supplier:78,margin:"30–39%",retail:"₽3 900–6 500",supplierPrice:"$9–14",markets:{WB:41,Ozon:45,Amazon:91,Lazada:83},tags:["Matter","smart home","высокий gap"],reasons:[["Feature shift","Matter становится отличием от commodity RGBIC."],["Cross-market signal","Amazon/Lazada заметно сильнее WB/Ozon."],["Russia Gap высокий","Предложение с Matter пока ограничено."],["Sourcing доступен","Supplier Probe нашёл готовые контроллеры и комплекты."]],evidence:["Amazon · Matter cluster","Lazada · smart strip cluster","WB/Ozon · low Matter density","Supplier Probe · 14 matches"]},
      {title:"TV backlight с камерой",desc:"RGBIC backlight · camera sync · 55–75 inch",score:85,transfer:86,gap:76,supplier:81,margin:"28–37%",retail:"₽5 500–9 000",supplierPrice:"$14–22",markets:{WB:58,Ozon:62,Amazon:88,Lazada:79},tags:["TV sync","camera","medium-high gap"],reasons:[["Понятный use case","Отдельный сценарий вместо generic LED strip."],["Спрос подтверждён зарубежом","Сильная видимость на Amazon."],["Россия уже догоняет","Gap есть, но ниже лидера."],["Комплектность повышает чек","Камера и контроллер дают лучшую экономику."]],evidence:["Amazon · TV sync cluster","WB/Ozon · growing offer","Supplier Probe · 18 matches","Higher retail ticket"]},
      {title:"Desktop ambient kit",desc:"Monitor backlight · addressable · USB-C · app",score:81,transfer:84,gap:79,supplier:75,margin:"32–41%",retail:"₽3 200–5 500",supplierPrice:"$7–11",markets:{WB:43,Ozon:47,Amazon:83,Lazada:77},tags:["desktop","gaming","USB-C"],reasons:[["Отдельный сегмент","Не конкурирует напрямую со всей категорией LED strips."],["Высокий gap","На РФ-площадках меньше специализированных комплектов."],["Дешёвый sourcing","Компактный набор, низкая закупка."],["Нужен качественный софт","App quality — ключевой риск."]],evidence:["Amazon · gaming desk cluster","Lazada · monitor ambient","WB/Ozon · low specialization","Supplier Probe · 12 matches"]},
      {title:"Neon rope RGBIC",desc:"Flexible neon rope · diffused light · IP67",score:77,transfer:73,gap:58,supplier:93,margin:"35–44%",retail:"₽2 900–5 000",supplierPrice:"$5–9",markets:{WB:67,Ozon:70,Amazon:79,Lazada:78},tags:["mature","supplier rich","visual product"],reasons:[["Сильная визуальная категория","Хорошо продаётся через контент."],["Gap уже небольшой","Архетип достаточно представлен в РФ."],["Поставщики очень доступны","Много типовых OEM."],["Commodity risk","Легко уйти в ценовую конкуренцию."]],evidence:["4-market strong presence","Supplier Probe · 34 matches","Russia Gap medium-low","High offer density"]},
      {title:"Outdoor smart strip IP67",desc:"Outdoor RGBIC · IP67 · scene automation",score:74,transfer:78,gap:70,supplier:80,margin:"29–38%",retail:"₽4 500–7 500",supplierPrice:"$11–17",markets:{WB:48,Ozon:52,Amazon:81,Lazada:74},tags:["outdoor","IP67","seasonal"],reasons:[["Отдельный outdoor use case","Меньше прямых аналогов в РФ."],["Сезонность","Спрос чувствителен к сезону."],["Cross-market signal хороший","Amazon заметно сильнее WB/Ozon."],["Sourcing средний","IP-рейтинг требует проверки качества."]],evidence:["Amazon · outdoor cluster","WB/Ozon · moderate gap","Supplier Probe · 15 matches","Seasonality risk"]},
    ]
  }
};

const SUPPLIERS = [
  {name:"Ningbo OEM Factory A",source:"Alibaba",price:"$27–31",moq:"300",lead:"18–24 дн.",match:"94%"},
  {name:"Shenzhen Appliance Factory B",source:"Made‑in‑China",price:"$29–34",moq:"500",lead:"21–28 дн.",match:"91%"},
  {name:"Suzhou Private Label C",source:"Alibaba",price:"$28–36",moq:"200",lead:"24–30 дн.",match:"88%"},
  {name:"Guangdong OEM Works D",source:"Made‑in‑China",price:"$26–33",moq:"500",lead:"20–26 дн.",match:"86%"},
  {name:"Zhejiang Export Factory E",source:"Alibaba",price:"$31–37",moq:"300",lead:"18–25 дн.",match:"83%"}
];

const screens = ["home","run","results","detail"];
let activeDataset = DATASETS.vacuum;
let activeQuery = "";
let activeRunId = null;
let activeRunState = null;
let liveOpportunities = [];
let liveOpportunityCount = 0;
let pollTimer = null;
let runFinished = false;

function showScreen(name){
  screens.forEach(s=>document.getElementById("screen-"+s).classList.toggle("active",s===name));
  window.scrollTo(0,0);
  updateHermesContext(name);
}

function datasetFor(query){
  return Object.values(DATASETS).find(d=>d.match.test(query)) || DATASETS.vacuum;
}

document.querySelectorAll(".demo-query").forEach(btn=>{
  btn.addEventListener("click",()=>{
    document.getElementById("researchInput").value=btn.dataset.query;
    startResearch(btn.dataset.query);
  });
});
document.querySelectorAll("[data-home]").forEach(btn=>btn.addEventListener("click",()=>{
  stopPolling();
  activeRunId=null;
  activeRunState=null;
  liveOpportunities=[];
  history.replaceState(null,"",location.pathname);
  showScreen("home");
}));
document.getElementById("backResults").addEventListener("click",()=>showScreen("results"));
document.getElementById("historyBtn").addEventListener("click",showResearchHistory);

document.getElementById("researchForm").addEventListener("submit",e=>{
  e.preventDefault();
  const q=document.getElementById("researchInput").value.trim();
  if(!q){showToast("Введите категорию или название товара.");return;}
  startResearch(q);
});

async function apiRequest(path, options={}){
  const response=await fetch(path,{
    ...options,
    headers:{"content-type":"application/json",...(options.headers||{})}
  });
  if(!response.ok){
    let detail="API error "+response.status;
    try{
      const payload=await response.json();
      detail=payload.detail||detail;
    }catch(_){}
    throw new Error(detail);
  }
  return response.json();
}

async function startResearch(query){
  stopPolling();
  activeQuery=query;
  activeDataset=datasetFor(query);
  activeRunId=null;
  activeRunState=null;
  liveOpportunities=[];
  runFinished=false;
  document.getElementById("runTitle").textContent=query;
  setRunSubtitle(query);
  resetRunUI();
  showScreen("run");
  try{
    const run=await apiRequest("/api/research",{
      method:"POST",
      body:JSON.stringify({query})
    });
    activeRunId=run.id;
    activeDataset=DATASETS[run.dataset_key]||datasetFor(run.query);
    activeQuery=run.query;
    history.replaceState(null,"",location.pathname+"?run="+encodeURIComponent(run.id));
    applyRunState(run);
    startPolling();
  }catch(err){
    showRunError("Не удалось создать research run: "+err.message);
  }
}

function setRunSubtitle(query){
  const isSpecific=query.toLowerCase()!==activeDataset.query.toLowerCase();
  document.getElementById("runSubtitle").textContent=isSpecific
    ? "Проверяем конкретный товар, ищем его архетип, аналоги и cross-market gap."
    : activeDataset.subtitle;
}

function stopPolling(){
  if(pollTimer){
    clearInterval(pollTimer);
    pollTimer=null;
  }
}

function startPolling(){
  stopPolling();
  pollTimer=setInterval(pollRun,500);
}

async function pollRun(){
  if(!activeRunId)return;
  try{
    const run=await apiRequest("/api/research/"+activeRunId);
    applyRunState(run);
  }catch(err){
    stopPolling();
    showToast("Связь с Product Hunter API потеряна: "+err.message);
  }
}

function resetRunUI(){
  document.getElementById("progressBar").style.width="8%";
  document.getElementById("progressPercent").textContent="8%";
  document.getElementById("stageTitle").textContent="Создаём research run";
  document.getElementById("stageDescription").textContent="Сохраняем задачу и ставим первый job в очередь";
  document.getElementById("costValue").textContent="$0.00";
  document.getElementById("researchLog").innerHTML="";
  ["statQueries","statPages","statRecords","statArchetypes","statCandidates"].forEach(id=>document.getElementById(id).textContent="0");
  document.querySelectorAll(".pipe-step").forEach((el,i)=>{
    el.classList.toggle("active",i===0);
    el.classList.remove("done");
  });
  document.querySelectorAll(".pipeline>i").forEach(el=>el.classList.remove("done"));
  document.querySelectorAll(".scout").forEach(el=>{
    el.classList.remove("running","done");
    el.querySelector(".scout-state").textContent="ожидает";
    el.querySelector(".scout-count").textContent="0";
    el.querySelector(".mini-progress i").style.width="0";
    el.querySelector("footer span:first-child").textContent="0 запросов";
    el.querySelector("footer span:last-child").textContent="0 страниц";
  });
}

function applyRunState(run){
  activeRunId=run.id;
  activeRunState=run;
  activeQuery=run.query;
  activeDataset=DATASETS[run.dataset_key]||datasetFor(run.query);
  document.getElementById("runId").textContent="PH-"+run.id.slice(0,8).toUpperCase();
  document.getElementById("runTitle").textContent=run.query;
  setRunSubtitle(run.query);
  document.getElementById("stageTitle").textContent=run.stage_title;
  document.getElementById("stageDescription").textContent=run.stage_description;
  document.getElementById("progressPercent").textContent=run.progress+"%";
  document.getElementById("progressBar").style.width=run.progress+"%";
  document.getElementById("costValue").textContent="$"+Number(run.actual_cost_usd ?? run.estimated_cost_usd ?? 0).toFixed(2);

  const stageIndex=Number(run.stage_index||0);
  document.querySelectorAll(".pipe-step").forEach((el,i)=>{
    el.classList.toggle("active",i===stageIndex && run.status!=="completed");
    el.classList.toggle("done",i<stageIndex || run.status==="completed");
  });
  document.querySelectorAll(".pipeline>i").forEach((el,i)=>{
    el.classList.toggle("done",i<stageIndex || run.status==="completed");
  });

  const stats=run.stats||{};
  document.getElementById("statQueries").textContent=stats.queries||0;
  document.getElementById("statPages").textContent=stats.pages||0;
  document.getElementById("statRecords").textContent=stats.records||0;
  document.getElementById("statArchetypes").textContent=stats.archetypes||0;
  document.getElementById("statCandidates").textContent=stats.candidates||0;

  renderScoutState(run.scouts||{},stageIndex,run.status);
  renderRunEvents(run.events||[]);

  if(run.status==="completed" && !runFinished){
    runFinished=true;
    stopPolling();
    setTimeout(renderResults,260);
  }else if(run.status==="failed"){
    stopPolling();
    showRunError(run.error||"Research worker завершился с ошибкой");
  }
}

function renderScoutState(scouts,stageIndex,status){
  ["wb","ozon","amazon","lazada"].forEach(key=>{
    const el=document.querySelector('.scout[data-scout="'+key+'"]');
    const value=scouts[key]||{status:"waiting",records:0,queries:0,pages:0};
    const live=value.source==="live";
    const terminal=["done","partial","empty","failed","budget_blocked"].includes(value.status);
    const done=terminal || stageIndex>2 || status==="completed";
    const running=!done && stageIndex===2;
    el.classList.toggle("done",done);
    el.classList.toggle("running",running);
    el.classList.toggle("live-source",live);
    let state=done?"готово":running?"исследует":"ожидает";
    if(live){
      if(value.status==="failed") state="LIVE · ошибка";
      else if(value.status==="partial") state="LIVE · частично";
      else if(value.status==="empty") state="LIVE · нет данных";
      else if(value.status==="budget_blocked") state="LIVE · budget";
      else state="LIVE · "+state;
    }else if(done){
      state="DEMO · готово";
    }
    el.querySelector(".scout-state").textContent=state;
    el.querySelector(".scout-count").textContent=value.records||0;
    el.querySelector(".mini-progress i").style.width=done?"100%":running?"35%":"0";
    el.querySelector("footer span:first-child").textContent=(value.queries||0)+" запросов";
    el.querySelector("footer span:last-child").textContent=(value.pages||0)+" страниц";
  });
}

function renderRunEvents(events){
  const log=document.getElementById("researchLog");
  log.innerHTML=events.map(ev=>{
    const date=new Date(ev.created_at);
    const time=Number.isNaN(date.getTime())?"":date.toLocaleTimeString("ru-RU",{hour:"2-digit",minute:"2-digit",second:"2-digit"});
    const tool=(ev.meta||{}).stage && ev.stage_index>=1;
    return '<div class="log-line '+(tool?"tool":"")+'"><time>'+time+'</time><div><b>'+escapeHtml(ev.actor||"Hermes")+'</b> · '+escapeHtml(ev.message)+'</div></div>';
  }).join("");
  log.scrollTop=log.scrollHeight;
}

function showRunError(message){
  document.getElementById("stageTitle").textContent="Ошибка research run";
  document.getElementById("stageDescription").textContent=message;
  showToast(message);
}

document.getElementById("skipRun").addEventListener("click",async()=>{
  if(!activeRunId){
    showToast("Research run ещё создаётся.");
    return;
  }
  try{
    const run=await apiRequest("/api/research/"+activeRunId+"/skip",{method:"POST",body:"{}"});
    applyRunState(run);
  }catch(err){
    showToast("Не удалось завершить demo-run: "+err.message);
  }
});

async function showResearchHistory(){
  try{
    const data=await apiRequest("/api/research?limit=10");
    if(!data.items.length){
      showToast("История пока пуста.");
      return;
    }
    const latest=data.items[0];
    showToast("В PostgreSQL сохранено "+data.items.length+" последних run. Последний: «"+latest.query+"» · "+latest.status+" · "+latest.progress+"%.");
  }catch(err){
    showToast("Не удалось прочитать историю: "+err.message);
  }
}

async function resumeRunFromUrl(){
  const runId=new URLSearchParams(location.search).get("run");
  if(!runId)return;
  try{
    const run=await apiRequest("/api/research/"+encodeURIComponent(runId));
    activeRunId=run.id;
    activeRunState=run;
    activeQuery=run.query;
    activeDataset=DATASETS[run.dataset_key]||datasetFor(run.query);
    runFinished=false;
    if(run.status==="completed"){
      runFinished=true;
      renderResults();
      return;
    }
    resetRunUI();
    showScreen("run");
    applyRunState(run);
    startPolling();
  }catch(err){
    history.replaceState(null,"",location.pathname);
    showToast("Сохранённый research run не найден.");
  }
}

async function renderResults(){
  const d=activeDataset;
  const runStats=(activeRunState&&activeRunState.stats)||{};
  liveOpportunities=[];
  liveOpportunityCount=0;

  if(activeRunId){
    try{
      const live=await apiRequest("/api/research/"+activeRunId+"/live-opportunities?limit=5");
      liveOpportunities=live.items||[];
      liveOpportunityCount=Number(live.count||liveOpportunities.length);
    }catch(_){}
  }

  const hasLive=liveOpportunities.length>0;
  document.getElementById("resultQuery").textContent=activeQuery;
  document.getElementById("sumRecords").textContent=runStats.records ?? d.stats.records;
  document.getElementById("sumArchetypes").textContent=hasLive?liveOpportunityCount:(runStats.archetypes ?? d.stats.archetypes);
  const supplierRecords=Number((activeRunState&&activeRunState.supplier_records)||0);
  document.getElementById("sumSuppliers").textContent=hasLive?(supplierRecords||"—"):(runStats.supplier_matches ?? d.stats.suppliers);

  if(hasLive){
    const top=liveOpportunities[0];
    const transfer=Math.round((Number(top.foreign_signal||0)+Number(top.russia_gap||0))/2);
    document.getElementById("mainInsightTitle").textContent="Самый сильный live-сигнал: "+top.label;
    document.getElementById("mainInsightText").textContent=
      "Foreign Signal "+Number(top.foreign_signal||0).toFixed(0)+
      " против Russia Signal "+Number(top.russia_signal||0).toFixed(0)+
      ". Russia Gap "+Number(top.russia_gap||0).toFixed(0)+
      ", cross-market presence "+Number(top.cross_market_presence||0).toFixed(0)+"%.";
    document.getElementById("mainTransferScore").textContent=transfer;
    document.getElementById("opportunityList").innerHTML=liveOpportunities.map((o,i)=>liveOpportunityCard(o,i)).join("");
    document.querySelectorAll(".opp-card").forEach(card=>card.addEventListener("click",()=>openLiveOpportunity(Number(card.dataset.index))));
  }else{
    document.getElementById("mainInsightTitle").textContent=d.insight.title;
    document.getElementById("mainInsightText").textContent=d.insight.text;
    document.getElementById("mainTransferScore").textContent=d.insight.transfer;
    document.getElementById("opportunityList").innerHTML=d.opportunities.map((o,i)=>opportunityCard(o,i)).join("");
    document.querySelectorAll(".opp-card").forEach(card=>card.addEventListener("click",()=>openOpportunity(Number(card.dataset.index))));
  }

  lucide.createIcons();
  showScreen("results");
  renderResultLiveEvidence();
}

function liveOpportunityCard(o,i){
  const marketNames={wb:"WB",ozon:"Ozon",amazon:"Amazon",lazada:"Lazada"};
  const signals=o.market_signals||{};
  const marketBars=Object.entries(marketNames).map(([key,label])=>{
    const value=Number((signals[key]||{}).presence_score||0);
    return '<div class="market-bar '+((key==="wb"||key==="ozon")?"ru":"")+'"><span>'+label+'</span><i><em style="width:'+value+'%"></em></i><b>'+Math.round(value)+'</b></div>';
  }).join("");
  const transfer=Math.round((Number(o.foreign_signal||0)+Number(o.russia_gap||0))/2);
  const tags=[
    Number(o.member_count||0)+" live records",
    Number(o.market_count||0)+"/4 рынка",
    "signals_v1"
  ];
  return '<article class="opp-card live-derived" data-index="'+i+'">'+
    '<div class="rank">#'+(i+1)+'</div>'+
    '<div class="opp-copy"><strong>'+escapeHtml(o.label)+'</strong><small>Архетип из нормализованных live records</small><div class="opp-tags">'+tags.map(t=>'<span>'+escapeHtml(t)+'</span>').join("")+'</div></div>'+
    '<div class="market-bars">'+marketBars+'</div>'+
    '<div class="opp-scores">'+
      miniScore("Opportunity",Number(o.opportunity_score||0).toFixed(0))+
      miniScore("Trend Transfer",transfer)+
      miniScore("Russia Gap",Number(o.russia_gap||0).toFixed(0))+
      miniScore("Cross-market",Number(o.cross_market_presence||0).toFixed(0))+
    '</div>'+
    '<button class="opp-open"><i data-lucide="chevron-right"></i></button>'+
  '</article>';
}

function opportunityCard(o,i){
  const marketBars=Object.entries(o.markets).map(([m,v])=>'<div class="market-bar '+((m==="WB"||m==="Ozon")?"ru":"")+'"><span>'+m+'</span><i><em style="width:'+v+'%"></em></i><b>'+v+'</b></div>').join("");
  return '<article class="opp-card" data-index="'+i+'">'+
    '<div class="rank">#'+(i+1)+'</div>'+
    '<div class="opp-copy"><strong>'+o.title+'</strong><small>'+o.desc+'</small><div class="opp-tags">'+o.tags.map(t=>'<span>'+t+'</span>').join("")+'</div></div>'+
    '<div class="market-bars">'+marketBars+'</div>'+
    '<div class="opp-scores">'+
      miniScore("Opportunity",o.score)+miniScore("Trend Transfer",o.transfer)+miniScore("Russia Gap",o.gap)+miniScore("Supplier",o.supplier)+
    '</div>'+
    '<button class="opp-open"><i data-lucide="chevron-right"></i></button>'+
  '</article>';
}
function miniScore(label,value){return '<div class="mini-score"><span>'+label+'</span><b>'+value+'</b></div>';}

function openLiveOpportunity(index){
  const o=liveOpportunities[index];
  if(!o)return;

  const transfer=Math.round((Number(o.foreign_signal||0)+Number(o.russia_gap||0))/2);
  const marketNames={wb:"WB",ozon:"Ozon",amazon:"Amazon",lazada:"Lazada"};
  const signals=o.market_signals||{};

  document.getElementById("detailRank").textContent="#"+(index+1);
  document.getElementById("detailTitle").textContent=o.label;
  document.getElementById("detailDesc").textContent=
    Number(o.member_count||0)+" live records · "+
    Number(o.market_count||0)+"/4 рынка · score "+o.score_version;
  document.getElementById("detailScore").textContent=Number(o.opportunity_score||0).toFixed(0);
  const supplierRecords=Number((activeRunState&&activeRunState.supplier_records)||0);
  document.getElementById("marginRange").textContent="следующий этап";
  document.getElementById("retailRange").textContent="—";
  document.getElementById("supplierPrice").textContent=supplierRecords?"см. live offers":"—";
  document.getElementById("supplierSignal").textContent=supplierRecords?(supplierRecords+" offers"):"нет evidence";
  document.getElementById("russiaGap").textContent=Number(o.russia_gap||0).toFixed(0)+" / 100";

  const reasons=[
    ["Сильный зарубежный сигнал","Foreign Signal "+Number(o.foreign_signal||0).toFixed(0)+" против Russia Signal "+Number(o.russia_signal||0).toFixed(0)+"."],
    ["Russia Gap","Cross-sectional gap = "+Number(o.russia_gap||0).toFixed(0)+" / 100. Это не исторический прогноз продаж."],
    ["Cross-market presence","Архетип найден на "+Number(o.market_count||0)+" из 4 исследуемых рынков."],
    ["Evidence density",Number(o.member_count||0)+" нормализованных товаров · review mass score "+Number(o.review_mass_score||0).toFixed(0)+" · recurrence "+Number(o.feature_recurrence||0).toFixed(0)+"."]
  ];
  document.getElementById("reasonsList").innerHTML=reasons.map((item,i)=>
    '<div class="reason"><span>0'+(i+1)+'</span><div><strong>'+escapeHtml(item[0])+'</strong><small>'+escapeHtml(item[1])+'</small></div></div>'
  ).join("");

  const marketRows=Object.entries(marketNames).map(([key,label])=>{
    const value=Number((signals[key]||{}).presence_score||0);
    const count=Number((signals[key]||{}).offer_count||0);
    return '<div class="signal-row '+((key==="wb"||key==="ozon")?"ru":"")+'"><span>'+label+'</span><i><em style="width:'+value+'%"></em></i><b>'+Math.round(value)+' · '+count+'</b></div>';
  }).join("");
  document.getElementById("marketSignals").innerHTML=
    marketRows+
    '<div class="signal-row"><span>Transfer</span><i><em style="width:'+transfer+'%"></em></i><b>'+transfer+'</b></div>'+
    '<div class="signal-row ru"><span>Russia Gap</span><i><em style="width:'+Number(o.russia_gap||0)+'%"></em></i><b>'+Number(o.russia_gap||0).toFixed(0)+'</b></div>';

  document.getElementById("supplierBody").innerHTML=
    '<tr><td colspan="6"><strong>Загрузка live Supplier Probe…</strong></td></tr>';

  document.getElementById("evidenceGrid").innerHTML=(o.evidence||[]).map(item=>{
    const href=String(item.source_url||"").startsWith("http")?item.source_url:"#";
    const meta=[
      String(item.market||"").toUpperCase(),
      item.price_text||null,
      item.rating!=null?("★ "+item.rating):null,
      item.review_count!=null?(item.review_count+" отзывов"):null
    ].filter(Boolean).join(" · ");
    return '<a class="evidence-item" href="'+escapeHtml(href)+'" target="_blank" rel="noopener noreferrer"><span>LIVE '+escapeHtml(String(item.market||"").toUpperCase())+'</span><strong>'+escapeHtml(item.canonical_title||"Без названия")+'</strong><small>'+escapeHtml(meta||"source evidence")+'</small></a>';
  }).join("");

  lucide.createIcons();
  showScreen("detail");
  loadLiveSupplierOffers(index);
  loadLiveEconomics(index);
}

function formatRub(value){
  if(value==null)return "—";
  return new Intl.NumberFormat("ru-RU",{maximumFractionDigits:0}).format(Number(value))+" ₽";
}

function formatUsd(value){
  if(value==null)return "—";
  return "$"+Number(value).toFixed(2);
}

async function loadLiveEconomics(index){
  const margin=document.getElementById("marginRange");
  const retail=document.getElementById("retailRange");
  const supplier=document.getElementById("supplierPrice");
  const signal=document.getElementById("supplierSignal");
  const warning=document.querySelector(".econ-warning span");
  if(!margin || !retail || !supplier || !signal || !warning || !activeRunId)return;

  if(index!==0){
    margin.textContent="не рассчитано";
    retail.textContent="—";
    supplier.textContent="—";
    signal.textContent="deep search нужен";
    warning.textContent="Preliminary economics V1 рассчитывается только для TOP‑1, потому что live Supplier Probe пока запускается только для лидирующего архетипа.";
    return;
  }

  try{
    const data=await apiRequest("/api/research/"+activeRunId+"/economics");
    const archetypeId=Number(liveOpportunities[index]?.id||0);
    const item=(data.items||[]).find(x=>Number(x.archetype_id)===archetypeId) || (data.items||[])[0];

    if(!item){
      margin.textContent="нет расчёта";
      retail.textContent="—";
      supplier.textContent="—";
      signal.textContent="—";
      warning.textContent="Economics scenario ещё не сформирован для этого research run.";
      return;
    }

    const retailMin=item.retail_price_min;
    const retailMax=item.retail_price_max;
    const supplierMin=item.supplier_price_min_usd;
    const supplierMax=item.supplier_price_max_usd;

    retail.textContent=
      retailMin==null?"—":
      Number(retailMin)===Number(retailMax)?formatRub(retailMin):(formatRub(retailMin)+" – "+formatRub(retailMax));
    supplier.textContent=
      supplierMin==null?"—":
      Number(supplierMin)===Number(supplierMax)?formatUsd(supplierMin):(formatUsd(supplierMin)+" – "+formatUsd(supplierMax));
    signal.textContent=Number(item.supplier_evidence_count||0)+" price evidence";

    if(item.status==="ready" || item.status==="partial"){
      const m1=Number(item.contribution_margin_min);
      const m2=Number(item.contribution_margin_max);
      margin.textContent=(Math.abs(m1-m2)<0.05?m1.toFixed(1):(m1.toFixed(1)+" – "+m2.toFixed(1)))+"%";
      const a=item.assumptions||{};
      warning.textContent=
        (item.status==="partial"?"PARTIAL · ":"READY · ")+
        "live inputs + assumptions_v1: FX "+Number(a.fx_usd_rub||0).toFixed(0)+" ₽/$ (модельное допущение), marketplace "+Number(a.marketplace_fee_pct||0)+"%, ads "+Number(a.ad_spend_pct||0)+"%, returns "+Number(a.returns_pct||0)+"%, tax "+Number(a.tax_pct||0)+"%.";
    }else{
      margin.textContent="недостаточно данных";
      const notes=item.notes||{};
      warning.textContent=
        "INSUFFICIENT DATA · "+
        (notes.retail_issue||notes.supplier_issue||"нет сопоставимой retail/supplier evidence для безопасного расчёта.");
    }
  }catch(err){
    margin.textContent="ошибка";
    warning.textContent="Не удалось загрузить economics scenario: "+err.message;
  }
}

async function loadLiveSupplierOffers(index){
  const body=document.getElementById("supplierBody");
  if(!body || !activeRunId)return;

  if(index!==0){
    body.innerHTML='<tr><td colspan="6"><strong>Deep Supplier Search для этого архетипа — следующий этап.</strong><br>V1 Supplier Probe сейчас выполняется для TOP‑1 возможности.</td></tr>';
    return;
  }

  try{
    const data=await apiRequest("/api/research/"+activeRunId+"/supplier-evidence");
    const allOffers=data.offers||[];
    const alibaba=allOffers.filter(x=>x.source==="alibaba");
    const mic=allOffers.filter(x=>x.source==="made_in_china");
    const offers=[...alibaba.slice(0,3),...mic.slice(0,2)];
    const calls=data.search_calls||[];
    const total=Number(calls.reduce((sum,x)=>sum+Number(x.cost_usd||0),0)).toFixed(4);
    const cacheHits=calls.filter(x=>(x.response_meta||{}).cache_hit).length;

    if(!offers.length){
      body.innerHTML='<tr><td colspan="6"><strong>Supplier evidence пока не найден.</strong><br>Product Hunter не подменяет отсутствующие supplier fields выдуманными значениями.</td></tr>';
      return;
    }

    body.innerHTML=offers.map(item=>{
      const raw=String(item.source_url||"");
      const href=raw.startsWith("http")?raw:"#";
      const source=item.source==="made_in_china"?"Made-in-China":"Alibaba";
      let supplier=item.supplier_name||"";
      if(!supplier && href!=="#"){
        try{
          const host=new URL(href).hostname;
          if(source==="Made-in-China") supplier=host.split(".")[0];
        }catch(_){}
      }
      supplier=supplier||source+" supplier";
      const customization=item.customization_text?"OEM/ODM":"LIVE";
      return '<tr>'+
        '<td><a href="'+escapeHtml(href)+'" target="_blank" rel="noopener noreferrer"><strong>'+escapeHtml(supplier)+'</strong></a><br><small>'+escapeHtml(item.product_title||"Supplier offer")+'</small></td>'+
        '<td><span class="supplier-source">'+escapeHtml(source)+'</span></td>'+
        '<td>'+escapeHtml(item.price_text||"—")+'</td>'+
        '<td>'+escapeHtml(item.moq_text||"—")+'</td>'+
        '<td>'+escapeHtml(item.lead_time_text||"—")+'</td>'+
        '<td class="match">'+escapeHtml(customization)+'</td>'+
      '</tr>';
    }).join("")+
      '<tr><td colspan="6"><small>LIVE Supplier Probe · '+offers.length+' показано · $'+total+' новых search-затрат'+(cacheHits?' · cache '+cacheHits:'')+'. Пустые поля означают, что источник их не подтвердил.</small></td></tr>';
  }catch(err){
    body.innerHTML='<tr><td colspan="6">Не удалось загрузить supplier evidence: '+escapeHtml(err.message)+'</td></tr>';
  }
}

function openOpportunity(index){
  const o=activeDataset.opportunities[index];
  document.getElementById("detailRank").textContent="#"+(index+1);
  document.getElementById("detailTitle").textContent=o.title;
  document.getElementById("detailDesc").textContent=o.desc+" · архетип сформирован из cross-market evidence.";
  document.getElementById("detailScore").textContent=o.score;
  document.getElementById("marginRange").textContent=o.margin;
  document.getElementById("retailRange").textContent=o.retail;
  document.getElementById("supplierPrice").textContent=o.supplierPrice;
  document.getElementById("supplierSignal").textContent=o.supplier+" / 100";
  document.getElementById("russiaGap").textContent=o.gap+" / 100";
  document.getElementById("reasonsList").innerHTML=o.reasons.map((r,i)=>'<div class="reason"><span>0'+(i+1)+'</span><div><strong>'+r[0]+'</strong><small>'+r[1]+'</small></div></div>').join("");
  document.getElementById("marketSignals").innerHTML=Object.entries(o.markets).map(([m,v])=>'<div class="signal-row '+((m==="WB"||m==="Ozon")?"ru":"")+'"><span>'+m+'</span><i><em style="width:'+v+'%"></em></i><b>'+v+'</b></div>').join("")+
    '<div class="signal-row"><span>Transfer</span><i><em style="width:'+o.transfer+'%"></em></i><b>'+o.transfer+'</b></div>'+
    '<div class="signal-row ru"><span>Russia Gap</span><i><em style="width:'+o.gap+'%"></em></i><b>'+o.gap+'</b></div>';
  document.getElementById("supplierBody").innerHTML=SUPPLIERS.map(s=>'<tr><td><strong>'+s.name+'</strong></td><td><span class="supplier-source">'+s.source+'</span></td><td>'+s.price+'</td><td>'+s.moq+'</td><td>'+s.lead+'</td><td class="match">'+s.match+'</td></tr>').join("");
  document.getElementById("evidenceGrid").innerHTML=o.evidence.map((e,i)=>'<div class="evidence-item"><span>'+(i<2?"market scout":"evidence")+'</span><strong>'+e+'</strong><small>Fixture record · в live-версии здесь будет source URL и timestamp.</small></div>').join("");
  lucide.createIcons();
  showScreen("detail");
}

const drawer=document.getElementById("drawer");
const backdrop=document.getElementById("drawerBackdrop");
function openDrawer(){drawer.classList.add("open");backdrop.classList.add("open");}
function closeDrawer(){drawer.classList.remove("open");backdrop.classList.remove("open");}
document.getElementById("hermesOpen").addEventListener("click",openDrawer);
document.getElementById("floatingHermes").addEventListener("click",openDrawer);
document.getElementById("drawerClose").addEventListener("click",closeDrawer);
backdrop.addEventListener("click",closeDrawer);

function updateHermesContext(screen){
  const map={home:"новый поиск",run:"активный research run",results:"TOP‑5 opportunities",detail:"выбранный товарный архетип"};
  document.querySelector("#drawerContext span").textContent="Контекст: "+map[screen];
  const sets={
    home:["Как система начнёт поиск?","Какие данные считаются реальными?","Сколько стоит один run?"],
    run:["Что сейчас делает Hermes?","Почему не парсим весь маркетплейс?","Как работает Budget Guard?"],
    results:["Почему этот товар №1?","Что такое Trend Transfer?","Где самый большой Russia Gap?"],
    detail:["Почему этот архетип перспективен?","Как найдены поставщики?","Что в экономике модельное?"]
  };
  document.getElementById("suggestions").innerHTML=sets[screen].map(x=>'<button>'+x+'</button>').join("");
  document.querySelectorAll("#suggestions button").forEach(b=>b.addEventListener("click",()=>sendHermes(b.textContent)));
}

const hermesAnswers=[
  [/как система начн|начнёт поиск/i,"Сначала я определяю intent и расширяю запрос в набор продуктовых гипотез. Затем запускаю четыре Market Scout с доменными ограничениями, собираю доступные карточки и snippets, нормализую признаки и только после этого строю архетипы.","resolve_intent → expand_queries → collect_markets"],
  [/реальн.*данн|данные.*реаль/i,"WB, Ozon, Amazon и Lazada исследуются реальным OpenRouter web-search. Normalizer, Opportunity Score и Supplier Probe уже считаются из live evidence. Modelled пока остаётся только preliminary economics.","get_evidence_policy"],
  [/стоит|стоимост|budget/i,"Свежий market scan стоит около $0.054 за 8 web-search вызовов. Supplier Probe добавляет около $0.015 за Alibaba + Made-in-China. Повтор в течение 6 часов использует cache и может стоить $0 новых search-затрат.","get_budget_status"],
  [/почему не парсим|весь маркетплейс/i,"Полный обход дорог, хрупок и часто блокируется. Product Hunter использует adaptive sampling: расширяет запросы, собирает разнообразную выборку и прекращает поиск, когда новые запросы перестают давать новые архетипы.","explain_sampling_strategy"],
  [/почему.*№1|перв|почему.*архетип|перспектив/i,"Лидер выбирается по live-derived сигналам: foreign presence, Russia Gap, cross-market presence, review mass и feature recurrence. Supplier score пока не входит в live-формулу.","get_opportunity_score"],
  [/trend transfer/i,"Trend Transfer V1 — не прогноз продаж. Это индекс расхождения: архетип уже силён на зарубежных рынках, но заметно слабее представлен в РФ. Исторический lead/lag появится только после накопления собственных snapshots.","explain_trend_transfer"],
  [/поставщик/i,"Supplier Probe уже LIVE: ищет supplier product pages на Alibaba и Made-in-China. Price/MOQ сохраняются только если они видны в evidence; отсутствующие поля остаются пустыми.","probe_suppliers"],
  [/экономик.*модел|модельн.*эконом/i,"Economics V1 уже работает детерминированно: retail и supplier prices берутся из live evidence, а FX, marketplace fee, ads, returns, tax и logistics — из assumptions_v1. Если единицы или цены нельзя сопоставить, расчёт возвращает insufficient_data.","explain_economics_assumptions"]
];

function sendHermes(text){
  if(!text.trim())return;
  const chat=document.getElementById("chat");
  chat.insertAdjacentHTML("beforeend",'<div class="msg user"><div><p>'+escapeHtml(text)+'</p></div></div>');
  const answer=hermesAnswers.find(([re])=>re.test(text)) || [null,"Market evidence, нормализация, архетипы, TOP‑5 и Supplier Probe уже LIVE. Preliminary economics использует live inputs + assumptions_v1 и умеет отказываться от расчёта при недостатке evidence.","Product Hunter context"];
  setTimeout(()=>{
    chat.insertAdjacentHTML("beforeend",'<div class="msg assistant"><span><i data-lucide="bot"></i></span><div><p>'+answer[1]+'</p><div class="tool-call">'+answer[2]+'</div></div></div>');
    lucide.createIcons();chat.scrollTop=chat.scrollHeight;
  },220);
}
document.getElementById("chatForm").addEventListener("submit",e=>{e.preventDefault();const input=document.getElementById("chatInput");sendHermes(input.value);input.value="";});

function showToast(text){const t=document.getElementById("toast");t.querySelector("span").textContent=text;t.classList.add("show");clearTimeout(showToast.timer);showToast.timer=setTimeout(()=>t.classList.remove("show"),3000);}
function escapeHtml(str){return String(str).replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]));}

updateHermesContext("home");
resumeRunFromUrl();
lucide.createIcons();

async function showLiveEvidence(){
  if(!activeRunId){
    showToast("Сначала запустите исследование.");
    return;
  }
  const panel=document.getElementById("liveEvidencePanel");
  const button=document.getElementById("liveEvidenceBtn");
  if(!panel || !button)return;
  button.disabled=true;
  button.textContent="Загрузка…";
  try{
    const data=await apiRequest("/api/research/"+activeRunId+"/live-evidence");
    const allProducts=data.products||[];
    const products=[];
    ["wb","ozon","amazon","lazada"].forEach(market=>{
      products.push(...allProducts.filter(p=>p.market===market).slice(0,2));
    });
    const calls=data.search_calls||[];
    const total=calls.reduce((sum,x)=>sum+Number(x.cost_usd||0),0);
    const cacheHits=calls.filter(x=>(x.response_meta||{}).cache_hit).length;
    const items=products.length
      ? products.map(p=>{
          const raw=String(p.source_url||"");
          const href=/^https?:\/\//i.test(raw)?raw:"#";
          const market=String(p.market||"").toUpperCase();
          const meta=[
            market||null,
            p.price_text||null,
            p.rating!=null?("★ "+p.rating):null,
            p.review_count!=null?(p.review_count+" отзывов"):null
          ].filter(Boolean).join(" · ") || "данные из live search";
          return '<a class="live-evidence-item" href="'+escapeHtml(href)+'" target="_blank" rel="noopener noreferrer"><strong>'+escapeHtml(p.title||"Без названия")+'</strong><small>'+escapeHtml(meta)+'</small></a>';
        }).join("")
      : '<div class="live-evidence-item"><strong>Live records пока нет</strong><small>Market Scouts ещё выполняются или сработал fallback.</small></div>';
    const costs=calls.map((c,i)=>{
      const cached=(c.response_meta||{}).cache_hit;
      return '<span>'+String(c.market||"").toUpperCase()+' · '+(cached?'CACHE':'search '+(i+1))+': $'+Number(c.cost_usd||0).toFixed(4)+'</span>';
    }).join("");
    panel.innerHTML='<div class="live-evidence-head"><strong>Live Market Scouts · реальные найденные карточки</strong><span>'+products.length+' показано · $'+total.toFixed(4)+(cacheHits?' · cache '+cacheHits:'')+'</span></div><div class="live-evidence-list">'+items+'</div><div class="live-costs">'+costs+'</div>';
    panel.hidden=false;
  }catch(err){
    showToast("Не удалось загрузить live evidence: "+err.message);
  }finally{
    button.disabled=false;
    button.textContent="Показать live evidence";
  }
}

const liveEvidenceButton=document.getElementById("liveEvidenceBtn");
if(liveEvidenceButton){
  liveEvidenceButton.addEventListener("click",showLiveEvidence);
}


async function renderResultLiveEvidence(){
  const panel=document.getElementById("resultLiveEvidence");
  if(!panel || !activeRunId)return;
  try{
    const data=await apiRequest("/api/research/"+activeRunId+"/live-evidence");
    const calls=data.search_calls||[];
    const products=data.products||[];
    if(!calls.length && !products.length){panel.hidden=true;return;}
    const total=calls.reduce((sum,item)=>sum+Number(item.cost_usd||0),0);
    const cacheHits=calls.filter(x=>(x.response_meta||{}).cache_hit).length;
    const markets=[...new Set(products.map(p=>String(p.market||"").toUpperCase()).filter(Boolean))];
    panel.textContent="LIVE · "+markets.length+" рынка · "+products.length+" records · $"+total.toFixed(4)+(cacheHits?" · cache "+cacheHits:"");
    panel.hidden=false;
  }catch(err){
    panel.hidden=true;
  }
}