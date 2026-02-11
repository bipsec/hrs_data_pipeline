/* HRS Data Pipeline - Main entry: init and global handlers */

document.addEventListener('DOMContentLoaded', () => {
  console.log('Initializing HRS Data Pipeline UI...');
  initializeTabs();
  initializeSearch();
  initCategorizationSubnav();
  if (typeof initExitSearchInput === 'function') initExitSearchInput();
  if (typeof initPostExitSearchInput === 'function') initPostExitSearchInput();
  loadDashboard();
  loadYearFilters();
  loadSourceFilters();
});

function filterByYear(year) {
  switchTab('codebooks');
  const filter = document.getElementById('codebook-year-filter');
  if (filter) filter.value = year;
  loadCodebooks();
}

window.filterByYear = filterByYear;
