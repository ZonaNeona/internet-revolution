var opportunities = [
  {icon:"shirt",name:"Компактный дорожный отпариватель",meta:"Home & Travel · €35–50",score:86,demand:"Высокий",trend:"+31%",competition:"Средняя",margin:"28,4%",gaps:"3",gapLabel:"2 высокой ценности",decision:"TEST",decisionClass:"test"},
  {icon:"chef-hat",name:"Магнитная полка для специй",meta:"Kitchen Storage · €28–39",score:82,demand:"Высокий",trend:"+22%",competition:"Низкая",margin:"29,8%",gaps:"2",gapLabel:"1 высокой ценности",decision:"TEST",decisionClass:"test"},
  {icon:"dog",name:"Портативная мойка для лап",meta:"Pet Care · €22–32",score:79,demand:"Средний",trend:"+37%",competition:"Средняя",margin:"32,7%",gaps:"4",gapLabel:"2 высокой ценности",decision:"TEST",decisionClass:"test"},
  {icon:"archive",name:"Органайзер под раковину",meta:"Storage · €30–45",score:76,demand:"Высокий",trend:"+14%",competition:"Средняя",margin:"24,3%",gaps:"3",gapLabel:"сборка и материалы",decision:"WATCH",decisionClass:"watch"},
  {icon:"dumbbell",name:"Складная балансировочная доска",meta:"Fitness · €42–58",score:74,demand:"Средний",trend:"+43%",competition:"Высокая",margin:"27,6%",gaps:"2",gapLabel:"устойчивость",decision:"WATCH",decisionClass:"watch"},
  {icon:"fan",name:"Аккумуляторный вентилятор для палатки",meta:"Outdoor · €32–46",score:71,demand:"Сезонный",trend:"+28%",competition:"Высокая",margin:"25,4%",gaps:"2",gapLabel:"шум и батарея",decision:"WATCH",decisionClass:"watch"},
  {icon:"lamp-desk",name:"Компактная лампа для чтения",meta:"Home Office · €24–34",score:68,demand:"Средний",trend:"+9%",competition:"Средняя",margin:"26,2%",gaps:"1",gapLabel:"крепление",decision:"WATCH",decisionClass:"watch"},
  {icon:"bath",name:"Органайзер для душа без сверления",meta:"Bathroom · €27–40",score:64,demand:"Высокий",trend:"+12%",competition:"Высокая",margin:"23,1%",gaps:"3",gapLabel:"клей и коррозия",decision:"NO-GO",decisionClass:"no"}
];

var pages = {researches:"Исследования",opportunities:"Возможности",methodology:"Методика оценки"};

function opportunityRows(){
  return opportunities.map(function(o,i){
    var scoreClass=o.score>=78?"good":o.score>=70?"mid":"low";
    return "<tr data-opportunity='"+i+"'>"+
      "<td><div class='opp-name'><span class='opp-thumb'><i data-lucide='"+o.icon+"'></i></span><div><strong>"+o.name+"</strong><small>"+o.meta+"</small></div></div></td>"+
      "<td><span class='score "+scoreClass+"'>"+o.score+"</span></td>"+
      "<td><strong>"+o.demand+"</strong></td>"+
      "<td><span class='trend up'>"+o.trend+"</span></td>"+
      "<td><span class='competition'>"+o.competition+"</span></td>"+
      "<td><b>"+o.margin+"</b></td>"+
      "<td><div class='review-gap'><b>"+o.gaps+"</b><span>"+o.gapLabel+"</span></div></td>"+
      "<td><span class='recommendation "+o.decisionClass+"'>"+o.decision+"</span></td>"+
      "<td><button class='row-open'><i data-lucide='chevron-right'></i></button></td>"+
    "</tr>";
  }).join("");
}

function overviewHtml(){
  return [
    "<div class='detail-grid'>",
      "<article class='panel detail-card'>",
        "<div class='detail-card-header'><h3>Почему кандидат получил 86 баллов</h3><span class='mini-badge'>6 факторов</span></div>",
        "<div class='reason-list'>",
          reason("01","Спрос растёт быстрее категории","Поисковый интерес и число продаж выросли на 31% за 12 месяцев.","market","12 источников"),
          reason("02","Рынок не сконцентрирован у нескольких брендов","Top-10 продавцов контролируют около 43% наблюдаемого сегмента.","competitors","18 аналогов"),
          reason("03","Есть повторяющиеся продуктовые проблемы","Протечки, короткий кабель и неудобная заливка воды встречаются у нескольких лидеров.","reviews","417 отзывов"),
          reason("04","Экономика проходит целевой порог","Базовый сценарий даёт 28,4% contribution margin после рекламы и возвратов.","economics","формула"),
        "</div>",
      "</article>",
      "<article class='panel detail-card'>",
        "<div class='detail-card-header'><h3>Opportunity Score</h3><span class='score good'>86</span></div>",
        "<div class='factor-list'>",
          factor("Спрос","22 / 25",88,"устойчивый объём + рост"),
          factor("Динамика","14 / 15",93,"+31% за 12 месяцев"),
          factor("Конкуренция","16 / 20",80,"рынок фрагментирован"),
          factor("Review Gaps","14 / 15",93,"3 решаемые проблемы"),
          factor("Экономика","15 / 20",75,"28,4% при цели 25%"),
          factor("Риск","5 / 5",100,"нет блокирующего риска"),
        "</div>",
      "</article>",
    "</div>",
    "<div class='detail-grid equal' style='margin-top:10px'>",
      "<article class='panel detail-card'><h3>Что Product Hunter предлагает улучшить</h3>",
        gap("Герметичный съёмный резервуар","высокая ценность","18,2% негативных отзывов содержат жалобы на протечки. Проблема встречается у 6 из 9 основных аналогов.","1 181 упоминание","6 конкурентов"),
        gap("Кабель 2,5 м вместо 1,5–1,8 м","высокая ценность","Короткий кабель — второй по частоте сценарный недостаток, особенно в отелях и небольших помещениях.","739 упоминаний","5 конкурентов"),
      "</article>",
      "<article class='panel detail-card'><h3>Риски, которые ещё нужно закрыть</h3>",
        risk("Закупочная цена пока предварительная","Из 7 найденных поставщиков только 3 показывают публичную цену. Нужен RFQ."),
        risk("CPC в категории растёт","Базовый сценарий использует 12% рекламных расходов. При 17% маржа падает до 23,4%."),
        "<div class='callout' style='margin-top:10px'><i data-lucide='bot'></i><p><b>Hermes:</b> я бы не переводил товар в GO до получения хотя бы двух подтверждённых quotes. Сейчас правильное решение — TEST.</p></div>",
      "</article>",
    "</div>"
  ].join("");
}

function marketHtml(){
  return [
    "<div class='detail-grid'>",
      "<article class='panel detail-card'>",
        "<div class='detail-card-header'><h3>Динамика спроса · 12 месяцев</h3><span class='tag'>+31% г/г</span></div>",
        "<div class='market-chart'>",
          "<div class='gridline' style='top:25%'><span>100</span></div><div class='gridline' style='top:50%'><span>75</span></div><div class='gridline' style='top:75%'><span>50</span></div>",
          "<svg viewBox='0 0 700 150' preserveAspectRatio='none'><defs><linearGradient id='area' x1='0' y1='0' x2='0' y2='1'><stop offset='0%' stop-color='#62dda8' stop-opacity='.28'/><stop offset='100%' stop-color='#62dda8' stop-opacity='0'/></linearGradient></defs><path d='M0,124 L64,119 L128,116 L192,108 L256,111 L320,96 L384,91 L448,84 L512,69 L576,59 L640,42 L700,31 L700,150 L0,150 Z' fill='url(#area)'/><path d='M0,124 L64,119 L128,116 L192,108 L256,111 L320,96 L384,91 L448,84 L512,69 L576,59 L640,42 L700,31' fill='none' stroke='#67dda8' stroke-width='3'/></svg>",
          "<div class='months'><span>Ноя</span><span>Янв</span><span>Мар</span><span>Май</span><span>Июл</span><span>Сен</span><span>Окт</span></div>",
        "</div>",
      "</article>",
      "<article class='panel detail-card'><h3>Снимок рынка</h3>",
        "<div class='stat-list'>",
          stat("Медианная цена","€42,90","+4,1% г/г"),
          stat("Активных продавцов","73","+8 за квартал"),
          stat("Top-10 share","43%","низкая концентрация"),
          stat("Средний рейтинг","4,23","из 5,0"),
          stat("Медиана отзывов","684","у top-20"),
          stat("Новых листингов","14","за 90 дней"),
        "</div>",
      "</article>",
    "</div>",
    "<div class='detail-grid equal' style='margin-top:10px'>",
      "<article class='panel detail-card'><h3>Ценовые сегменты</h3><div class='theme-list'>",
        theme("€20–34","23%","бюджетные модели · высокая конкуренция ценой",23,""),
        theme("€35–50","51%","целевой сегмент · лучший баланс спроса и маржи",51,""),
        theme("€51–70","19%","премиальные модели · сильнее бренды",19,""),
        theme("€70+","7%","нишевый премиум",7,""),
      "</div></article>",
      "<article class='panel detail-card'><h3>Evidence</h3><div class='reason-list'>",
        "<div class='reason-row'><span><i data-lucide='shopping-bag'></i></span><div><strong>4 812 исходных листингов</strong><small>Собраны в текущем research run, затем нормализованы до 3 926 SKU.</small></div></div>",
        "<div class='reason-row'><span><i data-lucide='clock-3'></i></span><div><strong>12 временных срезов</strong><small>Для fixture-демо сохранена история по ключевым рыночным признакам.</small></div></div>",
      "</div></article>",
    "</div>"
  ].join("");
}

function competitorsHtml(){
  return [
    "<article class='panel detail-card'>",
      "<div class='detail-card-header'><div><h3>Смысловые аналоги</h3><p style='font-size:10px;color:#667b73;margin:4px 0 0'>Из 73 листингов система оставила 18 реальных аналогов по сценарию использования, мощности и цене.</p></div><span class='tag'>18 из 73</span></div>",
      "<div class='data-table'><table><thead><tr><th>Конкурент</th><th>Цена</th><th>Рейтинг</th><th>Отзывы</th><th>Semantic match</th><th>Основная слабость</th><th>Статус</th></tr></thead><tbody>",
        competitor("SteamGo Mini 1200","€39,99","4,3","2 184",94,"протечки","аналог",""),
        competitor("VapoTrip S2","€44,90","4,1","1 736",91,"короткий кабель","аналог",""),
        competitor("QuickPress Compact","€37,50","4,0","1 221",89,"заливка воды","аналог",""),
        competitor("TravelSteam Pro","€49,90","4,5","918",87,"цена","аналог",""),
        competitor("HomePress 1800","€32,90","4,2","764",63,"другой сценарий","исключён","warn"),
      "</tbody></table></div>",
    "</article>",
    "<div class='detail-grid equal' style='margin-top:10px'>",
      "<article class='panel detail-card'><h3>Почему исключены 55 товаров</h3><div class='theme-list'>",
        theme("Другая мощность / форм-фактор","21","не конкурируют в целевом сценарии",38,""),
        theme("Другой ценовой сегмент","17","существенно дешевле или дороже",31,""),
        theme("Аксессуары и нерелевантные листинги","11","семантическая ошибка исходной выдачи",20,""),
        theme("Недостаточно данных","6","нет устойчивых признаков для сравнения",11,""),
      "</div></article>",
      "<article class='panel detail-card'><h3>Как это работает</h3>",
        "<div class='callout'><i data-lucide='sparkles'></i><p><b>AI-слой</b> строит semantic similarity по названию, характеристикам и сценарию использования. После этого детерминированные фильтры проверяют цену, мощность и обязательные признаки.</p></div>",
        "<div class='callout' style='margin-top:8px'><i data-lucide='shield-check'></i><p>В score попадают только аналоги, которые прошли оба слоя. LLM не может самовольно добавить товар в расчёт.</p></div>",
      "</article>",
    "</div>"
  ].join("");
}

function reviewsHtml(){
  return [
    "<div class='review-summary'>",
      "<article><span>Проанализировано</span><strong>6 482</strong><small>отзывов на 18 аналогов</small></article>",
      "<article><span>Негативных сигналов</span><strong>2 941</strong><small>после дедупликации тем</small></article>",
      "<article><span>Product Gaps</span><strong>3</strong><small>2 высокой ценности</small></article>",
    "</div>",
    "<div class='detail-grid equal'>",
      "<article class='panel detail-card'><div class='detail-card-header'><h3>Основные проблемы покупателей</h3><span class='tag warn'>negative themes</span></div><div class='theme-list'>",
        theme("Протекает резервуар","18,2%","1 181 упоминание · 6 из 9 ключевых аналогов",82,"negative"),
        theme("Короткий кабель","11,4%","739 упоминаний · особенно часто у travel-сценариев",51,"negative"),
        theme("Неудобно заливать воду","8,7%","564 упоминания · узкая горловина",39,"negative"),
        theme("Слабая упаковка","6,1%","395 упоминаний · повреждения при доставке",28,"negative"),
      "</div></article>",
      "<article class='panel detail-card'><div class='detail-card-header'><h3>Что покупателям нравится</h3><span class='tag'>positive themes</span></div><div class='theme-list'>",
        theme("Быстро нагревается","19,8%","1 284 положительных упоминания",89,""),
        theme("Компактность","13,8%","894 упоминания",62,""),
        theme("Удобно брать в поездку","9,7%","629 упоминаний",44,""),
      "</div></article>",
    "</div>",
    "<div class='detail-grid equal' style='margin-top:10px'>",
      "<article class='panel detail-card'><h3>Product Gaps</h3>",
        gap("01 · Герметичный съёмный резервуар","ценность 92/100","Закрывает крупнейшую проблему и одновременно упрощает заливку воды.","1 181 evidence","6 конкурентов"),
        gap("02 · Кабель 2,5 м","ценность 84/100","Простое изменение спецификации, закрывающее второй по частоте complaint cluster.","739 evidence","5 конкурентов"),
        gap("03 · Усиленная внутренняя упаковка","ценность 63/100","Снижает риск повреждения, но увеличивает COGS примерно на €0,18.","395 evidence",""),
      "</article>",
      "<article class='panel detail-card'><h3>Примеры evidence</h3><div class='quote-list'>",
        quote("После двух поездок резервуар начал подтекать в месте соединения.","анонимизированный fixture · рейтинг 2/5 · кластер «протечки»"),
        quote("Хороший размер для чемодана, но розетка должна быть почти рядом с зеркалом.","анонимизированный fixture · рейтинг 3/5 · кластер «кабель»"),
        quote("Нагревается очень быстро, в командировках реально удобно.","анонимизированный fixture · рейтинг 5/5 · кластер «быстрый нагрев»"),
      "</div><button class='btn secondary evidence-link' data-evidence='reviews' style='margin-top:10px'>Показать evidence выборку</button></article>",
    "</div>"
  ].join("");
}

function economicsHtml(){
  return [
    "<div class='detail-grid'>",
      "<article class='panel detail-card'><div class='detail-card-header'><h3>Unit Economics · базовый сценарий</h3><span class='tag'>500 шт.</span></div>",
        "<div class='waterfall'>",
          wf("€42,90","90","Цена<br>продажи",""),wf("-€8,70","44","Закупка","negative"),wf("-€3,10","26","Логистика","negative"),wf("-€1,92","18","Пошлины","negative"),wf("-€7,46","38","Комиссия","negative"),wf("-€5,20","31","Fulfillment","negative"),wf("-€3,80","27","Реклама","negative"),wf("-€0,54","10","Возвраты","negative"),wf("€12,18","52","Contribution<br>profit","result"),
        "</div>",
      "</article>",
      "<article class='panel detail-card'><div class='detail-card-header'><h3>Формула</h3><span class='tag'>28,4%</span></div><div class='econ-formula'>",
        econ("Цена продажи","€42,90",""),econ("Закупочная цена","− €8,70",""),econ("Международная логистика","− €3,10",""),econ("Пошлины","− €1,92",""),econ("Marketplace fee","− €7,46",""),econ("Fulfillment","− €5,20",""),econ("Реклама","− €3,80",""),econ("Возвраты","− €0,54",""),econ("Contribution profit","€12,18 · 28,4%","result"),
      "</div></article>",
    "</div>",
    "<div class='detail-grid equal' style='margin-top:10px'>",
      "<article class='panel detail-card'><h3>Sensitivity analysis</h3><div class='data-table sensitivity-table'><table><thead><tr><th>Сценарий</th><th>Изменение</th><th>Маржа</th><th>Результат</th></tr></thead><tbody>",
        "<tr><td><strong>Базовый</strong></td><td>—</td><td class='positive'>28,4%</td><td><span class='recommendation test'>TEST</span></td></tr>",
        "<tr><td><strong>Закупка дорожает</strong></td><td>+10%</td><td class='positive'>26,4%</td><td><span class='recommendation test'>TEST</span></td></tr>",
        "<tr><td><strong>Реклама дорожает</strong></td><td>12% → 17%</td><td class='negative'>23,4%</td><td><span class='recommendation watch'>WATCH</span></td></tr>",
        "<tr><td><strong>Цена продажи падает</strong></td><td>−10%</td><td class='negative'>21,2%</td><td><span class='recommendation no'>NO-GO</span></td></tr>",
      "</tbody></table></div></article>",
      "<article class='panel detail-card'><h3>Пересчитать сценарий</h3><div class='callout'><i data-lucide='bot'></i><p>В финальной версии можно написать Hermes: <b>«Пересчитай при закупке $9,20 и рекламе 15%»</b>. Он вызовет deterministic calculator и сохранит новый сценарий, а не посчитает цифры в тексте.</p></div><button class='btn secondary hermes-open' style='margin-top:10px'><i data-lucide='bot'></i> Спросить Hermes</button></article>",
    "</div>"
  ].join("");
}

function suppliersHtml(){
  return [
    "<div class='detail-grid'>",
      "<article class='panel detail-card'><div class='detail-card-header'><div><h3>Shortlist поставщиков</h3><p style='font-size:10px;color:#657a72;margin:4px 0 0'>Из 34 найденных фабрик 7 прошли первичный фильтр, 4 соответствуют ограничениям.</p></div><span class='tag'>4 подходят</span></div>",
        supplier("Ningbo Steam Appliances Co.","score 91","$7,90","500","21 день","Да","поддерживает съёмный резервуар · private label","проходит",""),
        supplier("Shenzhen Travel Electric Ltd.","score 87","$7,40","1 000","18 дней","Да","цена ниже, но MOQ превышает лимит исследования","нужен RFQ","warn"),
        supplier("Guangzhou HomeTech Factory","score 84","$8,15","300","24 дня","Да","готовы изменить кабель и внутреннюю упаковку","проходит",""),
      "</article>",
      "<article class='panel detail-card'><h3>Следующее действие</h3>",
        "<div class='callout'><i data-lucide='bot'></i><p><b>Hermes:</b> предлагаю запросить у трёх фабрик цену для партии 500 шт., стоимость съёмного резервуара и кабеля 2,5 м.</p></div>",
        "<div class='human-actions' style='margin-top:10px'><div class='human-action'><span><i data-lucide='mail'></i></span><div><strong>RFQ подготовлен</strong><small>3 поставщика · 7 вопросов · английский язык</small></div><button data-approval='rfq'>Посмотреть</button></div></div>",
        "<div class='risk-list' style='margin-top:10px'>"+risk("Цена пока не подтверждена","Экономика использует публичные / fixture quote values. Финальный score должен обновиться после RFQ.")+"</div>",
      "</article>",
    "</div>"
  ].join("");
}

function decisionHtml(){
  return [
    "<div class='decision-hero'><div><span class='eyebrow'>ИТОГ PRODUCT HUNTER</span><h2>Рекомендация: TEST</h2><p>Товар проходит пороги спроса, конкуренции и экономики, а два крупнейших review gaps можно закрыть изменением спецификации. До GO нужно подтвердить закупочную цену.</p></div><div class='decision-score'><strong>82%</strong><span>confidence</span></div></div>",
    "<div class='detail-grid equal'>",
      "<article class='panel detail-card'><h3>Почему стоит тестировать</h3><div class='reason-list'>",
        reason("01","Спрос +31% за 12 месяцев","Категория растёт без резкого роста концентрации лидеров.","",""),
        reason("02","Top-10 контролируют только 43%","Есть пространство для нового предложения.","",""),
        reason("03","Два сильных Product Gaps","Протечки и короткий кабель можно закрыть спецификацией.","",""),
        reason("04","Базовая маржа 28,4%","Выше установленного порога 25%.","",""),
      "</div></article>",
      "<article class='panel detail-card'><h3>Что может изменить решение</h3><div class='risk-list'>",
        risk("RFQ выше $9,70","При прочих равных экономика приблизится к минимальному порогу."),
        risk("Рекламные расходы >17%","Сценарий становится ниже целевой маржи."),
        risk("Сертификация увеличит fixed costs","Нужно проверить конкретную конфигурацию продукта."),
      "</div></article>",
    "</div>",
    "<div class='detail-grid equal' style='margin-top:10px'>",
      "<article class='panel detail-card'><div class='detail-card-header'><h3>Evidence coverage</h3><span class='tag'>96%</span></div><div class='factor-list'>",
        factor("Рынок","100%",100,"12 источников / срезов"),
        factor("Конкуренты","100%",100,"18 подтверждённых аналогов"),
        factor("Отзывы","100%",100,"6 482 записи"),
        factor("Экономика","100%",100,"воспроизводимая формула"),
        factor("Поставщики","80%",80,"не хватает подтверждённых quotes"),
      "</div></article>",
      "<article class='panel detail-card'><h3>Решения остаются человеку</h3><div class='human-actions'>",
        approval("package-check","Подтвердить целевую спецификацию","съёмный резервуар · кабель 2,5 м · усиленная упаковка","spec"),
        approval("send","Подтвердить отправку RFQ","3 выбранных фабрики","rfq"),
      "</div><div class='callout' style='margin-top:10px'><i data-lucide='shield-check'></i><p>Product Hunter автоматизирует исследование, но не отправляет запросы и не переводит товар в запуск без подтверждения пользователя.</p></div></article>",
    "</div>"
  ].join("");
}

function reason(n,title,text,evidence,label){
  var button=evidence?"<button class='evidence-link' data-evidence='"+evidence+"'>"+label+"</button>":"";
  return "<div class='reason-row'><span>"+n+"</span><div><strong>"+title+"</strong><small>"+text+"</small></div>"+button+"</div>";
}
function risk(title,text){return "<div class='risk-row'><span>!</span><div><strong>"+title+"</strong><small>"+text+"</small></div></div>";}
function factor(name,val,width,small){return "<div class='factor'><span>"+name+"</span><b>"+val+"</b><i><em style='width:"+width+"%'></em></i><small>"+small+"</small></div>";}
function gap(title,badge,text,a,b){
  var foot=a?"<footer><span class='tag'>"+a+"</span>"+(b?"<span class='tag blue'>"+b+"</span>":"")+"</footer>":"";
  return "<div class='gap-card'><header><strong>"+title+"</strong><span class='tag'>"+badge+"</span></header><p>"+text+"</p>"+foot+"</div>";
}
function stat(label,value,small){return "<div class='stat-box'><span>"+label+"</span><strong>"+value+"</strong><small>"+small+"</small></div>";}
function theme(title,value,small,width,cls){return "<div class='theme-row "+cls+"'><strong>"+title+"</strong><b>"+value+"</b><small>"+small+"</small><i><em style='width:"+width+"%'></em></i></div>";}
function competitor(name,price,rating,reviews,match,weak,status,cls){return "<tr><td><strong>"+name+"</strong></td><td>"+price+"</td><td>"+rating+"</td><td>"+reviews+"</td><td><span class='similarity'>"+match+"% <i><em style='width:"+match+"%'></em></i></span></td><td>"+weak+"</td><td><span class='tag "+cls+"'>"+status+"</span></td></tr>";}
function quote(text,small){return "<div class='review-quote'><p>«"+text+"»</p><small>"+small+"</small></div>";}
function wf(value,height,label,cls){return "<div class='waterfall-item "+cls+"'><b>"+value+"</b><i style='height:"+height+"%'></i><span>"+label+"</span></div>";}
function econ(label,value,cls){return "<div class='econ-row "+cls+"'><span>"+label+"</span><b>"+value+"</b></div>";}
function supplier(name,score,price,moq,lead,custom,small,status,cls){return "<div class='supplier-card'><header><strong>"+name+"</strong><span>"+score+"</span></header><div class='supplier-meta'><div><span>Цена</span><b>"+price+"</b></div><div><span>MOQ</span><b>"+moq+"</b></div><div><span>Lead time</span><b>"+lead+"</b></div><div><span>Кастомизация</span><b>"+custom+"</b></div></div><div class='supplier-footer'><small>"+small+"</small><span class='tag "+cls+"'>"+status+"</span></div></div>";}
function approval(icon,title,small,type){return "<div class='human-action'><span><i data-lucide='"+icon+"'></i></span><div><strong>"+title+"</strong><small>"+small+"</small></div><button data-approval='"+type+"'>Рассмотреть</button></div>";}

var tabHtml={overview:overviewHtml(),market:marketHtml(),competitors:competitorsHtml(),reviews:reviewsHtml(),economics:economicsHtml(),suppliers:suppliersHtml(),decision:decisionHtml()};

function renderOpportunities(){
  var body=document.getElementById("opportunityBody");
  body.innerHTML=opportunityRows();
  body.querySelectorAll("tr").forEach(function(row){row.addEventListener("click",function(){openOpportunity(Number(row.dataset.opportunity));});});
}

function renderTabs(){
  Object.keys(tabHtml).forEach(function(key){var el=document.getElementById("tab-"+key);if(el)el.innerHTML=tabHtml[key];});
  bindDynamicActions();
}

function switchView(view){
  document.querySelectorAll(".view").forEach(function(v){v.classList.remove("active");});
  var target=document.getElementById("view-"+view);
  if(target)target.classList.add("active");
  document.querySelectorAll(".nav-item").forEach(function(n){n.classList.toggle("active",n.dataset.view===view);});
  document.getElementById("pageTitle").textContent=pages[view]||"Товарная возможность";
  window.scrollTo(0,0);
}
document.querySelectorAll(".nav-item").forEach(function(btn){btn.addEventListener("click",function(){switchView(btn.dataset.view);});});

function openOpportunity(index){
  var o=opportunities[index]||opportunities[0];
  document.querySelector("#view-opportunity-detail .opp-title h1").textContent=o.name;
  document.querySelector("#view-opportunity-detail .opp-title p").textContent=o.meta+" · Amazon DE · обнаружен 7 октября 2026";
  document.querySelector("#view-opportunity-detail .hero-score strong").textContent=o.score;
  var rec=document.querySelector("#view-opportunity-detail .opp-decision .recommendation");
  rec.textContent=o.decision;rec.className="recommendation "+o.decisionClass;
  switchView("opportunity-detail");activateTab("overview");updateHermesContext("opportunity");lucide.createIcons();
}
function activateTab(tab){
  document.querySelectorAll("#detailTabs button").forEach(function(b){b.classList.toggle("active",b.dataset.tab===tab);});
  document.querySelectorAll(".tab-pane").forEach(function(p){p.classList.toggle("active",p.id==="tab-"+tab);});
  updateHermesContext(tab);lucide.createIcons();
}
document.querySelectorAll("#detailTabs button").forEach(function(btn){btn.addEventListener("click",function(){activateTab(btn.dataset.tab);});});
document.getElementById("backToOpps").addEventListener("click",function(){switchView("opportunities");});
document.querySelectorAll("[data-open-research]").forEach(function(el){el.addEventListener("click",function(e){e.stopPropagation();switchView("opportunities");});});

var drawer=document.getElementById("hermesDrawer");
var drawerBackdrop=document.getElementById("drawerBackdrop");
function openHermes(){drawer.classList.add("open");drawerBackdrop.classList.add("open");}
function closeHermes(){drawer.classList.remove("open");drawerBackdrop.classList.remove("open");}
document.querySelectorAll(".hermes-open").forEach(function(btn){btn.addEventListener("click",openHermes);});
document.getElementById("drawerClose").addEventListener("click",closeHermes);
drawerBackdrop.addEventListener("click",closeHermes);

var suggestions={
  "default":["Что сейчас исследуется?","Какие кандидаты сильнее 75?","Как считается Opportunity Score?"],
  "opportunity":["Почему оценка 86?","Покажи три главных риска","Что ещё нужно проверить?"],
  "market":["Почему считаем спрос растущим?","Насколько рынок концентрирован?","Покажи evidence по динамике"],
  "competitors":["Почему исключены 55 товаров?","Кто самый близкий аналог?","Где конкуренты слабее всего?"],
  "reviews":["Какая проблема самая ценная?","Покажи evidence по протечкам","Какие улучшения проще внедрить?"],
  "economics":["Пересчитай при закупке $9,20","Что сильнее всего влияет на маржу?","Когда сценарий станет NO-GO?"],
  "suppliers":["Кого запросить первым?","Найди MOQ до 500","Подготовь RFQ"],
  "decision":["Почему TEST, а не GO?","Что может изменить решение?","Какие действия ждут человека?"]
};
function updateHermesContext(ctx){
  ctx=ctx||"default";
  var contexts={
    opportunity:"Товар: Дорожный отпариватель · Opportunity 86",
    overview:"Товар: Дорожный отпариватель · Обзор",
    market:"Товар: Дорожный отпариватель · Рынок",
    competitors:"Товар: Дорожный отпариватель · Конкуренты",
    reviews:"Товар: Дорожный отпариватель · 6 482 отзыва",
    economics:"Товар: Дорожный отпариватель · Unit Economics",
    suppliers:"Товар: Дорожный отпариватель · 7 поставщиков",
    decision:"Товар: Дорожный отпариватель · Решение TEST"
  };
  document.querySelector("#drawerContext span").textContent="Контекст: "+(contexts[ctx]||"исследования Product Hunter");
  var key=suggestions[ctx]?ctx:(ctx==="overview"?"opportunity":"default");
  document.getElementById("chatSuggestions").innerHTML=(suggestions[key]||suggestions.default).map(function(x){return "<button>"+x+"</button>";}).join("");
  document.querySelectorAll("#chatSuggestions button").forEach(function(btn){btn.addEventListener("click",function(){sendHermes(btn.textContent);});});
}
updateHermesContext("default");

var hermesReplies=[
  {test:/почему.*86|оценк/i,reply:"Оценка 86 складывается из шести факторов: спрос 22/25, динамика 14/15, конкуренция 16/20, review gaps 14/15, экономика 15/20 и риск 5/5. Самые сильные сигналы — рост спроса и повторяющиеся проблемы у нескольких лидеров.",tool:"get_opportunity → score_breakdown"},
  {test:/риск/i,reply:"Три ключевых риска: закупочная цена пока не подтверждена RFQ; рекламные расходы могут поднять долю затрат выше 17%; для выбранной конфигурации нужно отдельно проверить сертификацию. Первый риск сейчас сильнее всего влияет на confidence.",tool:"get_opportunity → risks"},
  {test:/9[,.]20|пересчитай/i,reply:"В fixture-сценарии закупочная цена $9,20 снижает contribution margin примерно до 27%. Это всё ещё выше порога 25%, поэтому решение остаётся TEST. В рабочей версии Hermes вызовет deterministic calculator и сохранит сценарий.",tool:"calculate_economics · DEMO"},
  {test:/moq|500/i,reply:"Из текущего shortlist ограничения MOQ ≤500 проходят Ningbo Steam Appliances (500) и Guangzhou HomeTech (300). Shenzhen Travel Electric показывает MOQ 1 000 — для неё нужен запрос на снижение MOQ.",tool:"search_suppliers → filter(moq<=500)"},
  {test:/rfq/i,reply:"RFQ должен запросить цену для 500 шт., стоимость съёмного резервуара, кабеля 2,5 м, усиленной упаковки, lead time и условия private label. Отправка будет доступна только после human approval.",tool:"prepare_rfq · REVIEW_REQUIRED"},
  {test:/протеч|evidence/i,reply:"Кластер «протекает резервуар» содержит 1 181 упоминание и встречается у 6 из 9 ключевых аналогов. Это 18,2% негативных сигналов в текущей выборке. В интерфейсе этот вывод связан с исходной evidence-выборкой.",tool:"get_evidence → review_cluster"},
  {test:/test.*go|go.*test|почему.*test/i,reply:"Сейчас TEST, а не GO, потому что рыночная гипотеза и базовая экономика сильные, но закупочная цена ещё не подтверждена коммерческими предложениями. После двух-трёх RFQ система пересчитает economics и confidence.",tool:"get_decision → blockers"}
];
function escapeHtml(str){return String(str).replace(/[&<>"']/g,function(m){return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[m];});}
function sendHermes(text){
  if(!text.trim())return;
  var chat=document.getElementById("chat");
  chat.insertAdjacentHTML("beforeend","<div class='msg user'><div><p>"+escapeHtml(text)+"</p></div></div>");
  var data=hermesReplies.find(function(x){return x.test.test(text);})||{reply:"В демо этот вопрос пока отвечает fixture-слой. На этапе Hermes Orchestration тот же интерфейс будет вызывать Product Hunter tools и возвращать результат из сохранённого состояния исследования.",tool:"Product Hunter tool · planned"};
  setTimeout(function(){
    chat.insertAdjacentHTML("beforeend","<div class='msg assistant'><span class='msg-avatar'><i data-lucide='bot'></i></span><div><p>"+data.reply+"</p><div class='tool-call'><i data-lucide='wrench'></i><span>"+data.tool+"</span></div></div></div>");
    lucide.createIcons();chat.scrollTop=chat.scrollHeight;
  },260);
  chat.scrollTop=chat.scrollHeight;
}
document.getElementById("chatForm").addEventListener("submit",function(e){e.preventDefault();var input=document.getElementById("chatInput");sendHermes(input.value);input.value="";});

var modal=document.getElementById("researchModal");
var modalBackdrop=document.getElementById("modalBackdrop");
function openModal(){modal.classList.add("open");modalBackdrop.classList.add("open");}
function closeModal(){modal.classList.remove("open");modalBackdrop.classList.remove("open");}
document.getElementById("newResearchBtn").addEventListener("click",openModal);
document.getElementById("modalClose").addEventListener("click",closeModal);
document.getElementById("modalCancel").addEventListener("click",closeModal);
modalBackdrop.addEventListener("click",closeModal);
document.getElementById("oppResearchBtn").addEventListener("click",function(){showToast("Критерии: DE · Amazon DE · €25–70 · маржа ≥25% · MOQ ≤500");});

document.getElementById("researchForm").addEventListener("submit",function(e){
  e.preventDefault();
  var fd=new FormData(e.currentTarget);
  var record={category:fd.get("category"),marketplace:fd.get("marketplace"),priceMin:fd.get("priceMin"),priceMax:fd.get("priceMax"),margin:fd.get("margin"),moq:fd.get("moq")};
  localStorage.setItem("ph-last-research",JSON.stringify(record));
  var tr=document.createElement("tr");
  tr.innerHTML="<td><strong>"+escapeHtml(record.category)+" · €"+record.priceMin+"–"+record.priceMax+"</strong><small>маржа ≥"+record.margin+"% · MOQ ≤"+record.moq+"</small></td><td><span class='market'>NEW</span> "+escapeHtml(record.marketplace)+"</td><td><span class='status running'><i></i> Запускается</span></td><td><b>—</b></td><td><span class='score low'>—</span></td><td>только что</td><td><button class='row-open'><i data-lucide='chevron-right'></i></button></td>";
  document.getElementById("researchTableBody").prepend(tr);
  closeModal();lucide.createIcons();showToast("Исследование создано. В backend-версии здесь будет запущен job pipeline.");
});

function showToast(text){
  var toast=document.getElementById("toast");toast.querySelector("span").textContent=text;toast.classList.add("show");
  clearTimeout(showToast.timer);showToast.timer=setTimeout(function(){toast.classList.remove("show");},3300);
}
function bindDynamicActions(){
  document.querySelectorAll(".evidence-link").forEach(function(btn){btn.addEventListener("click",function(e){
    e.stopPropagation();
    var messages={
      market:"Evidence: 12 временных срезов и 4 812 исходных листингов.",
      competitors:"Evidence: 18 подтверждённых смысловых аналогов из 73 найденных.",
      reviews:"Evidence: выборка из 6 482 отзывов, 1 181 упоминание протечек.",
      economics:"Расчёт воспроизводим: €42,90 − все переменные затраты = €12,18 contribution profit."
    };
    showToast(messages[btn.dataset.evidence]||"Evidence связан с текущим выводом.");
  });});
  document.querySelectorAll("[data-approval]").forEach(function(btn){btn.addEventListener("click",function(){showToast("Human approval: действие подготовлено, но не выполняется без подтверждения пользователя.");});});
  document.querySelectorAll(".tab-pane .hermes-open").forEach(function(btn){btn.addEventListener("click",openHermes);});
}

renderOpportunities();
renderTabs();
lucide.createIcons();