/* HRS Data Pipeline - Sections */

async function loadSections() {
  const year = document.getElementById('section-year-filter')?.value ?? '';
  const source = document.getElementById('section-source-filter')?.value ?? 'hrs_core_codebook';

  if (!year) {
    alert('Please select a year');
    return;
  }

  const list = document.getElementById('sections-list');
  if (!list) return;

  showLoading('sections-list', 'Loading sections...');

  try {
    const params = new URLSearchParams({ year, source });
    const sections = await apiCall(`/sections?${params}`);

    if (sections.length === 0) {
      list.innerHTML = '<div class="empty-state">No sections found for the selected year and source.</div>';
      return;
    }

    list.innerHTML = sections
      .map(
        (sec) => `
      <div class="card">
        <div class="card-header">
          <div>
            <h3 class="card-title">Section ${escapeHtml(sec.code)}: ${escapeHtml(sec.name)}</h3>
            <p class="card-subtitle">Level: ${escapeHtml(sec.level || 'N/A')}</p>
          </div>
          <span class="badge badge-primary">${sec.variable_count ?? 0} vars</span>
        </div>
        <div class="card-meta">
          <div class="meta-item">
            <span class="meta-label">Variables:</span>
            <span>${(sec.variables || []).slice(0, 10).map((v) => escapeHtml(v)).join(', ')}${(sec.variables || []).length > 10 ? '...' : ''}</span>
          </div>
        </div>
      </div>
    `
      )
      .join('');
  } catch (error) {
    console.error('Error loading sections:', error);
    showError('sections-list', `Failed to load sections: ${error.message}. Make sure MongoDB is running and data is loaded.`);
  }
}

window.loadSections = loadSections;
