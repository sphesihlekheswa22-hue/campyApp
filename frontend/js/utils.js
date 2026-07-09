const Utils = {
  formatDate(d) {
    if (!d) return '-';
    return new Date(d).toLocaleDateString('en-ZA', { year: 'numeric', month: 'short', day: 'numeric' });
  },

  formatDateTime(d) {
    if (!d) return '-';
    return new Date(d).toLocaleString('en-ZA', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  },

  timeAgo(d) {
    if (!d) return '';
    const seconds = Math.floor((Date.now() - new Date(d).getTime()) / 1000);
    if (seconds < 60) return 'just now';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days}d ago`;
    return this.formatDate(d);
  },

  formatNumber(n) {
    if (!n) return '0';
    return Number(n).toLocaleString('en-ZA', { maximumFractionDigits: 2 });
  },

  formatCurrency(n) {
    return 'R ' + this.formatNumber(n);
  },

  riskBadge(level) {
    const cls = level === 'low' ? 'badge-low' : level === 'high' ? 'badge-high' : 'badge-medium';
    return `<span class="badge ${cls}">${level || 'medium'}</span>`;
  },

  statusBadge(status) {
    const s = (status || 'pending').toLowerCase();
    return `<span class="status-badge ${s}">${s}</span>`;
  },

  showAlert(el, message, type = 'error') {
    if (typeof AuthUI !== 'undefined') {
      AuthUI.showToast(message, type === 'success' ? 'success' : type === 'error' ? 'error' : 'info');
      return;
    }
    if (el) el.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
  },

  debounce(fn, ms = 300) {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), ms);
    };
  },

  getParam(name) {
    return new URLSearchParams(window.location.search).get(name);
  },

  buildQuery(params = {}) {
    const sp = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== null && value !== undefined && String(value).trim() !== '') {
        sp.set(key, String(value).trim());
      }
    });
    const query = sp.toString();
    return query ? `?${query}` : '';
  },

  /** Normalize paginated API responses `{ items, total }` or plain arrays. */
  unwrapList(data) {
    if (Array.isArray(data)) return data;
    if (data && Array.isArray(data.items)) return data.items;
    return [];
  },
};

window.Utils = Utils;
