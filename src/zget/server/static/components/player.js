import { ZgetBase } from './base.js';

export class ZgetPlayer extends ZgetBase {
  constructor() {
    super();
    this.video = null;
    this.loading = false;

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
    this.render();
  }

  async deleteVideo() {
    if (!this.video || !confirm(`Permanently delete "${this.video.title || 'this video'}"?`)) return;

    try {
      const res = await fetch(`/api/media/${this.video.id}`, { method: 'DELETE' });
      if (res.ok) {
        this.close();
        // Emit refresh event
        this.dispatchEvent(new CustomEvent('video-deleted', { bubbles: true, composed: true }));
      }
    } catch (e) {
      alert('Delete failed.');
    }
  }

  async downloadVideo() {
    if (!this.video) return;
    const link = document.createElement('a');
    const slug = this.video.title ? this.video.title.toLowerCase().replace(/[^\w\s-]/g, '').replace(/[\s_]+/g, '_').substring(0, 100) : this.video.id;
    link.href = `/api/media/${this.video.id}?download=1`;
    link.download = `${slug}.mp4`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  formatDate(dateStr) {
    if (!dateStr) return '';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
    } catch (e) {
      return dateStr;
    }
  }

  formatViews(count) {
    if (!count) return '';
    if (count >= 1000000) return (count / 1000000).toFixed(1) + 'M views';
    if (count >= 1000) return (count / 1000).toFixed(1) + 'K views';
    return count + ' views';
  }

  getPlatformIcon(platform) {
    if (!platform) return '';
    const platformKey = platform.toLowerCase();
    return this.PLATFORM_ICONS[platformKey] || '';
  }

  async open(initialData) {
    console.log("[Player] Opening with:", initialData);
    // Show modal loading state immediately
    this.loading = true;
    this.video = initialData; // might be partial
    this.render();

    // Animate in
    const modal = this.shadowRoot.getElementById('modal');
    if (modal) {
      modal.style.display = 'flex';
      requestAnimationFrame(() => modal.classList.add('visible'));
    }

    // Fetch full details if we only have an ID or to ensure freshness
    try {
      const videoId = initialData.id;
      if (!videoId) throw new Error("No video ID provided");

      const res = await fetch(`/api/video/${videoId}`);
      if (!res.ok) throw new Error('Video not found');
      const fullData = await res.json();
      console.log("[Player] Fetched full data:", fullData);
      this.video = fullData;
    } catch (e) {
      console.error("[Player] Failed to load details:", e);
      // Fallback: use initialData but ensure title/uploader aren't missing
      if (!this.video || !this.video.title) {
        this.video = { ...initialData, title: initialData.title || 'Unknown Video', uploader: initialData.uploader || 'Unknown' };
      }
    } finally {
      this.loading = false;
      this.render();
      // Re-apply visible class because render nuked the DOM
      const newModal = this.shadowRoot.getElementById('modal');
      if (newModal) {
        newModal.style.display = 'flex';
        newModal.classList.add('visible');
      }
    }
  }

  close() {
    const modal = this.shadowRoot.getElementById('modal');
    if (!modal) return;

    modal.classList.remove('visible');
    setTimeout(() => {
      modal.style.display = 'none';
      this.video = null;
      this.render(); // Clear video element to stop playback
    }, 200);
  }

  render() {
    const v = this.video;

    this.shadowRoot.innerHTML = `
      <link rel="stylesheet" href="/styles/theme.css">
      <link rel="stylesheet" href="/styles/shared.css">
      <style>
        .modal-overlay {
          position: fixed;
          top: 0; left: 0; right: 0; bottom: 0;
          background: rgba(0,0,0,0.92);
          backdrop-filter: blur(14px);
          z-index: 1000;
          display: none;
          justify-content: center;
          align-items: center;
          opacity: 0;
          transition: opacity 0.2s ease;
        }
        
        .modal-overlay.visible { opacity: 1; }

        .modal-content {
          width: 90%;
          max-width: 1000px;
          background: #0B0E14;
          border: 1px solid var(--border-color);
          border-radius: var(--radius-lg);
          overflow: hidden;
          box-shadow: 0 25px 50px -12px rgba(0,0,0,0.7);
          display: flex;
          flex-direction: column;
          max-height: 90vh;
          position: relative;
        }

        .video-wrapper {
          width: 100%;
          background: #000;
          position: relative;
          flex: 0 0 auto;
          aspect-ratio: 16/9;
          display: flex;
          justify-content: center;
          align-items: center;
        }

        video {
          width: 100%;
          height: 100%;
          max-height: 70vh;
          object-fit: contain;
        }

        .info-bar {
          padding: 24px;
          border-top: 1px solid var(--border-color);
          background: #0B0E14;
          display: flex;
          flex-direction: column;
          gap: 20px;
          flex: 1;
          overflow-y: auto;
        }

        .meta-header {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        h2 { 
            margin: 0; 
            font-size: 1.25rem; 
            font-weight: 600; 
            color: var(--text-color);
            line-height: 1.4;
        }
        
        .meta-row { 
            margin: 0; 
            color: var(--text-muted); 
            font-size: 0.85rem; 
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }

        .bullet { opacity: 0.3; }

        .platform-icon {
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .platform-icon svg {
            display: block;
        }

        .tag {
            background: rgba(255,255,255,0.05);
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.7rem;
            border: 1px solid var(--border-color);
            text-transform: uppercase;
            font-weight: 700;
            letter-spacing: 0.05em;
        }

        .actions {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          margin-top: auto;
          padding-top: 20px;
          border-top: 1px solid rgba(255,255,255,0.05);
        }

        @media (max-width: 768px) {
          .modal-content {
            width: 100%;
            height: 100%;
            max-height: 100vh;
            border-radius: 0;
            border: none;
          }

          .info-bar {
            padding: 20px;
          }

          .actions {
            position: sticky;
            bottom: 0;
            background: #0B0E14;
            padding-bottom: env(safe-area-inset-bottom, 20px);
          }

          .actions .btn {
            flex: 1;
            padding: 12px;
            justify-content: center;
          }

          .actions .btn.close-btn {
            order: -1;
            width: 100%;
            flex: none;
          }
        }
        
        .loading-title {
            height: 24px;
            width: 60%;
            background: rgba(255,255,255,0.05);
            border-radius: 4px;
            margin-bottom: 8px;
            animation: pulse 1.5s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 0.5; }
            50% { opacity: 0.8; }
            100% { opacity: 0.5; }
        }
      </style>

      <div class="modal-overlay" id="modal" onclick="if(event.target === this) this.getRootNode().host.close()">
        ${v ? `
          <div class="modal-content">
            <div class="video-wrapper">
              <video controls autoplay>
                <source src="/api/media/${v.id}" type="video/mp4">
                Your browser does not support the video tag.
              </video>
            </div>
            
            <div class="info-bar">
              <div class="meta-header">
                ${this.loading ? `
                    <div class="loading-title"></div> 
                    <p>Loading details...</p>
                ` : `
                    <h2>${v.title || 'Untitled Archive'}</h2>
                    <div class="meta-row">
                        <span class="platform-icon">${this.getPlatformIcon(v.platform)}</span>
                        <span style="font-weight: 600; color: var(--text-color);">${v.uploader || 'Creator Unknown'}</span>
                        <span class="bullet">•</span>
                        <span>${this.formatDate(v.upload_date)}</span>
                    </div>
                    ${v.view_count || v.resolution ? `
                        <div class="meta-row" style="opacity: 0.5; font-size: 0.75rem; gap: 12px; margin-top: -8px;">
                            ${v.view_count ? `<span>${this.formatViews(v.view_count)}</span>` : ''}
                            ${v.view_count && v.resolution ? '<span class="bullet" style="opacity: 0.2;">|</span>' : ''}
                            ${v.resolution ? `<span>${v.resolution}</span>` : ''}
                            ${(v.view_count || v.resolution) && v.codec ? '<span class="bullet" style="opacity: 0.2;">|</span>' : ''}
                            ${v.codec ? `<span>${v.codec.toUpperCase()}</span>` : ''}
                        </div>
                    ` : ''}
                `}
              </div>
              
              <div class="actions">
                ${!this.loading ? `
                    <button class="btn" style="color: #ef4444; border-color: rgba(239,68,68, 0.2);" onclick="this.getRootNode().host.deleteVideo()">
                        Delete
                    </button>
                    <button class="btn" onclick="window.open('${v.url || '#'}', '_blank')">Source</button>
                    <button class="btn primary" onclick="this.getRootNode().host.downloadVideo()">Download</button>
                ` : ''}
                <button class="btn close-btn" onclick="this.getRootNode().host.close()">Close</button>
              </div>
            </div>
          </div>
        ` : ''}
      </div>
    `;
  }
}

customElements.define('zget-player', ZgetPlayer);
