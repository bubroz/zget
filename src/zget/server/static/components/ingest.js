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
          align-items: center;
          gap: 12px;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid var(--border-color);
          border-radius: 4px;
          padding: 6px 12px;
          width: 100%;
          max-width: 100%;
          position: relative;
          transition: all 0.2s ease;
        }

        .ingest-wrapper:focus-within {
          background: rgba(255, 255, 255, 0.05);
          border-color: var(--primary-color);
          box-shadow: 0 0 15px hsla(var(--primary-hsl), 0.1);
        }

        input {
          flex: 1;
          background: transparent !important;
          border: none !important;
          color: var(--text-color);
          font-size: 0.8rem;
          font-family: var(--font-mono);
          outline: none;
          padding: 0;
          margin: 0;
          letter-spacing: 0.05em;
        }

        .submit-btn {
          height: 28px;
          padding: 0 16px;
          border-radius: 4px;
          font-size: 0.75rem;
          font-weight: 700;
          font-family: var(--font-mono);
          text-transform: uppercase;
          letter-spacing: 0.1em;
          white-space: nowrap;
          cursor: pointer;
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          gap: 6px;
          background: transparent;
          color: var(--primary-color);
          border: 1px solid var(--primary-color);
        }

        .submit-btn:hover:not(:disabled) {
          background: var(--primary-color);
          color: black;
          transform: translateY(-1px);
        }

        .submit-btn:disabled {
          opacity: 0.5;
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

        @media (max-width: 768px) {
          .ingest-wrapper {
            padding: 4px 10px;
            gap: 8px;
          }
          input {
            font-size: 0.75rem;
          }
          .submit-btn {
            padding: 0 12px;
            font-size: 0.7rem;
            height: 26px;
          }
        }
      </style>

      <div class="ingest-wrapper">
        <input type="text" 
          placeholder="PASTE URL // ARCHIVE" 
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
