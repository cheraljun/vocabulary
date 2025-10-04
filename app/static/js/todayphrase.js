import { showToast } from './dom.js';
import { fetchJSON } from './utils.js';

export async function initTodayPhrase() {
  const img = document.getElementById('todayphraseImg');
  if (!img) return;
  img.removeAttribute('src');
  img.alt = '今日一签';
  try {
    const data = await fetchJSON('/api/todayphrase');
    const url = data.url;
    if (!url) throw new Error('not found');
    img.src = url;
  } catch (e) {
    showToast('未找到今日一签图片');
  }
}


