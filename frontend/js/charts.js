const Charts = {
  createLineChart(canvasId, labels, datasets) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || typeof Chart === 'undefined') return null;
    return new Chart(ctx, {
      type: 'line',
      data: { labels, datasets },
      options: {
        responsive: true,
        plugins: { legend: { labels: { color: '#cbd5e1' } } },
        scales: {
          x: { ticks: { color: '#94a3b8' }, grid: { color: '#334155' } },
          y: { ticks: { color: '#94a3b8' }, grid: { color: '#334155' } },
        },
      },
    });
  },

  createBarChart(canvasId, labels, data, label = 'Value') {
    const ctx = document.getElementById(canvasId);
    if (!ctx || typeof Chart === 'undefined') return null;
    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{ label, data, backgroundColor: '#2563eb', borderRadius: 4 }],
      },
      options: {
        responsive: true,
        plugins: { legend: { labels: { color: '#cbd5e1' } } },
        scales: {
          x: { ticks: { color: '#94a3b8' }, grid: { color: '#334155' } },
          y: { ticks: { color: '#94a3b8' }, grid: { color: '#334155' } },
        },
      },
    });
  },

  createDoughnut(canvasId, value, max = 100) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || typeof Chart === 'undefined') return null;
    return new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Score', 'Remaining'],
        datasets: [{
          data: [value, max - value],
          backgroundColor: ['#2563eb', '#334155'],
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        cutout: '70%',
        plugins: { legend: { display: false } },
      },
    });
  },
};

window.Charts = Charts;
