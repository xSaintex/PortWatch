/*
 * admin_scan_history.js
 * Client-side logic for the Scan History page (/admin/history).
 *
 * Responsibilities:
 *   1. Filter rows: search (device name or IP), lab, risk, date range, unacknowledged.
 *      The Device dropdown was removed; the search box handles device filtering.
 *   2. Sort rows: Scanned At (default newest-first), Device, Highest Risk.
 *   3. Pagination — 10 rows per page via the shared initTablePagination.
 *      The "Showing X–Y of Z scans" text lives in the pagination bar only.
 *   4. Quick date buttons: Today / Last 7 days / Last 30 days.
 *   5. Date validation — inline error when Date To < Date From.
 *   6. Export CSV button — builds URL from current filters (uses "q" for search).
 *   7. Row click — navigate to the scan's View Results page.
 *   8. On page load, if window.scanHistoryData.prefill.deviceName is set
 *      (populated by the route when ?device_id= is given), pre-fill the search box.
 */

document.addEventListener("DOMContentLoaded", function () {

    const D       = window.scanHistoryData || {};
    const prefill = D.prefill || {};

    // ---------------------------------------------------------------- //
    // ELEMENT REFERENCES
    // ---------------------------------------------------------------- //
    const filterSearch   = document.getElementById("filterSearch");
    const filterLab      = document.getElementById("filterLab");
    const filterRisk     = document.getElementById("filterRisk");
    const filterDateFrom = document.getElementById("filterDateFrom");
    const filterDateTo   = document.getElementById("filterDateTo");
    const filterUnack    = document.getElementById("filterUnack");
    const clearBtn       = document.getElementById("clearFilters");
    const clearBtn2      = document.getElementById("clearFilters2");
    const noResults      = document.getElementById("noFilterResults");
    const dateError      = document.getElementById("dateError");
    const tableBody      = document.getElementById("scansTableBody");
    const exportBtn      = document.getElementById("exportCsvBtn");

    const RISK_ORDER = { "High": 4, "Medium": 3, "Low": 2, "None": 1, "": 0 };


    // ================================================================ //
    // 1. FILTER LOGIC
    // ================================================================ //

    let dateRangeValid = true;

    function applyFilters() {
        if (!tableBody) return;

        const search   = filterSearch   ? filterSearch.value.toLowerCase().trim() : "";
        const lab      = filterLab      ? filterLab.value.toLowerCase()            : "";
        const risk     = filterRisk     ? filterRisk.value                         : "";
        const dateFrom = filterDateFrom ? filterDateFrom.value                     : "";
        const dateTo   = filterDateTo   ? filterDateTo.value                       : "";
        const unack    = filterUnack    ? filterUnack.checked                      : false;

        // Date validation
        if (dateFrom && dateTo && dateTo < dateFrom) {
            if (dateError) dateError.style.display = "";
            dateRangeValid = false;
        } else {
            if (dateError) dateError.style.display = "none";
            dateRangeValid = true;
        }

        const rows = tableBody.querySelectorAll(".pw-scan-row");

        rows.forEach(function (row) {
            const rDevice = row.dataset.device || "";
            const rIp     = row.dataset.ip     || "";
            const rLab    = row.dataset.lab    || "";
            const rRisk   = row.dataset.risk   || "";
            const rDate   = row.dataset.date   || "";
            const rUnack  = row.dataset.unack  || "0";

            let visible = true;

            // Search filters on device name OR IP address
            if (search && !rDevice.includes(search) && !rIp.includes(search))
                visible = false;
            if (lab  && rLab  !== lab)  visible = false;
            if (risk && rRisk !== risk) visible = false;
            if (dateRangeValid) {
                if (dateFrom && rDate && rDate < dateFrom) visible = false;
                if (dateTo   && rDate && rDate > dateTo)   visible = false;
            }
            if (unack && rUnack !== "1") visible = false;

            if (visible) {
                row.classList.remove("pw-filtered-out");
            } else {
                row.classList.add("pw-filtered-out");
                row.style.display = "none";
            }
        });

        if (noResults) noResults.style.display = "none"; // pagination handles empty state

        // Reset pagination to page 1
        if (window.refreshPagination && window.refreshPagination["scansTable"]) {
            window.refreshPagination["scansTable"]();
        }

        // Check if all rows are filtered out (pagination hides its bar; show empty state)
        const visibleCount = Array.from(rows).filter(
            r => !r.classList.contains("pw-filtered-out")
        ).length;
        if (noResults) {
            noResults.style.display = visibleCount === 0 ? "flex" : "none";
        }

        updateExportUrl();
    }

    // Wire filter inputs
    if (filterSearch)   filterSearch.addEventListener("input",  applyFilters);
    if (filterLab)      filterLab.addEventListener("change",    applyFilters);
    if (filterRisk)     filterRisk.addEventListener("change",   applyFilters);
    if (filterDateFrom) filterDateFrom.addEventListener("change", applyFilters);
    if (filterDateTo)   filterDateTo.addEventListener("change",   applyFilters);
    if (filterUnack)    filterUnack.addEventListener("change",    applyFilters);


    // ================================================================ //
    // 2. SORTING
    // ================================================================ //

    let sortCol = "date";
    let sortDir = "desc";

    const sortableHeaders = document.querySelectorAll(".pw-sortable");

    sortableHeaders.forEach(function (th) {
        th.style.cursor = "pointer";
        th.addEventListener("click", function () {
            const col = th.dataset.sort;
            if (col === sortCol) {
                sortDir = sortDir === "desc" ? "asc" : "desc";
            } else {
                sortCol = col;
                sortDir = col === "date" ? "desc" : "asc";
            }
            sortTable();
            updateSortIcons();
        });
    });

    function sortTable() {
        if (!tableBody) return;
        const rows = Array.from(tableBody.querySelectorAll(".pw-scan-row"));
        rows.sort(function (a, b) {
            if (sortCol === "risk") {
                const va = RISK_ORDER[a.dataset.risk] || 0;
                const vb = RISK_ORDER[b.dataset.risk] || 0;
                return sortDir === "desc" ? vb - va : va - vb;
            }
            const va = sortCol === "date" ? (a.dataset.date || "") : (a.dataset.device || "");
            const vb = sortCol === "date" ? (b.dataset.date || "") : (b.dataset.device || "");
            if (va < vb) return sortDir === "desc" ?  1 : -1;
            if (va > vb) return sortDir === "desc" ? -1 :  1;
            return 0;
        });
        rows.forEach(function (row) { tableBody.appendChild(row); });
        applyFilters();
    }

    function updateSortIcons() {
        sortableHeaders.forEach(function (th) {
            const arrowEl = th.querySelector(".pw-sort-arrow");
            const col     = th.dataset.sort;
            th.classList.remove("pw-sort-active");
            th.removeAttribute("aria-sort");
            if (col === sortCol) {
                th.classList.add("pw-sort-active");
                th.setAttribute("aria-sort", sortDir === "desc" ? "descending" : "ascending");
                if (arrowEl) arrowEl.textContent = sortDir === "desc" ? "▼" : "▲";
            } else {
                if (arrowEl) arrowEl.textContent = "";
            }
        });
    }


    // ================================================================ //
    // 3. PAGINATION — 10 rows per page
    // ================================================================ //
    try {
        if (typeof initTablePagination === "function") {
            initTablePagination("scansTable", {
                pageSize:     10,
                itemWord:     "scans",
                paginationId: "scansPagination",
            });
        }
    } catch (e) {
        console.warn("PortWatch: pagination init failed:", e);
    }


    // ================================================================ //
    // 4. QUICK DATE BUTTONS
    // ================================================================ //
    function isoDate(d) { return d.toISOString().slice(0, 10); }

    function setDateRange(from, to) {
        if (filterDateFrom) filterDateFrom.value = from;
        if (filterDateTo)   filterDateTo.value   = to;
        applyFilters();
    }

    const btnToday = document.getElementById("quickToday");
    const btnWeek  = document.getElementById("quickWeek");
    const btnMonth = document.getElementById("quickMonth");

    if (btnToday) btnToday.addEventListener("click", function () {
        const t = isoDate(new Date()); setDateRange(t, t);
    });
    if (btnWeek) btnWeek.addEventListener("click", function () {
        const to = new Date(); const from = new Date(to);
        from.setDate(from.getDate() - 6);
        setDateRange(isoDate(from), isoDate(to));
    });
    if (btnMonth) btnMonth.addEventListener("click", function () {
        const to = new Date(); const from = new Date(to);
        from.setDate(from.getDate() - 29);
        setDateRange(isoDate(from), isoDate(to));
    });


    // ================================================================ //
    // 5. CLEAR FILTERS
    // ================================================================ //
    function clearAllFilters() {
        if (filterSearch)   filterSearch.value   = "";
        if (filterLab)      filterLab.value      = "";
        if (filterRisk)     filterRisk.value     = "";
        if (filterDateFrom) filterDateFrom.value = "";
        if (filterDateTo)   filterDateTo.value   = "";
        if (filterUnack)    filterUnack.checked  = false;
        if (dateError)      dateError.style.display = "none";
        applyFilters();
    }

    if (clearBtn)  clearBtn.addEventListener("click",  clearAllFilters);
    if (clearBtn2) clearBtn2.addEventListener("click", clearAllFilters);


    // ================================================================ //
    // 6. EXPORT CSV URL — mirrors current filters
    //    Uses "q" for the search text (device_id dropdown removed).
    // ================================================================ //
    function updateExportUrl() {
        if (!exportBtn) return;
        const params = new URLSearchParams();
        const search   = filterSearch   ? filterSearch.value.trim()   : "";
        const lab      = filterLab      ? filterLab.value              : "";
        const risk     = filterRisk     ? filterRisk.value             : "";
        const dateFrom = filterDateFrom ? filterDateFrom.value         : "";
        const dateTo   = filterDateTo   ? filterDateTo.value           : "";
        const unack    = filterUnack    ? filterUnack.checked          : false;

        if (search)   params.set("q",            search);
        if (lab)      params.set("lab",          lab);
        if (risk)     params.set("risk",         risk);
        if (dateFrom) params.set("date_from",    dateFrom);
        if (dateTo)   params.set("date_to",      dateTo);
        if (unack)    params.set("unacknowledged", "1");

        const qs = params.toString();
        exportBtn.href = D.exportUrl + (qs ? "?" + qs : "");
    }


    // ================================================================ //
    // 7. ROW CLICK → View Results
    //
    // Uses event delegation on the <tbody> so it works on every page of
    // pagination and after sorting/filtering, without attaching listeners
    // to individual rows.
    //
    // We stop early when the click came from:
    //   - any <a> or <button> element (icon links, action buttons)
    //   - the .row-actions cell (belt-and-braces — the cell already has
    //     stopPropagation, but this catches edge cases like Bootstrap tooltips
    //     firing a synthetic click event slightly outside the icon bounds)
    //   - any <form> element
    // ================================================================ //
    if (tableBody) {
        tableBody.addEventListener("click", function (event) {
            const row = event.target.closest(".pw-scan-row");
            if (!row) return;

            // Do not navigate if the user clicked an action element
            if (event.target.closest("a, button, form, .row-actions")) return;

            const url = row.dataset.viewUrl;
            if (url) window.location.href = url;
        });
    }


    // ================================================================ //
    // 8. INITIALISE — prefill filters from query params / ?device_id
    // ================================================================ //
    (function init() {
        // If a device_id was in the URL, the route sets prefill.deviceName
        // so we can pre-fill the search box instead of using a dropdown.
        if (prefill.deviceName && filterSearch && !filterSearch.value) {
            filterSearch.value = prefill.deviceName;
        } else if (prefill.search && filterSearch) {
            filterSearch.value = prefill.search;
        }
        if (prefill.lab      && filterLab)      filterLab.value      = prefill.lab;
        if (prefill.risk     && filterRisk)     filterRisk.value     = prefill.risk;
        if (prefill.dateFrom && filterDateFrom) filterDateFrom.value = prefill.dateFrom;
        if (prefill.dateTo   && filterDateTo)   filterDateTo.value   = prefill.dateTo;
        if (prefill.unacknowledged && filterUnack) filterUnack.checked = true;

        applyFilters();
        updateSortIcons();
    })();
});
