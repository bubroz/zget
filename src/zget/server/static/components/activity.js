import { ZgetBase } from './base.js';

export class ZgetActivity extends ZgetBase {
  constructor() {
    super();
    this.downloads = [];
    this.timer = null;
    this.deletedIds = new Set(); // Track IDs we've deleted to prevent re-appearance during polling
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
        let newData = await res.json();

        // Filter out any items we've locally deleted (race condition prevention)
        const serverIds = new Set(newData.map(d => d.id));
        // Clean up deletedIds for items the server has confirmed removed
        for (const id of this.deletedIds) {
          if (!serverIds.has(id)) {
            this.deletedIds.delete(id);
          }
        }
        // Don't show items we've deleted locally
        newData = newData.filter(d => !this.deletedIds.has(d.id));

        // Detect completions or removals to trigger vault refresh
        // We look for:
        // 1. Items that transitioned to 'complete' status
        // 2. Items that were in our list but are now gone (backend pruned them)
        const oldIds = new Set(this.downloads.map(d => d.id));
        const newIds = new Set(newData.map(d => d.id));

        const justCompleted = this.downloads.filter(d =>
          d.status !== 'complete' &&
          newData.find(n => n.id === d.id && n.status === 'complete')
        );

        const prunedOut = this.downloads.filter(d =>
          !newIds.has(d.id) && d.status !== 'complete'
        );

        if (justCompleted.length > 0 || prunedOut.length > 0) {
          this.dispatchEvent(new CustomEvent('archive-complete', {
            bubbles: true,
            composed: true,
            detail: { count: justCompleted.length + prunedOut.length }
          }));
        }

        this.downloads = newData;
        this.render();
      }
    } catch (e) {
      console.error('Activity poll failed:', e);
    }
  }

  async cancelDownload(itemId) {
    try {
      // Track this ID as deleted to prevent race condition with polling
      this.deletedIds.add(itemId);

      // Remove from local state immediately for responsive UI
      this.downloads = this.downloads.filter(d => d.id !== itemId);
      this.render();

      // Tell the server to cancel/remove
      await fetch(`/api/downloads/${itemId}`, { method: 'DELETE' });
    } catch (e) {
      console.error('Failed to cancel download:', e);
      // On error, remove from deletedIds so it can reappear
      this.deletedIds.delete(itemId);
    }
  }

  formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    if (!bytes || isNaN(bytes)) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  formatError(error) {
    if (!error) return '';
    // Extract the core error message (after "ERROR:" prefix)
    const coreMsg = error.replace(/^.*?ERROR:\s*/i, '').trim();
    // For display, get just the first line/sentence
    const firstLine = coreMsg.split(/[.\n]/)[0].trim();
    return { full: coreMsg, summary: firstLine || coreMsg.substring(0, 100) };
  }

  toggleErrorExpand(itemId) {
    const el = this.shadowRoot.querySelector(`[data-error-id="${itemId}"]`);
    if (el) {
      el.classList.toggle('expanded');
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
            background: rgba(34, 197, 94, 0.05);
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

        .progress-fill.failed {
            background: var(--status-error);
            box-shadow: 0 0 10px rgba(239, 68, 68, 0.5);
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

        .error-container {
            font-size: 0.75rem;
            color: var(--status-error);
            opacity: 0.9;
            margin-top: 4px;
            cursor: pointer;
            user-select: text;
        }

        .error-summary {
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .error-summary::before {
            content: '▶';
            font-size: 0.6rem;
            transition: transform 0.2s;
        }

        .error-container.expanded .error-summary::before {
            transform: rotate(90deg);
        }

        .error-full {
            display: none;
            margin-top: 6px;
            padding: 8px;
            background: rgba(239, 68, 68, 0.1);
            border-radius: 4px;
            font-family: var(--font-mono);
            font-size: 0.7rem;
            line-height: 1.4;
            white-space: pre-wrap;
            word-break: break-word;
            max-height: 200px;
            overflow-y: auto;
        }

        .error-container.expanded .error-full {
            display: block;
        }
      </style>

      <div class="activity-banner">
        <div class="banner-header">
            <span>Archival Progress</span>
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
                    <span class="item-title" title="${item.title || item.url}">${item.title || 'Resolving Stream...'}</span>
                    <span class="item-stats">
                        ${item.status === 'complete' ? 'COMPLETE' : (item.status === 'failed' ? 'FAILED' : (item.progress ? Math.round(item.progress) + '%' : '0%'))} 
                        ${item.speed ? '• ' + this.formatBytes(item.speed) + '/s' : ''} 
                        ${item.eta ? '• ' + Math.round(item.eta) + 's left' : ''}
                    </span>
                </div>
                ${(() => {
        if (item.status === 'failed' && item.error) {
          const err = this.formatError(item.error);
          return `
                    <div class="error-container" data-error-id="${item.id}" onclick="this.getRootNode().host.toggleErrorExpand('${item.id}')">
                      <div class="error-summary">${err.summary}</div>
                      <div class="error-full">${err.full}</div>
                    </div>`;
        }
        return '';
      })()}
                
                <div class="progress-track">
                    <div class="progress-fill ${item.status === 'failed' ? 'failed' : ''}" 
                         style="width: ${item.status === 'complete' ? 100 : (item.progress || 0)}%"></div>
                </div>
              </div>

              ${item.status !== 'complete' ? `
              <button class="cancel-btn" onclick="this.getRootNode().host.cancelDownload('${item.id}')" title="Stop">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
              ` : ''}
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }
}

customElements.define('zget-activity', ZgetActivity);
