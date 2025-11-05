/**
 * Get date string 5 years ago from today (kept for backward compatibility)
 * @returns Date string in YYYY-MM-DD format
 */
export function getDate5YearsAgo(): string {
  const date = new Date();
  date.setFullYear(date.getFullYear() - 5);
  return date.toISOString().split('T')[0];
}

/**
 * Get date string 2 years ago from today
 * Default for backtesting to ensure data availability and integrity
 * @returns Date string in YYYY-MM-DD format
 */
export function getDate2YearsAgo(): string {
  const date = new Date();
  date.setFullYear(date.getFullYear() - 2);
  return date.toISOString().split('T')[0];
}

/**
 * Data limits cache - will be populated from API on first load
 */
let dataLimitsCache: Record<string, number> | null = null;

/**
 * Fetch data limits from the API
 * @returns Promise with data limits object
 */
export async function fetchDataLimits(): Promise<Record<string, number>> {
  if (dataLimitsCache) {
    return dataLimitsCache;
  }

  try {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
    const token = localStorage.getItem("bt_jwt");
    
    if (!token) {
      // Fallback to default limits if not authenticated
      return getDefaultLimits();
    }

    const response = await fetch(`${API_URL}/analysis/data-limits`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (response.ok) {
      const data = await response.json();
      dataLimitsCache = data.limits || getDefaultLimits();
      return dataLimitsCache;
    }
  } catch (error) {
    console.warn("Failed to fetch data limits, using defaults:", error);
  }

  return getDefaultLimits();
}

/**
 * Get default data limits (fallback if API unavailable)
 */
function getDefaultLimits(): Record<string, number> {
  return {
    "5m": 30,
    "15m": 60,
    "30m": 90,
    "1h": 730,
    "4h": 730,
    "1d": 3650,
  };
}

/**
 * Clear the data limits cache (useful for testing or when limits change)
 */
export function clearDataLimitsCache(): void {
  dataLimitsCache = null;
}

/**
 * Get appropriate start date based on timeframe
 * Uses dynamic limits from the API, falls back to defaults if unavailable
 * @param timeframe - The timeframe string (1d, 4h, 1h, 30m, 15m, 5m)
 * @param limits - Optional limits object (will fetch if not provided)
 * @returns Promise<string> Date string in YYYY-MM-DD format
 */
export async function getStartDateForTimeframe(
  timeframe: string,
  limits?: Record<string, number>
): Promise<string> {
  const date = new Date();
  const tf = timeframe.toLowerCase();
  
  // Normalize timeframe
  let tfKey: string;
  if (tf === '1d' || tf === 'day') {
    tfKey = '1d';
  } else if (tf === '4h' || tf === '4hour') {
    tfKey = '4h';
  } else if (tf === '1h' || tf === 'hour') {
    tfKey = '1h';
  } else if (tf === '30m' || tf === '30min') {
    tfKey = '30m';
  } else if (tf === '15m' || tf === '15min') {
    tfKey = '15m';
  } else if (tf === '5m' || tf === '5min') {
    tfKey = '5m';
  } else {
    tfKey = '1d'; // Default
  }

  // Get limits (fetch if not provided)
  const limitsToUse = limits || await fetchDataLimits();
  const limitDays = limitsToUse[tfKey] || 730;

  // Calculate start date
  if (limitDays >= 365) {
    const years = Math.floor(limitDays / 365);
    date.setFullYear(date.getFullYear() - years);
  } else {
    date.setDate(date.getDate() - limitDays);
  }

  return date.toISOString().split('T')[0];
}

/**
 * Synchronous version that uses cached or default limits
 * Use this for immediate calculations (e.g., initial state)
 */
export function getStartDateForTimeframeSync(
  timeframe: string,
  limits?: Record<string, number>
): string {
  const date = new Date();
  const tf = timeframe.toLowerCase();
  
  // Normalize timeframe
  let tfKey: string;
  if (tf === '1d' || tf === 'day') {
    tfKey = '1d';
  } else if (tf === '4h' || tf === '4hour') {
    tfKey = '4h';
  } else if (tf === '1h' || tf === 'hour') {
    tfKey = '1h';
  } else if (tf === '30m' || tf === '30min') {
    tfKey = '30m';
  } else if (tf === '15m' || tf === '15min') {
    tfKey = '15m';
  } else if (tf === '5m' || tf === '5min') {
    tfKey = '5m';
  } else {
    tfKey = '1d'; // Default
  }

  // Use provided limits or defaults
  const limitsToUse = limits || getDefaultLimits();
  const limitDays = limitsToUse[tfKey] || 730;

  // Calculate start date
  if (limitDays >= 365) {
    const years = Math.floor(limitDays / 365);
    date.setFullYear(date.getFullYear() - years);
  } else {
    date.setDate(date.getDate() - limitDays);
  }

  return date.toISOString().split('T')[0];
}

/**
 * Get today's date string
 * @returns Date string in YYYY-MM-DD format
 */
export function getToday(): string {
  return new Date().toISOString().split('T')[0];
}

