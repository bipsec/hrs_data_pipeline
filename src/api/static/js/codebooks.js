/* HRS Data Pipeline - Codebooks (core): detail panel under grid, lazy-loaded variables */

if (typeof window.currentCodebookDetail === 'undefined') window.currentCodebookDetail = null;

var CORE_VARIABLES_BATCH = 60;
var _coreVariablesCache = [];
var _coreVariablesShown = 0;
var _coreVariablesYear = null;
var _coreVariablesSource = null;

async function loadCodebooks() {
  var year = document.getElementById('codebook-year-filter') && document.getElementById('codebook-year-filter').value;
  var source = document.getElementById('codebook-source-filter') && document.getElementById('codebook-source-filter').value;
  var list = document.getElementById('codebooks-list');
  if (!list) return;

  showLoading('codebooks-list', 'Loading codebooks...');

  try {
    var params = new URLSearchParams();
    if (year) params.append('year', year);
    if (source) params.append('source', source);
    var codebooks = await apiCall('/codebooks?' + params);

    if (codebooks.length === 0) {
      list.innerHTML =
        '<div class="empty-state">No codebooks found. Try adjusting your filters or make sure data is loaded in MongoDB.</div>';
      return;
    }

    list.innerHTML = codebooks
      .map(function (cb) {
        var src = escapeAttr(cb.source || '');
        var yr = Number(cb.year);
        return (
          '<div class="card codebook-card" data-year="' + yr + '" data-source="' + src + '" role="button" tabindex="0">' +
          '<div class="card-header">' +
          '<div><h3 class="card-title">' + escapeHtml(cb.source) + '</h3><p class="card-subtitle">Year: ' + cb.year + '</p></div>' +
          (cb.release_type ? '<span class="badge badge-primary">' + escapeHtml(cb.release_type) + '</span>' : '') +
          '</div>' +
          '<div class="card-meta">' +
          '<div class="meta-item"><span class="meta-label">Variables:</span><span>' + (cb.total_variables ?? 0) + '</span></div>' +
          '<div class="meta-item"><span class="meta-label">Sections:</span><span>' + (cb.total_sections ?? 0) + '</span></div>' +
          '<div class="meta-item"><span class="meta-label">Levels:</span><span>' + ((cb.levels || []).join(', ') || 'N/A') + '</span></div>' +
          '</div>' +
          '<div class="card-hint-block"><span class="card-hint-text">Click to view sections and variables</span></div>' +
          '</div>'
        );
      })
      .join('');

    list.querySelectorAll('.codebook-card').forEach(function (el) {
      el.addEventListener('click', function () {
        var y = this.getAttribute('data-year');
        var s = this.getAttribute('data-source') || '';
        if (y) viewCodebook(parseInt(y, 10), s);
      });
      el.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          this.click();
        }
      });
    });
  } catch (error) {
    console.error('Error loading codebooks:', error);
    showError('codebooks-list', 'Failed to load codebooks: ' + error.message + '. Make sure MongoDB is running and data is loaded.');
  }
}

function renderCoreVariablesBatch(container, variables, year, source, startIndex, count) {
  var end = Math.min(startIndex + count, variables.length);
  for (var i = startIndex; i < end; i++) {
    var v = variables[i];
    var desc = (v.description || '').slice(0, 80);
    var more = (v.description || '').length > 80 ? '…' : '';
    var div =
      '<div class="variable-card" data-name="' +
      escapeAttr(v.name) +
      '" data-year="' +
      year +
      '" data-source="' +
      escapeAttr(source) +
      '" onclick="viewCoreVariableInModal(this)">' +
      '<span class="variable-card-name">' +
      escapeHtml(v.name) +
      '</span>' +
      '<span class="variable-card-desc">' +
      escapeHtml(desc) +
      more +
      '</span></div>';
    container.insertAdjacentHTML('beforeend', div);
  }
}

function showMoreCoreVariables() {
  var container = document.getElementById('core-variables-list-inner');
  if (!container) return;
  var next = _coreVariablesShown + CORE_VARIABLES_BATCH;
  renderCoreVariablesBatch(container, _coreVariablesCache, _coreVariablesYear, _coreVariablesSource, _coreVariablesShown, CORE_VARIABLES_BATCH);
  _coreVariablesShown = Math.min(next, _coreVariablesCache.length);
  var loadMoreWrap = document.getElementById('core-load-more-wrap');
  if (loadMoreWrap) {
    if (_coreVariablesShown >= _coreVariablesCache.length) {
      loadMoreWrap.style.display = 'none';
    } else {
      var btn = loadMoreWrap.querySelector('.btn-load-more');
      if (btn) btn.textContent = 'Load more (' + (_coreVariablesCache.length - _coreVariablesShown) + ' remaining)';
    }
  }
}

function setCoreDetailTab(tab) {
  var panel = document.getElementById('core-detail-panel');
  if (!panel) return;
  panel.querySelectorAll('.detail-panel-tab').forEach(function (t) {
    t.classList.toggle('active', t.getAttribute('data-detail-tab') === tab);
  });
  var sectionsEl = document.getElementById('core-sections-content');
  var variablesEl = document.getElementById('core-variables-content');
  if (sectionsEl) sectionsEl.style.display = tab === 'sections' ? 'block' : 'none';
  if (variablesEl) variablesEl.style.display = tab === 'variables' ? 'block' : 'none';
}

function closeCoreDetail() {
  var panel = document.getElementById('core-detail-panel');
  if (panel) panel.style.display = 'none';
  window.currentCodebookDetail = null;
  _coreVariablesCache = [];
  _coreVariablesShown = 0;
  _coreVariablesYear = null;
  _coreVariablesSource = null;
}

async function viewCodebook(year, source) {
  window.currentCodebookDetail = { type: 'core', year: Number(year), source: source || 'hrs_core_codebook' };
  var panel = document.getElementById('core-detail-panel');
  var titleEl = document.getElementById('core-detail-title');
  var sectionsEl = document.getElementById('core-sections-content');
  var variablesEl = document.getElementById('core-variables-content');
  if (!panel || !titleEl || !sectionsEl || !variablesEl) return;

  titleEl.textContent = window.currentCodebookDetail.source + ' – ' + window.currentCodebookDetail.year;
  panel.style.display = 'block';
  setCoreDetailTab('sections');

  sectionsEl.innerHTML = '<div class="loading">Loading sections...</div>';
  variablesEl.innerHTML = '<div class="loading">Loading variables...</div>';

  try {
    var sections = await apiCall(
      '/sections?year=' + window.currentCodebookDetail.year + '&source=' + encodeURIComponent(window.currentCodebookDetail.source)
    );
    sectionsEl.innerHTML =
      sections.length === 0
        ? '<div class="detail-list-wrap"><div class="empty-state">No sections</div></div>'
        : '<div class="detail-list-wrap"><div class="section-cards-grid">' +
          sections
            .map(function (s) {
              var count = s.variable_count != null ? s.variable_count : 0;
              return (
                '<div class="section-card">' +
                '<span class="section-card-code">' + escapeHtml(s.code) + '</span>' +
                '<span class="section-card-name">' + escapeHtml(s.name) + '</span>' +
                '<span class="section-card-count">' + count + ' variables</span>' +
                '</div>'
              );
            })
            .join('') +
          '</div></div>';

    var variables = await apiCall(
      '/variables?year=' + window.currentCodebookDetail.year + '&source=' + encodeURIComponent(window.currentCodebookDetail.source) + '&limit=1000'
    );
    _coreVariablesCache = variables;
    _coreVariablesShown = 0;
    _coreVariablesYear = window.currentCodebookDetail.year;
    _coreVariablesSource = window.currentCodebookDetail.source;

    if (variables.length === 0) {
      variablesEl.innerHTML = '<div class="detail-list-wrap"><div class="empty-state">No variables</div></div>';
    } else {
      var total = variables.length;
      var initialCount = Math.min(CORE_VARIABLES_BATCH, total);
      var listHtml = '';
      for (var i = 0; i < initialCount; i++) {
        var v = variables[i];
        var desc = (v.description || '').slice(0, 80);
        var more = (v.description || '').length > 80 ? '…' : '';
        listHtml +=
          '<div class="variable-card" data-name="' +
          escapeAttr(v.name) +
          '" data-year="' +
          _coreVariablesYear +
          '" data-source="' +
          escapeAttr(_coreVariablesSource) +
          '" onclick="viewCoreVariableInModal(this)">' +
          '<span class="variable-card-name">' +
          escapeHtml(v.name) +
          '</span>' +
          '<span class="variable-card-desc">' +
          escapeHtml(desc) +
          more +
          '</span></div>';
      }
      _coreVariablesShown = initialCount;
      var loadMoreHtml =
        total > initialCount
          ? '<div class="load-more-wrap" id="core-load-more-wrap">' +
            '<button type="button" class="btn-load-more" onclick="showMoreCoreVariables()">Load more (' +
            (total - initialCount) +
            ' remaining)</button>' +
            '</div>'
          : '';
      variablesEl.innerHTML =
        '<div class="detail-list-wrap">' +
        '<div class="variable-cards-grid" id="core-variables-list-inner">' +
        listHtml +
        '</div>' +
        loadMoreHtml +
        '</div>';
    }
  } catch (error) {
    console.error('Error loading codebook detail:', error);
    sectionsEl.innerHTML = '<div class="detail-list-wrap"><div class="error">' + escapeHtml(error.message) + '</div></div>';
    variablesEl.innerHTML = '<div class="detail-list-wrap"><div class="error">' + escapeHtml(error.message) + '</div></div>';
  }
}

function viewCoreVariableInModal(el) {
  var name = el && el.getAttribute && el.getAttribute('data-name');
  var year = el && el.getAttribute && el.getAttribute('data-year');
  var source = el && el.getAttribute && el.getAttribute('data-source');
  if (!source && window.currentCodebookDetail) source = window.currentCodebookDetail.source;
  source = source || 'hrs_core_codebook';
  var y = parseInt(year, 10);
  if (!name || !Number.isFinite(y)) return;
  if (typeof window.viewVariable === 'function') {
    window.viewVariable(name, y, source);
  }
}

window.loadCodebooks = loadCodebooks;
window.viewCodebook = viewCodebook;
window.setCoreDetailTab = setCoreDetailTab;
window.closeCoreDetail = closeCoreDetail;
window.viewCoreVariableInModal = viewCoreVariableInModal;
window.showMoreCoreVariables = showMoreCoreVariables;
