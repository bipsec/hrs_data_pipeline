// HRS Data Pipeline - Application Logic
// Connects to FastAPI backend

// ===== CONFIGURATION =====
const API_BASE = window.location.origin;

// ===== STATE MANAGEMENT =====
let currentTab = 'dashboard';
let searchQuery = '';

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing HRS Data Pipeline UI...');
    initializeTabs();
    initializeSearch();
    loadDashboard();
    loadYearFilters();
    loadSourceFilters();
});

// ===== UTILITY FUNCTIONS =====
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error(`API call failed for ${endpoint}:`, error);
        throw error;
    }
}

function showLoading(elementId, message = 'Loading...') {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `<div class="loading">${message}</div>`;
    }
}

function showError(elementId, message) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `<div class="error">${message}</div>`;
    }
}

// ===== TAB NAVIGATION =====
function initializeTabs() {
    const tabs = document.querySelectorAll('.tab');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;
            switchTab(tabName);
        });
    });
}

function switchTab(tabName) {
    // Update active tab button
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
        tab.setAttribute('aria-selected', 'false');
    });
    const activeTab = document.querySelector(`[data-tab="${tabName}"]`);
    if (activeTab) {
        activeTab.classList.add('active');
        activeTab.setAttribute('aria-selected', 'true');
    }
    
    // Update active content section
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.remove('active');
    });
    const activeSection = document.getElementById(tabName);
    if (activeSection) {
        activeSection.classList.add('active');
    }
    
    currentTab = tabName;
    
    // Load data when switching tabs
    if (tabName === 'dashboard') {
        loadDashboard();
    } else if (tabName === 'codebooks') {
        loadCodebooks();
    }
}

// ===== SEARCH FUNCTIONALITY =====
function initializeSearch() {
    const searchInput = document.getElementById('searchInput');
    
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                searchVariables();
            }
        });
    }
}

// ===== DASHBOARD =====
async function loadDashboard() {
    console.log('Loading dashboard...');
    
    // Show loading state
    document.getElementById('stat-codebooks').textContent = '...';
    document.getElementById('stat-variables').textContent = '...';
    document.getElementById('stat-sections').textContent = '...';
    document.getElementById('stat-years').textContent = '...';
    showLoading('years-list', 'Loading years...');
    showLoading('sources-list', 'Loading sources...');
    
    try {
        // Load stats
        const stats = await apiCall('/stats');
        console.log('Stats loaded:', stats);
        
        document.getElementById('stat-codebooks').textContent = stats.total_codebooks || 0;
        document.getElementById('stat-variables').textContent = stats.total_variables || 0;
        document.getElementById('stat-sections').textContent = stats.total_sections || 0;
        document.getElementById('stat-years').textContent = stats.year_range || 'N/A';
        
        // Load years and sources from stats (they're included)
        if (stats.years && stats.years.length > 0) {
            renderYears(stats.years);
        } else {
            document.getElementById('years-list').innerHTML = '<p class="empty-state">No years available</p>';
        }
        
        if (stats.sources && stats.sources.length > 0) {
            renderSources(stats.sources);
        } else {
            document.getElementById('sources-list').innerHTML = '<p class="empty-state">No sources available</p>';
        }
        
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showError('dashboard', `Failed to load dashboard: ${error.message}. Make sure MongoDB is running and data is loaded.`);
        document.getElementById('stat-codebooks').textContent = 'Error';
        document.getElementById('stat-variables').textContent = 'Error';
        document.getElementById('stat-sections').textContent = 'Error';
        document.getElementById('stat-years').textContent = 'Error';
    }
}

function renderYears(years) {
    const container = document.getElementById('years-list');
    if (!container) return;
    
    if (!years || years.length === 0) {
        container.innerHTML = '<p class="empty-state">No years available</p>';
        return;
    }
    
    container.innerHTML = years.map(year => 
        `<div class="year-badge" onclick="filterByYear(${year})">${year}</div>`
    ).join('');
}

function renderSources(sources) {
    const container = document.getElementById('sources-list');
    if (!container) return;
    
    if (!sources || sources.length === 0) {
        container.innerHTML = '<p class="empty-state">No sources available</p>';
        return;
    }
    
    container.innerHTML = sources.map(source => 
        `<div class="source-badge">${source}</div>`
    ).join('');
}

// ===== YEAR AND SOURCE FILTERS =====
async function loadYearFilters() {
    try {
        const data = await apiCall('/years');
        const filters = ['codebook-year-filter', 'search-year-filter', 'section-year-filter'];
        
        filters.forEach(filterId => {
            const select = document.getElementById(filterId);
            if (select && data.years) {
                select.innerHTML = '<option value="">All Years</option>' + 
                    data.years.map(year => `<option value="${year}">${year}</option>`).join('');
            }
        });
    } catch (error) {
        console.error('Error loading years:', error);
    }
}

async function loadSourceFilters() {
    try {
        const data = await apiCall('/years');
        const filters = ['codebook-source-filter', 'search-source-filter', 'section-source-filter'];
        
        filters.forEach(filterId => {
            const select = document.getElementById(filterId);
            if (select && data.sources) {
                select.innerHTML = '<option value="">All Sources</option>' + 
                    data.sources.map(source => `<option value="${source}">${source}</option>`).join('');
            }
        });
    } catch (error) {
        console.error('Error loading sources:', error);
    }
}

// ===== CODEBOOKS =====
async function loadCodebooks() {
    const year = document.getElementById('codebook-year-filter')?.value || '';
    const source = document.getElementById('codebook-source-filter')?.value || '';
    
    const list = document.getElementById('codebooks-list');
    if (!list) return;
    
    showLoading('codebooks-list', 'Loading codebooks...');
    
    try {
        const params = new URLSearchParams();
        if (year) params.append('year', year);
        if (source) params.append('source', source);
        
        const codebooks = await apiCall(`/codebooks?${params}`);
        console.log('Codebooks loaded:', codebooks);
        
        if (codebooks.length === 0) {
            list.innerHTML = '<div class="empty-state">No codebooks found. Try adjusting your filters or make sure data is loaded in MongoDB.</div>';
            return;
        }
        
        list.innerHTML = codebooks.map(cb => `
            <div class="card" onclick="viewCodebook(${cb.year}, '${cb.source}')">
                <div class="card-header">
                    <div>
                        <h3 class="card-title">${escapeHtml(cb.source)}</h3>
                        <p class="card-subtitle">Year: ${cb.year}</p>
                    </div>
                    ${cb.release_type ? `<span class="badge badge-primary">${escapeHtml(cb.release_type)}</span>` : ''}
                </div>
                <div class="card-meta">
                    <div class="meta-item">
                        <span class="meta-label">Variables:</span>
                        <span>${cb.total_variables || 0}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Sections:</span>
                        <span>${cb.total_sections || 0}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Levels:</span>
                        <span>${(cb.levels || []).join(', ') || 'N/A'}</span>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading codebooks:', error);
        showError('codebooks-list', `Failed to load codebooks: ${error.message}. Make sure MongoDB is running and data is loaded.`);
    }
}

function viewCodebook(year, source) {
    alert(`Codebook: ${source} (${year})\n\nUse the API endpoints to get full details.`);
}

// ===== SEARCH VARIABLES =====
async function searchVariables() {
    const query = document.getElementById('searchInput')?.value.trim();
    if (!query) {
        alert('Please enter a search query');
        return;
    }
    
    // Switch to search tab
    switchTab('search');
    
    const year = document.getElementById('search-year-filter')?.value || '';
    const source = document.getElementById('search-source-filter')?.value || '';
    
    const results = document.getElementById('search-results');
    if (!results) return;
    
    showLoading('search-results', 'Searching...');
    
    try {
        const params = new URLSearchParams({ q: query });
        if (year) params.append('year', year);
        if (source) params.append('source', source);
        
        const data = await apiCall(`/search?${params}`);
        console.log('Search results:', data);
        
        if (!data.results || data.results.length === 0) {
            results.innerHTML = '<div class="empty-state">No variables found matching your search. Try a different query.</div>';
            return;
        }
        
        results.innerHTML = `
            <div class="search-summary">
                Found <strong>${data.total || 0}</strong> result(s), showing <strong>${data.results.length}</strong>
            </div>
            <div class="variable-list">
                ${data.results.map(v => `
                    <div class="variable-item" onclick="viewVariable('${escapeHtml(v.name)}', ${v.year}, '${escapeHtml(v.source || 'hrs_core_codebook')}')">
                        <div class="variable-header">
                            <h4 class="variable-name">${escapeHtml(v.name)}</h4>
                            <span class="badge badge-accent">${v.year}</span>
                        </div>
                        <div class="variable-meta">
                            <span class="meta-tag">Section: ${escapeHtml(v.section || 'N/A')}</span>
                            <span class="meta-tag">Level: ${escapeHtml(v.level || 'N/A')}</span>
                            <span class="meta-tag">Type: ${escapeHtml(v.type || 'N/A')}</span>
                        </div>
                        <p class="variable-description">${escapeHtml(v.description || 'No description available')}</p>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (error) {
        console.error('Error searching:', error);
        showError('search-results', `Search failed: ${error.message}. Make sure MongoDB is running and data is loaded.`);
    }
}

// ===== VIEW VARIABLE DETAILS =====
async function viewVariable(name, year, source) {
    const modal = document.getElementById('variable-modal');
    const detail = document.getElementById('variable-detail');
    
    if (!modal || !detail) return;
    
    detail.innerHTML = '<div class="loading">Loading variable details...</div>';
    modal.style.display = 'block';
    
    try {
        const params = new URLSearchParams({ year: year, source: source });
        const variable = await apiCall(`/variables/${encodeURIComponent(name)}?${params}`);
        console.log('Variable loaded:', variable);
        
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
                    <span>${escapeHtml(variable.type || 'N/A')} (Width: ${variable.width || 'N/A'}, Decimals: ${variable.decimals || 'N/A'})</span>
                </div>
            </div>
            ${variable.value_codes && variable.value_codes.length > 0 ? `
                <div class="value-codes-section">
                    <h3>Value Codes</h3>
                    <div class="value-codes-list">
                        ${variable.value_codes.map(vc => `
                            <div class="value-code-item">
                                <strong>${escapeHtml(String(vc.code))}</strong>${vc.frequency ? ` (${vc.frequency.toLocaleString()})` : ''}
                                ${vc.label ? `<div class="value-label">${escapeHtml(vc.label)}</div>` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
            ${variable.assignments && variable.assignments.length > 0 ? `
                <div class="variable-detail-section">
                    <h3>Assignments</h3>
                    <div class="assignment-list">
                        ${variable.assignments.map(a => `<div class="assignment-item">${escapeHtml(a.expression || '')}</div>`).join('')}
                    </div>
                </div>
            ` : ''}
            ${variable.references && variable.references.length > 0 ? `
                <div class="variable-detail-section">
                    <h3>References</h3>
                    <div class="reference-list">
                        ${variable.references.map(r => `<div class="reference-item">${escapeHtml(r.reference || '')}</div>`).join('')}
                    </div>
                </div>
            ` : ''}
        `;
    } catch (error) {
        console.error('Error loading variable:', error);
        detail.innerHTML = `<div class="error">Failed to load variable details: ${error.message}</div>`;
    }
}

// ===== SECTIONS =====
async function loadSections() {
    const year = document.getElementById('section-year-filter')?.value || '';
    const source = document.getElementById('section-source-filter')?.value || 'hrs_core_codebook';
    
    if (!year) {
        alert('Please select a year');
        return;
    }
    
    const list = document.getElementById('sections-list');
    if (!list) return;
    
    showLoading('sections-list', 'Loading sections...');
    
    try {
        const params = new URLSearchParams({ year: year, source: source });
        const sections = await apiCall(`/sections?${params}`);
        console.log('Sections loaded:', sections);
        
        if (sections.length === 0) {
            list.innerHTML = '<div class="empty-state">No sections found for the selected year and source.</div>';
            return;
        }
        
        list.innerHTML = sections.map(sec => `
            <div class="card">
                <div class="card-header">
                    <div>
                        <h3 class="card-title">Section ${escapeHtml(sec.code)}: ${escapeHtml(sec.name)}</h3>
                        <p class="card-subtitle">Level: ${escapeHtml(sec.level || 'N/A')}</p>
                    </div>
                    <span class="badge badge-primary">${sec.variable_count || 0} vars</span>
                </div>
                <div class="card-meta">
                    <div class="meta-item">
                        <span class="meta-label">Variables:</span>
                        <span>${(sec.variables || []).slice(0, 10).map(v => escapeHtml(v)).join(', ')}${(sec.variables || []).length > 10 ? '...' : ''}</span>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading sections:', error);
        showError('sections-list', `Failed to load sections: ${error.message}. Make sure MongoDB is running and data is loaded.`);
    }
}

// ===== MODAL =====
function closeModal() {
    const modal = document.getElementById('variable-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

window.onclick = function(event) {
    const modal = document.getElementById('variable-modal');
    if (event.target === modal) {
        closeModal();
    }
}

// ===== HELPER FUNCTIONS =====
function filterByYear(year) {
    switchTab('codebooks');
    const filter = document.getElementById('codebook-year-filter');
    if (filter) {
        filter.value = year;
    }
    loadCodebooks();
}

function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
