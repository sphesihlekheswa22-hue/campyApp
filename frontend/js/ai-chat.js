const AIChat = {
  open: false,
  loading: false,
  enabled: false,
  companyId: null,
  messages: [],

  SUGGESTIONS: [
    { text: 'Summarize our compliance gaps', icon: 'clipboard-check' },
    { text: 'Explain our risk score', icon: 'shield-alert' },
    { text: 'How is our financial health?', icon: 'trending-up' },
  ],

  init() {
    if (!Auth.isLoggedIn()) return;

    this.root = document.getElementById('ai-chat-root');
    this.fabWrap = document.getElementById('ai-chat-fab-wrap');
    this.fab = document.getElementById('ai-chat-fab');
    this.panelWrap = document.getElementById('ai-chat-panel-wrap');
    this.panel = document.getElementById('ai-chat-panel');
    this.messagesEl = document.getElementById('ai-chat-messages');
    this.input = document.getElementById('ai-chat-input');
    this.sendBtn = document.getElementById('ai-chat-send');
    this.closeBtn = document.getElementById('ai-chat-close');
    this.statusDot = document.getElementById('ai-chat-status-dot');
    this.statusText = document.getElementById('ai-chat-status-text');

    if (!this.fab) return;

    this.fab.addEventListener('click', () => this.toggle());
    this.closeBtn?.addEventListener('click', () => this.close());
    this.sendBtn?.addEventListener('click', () => this.send());
    this.input?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.send();
      }
    });

    this.resolveCompanyId().then(() => this.checkStatus());
    this.renderWelcome();
  },

  async resolveCompanyId() {
    const fromUrl = Utils.getParam('id');
    if (fromUrl) {
      this.companyId = parseInt(fromUrl, 10);
      return;
    }
    const stored = sessionStorage.getItem('company_id');
    if (stored) {
      this.companyId = parseInt(stored, 10);
      return;
    }
    try {
      const user = await API.get('/users/me');
      if (user.company_id) {
        this.companyId = user.company_id;
        sessionStorage.setItem('company_id', user.company_id);
      }
    } catch (_) {}
  },

  setStatus(online, label) {
    if (this.statusDot) {
      this.statusDot.classList.toggle('offline', !online);
    }
    if (this.statusText) {
      this.statusText.textContent = label;
    }
  },

  async checkStatus() {
    try {
      const status = await API.get('/chat/status');
      this.enabled = status.enabled;
      if (status.enabled) {
        this.setStatus(true, 'Ready · Powered by AI');
      } else {
        this.setStatus(false, 'Offline · Configure API key');
        this.renderWelcome(
          'AI requires OPENAI_API_KEY on the server. Analytics and compliance pages still work normally.',
        );
      }
    } catch (_) {
      this.enabled = false;
      this.setStatus(false, 'Unavailable');
    }
  },

  toggle() {
    if (this.open) this.close();
    else this.openPanel();
  },

  openPanel() {
    this.open = true;
    this.panelWrap?.classList.remove('hidden');
    this.panel?.classList.remove('ai-chat-closing');
    this.fab.classList.add('ai-chat-open');
    this.fabWrap?.classList.add('ai-chat-open');
    const icon = this.fab.querySelector('[data-lucide]');
    if (icon) icon.setAttribute('data-lucide', 'chevron-down');
    Layout.refreshIcons(this.fabWrap || this.fab);
    setTimeout(() => this.input?.focus(), 220);
  },

  close() {
    this.open = false;
    this.panel?.classList.add('ai-chat-closing');
    this.fab.classList.remove('ai-chat-open');
    this.fabWrap?.classList.remove('ai-chat-open');
    const icon = this.fab.querySelector('[data-lucide]');
    if (icon) icon.setAttribute('data-lucide', 'sparkles');
    Layout.refreshIcons(this.fabWrap || this.fab);
    setTimeout(() => {
      this.panelWrap?.classList.add('hidden');
      this.panel?.classList.remove('ai-chat-closing');
    }, 200);
  },

  userInitials() {
    const name = document.getElementById('user-name')?.textContent?.trim();
    if (!name || name === 'User Name') return 'U';
    const parts = name.split(/\s+/);
    return parts.length >= 2
      ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
      : name.slice(0, 2).toUpperCase();
  },

  renderWelcome(note) {
    const suggestions = this.SUGGESTIONS.map(
      (s) => `
        <button type="button" class="ai-chat-suggestion" data-prompt="${this._esc(s.text)}">
          <span class="ai-chat-suggestion-icon"><i data-lucide="${s.icon}" class="w-3.5 h-3.5"></i></span>
          <span>${this._esc(s.text)}</span>
        </button>`,
    ).join('');

    this.messagesEl.innerHTML = `
      <div class="ai-chat-welcome">
        <div class="ai-chat-welcome-icon">
          <i data-lucide="sparkles" class="w-7 h-7 text-blue-400"></i>
        </div>
        <h4>How can I help you today?</h4>
        <p>Ask about financial health, governance scores, risk levels, or King IV &amp; JSE compliance.</p>
        ${note ? `<div class="ai-chat-welcome-note">${this._esc(note)}</div>` : ''}
        <p class="ai-chat-suggestions-label">Suggested questions</p>
        ${suggestions}
      </div>`;

    Layout.refreshIcons(this.messagesEl);
    this.messagesEl.querySelectorAll('.ai-chat-suggestion').forEach((btn) => {
      btn.addEventListener('click', () => {
        this.input.value = btn.dataset.prompt || '';
        this.send();
      });
    });
  },

  appendMessage(role, content) {
    if (this.messagesEl.querySelector('.ai-chat-welcome')) {
      this.messagesEl.innerHTML = '';
    }

    const row = document.createElement('div');
    row.className = `ai-chat-row ${role === 'user' ? 'ai-chat-row-user' : ''}`;

    const avatar = document.createElement('div');
    if (role === 'user') {
      avatar.className = 'ai-chat-msg-avatar ai-chat-msg-avatar-user';
      avatar.textContent = this.userInitials();
    } else {
      avatar.className = 'ai-chat-msg-avatar ai-chat-msg-avatar-ai';
      avatar.innerHTML = '<i data-lucide="sparkles" class="w-3.5 h-3.5"></i>';
    }

    const bubble = document.createElement('div');
    bubble.className = `ai-chat-bubble ai-chat-bubble-${role === 'user' ? 'user' : 'assistant'}`;
    bubble.textContent = content;

    row.appendChild(avatar);
    row.appendChild(bubble);
    this.messagesEl.appendChild(row);
    Layout.refreshIcons(row);
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  },

  showTyping() {
    const row = document.createElement('div');
    row.id = 'ai-chat-typing-row';
    row.className = 'ai-chat-row';
    row.innerHTML = `
      <div class="ai-chat-msg-avatar ai-chat-msg-avatar-ai">
        <i data-lucide="sparkles" class="w-3.5 h-3.5"></i>
      </div>
      <div class="ai-chat-bubble ai-chat-bubble-assistant ai-chat-typing">
        <span></span><span></span><span></span>
      </div>`;
    this.messagesEl.appendChild(row);
    Layout.refreshIcons(row);
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  },

  hideTyping() {
    document.getElementById('ai-chat-typing-row')?.remove();
  },

  async send() {
    const text = (this.input?.value || '').trim();
    if (!text || this.loading) return;

    this.input.value = '';
    this.appendMessage('user', text);
    this.messages.push({ role: 'user', content: text });
    this.loading = true;
    this.sendBtn.disabled = true;
    this.showTyping();

    try {
      const payload = {
        message: text,
        history: this.messages.slice(-8),
      };
      if (this.companyId) payload.company_id = this.companyId;

      const res = await API.post('/chat/', payload);
      this.hideTyping();
      this.appendMessage('assistant', res.reply);
      this.messages.push({ role: 'assistant', content: res.reply });
    } catch (err) {
      this.hideTyping();
      this.appendMessage('assistant', err.message || 'Something went wrong. Please try again.');
    } finally {
      this.loading = false;
      this.sendBtn.disabled = false;
      this.input?.focus();
    }
  },

  _esc(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  },
};

document.addEventListener('DOMContentLoaded', () => {
  if (typeof Auth !== 'undefined' && Auth.isLoggedIn()) {
    AIChat.init();
  }
});

window.AIChat = AIChat;
