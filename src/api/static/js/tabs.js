/* HRS Data Pipeline - Tab navigation */

function initializeTabs() {
  const tabs = document.querySelectorAll('.tab');
  tabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      const tabName = tab.dataset.tab;
      switchTab(tabName);
    });
  });
}

function switchTab(tabName) {
  document.querySelectorAll('.tab').forEach((tab) => {
    tab.classList.remove('active');
    tab.setAttribute('aria-selected', 'false');
  });
  const activeTab = document.querySelector(`[data-tab="${tabName}"]`);
  if (activeTab) {
    activeTab.classList.add('active');
    activeTab.setAttribute('aria-selected', 'true');
  }

  document.querySelectorAll('.content-section').forEach((section) => {
    section.classList.remove('active');
  });
  const activeSection = document.getElementById(tabName);
  if (activeSection) {
    activeSection.classList.add('active');
  }

  if (window.HRS_STATE) window.HRS_STATE.currentTab = tabName;

  /* Only refresh dashboard when switching to it; Codebooks/Exit load on button click */
  if (tabName === 'dashboard') loadDashboard();
}

window.switchTab = switchTab;
