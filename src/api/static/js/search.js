/* HRS Data Pipeline - Search variables */

function initializeSearch() {
  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    searchInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') searchVariables();
    });
  }
}

/** Return a valid year number from variable or fallback; empty string if none. */
function getVariableYear(v, fallbackYear) {
  const y = v != null && v.year != null ? Number(v.year) : NaN;
  if (Number.isFinite(y) && y >= 1992 && y <= 2030) return String(Math.floor(y));
  const fy = fallbackYear != null && fallbackYear !== '' ? Number(fallbackYear) : NaN;
  if (Number.isFinite(fy) && fy >= 1992 && fy <= 2030) return String(Math.floor(fy));
  return '';
}

async function searchVariables() {
  const query = document.getElementById('searchInput')?.value?.trim();
  if (!query) {
    alert('Please enter a search query');
    return;
  }

  switchTab('search');

  const year = document.getElementById('search-year-filter')?.value ?? '';
  const source = document.getElementById('search-source-filter')?.value ?? 'hrs_core_codebook';
  const results = document.getElementById('search-results');
  if (!results) return;

  showLoading('search-results', 'Searching...');

  try {
    const params = new URLSearchParams({ q: query });
    if (year) params.append('year', year);
    if (source) params.append('source', source);
    const data = await apiCall(`/search?${params}`);

    if (!data.results || data.results.length === 0) {
      results.innerHTML =
        '<div class="empty-state">No variables found matching your search. Try a different query.</div>';
      return;
    }

    results.innerHTML = `
      <div class="search-summary">
        Found <strong>${data.total ?? 0}</strong> result(s), showing <strong>${data.results.length}</strong>
      </div>
      <div class="variable-list">
        ${data.results
          .map((v) => {
            const varYear = getVariableYear(v, year);
            const displayYear = varYear || (v.year != null ? escapeHtml(String(v.year)) : 'N/A');
            return `
          <div class="variable-item" data-name="${escapeAttr(v.name)}" data-year="${escapeAttr(varYear)}" data-source="${escapeAttr(source)}" onclick="viewVariableFromSearch(this)">
            <div class="variable-header">
              <h4 class="variable-name">${escapeHtml(v.name)}</h4>
              <span class="badge badge-accent">${displayYear}</span>
            </div>
            <div class="variable-meta">
              <span class="meta-tag">Section: ${escapeHtml(v.section || 'N/A')}</span>
              <span class="meta-tag">Level: ${escapeHtml(v.level || 'N/A')}</span>
              <span class="meta-tag">Type: ${escapeHtml(v.type || 'N/A')}</span>
            </div>
            <p class="variable-description">${escapeHtml(v.description || 'No description available')}</p>
          </div>`;
          })
          .join('')}
      </div>
    `;
  } catch (error) {
    console.error('Error searching:', error);
    showError('search-results', `Search failed: ${error.message}. Make sure MongoDB is running and data is loaded.`);
  }
}

window.searchVariables = searchVariables;
