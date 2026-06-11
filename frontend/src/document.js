import { apiFetch, checkAuth } from './api.js';

let currentPdf = '';
let docMeta = null;

// Verify session
checkAuth();

document.addEventListener('DOMContentLoaded', async () => {
  currentPdf = new URLSearchParams(window.location.search).get('pdf') || '';
  if (!currentPdf) {
    window.location.href = '/dashboard';
    return;
  }
  await loadDetails();
});

async function loadDetails() {
  const content = document.getElementById('content');
  try {
    const res = await apiFetch(`/api/document/meta/${encodeURIComponent(currentPdf)}`);
    docMeta = res.data;
    document.title = `DocMind | ${docMeta.filename}`;
    content.innerHTML = renderDetails(docMeta);
  } catch (err) {
    content.innerHTML = `
      <div class="border-4 border-ink bg-dangerSoft shadow-brutal p-6">
        <h1 class="text-3xl font-black text-danger">Could not load this document</h1>
        <p class="mt-2 font-bold text-danger">${escapeHtml(err.message)}</p>
        <a class="inline-block mt-5 border-4 border-ink bg-yellow px-5 py-3 font-black" href="/dashboard">Return to Library</a>
      </div>`;
  }
}

function renderDetails(doc) {
  const safe = encodeURIComponent(doc.filename);
  return `
    <section class="bg-yellow border-4 border-ink shadow-brutal p-5 sm:p-8">
      <p class="text-xs font-black uppercase tracking-[.18em] text-muted">Document details</p>
      <div class="mt-3 flex flex-col lg:flex-row lg:items-end lg:justify-between gap-5">
        <div class="min-w-0">
          <h1 class="text-4xl sm:text-5xl font-black tracking-tight break-words">${escapeHtml(doc.filename)}</h1>
          <p class="mt-2 text-lg font-semibold text-muted">${doc.indexed ? 'Indexed and ready for cited chat.' : 'Still needs indexing before chat is reliable.'}</p>
        </div>
        <a href="/chat?pdf=${safe}" class="press shadow-brutal bg-purple text-white border-4 border-ink px-5 py-4 font-black text-center">Open Chat</a>
      </div>
    </section>

    <section class="grid md:grid-cols-2 xl:grid-cols-4 gap-4">
      ${statCard('Upload date', doc.date || 'Unknown', 'calendar_today')}
      ${statCard('Total pages', doc.pages || 0, 'description')}
      ${statCard('Chats', doc.chats || 0, 'forum')}
      ${statCard('Status', doc.indexed ? 'Indexed' : 'Pending', 'database')}
    </section>

    <section class="grid lg:grid-cols-[1fr_340px] gap-6">
      <article class="bg-card border-4 border-ink shadow-brutal p-6">
        <div class="flex items-center gap-3 border-b-4 border-ink pb-3">
          <span class="material-symbols-outlined text-3xl">summarize</span>
          <h2 class="text-3xl font-black">Document Summary</h2>
        </div>
        <p class="mt-5 font-semibold text-muted leading-relaxed">${escapeHtml(doc.summary)}</p>
        <dl class="mt-6 grid sm:grid-cols-2 gap-3">
          <div class="border-4 border-ink bg-soft p-4"><dt class="text-xs font-black uppercase text-muted">File size</dt><dd class="text-xl font-black">${doc.size || 'Unknown'}</dd></div>
          <div class="border-4 border-ink bg-soft p-4"><dt class="text-xs font-black uppercase text-muted">Last activity</dt><dd class="text-xl font-black">${doc.last_activity || doc.date || 'Unknown'}</dd></div>
        </dl>
      </article>

      <aside class="bg-card border-4 border-ink shadow-brutal p-6 h-fit">
        <p class="text-xs font-black uppercase tracking-[.18em] text-muted">Quick actions</p>
        <h2 class="text-3xl font-black mt-1">Run with DocMind</h2>
        <div class="mt-5 grid gap-3">
          ${actionButton('Generate Notes')}
          ${actionButton('Generate Quiz')}
          ${actionButton('Summarize Document')}
          ${actionButton('Create Study Guide')}
          <button onclick="window.deleteDocument()" class="border-4 border-ink bg-dangerSoft px-4 py-3 font-black text-left hover:bg-white transition flex items-center justify-between">Delete Document <span class="material-symbols-outlined">delete</span></button>
        </div>
      </aside>
    </section>
  `;
}

function statCard(label, value, icon) {
  return `
    <article class="bg-card border-4 border-ink shadow-brutal p-5">
      <span class="material-symbols-outlined text-3xl">${icon}</span>
      <p class="text-xs font-black uppercase tracking-[.15em] text-muted mt-3">${label}</p>
      <p class="text-2xl font-black mt-1">${escapeHtml(value)}</p>
    </article>`;
}

function actionButton(action) {
  return `<button onclick="window.runAction('${action}')" class="border-4 border-ink bg-yellow px-4 py-3 font-black text-left hover:bg-yellowSoft transition flex items-center justify-between">${action} <span class="material-symbols-outlined">arrow_forward</span></button>`;
}

function runAction(action) {
  window.location.href = `/chat?pdf=${encodeURIComponent(currentPdf)}&action=${encodeURIComponent(action)}`;
}

async function deleteDocument() {
  if (!confirm(`Delete "${currentPdf}" from DocMind?`)) return;
  try {
    await apiFetch(`/api/document/${encodeURIComponent(currentPdf)}`, { method: 'DELETE' });
    window.location.href = '/dashboard';
  } catch (err) {
    showToast(err.message);
  }
}

function showToast(message) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.classList.remove('hidden');
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.add('hidden'), 3000);
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#039;' }[char]));
}

// Expose handlers to global window for inline actions
window.runAction = runAction;
window.deleteDocument = deleteDocument;
