// === MO TA FILE ===
// server/app/static/js/statistics.js
// CHUC NANG: Ve bieu do Chart.js
(function () {
  "use strict";

  var dataElement = document.getElementById("chart-data");
  if (!dataElement || !window.Chart) {
    return;
  }
  var chartData = JSON.parse(dataElement.textContent);
  var colorWarning = "#e0a100";
  var colorDanger = "#c62828";
  var colorPrimary = "#1f5fbf";

  Chart.defaults.font.family = "'Segoe UI', Roboto, Arial, sans-serif";
  Chart.defaults.color = "#4b5563";
  Chart.defaults.maintainAspectRatio = false;

  function createChart(canvasId, config) {
    var canvas = document.getElementById(canvasId);
    if (canvas) {
      new Chart(canvas, config);
    }
  }

  createChart("chart-per-day", {
    type: "bar",
    data: {
      labels: chartData.days,
      datasets: [
        { label: "Cảnh báo", data: chartData.per_day_warning, backgroundColor: colorWarning, borderRadius: 4, stack: "alerts" },
        { label: "Nguy hiểm", data: chartData.per_day_danger, backgroundColor: colorDanger, borderRadius: 4, stack: "alerts" }
      ]
    },
    options: {
      plugins: { legend: { position: "bottom" } },
      scales: {
        x: { stacked: true, grid: { display: false } },
        y: { stacked: true, beginAtZero: true, ticks: { precision: 0 } }
      }
    }
  });

  createChart("chart-by-class", {
    type: "bar",
    data: {
      labels: chartData.class_labels,
      datasets: [{ label: "Số cảnh báo", data: chartData.class_counts, backgroundColor: colorPrimary, borderRadius: 4 }]
    },
    options: {
      indexAxis: "y",
      plugins: { legend: { display: false } },
      scales: { x: { beginAtZero: true, ticks: { precision: 0 } }, y: { grid: { display: false } } }
    }
  });

  createChart("chart-by-level", {
    type: "doughnut",
    data: {
      labels: chartData.level_labels,
      datasets: [{ data: chartData.level_counts, backgroundColor: [colorWarning, colorDanger], borderWidth: 2 }]
    },
    options: { plugins: { legend: { position: "bottom" } }, cutout: "60%" }
  });

  createChart("chart-by-position", {
    type: "doughnut",
    data: {
      labels: chartData.position_labels,
      datasets: [{ data: chartData.position_counts, backgroundColor: ["#5b8def", colorPrimary, "#9db8e8"], borderWidth: 2 }]
    },
    options: { plugins: { legend: { position: "bottom" } }, cutout: "60%" }
  });
})();
