import { API_URL, apiFetch, checkAuth } from './api.js';

const prompts = {
  'Summarize Document': 'Summarize this document clearly. Include the main argument, important sections, and practical takeaways. Cite the most relevant pages.',
  'Generate Notes': 'Generate structured study notes from this document with headings, bullet points, definitions, and cited page references.',
  'Generate Quiz': 'Create a quiz from this document with 8 questions, answer choices where useful, correct answers, and page citations.',
  'Key Concepts': 'Identify the key concepts in this document. Explain each concept briefly and cite the pages where it appears.',
  'Explain Like Beginner': 'Explain the document like I am a beginner. Use simple language, examples, and cite the source pages.',
  'Create Study Guide': 'Create a complete study guide from this document with overview, key ideas, terms, likely exam questions, and cited pages.',
  'Explain Simply': 'Explain the selected document simply and clearly. Focus on the essential ideas and cite source pages.',
  'Extract Key Metrics': 'Extract key metrics, facts, dates, numbers, and named entities from the document. Organize them in a table-like list and cite source pages.'
};

let currentPdf = '';
let currentPage = 1;
let totalPages = 1;
let zoomScale = 1;
let mobilePdfVisible = false;

// Verify session
checkAuth();

document.addEventListener('DOMContentLoaded', init);

async function init() {
  const params = new URLSearchParams(window.location.search);
  currentPdf = params.get('pdf') || '';
  if (!currentPdf) {
    window.location.href = '/dashboard';
    return;
  }
  document.title = `DocMind | ${currentPdf}`;
  document.getElementById('current-doc-title').textContent = currentPdf;
  document.getElementById('pdf-title').textContent = currentPdf;
  document.getElementById('details-link').href = `/document?pdf=${encodeURIComponent(currentPdf)}`;
  
  bindUI();
  renderSuggestions();
  loadPdf();
  await verifyDocument();
  await loadRecent();
  appendSystemIntro();
  
  const action = params.get('action');
  if (action && prompts[action]) {
    setTimeout(() => sendSuggestion(action), 450);
  }
}

function bindUI() {
  document.querySelectorAll('.control-btn').forEach(btn => btn.className = 'border-4 border-ink bg-yellow h-10 w-10 grid place-items-center shadow-sm-brutal hover:bg-yellowSoft transition');
  document.getElementById('menu-btn').addEventListener('click', () => document.getElementById('sidebar').classList.toggle('-translate-x-full'));
  document.getElementById('new-chat-btn').addEventListener('click', clearChat);
  document.getElementById('settings-btn').addEventListener('click', openModal);
  document.getElementById('modal-close').addEventListener('click', closeModal);
  document.getElementById('logout-btn').addEventListener('click', logout);
  document.getElementById('send-btn').addEventListener('click', () => sendMessage());
  document.getElementById('prev-page').addEventListener('click', () => goToPage(currentPage - 1));
  document.getElementById('next-page').addEventListener('click', () => goToPage(currentPage + 1));
  document.getElementById('page-input').addEventListener('change', event => goToPage(Number(event.target.value)));
  document.getElementById('zoom-in').addEventListener('click', () => setZoom(zoomScale + .12));
  document.getElementById('zoom-out').addEventListener('click', () => setZoom(zoomScale - .12));
  document.getElementById('fit-width').addEventListener('click', () => setZoom(1));
  document.getElementById('fit-page').addEventListener('click', () => setZoom(.82));
  document.getElementById('mobile-pdf-tab').addEventListener('click', toggleMobilePdf);
  
  const input = document.getElementById('chat-input');
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight, 160)}px`;
  });
  setupSpeechRecognition();
}

function renderSuggestions() {
  const order = ['Summarize Document', 'Generate Notes', 'Generate Quiz', 'Key Concepts', 'Explain Like Beginner', 'Create Study Guide', 'Explain Simply', 'Extract Key Metrics'];
  document.getElementById('suggestions').innerHTML = order.map(label => `
    <button onclick="window.sendSuggestion('${label}')" class="shrink-0 border-4 border-ink bg-card px-3 py-2 text-sm font-black hover:bg-yellow transition">${label}</button>
  `).join('');
}

async function verifyDocument() {
  try {
    const res = await apiFetch(`/api/document/status/${encodeURIComponent(currentPdf)}`);
    if (res.data.status === 'indexed') {
      totalPages = Math.max(Number(res.data.pages || 1), 1);
      updatePageStatus();
    } else if (res.data.status === 'error') {
      showToast(`Indexing warning: ${res.data.detail}`);
    }
  } catch (err) {
    showToast('Could not verify indexing status.');
  }
}

async function loadRecent() {
  try {
    const res = await apiFetch('/api/documents');
    const docs = res.data.documents || [];
    document.getElementById('recent-list').innerHTML = docs.slice(0, 8).map(doc => `
      <li><a href="/chat?pdf=${encodeURIComponent(doc.filename)}" class="block border-4 ${doc.filename === currentPdf ? 'border-ink bg-yellow' : 'border-transparent hover:border-ink hover:bg-soft'} p-2 font-bold truncate">${escapeHtml(doc.filename)}</a></li>
    `).join('') || '<li class="font-bold text-muted">No documents yet.</li>';
  } catch {
    document.getElementById('recent-list').innerHTML = '<li class="font-bold text-danger">Could not load recent documents.</li>';
  }
}

function appendSystemIntro() {
  appendAiMessage('I have this PDF ready. Ask a question or pick a quick action below. Every answer will include clickable source pages when DocMind finds supporting chunks.', []);
}

function loadPdf() {
  document.getElementById('pdf-frame').src = `${API_URL}/api/document/${encodeURIComponent(currentPdf)}#page=${currentPage}`;
  updatePageStatus();
}

function goToPage(page, highlight = false) {
  const clean = Math.max(1, Math.min(Number(page) || 1, totalPages || Number(page) || 1));
  currentPage = clean;
  document.getElementById('pdf-frame').src = `${API_URL}/api/document/${encodeURIComponent(currentPdf)}#page=${clean}&zoom=page-width`;
  updatePageStatus();
  if (highlight) highlightPage(clean);
  if (window.innerWidth < 1024 && !mobilePdfVisible) toggleMobilePdf();
}

function updatePageStatus() {
  document.getElementById('page-status').textContent = `Page ${currentPage}${totalPages ? ` / ${totalPages}` : ''}`;
  document.getElementById('page-input').value = currentPage;
  document.getElementById('page-input').max = totalPages || '';
}

function highlightPage(page) {
  document.querySelectorAll('[data-source-page]').forEach(el => el.classList.toggle('bg-yellow', Number(el.dataset.sourcePage) === Number(page)));
  const shell = document.getElementById('pdf-shell');
  const banner = document.getElementById('source-banner');
  banner.textContent = `Highlighted Page ${page}`;
  banner.classList.remove('hidden');
  shell.classList.add('pdf-highlight');
  clearTimeout(highlightPage.timer);
  highlightPage.timer = setTimeout(() => {
    shell.classList.remove('pdf-highlight');
    banner.classList.add('hidden');
  }, 2200);
}

function setZoom(value) {
  zoomScale = Math.max(.55, Math.min(1.9, value));
  const frame = document.getElementById('pdf-frame');
  frame.style.transform = `scale(${zoomScale})`;
  frame.style.width = `${100 / zoomScale}%`;
  frame.style.height = `${100 / zoomScale}%`;
}

function toggleMobilePdf() {
  const pdfPane = document.getElementById('pdf-pane');
  const chatPane = document.getElementById('chat-pane');
  mobilePdfVisible = !mobilePdfVisible;
  pdfPane.classList.toggle('hidden', !mobilePdfVisible);
  pdfPane.classList.toggle('flex', mobilePdfVisible);
  pdfPane.classList.toggle('fixed', mobilePdfVisible);
  pdfPane.classList.toggle('inset-0', mobilePdfVisible);
  pdfPane.classList.toggle('z-[60]', mobilePdfVisible);
  chatPane.classList.toggle('hidden', mobilePdfVisible);
  document.getElementById('mobile-pdf-tab').textContent = mobilePdfVisible ? 'Chat' : 'PDF';
}

function clearChat() {
  document.getElementById('chat-history').innerHTML = '';
  appendSystemIntro();
  showToast('Started a fresh chat view for this document.');
}

function sendSuggestion(label) {
  sendMessage(prompts[label] || label, label);
}

async function sendMessage(overrideText = '', label = '') {
  const input = document.getElementById('chat-input');
  const text = (overrideText || input.value).trim();
  if (!text) return;
  input.value = '';
  input.style.height = 'auto';
  appendUserMessage(label || text);
  setLoading(true);
  try {
    const res = await apiFetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ filename: currentPdf, message: text })
    });
    appendAiMessage(res.data.answer, res.data.sources || []);
  } catch (err) {
    appendAiMessage(`Sorry, I hit an error: ${err.message}`, []);
  } finally {
    setLoading(false);
  }
}

function appendUserMessage(text) {
  const row = document.createElement('article');
  row.className = 'message-in justify-self-end max-w-[92%] sm:max-w-[78%] flex items-start gap-3 flex-row-reverse';
  row.innerHTML = `
    <div class="h-10 w-10 rounded-full border-4 border-ink bg-yellow grid place-items-center shadow-sm-brutal shrink-0"><span class="material-symbols-outlined">person</span></div>
    <div>
      <div class="text-right text-xs font-black uppercase tracking-[.14em] text-muted">You | ${timeNow()}</div>
      <div class="mt-1 bg-yellow border-4 border-ink shadow-brutal p-4 font-semibold whitespace-pre-wrap">${escapeHtml(text)}</div>
    </div>`;
  pushMessage(row);
}

function appendAiMessage(text, sources) {
  const row = document.createElement('article');
  row.className = 'message-in justify-self-start max-w-[96%] sm:max-w-[84%] flex items-start gap-3';
  const sourceHtml = sources && sources.length ? `
    <div class="mt-4 pt-3 border-t-4 border-ink">
      <p class="font-black mb-2">Sources:</p>
      <div class="flex flex-wrap gap-2">
        ${sources.map(src => `<button data-source-page="${Number(src)}" onclick="window.goToPage(${Number(src)}, true)" class="border-4 border-ink bg-card px-3 py-2 text-sm font-black hover:bg-yellow transition">Page ${escapeHtml(src)}</button>`).join('')}
      </div>
    </div>` : '';
  row.innerHTML = `
    <div class="h-10 w-10 rounded-full border-4 border-ink bg-purple text-white grid place-items-center shadow-sm-brutal shrink-0"><span class="material-symbols-outlined">smart_toy</span></div>
    <div>
      <div class="text-xs font-black uppercase tracking-[.14em] text-muted">DocMind | ${timeNow()}</div>
      <div class="mt-1 bg-card border-4 border-ink shadow-brutal p-4 font-semibold leading-relaxed">
        <div class="whitespace-pre-wrap">${formatMessage(text)}</div>
        ${sourceHtml}
        <div class="mt-3 flex gap-2">
          <button onclick="window.copyMessage(this)" class="border-4 border-ink bg-soft px-2 py-1 text-xs font-black hover:bg-yellow">Copy</button>
          <button onclick="window.speakMessage(this)" class="border-4 border-ink bg-soft px-2 py-1 text-xs font-black hover:bg-yellow">Read</button>
        </div>
      </div>
    </div>`;
  pushMessage(row);
}

function pushMessage(row) {
  const history = document.getElementById('chat-history');
  history.appendChild(row);
  history.scrollTop = history.scrollHeight;
}

function setLoading(isLoading) {
  document.getElementById('ai-loading').classList.toggle('hidden', !isLoading);
  document.getElementById('send-btn').disabled = isLoading;
}

function copyMessage(button) {
  const text = button.closest('.border-4').querySelector('.whitespace-pre-wrap').innerText;
  navigator.clipboard.writeText(text).then(() => showToast('Copied answer.'));
}

function speakMessage(button) {
  const text = button.closest('.border-4').querySelector('.whitespace-pre-wrap').innerText;
  if (!window.speechSynthesis) {
    showToast('Speech synthesis is not supported in this browser.');
    return;
  }
  if (speechSynthesis.speaking) {
    speechSynthesis.cancel();
    return;
  }
  speechSynthesis.speak(new SpeechSynthesisUtterance(text));
}

function setupSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const mic = document.getElementById('mic-btn');
  if (!SpeechRecognition) {
    mic.addEventListener('click', () => showToast('Voice input is not supported in this browser.'));
    return;
  }
  const recognition = new SpeechRecognition();
  recognition.lang = 'en-US';
  recognition.onstart = () => mic.classList.add('bg-yellow', 'text-ink');
  recognition.onend = () => mic.classList.remove('bg-yellow', 'text-ink');
  recognition.onresult = event => {
    const input = document.getElementById('chat-input');
    input.value = `${input.value} ${event.results[0][0].transcript}`.trim();
    input.dispatchEvent(new Event('input'));
  };
  recognition.onerror = () => showToast('Voice capture failed.');
  mic.addEventListener('click', () => recognition.start());
}

function openModal() {
  document.getElementById('modal').classList.remove('hidden');
  document.getElementById('modal').classList.add('flex');
}

function closeModal() {
  document.getElementById('modal').classList.add('hidden');
  document.getElementById('modal').classList.remove('flex');
}

async function logout() {
  try {
    await apiFetch('/api/logout', { method: 'POST' });
  } catch (err) {
    console.error('Logout API call failed:', err);
  } finally {
    localStorage.removeItem('session_id');
    window.location.href = '/login';
  }
}

function showToast(message) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.classList.remove('hidden');
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.add('hidden'), 3000);
}

function timeNow() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatMessage(text) {
  return escapeHtml(text)
    .replace(/\*\*(.*?)\*\*/g, '<strong class="bg-yellow px-1 border-2 border-ink">$1</strong>')
    .replace(/`([^`]+)`/g, '<code class="bg-soft border-2 border-ink px-1">$1</code>');
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#039;' }[char]));
}

// Expose modules to global window scope for inline HTML actions
window.goToPage = goToPage;
window.sendSuggestion = sendSuggestion;
window.copyMessage = copyMessage;
window.speakMessage = speakMessage;
