/* HRS Data Pipeline - Post Exit codebook UI (detail panel, lazy-loaded variables) */

var POST_EXIT_VARIABLES_BATCH = 48;
var _postExitVariablesCache = [];
var _postExitVariablesShown = 0;
var _postExitVariablesYear = null;
var _postExitSectionFilter = null; // { code, level } or null for all

async function loadPostExitCodebooks() {
  var yearEl = document.getElementById('post-exit-year-filter');
  var year = yearEl ? yearEl.value : '';
  var list = document.getElementById('post-exit-codebooks-list');
  if (!list) return;

  showLoading('post-exit-codebooks-list', 'Loading post-exit codebooks...');

  try {
    var params = new URLSearchParams();
    if (year) params.set('year', year);
    var codebooks = await apiCall('/post-exit/codebooks?' + params);

    if (codebooks.length === 0) {
      list.innerHTML =
        '<div class="empty-state">No post-exit codebooks found. Load post-exit data into MongoDB (parse and load hrs_post_exit_codebook).</div>';
      return;
    }

    list.innerHTML = codebooks
      .map(function (cb) {
        var yr = Number(cb.year);
        return (
          '<article class="exit-codebook-card card post-exit-card" data-year="' + yr + '" role="button" tabindex="0">' +
          '<div class="exit-codebook-card-inner">' +
          '<span class="post-exit-badge">Post Exit</span>' +
          '<h3 class="card-title">Post Exit ' + escapeHtml(String(cb.year)) + '</h3>' +
          '<p class="card-subtitle">' + (cb.release_type ? escapeHtml(cb.release_type) : 'Year ' + cb.year) + '</p>' +
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

    list.querySelectorAll('.post-exit-card').forEach(function (el) {
      el.addEventListener('click', function () {
        var y = this.getAttribute('data-year');
        if (y) viewPostExitCodebook(parseInt(y, 10));
      });
      el.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          this.click();
        }
      });
    });
  } catch (error) {
    console.error('Error loading post-exit codebooks:', error);
    showError('post-exit-codebooks-list', 'Failed to load post-exit codebooks: ' + error.message + '. Ensure MongoDB is running and post-exit data is loaded.');
  }
}

function buildPostExitSectionCard(s, selected) {
  var count = s.variable_count != null ? s.variable_count : 0;
  var levelLabel = s.level ? escapeHtml(String(s.level)) : '';
  var levelAttr = s.level ? escapeAttr(String(s.level)) : '';
  var sel = selected ? ' exit-section-card-selected' : '';
  return (
    '<div class="exit-section-card post-exit-section-card' + sel + '" role="button" tabindex="0" data-section="' + escapeAttr(s.code) + '" data-level="' + levelAttr + '">' +
    '<span class="exit-section-card-code">' + escapeHtml(s.code) + '</span>' +
    '<span class="exit-section-card-name">' + escapeHtml(s.name) + '</span>' +
    (levelLabel ? '<span class="exit-section-card-level">' + levelLabel + '</span>' : '') +
    '<span class="exit-section-card-badge">' + count + ' var' + (count === 1 ? '' : 's') + '</span>' +
    '</div>'
  );
}

function buildPostExitVariableCard(v, year) {
  var desc = (v.description || '').slice(0, 90);
  var more = (v.description || '').length > 90 ? '\u2026' : '';
  return (
    '<div class="exit-variable-card post-exit-variable-card" data-name="' + escapeAttr(v.name) + '" data-year="' + year + '" role="button" tabindex="0">' +
    '<span class="exit-variable-card-name">' + escapeHtml(v.name) + '</span>' +
    '<span class="exit-variable-card-desc">' + escapeHtml(desc) + more + '</span>' +
    '</div>'
  );
}

function renderPostExitVariablesChunk(container, variables, year, start, count) {
  var end = Math.min(start + count, variables.length);
  for (var i = start; i < end; i++) {
    var div = document.createElement('div');
    div.innerHTML = buildPostExitVariableCard(variables[i], year);
    var card = div.firstElementChild;
    card.addEventListener('click', function () {
      viewPostExitVariable(this);
    });
    card.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        viewPostExitVariable(this);
      }
    });
    container.appendChild(card);
  }
}

function showMorePostExitVariables() {
  var container = document.getElementById('post-exit-variables-list-inner');
  if (!container) return;
  renderPostExitVariablesChunk(container, _postExitVariablesCache, _postExitVariablesYear, _postExitVariablesShown, POST_EXIT_VARIABLES_BATCH);
  _postExitVariablesShown = Math.min(_postExitVariablesShown + POST_EXIT_VARIABLES_BATCH, _postExitVariablesCache.length);
  var wrap = document.getElementById('post-exit-load-more-wrap');
  if (wrap) {
    if (_postExitVariablesShown >= _postExitVariablesCache.length) {
      wrap.classList.add('is-hidden');
    } else {
      var btn = wrap.querySelector('.exit-load-more-btn');
      if (btn) btn.textContent = 'Load more (' + (_postExitVariablesCache.length - _postExitVariablesShown) + ' left)';
    }
  }
}

/** Load variables from API: all (sectionCode/level null) or filtered by section + level. */
async function loadPostExitVariablesFromApi(year, sectionCode, level) {
  var params = new URLSearchParams({ year: String(year), limit: '2000' });
  if (sectionCode) params.set('section', sectionCode);
  if (level) params.set('level', level);
  return apiCall('/post-exit/variables?' + params.toString());
}

/** Fill the Variables tab with a list of variable summaries and optional "All variables" link. */
function fillPostExitVariablesPanel(year, variables, sectionFilter) {
  var variablesEl = document.getElementById('post-exit-variables-content');
  if (!variablesEl) return;
  _postExitVariablesCache = variables;
  _postExitVariablesShown = 0;
  _postExitVariablesYear = year;
  _postExitSectionFilter = sectionFilter || null;

  if (variables.length === 0) {
    variablesEl.innerHTML = '<div class="exit-detail-empty">No variables' + (sectionFilter ? ' in this section' : '') + '</div>';
    return;
  }

  var topBar = '';
  if (sectionFilter) {
    topBar = '<div class="exit-variables-filter-bar"><span class="exit-variables-filter-label">Section ' + escapeHtml(sectionFilter.code) + (sectionFilter.level ? ' \u00b7 ' + escapeHtml(sectionFilter.level) : '') + '</span> <button type="button" class="btn-link exit-show-all-vars-btn" onclick="loadPostExitAllVariables()">All variables</button></div>';
  }

  var listInner = document.createElement('div');
  listInner.className = 'exit-variables-grid';
  listInner.id = 'post-exit-variables-list-inner';
  var initialCount = Math.min(POST_EXIT_VARIABLES_BATCH, variables.length);
  renderPostExitVariablesChunk(listInner, variables, year, 0, initialCount);
  _postExitVariablesShown = initialCount;

  var loadMoreWrap = document.createElement('div');
  loadMoreWrap.className = 'exit-load-more-wrap';
  loadMoreWrap.id = 'post-exit-load-more-wrap';
  if (variables.length > initialCount) {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'exit-load-more-btn';
    btn.textContent = 'Load more (' + (variables.length - initialCount) + ' left)';
    btn.addEventListener('click', showMorePostExitVariables);
    loadMoreWrap.appendChild(btn);
  } else {
    loadMoreWrap.classList.add('is-hidden');
  }

  var variablesWrap = document.createElement('div');
  variablesWrap.className = 'exit-variables-wrap';
  if (topBar) variablesWrap.innerHTML = topBar;
  variablesWrap.appendChild(listInner);
  variablesWrap.appendChild(loadMoreWrap);
  variablesEl.innerHTML = '';
  variablesEl.appendChild(variablesWrap);
}

async function viewPostExitSection(year, sectionCode, level) {
  var variablesEl = document.getElementById('post-exit-variables-content');
  if (variablesEl) variablesEl.innerHTML = '<div class="exit-detail-loading"><div class="exit-detail-loading-spinner"></div><p class="exit-detail-loading-text">Loading section variables\u2026</p></div>';
  setPostExitDetailTab('variables');
  try {
    var params = new URLSearchParams({ year: String(year), limit: '500' });
    if (sectionCode) params.set('section', sectionCode);
    if (level) params.set('level', level);
    var variables = await apiCall('/post-exit/variables?' + params.toString());
    fillPostExitVariablesPanel(year, variables, sectionCode ? { code: sectionCode, level: level || '' } : null);
    updatePostExitSectionSelection(sectionCode ? { code: sectionCode, level: level || '' } : null);
  } catch (e) {
    console.error('Error loading post-exit section variables:', e);
    if (variablesEl) variablesEl.innerHTML = '<div class="exit-detail-error">' + escapeHtml(e.message) + '</div>';
  }
}

async function loadPostExitAllVariables() {
  var year = _postExitVariablesYear || (window.currentCodebookDetail && window.currentCodebookDetail.year);
  if (!year) return;
  var variablesEl = document.getElementById('post-exit-variables-content');
  if (variablesEl) variablesEl.innerHTML = '<div class="exit-detail-loading"><div class="exit-detail-loading-spinner"></div><p class="exit-detail-loading-text">Loading variables\u2026</p></div>';
  try {
    var variables = await loadPostExitVariablesFromApi(year, null, null);
    fillPostExitVariablesPanel(year, variables, null);
    updatePostExitSectionSelection(null);
  } catch (e) {
    console.error('Error loading post-exit variables:', e);
    if (variablesEl) variablesEl.innerHTML = '<div class="exit-detail-error">' + escapeHtml(e.message) + '</div>';
  }
}

function updatePostExitSectionSelection(sectionFilter) {
  var sectionsEl = document.getElementById('post-exit-sections-content');
  if (!sectionsEl) return;
  var grid = sectionsEl.querySelector('.exit-sections-grid');
  if (!grid) return;
  grid.querySelectorAll('.post-exit-section-card').forEach(function (card) {
    var code = card.getAttribute('data-section');
    var lvl = card.getAttribute('data-level') || '';
    var selected = sectionFilter && sectionFilter.code === code && String(sectionFilter.level || '') === lvl;
    card.classList.toggle('exit-section-card-selected', !!selected);
  });
}

function setPostExitDetailTab(tab) {
  var panel = document.getElementById('post-exit-detail-panel');
  if (!panel) return;
  panel.querySelectorAll('.detail-panel-tab').forEach(function (t) {
    t.classList.toggle('active', t.getAttribute('data-detail-tab') === tab);
  });
  var sectionsEl = document.getElementById('post-exit-sections-content');
  var variablesEl = document.getElementById('post-exit-variables-content');
  if (sectionsEl) sectionsEl.style.display = tab === 'sections' ? 'block' : 'none';
  if (variablesEl) variablesEl.style.display = tab === 'variables' ? 'block' : 'none';
}

function closePostExitDetail() {
  var panel = document.getElementById('post-exit-detail-panel');
  if (panel) panel.style.display = 'none';
  if (window.currentCodebookDetail && window.currentCodebookDetail.type === 'post_exit') {
    window.currentCodebookDetail = null;
  }
  _postExitVariablesCache = [];
  _postExitVariablesShown = 0;
  _postExitVariablesYear = null;
}

async function viewPostExitCodebook(year) {
  if (typeof window.currentCodebookDetail === 'undefined') window.currentCodebookDetail = null;
  window.currentCodebookDetail = { type: 'post_exit', year: Number(year) };

  var panel = document.getElementById('post-exit-detail-panel');
  var titleYear = document.getElementById('post-exit-detail-year');
  var sectionsEl = document.getElementById('post-exit-sections-content');
  var variablesEl = document.getElementById('post-exit-variables-content');
  var searchResults = document.getElementById('post-exit-search-results');
  var summaryEl = document.getElementById('post-exit-detail-summary');

  if (!panel || !titleYear || !sectionsEl || !variablesEl) return;

  if (searchResults) searchResults.style.display = 'none';
  if (summaryEl) summaryEl.style.display = 'none';
  panel.style.display = 'block';
  titleYear.textContent = year;
  setPostExitDetailTab('sections');

  var loadingHtml =
    '<div class="exit-detail-loading">' +
    '<div class="exit-detail-loading-spinner"></div>' +
    '<p class="exit-detail-loading-text">Loading sections and variables\u2026</p>' +
    '</div>';
  sectionsEl.innerHTML = loadingHtml;
  variablesEl.innerHTML = '<div class="exit-detail-loading-placeholder"></div>';

  try {
    var sectionsPromise = apiCall('/post-exit/sections?year=' + year);
    var variablesPromise = loadPostExitVariablesFromApi(year, null, null);
    var results = await Promise.all([sectionsPromise, variablesPromise]);
    var sections = results[0];
    var variables = results[1];

    if (summaryEl) {
      summaryEl.textContent = sections.length + ' sections \u00b7 ' + variables.length + ' variables';
      summaryEl.style.display = 'block';
    }

    if (sections.length === 0) {
      sectionsEl.innerHTML = '<div class="exit-detail-empty">No sections</div>';
    } else {
      sectionsEl.innerHTML =
        '<div class="exit-sections-wrap">' +
        '<div class="exit-sections-grid">' +
        sections.map(function (s) { return buildPostExitSectionCard(s, false); }).join('') +
        '</div></div>';
      sectionsEl.querySelectorAll('.post-exit-section-card').forEach(function (card) {
        card.addEventListener('click', function () {
          var code = this.getAttribute('data-section');
          var lvl = this.getAttribute('data-level') || '';
          if (!code) return;
          viewPostExitSection(year, code, lvl || null);
        });
        card.addEventListener('keydown', function (e) {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            this.click();
          }
        });
      });
    }

    fillPostExitVariablesPanel(year, variables, null);
  } catch (error) {
    console.error('Error loading post-exit detail:', error);
    var errHtml = '<div class="exit-detail-error">' + escapeHtml(error.message) + '</div>';
    sectionsEl.innerHTML = errHtml;
    variablesEl.innerHTML = errHtml;
  }
}

function viewPostExitVariable(el) {
  var card = el && el.closest && el.closest('.exit-variable-card');
  if (!card) card = el;
  var name = card && card.getAttribute && card.getAttribute('data-name');
  var yearAttr = card && card.getAttribute && card.getAttribute('data-year');
  var year = yearAttr != null ? yearAttr : (window.currentCodebookDetail && window.currentCodebookDetail.year);
  if (!name) return;
  var y = parseInt(year, 10);
  if (!Number.isFinite(y) || y < 1998 || y > 2030) {
    alert('Select a valid year (1998\u20132022) for post-exit variable details.');
    return;
  }
  if (typeof window.viewPostExitVariableModal === 'function') {
    window.viewPostExitVariableModal(name, y);
  }
}

async function searchPostExitVariables() {
  var inputEl = document.getElementById('post-exit-search-input');
  var q = (inputEl && inputEl.value) ? inputEl.value.trim() : '';
  var yearEl = document.getElementById('post-exit-year-filter');
  var year = (yearEl && yearEl.value) ? yearEl.value : '';
  var resultsContainer = document.getElementById('post-exit-search-results');
  var listEl = document.getElementById('post-exit-search-results-list');
  if (!q) {
    alert('Enter a search term');
    return;
  }
  if (!resultsContainer || !listEl) return;

  showLoading('post-exit-search-results-list', 'Searching...');
  resultsContainer.style.display = 'block';

  try {
    var params = new URLSearchParams({ q: q, limit: '50' });
    if (year) params.set('year', year);
    var data = await apiCall('/post-exit/search?' + params.toString());

    if (!data.results || data.results.length === 0) {
      listEl.innerHTML = '<div class="empty-state">No post-exit variables found for this search.</div>';
      return;
    }

    listEl.innerHTML =
      '<p class="exit-search-summary">Found <strong>' + data.total + '</strong> result(s), showing ' + data.results.length + '</p>' +
      '<div class="variable-list">' +
      data.results
        .map(function (v) {
          return (
            '<div class="variable-item exit-variable-item post-exit-variable-item" data-name="' + escapeAttr(v.name) + '" data-year="' + v.year + '" role="button" tabindex="0">' +
            '<div class="variable-header"><h4 class="variable-name">' + escapeHtml(v.name) + '</h4><span class="badge badge-accent">' + v.year + '</span></div>' +
            '<p class="variable-description">' + escapeHtml(v.description || 'No description') + '</p></div>'
          );
        })
        .join('') +
      '</div>';

    listEl.querySelectorAll('.post-exit-variable-item').forEach(function (item) {
      item.addEventListener('click', function () {
        viewPostExitVariable(this);
      });
      item.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          viewPostExitVariable(this);
        }
      });
    });
  } catch (error) {
    console.error('Error searching post-exit variables:', error);
    listEl.innerHTML = '<div class="error">' + escapeHtml(error.message) + '</div>';
  }
}

function initPostExitSearchInput() {
  var input = document.getElementById('post-exit-search-input');
  if (input) {
    input.addEventListener('keypress', function (e) {
      if (e.key === 'Enter') searchPostExitVariables();
    });
  }
}

window.loadPostExitCodebooks = loadPostExitCodebooks;
window.viewPostExitCodebook = viewPostExitCodebook;
window.viewPostExitSection = viewPostExitSection;
window.loadPostExitAllVariables = loadPostExitAllVariables;
window.setPostExitDetailTab = setPostExitDetailTab;
window.closePostExitDetail = closePostExitDetail;
window.searchPostExitVariables = searchPostExitVariables;
window.viewPostExitVariable = viewPostExitVariable;
window.showMorePostExitVariables = showMorePostExitVariables;
window.initPostExitSearchInput = initPostExitSearchInput;
