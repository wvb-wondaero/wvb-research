function show(id, el) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('visible'));
  document.querySelectorAll('.navlink').forEach(n => n.classList.remove('active'));
  document.getElementById(id).classList.add('visible');
  el.classList.add('active');
}

function filterDeal(type, el) {
  document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
  el.classList.add('active');

  const groups = Array.from(document.querySelectorAll('#deal-list .deal-group'));

  groups.forEach(group => {
    if (type === 'all') {
      group.classList.remove('hidden');
    } else {
      const tags = group.dataset.types || '';
      group.classList.toggle('hidden', !tags.includes(type));
    }
  });

  let lastDate = '';
  groups.forEach(group => {
    if (group.classList.contains('hidden')) return;
    const dateEl = group.querySelector('.deal-date');
    if (!dateEl) return;
    const date = dateEl.dataset.date || dateEl.textContent.trim();
    dateEl.textContent = date && date !== lastDate ? (lastDate = date, date) : (lastDate = lastDate, '');
  });
}

function toggleGroup(el) {
  const articles = el.closest('.deal-group').querySelector('.deal-articles');
  const arrow = el.querySelector('.arrow');
  if (!articles) return;
  if (articles.classList.contains('open')) {
    articles.classList.remove('open');
    if (arrow) arrow.textContent = '▸';
  } else {
    articles.classList.add('open');
    if (arrow) arrow.textContent = '▾';
  }
}
