/* HRS Data Pipeline - Year and source filter dropdowns */

async function loadYearFilters() {
  try {
    const data = await apiCall('/years');
    const filterIds = ['codebook-year-filter', 'search-year-filter', 'section-year-filter', 'cat-year-filter', 'exit-year-filter'];
    filterIds.forEach((id) => {
      const select = document.getElementById(id);
      if (select && data.years) {
        const validYears = data.years.filter((y) => {
          const n = Number(y);
          return Number.isFinite(n) && n >= 1992 && n <= 2030;
        });
        select.innerHTML =
          '<option value="">All Years</option>' +
          validYears.map((y) => `<option value="${y}">${y}</option>`).join('');
      }
    });
  } catch (error) {
    console.error('Error loading years:', error);
  }
}

async function loadSourceFilters() {
  try {
    const data = await apiCall('/years');
    const filterIds = ['codebook-source-filter', 'search-source-filter', 'section-source-filter', 'cat-source-filter'];
    filterIds.forEach((id) => {
      const select = document.getElementById(id);
      if (select && data.sources) {
        select.innerHTML =
          '<option value="">All Sources</option>' +
          data.sources.map((s) => `<option value="${s}">${s}</option>`).join('');
      }
    });
  } catch (error) {
    console.error('Error loading sources:', error);
  }
}
