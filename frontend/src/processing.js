import { API_URL, apiFetch, checkAuth } from './api.js';

const steps = ['upload', 'chunk', 'embedding', 'indexing', 'ready'];
const progressFill = document.getElementById('progress-fill');
const progressLabel = document.getElementById('progress-label');
const statusTitle = document.getElementById('status-title');
const errorBox = document.getElementById('error-box');
let cancelled = false;

// Verify session
checkAuth();

document.addEventListener('DOMContentLoaded', startProcessing);
document.getElementById('cancel-btn').addEventListener('click', () => {
  cancelled = true;
  window.location.href = '/dashboard';
});

async function startProcessing() {
  try {
    const file = await getStoredFile();
    if (!file) throw new Error('The upload file reference was lost. Please choose the PDF again.');
    document.getElementById('file-note').textContent = `${file.name} | ${formatBytes(file.size)}`;
    await uploadWithProgress(file);
  } catch (err) {
    showError(err.message);
  }
}

function getStoredFile() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('DocMindDB', 1);
    request.onupgradeneeded = event => event.target.result.createObjectStore('temp_files');
    request.onerror = () => reject(new Error('Could not open browser storage.'));
    request.onsuccess = event => {
      const db = event.target.result;
      const tx = db.transaction(['temp_files'], 'readonly');
      const getReq = tx.objectStore('temp_files').get('current_upload');
      getReq.onsuccess = () => resolve(getReq.result);
      getReq.onerror = () => reject(new Error('Could not read the staged PDF.'));
    };
  });
}

function uploadWithProgress(file) {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const xhr = new XMLHttpRequest();
    
    // Set initial status to uploading
    activateStep('upload');
    
    xhr.upload.onprogress = event => {
      if (!event.lengthComputable) return;
      // Map file upload (0-100%) to total progress (0-10%)
      const pct = Math.round((event.loaded / event.total) * 10);
      setProgress(pct);
    };
    
    xhr.onload = async () => {
      if (cancelled) return;
      
      if (xhr.status < 200 || xhr.status >= 300) {
        try {
          const res = JSON.parse(xhr.responseText);
          reject(new Error(res.message || res.detail || 'Upload failed.'));
        } catch {
          reject(new Error('Upload failed.'));
        }
        return;
      }
      
      try {
        const res = JSON.parse(xhr.responseText);
        if (res.success === false) {
          reject(new Error(res.message || 'Upload failed.'));
          return;
        }
        
        // Successfully uploaded, now poll background indexing progress
        const jobId = res.data.job_id;
        setProgress(15);
        startPolling(jobId, resolve, reject);
      } catch (e) {
        reject(new Error('Failed to parse upload response.'));
      }
    };
    
    xhr.onerror = () => {
      reject(new Error('Network error while uploading the PDF.'));
    };
    
    xhr.open('POST', `${API_URL}/api/upload`);
    xhr.send(formData);
  });
}

function startPolling(jobId, resolve, reject) {
  let pollInterval = setInterval(async () => {
    if (cancelled) {
      clearInterval(pollInterval);
      return;
    }
    
    try {
      const res = await apiFetch(`/api/upload/status/${jobId}`);
      const job = res.data;
      
      // Update progress bar
      setProgress(job.progress);
      
      // Update steps based on progress and status
      if (job.status === 'queued') {
        activateStep('upload');
      } else if (job.status === 'processing') {
        if (job.progress >= 15 && job.progress < 45) {
          activateStep('chunk');
        } else if (job.progress >= 45 && job.progress < 70) {
          activateStep('embedding');
        } else if (job.progress >= 70) {
          activateStep('indexing');
        }
      } else if (job.status === 'completed') {
        clearInterval(pollInterval);
        activateStep('ready');
        statusTitle.textContent = 'Ready to chat';
        document.getElementById('main-icon').textContent = 'check_circle';
        setProgress(100);
        clearStoredFile();
        
        setTimeout(() => {
          window.location.href = `/chat?pdf=${encodeURIComponent(job.filename)}&welcome=1`;
        }, 850);
        resolve();
      } else if (job.status === 'failed') {
        clearInterval(pollInterval);
        reject(new Error(job.error || 'Background indexing failed.'));
      }
    } catch (err) {
      // We don't reject immediately on transient network errors while polling
      console.warn('Status poll error (retrying):', err);
    }
  }, 800);
}

function activateStep(stepName) {
  const index = steps.indexOf(stepName);
  steps.forEach((step, stepIndex) => {
    const el = document.querySelector(`[data-step="${step}"]`);
    if (el) {
      el.classList.toggle('bg-yellow', stepIndex <= index);
      el.classList.toggle('bg-soft', stepIndex > index);
    }
  });
  
  const titles = {
    upload: 'Uploading PDF...',
    chunk: 'Chunking document...',
    embedding: 'Creating embeddings...',
    indexing: 'Indexing into Qdrant...',
    ready: 'Ready to chat'
  };
  statusTitle.textContent = titles[stepName];
}

// Global expose for cancel button
window.activateStep = activateStep;

function setProgress(value) {
  const pct = Math.max(0, Math.min(100, Math.round(value)));
  progressFill.style.width = `${pct}%`;
  progressLabel.textContent = `${pct}%`;
}

function showError(message) {
  statusTitle.textContent = 'Processing failed';
  document.getElementById('main-icon').textContent = 'error';
  errorBox.textContent = message;
  errorBox.classList.remove('hidden');
  document.getElementById('cancel-btn').textContent = 'Back to Library';
}

function clearStoredFile() {
  const request = indexedDB.open('DocMindDB', 1);
  request.onsuccess = event => {
    const db = event.target.result;
    db.transaction(['temp_files'], 'readwrite').objectStore('temp_files').delete('current_upload');
  };
}

function formatBytes(bytes) {
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(index ? 1 : 0)} ${units[index]}`;
}
