/* HRS Data Pipeline - Utility endpoints UI */

async function utilExtractBaseName() {
  const input = document.getElementById('util-extract-input')?.value?.trim();
  const resultEl = document.getElementById('util-extract-result');
  if (!resultEl) return;
  if (!input) {
    resultEl.innerHTML = '<span class="util-error">Enter a variable name</span>';
    return;
  }
  try {
    const data = await apiCall(`/utils/extract-base-name?variable_name=${encodeURIComponent(input)}`);
    resultEl.innerHTML = `<div class="util-success"><strong>Base name:</strong> ${escapeHtml(data.base_name || '')}${data.prefix ? ` <span class="meta-tag">Prefix: ${escapeHtml(data.prefix)}</span>` : ''}</div>`;
  } catch (e) {
    resultEl.innerHTML = `<span class="util-error">${escapeHtml(e.message)}</span>`;
  }
}

async function utilConstructName() {
  const base = document.getElementById('util-construct-base')?.value?.trim();
  const year = document.getElementById('util-construct-year')?.value?.trim();
  const resultEl = document.getElementById('util-construct-result');
  if (!resultEl) return;
  if (!base || !year) {
    resultEl.innerHTML = '<span class="util-error">Enter base name and year</span>';
    return;
  }
  try {
    const data = await apiCall(`/utils/construct-variable-name?base_name=${encodeURIComponent(base)}&year=${encodeURIComponent(year)}`);
    resultEl.innerHTML = `<div class="util-success"><strong>Variable name:</strong> ${escapeHtml(data.variable_name || '')} <span class="meta-tag">Prefix: ${escapeHtml(data.prefix || '')}</span></div>`;
  } catch (e) {
    resultEl.innerHTML = `<span class="util-error">${escapeHtml(e.message)}</span>`;
  }
}

async function utilYearPrefix() {
  const year = document.getElementById('util-prefix-year')?.value?.trim();
  const resultEl = document.getElementById('util-prefix-result');
  if (!resultEl) return;
  if (!year) {
    resultEl.innerHTML = '<span class="util-error">Enter a year</span>';
    return;
  }
  try {
    const data = await apiCall(`/utils/year-prefix?year=${encodeURIComponent(year)}`);
    resultEl.innerHTML = `<div class="util-success"><strong>Prefix:</strong> ${escapeHtml(data.prefix || '')} <span class="meta-tag">Wave: ${data.wave ?? ''}</span></div>`;
  } catch (e) {
    resultEl.innerHTML = `<span class="util-error">${escapeHtml(e.message)}</span>`;
  }
}

async function utilPrefixYear() {
  const prefix = document.getElementById('util-year-prefix')?.value?.trim();
  const resultEl = document.getElementById('util-year-result');
  if (!resultEl) return;
  if (!prefix) {
    resultEl.innerHTML = '<span class="util-error">Enter a prefix</span>';
    return;
  }
  try {
    const data = await apiCall(`/utils/prefix-year?prefix=${encodeURIComponent(prefix)}`);
    resultEl.innerHTML = `<div class="util-success"><strong>Year:</strong> ${data.year ?? ''} <span class="meta-tag">Wave: ${data.wave ?? ''}</span></div>`;
  } catch (e) {
    resultEl.innerHTML = `<span class="util-error">${escapeHtml(e.message)}</span>`;
  }
}

window.utilExtractBaseName = utilExtractBaseName;
window.utilConstructName = utilConstructName;
window.utilYearPrefix = utilYearPrefix;
window.utilPrefixYear = utilPrefixYear;
