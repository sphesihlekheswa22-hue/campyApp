const AuthUI = {
  showToast(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const icons = { success: 'check-circle', error: 'x-circle', info: 'info', warning: 'alert-triangle' };
    const toastType = type === 'success' ? 'success' : type === 'error' ? 'error' : 'info';

    const toast = document.createElement('div');
    toast.className = `toast toast-${toastType}`;
    toast.innerHTML = `
      <i data-lucide="${icons[toastType] || icons.info}" class="w-5 h-5 flex-shrink-0"></i>
      <span class="text-sm font-medium">${message}</span>
      <button type="button" onclick="this.parentElement.remove()" class="ml-auto opacity-60 hover:opacity-100 transition-opacity p-1">
        <i data-lucide="x" class="w-4 h-4"></i>
      </button>`;
    container.appendChild(toast);
    if (typeof lucide !== 'undefined') lucide.createIcons();

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(-10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  },

  generateParticles() {
    /* Disabled for performance */
  },

  togglePassword(inputId, button) {
    const input = document.getElementById(inputId);
    const icon = button?.querySelector('i');
    if (!input || !icon) return;

    if (input.type === 'password') {
      input.type = 'text';
      icon.setAttribute('data-lucide', 'eye-off');
    } else {
      input.type = 'password';
      icon.setAttribute('data-lucide', 'eye');
    }
    if (typeof lucide !== 'undefined') lucide.createIcons();
  },

  validateForm(form) {
    const inputs = form.querySelectorAll('.input-premium[required]');
    let isValid = true;
    inputs.forEach((input) => {
      if (!input.value.trim()) {
        isValid = false;
        input.style.borderColor = 'rgba(239, 68, 68, 0.5)';
        input.style.boxShadow = '0 0 0 3px rgba(239, 68, 68, 0.1)';
      } else {
        input.style.borderColor = '';
        input.style.boxShadow = '';
      }
    });
    return isValid;
  },

  setButtonLoading(button, loading = true) {
    if (!button) return;
    if (loading) {
      button.disabled = true;
      button.dataset.originalContent = button.innerHTML;
      button.innerHTML = '<div class="spinner"></div><span>Processing...</span>';
    } else {
      button.disabled = false;
      button.innerHTML = button.dataset.originalContent || button.innerHTML;
      if (typeof lucide !== 'undefined') lucide.createIcons();
    }
  },

  init() {
    const yearEl = document.getElementById('year');
    if (yearEl) yearEl.textContent = new Date().getFullYear();
    if (typeof lucide !== 'undefined') lucide.createIcons();
    requestAnimationFrame(() => this.generateParticles());
  },
};

function togglePassword(inputId, button) {
  AuthUI.togglePassword(inputId, button);
}

function validateForm(form) {
  return AuthUI.validateForm(form);
}

function setButtonLoading(button, loading) {
  AuthUI.setButtonLoading(button, loading);
}

window.AuthUI = AuthUI;
window.AuthToast = { show: AuthUI.showToast.bind(AuthUI) };
window.validateForm = validateForm;
window.setButtonLoading = setButtonLoading;

document.addEventListener('DOMContentLoaded', () => AuthUI.init());
