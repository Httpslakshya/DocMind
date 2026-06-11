export const API_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

/**
 * Custom fetch wrapper to handle API requests and standardize errors.
 */
export async function apiFetch(endpoint, options = {}) {
  const url = endpoint.startsWith('http') ? endpoint : `${API_URL}${endpoint}`;
  const sessionId = localStorage.getItem('session_id');
  const headers = {
    ...(sessionId ? { 'x-session-id': sessionId } : {}),
    ...options.headers
  };
  
  // Set credentials mode to send session cookies to Render backend
  options.credentials = options.credentials || 'include';
  
  if (options.body && !(options.body instanceof FormData)) {
    options.headers = {
      'Content-Type': 'application/json',
      ...headers
    };
  } else {
    options.headers = headers;
  }

  const response = await fetch(url, options);
  
  // If it's a binary file stream (not JSON), return response directly
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }
    return response;
  }

  const data = await response.json();
  
  if (!response.ok || data.success === false) {
    throw new Error(data.message || data.detail || 'API request failed');
  }
  
  return data;
}

/**
 * Helper to check local session status and redirect if necessary.
 */
export function checkAuth() {
  const sessionId = localStorage.getItem('session_id');
  if (!sessionId) {
    window.location.href = '/login';
    return null;
  }
  return sessionId;
}
