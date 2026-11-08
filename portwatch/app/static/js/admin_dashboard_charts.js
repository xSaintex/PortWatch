/*
 * admin_dashboard_charts.js
 * Creates the two Chart.js charts on the Admin Dashboard:
 *   1. "Findings by Label"  — doughnut chart
 *   2. "Findings by Risk Level" — bar chart
 *
 * HOW DATA GETS HERE:
 * The Admin Dashboard template (admin_dashboard.html) renders two
 * <script> tags that set window.chartFindingsByLabel and
 * window.chartFindingsByRisk as plain JavaScript objects using
 * Jinja2's {{ variable | tojson }} filter. This is the safest way to
 * pass Python data to JavaScript without concatenating strings.
 *
 * This script runs after those inline scripts and after Chart.js is loaded.
 */

document.addEventListener("DOMContentLoaded", function () {

    // ---------------------------------------------------------------- //
    // SHARED CHART DEFAULTS
    // Dark theme settings reused by both charts.
    // ---------------------------------------------------------------- //
    const gridColor  = "rgba(255, 255, 255, 0.07)";  // Very faint white grid lines
    const tickColor  = "#A6A6A6";                     // Muted gray axis labels
    const legendColor = "#A6A6A6";

    Chart.defaults.color = tickColor;
    Chart.defaults.font.family = "'Segoe UI', system-ui, sans-serif";
    Chart.defaults.font.size   = 12;


    // ================================================================ //
    // CHART 1 — FINDINGS BY LABEL (DOUGHNUT)
    // ================================================================ //
    const labelCanvas = document.getElementById("chartFindingsByLabel");

    if (labelCanvas && window.chartFindingsByLabel) {
        const labelData = window.chartFindingsByLabel;

        new Chart(labelCanvas, {
            type: "doughnut",
            data: {
                labels: labelData.labels,
                datasets: [{
                    data: labelData.counts,
                    backgroundColor: labelData.colors,
                    borderColor: "#1A1A1A",   // match --pw-surface so segments look separated
                    borderWidth: 3,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                cutout: "62%",       // Makes it a thick doughnut rather than a pie
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            color: legendColor,
                            padding: 16,
                            boxWidth: 12,
                            usePointStyle: true,
                            pointStyle: "circle"
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                // Show "Label: count (percentage%)"
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const pct   = total > 0
                                    ? Math.round((context.parsed / total) * 100)
                                    : 0;
                                return ` ${context.label}: ${context.parsed} (${pct}%)`;
                            }
                        }
                    }
                }
            }
        });
    }


    // ================================================================ //
    // CHART 2 — FINDINGS BY RISK LEVEL (BAR)
    // ================================================================ //
    const riskCanvas = document.getElementById("chartFindingsByRisk");

    if (riskCanvas && window.chartFindingsByRisk) {
        const riskData = window.chartFindingsByRisk;

        new Chart(riskCanvas, {
            type: "bar",
            data: {
                labels: riskData.labels,
                datasets: [{
                    label: "Findings",
                    data: riskData.counts,
                    backgroundColor: riskData.colors,
                    borderRadius: 5,
                    borderSkipped: false,
                    barPercentage: 0.55
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false   // Only one dataset, legend not needed
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return ` ${context.parsed.y} finding${context.parsed.y !== 1 ? "s" : ""}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: gridColor
                        },
                        ticks: {
                            color: tickColor
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: gridColor
                        },
                        ticks: {
                            color: tickColor,
                            // Only show whole numbers on the y-axis
                            stepSize: 1,
                            callback: function (value) {
                                return Number.isInteger(value) ? value : null;
                            }
                        }
                    }
                }
            }
        });
    }

});
