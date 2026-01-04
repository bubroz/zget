import { ZgetBase } from './base.js';

export class ZgetIngest extends ZgetBase {
  constructor() {
    super();
    this.value = '';
    this.status = 'idle'; // idle, loading, success, error
    this.error = '';
  }

  connectedCallback() {
    this.loadStyles();
    this.render();
    this.setupListeners();
  }

  setupListeners() {
    const input = this.shadowRoot.querySelector('input');
    const form = this.shadowRoot.querySelector('.ingest-wrapper');

    input.addEventListener('input', (e) => {
      this.value = e.target.value;
      if (this.status !== 'idle') {
        this.status = 'idle';
        this.render();
      }
    });

    input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.handleSubmit();
    });

    this.shadowRoot.querySelector('.submit-btn').addEventListener('click', () => {
      this.handleSubmit();
    });
  }

  async handleSubmit() {
    if (!this.value.trim() || this.status === 'loading') return;

    this.status = 'loading';
    this.render();

    try {
      const res = await fetch('/api/downloads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: this.value.trim() })
      });

      if (!res.ok) throw new Error('Submission failed');

      const data = await res.json();
      this.status = 'success';
      this.value = '';

      // Emit event for parents to refresh if needed
      this.emit('download-started', data);

      // Auto-reset after 3s
      setTimeout(() => {
        this.status = 'idle';
        this.render();
      }, 3000);

    } catch (err) {
      this.status = 'error';
      this.error = err.message;
    }

    this.render();
  }

  render() {
    this.shadowRoot.innerHTML = `
      <link rel="stylesheet" href="/styles/theme.css">
      <link rel="stylesheet" href="/styles/shared.css">
      <style>
        :host { display: block; }
        
        .ingest-wrapper {
          display: flex;
          align-items: flex-end;
          gap: 16px;
          background: transparent !important;
          border-bottom: 2px solid var(--border) !important;
          border-top: none !important;
          border-left: none !important;
          border-right: none !important;
          border-radius: 0 !important;
          padding: 0 0 4px 4px;
          width: 100%;
          max-width: 600px;
          transition: border-color 0.3s var(--ease-out);
          position: relative;
        }

        .ingest-wrapper:focus-within {
          border-bottom-color: var(--primary) !important;
          background: transparent !important;
        }

        input {
          flex: 1;
          height: 32px;
          background: transparent !important;
          border: none !important;
          box-shadow: none !important;
          color: var(--text-main);
          font-size: 1rem;
          outline: none;
          padding: 0;
          margin: 0;
          letter-spacing: 0.01em;
        }

        .submit-btn {
          height: 28px;
          padding: 0 12px;
          border-radius: 4px;
          font-size: 0.75rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          white-space: nowrap;
          cursor: pointer;
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          gap: 6px;
          background: transparent;
          color: var(--primary);
          border: 1px solid var(--primary);
          margin-bottom: 2px;
        }

        .submit-btn:hover:not(:disabled) {
          background: var(--primary);
          color: var(--bg);
        }

        .submit-btn:hover:not(:disabled) {
          transform: scale(1.02);
          filter: brightness(1.1);
        }

        .submit-btn:disabled {
          background: var(--border);
          color: var(--text-dim);
          cursor: not-allowed;
        }

        .submit-btn.success {
          background: var(--success);
          color: white;
        }

        /* Status Indicators */
        .status-msg {
          position: absolute;
          top: 100%;
          left: 16px;
          margin-top: 8px;
          font-size: 0.75rem;
          animation: slideUp 0.3s ease;
        }
        
        .status-msg.error { color: var(--danger); }
        .status-msg.success { color: var(--success); }

        @keyframes slideUp {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
      </style>

      <div class="ingest-wrapper">
        <input type="text" 
          placeholder="Paste URL..." 
          id="urlInput"
          value="${this.value}"
          ${this.status === 'loading' ? 'disabled' : ''}>
        
        <button class="submit-btn ${this.status}" ${this.status === 'loading' ? 'disabled' : ''}>
          ${this.status === 'loading' ? 'Working...' : (this.status === 'success' ? '✓ Queued' : 'Archive')}
        </button>

        ${this.status === 'error' ? `<div class="status-msg error">Error: ${this.error}</div>` : ''}
        ${this.status === 'success' ? `<div class="status-msg success">Archival sequence initiated.</div>` : ''}
      </div>
    `;

    // Re-setup listeners since innerHTML nuked them
    this.setupListeners();
  }
}

customElements.define('zget-ingest', ZgetIngest);
