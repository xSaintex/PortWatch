/*
 * admin_scan_progress.js
 * Polls the scan status endpoint every second and updates the progress page.
 *
 * HOW IT WORKS:
 *   1. Every 1 second, fetch() calls GET /admin/scan/status/<job_id>.
 *   2. The server returns a JSON object describing the current stage,
 *      percent complete, list of finished devices, and (when done)
 *      the results summary.
 *   3. This script updates the progress bar, stage stepper, devices-done
 *      table, and (when complete) renders the results summary cards.
 *   4. Polling stops automatically when status is "completed" or "failed".
 *   5. If the fetch fails (e.g. network hiccup), we show a small retry
 *      notice and keep polling.
 *
 * Data injected by the template via window.scanProgressData:
 *   jobId        — UUID string
 *   statusUrl    — /admin/scan/status/<job_id>
 *   historyUrl   — /admin/history
 *   scanUrl      — /admin/scan
 *   singleDevice — bool
 *   deviceName   — string (single device only)
 *   deviceId     — int (single device only)
 *   totalStages  — int
 */

document.addEventListener("DOMContentLoaded", function () {

    const P = window.scanProgressData || {};

    // ---------------------------------------------------------------- //
    // ELEMENT REFERENCES
    // ---------------------------------------------------------------- //
    const progressBar       = document.getElementById("progressBar");
    const progressLabel     = document.getElementById("progressLabel");
    const progressPct       = document.getElementById("progressPct");
    const progressTitle     = document.getElementById("progressTitle");
    const stageStepper      = document.getElementById("stageStepper");
    const currentDeviceWrap = document.getElementById("currentDeviceWrap");
    const currentDeviceText = document.getElementById("currentDeviceText");
    const devicesDoneCount  = document.getElementById("devicesDoneCount");
    const devicesDoneBody   = document.getElementById("devicesDoneBody");
    const devicesDoneCol    = document.getElementById("devicesDoneCol");
    const errorBox          = document.getElementById("errorBox");
    const errorText         = document.getElementById("errorText");
    const resultsSummary    = document.getElementById("resultsSummary");
    const resultStatCards   = document.getElementById("resultStatCards");
    const resultsTableWrap  = document.getElementById("resultsTableWrap");
    const resultsTableBody  = document.getElementById("resultsTableBody");
    const resultsHighRisk   = document.getElementById("resultsHighRiskBanner");
    const resultsHighText   = document.getElementById("resultsHighRiskText");
    const viewResultsBtn    = document.getElementById("viewResultsBtn");

    const RISK_ORDER = { "High": 3, "Medium": 2, "Low": 1, "None": 0, null: 0 };

    let pollInterval = null;
    let retryCount   = 0;
    const MAX_RETRY  = 5;


    // ================================================================ //
    // MAIN POLL LOOP
    // ================================================================ //
    function startPolling() {
        pollInterval = setInterval(fetchStatus, 1000);
        fetchStatus();   // also fetch immediately
    }

    function stopPolling() {
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
    }

    async function fetchStatus() {
        try {
            const response = await fetch(P.statusUrl);
            if (!response.ok) {
                throw new Error("HTTP " + response.status);
            }
            const data = await response.json();
            retryCount = 0;
            updatePage(data);

            if (data.status === "completed" || data.status === "failed") {
                stopPolling();
            }
        } catch (err) {
            retryCount++;
            if (retryCount >= MAX_RETRY) {
                stopPolling();
                showError(
                    "Could not reach the server after " + MAX_RETRY +
                    " attempts. The scan may still be running — " +
                    "check Scan History in a moment."
                );
            }
            // Otherwise silently retry on next tick
        }
    }


    // ================================================================ //
    // PAGE UPDATE — called with each status response
    // ================================================================ //
    function updatePage(data) {

        // ---- Progress bar ------------------------------------------ //
        const pct = data.percent || 0;
        if (progressBar) {
            progressBar.style.width = pct + "%";
            progressBar.setAttribute("aria-valuenow", pct);
        }
        if (progressPct) progressPct.textContent = pct + "%";
        if (progressLabel) progressLabel.textContent = data.stage || "";

        // ---- Page title -------------------------------------------- //
        if (progressTitle) {
            if (data.status === "completed") {
                progressTitle.textContent = "Scan Complete";
            } else if (data.status === "failed") {
                progressTitle.textContent = "Scan Failed";
            } else {
                progressTitle.textContent = "Scan in Progress";
            }
        }

        // ---- Stage stepper ----------------------------------------- //
        if (stageStepper) {
            const steps = stageStepper.querySelectorAll(".pw-scan-step");
            steps.forEach(function (step) {
                const idx = parseInt(step.dataset.stageIndex, 10);
                const iconEl = step.querySelector(".pw-scan-step-icon");

                step.classList.remove("done", "current", "pending");

                if (data.status === "completed" || idx < data.stage_index) {
                    step.classList.add("done");
                    if (iconEl) iconEl.innerHTML =
                        '<i class="bi bi-check-circle-fill" aria-hidden="true"></i>';
                } else if (idx === data.stage_index && data.status === "running") {
                    step.classList.add("current");
                    if (iconEl) iconEl.innerHTML =
                        '<span class="spinner-border spinner-border-sm" ' +
                        'role="status" aria-hidden="true"></span>';
                } else {
                    step.classList.add("pending");
                    if (iconEl) iconEl.innerHTML =
                        '<i class="bi bi-circle" aria-hidden="true"></i>';
                }
            });
        }

        // ---- Current device indicator ------------------------------ //
        if (currentDeviceWrap) {
            if (data.current_device && data.status === "running") {
                currentDeviceWrap.style.display = "";
                if (currentDeviceText) {
                    currentDeviceText.textContent =
                        "Scanning device " +
                        (data.devices_done.length + 1) +
                        " of " + data.devices_total +
                        ": " + data.current_device;
                }
            } else {
                currentDeviceWrap.style.display = "none";
            }
        }

        // ---- Devices done table ------------------------------------ //
        if (devicesDoneCount) {
            devicesDoneCount.textContent =
                "(" + data.devices_done.length + " / " + data.devices_total + ")";
        }

        if (devicesDoneBody && data.devices_done) {
            devicesDoneBody.innerHTML = "";
            data.devices_done.forEach(function (d) {
                const tr = document.createElement("tr");
                tr.innerHTML =
                    '<td><div class="fw-semibold small">' + esc(d.device_name) + '</div>' +
                    '<div class="pw-mono pw-text-muted" style="font-size:0.75rem;">' +
                    esc(d.ip_address) + '</div></td>' +
                    '<td class="small">' + d.open_ports + '</td>' +
                    '<td class="small">' + d.flagged + '</td>' +
                    '<td>' + riskBadge(d.highest_risk) + '</td>';
                devicesDoneBody.appendChild(tr);
            });
        }

        // Show devices-done column for multi-device scans
        if (devicesDoneCol && data.devices_total > 1) {
            devicesDoneCol.style.display = "";
        }

        // ---- Error ------------------------------------------------- //
        if (data.status === "failed") {
            showError(data.error || "The scan failed for an unknown reason.");
        }

        // ---- Results summary (when complete) ----------------------- //
        if (data.status === "completed" && data.results_summary) {
            renderResults(data.results_summary);
        }
    }


    // ================================================================ //
    // RENDER RESULTS SUMMARY
    // ================================================================ //
    function renderResults(rs) {
        if (!resultsSummary) return;
        resultsSummary.style.display = "";

        // Stat cards
        if (resultStatCards) {
            resultStatCards.innerHTML = [
                statCard(rs.devices_scanned, "Devices Scanned",    "bi-hdd-network",     ""),
                statCard(rs.total_open,      "Open Ports Found",   "bi-door-open",       ""),
                statCard(rs.total_flagged,   "Flagged Findings",   "bi-flag",            ""),
                statCard(rs.high_risk_devices,
                         "High-Risk Devices", "bi-exclamation-octagon",
                         rs.high_risk_devices > 0 ? "pw-red" : ""),
            ].join("");
        }

        // High-risk banner
        if (resultsHighRisk && resultsHighText) {
            if (rs.high_risk_devices > 0) {
                resultsHighText.textContent =
                    rs.high_risk_devices + " device" +
                    (rs.high_risk_devices !== 1 ? "s" : "") +
                    " had High-risk findings. Review them now.";
                resultsHighRisk.style.display = "";
            }
        }

        // Table (multi-device)
        if (rs.devices_scanned > 1 && resultsTableWrap && resultsTableBody) {
            resultsTableWrap.style.display = "";
            resultsTableBody.innerHTML = "";
            (rs.devices_done || []).forEach(function (d) {
                const lc = d.summary.label_counts || {};
                const viewUrl = d.scan_id
                    ? "/admin/scans/" + d.scan_id
                    : "#";
                const tr = document.createElement("tr");
                tr.innerHTML =
                    '<td><div class="fw-semibold small">' + esc(d.device_name) + '</div></td>' +
                    '<td class="pw-mono small">' + esc(d.ip_address) + '</td>' +
                    '<td class="small">' + d.summary.open_ports + '</td>' +
                    '<td class="small">' + (lc.Approved   || 0) + '</td>' +
                    '<td class="small">' + (lc.Unexpected || 0) + '</td>' +
                    '<td class="small">' + (lc.Risky      || 0) + '</td>' +
                    '<td class="small">' + (lc.Missing    || 0) + '</td>' +
                    '<td>' + riskBadge(d.summary.highest_risk) + '</td>' +
                    '<td><a href="' + viewUrl + '" class="btn-icon" ' +
                    'title="View results" aria-label="View results">' +
                    '<i class="bi bi-eye" aria-hidden="true"></i></a></td>';
                resultsTableBody.appendChild(tr);
            });

            // Paginate if many devices
            if (typeof initTablePagination === "function") {
                try {
                    initTablePagination("resultsTable", {
                        pageSize:     8,
                        itemWord:     "devices",
                        paginationId: "resultsTablePagination",
                    });
                } catch (e) { /* ignore */ }
            }
        }

        // View Results / View Scan History button
        if (viewResultsBtn) {
            if (P.singleDevice) {
                const done = rs.devices_done || [];
                if (done.length > 0 && done[0].scan_id) {
                    viewResultsBtn.href = "/admin/scans/" + done[0].scan_id;
                    viewResultsBtn.innerHTML =
                        '<i class="bi bi-eye me-1" aria-hidden="true"></i>View Results';
                }
            } else {
                viewResultsBtn.href = P.historyUrl;
                viewResultsBtn.innerHTML =
                    '<i class="bi bi-clock-history me-1" aria-hidden="true"></i>' +
                    'View Scan History';
            }
        }
    }


    // ================================================================ //
    // HELPERS
    // ================================================================ //

    function showError(msg) {
        if (errorBox)  errorBox.style.display  = "";
        if (errorText) errorText.textContent   = msg;
    }

    function esc(str) {
        // Minimal HTML escaping to prevent XSS in dynamically built table cells
        return String(str || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function riskBadge(risk) {
        if (risk === "High")   return '<span class="badge-risk-high">High</span>';
        if (risk === "Medium") return '<span class="badge-risk-medium">Medium</span>';
        if (risk === "Low")    return '<span class="badge-risk-low">Low</span>';
        return '<span class="badge-risk-none">None</span>';
    }

    function statCard(number, label, icon, numberClass) {
        return `
        <div class="col-6 col-lg-3">
          <div class="pw-stat-card">
            <i class="bi ${icon} pw-summary-icon" aria-hidden="true"></i>
            <div>
              <div class="pw-summary-number ${numberClass}">${number}</div>
              <div class="pw-summary-label">${label}</div>
            </div>
          </div>
        </div>`;
    }


    // ================================================================ //
    // START
    // ================================================================ //
    startPolling();
});
