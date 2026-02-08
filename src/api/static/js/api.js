/* HRS Data Pipeline - API client */

const API_BASE = window.location.origin;

async function apiCall(endpoint, options = {}) {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
      const detail = errorData.detail;
      const message = Array.isArray(detail)
        ? detail.map((d) => (d && d.msg) || String(d)).join('; ')
        : typeof detail === 'string'
          ? detail
          : `HTTP ${response.status}`;
      throw new Error(message);
    }

    return await response.json();
  } catch (error) {
    console.error(`API call failed for ${endpoint}:`, error);
    throw error;
  }
}
