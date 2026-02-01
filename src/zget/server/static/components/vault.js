import { ZgetBase } from './base.js';

export class ZgetVault extends ZgetBase {
  constructor() {
    super();
    this.videos = [];
    this.loading = true;
    this.searchQuery = '';
    this.selectedIds = new Set(); // Multi-select state
    this.orphanedCount = 0; // Orphan detection state
    this.orphanedIds = []; // IDs of orphaned records

    // Platform Color Intelligence (Arc Raiders Radiant Alignment)
    this.PLATFORM_COLORS = {
      'youtube': { bg: '#FF0000', fg: '#FFFFFF' },
      'instagram': { bg: '#E4405F', fg: '#FFFFFF' },
      'tiktok': { bg: '#00F2EA', fg: '#000000' },
      'twitter': { bg: '#1DA1F2', fg: '#FFFFFF' },
      'x': { bg: '#FFFFFF', fg: '#000000' }, // X is often White/Black
      'reddit': { bg: '#FF4500', fg: '#FFFFFF' },
      'twitch': { bg: '#9146FF', fg: '#FFFFFF' },
      'facebook': { bg: '#1877F2', fg: '#FFFFFF' },
      'c-span': { bg: '#182A4E', fg: '#FFFFFF' }
    };

    // Platform Icons - use downloaded logos from static/images/platforms/
    this.PLATFORM_ICONS = {
      'youtube': `<img src="/images/platforms/youtube.png" alt="YouTube" style="height: 14px; width: auto;">`,
      'instagram': `<img src="/images/platforms/instagram.png" alt="Instagram" style="height: 14px; width: auto;">`,
      'tiktok': `<img src="/images/platforms/tiktok.png" alt="TikTok" style="height: 14px; width: auto;">`,
      'twitter': `<img src="/images/platforms/twitter.png" alt="Twitter" style="height: 14px; width: auto;">`,
      'x': `<img src="/images/platforms/x.png" alt="X" style="height: 14px; width: auto; filter: invert(1);">`,
      'reddit': `<img src="/images/platforms/reddit.png" alt="Reddit" style="height: 14px; width: auto;">`,
      'twitch': `<img src="/images/platforms/twitch.png" alt="Twitch" style="height: 14px; width: auto;">`,
      'facebook': `<img src="/images/platforms/facebook.png" alt="Facebook" style="height: 14px; width: auto;">`,
      'c-span': `<img src="/images/platforms/c-span.png" alt="C-SPAN" style="height: 14px; width: auto; filter: brightness(0) invert(1);">`,
    };
  }

  connectedCallback() {
    this.loadStyles();
    this.renderTemplate();
    this.fetchVideos();
    // Listen for Escape key to clear selection
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') this.clearSelection();
    });
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

      // Proactively check for orphaned records
      this.checkOrphans();
    } catch (err) {
      console.error('Failed to fetch videos:', err);
    } finally {
      this.loading = false;
      this.updateList();
    }
  }

  async checkOrphans() {
    try {
      const res = await fetch('/api/library/doctor', { method: 'POST' });
      const data = await res.json();
      this.orphanedCount = data.orphaned_count || 0;
      this.orphanedIds = data.orphaned_ids || [];
      // Re-render to show orphan banner if needed
      if (this.orphanedCount > 0) {
        this.updateList();
      }
    } catch (err) {
      console.error('Failed to check orphans:', err);
    }
  }

  async cleanupOrphans() {
    try {
      const res = await fetch('/api/library/cleanup', { method: 'POST' });
      const data = await res.json();
      this.orphanedCount = 0;
      this.orphanedIds = [];
      this.fetchVideos(); // Refresh the list
    } catch (err) {
      console.error('Failed to cleanup orphans:', err);
    }
  }

  toggleSelection(videoId) {
    if (this.selectedIds.has(videoId)) {
      this.selectedIds.delete(videoId);
    } else {
      this.selectedIds.add(videoId);
    }
    this.updateList();
  }

  clearSelection() {
    this.selectedIds.clear();
    this.updateList();
  }

  selectAll() {
    this.videos.forEach(v => this.selectedIds.add(v.id));
    this.updateList();
  }

  async bulkDelete() {
    const count = this.selectedIds.size;
    if (count === 0) return;

    if (!confirm(`Delete ${count} video${count > 1 ? 's' : ''}? This cannot be undone.`)) return;

    try {
      const res = await fetch('/api/media/bulk', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: Array.from(this.selectedIds) })
      });
      const data = await res.json();
      this.selectedIds.clear();
      this.fetchVideos();
      // Emit refresh event
      this.dispatchEvent(new CustomEvent('video-deleted', { bubbles: true, composed: true }));
    } catch (err) {
      console.error('Bulk delete failed:', err);
      alert('Delete failed. Please try again.');
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

        .delete-overlay-btn {
            position: absolute;
            top: 8px;
            right: 8px;
            background: rgba(239, 68, 68, 0.9);
            border: none;
            border-radius: 6px;
            padding: 6px;
            cursor: pointer;
            opacity: 0;
            transition: opacity 0.15s ease, transform 0.15s ease;
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10;
        }
        
        .video-card:hover .delete-overlay-btn {
            opacity: 1;
        }
        
        .delete-overlay-btn:hover {
            background: #dc2626;
            transform: scale(1.1);
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

        /* Selection State */
        .video-card.selected {
          border: 2px solid var(--primary-color) !important;
          box-shadow: 0 0 20px hsla(var(--primary-hsl), 0.3);
          background: #0B0E14;
        }

        .video-card.selected .thumbnail-container::after {
          content: '✓';
          position: absolute;
          top: 8px;
          left: 8px;
          background: var(--primary-color);
          color: white;
          width: 24px;
          height: 24px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 14px;
          font-weight: bold;
          box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }

        /* Orphan Warning Banner */
        .orphan-banner {
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.3);
          border-radius: 8px;
          padding: 12px 16px;
          margin-bottom: 20px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
        }

        .orphan-banner-text {
          color: #ef4444;
          font-size: 0.85rem;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .orphan-banner-btn {
          background: rgba(239, 68, 68, 0.2);
          border: 1px solid rgba(239, 68, 68, 0.4);
          color: #ef4444;
          padding: 6px 12px;
          border-radius: 6px;
          font-size: 0.75rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
          white-space: nowrap;
        }

        .orphan-banner-btn:hover {
          background: rgba(239, 68, 68, 0.3);
        }

        /* Floating Action Bar */
        .action-bar {
          position: fixed;
          bottom: 0;
          left: 0;
          right: 0;
          background: var(--glass-bg);
          backdrop-filter: blur(12px);
          border-top: 1px solid var(--glass-border);
          padding: 12px 20px;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 16px;
          z-index: 100;
          animation: slideUp 0.2s ease;
        }

        @keyframes slideUp {
          from { transform: translateY(100%); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }

        .action-bar-inner {
          display: flex;
          align-items: center;
          gap: 16px;
          max-width: 600px;
          width: 100%;
        }

        .action-bar-count {
          font-family: var(--font-mono);
          font-size: 0.85rem;
          color: var(--text-color);
          font-weight: 600;
        }

        .action-bar-btn {
          padding: 8px 16px;
          border-radius: 6px;
          font-size: 0.8rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
          border: 1px solid var(--border-color);
          background: rgba(255,255,255,0.05);
          color: var(--text-color);
        }

        .action-bar-btn:hover {
          background: rgba(255,255,255,0.1);
        }

        .action-bar-btn.danger {
          background: rgba(239, 68, 68, 0.2);
          border-color: rgba(239, 68, 68, 0.4);
          color: #ef4444;
        }

        .action-bar-btn.danger:hover {
          background: rgba(239, 68, 68, 0.3);
        }

        .action-bar-spacer {
          flex: 1;
        }

        @media (max-width: 768px) {
          .action-bar {
            padding: 12px 16px;
            padding-bottom: max(12px, env(safe-area-inset-bottom));
          }

          .action-bar-inner {
            gap: 12px;
          }

          .action-bar-btn {
            padding: 10px 14px;
            flex: 1;
          }
        }

        /* Padding for action bar */
        :host(.has-selection) {
          padding-bottom: 100px;
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
      <div id="orphanBanner"></div>
      <div class="video-grid" id="grid">
        <!-- Videos injected here -->
      </div>
      <div id="actionBar"></div>
    `;

    this.shadowRoot.getElementById('vaultSearch').addEventListener('input', (e) => {
      this.searchQuery = e.target.value;
      this.fetchVideos();
    });
  }

  updateList() {
    const grid = this.shadowRoot.getElementById('grid');
    const orphanBanner = this.shadowRoot.getElementById('orphanBanner');
    const actionBar = this.shadowRoot.getElementById('actionBar');

    if (!grid) return;

    // Update host class for selection padding
    if (this.selectedIds.size > 0) {
      this.classList.add('has-selection');
    } else {
      this.classList.remove('has-selection');
    }

    // Render orphan banner
    if (orphanBanner) {
      if (this.orphanedCount > 0) {
        orphanBanner.innerHTML = `
          <div class="orphan-banner">
            <span class="orphan-banner-text">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
                <path d="M12 9v4"/><path d="M12 17h.01"/>
              </svg>
              ${this.orphanedCount} archived item${this.orphanedCount > 1 ? 's have' : ' has'} missing files
            </span>
            <button class="orphan-banner-btn" id="cleanupBtn">Clean Up</button>
          </div>
        `;
        this.shadowRoot.getElementById('cleanupBtn').onclick = () => this.cleanupOrphans();
      } else {
        orphanBanner.innerHTML = '';
      }
    }

    // Render action bar
    if (actionBar) {
      if (this.selectedIds.size > 0) {
        actionBar.innerHTML = `
          <div class="action-bar">
            <div class="action-bar-inner">
              <span class="action-bar-count">${this.selectedIds.size} selected</span>
              <div class="action-bar-spacer"></div>
              <button class="action-bar-btn" id="selectAllBtn">Select All</button>
              <button class="action-bar-btn" id="clearBtn">Clear</button>
              <button class="action-bar-btn danger" id="deleteBtn">Delete</button>
            </div>
          </div>
        `;
        this.shadowRoot.getElementById('selectAllBtn').onclick = () => this.selectAll();
        this.shadowRoot.getElementById('clearBtn').onclick = () => this.clearSelection();
        this.shadowRoot.getElementById('deleteBtn').onclick = () => this.bulkDelete();
      } else {
        actionBar.innerHTML = '';
      }
    }

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
      if (this.selectedIds.has(v.id)) {
        card.classList.add('selected');
      }
      card.style.setProperty('--platform-color', colorSet.bg);
      card.style.setProperty('--platform-fg', colorSet.fg);

      card.innerHTML = `
            <div class="thumbnail-container">
              <img src="/api/thumbnails/${v.id}" loading="lazy" alt="${v.title}">
              <div class="duration-badge">${this.formatDuration(v.duration_seconds)}</div>
              <button class="delete-overlay-btn" title="Delete Video">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>
                </svg>
              </button>
            </div>
            <div class="card-info">
              <div class="card-title">${v.title}</div>
              <div class="card-meta-row" style="font-size: 0.75rem; color: var(--text-muted);">
                <div style="display: flex; align-items: center; gap: 6px;">
                  <span class="platform-icon">${platformIcon}</span>
                  ${(v.uploader || '').toLowerCase() !== platformKey ? `<span style="color: var(--text-color); font-weight: 500;">${v.uploader || ''}</span>` : ''}
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

      // Delete overlay button
      const deleteBtn = card.querySelector('.delete-overlay-btn');
      deleteBtn.onclick = async (e) => {
        e.stopPropagation();
        if (confirm(`Delete "${v.title || 'this video'}"?`)) {
          try {
            const res = await fetch(`/api/media/${v.id}`, { method: 'DELETE' });
            if (res.ok) {
              this.fetchVideos();
              this.dispatchEvent(new CustomEvent('video-deleted', { bubbles: true, composed: true }));
            }
          } catch (err) {
            alert('Delete failed.');
          }
        }
      };

      // Card click: toggle selection if in selection mode, otherwise open video
      card.onclick = (e) => {
        if (this.selectedIds.size > 0) {
          // Already in selection mode - toggle this card
          e.preventDefault();
          this.toggleSelection(v.id);
        } else {
          // Not in selection mode - open the video
          this.openVideo(e, v);
        }
      };

      // Long press / right-click to start selection (optional: add later)
      card.oncontextmenu = (e) => {
        e.preventDefault();
        this.toggleSelection(v.id);
      };

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
