/** Light / dark theme controller — default remains dark. */
const Theme = {
  STORAGE_KEY: 'theme',

  current() {
    return document.documentElement.classList.contains('light') ? 'light' : 'dark';
  },

  apply(mode, { silent } = {}) {
    const next = mode === 'light' ? 'light' : 'dark';
    document.documentElement.classList.remove('dark', 'light');
    document.documentElement.classList.add(next);
    try {
      localStorage.setItem(this.STORAGE_KEY, next);
    } catch (_) { /* ignore */ }
    this.syncControls();
    if (!silent) {
      if (typeof Layout !== 'undefined' && Layout.showToast) {
        Layout.showToast(next === 'light' ? 'Light mode on' : 'Dark mode on', 'success');
      } else if (typeof AuthUI !== 'undefined' && AuthUI.showToast) {
        AuthUI.showToast(next === 'light' ? 'Light mode on' : 'Dark mode on', 'success');
      }
    }
  },

  toggle() {
    this.apply(this.current() === 'light' ? 'dark' : 'light');
  },

  syncControls() {
    const mode = this.current();
    const isLight = mode === 'light';
    document.querySelectorAll('[data-theme-toggle]').forEach((btn) => {
      const icon = btn.querySelector('[data-theme-icon]');
      const label = btn.querySelector('[data-theme-label]');
      if (icon) {
        icon.setAttribute('data-lucide', isLight ? 'moon' : 'sun');
      }
      if (label) {
        label.textContent = isLight ? 'Dark' : 'Light';
      }
      btn.setAttribute('aria-label', isLight ? 'Switch to dark mode' : 'Switch to light mode');
      btn.setAttribute('title', isLight ? 'Switch to dark mode' : 'Switch to light mode');
      btn.setAttribute('aria-pressed', isLight ? 'true' : 'false');
    });
    if (typeof Layout !== 'undefined') {
      Layout.refreshIcons(document.body);
    } else if (typeof lucide !== 'undefined') {
      lucide.createIcons();
    }
  },

  init() {
    const saved = (() => {
      try {
        return localStorage.getItem(this.STORAGE_KEY);
      } catch (_) {
        return null;
      }
    })();
    this.apply(saved === 'light' ? 'light' : 'dark', { silent: true });
    document.querySelectorAll('[data-theme-toggle]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        this.toggle();
      });
    });
  },
};

window.Theme = Theme;
