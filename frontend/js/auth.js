const Auth = {
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

  requireAuth() {
    if (!this.isLoggedIn()) {
      window.location.href = '/auth/login.html';
      return false;
    }
    return true;
  },

  redirectByRole() {
    const role = this.getRole();
    if (role === 'platform_owner') window.location.href = '/dashboard/admin.html';
    else if (role === 'company_admin') window.location.href = '/dashboard/company-admin.html';
    else window.location.href = '/dashboard/employee.html';
  },

  canAccess(roles) {
    return roles.includes(this.getRole());
  },
};

window.Auth = Auth;
