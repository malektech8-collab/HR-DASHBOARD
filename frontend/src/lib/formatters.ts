export function formatNumber(val: number): string {
  return new Intl.NumberFormat('en-US').format(val);
}

export function formatCurrency(val: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'SAR',
    maximumFractionDigits: 0
  }).format(val);
}

export function formatPercent(val: number): string {
  return `${val.toFixed(1)}%`;
}

export function formatDate(valStr: string): string {
  if (!valStr || valStr === 'Unknown') return 'Unknown';
  try {
    const date = new Date(valStr);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (e) {
    return valStr;
  }
}
