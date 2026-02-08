/* HRS Data Pipeline - Exit codebook UI (detail panel, lazy-loaded variables) */

var EXIT_VARIABLES_BATCH = 48;
var _exitVariablesCache = [];
var _exitVariablesShown = 0;
var _exitVariablesYear = null;

async function loadExitCodebooks() {
  var yearEl = document.getElementById('exit-year-filter');
  var year = yearEl ? yearEl.value : '';
  var list = document.getElementById('exit-codebooks-list');
  if (!list) return;

  showLoading('exit-codebooks-list', 'Loading exit codebooks...');

  try {
    var params = new URLSearchParams();
    if (year) params.set('year', year);
    var codebooks = await apiCall('/exit/codebooks?' + params);

    if (codebooks.length === 0) {
      list.innerHTML =
        '<div class="empty-state">No exit codebooks found. Load exit data into MongoDB (parse and load hrs_exit_codebook).</div>';
      return;
    }

    list.innerHTML = codebooks
      .map(function (cb) {
        var yr = Number(cb.year);
        return (
          '<article class="exit-codebook-card card exit-card" data-year="' + yr + '" role="button" tabindex="0">' +
          '<div class="exit-codebook-card-inner">' +
          '<span class="exit-badge">Exit</span>' +
          '<h3 class="card-title">' + escapeHtml(cb.source) + '</h3>' +
          '<p class="card-subtitle">Year ' + cb.year + '</p>' +
          '<div class="exit-codebook-meta">' +
          '<span class="exit-meta-pill"><span class="exit-meta-num">' + (cb.total_variables ?? 0) + '</span> variables</span>' +
          '<span class="exit-meta-pill"><span class="exit-meta-num">' + (cb.total_sections ?? 0) + '</span> sections</span>' +
          (cb.release_type ? '<span class="badge badge-primary">' + escapeHtml(cb.release_type) + '</span>' : '') +
          '</div>' +
          '<p class="exit-codebook-hint">Click to view sections and variables</p>' +
          '</div></article>'
        );
      })
      .join('');

    list.querySelectorAll('.exit-codebook-card').forEach(function (el) {
      el.addEventListener('click', function () {
        var y = this.getAttribute('data-year');
        if (y) viewExitCodebook(parseInt(y, 10));
      });
      el.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          this.click();
        }
      });
    });
  } catch (error) {
    console.error('Error loading exit codebooks:', error);
    showError('exit-codebooks-list', 'Failed to load exit codebooks: ' + error.message + '. Ensure MongoDB is running and exit data is loaded.');
  }
}

function buildSectionCard(s) {
  var count = s.variable_count != null ? s.variable_count : 0;
  return (
    '<div class="exit-section-card" role="button" tabindex="0">' +
    '<span class="exit-section-card-code">' + escapeHtml(s.code) + '</span>' +
    '<span class="exit-section-card-name">' + escapeHtml(s.name) + '</span>' +
    '<span class="exit-section-card-badge">' + count + ' var' + (count === 1 ? '' : 's') + '</span>' +
    '</div>'
  );
}

function buildVariableCard(v, year) {
  var desc = (v.description || '').slice(0, 90);
  var more = (v.description || '').length > 90 ? '…' : '';
  return (
    '<div class="exit-variable-card" data-name="' + escapeAttr(v.name) + '" data-year="' + year + '" role="button" tabindex="0">' +
    '<span class="exit-variable-card-name">' + escapeHtml(v.name) + '</span>' +
    '<span class="exit-variable-card-desc">' + escapeHtml(desc) + more + '</span>' +
    '</div>'
  );
}

function renderExitVariablesChunk(container, variables, year, start, count) {
  var end = Math.min(start + count, variables.length);
  for (var i = start; i < end; i++) {
    var div = document.createElement('div');
    div.innerHTML = buildVariableCard(variables[i], year);
    var card = div.firstElementChild;
    card.addEventListener('click', function () {
      viewExitVariable(this);
    });
    card.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        viewExitVariable(this);
      }
    });
    container.appendChild(card);
  }
}

function showMoreExitVariables() {
  var container = document.getElementById('exit-variables-list-inner');
  if (!container) return;
  renderExitVariablesChunk(container, _exitVariablesCache, _exitVariablesYear, _exitVariablesShown, EXIT_VARIABLES_BATCH);
  _exitVariablesShown = Math.min(_exitVariablesShown + EXIT_VARIABLES_BATCH, _exitVariablesCache.length);
  var wrap = document.getElementById('exit-load-more-wrap');
  if (wrap) {
    if (_exitVariablesShown >= _exitVariablesCache.length) {
      wrap.classList.add('is-hidden');
    } else {
      var btn = wrap.querySelector('.exit-load-more-btn');
      if (btn) btn.textContent = 'Load more (' + (_exitVariablesCache.length - _exitVariablesShown) + ' left)';
    }
  }
}

function setExitDetailTab(tab) {
  var panel = document.getElementById('exit-detail-panel');
  if (!panel) return;
  panel.querySelectorAll('.detail-panel-tab').forEach(function (t) {
    t.classList.toggle('active', t.getAttribute('data-detail-tab') === tab);
  });
  var sectionsEl = document.getElementById('exit-sections-content');
  var variablesEl = document.getElementById('exit-variables-content');
  if (sectionsEl) sectionsEl.style.display = tab === 'sections' ? 'block' : 'none';
  if (variablesEl) variablesEl.style.display = tab === 'variables' ? 'block' : 'none';
}

function closeExitDetail() {
  var panel = document.getElementById('exit-detail-panel');
  if (panel) panel.style.display = 'none';
  window.currentCodebookDetail = null;
  _exitVariablesCache = [];
  _exitVariablesShown = 0;
  _exitVariablesYear = null;
}

async function viewExitCodebook(year) {
  if (typeof window.currentCodebookDetail === 'undefined') window.currentCodebookDetail = null;
  window.currentCodebookDetail = { type: 'exit', year: Number(year) };

  var panel = document.getElementById('exit-detail-panel');
  var titleYear = document.getElementById('exit-detail-year');
  var sectionsEl = document.getElementById('exit-sections-content');
  var variablesEl = document.getElementById('exit-variables-content');
  var searchResults = document.getElementById('exit-search-results');
  var summaryEl = document.getElementById('exit-detail-summary');

  if (!panel || !titleYear || !sectionsEl || !variablesEl) return;

  if (searchResults) searchResults.style.display = 'none';
  if (summaryEl) summaryEl.style.display = 'none';
  panel.style.display = 'block';
  titleYear.textContent = year;
  setExitDetailTab('sections');

  /* Single loading state for both sections and variables */
  var loadingHtml =
    '<div class="exit-detail-loading">' +
    '<div class="exit-detail-loading-spinner"></div>' +
    '<p class="exit-detail-loading-text">Loading sections and variables…</p>' +
    '</div>';
  sectionsEl.innerHTML = loadingHtml;
  variablesEl.innerHTML = '<div class="exit-detail-loading-placeholder"></div>';

  try {
    var sectionsPromise = apiCall('/exit/sections?year=' + year);
    var variablesPromise = apiCall('/exit/variables?year=' + year + '&limit=1000');
    var results = await Promise.all([sectionsPromise, variablesPromise]);
    var sections = results[0];
    var variables = results[1];

    /* Summary strip */
    if (summaryEl) {
      summaryEl.textContent = sections.length + ' sections · ' + variables.length + ' variables';
      summaryEl.style.display = 'block';
    }

    /* Sections */
    if (sections.length === 0) {
      sectionsEl.innerHTML = '<div class="exit-detail-empty">No sections</div>';
    } else {
      sectionsEl.innerHTML =
        '<div class="exit-sections-wrap">' +
        '<div class="exit-sections-grid">' +
        sections.map(buildSectionCard).join('') +
        '</div></div>';
    }

    /* Variables */
    _exitVariablesCache = variables;
    _exitVariablesShown = 0;
    _exitVariablesYear = year;

    if (variables.length === 0) {
      variablesEl.innerHTML = '<div class="exit-detail-empty">No variables</div>';
    } else {
      var initialCount = Math.min(EXIT_VARIABLES_BATCH, variables.length);
      var listInner = document.createElement('div');
      listInner.className = 'exit-variables-grid';
      listInner.id = 'exit-variables-list-inner';
      renderExitVariablesChunk(listInner, variables, year, 0, initialCount);
      _exitVariablesShown = initialCount;

      var loadMoreWrap = document.createElement('div');
      loadMoreWrap.className = 'exit-load-more-wrap';
      loadMoreWrap.id = 'exit-load-more-wrap';
      if (variables.length > initialCount) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'exit-load-more-btn';
        btn.textContent = 'Load more (' + (variables.length - initialCount) + ' left)';
        btn.addEventListener('click', showMoreExitVariables);
        loadMoreWrap.appendChild(btn);
      } else {
        loadMoreWrap.classList.add('is-hidden');
      }

      var variablesWrap = document.createElement('div');
      variablesWrap.className = 'exit-variables-wrap';
      variablesWrap.appendChild(listInner);
      variablesWrap.appendChild(loadMoreWrap);
      variablesEl.innerHTML = '';
      variablesEl.appendChild(variablesWrap);
    }
  } catch (error) {
    console.error('Error loading exit detail:', error);
    var errHtml = '<div class="exit-detail-error">' + escapeHtml(error.message) + '</div>';
    sectionsEl.innerHTML = errHtml;
    variablesEl.innerHTML = errHtml;
  }
}

function viewExitVariable(el) {
  var name = el && el.getAttribute && el.getAttribute('data-name');
  var yearAttr = el && el.getAttribute && el.getAttribute('data-year');
  var year = yearAttr != null ? yearAttr : (window.currentCodebookDetail && window.currentCodebookDetail.year);
  if (!name) return;
  var y = parseInt(year, 10);
  if (!Number.isFinite(y) || y < 1995 || y > 2030) {
    alert('Select a valid year (1995–2022) for exit variable details.');
    return;
  }
  if (typeof window.viewExitVariableModal === 'function') {
    window.viewExitVariableModal(name, y);
  }
}

async function searchExitVariables() {
  var inputEl = document.getElementById('exit-search-input');
  var q = (inputEl && inputEl.value) ? inputEl.value.trim() : '';
  var yearEl = document.getElementById('exit-year-filter');
  var year = (yearEl && yearEl.value) ? yearEl.value : '';
  var resultsContainer = document.getElementById('exit-search-results');
  var listEl = document.getElementById('exit-search-results-list');
  if (!q) {
    alert('Enter a search term');
    return;
  }
  if (!resultsContainer || !listEl) return;

  showLoading('exit-search-results-list', 'Searching...');
  resultsContainer.style.display = 'block';

  try {
    var params = new URLSearchParams({ q: q, limit: '50' });
    if (year) params.set('year', year);
    var data = await apiCall('/exit/search?' + params.toString());

    if (!data.results || data.results.length === 0) {
      listEl.innerHTML = '<div class="empty-state">No exit variables found for this search.</div>';
      return;
    }

    listEl.innerHTML =
      '<p class="exit-search-summary">Found <strong>' + data.total + '</strong> result(s), showing ' + data.results.length + '</p>' +
      '<div class="variable-list">' +
      data.results
        .map(function (v) {
          return (
            '<div class="variable-item exit-variable-item" data-name="' + escapeAttr(v.name) + '" data-year="' + v.year + '" role="button" tabindex="0">' +
            '<div class="variable-header"><h4 class="variable-name">' + escapeHtml(v.name) + '</h4><span class="badge badge-accent">' + v.year + '</span></div>' +
            '<p class="variable-description">' + escapeHtml(v.description || 'No description') + '</p></div>'
          );
        })
        .join('') +
      '</div>';

    listEl.querySelectorAll('.exit-variable-item').forEach(function (item) {
      item.addEventListener('click', function () {
        viewExitVariable(this);
      });
      item.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          viewExitVariable(this);
        }
      });
    });
  } catch (error) {
    console.error('Error searching exit variables:', error);
    listEl.innerHTML = '<div class="error">' + escapeHtml(error.message) + '</div>';
  }
}

function initExitSearchInput() {
  var input = document.getElementById('exit-search-input');
  if (input) {
    input.addEventListener('keypress', function (e) {
      if (e.key === 'Enter') searchExitVariables();
    });
  }
}

window.loadExitCodebooks = loadExitCodebooks;
window.viewExitCodebook = viewExitCodebook;
window.setExitDetailTab = setExitDetailTab;
window.closeExitDetail = closeExitDetail;
window.searchExitVariables = searchExitVariables;
window.viewExitVariable = viewExitVariable;
window.showMoreExitVariables = showMoreExitVariables;
window.initExitSearchInput = initExitSearchInput;
