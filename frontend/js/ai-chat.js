const AIChat = {
  open: false,
  loading: false,
  enabled: false,
  companyId: null,
  messages: [],

  SUGGESTIONS: [
    'Summarize our compliance gaps',
    'Explain our risk score',
    'How is our financial health?',
  ],

  init() {
    if (!Auth.isLoggedIn()) return;

    this.fab = document.getElementById('ai-chat-fab');
    this.panel = document.getElementById('ai-chat-panel');
    this.messagesEl = document.getElementById('ai-chat-messages');
    this.input = document.getElementById('ai-chat-input');
    this.sendBtn = document.getElementById('ai-chat-send');
    this.closeBtn = document.getElementById('ai-chat-close');

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

  async checkStatus() {
    try {
      const status = await API.get('/chat/status');
      this.enabled = status.enabled;
      if (!status.enabled) {
        this.renderWelcome(
          'AI assistant requires OPENAI_API_KEY on the server. You can still browse analytics manually.',
        );
      }
    } catch (_) {
      this.enabled = false;
    }
  },

  toggle() {
    if (this.open) this.close();
    else this.openPanel();
  },

  openPanel() {
    this.open = true;
    this.panel.classList.remove('hidden', 'ai-chat-closing');
    this.fab.classList.add('ai-chat-open');
    this.fab.querySelector('[data-lucide]')?.setAttribute('data-lucide', 'chevron-down');
    document.getElementById('ai-chat-fab-pulse')?.classList.add('hidden');
    Layout.refreshIcons(this.fab);
    setTimeout(() => this.input?.focus(), 200);
  },

  close() {
    this.open = false;
    this.panel.classList.add('ai-chat-closing');
    this.fab.classList.remove('ai-chat-open');
    this.fab.querySelector('[data-lucide]')?.setAttribute('data-lucide', 'message-circle');
    Layout.refreshIcons(this.fab);
    setTimeout(() => {
      this.panel.classList.add('hidden');
      this.panel.classList.remove('ai-chat-closing');
      if (this.enabled) {
        document.getElementById('ai-chat-fab-pulse')?.classList.remove('hidden');
      }
    }, 180);
  },

  renderWelcome(note) {
    const suggestions = this.SUGGESTIONS.map(
      (s) => `<button type="button" class="ai-chat-suggestion" data-prompt="${this._esc(s)}">${this._esc(s)}</button>`,
    ).join('');

    this.messagesEl.innerHTML = `
      <div class="ai-chat-bubble ai-chat-bubble-system">
        <p class="mb-2">Hi! I can help with financial scores, governance, risk, and King IV / JSE compliance.</p>
        ${note ? `<p class="text-amber-400/90 mb-2">${this._esc(note)}</p>` : ''}
        <div class="text-left mt-3">${suggestions}</div>
      </div>`;

    this.messagesEl.querySelectorAll('.ai-chat-suggestion').forEach((btn) => {
      btn.addEventListener('click', () => {
        this.input.value = btn.dataset.prompt || '';
        this.send();
      });
    });
  },

  appendMessage(role, content) {
    if (this.messagesEl.querySelector('.ai-chat-bubble-system')) {
      this.messagesEl.innerHTML = '';
    }
    const div = document.createElement('div');
    div.className = `ai-chat-bubble ai-chat-bubble-${role === 'user' ? 'user' : 'assistant'}`;
    div.textContent = content;
    this.messagesEl.appendChild(div);
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  },

  showTyping() {
    const el = document.createElement('div');
    el.id = 'ai-chat-typing';
    el.className = 'ai-chat-bubble ai-chat-bubble-assistant ai-chat-typing';
    el.innerHTML = '<span></span><span></span><span></span>';
    this.messagesEl.appendChild(el);
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  },

  hideTyping() {
    document.getElementById('ai-chat-typing')?.remove();
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
