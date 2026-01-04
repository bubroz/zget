import { ZgetBase } from './base.js';

export class ZgetSettings extends ZgetBase {
  constructor() {
    super();
    this.settings = {};
    this.loading = true;
    this.saving = false;
  }

  connectedCallback() {
    this.loadStyles();
    this.fetchSettings();
  }

  async fetchSettings() {
    try {
      const res = await fetch('/api/settings');
      if (res.ok) {
        this.settings = await res.json();
      }
    } catch (e) {
      console.error('Failed to load settings:', e);
    } finally {
      this.loading = false;
      this.render();
    }
  }

  async handleSave(e) {
    e.preventDefault();
    this.saving = true;
    this.render();

    const formData = new FormData(e.target);
    const updates = Object.fromEntries(formData.entries());

    // Ensure numeric types
    if (updates.port) updates.port = parseInt(updates.port, 10);

    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });
      if (res.ok) {
        // Show a temporary success state or distinct alert
        const btn = this.shadowRoot.querySelector('.btn.primary');
        if (btn) {
          btn.textContent = 'Saved!';
          setTimeout(() => this.fetchSettings(), 1000);
        } else {
          this.fetchSettings();
        }
      }
    } catch (e) {
      alert('Failed to save settings.');
      this.saving = false;
      this.render();
    }
  }

  async triggerRepair(type) {
    if (!confirm(`Run ${type === 'library' ? 'Library Scan' : 'Thumbnail Regen'}? This may take a moment.`)) return;
    try {
      const endpoint = type === 'library' ? '/api/repair/library' : '/api/repair/thumbnails';
      await fetch(endpoint, { method: 'POST' });
      alert('Maintenance task started in background.');
    } catch (e) {
      alert('Failed to start task.');
    }
  }

  render() {
    if (this.loading) {
      this.shadowRoot.innerHTML = `
                <div style="padding: 40px; text-align: center; color: var(--text-muted);">
                    Loading preferences...
                </div>`;
      return;
    }

    this.shadowRoot.innerHTML = `
      <link rel="stylesheet" href="/styles/theme.css">
      <link rel="stylesheet" href="/styles/shared.css">
      <style>
        :host { 
            display: block; 
            width: 100%; 
            height: 100%; 
            color: var(--text-color);
        }
        
        .settings-header {
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .settings-header h2 { 
            font-size: 1.25rem; 
            font-weight: 600; 
            margin: 0; 
            color: var(--text-color);
        }

        .section {
          background: rgba(255,255,255,0.02);
          border: 1px solid var(--border-color);
          border-radius: var(--radius-lg);
          padding: 24px;
          margin-bottom: 24px;
        }

        .section-title {
          font-size: 0.9rem;
          font-weight: 600;
          color: var(--primary-color);
          margin-bottom: 16px;
          display: flex;
          align-items: center;
          gap: 8px;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .form-grid {
          display: grid;
          gap: 20px;
        }

        .field {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        label {
          font-size: 0.9rem;
          font-weight: 500;
          color: var(--text-color);
        }

        .help-text {
            font-size: 0.8rem;
            color: var(--text-muted);
            line-height: 1.4;
        }

        .input-group input {
            background: rgba(0,0,0,0.3);
            font-family: var(--font-mono);
            font-size: 0.85rem;
        }

        .maintenance-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
        }

        .action-card {
          padding: 16px;
          border: 1px solid var(--border-color);
          border-radius: var(--radius-md);
          display: flex;
          flex-direction: column;
          gap: 12px;
          background: rgba(255,255,255,0.02);
          transition: border-color 0.2s;
        }

        .action-card:hover {
            border-color: var(--text-muted);
        }

        .action-card h4 { margin: 0; font-size: 0.95rem; font-weight: 600; }
        .action-card p { font-size: 0.8rem; color: var(--text-muted); margin: 0; line-height: 1.4; flex: 1; }
        
        .save-bar {
          display: flex;
          justify-content: flex-end;
          padding-top: 12px;
          border-top: 1px solid var(--border-color);
          margin-top: 8px;
        }
        
        .badge-ip {
            display: inline-block;
            background: rgba(34, 197, 94, 0.1);
            color: var(--primary-color);
            padding: 2px 8px;
            border-radius: 4px;
            font-family: var(--font-mono);
            font-size: 0.8rem;
            margin-right: 8px;
        }

        /* Mobile Responsive */
        @media (max-width: 768px) {
          .form-grid[style*="grid-template-columns: 2fr 1fr"] {
            grid-template-columns: 1fr !important;
          }

          .maintenance-grid {
            grid-template-columns: 1fr;
          }

          .save-bar {
            justify-content: stretch;
          }

          .save-bar .btn {
            width: 100%;
          }
        }
      </style>

      <div class="settings-header">
        <h2>App Preferences</h2>
      </div>

      <form onsubmit="this.getRootNode().host.handleSave(event)">
        <div class="section">
          <div class="section-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
            Library & Storage
          </div>
          
          <div class="form-grid">
            <div class="field">
              <label>zget Home Directory</label>
              <div class="help-text">Where your downloads and database live. Default is <code>~/.zget</code></div>
              <div class="input-group">
                <input type="text" name="zget_home" value="${this.settings.zget_home || ''}" placeholder="/Users/name/zget">
              </div>
            </div>
          </div>
        </div>

        <div class="section">
          <div class="section-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2"/><line x1="6" y1="6" x2="6" y2="6"/><line x1="6" y1="18" x2="6" y2="18"/></svg>
            Network Architecture
          </div>
          
          <div class="form-grid" style="grid-template-columns: 2fr 1fr; gap: 32px;">
            <div class="field">
              <label>Server Bind Address</label>
              <div class="help-text">Use <code>0.0.0.0</code> to be visible on your network.</div>
              <div class="input-group">
                <input type="text" name="host" value="${this.settings.host || '127.0.0.1'}" placeholder="127.0.0.1">
              </div>
            </div>

            <div class="field">
              <label>Port</label>
              <div class="help-text">Default is <code>8000</code></div>
              <div class="input-group">
                <input type="text" name="port" value="${this.settings.port || '8000'}" placeholder="8000">
              </div>
            </div>
          </div>

          <div style="margin-top: 24px; padding: 16px; background: rgba(var(--primary-hsl), 0.03); border: 1px solid rgba(var(--primary-hsl), 0.1); border-radius: 8px; display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div class="badge-ip" style="background: var(--primary-color); color: var(--bg-color); font-weight: 700;">
                    ${this.settings.local_ip?.startsWith('100.') ? 'VPN / TAILSCALE' : 'LOCAL ACCESS'}
                </div>
                <div style="font-size: 0.9rem; font-family: var(--font-mono); color: var(--text-color);">
                  <span style="opacity: 0.5;">http://</span>${this.settings.local_ip || '...'}<span style="color: var(--primary-color); font-weight: 700;">:${this.settings.port || '8000'}</span>
                </div>
            </div>
            <div style="font-size: 0.75rem; color: var(--text-muted); font-style: italic;">Requires server restart to apply</div>
          </div>
        </div>

        <div class="save-bar">
          <button class="btn primary" type="submit" ${this.saving ? 'disabled' : ''}>
            ${this.saving ? 'Updating System...' : 'Commit Changes'}
          </button>
        </div>
      </form>

      <div class="section" style="margin-top: 40px; background: transparent; border-color: rgba(255,255,255,0.05);">
        <div class="section-title" style="color: var(--text-muted);">Maintenance</div>
        <div class="maintenance-grid">
          <div class="action-card">
            <h4>Sync Library</h4>
            <p>Scan disk for manual additions or deletions.</p>
            <button class="btn" style="width: 100%;" onclick="this.getRootNode().host.triggerRepair('library')">Run Scan</button>
          </div>
          <div class="action-card">
            <h4>Fix Thumbnails</h4>
            <p>Heal missing or broken cover images.</p>
            <button class="btn" style="width: 100%;" onclick="this.getRootNode().host.triggerRepair('thumbnails')">Regenerate</button>
          </div>
        </div>
      </div>
      
      <div style="text-align: center; margin-top: 24px; opacity: 0.3; font-size: 0.7rem; font-family: var(--font-mono);">
        zget ${this.settings.version || '0.4.0'} 
      </div>
    `;
  }
}

customElements.define('zget-settings', ZgetSettings);
