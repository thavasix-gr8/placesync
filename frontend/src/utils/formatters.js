export function formatDate(date) {
  return new Date(date).toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
  })
}

export function statusClass(status) {
  return status.toLowerCase().replace(' ', '-')
}
