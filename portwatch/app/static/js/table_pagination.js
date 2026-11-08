/*
 * table_pagination.js
 * Reusable client-side pagination for any PortWatch data table.
 *
 * BEHAVIOUR (updated):
 *   - The "Showing X–Y of Z items" text is ALWAYS visible (one page or many).
 *     This is the single authoritative count for every table; per-table
 *     "Showing X of Y" labels in filter bars have been removed.
 *   - When there is only ONE page: show the info text, hide the buttons.
 *   - When there are ZERO matching rows: hide the entire pagination bar
 *     (the empty-state message takes over).
 *
 * FILTER INTEGRATION CONTRACT:
 *   - Filters mark non-matching rows with "pw-filtered-out". They do NOT
 *     set row.style.display.
 *   - When filters change, call: window.refreshPagination["tableId"]()
 *   - Pagination owns row.style.display for its current page slice.
 */

function initTablePagination(tableId, options) {
    const cfg = Object.assign(
        { pageSize: 8, itemWord: "items", paginationId: tableId + "Pagination" },
        options
    );

    const table      = document.getElementById(tableId);
    const mountPoint = document.getElementById(cfg.paginationId);

    if (!table || !mountPoint) return;

    let currentPage = 1;

    // ---------------------------------------------------------------- //
    // CORE RENDER
    // ---------------------------------------------------------------- //
    function render() {
        const tbody = table.querySelector("tbody");
        if (!tbody) return;

        const allRows      = Array.from(tbody.querySelectorAll("tr"));
        const eligibleRows = allRows.filter(r => !r.classList.contains("pw-filtered-out"));
        const total        = eligibleRows.length;
        const totalPages   = Math.max(1, Math.ceil(total / cfg.pageSize));

        if (currentPage > totalPages) currentPage = totalPages;

        const startIdx = (currentPage - 1) * cfg.pageSize;
        const endIdx   = startIdx + cfg.pageSize;

        // Show only the current-page slice
        allRows.forEach(function (row) { row.style.display = "none"; });
        eligibleRows.forEach(function (row, idx) {
            if (idx >= startIdx && idx < endIdx) {
                row.style.display = "";
            }
        });

        // Hide any lingering tooltips before changing which rows are visible.
        // Without this, a tooltip attached to a hidden row can stay on screen.
        if (typeof window.hideAllTooltips === "function") {
            window.hideAllTooltips();
        }

        // ── Zero results: hide the whole bar (empty state takes over) ──
        if (total === 0) {
            mountPoint.style.display = "none";
            mountPoint.innerHTML     = "";
            return;
        }

        // ── One or more pages: always show the info text ──────────────
        const showingFrom = startIdx + 1;
        const showingTo   = Math.min(endIdx, total);
        const infoText    = `Showing ${showingFrom}–${showingTo} of ${total} ${cfg.itemWord}`;

        let buttonsHtml = "";

        if (totalPages > 1) {
            // Previous
            buttonsHtml += `<button class="pw-page-btn pw-page-prev" data-page="prev"
                ${currentPage === 1 ? "disabled" : ""} aria-label="Previous page">
                <i class="bi bi-chevron-left"></i></button>`;

            // Numbered buttons with "…" collapse
            buildPageNumbers(currentPage, totalPages).forEach(function (p) {
                if (p === "…") {
                    buttonsHtml += `<span class="pw-page-ellipsis">…</span>`;
                } else {
                    buttonsHtml += `<button class="pw-page-btn ${p === currentPage ? "active" : ""}"
                        data-page="${p}" aria-label="Page ${p}"
                        ${p === currentPage ? 'aria-current="page"' : ""}>${p}</button>`;
                }
            });

            // Next
            buttonsHtml += `<button class="pw-page-btn pw-page-next" data-page="next"
                ${currentPage === totalPages ? "disabled" : ""} aria-label="Next page">
                <i class="bi bi-chevron-right"></i></button>`;
        }
        // If totalPages === 1, buttonsHtml stays empty → only the info text is shown

        mountPoint.innerHTML = `
            <span class="pw-pagination-info">${infoText}</span>
            ${buttonsHtml
                ? `<div class="pw-pagination-controls" role="navigation" aria-label="Table pagination">${buttonsHtml}</div>`
                : ""}`;

        // Attach click handlers to the freshly rendered buttons
        mountPoint.querySelectorAll(".pw-page-btn").forEach(function (btn) {
            btn.addEventListener("click", function () {
                const target = btn.dataset.page;
                if (target === "prev" && currentPage > 1)              currentPage--;
                else if (target === "next" && currentPage < totalPages) currentPage++;
                else if (!isNaN(parseInt(target)))                     currentPage = parseInt(target);
                render();
            });
        });

        mountPoint.style.display = "flex";
    }

    // ---------------------------------------------------------------- //
    // PAGE NUMBERS — collapses long sequences with "…"
    // ---------------------------------------------------------------- //
    function buildPageNumbers(current, total) {
        if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);

        const pages = new Set([1, total, current]);
        if (current > 1) pages.add(current - 1);
        if (current < total) pages.add(current + 1);

        const sorted = Array.from(pages).sort((a, b) => a - b);
        const result = [];
        sorted.forEach(function (p, i) {
            if (i > 0 && p - sorted[i - 1] > 1) result.push("…");
            result.push(p);
        });
        return result;
    }

    // ---------------------------------------------------------------- //
    // PUBLIC REFRESH — resets to page 1 and re-renders
    // ---------------------------------------------------------------- //
    function refresh() {
        currentPage = 1;
        render();
    }

    if (!window.refreshPagination) window.refreshPagination = {};
    window.refreshPagination[tableId] = refresh;

    render();
}
