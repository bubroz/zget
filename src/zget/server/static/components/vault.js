import { ZgetBase } from './base.js';

export class ZgetVault extends ZgetBase {
  constructor() {
    super();
    this.videos = [];
    this.loading = true;
    this.searchQuery = '';

    // Platform Color Intelligence (Arc Raiders Radiant Alignment)
    this.PLATFORM_COLORS = {
      'youtube': { bg: '#FF0000', fg: '#FFFFFF' },
      'instagram': { bg: '#E4405F', fg: '#FFFFFF' },
      'tiktok': { bg: '#00F2EA', fg: '#000000' },
      'twitter': { bg: '#1DA1F2', fg: '#FFFFFF' },
      'x': { bg: '#FFFFFF', fg: '#000000' }, // X is often White/Black
      'reddit': { bg: '#FF4500', fg: '#FFFFFF' },
      'twitch': { bg: '#9146FF', fg: '#FFFFFF' },
      'facebook': { bg: '#1877F2', fg: '#FFFFFF' }
    };

    // Platform SVG Icons (recognizable at a glance)
    this.PLATFORM_ICONS = {
      'youtube': `<svg width="16" height="16" viewBox="0 0 24 24" fill="#FF0000"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>`,
      'instagram': `<svg width="16" height="16" viewBox="0 0 24 24" fill="#E4405F"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>`,
      'tiktok': `<svg width="16" height="16" viewBox="0 0 24 24" fill="#FF0050"><path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z"/></svg>`,
      'twitter': `<svg width="16" height="16" viewBox="0 0 24 24" fill="#1DA1F2"><path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z"/></svg>`,
      'x': `<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>`,
      'reddit': `<svg width="16" height="16" viewBox="0 0 24 24" fill="#FF4500"><path d="M12 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0zm5.01 4.744c.688 0 1.25.561 1.25 1.249a1.25 1.25 0 0 1-2.498.056l-2.597-.547-.8 3.747c1.824.07 3.48.632 4.674 1.488.308-.309.73-.491 1.207-.491.968 0 1.754.786 1.754 1.754 0 .716-.435 1.333-1.01 1.614a3.111 3.111 0 0 1 .042.52c0 2.694-3.13 4.87-7.004 4.87-3.874 0-7.004-2.176-7.004-4.87 0-.183.015-.366.043-.534A1.748 1.748 0 0 1 4.028 12c0-.968.786-1.754 1.754-1.754.463 0 .898.196 1.207.49 1.207-.883 2.878-1.43 4.744-1.487l.885-4.182a.342.342 0 0 1 .14-.197.35.35 0 0 1 .238-.042l2.906.617a1.214 1.214 0 0 1 1.108-.701zM9.25 12C8.561 12 8 12.562 8 13.25c0 .687.561 1.248 1.25 1.248.687 0 1.248-.561 1.248-1.249 0-.688-.561-1.249-1.249-1.249zm5.5 0c-.687 0-1.248.561-1.248 1.25 0 .687.561 1.248 1.249 1.248.688 0 1.249-.561 1.249-1.249 0-.687-.562-1.249-1.25-1.249zm-5.466 3.99a.327.327 0 0 0-.231.094.33.33 0 0 0 0 .463c.842.842 2.484.913 2.961.913.477 0 2.105-.056 2.961-.913a.361.361 0 0 0 .029-.463.33.33 0 0 0-.464 0c-.547.533-1.684.73-2.512.73-.828 0-1.979-.196-2.512-.73a.326.326 0 0 0-.232-.095z"/></svg>`,
      'twitch': `<svg width="16" height="16" viewBox="0 0 24 24" fill="#9146FF"><path d="M11.571 4.714h1.715v5.143H11.57zm4.715 0H18v5.143h-1.714zM6 0L1.714 4.286v15.428h5.143V24l4.286-4.286h3.428L22.286 12V0zm14.571 11.143l-3.428 3.428h-3.429l-3 3v-3H6.857V1.714h13.714z"/></svg>`,
      'facebook': `<svg width="16" height="16" viewBox="0 0 24 24" fill="#1877F2"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>`,
    };
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
        :host { display: block; padding: 0 40px 40px 40px; }
        
        .vault-header {
          display: none;
        }

        .search-container {
          margin-bottom: 20px;
          display: flex;
          width: 100%;
          padding-top: 0;
        }

        .search-box {
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid var(--border-color);
          border-radius: 4px;
          padding: 8px 16px;
          display: flex;
          align-items: center;
          gap: 12px;
          width: 100%;
          transition: all 0.2s ease;
        }

        .search-box:focus-within {
          background: rgba(255, 255, 255, 0.05);
          border-color: var(--primary-color);
          box-shadow: 0 0 15px hsla(var(--primary-hsl), 0.1);
        }

        .search-box input {
          background: transparent;
          border: none;
          color: var(--text-color);
          font-size: 0.8rem;
          font-family: var(--font-mono);
          outline: none;
          flex: 1;
          letter-spacing: 0.05em;
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
            background: var(--platform-color, var(--primary-color));
            color: var(--platform-fg, white);
            font-size: 0.65rem;
            font-weight: 800;
            padding: 3px 10px;
            border-radius: 4px;
            text-transform: uppercase;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            letter-spacing: 0.05em;
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
            background: rgba(16, 185, 129, 0.1);
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
            padding: 0 16px 40px 16px;
          }

          .search-container {
            margin-bottom: 16px;
          }

          .video-grid {
            grid-template-columns: 1fr;
            gap: 20px;
            padding: 0;
          }

          .video-card {
            border-radius: 12px;
            background: #0B0E14;
            border: 1px solid var(--border-color);
          }

          .thumbnail-container {
            aspect-ratio: 16/9;
            min-height: auto;
            max-height: 40vh;
            border-bottom: 1px solid var(--border-color);
          }

          .thumbnail-container img {
            height: 100%;
            object-fit: cover;
          }

          .card-info {
            padding: 12px;
          }

          .card-title {
            font-size: 0.85rem;
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
            padding: 8px;
            background: rgba(255,255,255,0.08);
          }
        }
      </style>

      <div class="search-container">
        <div class="search-box">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="opacity: 0.4;">
            <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
          </svg>
          <input type="text" placeholder="SEARCH // ARCHIVE" id="vaultSearch">
        </div>
      </div>
      <div class="video-grid" id="grid">
        <!-- Videos injected here -->
      </div>
    `;

    this.shadowRoot.getElementById('vaultSearch').addEventListener('input', (e) => {
      this.searchQuery = e.target.value;
      this.fetchVideos();
    });
  }

  updateList() {
    const grid = this.shadowRoot.getElementById('grid');

    if (!grid) return;

    if (this.loading) {
      grid.innerHTML = '<div class="empty-state">Loading Library...</div>';
      return;
    }

    // Dispatch library-updated event for the global header
    this.dispatchEvent(new CustomEvent('library-updated', {
      detail: { count: this.videos.length },
      bubbles: true,
      composed: true
    }));

    if (this.videos.length === 0) {
      grid.innerHTML = '<div class="empty-state">No files found in library.</div>';
      return;
    }

    grid.innerHTML = ''; // clear

    this.videos.forEach(v => {
      const platformDisplay = (v.platform_display || 'Web').toLowerCase();
      let platformKey = Object.keys(this.PLATFORM_COLORS).find(key =>
        platformDisplay.includes(key)
      );

      const colorSet = this.PLATFORM_COLORS[platformKey] || {
        bg: 'var(--primary-color)',
        fg: '#FFFFFF'
      };

      // Get platform icon (or fallback to empty)
      const platformIcon = this.PLATFORM_ICONS[platformKey] || '';

      const card = document.createElement('div');
      card.className = 'video-card';
      card.style.setProperty('--platform-color', colorSet.bg);
      card.style.setProperty('--platform-fg', colorSet.fg);

      card.innerHTML = `
            <div class="thumbnail-container">
              <img src="/api/thumbnails/${v.id}" loading="lazy" alt="${v.title}">
              <div class="duration-badge">${this.formatDuration(v.duration_seconds)}</div>
            </div>
            <div class="card-info">
              <div class="card-title">${v.title}</div>
              <div class="card-meta-row" style="font-size: 0.75rem; color: var(--text-muted);">
                <div style="display: flex; align-items: center; gap: 6px;">
                  <span class="platform-icon">${platformIcon}</span>
                  <span style="color: var(--text-color); font-weight: 500;">${v.uploader}</span>
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
