/* HRS Data Pipeline - Variable detail modal */

function viewVariableFromSearch(el) {
  const name = el.getAttribute('data-name') || '';
  const yearAttr = el.getAttribute('data-year') || '';
  const sourceAttr = el.getAttribute('data-source') || '';
  let year = parseInt(yearAttr, 10);
  if (!isValidVariableYear(year)) {
    const filterYear = document.getElementById('search-year-filter')?.value || '';
    year = parseInt(filterYear, 10);
  }
  if (!isValidVariableYear(year)) {
    alert('Variable details require a valid year (1992–2030). Please set a year in the search filters and try again.');
    return;
  }
  const source = sourceAttr || document.getElementById('search-source-filter')?.value || 'hrs_core_codebook';
  viewVariable(name, year, source);
}

function isValidVariableYear(year) {
  const y = typeof year === 'number' ? year : parseInt(year, 10);
  return Number.isFinite(y) && y >= 1992 && y <= 2030;
}

async function viewVariable(name, year, source) {
  const modal = document.getElementById('variable-modal');
  const detail = document.getElementById('variable-detail');
  if (!modal || !detail) return;

  if (!name || !isValidVariableYear(year)) {
    alert('Variable details require a valid year (1992–2030). Please set a year in the search filters and try again.');
    return;
  }

  detail.innerHTML = '<div class="loading">Loading variable details...</div>';
  modal.classList.add('is-open');
  modal.style.display = '';

  try {
    const params = new URLSearchParams({ year: String(year), source });
    const variable = await apiCall(`/variables/${encodeURIComponent(name)}?${params}`);

    detail.innerHTML = `
      <h2>${escapeHtml(variable.name)}</h2>
      <div class="variable-detail-section">
        <div class="detail-row">
          <span class="detail-label">Description:</span>
          <span>${escapeHtml(variable.description || 'No description')}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Year:</span>
          <span>${variable.year}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Section:</span>
          <span>${escapeHtml(variable.section || 'N/A')}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Level:</span>
          <span>${escapeHtml(variable.level || 'N/A')}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Type:</span>
          <span>${escapeHtml(variable.type || 'N/A')} (Width: ${variable.width ?? 'N/A'}, Decimals: ${variable.decimals ?? 'N/A'})</span>
        </div>
      </div>
      ${variable.value_codes && variable.value_codes.length > 0 ? `
        <div class="value-codes-section">
          <h3>Value Codes</h3>
          <div class="value-codes-list">
            ${variable.value_codes
              .map(
                (vc) => `
              <div class="value-code-item">
                <strong>${escapeHtml(String(vc.code))}</strong>${vc.frequency ? ` (${vc.frequency.toLocaleString()})` : ''}
                ${vc.label ? `<div class="value-label">${escapeHtml(vc.label)}</div>` : ''}
              </div>
            `
              )
              .join('')}
          </div>
        </div>
      ` : ''}
      ${variable.assignments && variable.assignments.length > 0 ? `
        <div class="variable-detail-section">
          <h3>Assignments</h3>
          <div class="assignment-list">
            ${variable.assignments.map((a) => `<div class="assignment-item">${escapeHtml(a.expression || '')}</div>`).join('')}
          </div>
        </div>
      ` : ''}
      ${variable.references && variable.references.length > 0 ? `
        <div class="variable-detail-section">
          <h3>References</h3>
          <div class="reference-list">
            ${variable.references.map((r) => `<div class="reference-item">${escapeHtml(r.reference || '')}</div>`).join('')}
          </div>
        </div>
      ` : ''}
    `;
  } catch (error) {
    console.error('Error loading variable:', error);
    detail.innerHTML = `<div class="error">Failed to load variable details: ${error.message}</div>`;
  }
}

function isValidExitVariableYear(year) {
  const y = typeof year === 'number' ? year : parseInt(year, 10);
  return Number.isFinite(y) && y >= 1995 && y <= 2030;
}

async function viewExitVariableModal(name, year) {
  const modal = document.getElementById('variable-modal');
  const detail = document.getElementById('variable-detail');
  if (!modal || !detail) return;

  if (!name || !isValidExitVariableYear(year)) {
    alert('Exit variable details require a valid year (1995–2022).');
    return;
  }

  detail.innerHTML = '<div class="loading">Loading exit variable...</div>';
  modal.classList.add('is-open');
  modal.style.display = '';

  try {
    const variable = await apiCall(`/exit/variables/${encodeURIComponent(name)}?year=${year}`);

    detail.innerHTML = `
      <div class="variable-detail-badge exit-detail-badge">Exit variable</div>
      <h2>${escapeHtml(variable.name)}</h2>
      <div class="variable-detail-section">
        <div class="detail-row">
          <span class="detail-label">Description:</span>
          <span>${escapeHtml(variable.description || 'No description')}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Year:</span>
          <span>${variable.year}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Section:</span>
          <span>${escapeHtml(variable.section || 'N/A')}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Level:</span>
          <span>${escapeHtml(variable.level || 'N/A')}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Type:</span>
          <span>${escapeHtml(variable.type || 'N/A')} (Width: ${variable.width ?? 'N/A'}, Decimals: ${variable.decimals ?? 'N/A'})</span>
        </div>
      </div>
      ${variable.value_codes && variable.value_codes.length > 0 ? `
        <div class="value-codes-section">
          <h3>Value Codes</h3>
          <div class="value-codes-list">
            ${variable.value_codes
              .map(
                (vc) => `
              <div class="value-code-item${vc.is_missing ? ' value-code-missing' : ''}">
                <strong>${escapeHtml(String(vc.code))}</strong>${vc.frequency != null ? ` (${Number(vc.frequency).toLocaleString()})` : ''}${vc.is_missing ? ' <span class="value-code-missing-badge">Missing</span>' : ''}
                ${vc.label ? `<div class="value-label">${escapeHtml(vc.label)}</div>` : ''}
              </div>
            `
              )
              .join('')}
          </div>
        </div>
      ` : ''}
    `;
  } catch (error) {
    console.error('Error loading exit variable:', error);
    detail.innerHTML = `<div class="error">Failed to load exit variable: ${error.message}</div>`;
  }
}

async function viewPostExitVariableModal(name, year) {
  const modal = document.getElementById('variable-modal');
  const detail = document.getElementById('variable-detail');
  if (!modal || !detail) return;

  const y = Number(year);
  if (!Number.isFinite(y) || y < 1998 || y > 2030) {
    alert('Post-exit variable details require a valid year (1998–2022).');
    return;
  }

  detail.innerHTML = '<div class="loading">Loading post-exit variable...</div>';
  modal.classList.add('is-open');
  modal.style.display = '';

  try {
    const variable = await apiCall(`/post-exit/variables/${encodeURIComponent(name)}?year=${year}`);

    detail.innerHTML = `
      <div class="variable-detail-badge post-exit-detail-badge">Post-exit variable</div>
      <h2>${escapeHtml(variable.name)}</h2>
      <div class="variable-detail-section">
        <div class="detail-row">
          <span class="detail-label">Description:</span>
          <span>${escapeHtml(variable.description || 'No description')}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Year:</span>
          <span>${variable.year}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Section:</span>
          <span>${escapeHtml(variable.section || 'N/A')}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Level:</span>
          <span>${escapeHtml(variable.level || 'N/A')}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Type:</span>
          <span>${escapeHtml(variable.type || 'N/A')} (Width: ${variable.width ?? 'N/A'}, Decimals: ${variable.decimals ?? 'N/A'})</span>
        </div>
      </div>
      ${variable.value_codes && variable.value_codes.length > 0 ? `
        <div class="value-codes-section">
          <h3>Value Codes</h3>
          <div class="value-codes-list">
            ${variable.value_codes
              .map(
                (vc) => `
              <div class="value-code-item${vc.is_missing ? ' value-code-missing' : ''}">
                <strong>${escapeHtml(String(vc.code))}</strong>${vc.frequency != null ? ` (${Number(vc.frequency).toLocaleString()})` : ''}${vc.is_missing ? ' <span class="value-code-missing-badge">Missing</span>' : ''}
                ${vc.label ? `<div class="value-label">${escapeHtml(vc.label)}</div>` : ''}
              </div>
            `
              )
              .join('')}
          </div>
        </div>
      ` : ''}
    `;
  } catch (error) {
    console.error('Error loading post-exit variable:', error);
    detail.innerHTML = `<div class="error">Failed to load post-exit variable: ${error.message}</div>`;
  }
}

function closeModal() {
  const modal = document.getElementById('variable-modal');
  if (modal) {
    modal.classList.remove('is-open');
    modal.style.display = 'none';
  }
}

window.onclick = function (event) {
  const modal = document.getElementById('variable-modal');
  const codebookModal = document.getElementById('codebook-detail-modal');
  if (event.target === modal) closeModal();
  else if (event.target === codebookModal && typeof closeCodebookDetailModal === 'function') closeCodebookDetailModal();
};

window.viewVariable = viewVariable;
window.viewVariableFromSearch = viewVariableFromSearch;
window.viewExitVariableModal = viewExitVariableModal;
window.viewPostExitVariableModal = viewPostExitVariableModal;
window.closeModal = closeModal;
