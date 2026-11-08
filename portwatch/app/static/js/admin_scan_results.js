/*
 * admin_scan_results.js
 * Client-side logic for the Scan Results page (/admin/scans/<scan_id>).
 *
 * Responsibilities:
 *   1. Label filter tabs (All / Approved / Unexpected / Risky / Missing)
 *      — marks non-matching rows with "pw-filtered-out", resets pagination.
 *      Detail rows follow their parent row's visibility.
 *   2. Pagination — 8 findings per page via the shared initTablePagination.
 *      Works together with the label filters.
 *   3. Expand/collapse chevron — toggles the detail row below each finding.
 *   4. Nmap command copy button.
 */

document.addEventListener("DOMContentLoaded", function () {

    // ================================================================ //
    // 1. LABEL FILTER TABS
    // ================================================================ //

    const labelBtns   = document.querySelectorAll("#labelFilterBtns .pw-filter-tab");
    const tableBody   = document.getElementById("findingsTableBody");
    const noFindingEl = document.getElementById("noFindingResults");

    function applyLabelFilter(label) {
        if (!tableBody) return;

        // Select only the main data rows (not the detail rows)
        const rows = tableBody.querySelectorAll(".pw-finding-row:not(.pw-finding-detail)");
        let matchCount = 0;

        rows.forEach(function (row) {
            const rowLabel  = row.dataset.label || "";
            const matches   = (label === "all" || rowLabel === label);
            const detailRow = row.nextElementSibling;   // the expand detail row

            if (matches) {
                row.classList.remove("pw-filtered-out");
                matchCount++;
                // Detail row follows its parent — keep it hidden until expanded
                if (detailRow && detailRow.classList.contains("pw-finding-detail")) {
                    detailRow.classList.remove("pw-filtered-out");
                    // Don't un-hide if it was closed (user hasn't expanded it)
                }
            } else {
                row.classList.add("pw-filtered-out");
                row.style.display = "none";
                if (detailRow && detailRow.classList.contains("pw-finding-detail")) {
                    detailRow.classList.add("pw-filtered-out");
                    detailRow.style.display = "none";
                }
            }
        });

        if (noFindingEl) {
            noFindingEl.style.display = matchCount === 0 ? "flex" : "none";
        }

        // Tell pagination to re-slice from page 1
        if (window.refreshPagination && window.refreshPagination["findingsTable"]) {
            window.refreshPagination["findingsTable"]();
        }
    }

    labelBtns.forEach(function (btn) {
        btn.addEventListener("click", function () {
            labelBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            applyLabelFilter(btn.dataset.label);
        });
    });


    // ================================================================ //
    // 2. PAGINATION — 8 findings per page
    //    NOTE: pagination must only page over the main data rows, not
    //    the detail rows. The detail rows are hidden/shown by the expand
    //    logic, not by pagination. We solve this by marking them with
    //    "pw-filtered-out" so pagination ignores them, then the expand
    //    logic controls them separately.
    // ================================================================ //

    // Pre-mark all detail rows so pagination skips them
    if (tableBody) {
        tableBody.querySelectorAll(".pw-finding-detail").forEach(function (row) {
            row.classList.add("pw-filtered-out");
        });
    }

    try {
        if (typeof initTablePagination === "function") {
            initTablePagination("findingsTable", {
                pageSize:     8,
                itemWord:     "findings",
                paginationId: "findingsPagination",
            });
        }
    } catch (e) {
        console.warn("PortWatch: findings pagination init failed:", e);
    }


    // ================================================================ //
    // 3. EXPAND / COLLAPSE CHEVRON
    // ================================================================ //

    if (tableBody) {
        // Use event delegation so it works after pagination changes visibility
        tableBody.addEventListener("click", function (event) {
            const btn = event.target.closest(".pw-expand-btn");
            if (!btn) return;

            const row       = btn.closest("tr");
            const detailRow = row ? row.nextElementSibling : null;
            if (!detailRow || !detailRow.classList.contains("pw-finding-detail")) return;

            const isOpen = btn.getAttribute("aria-expanded") === "true";

            if (isOpen) {
                // Collapse
                detailRow.style.display = "none";
                btn.setAttribute("aria-expanded", "false");
                const icon = btn.querySelector("i");
                if (icon) { icon.classList.remove("bi-chevron-down"); icon.classList.add("bi-chevron-right"); }
            } else {
                // Expand — only if the parent row is visible (on the current page)
                detailRow.style.display = "";
                btn.setAttribute("aria-expanded", "true");
                const icon = btn.querySelector("i");
                if (icon) { icon.classList.remove("bi-chevron-right"); icon.classList.add("bi-chevron-down"); }
            }
        });
    }


    // ================================================================ //
    // 4. NMAP COMMAND COPY BUTTON
    // ================================================================ //

    const copyBtn = document.getElementById("copyNmapBtn");
    const cmdEl   = document.getElementById("nmapCmdText");

    if (copyBtn && cmdEl) {
        copyBtn.addEventListener("click", function () {
            const text = cmdEl.textContent.trim().replace(/\s+/g, " ");
            navigator.clipboard.writeText(text).then(function () {
                copyBtn.innerHTML = '<i class="bi bi-clipboard-check"></i>';
                setTimeout(function () {
                    copyBtn.innerHTML = '<i class="bi bi-clipboard"></i>';
                }, 1500);
            });
        });
    }

});
