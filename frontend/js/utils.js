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

  /** Default page size for all list views */
  PAGE_SIZE: 10,

  /**
   * Client-side pager for list pages.
   * Usage:
   *   const pager = Utils.createPager({ onChange: () => render() });
   *   const pageItems = pager.slice(filtered);
   *   pager.render('pagination-bar');
   */
  createPager(options = {}) {
    const pageSize = options.pageSize || this.PAGE_SIZE;
    const onChange = typeof options.onChange === 'function' ? options.onChange : () => {};
    return {
      page: 1,
      pageSize,
      total: 0,
      setItems(items) {
        const list = Array.isArray(items) ? items : [];
        this.total = list.length;
        const maxPage = Math.max(1, Math.ceil(this.total / this.pageSize) || 1);
        if (this.page > maxPage) this.page = maxPage;
        return this.slice(list);
      },
      slice(items) {
        const list = Array.isArray(items) ? items : [];
        this.total = list.length;
        const maxPage = Math.max(1, Math.ceil(this.total / this.pageSize) || 1);
        if (this.page > maxPage) this.page = maxPage;
        if (this.page < 1) this.page = 1;
        const start = (this.page - 1) * this.pageSize;
        return list.slice(start, start + this.pageSize);
      },
      totalPages() {
        return Math.max(1, Math.ceil(this.total / this.pageSize) || 1);
      },
      rangeLabel() {
        if (this.total === 0) return 'Showing 0 results';
        const start = (this.page - 1) * this.pageSize + 1;
        const end = Math.min(this.page * this.pageSize, this.total);
        return `Showing ${start}–${end} of ${this.total}`;
      },
      next() {
        if (this.page < this.totalPages()) {
          this.page += 1;
          onChange(this.page);
        }
      },
      prev() {
        if (this.page > 1) {
          this.page -= 1;
          onChange(this.page);
        }
      },
      go(page) {
        const p = Math.min(Math.max(1, page), this.totalPages());
        if (p !== this.page) {
          this.page = p;
          onChange(this.page);
        }
      },
      reset() {
        this.page = 1;
      },
      /** Render into a container that already has #id-info, #id-prev, #id-next (or create full bar). */
      render(containerId) {
        const el = document.getElementById(containerId);
        if (!el) return;
        const pages = this.totalPages();
        const canPrev = this.page > 1;
        const canNext = this.page < pages && this.total > 0;
        el.innerHTML = `
          <p class="text-xs text-slate-500">${this.rangeLabel()}</p>
          <div class="flex items-center gap-2">
            <button type="button" class="btn-premium btn-secondary-glass px-3 py-1.5 text-xs ${canPrev ? '' : 'opacity-40 cursor-not-allowed'}" data-pager-prev ${canPrev ? '' : 'disabled'}>
              <i data-lucide="chevron-left" class="w-3.5 h-3.5"></i>
              <span class="hidden sm:inline">Prev</span>
            </button>
            <span class="text-xs text-slate-400 font-medium min-w-[4.5rem] text-center">Page ${this.page} / ${pages}</span>
            <button type="button" class="btn-premium btn-secondary-glass px-3 py-1.5 text-xs ${canNext ? '' : 'opacity-40 cursor-not-allowed'}" data-pager-next ${canNext ? '' : 'disabled'}>
              <span class="hidden sm:inline">Next</span>
              <i data-lucide="chevron-right" class="w-3.5 h-3.5"></i>
            </button>
          </div>`;
        el.querySelector('[data-pager-prev]')?.addEventListener('click', () => this.prev());
        el.querySelector('[data-pager-next]')?.addEventListener('click', () => this.next());
        if (typeof Layout !== 'undefined') Layout.refreshIcons(el);
        else if (typeof lucide !== 'undefined') lucide.createIcons({ root: el });
      },
    };
  },
};

window.Utils = Utils;
