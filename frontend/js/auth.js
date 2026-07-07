const Auth = {
  PAGE_ROLES: {
    '/dashboard/admin.html': ['platform_owner'],
    '/dashboard/company-admin.html': ['company_admin'],
    '/dashboard/employee.html': ['employee'],
    '/companies/index.html': ['platform_owner'],
    '/companies/detail.html': ['platform_owner', 'company_admin', 'employee'],
    '/reports/index.html': ['platform_owner', 'company_admin', 'employee'],
    '/analytics/index.html': ['platform_owner', 'company_admin', 'employee'],
    '/governance/index.html': ['platform_owner', 'company_admin', 'employee'],
    '/audit-logs/index.html': ['platform_owner'],
    '/settings/index.html': ['platform_owner', 'company_admin', 'employee'],
  },

  PERMISSIONS: {
    platform_owner: [
      'upload_reports', 'export_analytics', 'run_analytics', 'manage_companies',
      'view_audit', 'company_comparison', 'retry_extraction', 'create_company',
    ],
    company_admin: ['upload_reports', 'export_analytics', 'run_analytics', 'retry_extraction'],
    employee: ['view_reports', 'view_analytics', 'view_governance'],
  },

  ROLE_LABELS: {
    platform_owner: 'Platform Owner',
    company_admin: 'Company Admin',
    employee: 'Employee',
  },

  login(data) {
    sessionStorage.setItem('access_token', data.access_token);
    sessionStorage.setItem('refresh_token', data.refresh_token);
    sessionStorage.setItem('role', data.role);
    sessionStorage.setItem('user_id', data.user_id);
  },

  logout() {
    sessionStorage.clear();
    window.location.href = '/auth/login.html';
  },

  isLoggedIn() {
    return !!sessionStorage.getItem('access_token');
  },

  getRole() {
    return sessionStorage.getItem('role');
  },

  getUserId() {
    return sessionStorage.getItem('user_id');
  },

  getCompanyId() {
    return sessionStorage.getItem('company_id');
  },

  getRoleLabel() {
    return this.ROLE_LABELS[this.getRole()] || this.getRole() || '';
  },

  requireAuth() {
    if (!this.isLoggedIn()) {
      window.location.href = '/auth/login.html';
      return false;
    }
    return true;
  },

  getDashboardUrl() {
    const role = this.getRole();
    if (role === 'platform_owner') return '/dashboard/admin.html';
    if (role === 'company_admin') return '/dashboard/company-admin.html';
    return '/dashboard/employee.html';
  },

  redirectByRole() {
    window.location.href = this.getDashboardUrl();
  },

  canAccess(roles) {
    return roles.includes(this.getRole());
  },

  hasPermission(permission) {
    const perms = this.PERMISSIONS[this.getRole()] || [];
    return perms.includes(permission);
  },

  _pageRoles() {
    const path = window.location.pathname;
    return this.PAGE_ROLES[path] || null;
  },

  guardPage(allowedRoles) {
    if (!this.requireAuth()) return false;

    const roles = allowedRoles || this._pageRoles();
    if (!roles) return true;

    if (!roles.includes(this.getRole())) {
      if (typeof Layout !== 'undefined') {
        Layout.showToast('You do not have permission to access this page', 'error');
      }
      setTimeout(() => this.redirectByRole(), 700);
      return false;
    }
    return true;
  },

  async guardCompanyAccess(companyId) {
    if (this.canAccess(['platform_owner'])) return true;
    const myCompanyId = this.getCompanyId();
    if (myCompanyId && String(companyId) === String(myCompanyId)) return true;
    try {
      const user = await API.get('/users/me');
      if (user.company_id) sessionStorage.setItem('company_id', user.company_id);
      if (String(user.company_id) === String(companyId)) return true;
    } catch (_) {}
    if (typeof Layout !== 'undefined') {
      Layout.showToast('You can only view your assigned company', 'error');
    }
    setTimeout(() => this.redirectByRole(), 700);
    return false;
  },

  async redirectIfNotCompanyDirectory() {
    if (this.canAccess(['platform_owner'])) return false;
    try {
      const user = await API.get('/users/me');
      if (user.company_id) {
        sessionStorage.setItem('company_id', user.company_id);
        window.location.href = `/companies/detail.html?id=${user.company_id}`;
        return true;
      }
    } catch (_) {}
    this.redirectByRole();
    return true;
  },
};

window.Auth = Auth;
