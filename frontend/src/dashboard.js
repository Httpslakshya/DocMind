import { apiFetch, checkAuth } from './api.js';

const state = { docs: [], showAll: false };
const fileInput = document.getElementById('file-upload');
const grid = document.getElementById('documents-grid');
const toast = document.getElementById('toast');

// Verify session
const sessionId = checkAuth();
if (sessionId) {
  const userGreeting = document.getElementById('user-greeting');
  if (userGreeting) {
    const name = sessionId.split('@')[0];
    const capitalized = name.charAt(0).toUpperCase() + name.slice(1);
    userGreeting.textContent = `Good Morning, ${capitalized}`;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  bindUI();
  loadDocuments();
});

function bindUI() {
  document.getElementById('menu-btn').addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('-translate-x-full');
  });
  
  document.getElementById('new-chat-btn').addEventListener('click', () => fileInput.click());
  document.getElementById('view-all-btn').addEventListener('click', toggleViewAll);
  document.getElementById('view-all-nav').addEventListener('click', toggleViewAll);
  document.getElementById('refresh-btn').addEventListener('click', loadDocuments);
  document.getElementById('settings-btn').addEventListener('click', showSettings);
  
  document.getElementById('upgrade-btn').addEventListener('click', () => {
    showToast('DocMind Pro is a demo placeholder. Your current workspace already has all core features enabled.');
  });
  
  document.getElementById('logout-btn').addEventListener('click', logout);
  document.getElementById('modal-close').addEventListener('click', closeModal);
  fileInput.addEventListener('change', () => fileInput.files[0] && handleUpload(fileInput.files[0]));

  const dropZone = document.getElementById('drop-zone');
  ['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.add('bg-yellowSoft');
    });
  });
  
  ['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.remove('bg-yellowSoft');
    });
  });
  
  dropZone.addEventListener('drop', (event) => {
    const file = event.dataTransfer.files[0];
    if (file) handleUpload(file);
  });
  
  dropZone.addEventListener('click', () => fileInput.click());

  document.querySelectorAll('.quick-action').forEach(button => {
    button.addEventListener('click', () => {
      if (!state.docs.length) {
        showToast('Upload a PDF first, then DocMind can run that action.');
        fileInput.click();
        return;
      }
      const doc = state.docs[0];
      window.location.href = `/chat?pdf=${encodeURIComponent(doc.filename)}&action=${encodeURIComponent(button.dataset.action)}`;
    });
  });
}

async function loadDocuments() {
  grid.innerHTML = loadingState();
  try {
    const res = await apiFetch('/api/documents');
    state.docs = res.data.documents || [];
    renderDocuments();
  } catch (err) {
    grid.innerHTML = errorState(err.message);
  }
}

function renderDocuments() {
  const visible = state.showAll ? state.docs : state.docs.slice(0, 6);
  document.getElementById('doc-count').textContent = `${state.docs.length} document${state.docs.length === 1 ? '' : 's'} in your workspace`;
  document.getElementById('section-title').textContent = state.showAll ? 'All Documents' : 'Recent Documents';
  document.getElementById('view-all-btn').textContent = state.showAll ? 'Show Recent' : 'View All';
  
  if (!state.docs.length) {
    grid.innerHTML = emptyState();
    return;
  }
  grid.innerHTML = visible.map((doc, index) => cardTemplate(doc, index)).join('');
}

function cardTemplate(doc, index) {
  const indexed = (doc.indexed || Number(doc.pages || 0) > 0);
  const safe = encodeURIComponent(doc.filename);
  return `
    <article class="card-reveal bg-card border-4 border-ink shadow-brutal p-5 flex flex-col gap-4" style="animation-delay:${index * 35}ms">
      <div class="flex justify-between gap-3">
        <div class="h-14 w-14 border-4 border-ink bg-${indexed ? 'yellow' : 'soft'} grid place-items-center shadow-sm-brutal shrink-0">
          <span class="material-symbols-outlined text-3xl">picture_as_pdf</span>
        </div>
        <span class="h-fit border-4 border-ink ${indexed ? 'bg-yellow' : 'bg-dangerSoft'} px-2 py-1 text-xs font-black uppercase">${indexed ? 'Indexed' : 'Pending'}</span>
      </div>
      <div>
        <h3 class="text-xl font-black leading-tight line-clamp-2" title="${escapeHtml(doc.filename)}">${escapeHtml(doc.filename)}</h3>
        <p class="mt-1 text-sm font-bold text-muted">${doc.date || 'Unknown date'} | ${doc.size || 'Unknown size'}</p>
      </div>
      <dl class="grid grid-cols-3 gap-2 text-center">
        <div class="border-4 border-ink bg-soft p-2"><dt class="text-xs font-black uppercase text-muted">Pages</dt><dd class="font-black">${doc.pages || 0}</dd></div>
        <div class="border-4 border-ink bg-soft p-2"><dt class="text-xs font-black uppercase text-muted">Chats</dt><dd class="font-black">${doc.chats || 0}</dd></div>
        <div class="border-4 border-ink bg-soft p-2"><dt class="text-xs font-black uppercase text-muted">Activity</dt><dd class="font-black text-xs">${doc.last_activity || doc.date || 'New'}</dd></div>
      </dl>
      <div class="mt-auto grid grid-cols-[1fr_auto_auto] gap-2 pt-3 border-t-4 border-dashed border-ink">
        <a href="/chat?pdf=${safe}" class="border-4 border-ink bg-yellow px-3 py-2 font-black text-center hover:bg-yellowSoft transition">Open Chat</a>
        <a href="/document?pdf=${safe}" class="border-4 border-ink bg-card px-3 py-2 font-black hover:bg-soft transition" title="View Details"><span class="material-symbols-outlined">info</span></a>
        <button onclick="window.deleteDocument('${safe}')" class="border-4 border-ink bg-card px-3 py-2 font-black hover:bg-dangerSoft transition" title="Delete"><span class="material-symbols-outlined">delete</span></button>
      </div>
    </article>
  `;
}

function loadingState() {
  return '<div class="col-span-full border-4 border-ink bg-card shadow-brutal p-6 font-black">Loading documents...</div>';
}

function emptyState() {
  return `
    <div class="col-span-full bg-card border-4 border-ink shadow-brutal p-8 text-center">
      <div class="mx-auto h-20 w-20 rounded-full border-4 border-ink bg-yellow grid place-items-center shadow-sm-brutal"><span class="material-symbols-outlined text-4xl">folder_open</span></div>
      <h3 class="mt-5 text-3xl font-black">No documents yet</h3>
      <p class="mt-2 font-semibold text-muted">Upload your first PDF and DocMind will build a searchable, cited chat workspace.</p>
      <button onclick="document.getElementById('file-upload').click()" class="press shadow-brutal mt-5 bg-purple text-white border-4 border-ink px-5 py-3 font-black">Upload First PDF</button>
    </div>
  `;
}

function errorState(message) {
  return `<div class="col-span-full border-4 border-ink bg-dangerSoft shadow-brutal p-6 font-black text-danger">${escapeHtml(message)} <button onclick="window.loadDocuments()" class="underline">Try again</button></div>`;
}

function toggleViewAll() {
  state.showAll = !state.showAll;
  renderDocuments();
  document.getElementById('section-title').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function showSettings() {
  document.getElementById('modal-title').textContent = 'Settings';
  document.getElementById('modal-body').innerHTML = `
    <div class="space-y-3">
      <label class="flex items-center justify-between gap-3 border-4 border-ink bg-soft p-3"><span>Use cited answers</span><input type="checkbox" checked disabled></label>
      <label class="flex items-center justify-between gap-3 border-4 border-ink bg-soft p-3"><span>Neubrutalist motion</span><input type="checkbox" checked disabled></label>
      <p>Settings are wired as a product surface for this local demo. Core behavior is controlled by the FastAPI backend and document routes.</p>
    </div>`;
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

async function handleUpload(file) {
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    showFeedback('Please choose a PDF file.', true);
    return;
  }
  showFeedback(`Preparing ${file.name}...`);
  const request = indexedDB.open('DocMindDB', 1);
  request.onupgradeneeded = event => event.target.result.createObjectStore('temp_files');
  request.onerror = () => showFeedback('Browser storage failed. Try again.', true);
  request.onsuccess = event => {
    const db = event.target.result;
    const tx = db.transaction(['temp_files'], 'readwrite');
    tx.objectStore('temp_files').put(file, 'current_upload');
    tx.oncomplete = () => window.location.href = `/processing?file=${encodeURIComponent(file.name)}`;
  };
}

function showFeedback(message, isError = false) {
  const el = document.getElementById('upload-feedback');
  el.textContent = message;
  el.classList.remove('hidden', 'bg-dangerSoft', 'bg-soft', 'text-danger');
  el.classList.add(isError ? 'bg-dangerSoft' : 'bg-soft');
  if (isError) el.classList.add('text-danger');
}

async function deleteDocument(filename) {
  const decoded = decodeURIComponent(filename);
  if (!confirm(`Delete "${decoded}" from DocMind?`)) return;
  try {
    await apiFetch(`/api/document/${filename}`, { method: 'DELETE' });
    showToast('Document deleted.');
    await loadDocuments();
  } catch (err) {
    showToast(err.message);
  }
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.remove('hidden');
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.add('hidden'), 3200);
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#039;' }[char]));
}

// Expose modules to global window for inline HTML actions
window.deleteDocument = deleteDocument;
window.loadDocuments = loadDocuments;
window.toggleViewAll = toggleViewAll;
