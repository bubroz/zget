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

  openVideo(e, videoData) {
    // Dispatches event with full video object
    const event = new CustomEvent('open-video', {
      detail: videoData,
      bubbles: true,
      composed: true
    });
    this.dispatchEvent(event);
  }

  renderTemplate() {
    this.shadowRoot.innerHTML = `
      <link rel="stylesheet" href="/styles/theme.css">
      <link rel="stylesheet" href="/styles/shared.css">
      <style>
        :host { display: block; padding: 0 20px 40px 20px; }
        
        .vault-header {
          margin-bottom: 40px;
          display: flex;
          justify-content: space-between;
          align-items: flex-end;
        }

        .header-title h2 { 
          margin: 0; 
          font-size: 1.8rem; 
          font-weight: 700; 
          color: white; 
        }

        .header-title .subtitle {
            color: var(--text-muted);
            font-size: 0.85rem;
            margin-top: 4px;
        }

        .video-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: 32px;
        }

        /* Restoration Card Style */
        .video-card {
          background: #06090F;
          border: 1px solid transparent;
          border-radius: 12px;
          overflow: hidden;
          transition: all 0.2s ease;
          cursor: pointer;
        }

        .video-card:hover {
          border-color: var(--border-color);
          background: #0B0E14;
        }

        .thumbnail-container {
          position: relative;
          aspect-ratio: 16/9;
          background: #000;
          border: none;
          outline: none;
          /* No border here to avoid double-border look */
        }
        
        .thumbnail-container img {
          width: 100%;
          height: 100%;
          object-fit: cover;
          opacity: 1;
          display: block;
        }

        .duration-badge {
          position: absolute;
          bottom: 8px;
          right: 8px;
          background: rgba(0, 0, 0, 0.7);
          backdrop-filter: blur(4px);
          color: white;
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 0.7rem;
          font-weight: 600;
          font-family: var(--font-mono);
          letter-spacing: 0.05em;
        }
        
        .platform-badge {
            position: absolute;
            top: 8px;
            right: 8px;
            background: #7c3aed; /* Violet for tags */
            color: white;
            font-size: 0.65rem;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }

        .card-info { 
            padding: 16px; 
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .card-title {
          font-weight: 600;
          font-size: 0.95rem;
          color: var(--text-color);
          line-height: 1.4;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
        
        .card-meta-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-top: 4px;
        }
        
        .uploader-name {
            color: var(--text-muted);
            font-size: 0.8rem;
        }
        
        .status-badge {
            font-size: 0.65rem;
            font-weight: 700;
            color: var(--primary-color);
            background: rgba(16, 185, 129, 0.1); /* Green tint */
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid rgba(16, 185, 129, 0.2);
            text-transform: uppercase;
        }

        .empty-state {
          text-align: center;
          padding: 60px;
          color: var(--text-muted);
          grid-column: 1 / -1;
          background: var(--bg-card);
          border-radius: var(--radius-lg);
          border: 1px dashed var(--border-color);
        }

        /* Mobile Responsive */
        @media (max-width: 768px) {
          :host {
            padding: 0 0 40px 0;
          }

          .vault-header {
            flex-direction: row;
            align-items: center;
            gap: 12px;
            margin-bottom: 24px;
            padding: 0 16px;
          }

          .header-title {
            display: none;
          }

          .vault-header .input-group {
            flex: 1;
            width: auto !important;
          }

          .video-grid {
            grid-template-columns: 1fr;
            gap: 16px;
            padding: 0;
            background: rgba(255,255,255,0.02);
          }

          .video-card {
            border-radius: 0;
            border-left: none;
            border-right: none;
            border-top: none;
            background: transparent;
          }

          .video-card:hover {
            background: transparent;
          }

          .thumbnail-container {
            border-radius: 0;
            aspect-ratio: auto;
            min-height: 200px;
          }

          .thumbnail-container img {
            height: auto;
            max-height: 70vh;
            object-fit: contain;
            background: #000;
          }

          .card-info {
            padding: 16px;
            background: #0B0E14;
          }

          .card-title {
            font-size: 0.9rem;
          }
        }

        .download-btn {
          background: rgba(255,255,255,0.05);
          border: 1px solid var(--border-color);
          border-radius: 6px;
          padding: 6px;
          color: var(--text-color);
          cursor: pointer;
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          justify-content: center;
          opacity: 0.8;
        }

        .download-btn:hover {
          background: rgba(255,255,255,0.1);
          opacity: 1;
          color: var(--primary-color);
          border-color: var(--primary-color);
        }

        @media (max-width: 768px) {
          .download-btn {
            padding: 8px; /* Bigger touch target */
            background: rgba(255,255,255,0.08);
          }
        }
      </style>

      <div class="vault-header">
        <div class="header-title">
          <h2>The Vault</h2>
          <div class="subtitle">Secure Archive <span style="opacity: 0.3; margin-left: 8px;" id="count-badge">0 Files</span></div>
        </div>
        <div class="input-group" style="width: 240px; background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); border-radius: 20px; padding: 6px 16px;">
          <input type="text" placeholder="Search..." id="searchInput" style="background: transparent; border: none; font-size: 0.75rem; outline: none; width: 100%; color: var(--text-color);">
          <span id="mobile-count" style="font-size: 0.7rem; color: var(--text-muted); white-space: nowrap; margin-left: 8px;"></span>
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
    const badge = this.shadowRoot.getElementById('count-badge');
    const mobileCount = this.shadowRoot.getElementById('mobile-count');

    if (!grid) return;

    if (this.loading) {
      grid.innerHTML = '<div class="empty-state">Loading Library...</div>';
      return;
    }

    // Update count
    if (badge) badge.textContent = `${this.videos.length} Files`;
    if (mobileCount) mobileCount.textContent = `${this.videos.length}`;

    if (this.videos.length === 0) {
      grid.innerHTML = '<div class="empty-state">No files found in library.</div>';
      return;
    }

    // Attach click handlers properly instead of inline HTML for better performance?
    // For simplicity, we just attach a data attribute and use delegation or direct onclick
    grid.innerHTML = ''; // clear

    this.videos.forEach(v => {
      const card = document.createElement('div');
      card.className = 'video-card';
      card.innerHTML = `
            <div class="thumbnail-container">
              <img src="/api/thumbnails/${v.id}" loading="lazy" alt="${v.title}">
              <div class="duration-badge">${this.formatDuration(v.duration_seconds)}</div>
            </div>
            <div class="card-info">
              <div class="card-title">${v.title}</div>
              <div class="card-meta-row" style="font-size: 0.75rem; color: var(--text-muted);">
                <div style="display: flex; align-items: center; gap: 8px;">
                  <span style="color: var(--text-color); font-weight: 500;">${v.uploader}</span>
                  <span style="opacity: 0.3">•</span>
                  <span>${v.platform_display || 'Web'}</span>
                </div>
                <button class="download-btn" title="Download Video">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
                  </svg>
                </button>
              </div>
            </div>
        `;

      const dlBtn = card.querySelector('.download-btn');
      dlBtn.onclick = (e) => {
        e.stopPropagation();
        this.downloadVideo(v.id);
      };

      card.onclick = (e) => this.openVideo(e, v);
      grid.appendChild(card);
    });
  }

  downloadVideo(id) {
    const video = this.videos.find(v => v.id === id);
    const title = video ? video.title : '';
    const slug = title ? title.toLowerCase().replace(/[^\w\s-]/g, '').replace(/[\s_]+/g, '_').substring(0, 100) : id;
    const link = document.createElement('a');
    link.href = `/api/media/${id}?download=1`;
    link.download = `${slug}.mp4`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  formatDuration(seconds) {
    if (!seconds) return '0:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  }
}

customElements.define('zget-vault', ZgetVault);
