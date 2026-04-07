class LilkaRepository {
  constructor() {
    this.currentType = 'apps';
    this.currentPage = 0;
    this.totalPages = 0;
    this.manifests = [];
    this.currentScreenshots = [];
    this.currentLightboxIndex = 0;
    this.init();
  }

  init() {
    this.setupEventListeners();
    this.setupLightboxListeners();
    this.handleRouting();
  }

  async handleRouting() {
    const params = new URLSearchParams(window.location.search);
    const type = params.get('type');
    const page = params.get('page');
    const item = params.get('item');

    // Handle direct item link: ?type=apps&item=ble.app
    if (item && type) {
      this.currentType = type;
      this.updateActiveTab(type);
      // Load the page list in background first
      await this.loadPage();
      // Then open the modal
      await this.openDirectItem(type, item);
      return;
    }

    // Handle authors page
    if (type === 'authors') {
      this.currentType = type;
      const authorParam = params.get('author');
      await this.showAuthors();
      this.updateActiveTab('authors');
      if (authorParam) {
        const sectionId = `author-${this.authorSlug(authorParam)}`;
        const section = document.getElementById(sectionId);
        if (section) {
          section.classList.remove('collapsed');
          section.scrollIntoView({behavior: 'smooth', block: 'start'});
          section.classList.add('author-highlight');
          setTimeout(() => section.classList.remove('author-highlight'), 2000);
        }
      }
      return;
    }

    // Handle page navigation: ?type=apps&page=1
    if (type) {
      this.currentType = type;
      this.currentPage = page ? parseInt(page) : 0;
      await this.switchType(type);
      return;
    }

    // Default: load apps page 0
    await this.loadPage();
  }

  updateActiveTab(type) {
    // Update active tab
    document.querySelectorAll('.tab-button').forEach(btn => {
      btn.classList.remove('active');
    });
    document.querySelector(`[data-type="${type}"]`).classList.add('active');

    // Show/hide appropriate content
    document.getElementById('content').style.display =
        (type === 'docs' || type === 'authors') ? 'none' : 'block';
    document.getElementById('docs').style.display =
        type === 'docs' ? 'block' : 'none';
    document.getElementById('authors').style.display =
        type === 'authors' ? 'block' : 'none';
  }

  async openDirectItem(type, itemName) {
    try {
      const manifestPath = `${type}/${itemName}/index.json`;
      const response = await fetch(manifestPath);

      if (!response.ok) {
        throw new Error(`Item not found: ${itemName}`);
      }

      const manifest = await response.json();
      this.showModal(manifest, itemName);
    } catch (error) {
      console.error('Error opening direct item:', error);
      this.showError(`Failed to load ${type.slice(0, -1)}: ${itemName}`);
    }
  }

  updateURL(type = null, page = null, itemName = null) {
    const params = new URLSearchParams();

    if (itemName) {
      // Direct item link: ?type=apps&item=ble.app
      params.set('type', type);
      params.set('item', itemName);
    } else if (type) {
      // Page navigation: ?type=apps&page=1
      params.set('type', type);
      if (page !== null && page > 0) {
        params.set('page', page);
      }
    }

    const url = params.toString() ? `?${params.toString()}` : '/';
    window.history.pushState({type, page, itemName}, '', url);
  }

  setupLightboxListeners() {
    const lightbox = document.getElementById('lightbox');
    const lightboxClose = document.getElementById('lightboxClose');
    const lightboxPrev = document.getElementById('lightboxPrev');
    const lightboxNext = document.getElementById('lightboxNext');

    lightboxClose.addEventListener('click', () => this.closeLightbox());
    lightboxPrev.addEventListener('click', () => this.prevLightboxImage());
    lightboxNext.addEventListener('click', () => this.nextLightboxImage());

    // Close on background click
    lightbox.addEventListener('click', (e) => {
      if (e.target === lightbox) {
        this.closeLightbox();
      }
    });

    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
      if (lightbox.style.display === 'flex') {
        if (e.key === 'Escape') this.closeLightbox();
        if (e.key === 'ArrowLeft') this.prevLightboxImage();
        if (e.key === 'ArrowRight') this.nextLightboxImage();
      }
    });
  }

  setupEventListeners() {
    // Tab switching
    document.querySelectorAll('.tab-button').forEach(button => {
      button.addEventListener('click', (e) => {
        const type = e.target.dataset.type;
        // Track tab clicks
        if (window.umami) {
          window.umami.track('tab-navigation', {tab: type});
        }
        if (type === 'docs') {
          this.showDocumentation();
        } else if (type === 'authors') {
          this.showAuthors();
        } else {
          this.switchType(type);
        }
      });
    });

    // Pagination - top
    document.getElementById('prevPage').addEventListener('click', () => {
      if (this.currentPage > 0) {
        this.currentPage--;
        this.loadPage();
      }
    });

    document.getElementById('nextPage').addEventListener('click', () => {
      if (this.currentPage < this.totalPages - 1) {
        this.currentPage++;
        this.loadPage();
      }
    });

    // Pagination - bottom
    document.getElementById('prevPageBottom').addEventListener('click', () => {
      if (this.currentPage > 0) {
        this.currentPage--;
        this.loadPage();
      }
    });

    document.getElementById('nextPageBottom').addEventListener('click', () => {
      if (this.currentPage < this.totalPages - 1) {
        this.currentPage++;
        this.loadPage();
      }
    });

    // Modal
    const modal = document.getElementById('modal');
    const closeBtn = document.querySelector('.close');

    closeBtn.addEventListener('click', () => {
      modal.style.display = 'none';
      // Return to list view URL
      this.updateURL(this.currentType, this.currentPage);
    });

    window.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.style.display = 'none';
        // Return to list view URL
        this.updateURL(this.currentType, this.currentPage);
      }
    });

    // Close modal with ESC key
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && modal.style.display === 'block') {
        modal.style.display = 'none';
        // Return to list view URL
        this.updateURL(this.currentType, this.currentPage);
      }
    });

    // Handle browser back/forward buttons
    window.addEventListener('popstate', (e) => {
      modal.style.display = 'none';
      this.handleRouting();
    });
  }
  async switchType(type) {
    this.currentType = type;
    const params = new URLSearchParams(window.location.search);
    if (params.get('type') !== type) {
      this.currentPage = 0;
    }

    // Update active tab
    document.querySelectorAll('.tab-button').forEach(btn => {
      btn.classList.remove('active');
    });
    document.querySelector(`[data-type="${type}"]`).classList.add('active');

    // Show/hide appropriate content
    document.getElementById('content').style.display = 'block';
    document.getElementById('docs').style.display = 'none';
    document.getElementById('authors').style.display = 'none';

    await this.loadPage();
  }

  async showAuthors() {
    this.updateActiveTab('authors');
    document.getElementById('content').style.display = 'none';
    document.getElementById('loading').style.display = 'none';
    document.getElementById('error').style.display = 'none';
    document.getElementById('docs').style.display = 'none';
    const authorsContainer = document.getElementById('authors');
    authorsContainer.style.display = 'block';

    this.updateURL('authors');

    try {
      const response = await fetch('authors.json');
      if (!response.ok) {
        throw new Error('Failed to load authors data');
      }
      const authors = await response.json();
      authorsContainer.innerHTML = this.renderAuthorsPage(authors);

      // Add click handlers for author item cards
      authorsContainer.querySelectorAll('.author-item-card').forEach(card => {
        card.addEventListener('click', async () => {
          const itemType = card.dataset.itemType;
          const itemPath = card.dataset.itemPath;
          try {
            const manifestPath = `${itemType}/${itemPath}/index.json`;
            const resp = await fetch(manifestPath);
            if (!resp.ok) throw new Error(`Item not found: ${itemPath}`);
            const manifest = await resp.json();
            this.currentType = itemType;
            this.showModal(manifest, itemPath);
          } catch (err) {
            console.error('Error opening item from authors:', err);
          }
        });
      });

      // Collapsible author sections
      authorsContainer.querySelectorAll('.author-section-header')
          .forEach(header => {
            header.addEventListener('click', () => {
              const section = header.closest('.author-section');
              section.classList.toggle('collapsed');
            });
          });
    } catch (error) {
      authorsContainer.innerHTML =
          `<p style="color: var(--error);">Failed to load authors: ${
              error.message}</p>`;
    }
  }

  renderAuthorsPage(authors) {
    const authorNames = Object.keys(authors);
    let html = `<h2 class="authors-title">Authors (${authorNames.length})</h2>`;

    for (const author of authorNames) {
      const items = authors[author];
      const apps = items.filter(i => i.type === 'apps');
      const mods = items.filter(i => i.type === 'mods');
      const badge = [];
      if (apps.length)
        badge.push(`${apps.length} app${apps.length > 1 ? 's' : ''}`);
      if (mods.length)
        badge.push(`${mods.length} mod${mods.length > 1 ? 's' : ''}`);

      const sectionId = `author-${this.authorSlug(author)}`;
      html += `<div class="author-section" id="${sectionId}">`;
      html += `<div class="author-section-header">`;
      html +=
          `<span class="author-section-name">${this.escapeHtml(author)}</span>`;
      html += `<span class="author-section-badge">${badge.join(', ')}</span>`;
      html += `<span class="author-section-toggle">&#9660;</span>`;
      html += `</div>`;
      html += `<div class="author-section-body">`;
      html += `<div class="author-items-grid">`;

      for (const item of items) {
        const iconPath =
            item.icon ? `${item.type}/${item.path}/static/${item.icon}` : '';
        const typeLabel = item.type === 'apps' ? 'App' : 'Mod';
        html += `<div class="author-item-card" data-item-type="${
            item.type}" data-item-path="${this.escapeHtml(item.path)}">`;
        if (item.icon) {
          html += `<img src="${iconPath}" alt="${
              this.escapeHtml(
                  item.name)}" class="icon" onerror="this.style.display='none'">`;
        }
        html += `<h3>${this.escapeHtml(item.name)}</h3>`;
        html += `<span class="author-item-type type-${item.type}">${
            typeLabel}</span>`;
        html += `<div class="short-desc">${
            this.escapeHtml(item.short_description)}</div>`;
        html += `</div>`;
      }

      html += `</div></div></div>`;
    }

    return html;
  }

  async showDocumentation() {
    // Update active tab
    document.querySelectorAll('.tab-button').forEach(btn => {
      btn.classList.remove('active');
    });
    document.querySelector('[data-type="docs"]').classList.add('active');

    // Hide items content, show docs
    document.getElementById('content').style.display = 'none';
    document.getElementById('loading').style.display = 'none';
    document.getElementById('error').style.display = 'none';
    document.getElementById('authors').style.display = 'none';
    const docsContainer = document.getElementById('docs');
    docsContainer.style.display = 'block';

    try {
      const response = await fetch('README.md');
      if (!response.ok) {
        throw new Error('Failed to load documentation');
      }
      const markdown = await response.text();
      docsContainer.innerHTML = marked.parse(markdown);
    } catch (error) {
      docsContainer.innerHTML =
          `<p style="color: var(--error);">Failed to load documentation: ${
              error.message}</p>`;
    }
  }

  async loadPage() {
    // Don't load if we're on docs tab
    if (this.currentType === 'docs') {
      return;
    }

    this.showLoading(true);
    this.hideError();

    try {
      const indexPath = `${this.currentType}/index_${this.currentPage}.json`;
      const response = await fetch(indexPath);

      if (!response.ok) {
        throw new Error(`Failed to load ${indexPath}: ${response.status}`);
      }

      const data = await response.json();
      this.totalPages = data.total_pages;
      // Remove trailing comma from manifests array
      this.manifests = data.manifests.filter(m => m && m.trim());

      this.loadManifests();
      this.updatePagination();

      // Update URL when page loads
      this.updateURL(this.currentType, this.currentPage);
    } catch (error) {
      this.showError(`Error loading page: ${error.message}`);
      console.error(error);
    } finally {
      this.showLoading(false);
    }
  }

  loadManifests() {
    const itemsContainer = document.getElementById('items');
    itemsContainer.innerHTML = '';

    for (const manifestName of this.manifests) {
      try {
        const manifestPath = `${this.currentType}/${manifestName}/index.json`;
        fetch(manifestPath)
            .then(response => {
              if (!response.ok) {
                console.warn(`Failed to load ${manifestPath}`);
                return null;
              }
              return response.json();
            })
            .then(manifest => {
              if (manifest) {
                const card = this.createItemCard(manifest, manifestName);
                itemsContainer.appendChild(card);
              }
            })
            .catch(error => {
              console.error(`Error loading manifest ${manifestName}:`, error);
            });
      } catch (error) {
        console.error(`Error loading manifest ${manifestName}:`, error);
      }
    }
  }

  createItemCard(manifest, manifestName) {
    const card = document.createElement('div');
    card.className = 'item-card';

    // Build icon path without duplicating type
    const iconPath =
        `${this.currentType}/${manifestName}/static/${manifest.icon}`;

    const authorId = this.authorSlug(manifest.author);
    card.innerHTML = `
            ${
        manifest.icon ?
            `<img src="${iconPath}" alt="${
                manifest
                    .name}" class="icon" onerror="this.style.display='none'">` :
            ''}
            <h3>${this.escapeHtml(manifest.name)}</h3>
            <div class="author"><a href="?type=authors&author=${
        encodeURIComponent(
            manifest.author)}" class="author-link" data-author="${
        this.escapeHtml(
            manifest.author)}">${this.escapeHtml(manifest.author)}</a></div>
            <div class="short-desc">${
        this.escapeHtml(manifest.short_description)}</div>
        `;

    // Author link click — navigate to authors page
    const authorLink = card.querySelector('.author-link');
    if (authorLink) {
      authorLink.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.navigateToAuthor(manifest.author);
      });
    }

    card.addEventListener('click', () => {
      // Track card clicks to view details
      if (window.umami) {
        window.umami.track(
            'view-details',
            {type: this.currentType, name: manifest.name, item: manifestName});
      }
      this.showModal(manifest, manifestName);
      // Update URL when opening modal
      this.updateURL(this.currentType, null, manifestName);
    });

    return card;
  }

  showModal(manifest, manifestName) {
    console.log('Opening modal for:', manifestName, manifest);

    // Track manifest views
    if (window.umami) {
      window.umami.track('view-manifest', {
        type: this.currentType,
        name: manifest.name,
        manifest: manifestName,
        author: manifest.author
      });
    }

    const modal = document.getElementById('modal');
    const modalBody = document.getElementById('modalBody');

    // Build paths - manifestName already includes the full path relative to
    // type
    const basePath = `${this.currentType}/${manifestName}`;
    const iconPath = `${basePath}/static/${manifest.icon}`;

    // Parse execution file or mod files
    let filesSection = '';
    try {
      if (this.currentType === 'apps' && manifest.entryfile) {
        const entryFile = this.parseJsonString(manifest.entryfile);
        if (entryFile && entryFile.location) {
          const downloadPath = `${basePath}/static/${entryFile.location}`;
          filesSection = `
                        <div class="modal-section">
                            <h3>📦 Entry File</h3>
                            <p><strong>Type:</strong> ${
              this.escapeHtml(entryFile.type || 'N/A')}</p>
                            <p><strong>File:</strong> ${
              this.escapeHtml(entryFile.location || 'N/A')}</p>
                            <a href="${
              downloadPath}" download class="download-btn" data-umami-event="download-entry-file" data-umami-event-app="${
              this.escapeHtml(manifest.name)}">⬇️ Download Entry File</a>
                        </div>
                    `;
        }
      }

      // Add additional files section
      if (manifest.files && Array.isArray(manifest.files) &&
          manifest.files.length > 0) {
        const additionalFilesSection = `
                    <div class="modal-section">
                        <h3>📁 Additional Files</h3>
                        ${
            manifest.files
                .map(file => {
                  const fileObj = typeof file === 'string' ?
                      this.parseJsonString(file) :
                      file;
                  if (fileObj && fileObj.location) {
                    const downloadPath =
                        `${basePath}/static/${fileObj.location}`;
                    return `
                                    <div class="file-item">
                                        <p><strong>${
                        this.escapeHtml(fileObj.type || 'Unknown')}:</strong> ${
                        this.escapeHtml(fileObj.location || 'N/A')}</p>
                                        <a href="${
                        downloadPath}" download class="download-btn-small" data-umami-event="download-additional-file" data-umami-event-app="${
                        this.escapeHtml(
                            manifest.name)}" data-umami-event-type="${
                        this.escapeHtml(fileObj.type)}">⬇️ Download</a>
                                    </div>
                                `;
                  }
                  return '';
                })
                .join('')}
                    </div>
                `;
        filesSection += additionalFilesSection;
      }

      if (this.currentType === 'mods' && manifest.modfiles) {
        const modFiles = this.parseJsonString(manifest.modfiles);
        if (Array.isArray(modFiles)) {
          filesSection = `
                        <div class="modal-section">
                            <h3>📦 Mod Files</h3>
                            ${
              modFiles
                  .map(file => {
                    const downloadPath = `${basePath}/static/${file.location}`;
                    return `
                                    <div class="file-item">
                                        <p><strong>${
                        this.escapeHtml(file.type || 'Unknown')}:</strong> ${
                        this.escapeHtml(file.location || 'N/A')}</p>
                                        <a href="${
                        downloadPath}" download class="download-btn-small" data-umami-event="download-mod-file" data-umami-event-mod="${
                        this.escapeHtml(
                            manifest.name)}" data-umami-event-type="${
                        this.escapeHtml(file.type)}">⬇️ Download</a>
                                    </div>
                                `;
                  })
                  .join('')}
                        </div>
                    `;
        }
      }

      if (manifest.package) {
        const packageDownloadPath = `${basePath}/${manifest.package}`;
        filesSection += `
                    <div class="modal-section">
                        <h3>📦 Package ZIP</h3>
                        <p><strong>File:</strong> ${
            this.escapeHtml(manifest.package)}</p>
                        <a href="${
            packageDownloadPath}" download class="download-btn" data-umami-event="download-package-zip" data-umami-event-item="${
            this.escapeHtml(manifest.name)}">⬇️ Download ZIP</a>
                    </div>
                `;
      }
    } catch (error) {
      console.error('Error parsing files section:', error);
      filesSection = `
                <div class="modal-section">
                    <h3>📦 Files</h3>
                    <p style="color: var(--error);">Error loading file information</p>
                </div>
            `;
    }

    // Build security section
    let securitySection = '';
    if (manifest.security && manifest.security.files &&
        manifest.security.files.length > 0) {
      const sec = manifest.security;
      const scanDate =
          sec.scan_date ? new Date(sec.scan_date).toLocaleString() : 'N/A';
      const allClean =
          sec.files.every(f => !f.av_scan || f.av_scan.status === 'clean');
      const hasAvScan = sec.clamav_available && sec.files.some(f => f.av_scan);

      let overallBadge;
      if (hasAvScan) {
        overallBadge = allClean ?
            '<span class="security-badge security-clean">✅ All files clean</span>' :
            '<span class="security-badge security-infected">⚠️ Threats detected</span>';
      } else {
        overallBadge =
            '<span class="security-badge security-noav">🔒 Checksums only</span>';
      }

      securitySection = `
        <div class="modal-section security-section">
          <h3>🛡️ Security</h3>
          <div class="security-header">
            ${overallBadge}
            <span class="security-date">Scanned: ${
          this.escapeHtml(scanDate)}</span>
          </div>
          <div class="security-files">
            ${
          sec.files
              .map(f => {
                const avBadge = f.av_scan ?
                    (f.av_scan.status === 'clean' ?
                         '<span class="security-badge-sm security-clean">✅ Clean</span>' :
                         f.av_scan.status === 'infected' ?
                         '<span class="security-badge-sm security-infected">❌ ' +
                             this.escapeHtml(f.av_scan.detail) + '</span>' :
                         '<span class="security-badge-sm security-noav">' +
                             this.escapeHtml(f.av_scan.detail) + '</span>') :
                    '';
                return `
                <div class="security-file-item">
                  <div class="security-file-name">
                    <strong>${this.escapeHtml(f.file)}</strong>
                    ${avBadge}
                  </div>
                  <div class="security-file-details">
                    <span class="security-hash" title="SHA-256 checksum">
                      🔑 SHA-256: <code>${
                    f.sha256 ? f.sha256.substring(0, 16) + '…' : 'N/A'}</code>
                      ${
                    f.sha256 ?
                        '<button class="copy-hash-btn" data-hash="' + f.sha256 +
                            '" title="Copy full SHA-256">📋</button>' :
                        ''}
                    </span>
                    <span class="security-hash" title="MD5 checksum">
                      🔑 MD5: <code>${f.md5 ? f.md5 : 'N/A'}</code>
                      ${
                    f.md5 ? '<button class="copy-hash-btn" data-hash="' +
                            f.md5 + '" title="Copy MD5">📋</button>' :
                            ''}
                    </span>
                    <span class="security-size">${
                    f.size ? (f.size / 1024).toFixed(1) + ' KB' : ''}</span>
                  </div>
                </div>`;
              })
              .join('')}
          </div>
        </div>
      `;
    }

    // Parse sources
    const sources = this.parseJsonString(manifest.sources);
    const sourcesSection = sources ?
        `
            <div class="modal-section">
                <h3>🔗 Sources</h3>
                <p><strong>Type:</strong> ${
            this.escapeHtml(sources.type || 'N/A')}</p>
                ${
            sources.location && sources.location.origin ?
                `<p><strong>Repository:</strong> <a href="${
                    this.escapeHtml(
                        sources.location
                            .origin)}" target="_blank" style="color: var(--primary-color);">${
                    this.escapeHtml(sources.location.origin)}</a></p>` :
                ''}
            </div>
        ` :
        '';

    // Create screenshots gallery
    let screenshotsSection = '';
    if (manifest.screenshots && Array.isArray(manifest.screenshots) &&
        manifest.screenshots.length > 0) {
      screenshotsSection = `
                <div class="modal-section">
                    <h3>📷 Screenshots</h3>
                    <div class="screenshots-gallery">
                        ${
          manifest.screenshots
              .map((screenshot, index) => {
                const screenshotPath = `${basePath}/static/${screenshot}`;
                return `<img src="${
                    screenshotPath}" alt="Screenshot" class="screenshot-thumb" data-index="${
                    index}" onerror="this.style.display='none'">`;
              })
              .join('')}
                    </div>
                </div>
            `;
    }

    // Store screenshots for lightbox
    this.currentScreenshots = manifest.screenshots ?
        manifest.screenshots.map(s => `${basePath}/static/${s}`) :
        [];

    modalBody.innerHTML = `
            <div class="modal-header">
                <h2>${this.escapeHtml(manifest.name)}</h2>
                <div class="author"><a href="?type=authors&author=${
        encodeURIComponent(
            manifest.author)}" class="author-link" data-author="${
        this.escapeHtml(
            manifest.author)}">${this.escapeHtml(manifest.author)}</a></div>
            </div>
            ${
        manifest.icon ?
            `<img src="${iconPath}" alt="${
                manifest
                    .name}" class="modal-icon" onerror="this.style.display='none'">` :
            ''}
            ${screenshotsSection}
            ${
        manifest.description && manifest.description.trim() ?
            `
            <div class="modal-section">
                <h3>📝 Description</h3>
                <div class="markdown-content">${
                marked.parse(manifest.description)}</div>
            </div>
            ` :
            ''}
            ${
        manifest.changelog && manifest.changelog.trim() ?
            `
            <div class="modal-section">
                <h3>📋 Changelog</h3>
                <div class="markdown-content">${
                marked.parse(manifest.changelog)}</div>
            </div>
            ` :
            ''}
            ${filesSection}
            ${securitySection}
            ${sourcesSection}
        `;

    modal.style.display = 'block';

    // Scroll modal content to top
    const modalContent = modal.querySelector('.modal-content');
    if (modalContent) {
      modalContent.scrollTop = 0;
    }

    console.log('Modal opened successfully');

    // Add click handlers for screenshots after modal is populated
    setTimeout(() => {
      document.querySelectorAll('.screenshot-thumb').forEach(thumb => {
        thumb.addEventListener('click', (e) => {
          const index = parseInt(e.target.dataset.index);
          this.openLightbox(index);
        });
      });

      // Add click handler for author link in modal
      const modalAuthorLink = modalBody.querySelector('.author-link');
      if (modalAuthorLink) {
        modalAuthorLink.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();
          this.navigateToAuthor(modalAuthorLink.dataset.author);
        });
      }

      // Add click handlers for copy-hash buttons
      document.querySelectorAll('.copy-hash-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.preventDefault();
          const hash = btn.dataset.hash;
          navigator.clipboard.writeText(hash).then(() => {
            const original = btn.textContent;
            btn.textContent = '✓';
            setTimeout(() => btn.textContent = original, 1500);
          });
        });
      });
    }, 100);
  }

  openLightbox(index) {
    const lightbox = document.getElementById('lightbox');
    const lightboxImg = document.getElementById('lightboxImg');

    this.currentLightboxIndex = index;
    lightboxImg.src = this.currentScreenshots[index];
    lightbox.style.display = 'flex';

    this.updateLightboxButtons();
  }

  closeLightbox() {
    document.getElementById('lightbox').style.display = 'none';
  }

  nextLightboxImage() {
    if (this.currentLightboxIndex < this.currentScreenshots.length - 1) {
      this.currentLightboxIndex++;
      document.getElementById('lightboxImg').src =
          this.currentScreenshots[this.currentLightboxIndex];
      this.updateLightboxButtons();
    }
  }

  prevLightboxImage() {
    if (this.currentLightboxIndex > 0) {
      this.currentLightboxIndex--;
      document.getElementById('lightboxImg').src =
          this.currentScreenshots[this.currentLightboxIndex];
      this.updateLightboxButtons();
    }
  }

  updateLightboxButtons() {
    const prevBtn = document.getElementById('lightboxPrev');
    const nextBtn = document.getElementById('lightboxNext');
    const counter = document.getElementById('lightboxCounter');

    prevBtn.style.display = this.currentLightboxIndex > 0 ? 'block' : 'none';
    nextBtn.style.display =
        this.currentLightboxIndex < this.currentScreenshots.length - 1 ?
        'block' :
        'none';
    counter.textContent =
        `${this.currentLightboxIndex + 1} / ${this.currentScreenshots.length}`;
  }

  parseJsonString(str) {
    try {
      // Handle Python dict-like strings
      if (typeof str === 'string') {
        // Replace single quotes with double quotes for JSON parsing
        const jsonStr = str.replace(/'/g, '"');
        return JSON.parse(jsonStr);
      }
      return str;
    } catch (e) {
      console.warn('Failed to parse:', str, e);
      return null;
    }
  }

  updatePagination() {
    // Update prev/next buttons
    const prevDisabled = this.currentPage === 0;
    const nextDisabled = this.currentPage >= this.totalPages - 1;

    document.getElementById('prevPage').disabled = prevDisabled;
    document.getElementById('prevPageBottom').disabled = prevDisabled;
    document.getElementById('nextPage').disabled = nextDisabled;
    document.getElementById('nextPageBottom').disabled = nextDisabled;

    // Render page numbers
    this.renderPageNumbers('pageNumbers');
    this.renderPageNumbers('pageNumbersBottom');
  }

  renderPageNumbers(containerId) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';

    const maxButtons = 7;  // Maximum number of page buttons to show
    let startPage = Math.max(0, this.currentPage - Math.floor(maxButtons / 2));
    let endPage = Math.min(this.totalPages - 1, startPage + maxButtons - 1);

    // Adjust startPage if we're near the end
    if (endPage - startPage < maxButtons - 1) {
      startPage = Math.max(0, endPage - maxButtons + 1);
    }

    // First page
    if (startPage > 0) {
      container.appendChild(this.createPageButton(0));
      if (startPage > 1) {
        const ellipsis = document.createElement('span');
        ellipsis.className = 'page-ellipsis';
        ellipsis.textContent = '...';
        container.appendChild(ellipsis);
      }
    }

    // Page buttons
    for (let i = startPage; i <= endPage; i++) {
      container.appendChild(this.createPageButton(i));
    }

    // Last page
    if (endPage < this.totalPages - 1) {
      if (endPage < this.totalPages - 2) {
        const ellipsis = document.createElement('span');
        ellipsis.className = 'page-ellipsis';
        ellipsis.textContent = '...';
        container.appendChild(ellipsis);
      }
      container.appendChild(this.createPageButton(this.totalPages - 1));
    }
  }

  createPageButton(pageIndex) {
    const button = document.createElement('button');
    button.className = 'page-btn';
    button.textContent = pageIndex + 1;

    if (pageIndex === this.currentPage) {
      button.classList.add('active');
    }

    button.addEventListener('click', () => {
      this.currentPage = pageIndex;
      this.loadPage();
    });

    return button;
  }

  showLoading(show) {
    document.getElementById('loading').style.display = show ? 'block' : 'none';
    document.getElementById('content').style.display = show ? 'none' : 'block';
  }

  showError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
  }

  hideError() {
    document.getElementById('error').style.display = 'none';
  }

  escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  authorSlug(author) {
    return (author || '').replace(/[^a-zA-Z0-9_-]/g, '_').toLowerCase();
  }

  async navigateToAuthor(author) {
    // Close modal if open
    document.getElementById('modal').style.display = 'none';

    // Load authors page
    await this.showAuthors();

    // Scroll to the author section & highlight it
    const sectionId = `author-${this.authorSlug(author)}`;
    const section = document.getElementById(sectionId);
    if (section) {
      // Make sure it's not collapsed
      section.classList.remove('collapsed');
      section.scrollIntoView({behavior: 'smooth', block: 'start'});
      section.classList.add('author-highlight');
      setTimeout(() => section.classList.remove('author-highlight'), 2000);
    }

    // Update URL
    const params = new URLSearchParams();
    params.set('type', 'authors');
    params.set('author', author);
    window.history.pushState(
        {type: 'authors', author}, '', `?${params.toString()}`);
  }
}

// Initialize the app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  new LilkaRepository();
});
