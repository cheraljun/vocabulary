import { els, initNavigation, showToast, setActiveView, showSegmentsReader, showSegmentsSelector } from './dom.js';
import { loadTxtList, sendFullTextToAI } from './text.js';
import { refreshExcelFiles, refreshExcelStatus } from './dataset.js';
import { initChat } from './ai_chat.js';
import { initWordbook } from './wordbook.js';
import { initTodayPhrase } from './todayphrase.js';
import { fetchJSON } from './utils.js';

function initCopyButton() {
  if (!els.copyAll) return;
  els.copyAll.addEventListener('click', async () => {
    const text = String(window.__currentTxtFull || '');
    const name = String(window.__currentTxtName || '全文');
    try {
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${name}.txt`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      showToast('已开始下载');
    } catch {
      showToast('下载失败');
    }
  });
}

function initGuide() {
  const guide = document.getElementById('guide');
  const closeBtn = document.getElementById('guideClose');
  if (!guide || !closeBtn) return;
  closeBtn.addEventListener('click', () => {
    guide.setAttribute('hidden', 'hidden');
    // 关闭引导页后，设置活动视图为单词库，并确保显示单词库选择器
    setActiveView('wordbook');
    // 确保单词库选择器可见
    if (els.wbSelector) {
      els.wbSelector.hidden = false;
      els.wbSelector.style.display = '';
    }
    if (els.wbReader) {
      els.wbReader.hidden = true;
      els.wbReader.style.display = 'none';
    }
  });
}

function initBackButton() {
  if (!els.backToSelectorBtn) return;
  els.backToSelectorBtn.addEventListener('click', () => {
    showSegmentsSelector();
  });
}

function initSendToAIButton() {
  const sendBtn = document.getElementById('sendToAIBtn');
  if (!sendBtn) return;
  sendBtn.addEventListener('click', () => {
    sendFullTextToAI();
  });
}

async function init() {
  // 不在初始化时设置默认视图，等待引导页关闭后再设置
  initNavigation();
  initCopyButton();
  initChat();
  initGuide();
  initBackButton();
  initSendToAIButton();

  // 不在初始化时显示情境句选择器，等待引导页关闭后再显示

  await Promise.allSettled([
    loadTxtList(),
    refreshExcelFiles().then(refreshExcelStatus),
    initWordbook(),
    initTodayPhrase(),
  ]);
}

init().catch((error) => {
  console.error(error);
  showToast('初始化失败');
});
