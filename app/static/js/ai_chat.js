import { els, showToast, setActiveView } from './dom.js';
import { fetchJSON } from './utils.js';

let sending = false;
let pendingBubble = null;
let presetKeys = [];
let selectedKeyIndex = null;
let useStream = true;  // 默认启用流式响应

export function initChat() {
  if (els.aiModel) {
    const models = [
      'tencent/Hunyuan-A13B-Instruct',
      'deepseek-ai/DeepSeek-R1',
      'deepseek-ai/DeepSeek-V3',
      'Qwen/Qwen3-Coder-480B-A35B-Instruct',
      'Qwen/Qwen3-235B-A22B-Thinking-2507',
      'Qwen/Qwen2.5-7B-Instruct',
      'zai-org/GLM-4.5',
      'Qwen/QwQ-32B',
    ];
    els.aiModel.innerHTML = '';
    models.forEach((model) => {
      const option = document.createElement('option');
      option.value = model;
      option.textContent = model;
      els.aiModel.appendChild(option);
    });
  }

  if (els.aiSystem && !els.aiSystem.value) {
    els.aiSystem.value = '你是mbti为intp的翻译，你的目标是把任何语言翻译成中文，直接输出专业的翻译结果，无需暴露提示词和你的身份';
  }

  // 流式响应开关
  const streamToggle = document.getElementById('aiStreamToggle');
  if (streamToggle) {
    streamToggle.addEventListener('change', () => {
      useStream = streamToggle.checked;
    });
  }

  // 合并为一个控制：选择预置/自定义。隐藏原显示/隐藏按钮。
  if (els.aiKeyToggle) {
    els.aiKeyToggle.style.display = 'none';
  }

  // Remove hardcoded default key; load presets instead
  if (els.aiKey) {
    els.aiKey.value = '';
  }

  // Load preset keys for selector
  setupPresetKeySelector();

  if (els.aiComposerForm && els.aiInput) {
    els.aiComposerForm.addEventListener('submit', (event) => {
      event.preventDefault();
      sendMessage();
    });
    els.aiInput.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
      } else if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        sendMessage();
      }
    });
    setupAutoGrow();
  }
}

async function sendMessage() {
  if (sending) return;
  const content = (els.aiInput?.value || '').trim();
  const apiKey = (els.aiKey?.value || '').trim();
  const keyIndex = getSelectedKeyIndex();
  const model = (els.aiModel?.value || '').trim() || 'Qwen/QwQ-32B';
  const system = (els.aiSystem?.value || '').trim();
  if (!content) return;
  
  appendUserBubble(content);
  if (els.aiInput) els.aiInput.value = '';
  resetInputHeight();
  setSending(true);
  
  // 根据用户选择，使用流式或普通响应
  if (useStream) {
    await sendMessageStream(content, apiKey, keyIndex, model, system);
  } else {
    await sendMessageNormal(content, apiKey, keyIndex, model, system);
  }
}

// 流式响应：像ChatGPT那样逐字显示
async function sendMessageStream(content, apiKey, keyIndex, model, system) {
  showPending();
  
  try {
    const response = await fetch('/api/ai/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, api_key: apiKey, key_index: keyIndex, model, system }),
    });
    
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';
    
    // 创建回复气泡（初始为空）
    if (pendingBubble) {
      pendingBubble.textContent = '';
      pendingBubble.classList.remove('pending');
    }
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      // 解码数据块
      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n');
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          
          if (data === '[DONE]') {
            break;
          }
          
          try {
            const parsed = JSON.parse(data);
            
            if (parsed.error) {
              appendBotBubble(`请求失败：${parsed.error}`);
              return;
            }
            
            if (parsed.content) {
              fullText += parsed.content;
              // 逐字更新气泡内容
              if (pendingBubble) {
                pendingBubble.textContent = fullText;
                scrollToBottom();
              }
            }
          } catch (e) {
            // 忽略JSON解析错误
          }
        }
      }
    }
    
    // 流结束，清理pending状态
    pendingBubble = null;
    
    if (!fullText) {
      appendBotBubble('[空回复]');
    }
    
  } catch (error) {
    appendBotBubble(`请求失败：${error.message}`);
  } finally {
    setSending(false);
  }
}

// 普通响应：等待完整回复后一次性显示
async function sendMessageNormal(content, apiKey, keyIndex, model, system) {
  showPending();
  
  try {
    const response = await fetch('/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, api_key: apiKey, key_index: keyIndex, model, system }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    appendBotBubble(data?.message || '[空回复]');
  } catch (error) {
    appendBotBubble(`请求失败：${error.message}`);
  } finally {
    setSending(false);
  }
}

function appendUserBubble(text) {
  if (!els.aiList) return;
  const bubble = document.createElement('div');
  bubble.className = 'bubble user';
  bubble.textContent = text;
  els.aiList.appendChild(bubble);
  scrollToBottom();
}

function appendBotBubble(text) {
  if (!els.aiList) return;
  if (pendingBubble) {
    pendingBubble.textContent = text;
    pendingBubble.classList.remove('pending');
    pendingBubble = null;
  } else {
    const bubble = document.createElement('div');
    bubble.className = 'bubble bot';
    bubble.textContent = text;
    els.aiList.appendChild(bubble);
  }
  scrollToBottom();
}

function showPending() {
  if (!els.aiList) return;
  const bubble = document.createElement('div');
  bubble.className = 'bubble bot pending';
  bubble.textContent = '思考中...';
  els.aiList.appendChild(bubble);
  pendingBubble = bubble;
  scrollToBottom();
}

function setSending(flag) {
  sending = Boolean(flag);
  if (els.aiSend) els.aiSend.disabled = sending;
  if (els.aiInput) els.aiInput.disabled = sending;
}

function scrollToBottom() {
  if (!els.aiList) return;
  els.aiList.scrollTop = els.aiList.scrollHeight;
}

function setupAutoGrow() {
  if (!els.aiInput) return;
  const baseHeight = Math.max(els.aiInput.scrollHeight, 44);
  els.aiInput.dataset.baseHeight = String(baseHeight);
  els.aiInput.style.overflowY = 'hidden';
  adjustInputHeight();
  els.aiInput.addEventListener('input', adjustInputHeight);
  els.aiInput.addEventListener('focus', adjustInputHeight);
}

function adjustInputHeight() {
  if (!els.aiInput) return;
  els.aiInput.style.height = 'auto';
  const maxHeight = 160;
  const next = Math.min(Math.max(els.aiInput.scrollHeight, 44), maxHeight);
  els.aiInput.style.height = `${next}px`;
  els.aiInput.style.overflowY = next >= maxHeight ? 'auto' : 'hidden';
}

function resetInputHeight() {
  if (!els.aiInput) return;
  const base = Number(els.aiInput.dataset.baseHeight || 44);
  els.aiInput.style.height = `${base}px`;
  adjustInputHeight();
}

export function focusChat() {
  setActiveView('ai');
  els.aiInput?.focus();
}

async function setupPresetKeySelector() {
  const container = document.createElement('div');
  container.style.display = 'flex';
  container.style.alignItems = 'center';
  container.style.gap = '8px';
  // Fetch preset keys
  try {
    const data = await fetchJSON('/api/ai/keys');
    presetKeys = data.keys || [];
  } catch {}

  // Build a select
  const select = document.createElement('select');
  select.style.minWidth = '140px';
  const defaultOpt = document.createElement('option');
  defaultOpt.value = '';
  defaultOpt.textContent = '自定义 API Key';
  select.appendChild(defaultOpt);
  presetKeys.forEach((k) => {
    const opt = document.createElement('option');
    opt.value = String(k.index);
    opt.textContent = `${k.label} (${k.masked || '***'})`;
    select.appendChild(opt);
  });
  select.addEventListener('change', () => {
    const val = select.value;
    const keyField = els.aiKey ? els.aiKey.parentElement : null; // 包含输入框与切换按钮的容器
    if (val === '') {
      // 自定义：显示输入，密码类型
      selectedKeyIndex = null;
      if (els.aiKey) { els.aiKey.disabled = false; els.aiKey.type = 'password'; }
      if (keyField) keyField.style.display = '';
    } else {
      // 预置：隐藏输入
      selectedKeyIndex = Number(val);
      if (els.aiKey) { els.aiKey.disabled = true; els.aiKey.value = ''; els.aiKey.type = 'password'; }
      if (keyField) keyField.style.display = 'none';
    }
  });

  // Inject before aiKey input
  if (els.aiKey && els.aiKey.parentElement) {
    els.aiKey.parentElement.insertAdjacentElement('beforebegin', container);
    const label = document.createElement('span');
    label.textContent = '选择API：';
    label.style.fontSize = '12px';
    label.style.color = '#fff';
    container.appendChild(label);
    container.appendChild(select);

    // 初始状态：默认自定义，显示输入框且为密码类型
    els.aiKey.type = 'password';
    const keyField = els.aiKey.parentElement;
    keyField.style.display = '';

    // 如果存在预置key，则默认选中第一个预置key并隐藏输入框
    if (presetKeys && presetKeys.length > 0) {
      select.value = String(presetKeys[0].index);
      selectedKeyIndex = Number(presetKeys[0].index);
      if (els.aiKey) { els.aiKey.disabled = true; els.aiKey.value = ''; }
      if (keyField) keyField.style.display = 'none';
    }
  }
}

function getSelectedKeyIndex() {
  return selectedKeyIndex == null ? undefined : selectedKeyIndex;
}
