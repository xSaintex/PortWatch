/*
 * admin_audit_log.js
 * Client-side logic for the Audit Log page (/admin/audit-log).
 *
 * Responsibilities:
 *   1. Filter rows: search (user/target/details), category, result,
 *      user dropdown, date range, "blocked attempts only" checkbox.
 *   2. Date validation — inline error when Date To < Date From.
 *   3. Quick date buttons: Today / Last 7 days / Last 30 days.
 *   4. Pagination — 10 rows per page via the shared initTablePagination.
 *      The "Showing X–Y of Z" text lives only in the pagination bar.
 *   5. Export CSV button — appends current filters to the URL so the
 *      download always matches what is shown on screen.
 *   6. Clear filters.
 *   7. Prefill from window.auditLogData.prefill (set by query params).
 *
 * FILTER + PAGINATION CONTRACT:
 *   Filters add "pw-filtered-out" to non-matching rows and call
 *   window.refreshPagination["auditTable"]() so pagination re-slices.
 */

document.addEventListener("DOMContentLoaded", function () {

    const D       = window.auditLogData || {};
    const prefill = D.prefill || {};

    // ---------------------------------------------------------------- //
    // ELEMENT REFERENCES
    // ---------------------------------------------------------------- //
    const filterSearch   = document.getElementById("filterSearch");
    const filterCategory = document.getElementById("filterCategory");
    const filterResult   = document.getElementById("filterResult");
    const filterUser     = document.getElementById("filterUser");
    const filterDateFrom = document.getElementById("filterDateFrom");
    const filterDateTo   = document.getElementById("filterDateTo");
    const filterBlocked  = document.getElementById("filterBlocked");
    const clearBtn       = document.getElementById("clearFilters");
    const clearBtn2      = document.getElementById("clearFilters2");
    const dateError      = document.getElementById("dateError");
    const tableBody      = document.getElementById("auditTableBody");
    const noResults      = document.getElementById("noFilterResults");
    const exportBtn      = document.getElementById("exportCsvBtn");


    // ================================================================ //
    // 1. FILTER LOGIC
    // ================================================================ //
    let dateRangeValid = true;

    function applyFilters() {
        if (!tableBody) return;

        const search   = filterSearch   ? filterSearch.value.toLowerCase().trim() : "";
        const category = filterCategory ? filterCategory.value                     : "";
        const result   = filterResult   ? filterResult.value                       : "";
        const user     = filterUser     ? filterUser.value.toLowerCase()           : "";
        const dateFrom = filterDateFrom ? filterDateFrom.value                     : "";
        const dateTo   = filterDateTo   ? filterDateTo.value                       : "";
        const blocked  = filterBlocked  ? filterBlocked.checked                    : false;

        // Date validation
        if (dateFrom && dateTo && dateTo < dateFrom) {
            if (dateError) dateError.style.display = "";
            dateRangeValid = false;
        } else {
            if (dateError) dateError.style.display = "none";
            dateRangeValid = true;
        }

        const rows = tableBody.querySelectorAll(".pw-audit-row");

        rows.forEach(function (row) {
            const rSearch   = row.dataset.search   || "";
            const rCategory = row.dataset.category || "";
            const rResult   = row.dataset.result   || "";
            const rUser     = row.dataset.user     || "";
            const rDate     = row.dataset.date     || "";

            let visible = true;

            if (search   && !rSearch.includes(search))    visible = false;
            if (category && rCategory !== category)        visible = false;
            if (result   && rResult   !== result)          visible = false;
            if (user     && rUser     !== user)            visible = false;
            if (dateRangeValid) {
                if (dateFrom && rDate && rDate < dateFrom) visible = false;
                if (dateTo   && rDate && rDate > dateTo)   visible = false;
            }
            // "Blocked attempts only" also accepts "failed" since both are
            // security-relevant non-success outcomes
            if (blocked && rResult !== "blocked") visible = false;

            if (visible) {
                row.classList.remove("pw-filtered-out");
            } else {
                row.classList.add("pw-filtered-out");
                row.style.display = "none";
            }
        });

        // Show/hide the no-results empty state
        if (noResults) {
            const anyVisible = Array.from(rows).some(
                r => !r.classList.contains("pw-filtered-out")
            );
            noResults.style.display = anyVisible ? "none" : "flex";
        }

        // Reset pagination to page 1
        if (window.refreshPagination && window.refreshPagination["auditTable"]) {
            window.refreshPagination["auditTable"]();
        }

        updateExportUrl();
    }

    // Wire all filter inputs
    if (filterSearch)   filterSearch.addEventListener("input",   applyFilters);
    if (filterCategory) filterCategory.addEventListener("change", applyFilters);
    if (filterResult)   filterResult.addEventListener("change",   applyFilters);
    if (filterUser)     filterUser.addEventListener("change",     applyFilters);
    if (filterDateFrom) filterDateFrom.addEventListener("change", applyFilters);
    if (filterDateTo)   filterDateTo.addEventListener("change",   applyFilters);
    if (filterBlocked)  filterBlocked.addEventListener("change",  applyFilters);


    // ================================================================ //
    // 2. QUICK DATE BUTTONS
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
    // 3. PAGINATION — 10 entries per page
    // ================================================================ //
    try {
        if (typeof initTablePagination === "function") {
            initTablePagination("auditTable", {
                pageSize:     10,
                itemWord:     "entries",
                paginationId: "auditPagination",
            });
        }
    } catch (e) {
        console.warn("PortWatch: audit log pagination init failed:", e);
    }


    // ================================================================ //
    // 4. CLEAR FILTERS
    // ================================================================ //
    function clearAllFilters() {
        if (filterSearch)   filterSearch.value   = "";
        if (filterCategory) filterCategory.value = "";
        if (filterResult)   filterResult.value   = "";
        if (filterUser)     filterUser.value     = "";
        if (filterDateFrom) filterDateFrom.value = "";
        if (filterDateTo)   filterDateTo.value   = "";
        if (filterBlocked)  filterBlocked.checked = false;
        if (dateError)      dateError.style.display = "none";
        applyFilters();
    }

    if (clearBtn)  clearBtn.addEventListener("click",  clearAllFilters);
    if (clearBtn2) clearBtn2.addEventListener("click", clearAllFilters);


    // ================================================================ //
    // 5. EXPORT CSV URL — mirrors the active filters
    // ================================================================ //
    function updateExportUrl() {
        if (!exportBtn) return;
        const params = new URLSearchParams();

        const search   = filterSearch   ? filterSearch.value.trim()   : "";
        const category = filterCategory ? filterCategory.value         : "";
        const result   = filterResult   ? filterResult.value           : "";
        const user     = filterUser     ? filterUser.value             : "";
        const dateFrom = filterDateFrom ? filterDateFrom.value         : "";
        const dateTo   = filterDateTo   ? filterDateTo.value           : "";
        const blocked  = filterBlocked  ? filterBlocked.checked        : false;

        if (search)   params.set("q",        search);
        if (category) params.set("category", category);
        if (result)   params.set("result",   result);
        if (user)     params.set("user",     user);
        if (dateFrom) params.set("date_from",dateFrom);
        if (dateTo)   params.set("date_to",  dateTo);
        if (blocked)  params.set("blocked",  "1");

        const qs = params.toString();
        exportBtn.href = D.exportUrl + (qs ? "?" + qs : "");
    }


    // ================================================================ //
    // 6. INITIALISE — apply prefilled filters from query params
    // ================================================================ //
    (function init() {
        if (prefill.q        && filterSearch)   filterSearch.value   = prefill.q;
        if (prefill.category && filterCategory) filterCategory.value = prefill.category;
        if (prefill.result   && filterResult)   filterResult.value   = prefill.result;
        if (prefill.user     && filterUser)     filterUser.value     = prefill.user;
        if (prefill.dateFrom && filterDateFrom) filterDateFrom.value = prefill.dateFrom;
        if (prefill.dateTo   && filterDateTo)   filterDateTo.value   = prefill.dateTo;
        if (prefill.blocked  && filterBlocked)  filterBlocked.checked = true;

        applyFilters();
    })();
});
