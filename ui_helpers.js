// 外部データはテキスト、URL、列挙値を分けて描画する。
function safeExternalUrl(value) {
  try {
    const url = new URL(String(value));
    return url.protocol === 'https:' && !url.username && !url.password ? escapeHtml(url.href) : '';
  } catch { return ''; }
}

function safeImageUrl(value) {
  try {
    const url = new URL(String(value));
    return url.protocol === 'https:' && url.hostname === 'ddragon.leagueoflegends.com'
      && /^\/cdn\/\d+\.\d+\.\d+\/img\/(champion|passive|spell|item)\/[A-Za-z0-9_.-]+\.png$/.test(url.pathname)
      && !url.search && !url.hash ? escapeHtml(url.href) : 'icon.png';
  } catch { return 'icon.png'; }
}

function safeBadgeClass(value) {
  return ['badge-ad', 'badge-ap', 'badge-tank', 'badge-hybrid'].includes(value) ? value : 'badge-ad';
}

function getRoleData(champion, role) {
  return { ...(champion.common_role_data || {}), ...(champion.role_data?.[role] || {}) };
}

function guidanceSourcesHtml(data) {
  const entries = Object.entries(data.guidance_sources || {});
  const labels = {gameplay_notes: '立ち回り', combos: 'コンボ', skill_order: 'スキル順', skill_matrix: '取得表'};
  return entries.map(([field, source]) => {
    const url = safeExternalUrl(source.source_url);
    if (!url) return '';
    return `<div class="guidance-source"><a href="${url}" target="_blank" rel="noopener noreferrer">${escapeHtml(labels[field] || field)}の出典</a>・参照パッチ ${escapeHtml(source.source_patch || '未検証')}・確認日 ${escapeHtml((source.checked_at || '').slice(0,10))}</div>`;
  }).join('');
}

function renderItemPills(items, patch, numbered = false) {
  return (items || []).map((ref, index) => {
    const id = String(ref.item_id || ref.id || '');
    const item = ITEMS[id];
    if (!item || !/^\d{1,4}$/.test(id)) return '';
    const image = safeImageUrl(`https://ddragon.leagueoflegends.com/cdn/${patch}/img/item/${id}.png`);
    return `<button type="button" class="item-pill clickable-item" data-item-id="${escapeHtml(id)}" title="タップして詳細を表示">${numbered ? `<span class="item-step">${index+1}</span>` : ''}<img class="item-img" src="${image}" alt="${escapeHtml(item.name)}" onerror="this.src='icon.png';"><span>${escapeHtml(item.name)}</span></button>`;
  }).join('');
}

// モーダルの履歴は、表示内容を復元できる状態として保存する。
let modalStack = history.state?.loldb ? (history.state.stack || []) : [];
let restoringModalHistory = false;
let modalReturnFocus = null;
const modalIds = {champion_detail: 'detailModal', item_detail: 'itemDetailModal', changelog: 'changelogModal'};
history.replaceState({loldb: true, stack: modalStack}, '');

function syncModalAccessibility(focus = false) {
  const top = modalStack.at(-1);
  const topId = top ? modalIds[top.modal] : null;
  document.body.style.overflow = modalStack.length ? 'hidden' : '';
  Object.values(modalIds).forEach(id => {
    const dialog = document.getElementById(id);
    const active = id === topId;
    dialog.inert = !active;
    dialog.setAttribute('aria-hidden', String(!active));
    dialog.setAttribute('aria-modal', String(active));
    if (active && focus) (dialog.querySelector('button, [tabindex="0"]') || dialog).focus();
  });
  for (const element of document.body.children) {
    if (!Object.values(modalIds).includes(element.id) && element.tagName !== 'SCRIPT') element.inert = Boolean(top);
  }
  if (!top && modalReturnFocus?.isConnected) {
    modalReturnFocus.focus();
    modalReturnFocus = null;
  }
}

function recordModal(entry) {
  if (restoringModalHistory) return;
  if (!modalStack.length) modalReturnFocus = document.activeElement;
  const current = modalStack.at(-1);
  const sameChampion = current?.modal === 'champion_detail' && entry.modal === 'champion_detail' && current.champId === entry.champId;
  if (sameChampion) {
    modalStack = [...modalStack.slice(0,-1), entry];
    history.replaceState({loldb:true, stack:modalStack}, '');
  } else if (JSON.stringify(current) !== JSON.stringify(entry)) {
    modalStack = [...modalStack, entry];
    history.pushState({loldb:true, stack:modalStack}, '');
  }
  syncModalAccessibility(true);
}

function restoreModalStack(stack) {
  restoringModalHistory = true;
  modalStack = stack;
  Object.values(modalIds).forEach(id => document.getElementById(id).classList.remove('open'));
  for (const entry of stack) {
    if (entry.modal === 'champion_detail') openDetail(entry.champId, entry.role);
    if (entry.modal === 'item_detail') openItemDetail(entry.itemId);
    if (entry.modal === 'changelog') openChangelogModal();
  }
  restoringModalHistory = false;
  syncModalAccessibility(true);
}

function closeTopModal() {
  if (modalStack.length) history.back();
}

window.addEventListener('popstate', event => restoreModalStack(event.state?.loldb ? event.state.stack || [] : []));
window.addEventListener('keydown', event => {
  if (!modalStack.length) return;
  if (event.key === 'Escape') { event.preventDefault(); closeTopModal(); return; }
  if (event.key !== 'Tab') return;
  const dialog = document.getElementById(modalIds[modalStack.at(-1).modal]);
  const controls = [...dialog.querySelectorAll('button, a[href], input, select, [tabindex="0"]')].filter(el => !el.disabled && el.getClientRects().length);
  const first = controls[0], last = controls.at(-1);
  if (!first) { event.preventDefault(); dialog.focus(); return; }
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
});
queueMicrotask(() => restoreModalStack(modalStack));
