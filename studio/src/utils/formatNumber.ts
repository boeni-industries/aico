/**
 * Format large numbers with K/M/B notation
 * 
 * Best practices:
 * - Use K/M/B for numbers >= 10,000
 * - 1 decimal place for readability
 * - Preserve precision for small numbers
 */

export function formatNumber(value: number | string, options?: {
  decimals?: number;
  forceDecimals?: boolean;
  preserveSmall?: boolean;
}): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  
  if (isNaN(num)) return '0';
  
  const decimals = options?.decimals ?? 1;
  const forceDecimals = options?.forceDecimals ?? false;
  const preserveSmall = options?.preserveSmall ?? true;
  
  // For very small numbers (< 0.01), show more precision
  if (preserveSmall && num > 0 && num < 0.01) {
    return num.toFixed(3);
  }
  
  // For small numbers (< 10,000), show with comma separators
  if (Math.abs(num) < 10000) {
    if (num % 1 === 0) {
      return num.toLocaleString('en-US');
    }
    return num.toLocaleString('en-US', {
      minimumFractionDigits: forceDecimals ? decimals : 0,
      maximumFractionDigits: decimals,
    });
  }
  
  // For large numbers, use K/M/B notation
  const absNum = Math.abs(num);
  const sign = num < 0 ? '-' : '';
  
  if (absNum >= 1e9) {
    return sign + (absNum / 1e9).toFixed(decimals) + 'B';
  }
  if (absNum >= 1e6) {
    return sign + (absNum / 1e6).toFixed(decimals) + 'M';
  }
  if (absNum >= 1e3) {
    return sign + (absNum / 1e3).toFixed(decimals) + 'K';
  }
  
  return num.toLocaleString('en-US');
}

/**
 * Format metric values with appropriate precision
 * Handles special cases for rates, percentages, and latencies
 */
export function formatMetricValue(
  value: number | string,
  unit?: string
): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  
  if (isNaN(num)) return '0';
  
  // Special handling for percentages - always show decimals
  if (unit === '%') {
    return num.toFixed(1);
  }
  
  // Special handling for rates (req/s, t/s, etc.) - adaptive precision for all scales
  if (unit?.includes('/s') || unit?.includes('/sec')) {
    // For very small non-zero values, show enough precision to be visible
    if (num > 0 && num < 0.01) {
      return num.toFixed(6); // e.g., 0.003750
    }
    if (num < 0.1) {
      return num.toFixed(4); // e.g., 0.0125
    }
    if (num < 1) {
      return num.toFixed(3); // e.g., 0.125
    }
    if (num < 10) {
      return num.toFixed(2); // e.g., 5.25
    }
    if (num < 100) {
      return num.toFixed(1); // e.g., 45.2
    }
    // For >= 100, use default K/M/B notation
  }
  
  // Special handling for latencies (ms, s) - show 2 decimals for precision
  if (unit === 'ms' || unit === 's') {
    if (num < 10) {
      return num.toFixed(2);
    }
    if (num < 100) {
      return num.toFixed(1);
    }
  }
  
  // Default: use K/M/B notation for large numbers
  return formatNumber(num);
}
