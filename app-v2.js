"use strict";
const root=document.querySelector('main');
const S={catalog:[],mode:'category',selected:new Set(),run:null,items:[],view:'home',epoch:0,timer:null,retries:0,creating:false};
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safeURL=x=>/^https?:\/\//i.test(String(x))?esc(x):'#';
const name=m=>S.catalog.find(x=>x.id===m)?.label||m;
const fmt=x=>x==null?'—':Number(x).toLocaleString('ru-RU',{maximumFractionDigits:2});
const quality={pending:'Исследование продолжается',partial:'Частичный результат',complete:'Исследование завершено',insufficient_data:'Недостаточно данных',legacy:'Архивный отчёт V1 · сохранён без пересчёта'};
const decisionLabel=x=>({NEEDS_DATA:'Нужны данные',TEST:'Можно тестировать',WATCH:'Наблюдать', 'NO-GO':'Сценарий невыгоден'}[x]||x);
const statuses={waiting:'Ожидает',running:'Исследует',done:'Готово',partial:'Частично',empty:'Нет данных',failed:'Ошибка',budget_blocked:'Лимит расходов',disabled:'Отключено',no_query_plan:'Нет поисковых запросов'};
function notice(t){const el=document.getElementById('toast');el.querySelector('span').textContent=t;el.classList.add('show');clearTimeout(notice.timer);notice.timer=setTimeout(()=>el.classList.remove('show'),7000);}
async function api(path,options={}){
  const response=await fetch(path,{...options,headers:{'Content-Type':'application/json'},signal:AbortSignal.timeout(20000)});
  if(!response.ok){let e=await response.json().catch(()=>({}));throw Error(Array.isArray(e.detail)?e.detail.map(x=>x.msg).join('; '):e.detail||'Ошибка '+response.status);}
  return response.json();
}
function reset(){S.epoch++;clearTimeout(S.timer);S.run=null;S.items=[];S.view='home';history.replaceState(null,'',location.pathname);home();}
function icons(){if(window.lucide)lucide.createIcons();}
function modeSet(mode){S.mode=mode;document.querySelectorAll('[data-mode]').forEach(b=>{b.classList.toggle('selected',b.dataset.mode===mode);b.setAttribute('aria-pressed',String(b.dataset.mode===mode));});}
function home(){
 S.view='home';root.innerHTML=`<section class="home-wrap v2-home"><div class="hero"><span class="eyebrow">PRODUCT HUNTER · ИССЛЕДОВАНИЕ ТОВАРОВ</span><h1>Что будем исследовать?</h1><p>Сравним площадки, найдём перспективные варианты и поставщиков. Рассчитаем экономику и объясним, каких данных пока не хватает.</p></div>
 <div class="mode-switch" role="group" aria-label="Режим исследования"><button data-mode="category" type="button">Анализ категории</button><button data-mode="product" type="button">Конкретный товар</button></div>
 <form id="researchForm" class="search-box"><label class="sr-only" for="researchInput">Категория или товар и характеристики</label><div class="search-main"><i data-lucide="search"></i><input id="researchInput" required minlength="2" maxlength="240" placeholder="Например, автомобильный чайник 12V"><button type="submit">Исследовать →</button></div>
 <div class="search-hint">Для товара укажите важные характеристики. Все пять этапов выполняются автоматически.</div>
 <fieldset class="market-picker"><legend>Площадки исследования <span id="marketCount"></span></legend><div class="market-options">${S.catalog.filter(x=>x.available).map(x=>`<label><input type="checkbox" value="${esc(x.id)}" ${S.selected.has(x.id)?'checked':''}><span><b>${esc(x.label)}</b><small>${x.country} · ${x.currency}</small></span></label>`).join('')}</div>
 <details><summary>Все площадки — ${S.catalog.length}</summary><div class="market-options unavailable">${S.catalog.filter(x=>!x.available).map(x=>`<label><input type="checkbox" disabled><span><b>${esc(x.label)}</b><small>Недоступно в демо</small></span></label>`).join('')}</div></details></fieldset></form>
 <div class="chips v2-examples">${['Вертикальные пылесосы','Коврики для ванной','Светодиодные ленты','Мини-принтер','Дорожная подушка'].map(q=>`<button type="button" class="chip" data-example="${esc(q)}">${esc(q)}</button>`).join('')}</div>
 <div class="journey">${['1 · Запрос','2 · Площадки','3 · Перспективные товары','4 · Поставщики','5 · Экономика и рекомендации'].map(x=>`<span>${x}</span>`).join('')}</div>
 <div class="transparency-note"><p><strong>Реальные источники, прозрачные допущения.</strong> Публичный поиск показывает выборку карточек. Индексы не равны продажам; объёмы в экономике — сценарии, не прогноз спроса. Лимит запросов — $1.50 на исследование.</p></div></section>`;
 document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>modeSet(b.dataset.mode));modeSet(S.mode);
 document.querySelectorAll('.market-picker input:not(:disabled)').forEach(i=>i.onchange=()=>{i.checked?S.selected.add(i.value):S.selected.delete(i.value);marketCount();});marketCount();
 document.querySelectorAll('[data-example]').forEach(b=>b.onclick=()=>{document.getElementById('researchInput').value=b.dataset.example;modeSet('category');document.getElementById('researchInput').focus();});
 document.getElementById('researchForm').onsubmit=async e=>{e.preventDefault();if(!S.selected.size){notice('Выберите хотя бы одну площадку');return;}await create(document.getElementById('researchInput').value.trim());};icons();
}
function marketCount(){document.getElementById('marketCount').textContent='· выбрано '+S.selected.size+' из 7';}
async function create(query){
 if(S.creating)return;S.creating=true;const epoch=++S.epoch;
 const button=document.querySelector('#researchForm button[type=submit]');button.disabled=true;button.textContent='Создаём…';
 try{const run=await api('/api/research',{method:'POST',body:JSON.stringify({query,analysis_mode:S.mode,selected_markets:[...S.selected]})});if(epoch!==S.epoch)return;S.run=run;S.items=[];S.view='run';history.replaceState(null,'','?run='+run.id);renderRun();schedule(300);}
 catch(e){notice(e.message);}finally{S.creating=false;if(document.contains(button)){button.disabled=false;button.textContent='Исследовать →';}}
}
function schedule(ms=1500){clearTimeout(S.timer);S.timer=setTimeout(poll,ms);}
async function poll(){
 const epoch=S.epoch,id=S.run?.id;if(!id)return;
 try{
  const run=await api('/api/research/'+id);if(epoch!==S.epoch||id!==S.run?.id)return;S.run=run;S.retries=0;
  if(run.stage_index>=4){const data=await api('/api/research/'+id+'/live-opportunities');if(epoch!==S.epoch)return;S.items=data.items;}
  if(S.view==='run')renderRun();
  if(!['completed','failed','cancelled'].includes(run.status))schedule();
 }catch(e){if(epoch!==S.epoch)return;S.retries++;if(S.retries===1)notice('Связь прервана. Пробуем восстановить…');schedule(Math.min(12000,1500*2**S.retries));}
}
function publicStage(r){return r.stage_index<=1?0:r.stage_index<=3?1:r.stage_index===4?2:r.stage_index===5?3:4;}
function renderRun(){
 const r=S.run,done=r.status==='completed',terminal=['completed','failed','cancelled'].includes(r.status);S.view='run';S.detail=null;
 root.innerHTML=`<section class="run-wrap v2-report"><button class="back-link" id="newSearch">← Новый поиск</button><div class="run-head"><div><span class="eyebrow">${r.analysis_mode==='product'?'АНАЛИЗ ТОВАРА':'АНАЛИЗ КАТЕГОРИИ'} · ${esc(r.id.slice(0,8))}</span><h1>${esc(r.query)}</h1><p>${r.status==='cancelled'?'Исследование отменено':r.status==='failed'?'Ошибка этапа':quality[r.quality]||''}</p></div><div class="budget-card"><span>Расходы исследования</span><strong>$${Number(r.actual_cost_usd||0).toFixed(4)}</strong><small>${r.result_summary?.cost_has_estimates?'Включает резерв неизвестной стоимости':'По ответам поставщиков API'} · лимит $1.50</small></div></div>
 <article class="panel run-progress"><div class="progress-top"><div><strong>${esc(r.status==='cancelled'?'Остановлено':r.stage_title)}</strong><span>${esc(r.error||(done?'Подтверждённые варианты и ограничения доступны в карточках':r.stage_description)||'')}</span></div><b>${r.progress}%</b></div><div class="progress-track"><i style="width:${Number(r.progress)}%"></i></div><div class="journey">${['Запрос','Площадки','Перспективные товары','Поставщики','Экономика и рекомендации'].map((x,i)=>`<span class="${done||i<publicStage(r)?'done':i===publicStage(r)?'active':''}">${i+1} · ${x}</span>`).join('')}</div></article>
 <div class="scout-grid v2-scouts">${(r.selected_markets||Object.keys(r.scouts)).map(m=>{const v=r.scouts[m]||{};return `<article class="scout"><header><b>${esc(name(m))}</b><span class="scout-state">${esc(statuses[v.status]||v.status)}</span></header><strong>${Number(v.records||0)}</strong><small>карточек в выборке</small></article>`;}).join('')}</div>
 ${(r.warnings||[]).length?`<details class="v2-warning"><summary>Ограничения исследования · ${r.warnings.length}</summary><ul>${r.warnings.map(w=>`<li>${esc(w)}</li>`).join('')}</ul></details>`:''}
 <div class="v2-section-head"><h2>${done?'Результаты исследования':'Кандидаты исследования'}</h2>${!terminal?'<button class="ghost" id="cancelRun">Остановить</button>':''}</div>
 <div class="v2-candidates">${S.items.length?S.items.map(card).join(''):`<article class="panel v2-empty">${terminal?'Подтверждённых кандидатов недостаточно. Измените запрос или набор площадок. Результаты из других категорий не подставляются.':'Здесь появятся кандидаты после анализа площадок. Затем система дополнит их поставщиками и экономикой.'}</article>`}</div>
 <details class="v2-log"><summary>Журнал исследования</summary>${(r.events||[]).map(x=>`<p><small>${new Date(x.created_at).toLocaleTimeString('ru-RU')}</small> ${esc(x.message)}</p>`).join('')}</details></section>`;
 document.getElementById('newSearch').onclick=reset;
 document.getElementById('cancelRun')?.addEventListener('click',async()=>{const epoch=S.epoch;try{const r=await api('/api/research/'+S.run.id+'/cancel',{method:'POST'});if(epoch===S.epoch){S.run=r;clearTimeout(S.timer);renderRun();}}catch(e){notice(e.message);}});
 document.querySelectorAll('[data-candidate]').forEach(b=>b.onclick=()=>detail(Number(b.dataset.candidate)));icons();
}
function card(c,i){
 const target=S.run.analysis_mode==='product'&&c.archetype_key==='target_product';const gap=c.explanation?.gap_available;
 return `<button class="panel v2-candidate" data-candidate="${c.id}"><div class="v2-card-title"><span class="badge">${target?'Исходный товар':S.run.analysis_mode==='product'?'Близкий вариант':'Кандидат '+(i+1)}</span><b>${esc(decisionLabel(c.decision)||'Предварительно')}</b></div><h3>${esc(c.label)}</h3><p>${c.member_count?`${c.member_count} карточек · ${c.market_count} площадок`:'Точное совпадение пока не подтверждено'}</p><div class="v2-score"><strong>${fmt(c.final_score??c.opportunity_score)}</strong><span>индекс перспективности, не продажи</span></div><small>Уверенность в данных: ${Math.round(Number(c.explanation?.confidence||0)*100)}%${gap?' · Russia Gap '+fmt(c.russia_gap):''}</small><span class="v2-card-link">Источники, поставщики и экономика →</span></button>`;
}
async function detail(id){
 const c=S.items.find(x=>Number(x.id)===id);if(!c)return;S.view='detail';S.detail=id;const epoch=S.epoch,rid=S.run.id;
 root.innerHTML=`<section class="run-wrap"><button class="back-link" id="backReport">← К исследованию</button><h1>${esc(c.label)}</h1><p>Загружаем поставщиков и расчёты…</p></section>`;document.getElementById('backReport').onclick=renderRun;
 try{
  const [supplier,eco]=await Promise.all([api('/api/research/'+rid+'/supplier-evidence?archetype_id='+id),api('/api/research/'+rid+'/economics')]);
  if(epoch!==S.epoch||S.view!=='detail'||S.detail!==id)return;
  const companies=supplier.shortlist||[];
  root.innerHTML=`<section class="run-wrap v2-detail"><button class="back-link" id="backReport">← К исследованию</button><span class="eyebrow">${esc(decisionLabel(c.decision)||'Предварительная оценка')}</span><h1>${esc(c.label)}</h1>
  <p>Оценка: ${fmt(c.final_score??c.opportunity_score)} / 100. ${esc(c.final_explanation?.scope||'Выборка публичных карточек; не оценка объёма продаж.')}</p>
  ${c.features?._differences?`<p class="v2-warning">Отличия и ограничения аналога: ${esc(c.features._differences)}</p>`:''}
  <article class="panel v2-block"><h2>Что найдено на площадках</h2><div class="v2-evidence">${(c.evidence||[]).map(x=>`<a href="${safeURL(x.source_url)}" target="_blank" rel="noopener noreferrer"><span class="badge">Источник · ${esc(name(x.market))}</span><strong>${esc(x.canonical_title)}</strong><small>${esc(x.price_text||'Цена не подтверждена')}${x.created_at?' · '+new Date(x.created_at).toLocaleDateString('ru-RU'):''}</small></a>`).join('')||'<p>Карточек с подтверждённым соответствием пока нет.</p>'}</div></article>
  <article class="panel v2-block"><h2>Поставщики · ${companies.length} компаний</h2><p>${companies.length<3?'Найдено меньше трёх идентифицированных компаний. Недостающие предложения не заменяются выдуманными.':'Кандидаты для запроса образца и коммерческих условий.'}</p><div class="v2-table-wrap"><table><thead><tr><th>Компания и предложение</th><th>Цена / MOQ</th><th>Соответствие</th><th>Срок</th></tr></thead><tbody>${companies.map(x=>`<tr><td><a href="${safeURL(x.source_url)}" target="_blank" rel="noopener noreferrer">${esc(x.supplier_name||x.company_key)}</a><small>${esc(x.product_title)}</small></td><td>${esc(x.price_text||'Не подтверждена')}<small>MOQ: ${esc(x.moq_text||'Нет данных')}</small></td><td><b>${x.verification?.match==='confirmed'?'Признаки совпадают':'Нужно уточнить'}</b><small>${esc(x.verification?.matched_features||'')}</small><small>${esc(x.verification?.differences||'')}</small></td><td>${esc(x.lead_time_text||'Нет данных')}</td></tr>`).join('')||'<tr><td colspan="4">Нет подтверждённых компаний. Поиск не является проверкой надёжности поставщика.</td></tr>'}</tbody></table></div></article>
  <article class="panel v2-block"><h2>Юнит-экономика и сценарии</h2><p>Курс и расходы — модельные допущения. Объёмы — сценарии, не прогноз заказов.</p><div id="economicsContent"></div></article></section>`;
  document.getElementById('backReport').onclick=()=>{renderRun();if(S.run.status==='completed')poll();};
  const items=eco.items.filter(x=>Number(x.archetype_id)===id);
  if(eco.version!==2){document.getElementById('economicsContent').innerHTML='<p>Архивный расчёт V1. Новые исследования поддерживают редактирование по площадкам.</p><pre>'+esc(JSON.stringify(items,null,2))+'</pre>';return;}
  if(!items.length){document.getElementById('economicsContent').innerHTML='<p>Расчёты появятся после этапа экономики. Вернитесь к исследованию, чтобы обновить результат.</p>';return;}
  economicView(items,id);
 }catch(e){if(epoch===S.epoch)notice('Не удалось загрузить данные: '+e.message);}
}
const labels={retail_price:'Цена продажи, валюта площадки',supplier_price_usd:'Закупка за единицу, USD',fx:'Курс: единиц валюты за 1 USD',batch_size:'Размер партии, шт.',shipping_unit:'Доставка единицы',import_pct:'Импортные расходы, %',fee_pct:'Комиссия площадки, %',fulfillment_unit:'Исполнение заказа за единицу',storage_unit:'Хранение за единицу',ads_pct:'Реклама, % выручки',returns_pct:'Возвраты, % выручки',tax_pct:'Налоговая нагрузка, %',launch_cost:'Разовые расходы запуска',monthly_units:'Сценарный темп продаж, шт./мес.'};
const origins={source:'Из источника',user:'Введено пользователем',modelled_assumption:'Модельное допущение',missing:'Нет данных'};
function economicView(items,id,chosen){
 const container=document.getElementById('economicsContent');const item=items.find(x=>x.market===chosen)||items[0];const r=item.result;
 container.innerHTML=`<div class="v2-eco-tabs">${items.map(x=>`<button class="ghost ${x.market===item.market?'selected':''}" data-market="${x.market}">${esc(name(x.market))} · ${x.currency}</button>`).join('')}</div><p><b>${item.country} · ${item.currency}</b> · ${r.evidence_quality==='sufficient'?'Сопоставимые ценовые источники':'Ценовые данные неполные'}</p>
 <form id="ecoForm"><div class="v2-inputs">${Object.entries(labels).map(([key,label])=>`<label>${label}<input name="${key}" type="number" step="${key==='batch_size'?'1':'any'}" min="${['retail_price','supplier_price_usd','fx','monthly_units'].includes(key)?'0.000001':key==='batch_size'?'1':'0'}" ${!['retail_price','supplier_price_usd','launch_cost','monthly_units'].includes(key)?'required':''} value="${item.inputs[key]??''}"><small class="origin-${item.provenance[key]}">${origins[item.provenance[key]]}</small></label>`).join('')}<label>Сценарные объёмы через запятую<input name="volumes" value="${item.inputs.volumes.join(', ')}" required><small>Не прогноз спроса</small></label></div><button class="primary" type="submit" ${S.run.status!=='completed'?'disabled':''}>Пересчитать без нового поиска</button><p id="ecoError" role="status"></p></form>
 ${r.status==='calculated'?`<div class="v2-eco-results">${[['Себестоимость с доставкой',r.landed_unit],['Расходы на единицу',r.total_unit_cost],['Вклад в прибыль / ед.',r.contribution_unit],['Маржа, %',r.margin_pct],['Предельное привлечение заказа',r.max_acquisition_cost],['Безубыточность, шт.',r.break_even_units],['Средства на закупку партии',r.inventory_cash],['Средства с запуском',r.launch_cash],['Окупаемость, мес.',r.payback_months]].map(([l,v])=>`<div><small>${l}</small><strong>${fmt(v)}</strong></div>`).join('')}</div><p>${esc(r.payback_note)}</p><table><thead><tr><th>Продано, шт.</th><th>Вклад в прибыль</th><th>После расходов запуска</th></tr></thead><tbody>${r.scenarios.map(x=>`<tr><td>${x.units}</td><td>${fmt(x.contribution)} ${item.currency}</td><td>${fmt(x.profit_after_launch)} ${item.currency}</td></tr>`).join('')}</tbody></table>`:'<div class="v2-warning">Не хватает сопоставимой цены продажи или закупки. Можно ввести подтверждённую цену вручную; это останется пользовательским сценарием.</div>'}
 <details><summary>Ценовые источники расчёта</summary>${[...item.evidence.retail,...item.evidence.suppliers].map(x=>`<p><a href="${safeURL(x.url)}" target="_blank" rel="noopener noreferrer">${esc(x.text)}</a> · ${esc(x.observed_at)}</p>`).join('')||'<p>Сопоставимые цены отсутствуют.</p>'}</details><h3>Рекомендации</h3><ul>${item.recommendations.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`;
 container.querySelectorAll('[data-market]').forEach(b=>b.onclick=()=>economicView(items,id,b.dataset.market));
 document.getElementById('ecoForm').onsubmit=async e=>{
  e.preventDefault();const inputs={};const form=new FormData(e.target);
  for(const [key] of Object.entries(labels)){const raw=form.get(key);const value=raw===''?null:Number(raw);if(value!==item.inputs[key])inputs[key]=value;}
  const vols=String(form.get('volumes')).split(',').map(x=>Number(x.trim()));if(JSON.stringify(vols)!==JSON.stringify(item.inputs.volumes))inputs.volumes=vols;
  const epoch=S.epoch,rid=S.run.id,button=e.target.querySelector('button');button.disabled=true;
  try{const updated=await api('/api/research/'+rid+'/economics/recalculate',{method:'POST',body:JSON.stringify({archetype_id:id,market:item.market,inputs})});if(epoch!==S.epoch||S.view!=='detail'||S.detail!==id)return;if(!document.contains(e.target))return;items[items.indexOf(item)]=updated;economicView(items,id,item.market);notice('Сценарий пересчитан; поисковых расходов нет');}
  catch(err){if(document.contains(e.target)){document.getElementById('ecoError').textContent=err.message;button.disabled=false;}}
 };
}
async function historyView(){
 clearTimeout(S.timer);S.epoch++;S.view='history';const epoch=S.epoch;
 root.innerHTML='<section class="run-wrap"><p>Загрузка истории…</p></section>';
 try{const data=await api('/api/research?limit=30');if(epoch!==S.epoch)return;root.innerHTML=`<section class="run-wrap"><button class="back-link" id="newSearch">← Новый поиск</button><h1>История исследований</h1><div class="v2-history">${data.items.map(x=>`<button class="panel" data-run="${x.id}"><strong>${esc(x.query)}</strong><span>${esc(x.analysis_mode==='product'?'Товар':'Категория')} · ${esc(x.status)} · $${Number(x.actual_cost_usd||0).toFixed(4)}</span><small>${new Date(x.created_at).toLocaleString('ru-RU')}</small></button>`).join('')||'История пуста'}</div></section>`;document.getElementById('newSearch').onclick=reset;document.querySelectorAll('[data-run]').forEach(b=>b.onclick=()=>resume(b.dataset.run));}catch(e){notice(e.message);}
}
async function resume(id){
 const epoch=++S.epoch;clearTimeout(S.timer);S.view='run';
 try{const r=await api('/api/research/'+encodeURIComponent(id));if(epoch!==S.epoch)return;S.run=r;S.items=[];history.replaceState(null,'','?run='+r.id);renderRun();poll();}catch(e){notice(e.message);reset();}
}
document.getElementById('historyBtn').onclick=historyView;
document.getElementById('hermesOpen').onclick=()=>notice('Hermes: исследование публичных источников → проверка вариантов → поставщики → сценарная экономика. Все рекомендации находятся в карточке кандидата.');
async function boot(){try{const data=await api('/api/marketplaces');S.catalog=data.items;S.selected=new Set(data.items.filter(x=>x.available).map(x=>x.id));home();const id=new URLSearchParams(location.search).get('run');if(id)resume(id);}catch(e){root.innerHTML='<section class="run-wrap"><h1>Нет связи с сервером</h1><p>Повторяем подключение…</p></section>';setTimeout(boot,5000);}}
boot();
