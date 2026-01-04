import { ZgetBase } from './base.js';

export class ZgetVault extends ZgetBase {
    constructor() {
        super();
        this.videos = [];
        this.loading = true;
        this.searchQuery = '';
    }

    connectedCallback() {
        this.loadStyles();
        this.renderTemplate();
        this.fetchVideos();
    }

    async fetchVideos() {
        this.loading = true;
        this.updateList();

        try {
            const url = this.searchQuery
                ? `/api/library?q=${encodeURIComponent(this.searchQuery)}`
                : '/api/library?limit=100';

            const res = await fetch(url);
            this.videos = await res.json();
        } catch (err) {
            console.error('Failed to fetch videos:', err);
        } finally {
            this.loading = false;
            this.updateList();
        }
    }

    handleSearch(e) {
        if (e.key === 'Enter') {
            this.searchQuery = e.target.value;
            this.fetchVideos();
        }
    }

    renderTemplate() {
        this.shadowRoot.innerHTML = `
      <link rel="stylesheet" href="/styles/theme.css">
      <link rel="stylesheet" href="/styles/shared.css">
      <style>
        :host { display: block; padding: 20px; }
        
        .vault-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 24px;
        }

        .header-title h2 { margin: 0; font-size: 1.5rem; color: var(--text-main); }
        .header-title p { margin: 4px 0 0; color: var(--text-dim); font-size: 0.9rem; }

        .video-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: 20px;
        }

        .video-card {
          background: rgba(255, 255, 255, 0.02);
          border: 1px solid var(--border);
          border-radius: var(--radius-md);
          overflow: hidden;
          transition: transform 0.2s, box-shadow 0.2s;
          cursor: pointer;
        }

        .video-card:hover {
          transform: translateY(-4px);
          border-color: var(--primary);
          box-shadow: 0 10px 20px rgba(0,0,0,0.3);
        }

        .thumbnail-container {
          position: relative;
          aspect-ratio: 16/9;
          background: #000;
        }
        
        .thumbnail-container img {
          width: 100%;
          height: 100%;
          object-fit: contain; /* Keep original aspect ratio */
          background: #000; /* Letterbox fill */
        }

        .duration-badge {
          position: absolute;
          bottom: 8px;
          right: 8px;
          background: rgba(0, 0, 0, 0.8);
          color: white;
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 0.75rem;
          font-weight: 600;
        }

        .card-info { padding: 12px; }
        .card-title {
          font-weight: 600;
          font-size: 0.95rem;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          margin-bottom: 4px;
        }
        .card-meta {
          color: var(--text-dim);
          font-size: 0.8rem;
          display: flex;
          justify-content: space-between;
        }

        .empty-state {
          text-align: center;
          padding: 40px;
          color: var(--text-dim);
          grid-column: 1 / -1;
        }
      </style>

      <div class="vault-header">
        <div class="header-title">
          <h2>The Vault</h2>
          <p>Secure Archive</p>
        </div>
        <div class="input-group" style="width: 250px;">
          <span>🔍</span>
          <input type="text" placeholder="Search archives..." id="searchInput">
        </div>
      </div>

      <div class="video-grid" id="grid">
        <!-- Videos injected here -->
      </div>
    `;

        this.shadowRoot.getElementById('searchInput').addEventListener('keypress', (e) => this.handleSearch(e));
    }

    updateList() {
        const grid = this.shadowRoot.getElementById('grid');
        if (!grid) return;

        if (this.loading) {
            grid.innerHTML = '<div class="empty-state">Loading The Vault...</div>';
            return;
        }

        if (this.videos.length === 0) {
            grid.innerHTML = '<div class="empty-state">No artifacts found in the archives.</div>';
            return;
        }

        grid.innerHTML = this.videos.map(v => `
      <div class="video-card" onclick="this.getRootNode().host.emit('open-video', {id: ${v.id}})">
        <div class="thumbnail-container">
          <img src="/api/thumbnails/${v.id}" loading="lazy" alt="${v.title}">
          <div class="duration-badge">${this.formatDuration(v.duration_seconds)}</div>
        </div>
        <div class="card-info">
          <div class="card-title">${v.title}</div>
          <div class="card-meta">
            <span>${v.uploader}</span>
            <span>${v.platform_display}</span>
          </div>
        </div>
      </div>
    `).join('');
    }

    formatDuration(seconds) {
        if (!seconds) return '0:00';
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return `${m}:${s.toString().padStart(2, '0')}`;
    }
}

customElements.define('zget-vault', ZgetVault);
