const Layout = {
  menus: {
    platform_owner: [
      { href: '/dashboard/admin.html', label: 'Dashboard', icon: 'layout-dashboard' },
      { href: '/companies/index.html', label: 'Companies', icon: 'building-2' },
      { href: '/team/index.html', label: 'Users', icon: 'users' },
      { href: '/reports/index.html', label: 'Reports', icon: 'file-text' },
      { href: '/analytics/index.html', label: 'Analytics', icon: 'trending-up' },
      { href: '/governance/index.html', label: 'Governance', icon: 'shield' },
      { href: '/audit-logs/index.html', label: 'Audit Logs', icon: 'clipboard-list' },
      { href: '/settings/index.html', label: 'Settings', icon: 'settings' },
    ],
    company_admin: [
      { href: '/dashboard/company-admin.html', label: 'Dashboard', icon: 'layout-dashboard' },
      { href: '/companies/detail.html', label: 'My Company', icon: 'building-2', dynamic: 'company', tooltip: 'Your company profile' },
      { href: '/team/index.html', label: 'Team', icon: 'users' },
      { href: '/reports/index.html', label: 'Reports', icon: 'file-text' },
      { href: '/analytics/index.html', label: 'Analytics', icon: 'trending-up' },
      { href: '/governance/index.html', label: 'Governance', icon: 'shield' },
      { href: '/settings/index.html', label: 'Settings', icon: 'settings' },
    ],
    employee: [
      { href: '/dashboard/employee.html', label: 'Dashboard', icon: 'layout-dashboard' },
      { href: '/companies/detail.html', label: 'My Company', icon: 'building-2', dynamic: 'company', tooltip: 'Your company profile' },
      { href: '/reports/index.html', label: 'Reports', icon: 'file-text' },
      { href: '/analytics/index.html', label: 'Analytics', icon: 'bar-chart-2' },
      { href: '/governance/index.html', label: 'Governance', icon: 'shield' },
      { href: '/settings/index.html', label: 'Settings', icon: 'settings' },
    ],
  },

  _iconRefreshScheduled: false,
  _initStarted: false,

  refreshIcons(root) {
    if (typeof lucide === 'undefined') return;
    if (this._iconRefreshScheduled) return;
    this._iconRefreshScheduled = true;
    requestAnimationFrame(() => {
      try {
        lucide.createIcons(root ? { root } : undefined);
      } catch (e) {
        console.warn('Icon refresh failed', e);
      }
      this._iconRefreshScheduled = false;
    });
  },

  _updateSidebarToggleIcon(collapsed) {
    const icon = document.getElementById('sidebar-toggle-icon');
    if (icon) {
      icon.setAttribute('data-lucide', collapsed ? 'panel-left-open' : 'panel-left-close');
      this.refreshIcons(icon.parentElement || document.getElementById('sidebar'));
    }
    const headerBtn = document.getElementById('desktop-sidebar-toggle');
    if (headerBtn) {
      const headerIcon = headerBtn.querySelector('[data-lucide]');
      if (headerIcon) {
        headerIcon.setAttribute('data-lucide', collapsed ? 'panel-left-open' : 'panel-left');
        this.refreshIcons(headerBtn);
      }
    }
  },

  _applySidebarState() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    const collapsed = localStorage.getItem('sidebar-collapsed') === 'true';
    sidebar.classList.toggle('collapsed', collapsed);
    this._updateSidebarToggleIcon(collapsed);
  },

  async init() {
    if (this._initStarted) return;
    this._initStarted = true;

    this._applySidebarState();

    const role = Auth.getRole();
    const path = window.location.pathname;
    const nav = document.getElementById('sidebar-nav');

    let menu = [...(this.menus[role] || [])];

    if (Auth.isLoggedIn() && (role === 'company_admin' || role === 'employee')) {
      let companyId = sessionStorage.getItem('company_id');
      if (!companyId) {
        try {
          const user = await Promise.race([
            API.get('/users/me'),
            new Promise((resolve) => setTimeout(() => resolve(null), 8000)),
          ]);
          if (user?.company_id) {
            companyId = String(user.company_id);
            sessionStorage.setItem('company_id', companyId);
          }
        } catch {
          /* use default menu hrefs */
        }
      }
      if (companyId) {
        menu = menu.map((item) => {
          if (item.dynamic === 'company') {
            return { ...item, href: `/companies/detail.html?id=${companyId}` };
          }
          return item;
        });
      }
    }

    if (nav) {
      nav.innerHTML = menu.map((item) => {
        const segment = item.href.replace('/index.html', '').replace('.html', '').split('?')[0];
        const active = path.includes(segment) ? 'active' : '';
        return `
          <a href="${item.href}" class="nav-link ${active} tooltip" data-tooltip="${item.label}">
            <i data-lucide="${item.icon}" class="nav-icon"></i>
            <span class="sidebar-text">${item.label}</span>
          </a>`;
      }).join('');

      this.refreshIcons(nav);
    }

    const roleLabel = document.getElementById('user-role-label');
    if (roleLabel && role) {
      roleLabel.textContent = Auth.getRoleLabel();
    }

    this.loadUserProfile().catch(() => {});
    this.loadNotificationBadge().catch(() => {});

    const yearEl = document.getElementById('year');
    if (yearEl) yearEl.textContent = new Date().getFullYear();
  },

  async loadUserProfile() {
    if (!Auth.isLoggedIn()) return;
    try {
      const user = await Promise.race([
        API.get('/users/me'),
        new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 15000)),
      ]);
      if (user.company_id) sessionStorage.setItem('company_id', user.company_id);
      const initials = `${(user.name || 'U')[0]}${(user.surname || '')[0] || ''}`.toUpperCase();
      const initialsEl = document.getElementById('user-initials');
      const nameEl = document.getElementById('user-name');
      const emailEl = document.getElementById('user-email');
      if (initialsEl) initialsEl.textContent = initials;
      if (nameEl) nameEl.textContent = `${user.name} ${user.surname}`;
      if (emailEl) emailEl.textContent = user.email;
    } catch {
      /* profile optional on some pages */
    }
  },

  toggleMobile() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('mobile-overlay');
    if (!sidebar) return;
    sidebar.classList.toggle('mobile-open');
    if (overlay) overlay.classList.toggle('active');
    document.body.style.overflow = sidebar.classList.contains('mobile-open') ? 'hidden' : '';
  },

  toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    sidebar.classList.toggle('collapsed');
    const collapsed = sidebar.classList.contains('collapsed');
    localStorage.setItem('sidebar-collapsed', collapsed);
    this._updateSidebarToggleIcon(collapsed);
    this.refreshIcons(sidebar);
  },

  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const icons = {
      success: 'check-circle',
      error: 'x-circle',
      warning: 'alert-triangle',
      info: 'info',
    };
    const colors = {
      success: 'border-green-500/30 bg-green-500/10 text-green-400',
      error: 'border-red-500/30 bg-red-500/10 text-red-400',
      warning: 'border-yellow-500/30 bg-yellow-500/10 text-yellow-400',
      info: 'border-blue-500/30 bg-blue-500/10 text-blue-400',
    };

    const toast = document.createElement('div');
    toast.className = `pointer-events-auto flex items-center gap-3 px-5 py-4 rounded-xl border shadow-lg ${colors[type] || colors.info}`;
    toast.innerHTML = `
      <i data-lucide="${icons[type] || icons.info}" class="w-5 h-5 flex-shrink-0"></i>
      <span class="text-sm font-medium">${message}</span>
      <button type="button" onclick="this.parentElement.remove()" class="ml-auto opacity-60 hover:opacity-100 transition-opacity">
        <i data-lucide="x" class="w-4 h-4"></i>
      </button>`;
    container.appendChild(toast);
    this.refreshIcons();

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  },

  openModal(content, options = {}) {
    const container = document.getElementById('modal-container');
    const contentDiv = document.getElementById('modal-content');
    if (!container || !contentDiv) return;

    contentDiv.className = `relative bg-slate-800 border border-slate-700/50 rounded-2xl shadow-2xl w-full max-h-[90vh] overflow-auto ${options.size === 'xl' ? 'max-w-xl' : 'max-w-lg'}`;
    contentDiv.innerHTML = content;
    container.classList.remove('hidden');
    container.classList.add('flex');
    document.body.style.overflow = 'hidden';

    this.refreshIcons(contentDiv);
  },

  closeModal() {
    const container = document.getElementById('modal-container');
    const contentDiv = document.getElementById('modal-content');
    if (!container || !contentDiv) return;

    container.classList.add('hidden');
    container.classList.remove('flex');
    contentDiv.innerHTML = '';
    document.body.style.overflow = '';
  },

  async openNotifications() {
    try {
      const [list, count] = await Promise.all([
        API.get('/notifications/?limit=20'),
        API.get('/notifications/unread-count'),
      ]);
      const items = Utils.unwrapList(list);
      const body = items.length ? items.map(n => `
        <div class="p-4 rounded-xl border border-slate-700/40 bg-slate-800/40 mb-3 ${n.is_read ? 'opacity-70' : ''}">
          <div class="flex items-start justify-between gap-2">
            <p class="text-sm font-medium text-slate-200">${n.title}</p>
            <span class="text-xs text-slate-500 whitespace-nowrap">${Utils.timeAgo(n.created_at)}</span>
          </div>
          <p class="text-xs text-slate-400 mt-1">${n.message}</p>
        </div>`).join('') : '<p class="text-sm text-slate-400">No notifications yet.</p>';

      this.openModal(`
        <div class="p-6 max-w-lg">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-semibold text-slate-100">Notifications ${count.count ? `<span class="text-xs text-blue-400">(${count.count} unread)</span>` : ''}</h3>
            <div class="flex gap-2">
              ${count.count ? `<button type="button" class="text-xs text-blue-400 hover:text-blue-300" onclick="Layout.markAllNotificationsRead()">Mark all read</button>` : ''}
              <button type="button" onclick="Layout.closeModal()" class="p-1.5 rounded-lg hover:bg-slate-700/50 text-slate-400">
                <i data-lucide="x" class="w-5 h-5"></i>
              </button>
            </div>
          </div>
          <div class="max-h-96 overflow-y-auto">${body}</div>
        </div>`);
    } catch (err) {
      this.openModal(`<div class="p-6"><p class="text-sm text-slate-400">${err.message || 'Failed to load notifications'}</p></div>`);
    }
  },

  async markAllNotificationsRead() {
    try {
      await API.post('/notifications/read-all');
      this.closeModal();
      this.openNotifications();
    } catch (err) {
      this.showToast(err.message || 'Failed', 'error');
    }
  },

  async loadNotificationBadge() {
    if (!Auth.isLoggedIn()) return;
    try {
      const { count } = await Promise.race([
        API.get('/notifications/unread-count'),
        new Promise((resolve) => setTimeout(() => resolve({ count: 0 }), 8000)),
      ]);
      const badge = document.getElementById('notification-badge') || document.getElementById('notif-badge');
      if (badge) {
        badge.textContent = count > 99 ? '99+' : count;
        badge.classList.toggle('hidden', !count);
      }
    } catch { /* optional */ }
  },

  openSettings() {
    this.openProfile();
  },

  openProfile(event) {
    if (event) event.preventDefault();
    const sidebar = document.getElementById('sidebar');
    if (sidebar?.classList.contains('mobile-open')) this.toggleMobile();
    window.location.href = '/settings/index.html';
  },

  setBreadcrumbs(items) {
    const bar = document.getElementById('breadcrumb-bar');
    const container = document.getElementById('breadcrumbs');
    if (!bar || !container) return;

    if (!items || items.length === 0) {
      bar.classList.add('hidden');
      return;
    }

    bar.classList.remove('hidden');
    container.innerHTML = items.map((item, index) => {
      const isLast = index === items.length - 1;
      return `
        ${index > 0 ? '<span class="breadcrumb-separator">/</span>' : ''}
        ${isLast
          ? `<span class="breadcrumb-item text-slate-300 font-medium">${item.label}</span>`
          : `<a href="${item.href || '#'}" class="breadcrumb-item hover:text-blue-400 transition-colors">${item.label}</a>`}`;
    }).join('');
  },
};

window.Layout = Layout;

const Toast = {
  show(type, message) {
    Layout.showToast(message, type);
  },
};
window.Toast = Toast;

document.addEventListener('DOMContentLoaded', () => {
  Layout.refreshIcons();
  if (Auth.isLoggedIn()) Layout.init();
});

document.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    const searchInput = document.getElementById('global-search') || document.getElementById('sidebar-search');
    if (searchInput) searchInput.focus();
  }
  if (e.key === 'Escape') {
    Layout.closeModal();
    const sidebar = document.getElementById('sidebar');
    if (sidebar?.classList.contains('mobile-open')) Layout.toggleMobile();
  }
});
