/**
 * HRS Data Pipeline - Categorization module
 * Handles view-by selection (Full, By Section, etc.) and loading/rendering categorization data.
 */

(function () {
  'use strict';

  const CONTAINER_ID = 'categorization-content';
  const BASE_PATH = '/categorization';

  /** View keys and their API response property names */
  const VIEWS = {
    full: { key: 'full', dataKey: null, label: 'Full' },
    sections: { key: 'sections', dataKey: 'sections', label: 'Section' },
    levels: { key: 'levels', dataKey: 'levels', label: 'Level' },
    types: { key: 'types', dataKey: 'types', label: 'Type' },
    'base-names': { key: 'base-names', dataKey: 'base_names', label: 'Base name' },
    special: { key: 'special', dataKey: null, label: 'Special' },
  };

  /** Special-category keys for rendering (order preserved) */
  const SPECIAL_KEYS = [
    'identifiers',
    'derived',
    'with_value_codes',
    'without_value_codes',
    'year_prefixed',
    'no_prefix',
  ];

  const SPECIAL_LABELS = {
    identifiers: 'Identifiers',
    derived: 'Derived',
    with_value_codes: 'With value codes',
    without_value_codes: 'Without value codes',
    year_prefixed: 'Year prefixed',
    no_prefix: 'No prefix',
  };

  function getCurrentView() {
    return (window.HRS_STATE && window.HRS_STATE.currentCatView) || 'full';
  }

  function setCurrentView(viewKey) {
    if (window.HRS_STATE) window.HRS_STATE.currentCatView = viewKey;
  }

  function getFilterValues() {
    return {
      year: document.getElementById('cat-year-filter')?.value ?? '',
      source: document.getElementById('cat-source-filter')?.value ?? '',
      corePeriod: document.getElementById('cat-core-period-filter')?.value ?? '',
    };
  }

  function buildCategorizationUrl(viewKey) {
    const { year, source, corePeriod } = getFilterValues();
    const params = new URLSearchParams();
    if (year) params.set('year', year);
    if (source) params.set('source', source);
    if (corePeriod) params.set('core_period', corePeriod);
    const query = params.toString();
    if (viewKey === 'full') {
      return query ? `${BASE_PATH}?${query}` : BASE_PATH;
    }
    return query ? `${BASE_PATH}/${viewKey}?${query}` : `${BASE_PATH}/${viewKey}`;
  }

  function getContainer() {
    return document.getElementById(CONTAINER_ID);
  }

  function setActiveCard(activeButton) {
    document.querySelectorAll('.btn-cat').forEach((btn) => {
      btn.classList.toggle('active', btn === activeButton);
      btn.setAttribute('aria-pressed', btn === activeButton ? 'true' : 'false');
    });
  }

  /** Initialize view-by card click handlers */
  function initCategorizationSubnav() {
    document.querySelectorAll('.btn-cat').forEach((btn) => {
      btn.addEventListener('click', () => {
        const viewKey = btn.getAttribute('data-cat');
        if (!viewKey) return;
        setActiveCard(btn);
        setCurrentView(viewKey);
      });
    });
  }

  /** Fetch and render categorization; show loading/error in container */
  async function loadCategorization() {
    const container = getContainer();
    if (!container) return;

    const viewKey = getCurrentView();
    showLoading(CONTAINER_ID, 'Loading categorization...');

    try {
      const url = buildCategorizationUrl(viewKey);
      const data = await apiCall(url);
      container.innerHTML = '';

      if (viewKey === 'full') {
        renderFullCategorization(data, container);
      } else if (viewKey === 'special') {
        renderSpecialCategories(data, container);
      } else {
        const config = VIEWS[viewKey];
        const dict = config?.dataKey ? (data[config.dataKey] ?? {}) : {};
        renderCategoryDict(dict, config?.label ?? viewKey, container);
      }
    } catch (err) {
      console.error('Categorization load failed:', err);
      showError(
        CONTAINER_ID,
        `Failed to load categorization: ${err.message}. Ensure MongoDB is running and data is loaded.`
      );
    }
  }

  /** Render a dictionary of categories (sections, levels, types, base_names) */
  function renderCategoryDict(dict, labelKey, container) {
    const entries = Object.entries(dict);
    if (entries.length === 0) {
      container.innerHTML = '<div class="empty-state">No categories in this dimension.</div>';
      return;
    }

    const cards = entries
      .map(([key, cat]) => {
        const count = cat.count ?? 0;
        const years = (cat.years ?? []).slice(0, 8);
        const totalYears = (cat.years ?? []).length;
        const yearsText = totalYears > 8 ? `${years.join(', ')}…` : years.join(', ');
        const names = (cat.variable_names ?? []).slice(0, 15);
        const namesText = names.map((v) => escapeHtml(v)).join(', ');
        const hasMore = (cat.variable_names ?? []).length > 15;
        const details =
          names.length > 0
            ? `
          <details class="cat-details">
            <summary>Sample variables (${(cat.variable_names ?? []).length})</summary>
            <div class="variable-names-list">${namesText}${hasMore ? '…' : ''}</div>
          </details>`
            : '';

        return `
          <div class="card cat-card">
            <div class="card-header">
              <h3 class="card-title">${escapeHtml(key)}</h3>
              <span class="badge badge-primary">${count} vars</span>
            </div>
            <p class="card-description">${escapeHtml(cat.description ?? '')}</p>
            <div class="card-meta">
              <span class="meta-label">Years:</span> ${yearsText}
            </div>
            ${details}
          </div>`;
      })
      .join('');

    container.innerHTML = `
      <div class="cat-summary">${entries.length} ${labelKey.toLowerCase()}(s)</div>
      <div class="cards-grid cat-cards">${cards}</div>`;
  }

  /** Render special categories (identifiers, derived, etc.) */
  function renderSpecialCategories(data, container) {
    const cards = SPECIAL_KEYS.map((key) => {
      const cat = data[key];
      if (!cat) return '';
      const count = cat.count ?? 0;
      const names = (cat.variable_names ?? []).slice(0, 20);
      const namesText = names.map((v) => escapeHtml(v)).join(', ');
      const hasMore = (cat.variable_names ?? []).length > 20;
      const label = SPECIAL_LABELS[key] ?? key;
      const details =
        names.length > 0
          ? `
        <details class="cat-details">
          <summary>Sample (${(cat.variable_names ?? []).length})</summary>
          <div class="variable-names-list">${namesText}${hasMore ? '…' : ''}</div>
        </details>`
          : '';

      return `
        <div class="card cat-card">
          <div class="card-header">
            <h3 class="card-title">${escapeHtml(label)}</h3>
            <span class="badge badge-primary">${count} vars</span>
          </div>
          <p class="card-description">${escapeHtml(cat.description ?? '')}</p>
          ${details}
        </div>`;
    }).join('');

    container.innerHTML = `<div class="cards-grid cat-cards">${cards}</div>`;
  }

  /** Render full categorization (summary + by_section + special_categories) */
  function renderFullCategorization(data, container) {
    const totalVars = data.total_variables ?? 0;
    const totalYears = data.total_years ?? 0;
    const yearsCovered = (data.years_covered ?? []).join(', ');

    let html = `
      <div class="cat-full-summary">
        <div class="stat-card stat-inline">
          <span class="stat-value">${totalVars}</span>
          <span class="stat-label">Total variables</span>
        </div>
        <div class="stat-card stat-inline">
          <span class="stat-value">${totalYears}</span>
          <span class="stat-label">Years covered</span>
        </div>
        <div class="stat-card stat-inline">
          <span class="stat-value" style="font-size:1rem;">${yearsCovered || 'N/A'}</span>
          <span class="stat-label">Years</span>
        </div>
      </div>
      <div class="cat-full-sections">
        <h3>By section</h3>
        ${Object.keys(data.by_section ?? {}).length === 0 ? '<p class="empty-state">No sections</p>' : ''}
      </div>`;

    const bySection = data.by_section ?? {};
    if (Object.keys(bySection).length > 0) {
      html += '<div class="cards-grid cat-cards">';
      for (const [key, cat] of Object.entries(bySection)) {
        const count = cat.count ?? 0;
        const names = (cat.variable_names ?? []).slice(0, 20);
        const namesText = names.map((v) => escapeHtml(v)).join(', ');
        const hasMore = (cat.variable_names ?? []).length > 20;
        html += `
          <div class="card cat-card">
            <div class="card-header"><h3 class="card-title">${escapeHtml(key)}</h3><span class="badge badge-primary">${count}</span></div>
            <p class="card-description">${escapeHtml(cat.description ?? '')}</p>
            <details class="cat-details"><summary>Variables</summary><div class="variable-names-list">${namesText}${hasMore ? '…' : ''}</div></details>
          </div>`;
      }
      html += '</div>';
    }

    html += '<h3 class="mt-4">Special categories</h3><div class="cards-grid cat-cards">';
    const sc = data.special_categories ?? {};
    for (const key of SPECIAL_KEYS) {
      const cat = sc[key];
      if (!cat) continue;
      const label = SPECIAL_LABELS[key] ?? key;
      const count = cat.count ?? 0;
      const names = (cat.variable_names ?? []).slice(0, 15);
      const namesText = names.map((v) => escapeHtml(v)).join(', ');
      const hasMore = (cat.variable_names ?? []).length > 15;
      html += `
        <div class="card cat-card">
          <div class="card-header"><h3 class="card-title">${escapeHtml(label)}</h3><span class="badge badge-primary">${count}</span></div>
          <p class="card-description">${escapeHtml(cat.description ?? '')}</p>
          <details class="cat-details"><summary>Sample</summary><div class="variable-names-list">${namesText}${hasMore ? '…' : ''}</div></details>
        </div>`;
    }
    html += '</div>';

    container.innerHTML = html;
  }

  window.initCategorizationSubnav = initCategorizationSubnav;
  window.loadCategorization = loadCategorization;
})();
