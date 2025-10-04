const views = {
  database: document.getElementById('view-database'),
  segments: document.getElementById('view-segments'),
  wordbook: document.getElementById('view-wordbook'),
  lookup: document.getElementById('view-lookup'),
  ai: document.getElementById('view-ai'),
  todayphrase: document.getElementById('view-todayphrase'),
};

const tabs = Array.from(document.querySelectorAll('.bottom-nav .tab'));

export const els = {
  txtList: document.getElementById('txtList'),
  excelFiles: document.getElementById('excelFiles'),
  lookupBody: document.getElementById('lookupBody'),
  aiList: document.getElementById('aiList'),
  aiSend: document.getElementById('aiSend'),
  aiInput: document.getElementById('aiInput'),
  aiKey: document.getElementById('aiKey'),
  aiModel: document.getElementById('aiModel'),
  aiSystem: document.getElementById('aiSystem'),
  aiKeyToggle: document.getElementById('aiKeyToggle'),
  aiComposerForm: document.getElementById('aiComposerForm'),
  content: document.getElementById('content'),
  copyAll: document.getElementById('copyAllBtn'),
  backToSelectorBtn: document.getElementById('backToSelectorBtn'),
  segmentsSelector: document.getElementById('segments-selector'),
  segmentsReader: document.getElementById('segments-reader'),
  wbBatchList: document.getElementById('wbBatchList'),
  wbBackBtn: document.getElementById('wbBackBtn'),
  wbExplainSwitch: document.getElementById('wbExplainSwitch'),
  wbDownloadBtn: document.getElementById('wbDownloadBtn'),
  wbSelector: document.getElementById('wordbook-selector'),
  wbReader: document.getElementById('wordbook-reader'),
  wbList: document.getElementById('wbList'),
  wbDetail: document.getElementById('wbDetail')
};

let toastTimer = null;

export function showToast(text, timeout = 1500) {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  container.textContent = String(text || '');
  container.classList.add('show');
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => container.classList.remove('show'), timeout);
}

export function setActiveView(name) {
  Object.entries(views).forEach(([key, node]) => {
    if (!node) return;
    const isActive = key === name;
    node.classList.toggle('active', isActive);
  });
  tabs.forEach((tab) => {
    const target = tab.getAttribute('data-view');
    tab.setAttribute('aria-selected', String(target === name));
  });
  window.__currentView = name;
}

export function initNavigation(defaultView = null) {
  tabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      const name = tab.getAttribute('data-view');
      if (name) setActiveView(name);
    });
  });
  // 只有当提供了默认视图时才设置活动视图
  if (defaultView) {
    setActiveView(defaultView);
  }
}

export function showSegmentsSelector() {
  if (els.segmentsSelector) {
    els.segmentsSelector.hidden = false;
    els.segmentsSelector.style.display = '';
  }
  if (els.segmentsReader) {
    els.segmentsReader.hidden = true;
    els.segmentsReader.style.display = 'none';
  }
}

export function showSegmentsReader() {
  if (els.segmentsSelector) {
    els.segmentsSelector.hidden = true;
    els.segmentsSelector.style.display = 'none';
  }
  if (els.segmentsReader) {
    els.segmentsReader.hidden = false;
    els.segmentsReader.style.display = '';
  }
}
