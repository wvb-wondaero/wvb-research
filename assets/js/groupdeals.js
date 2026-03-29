document.addEventListener('DOMContentLoaded', function() {
  var list = document.getElementById('deal-list');
  if (!list) return;
  var rows = [];
  list.querySelectorAll('.deal-row').forEach(function(r) { rows.push(r); });
  if (!rows.length) return;

  var NOISE_TITLE_KEYWORDS = [
    '주가', '랠리', '시황', '마감', '이사회', '사외이사', 'CFO',
    '대표이사', '인사', '조직', '노조', '파업', '규탄', '비판',
    'People', 'Story', '영상', 'Board Change'
  ];
  var MEDIA_PREFIXES = [
    '더벨', '단독', '이데일리', 'thebell', 'note', 'Who Is',
    '기획', '진단', '동십자각'
  ];

  function isNoise(title) {
    for (var i = 0; i < NOISE_TITLE_KEYWORDS.length; i++) {
      if (title.includes(NOISE_TITLE_KEYWORDS[i])) return true;
    }
    for (var j = 0; j < MEDIA_PREFIXES.length; j++) {
      if (title.startsWith('[' + MEDIA_PREFIXES[j]) || title.startsWith(MEDIA_PREFIXES[j])) return true;
    }
    return false;
  }

  function normalizeCompany(name) {
    if (!name || name === 'null' || name === 'undefined') return null;
    var cleaned = name
      .replace(/^(주식회사|㈜|유한회사|합자회사)\s*/g, '')
      .replace(/\s*(주식회사|㈜|유한회사)$/g, '')
      .replace(/\s+/g, ' ')
      .trim();
    return cleaned || null;
  }

  var groups = {};
  var order = [];

  rows.forEach(function(row) {
    var title = row.dataset.title || '';
    if (isNoise(title)) return;
    var key = normalizeCompany(row.dataset.company);
    if (!key) return;
    if (!groups[key]) {
      groups[key] = [];
      order.push(key);
    }
    groups[key].push(row);
  });

  order.sort(function(a, b) {
    var dateA = groups[a][0].dataset.date || '';
    var dateB = groups[b][0].dataset.date || '';
    return dateB.localeCompare(dateA);
  });

  var targetList = document.getElementById('deal-list');
  targetList.innerHTML = '';
  var lastDate = '';

  order.forEach(function(company) {
    var items = groups[company];
    items.sort(function(a, b) {
      return (b.dataset.date || '').localeCompare(a.dataset.date || '');
    });

    var types = [...new Set(items.map(function(r) { return r.dataset.type; }))].join(' ');
    var latest = items[0];
    var date = latest.dataset.date || '';
    var ev = latest.dataset.ev && latest.dataset.ev !== 'null' ? latest.dataset.ev : '—';
    var tagsHTML = latest.querySelector('.deal-tags') ? latest.querySelector('.deal-tags').innerHTML : '';

    var stage = latest.dataset.dealStage || '';
    var stageLabels = { '소문': 'Rumor', '협상': 'Nego', '계약': 'Signed', '완료': 'Closed' };
    var stageLabel = stageLabels[stage] || stage;
    var stageBadge = stage
      ? '<span class="stage-badge stage--' + stage + '"><span class="stage-dot"></span>' + stageLabel + '</span>'
      : '';

    var investor = latest.dataset.acquirer || '';
    var investorText = investor ? '<span class="deal-acquirer">' + investor + '</span>' : '';

    var hasMultiple = items.length > 1;
    var showDate = date !== lastDate;
    lastDate = date;

    var group = document.createElement('div');
    group.className = 'deal-group';
    group.dataset.types = types;

    var onclickAttr = hasMultiple
      ? 'toggleGroup(this)'
      : "window.open('" + latest.dataset.url + "','_blank')";

    group.innerHTML =
      '<div class="deal-group-header" onclick="' + onclickAttr + '">' +
        '<div class="deal-date" data-date="' + date + '">' + (showDate ? date : '') + '</div>' +
        '<div class="deal-body">' +
          '<div class="deal-title">' +
            company + ' ' + stageBadge +
            (hasMultiple ? '<span class="article-count">' + items.length + '개 기사</span>' : '') +
          '</div>' +
          '<div class="deal-sub">' + investorText + (investorText && latest.dataset.summary ? ' · ' : '') + (latest.dataset.summary || '') + '</div>' +
          '<div class="deal-tags">' + tagsHTML + '</div>' +
        '</div>' +
        '<div class="deal-ev">' + ev + (hasMultiple ? ' <span class="arrow">▸</span>' : '') + '</div>' +
      '</div>' +
      (hasMultiple
        ? '<div class="deal-articles">' +
            items.map(function(r) {
              return '<a class="deal-article-item" href="' + r.dataset.url + '" target="_blank" rel="noopener">' +
                '<span class="deal-article-title">' + r.dataset.title + '</span>' +
                '<span class="deal-article-date">' + r.dataset.date + '</span>' +
              '</a>';
            }).join('') +
          '</div>'
        : '');

    targetList.appendChild(group);
  });
});

function toggleGroup(el) {
  var articles = el.closest('.deal-group').querySelector('.deal-articles');
  var arrow = el.querySelector('.arrow');
  if (!articles) return;
  if (articles.classList.contains('open')) {
    articles.classList.remove('open');
    if (arrow) arrow.textContent = '▸';
  } else {
    articles.classList.add('open');
    if (arrow) arrow.textContent = '▾';
  }
}
