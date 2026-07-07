const Layout = {
  menus: {
    platform_owner: [
      { href: '/dashboard/admin.html', label: 'Dashboard', icon: 'layout-dashboard' },
      { href: '/companies/index.html', label: 'Companies', icon: 'building-2' },
      { href: '/reports/index.html', label: 'Reports', icon: 'file-text' },
      { href: '/analytics/index.html', label: 'Analytics', icon: 'trending-up' },
      { href: '/governance/index.html', label: 'Governance', icon: 'shield' },
      { href: '/audit-logs/index.html', label: 'Audit Logs', icon: 'clipboard-list' },
      { href: '/settings/index.html', label: 'Settings', icon: 'settings' },
    ],
    company_admin: [
      { href: '/dashboard/company-admin.html', label: 'Dashboard', icon: 'layout-dashboard' },
      { href: '/companies/detail.html', label: 'My Company', icon: 'building-2', dynamic: 'company', tooltip: 'Your company profile' },
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

  refreshIcons() {
    if (typeof lucide === 'undefined' || this._iconRefreshScheduled) return;
    this._iconRefreshScheduled = true;
    requestAnimationFrame(() => {
      lucide.createIcons();
      this._iconRefreshScheduled = false;
    });
  },

  async init() {
    const role = Auth.getRole();
    const path = window.location.pathname;
    const nav = document.getElementById('sidebar-nav');

    let menu = [...(this.menus[role] || [])];

    if (Auth.isLoggedIn() && (role === 'company_admin' || role === 'employee')) {
      try {
        const user = await API.get('/users/me');
        if (user.company_id) {
          sessionStorage.setItem('company_id', user.company_id);
          menu = menu.map((item) => {
            if (item.dynamic === 'company') {
              return { ...item, href: `/companies/detail.html?id=${user.company_id}` };
            }
            return item;
          });
        }
      } catch {
        /* profile optional */
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

      this.refreshIcons();
    }

    const roleLabel = document.getElementById('user-role-label');
    if (roleLabel && role) {
      roleLabel.textContent = Auth.getRoleLabel();
    }

    await this.loadUserProfile();

    const sidebarCollapsed = localStorage.getItem('sidebar-collapsed') === 'true';
    const sidebar = document.getElementById('sidebar');
    if (sidebar && sidebarCollapsed) sidebar.classList.add('collapsed');

    const yearEl = document.getElementById('year');
    if (yearEl) yearEl.textContent = new Date().getFullYear();
  },

  async loadUserProfile() {
    if (!Auth.isLoggedIn()) return;
    try {
      const user = await API.get('/users/me');
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
    localStorage.setItem('sidebar-collapsed', sidebar.classList.contains('collapsed'));
    this.refreshIcons();
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

  openModal(content) {
    const container = document.getElementById('modal-container');
    const contentDiv = document.getElementById('modal-content');
    if (!container || !contentDiv) return;

    contentDiv.innerHTML = content;
    container.classList.remove('hidden');
    container.classList.add('flex');

    requestAnimationFrame(() => {
      contentDiv.classList.remove('scale-95', 'opacity-0');
      contentDiv.classList.add('scale-100', 'opacity-100');
    });

    this.refreshIcons();
  },

  closeModal() {
    const container = document.getElementById('modal-container');
    const contentDiv = document.getElementById('modal-content');
    if (!container || !contentDiv) return;

    contentDiv.classList.remove('scale-100', 'opacity-100');
    contentDiv.classList.add('scale-95', 'opacity-0');

    setTimeout(() => {
      container.classList.add('hidden');
      container.classList.remove('flex');
    }, 300);
  },

  openNotifications() {
    this.openModal(`
      <div class="p-6">
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-lg font-semibold text-slate-100">Notifications</h3>
          <button type="button" onclick="Layout.closeModal()" class="p-1.5 rounded-lg hover:bg-slate-700/50 text-slate-400 hover:text-slate-200 transition-colors">
            <i data-lucide="x" class="w-5 h-5"></i>
          </button>
        </div>
        <p class="text-sm text-slate-400">No new notifications.</p>
      </div>`);
  },

  openSettings() {
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
