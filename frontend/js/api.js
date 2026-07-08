const API = {
  REQUEST_TIMEOUT_MS: 20000,
  REFRESH_TIMEOUT_MS: 10000,

  async fetchWithTimeout(url, options = {}, timeoutMs = this.REQUEST_TIMEOUT_MS) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    try {
      return await fetch(url, { ...options, signal: controller.signal });
    } catch (err) {
      if (err.name === 'AbortError') {
        throw new Error('Request timed out — server may be waking up, please retry');
      }
      throw new Error('Network error — check your connection and server');
    } finally {
      clearTimeout(timeoutId);
    }
  },

  async request(method, path, body, isForm = false) {
    const buildOptions = (token) => {
      const headers = {};
      if (token) headers.Authorization = `Bearer ${token}`;
      if (!isForm) headers['Content-Type'] = 'application/json';
      const opts = { method, headers };
      if (body) opts.body = isForm ? body : JSON.stringify(body);
      return opts;
    };

    let token = sessionStorage.getItem('access_token');
    let res = await this.fetchWithTimeout(`/api${path}`, buildOptions(token));

    if (res.status === 401 && sessionStorage.getItem('refresh_token')) {
      const refreshed = await this.refresh();
      if (refreshed) {
        token = sessionStorage.getItem('access_token');
        res = await this.fetchWithTimeout(`/api${path}`, buildOptions(token));
      }
    }

    if (res.status === 401) {
      sessionStorage.clear();
      window.location.href = '/auth/login.html';
      throw new Error('Session expired — please sign in again');
    }

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = data.detail;
      let msg = data.message || 'Request failed';
      if (Array.isArray(detail)) {
        msg = detail.map((d) => d.msg || JSON.stringify(d)).join('; ');
      } else if (typeof detail === 'string') {
        msg = detail;
      }
      throw new Error(msg);
    }
    return data;
  },

  async download(path, filename) {
    const token = sessionStorage.getItem('access_token');
    const res = await this.fetchWithTimeout(`/api${path}`, {
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
    const refreshToken = sessionStorage.getItem('refresh_token');
    if (!refreshToken) return false;
    try {
      const res = await this.fetchWithTimeout(
        '/api/auth/refresh',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        },
        this.REFRESH_TIMEOUT_MS,
      );
      if (!res.ok) return false;
      const data = await res.json();
      sessionStorage.setItem('access_token', data.access_token);
      sessionStorage.setItem('refresh_token', data.refresh_token);
      return true;
    } catch {
      return false;
    }
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
      xhr.timeout = this.REQUEST_TIMEOUT_MS;
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress) onProgress(Math.round((e.loaded / e.total) * 100));
      };
      xhr.onload = () => {
        try {
          const data = JSON.parse(xhr.responseText);
          if (xhr.status >= 400) reject(new Error(data.detail || 'Upload failed'));
          else resolve(data);
        } catch (e) {
          reject(e);
        }
      };
      xhr.onerror = () => reject(new Error('Upload failed'));
      xhr.ontimeout = () => reject(new Error('Upload timed out'));
      xhr.send(formData);
    });
  },
};

window.API = API;
