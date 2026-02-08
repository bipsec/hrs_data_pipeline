/* HRS Data Pipeline - Dashboard */

async function loadDashboard() {
  const statCodebooks = document.getElementById('stat-codebooks');
  const statVariables = document.getElementById('stat-variables');
  const statSections = document.getElementById('stat-sections');
  const statYears = document.getElementById('stat-years');
  if (statCodebooks) statCodebooks.textContent = '...';
  if (statVariables) statVariables.textContent = '...';
  if (statSections) statSections.textContent = '...';
  if (statYears) statYears.textContent = '...';
  showLoading('years-list', 'Loading years...');
  showLoading('sources-list', 'Loading sources...');

  try {
    const stats = await apiCall('/stats');
    if (statCodebooks) statCodebooks.textContent = stats.total_codebooks ?? 0;
    if (statVariables) statVariables.textContent = stats.total_variables ?? 0;
    if (statSections) statSections.textContent = stats.total_sections ?? 0;
    if (statYears) statYears.textContent = stats.year_range ?? 'N/A';

    const yearsEl = document.getElementById('years-list');
    if (stats.years && stats.years.length > 0) {
      renderYears(stats.years);
    } else if (yearsEl) {
      yearsEl.innerHTML = '<p class="empty-state">No years available</p>';
    }

    const sourcesEl = document.getElementById('sources-list');
    if (stats.sources && stats.sources.length > 0) {
      renderSources(stats.sources);
    } else if (sourcesEl) {
      sourcesEl.innerHTML = '<p class="empty-state">No sources available</p>';
    }
  } catch (error) {
    console.error('Error loading dashboard:', error);
    showError('years-list', `Failed to load dashboard: ${error.message}. Make sure MongoDB is running and data is loaded.`);
    if (statCodebooks) statCodebooks.textContent = 'Error';
    if (statVariables) statVariables.textContent = 'Error';
    if (statSections) statSections.textContent = 'Error';
    if (statYears) statYears.textContent = 'Error';
  }
}

function renderYears(years) {
  const container = document.getElementById('years-list');
  if (!container) return;
  if (!years || years.length === 0) {
    container.innerHTML = '<p class="empty-state">No years available</p>';
    return;
  }
  container.innerHTML = years
    .map((y) => `<div class="year-badge" onclick="filterByYear(${y})">${y}</div>`)
    .join('');
}

function renderSources(sources) {
  const container = document.getElementById('sources-list');
  if (!container) return;
  if (!sources || sources.length === 0) {
    container.innerHTML = '<p class="empty-state">No sources available</p>';
    return;
  }
  container.innerHTML = sources.map((s) => `<div class="source-badge">${escapeHtml(s)}</div>`).join('');
}
