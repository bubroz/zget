import { ZgetBase } from './base.js';

export class ZgetActivity extends ZgetBase {
  constructor() {
    super();
    this.downloads = [];
    this.timer = null;
  }

  connectedCallback() {
    this.loadStyles();
    this.render();
    this.startPolling();
  }

  disconnectedCallback() {
    if (this.timer) clearInterval(this.timer);
  }

  startPolling() {
    this.fetchActivity();
    this.timer = setInterval(() => this.fetchActivity(), 2000);
  }

  async fetchActivity() {
    try {
      const res = await fetch('/api/downloads');
      if (res.ok) {
        this.downloads = await res.json();
        this.render();
      }
    } catch (e) {
      console.error('Activity poll failed:', e);
    }
  }

  async cancelDownload(id) {
    if (!confirm('Cancel this archival sequence?')) return;
    try {
      await fetch(`/api/downloads/${id}`, { method: 'DELETE' });
      this.fetchActivity();
    } catch (e) {
      console.error('Cancel failed:', e);
    }
  }

  render() {
    if (this.downloads.length === 0) {
      this.style.display = 'none';
      return;
    }
    this.style.display = 'block';

    this.shadowRoot.innerHTML = `
      <link rel="stylesheet" href="/styles/theme.css">
      <link rel="stylesheet" href="/styles/shared.css">
      <style>
        :host { 
            display: block; 
            margin: var(--spacing-sm) var(--spacing-lg);
        }

        .activity-banner {
            background: rgba(34, 197, 94, 0.05); /* Very subtle green tint */
            border: 1px solid rgba(34, 197, 94, 0.2);
            border-radius: var(--radius-md);
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            backdrop-filter: blur(10px);
        }

        .banner-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.8rem;
            color: var(--primary-color);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .items-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .download-item {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        
        .item-details {
            flex: 1;
            min-width: 0;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .item-main-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .item-title {
            font-weight: 500;
            font-size: 0.9rem;
            color: var(--text-color);
            text-overflow: ellipsis;
            white-space: nowrap;
            overflow: hidden;
        }

        .item-stats {
            font-family: var(--font-mono);
            font-size: 0.75rem;
            color: var(--text-muted);
        }

        .progress-track {
            height: 4px;
            background: rgba(255,255,255,0.05);
            border-radius: 2px;
            overflow: hidden;
            width: 100%;
        }

        .progress-fill {
            height: 100%;
            background: var(--primary-color);
            transition: width 0.3s ease;
            box-shadow: 0 0 10px rgba(34, 197, 94, 0.5);
        }

        .cancel-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            padding: 6px;
            border-radius: 50%;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .cancel-btn:hover {
            color: var(--status-error);
            background: rgba(255, 255, 255, 0.05);
        }
      </style>

      <div class="activity-banner">
        <div class="banner-header">
            <span>Resolving Stream...</span>
            <div style="display: flex; align-items: center; gap: 6px;">
                 <span style="width: 6px; height: 6px; background: var(--primary-color); border-radius: 50%; box-shadow: 0 0 8px var(--primary-color);"></span>
                 <span style="font-size: 0.75rem; opacity: 0.8;">Active</span>
            </div>
        </div>
        
        <div class="items-list">
          ${this.downloads.map(item => `
            <div class="download-item">
              <div class="item-details">
                <div class="item-main-row">
                    <span class="item-title" title="${item.title || item.url}">${item.title || 'Processing...'}</span>
                    <span class="item-stats">
                        ${item.percent ? item.percent.toFixed(1) + '%' : '0%'} 
                        ${item.speed ? '• ' + item.speed : ''} 
                        ${item.eta ? '• ' + item.eta : ''}
                    </span>
                </div>
                
                <div class="progress-track">
                    <div class="progress-fill" style="width: ${item.percent || 0}%"></div>
                </div>
              </div>

              <button class="cancel-btn" onclick="this.getRootNode().host.cancelDownload('${item.id}')" title="Stop">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }
}

customElements.define('zget-activity', ZgetActivity);
