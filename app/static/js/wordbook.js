import { els, showToast, setActiveView } from './dom.js';
import { fetchJSON } from './utils.js';

let currentBatch = null; // { start, end, items: [...] }
let explainOn = false;

function renderBatches(batches) {
  if (!els.wbBatchList) return;
  els.wbBatchList.innerHTML = '';
  batches.forEach((b) => {
    const tile = document.createElement('div');
    tile.className = 'tile';
    tile.textContent = b.label;
    tile.dataset.start = String(b.start);
    tile.dataset.end = String(b.end);
    tile.addEventListener('click', () => openBatch(b.start, b.end));
    els.wbBatchList.appendChild(tile);
  });
  els.wbBatchList.classList.add('tile-grid');
}

async function openBatch(start, end) {
  try {
    const data = await fetchJSON(`/api/wordbook/range?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`);
    currentBatch = { start: data.start, end: data.end, items: data.items || [] };
    // 每次进入批次时，默认关闭释义并复位开关
    explainOn = false;
    if (els.wbExplainSwitch) els.wbExplainSwitch.checked = false;
    renderList();
    // Switch to reader
    if (els.wbSelector) { els.wbSelector.hidden = true; els.wbSelector.style.display = 'none'; }
    if (els.wbReader) { els.wbReader.hidden = false; els.wbReader.style.display = ''; }
  } catch (e) {
    showToast('加载批次失败');
  }
}

function renderList() {
  if (!els.wbDetail) return;
  // 单列渲染：只使用 wbDetail 区域作为列表容器
  els.wbDetail.innerHTML = '';
  if (!currentBatch) return;
  const container = els.wbDetail;
  currentBatch.items.forEach((item, idx) => {
    const row = document.createElement('div');
    row.className = 'list-item wb-item';
    // 单列区域样式：左对齐、占满一行、自动换行
    row.style.textAlign = 'left';
    row.style.display = 'block';
    row.style.padding = '8px 10px';
    row.style.borderBottom = '1px solid #eee';
    row.style.whiteSpace = 'normal';
    row.style.wordBreak = 'break-word';

    const seq = (currentBatch.start || 1) + idx; // 全局序号
    const w = item.word || '';
    const p = item.phonetic || '';
    const m = item.meaning || '';
    if (explainOn) {
      row.textContent = `单词${seq}：${w}${p ? '  ' + p : ''}${m ? '  ' + m : ''}`;
    } else {
      row.textContent = `单词${seq}：${w}`;
    }
    container.appendChild(row);
  });
}

function toggleExplain() {
  explainOn = !explainOn;
  if (els.wbToggleExplain) {
    els.wbToggleExplain.textContent = explainOn ? '关闭释义' : '开启释义';
  }
  renderList();
}

function backToSelector() {
  currentBatch = null;
  explainOn = false;
  if (els.wbExplainSwitch) els.wbExplainSwitch.checked = false;
  if (els.wbReader) { els.wbReader.hidden = true; els.wbReader.style.display = 'none'; }
  if (els.wbSelector) { els.wbSelector.hidden = false; els.wbSelector.style.display = ''; }
}

function downloadCurrent() {
  if (!currentBatch || !currentBatch.items || !currentBatch.items.length) return;
  const start = currentBatch.start;
  const end = currentBatch.end;
  const lines = currentBatch.items.map((it) => it.word || '');
  const text = lines.join('\n');
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `V${start}-${end}.txt`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export async function initWordbook() {
  // buttons
  if (els.wbBackBtn) els.wbBackBtn.addEventListener('click', backToSelector);
  if (els.wbExplainSwitch) els.wbExplainSwitch.addEventListener('change', () => { explainOn = !!els.wbExplainSwitch.checked; renderList(); });

  // 默认显示选择器，隐藏阅读区（防止上下叠加）
  if (els.wbReader) { els.wbReader.hidden = true; els.wbReader.style.display = 'none'; }
  if (els.wbSelector) { els.wbSelector.hidden = false; els.wbSelector.style.display = ''; }

  // load batches
  try {
    const data = await fetchJSON('/api/wordbook/batches');
    renderBatches(data.batches || []);
  } catch (e) {
    showToast('读取批次失败');
  }
}


