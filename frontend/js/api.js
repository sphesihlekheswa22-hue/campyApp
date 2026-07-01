const API = {
  async request(method, path, body, isForm = false) {
    const headers = {};
    const token = sessionStorage.getItem('access_token');
    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (!isForm) headers['Content-Type'] = 'application/json';

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);
    const opts = { method, headers, signal: controller.signal };
    if (body) opts.body = isForm ? body : JSON.stringify(body);

    let res;
    try {
      res = await fetch(`/api${path}`, opts);
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') throw new Error('Request timed out — is the server running?');
      throw new Error('Network error — check your connection and server');
    }
    clearTimeout(timeoutId);

    if (res.status === 401 && sessionStorage.getItem('refresh_token')) {
      const refreshed = await this.refresh();
      if (refreshed) {
        headers['Authorization'] = `Bearer ${sessionStorage.getItem('access_token')}`;
        res = await fetch(`/api${path}`, { method, headers, body: opts.body, signal: controller.signal });
      }
    }
    if (res.status === 401) {
      sessionStorage.clear();
      throw new Error('Session expired — please sign in again');
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = data.detail;
      const msg = Array.isArray(detail) ? detail.map(d => d.msg).join(', ') : (detail || data.message || 'Request failed');
      throw new Error(msg);
    }
    return data;
  },

  async download(path, filename) {
    const token = sessionStorage.getItem('access_token');
    const res = await fetch(`/api${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error('Download failed');
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },

  async refresh() {
    try {
      const res = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: sessionStorage.getItem('refresh_token') }),
      });
      if (!res.ok) return false;
      const data = await res.json();
      sessionStorage.setItem('access_token', data.access_token);
      sessionStorage.setItem('refresh_token', data.refresh_token);
      return true;
    } catch { return false; }
  },

  get: (path) => API.request('GET', path),
  post: (path, body) => API.request('POST', path, body),
  put: (path, body) => API.request('PUT', path, body),
  delete: (path) => API.request('DELETE', path),

  uploadWithProgress(path, formData, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', `/api${path}`);
      const token = sessionStorage.getItem('access_token');
      if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress) onProgress(Math.round((e.loaded / e.total) * 100));
      };
      xhr.onload = () => {
        try {
          const data = JSON.parse(xhr.responseText);
          if (xhr.status >= 400) reject(new Error(data.detail || 'Upload failed'));
          else resolve(data);
        } catch (e) { reject(e); }
      };
      xhr.onerror = () => reject(new Error('Upload failed'));
      xhr.send(formData);
    });
  },
};

window.API = API;
