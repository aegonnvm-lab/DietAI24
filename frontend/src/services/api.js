/**
 * DietAI24 API Service Layer
 * Connects frontend to the FastAPI backend.
 */

const API_BASE = '';

/**
 * Fetch health status and config from backend
 */
export async function getHealthStatus() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    throw new Error(`Health check failed (${res.status})`);
  }
  return res.json();
}

/**
 * Fetch foods list with optional search and category filters
 */
export async function getFoods({ search = '', category = '', limit = 100 } = {}) {
  const params = new URLSearchParams();
  if (search) params.append('search', search);
  if (category && category !== 'All') params.append('category', category);
  if (limit) params.append('limit', limit.toString());

  const res = await fetch(`${API_BASE}/foods?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch foods (${res.status})`);
  }
  return res.json();
}

/**
 * Fetch a single food item by ID
 */
export async function getFoodById(foodId) {
  const res = await fetch(`${API_BASE}/foods/${foodId}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch food ${foodId}`);
  }
  return res.json();
}

/**
 * Analyze an uploaded meal image
 * @param {File|Blob} imageFile - The image file to analyze
 * @param {boolean} debug - Whether to include RAG & pipeline debug details
 */
export async function analyzeMealImage(imageFile, debug = true) {
  const formData = new FormData();
  formData.append('image', imageFile, imageFile.name || 'meal_upload.jpg');

  const res = await fetch(`${API_BASE}/analyze?debug=${debug}`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    let errorMsg = `Analysis failed (${res.status})`;
    try {
      const errorData = await res.json();
      if (errorData?.detail) {
        if (typeof errorData.detail === 'string') {
          errorMsg = errorData.detail;
        } else if (Array.isArray(errorData.detail)) {
          errorMsg = errorData.detail.map((d) => d.msg || JSON.stringify(d)).join(', ');
        } else {
          errorMsg = JSON.stringify(errorData.detail);
        }
      }
    } catch {
      // Non-JSON response (e.g. text/plain from 500 error)
      const text = await res.text().catch(() => '');
      if (text) errorMsg = text;
    }
    throw new Error(errorMsg);
  }

  return res.json();
}

/**
 * Recalculate nutrition with user-corrected portions or foods
 * @param {Array<{food_id: string, portion_grams: number}>} foods
 */
export async function recalculateNutrition(foods) {
  const res = await fetch(`${API_BASE}/recalculate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ foods }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Recalculation failed' }));
    throw new Error(errorData.detail || `Recalculation failed (${res.status})`);
  }

  return res.json();
}
