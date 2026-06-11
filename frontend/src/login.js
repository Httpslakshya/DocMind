import { apiFetch } from './api.js';

const statusEl = document.getElementById('login-status');
const form = document.getElementById('login-form');

// Check if user is already logged in
if (localStorage.getItem('session_id')) {
  window.location.href = '/dashboard';
}

function setStatus(message, isError = true) {
  statusEl.textContent = message;
  statusEl.classList.remove('hidden', 'bg-dangerSoft', 'text-danger', 'bg-yellow');
  statusEl.classList.add(isError ? 'bg-dangerSoft' : 'bg-yellow', isError ? 'text-danger' : 'text-ink');
}

async function login(email, password) {
  const formData = new FormData();
  formData.append('email', email);
  formData.append('password', password);
  
  const btn = document.getElementById('signin-btn');
  const btnText = btn.querySelector('span');
  const originalText = btnText.textContent;
  
  btn.disabled = true;
  btnText.textContent = 'Signing In...';
  
  try {
    const res = await apiFetch('/api/login', { 
      method: 'POST', 
      body: formData 
    });
    
    // Cache session credentials
    localStorage.setItem('session_id', res.data.session_id);
    window.location.href = res.data.redirect;
  } catch (err) {
    setStatus(err.message);
    btn.disabled = false;
    btnText.textContent = originalText;
  }
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const email = document.getElementById('email').value.trim();
  const password = document.getElementById('password').value.trim();
  if (!email || !password) {
    setStatus('Add an email and password to continue.');
    return;
  }
  login(email, password);
});

document.getElementById('google-login-btn').addEventListener('click', () => {
  login('guest@docmind.local', 'demo-access');
});

document.getElementById('signup-btn').addEventListener('click', () => {
  login('new-user@docmind.local', 'demo-access');
});

document.getElementById('forgot-btn').addEventListener('click', () => {
  setStatus('Demo mode accepts any email and password. Try signing in directly.', false);
});
