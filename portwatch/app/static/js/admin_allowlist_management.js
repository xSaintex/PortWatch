/*
 * admin_allowlist_management.js
 * Client-side logic for the Allowlist Management page (/admin/allowlist).
 *
 * OVERVIEW STATE  (/admin/allowlist, no device selected):
 *   1. Filter buttons (All / Needs setup / Configured) — mark rows with
 *      pw-filtered-out, then call refreshPagination.
 *   2. Pagination via the shared initTablePagination — 15 rows per page.
 *   3. Empty state when a filter matches nothing.
 *
 * MANAGE STATE  (/admin/allowlist?device_id=<id>):
 *   4. Live search filter on entries table → marks pw-filtered-out → refreshPagination.
 *   5. Pagination — 8 entries per page.
 *   6. New-entry row highlight + scroll + URL cleanup (same as Device Registry).
 *   7. Add/Edit entry modal:
 *        - ADD  mode: reset all fields, restore Add URL, hide hints.
 *        - EDIT mode: prefill every field from data-* attributes on the trigger
 *          button, set form action to the edit URL, show port hints.
 *        - Auto-open on server validation error (window.allowlistState.openEntryModal).
 *        - Port auto-fill hint and risky warning box.
 *        - Notes character counter.
 *        - Submit spinner to prevent double-clicks.
 *   8. Delete entry modal: fill confirmation text and form action from
 *      data-* attributes on the trigger button.
 *   9. Copy modal: preview table populated from window.allowlistEntriesByDevice,
 *      Replace warning shown/hidden based on selected mode.
 *
 * FILTER + PAGINATION CONTRACT (same as Device Registry):
 *   Filters add "pw-filtered-out" to non-matching rows and call
 *   window.refreshPagination[tableId]() so pagination re-slices.
 *   Pagination (table_pagination.js) controls row.style.display.
 */

document.addEventListener("DOMContentLoaded", function () {

    const S = window.allowlistState || {};


    // ================================================================ //
    // ---------------------------------------------------------------- //
    // STATE 1: OVERVIEW                                                 //
    // ---------------------------------------------------------------- //
    // ================================================================ //
    if (!S.hasDevice) {

        const tableBody   = document.getElementById("overviewTableBody");
        const filterBtns  = document.querySelectorAll(".pw-filter-tab");
        const noResults   = document.getElementById("noOverviewResults");

        // Current active filter — start on "all"
        let currentFilter = "all";

        // ---- Apply filter ----------------------------------------- //
        function applyOverviewFilter(filter) {
            currentFilter = filter;
            if (!tableBody) return;

            const rows = tableBody.querySelectorAll(".pw-overview-row");
            let matchCount = 0;

            rows.forEach(function (row) {
                const hasEntries = row.dataset.hasEntries === "yes";
                let visible = true;
                if (filter === "needs-setup") visible = !hasEntries;
                if (filter === "configured")  visible = hasEntries;

                if (visible) {
                    row.classList.remove("pw-filtered-out");
                    matchCount++;
                } else {
                    row.classList.add("pw-filtered-out");
                    row.style.display = "none";   // hide immediately for responsiveness
                }
            });

            // Show/hide empty state
            if (noResults) {
                noResults.style.display = matchCount === 0 ? "flex" : "none";
            }

            // Tell pagination to re-slice from page 1
            if (window.refreshPagination && window.refreshPagination["overviewTable"]) {
                window.refreshPagination["overviewTable"]();
            }
        }

        // ---- Wire filter buttons ---------------------------------- //
        filterBtns.forEach(function (btn) {
            btn.addEventListener("click", function () {
                // Toggle active style
                filterBtns.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                applyOverviewFilter(btn.dataset.filter);
            });
        });

        // ---- Initialise pagination — 15 rows per page ------------- //
        try {
            if (typeof initTablePagination === "function") {
                initTablePagination("overviewTable", {
                    pageSize:     15,
                    itemWord:     "devices",
                    paginationId: "overviewPagination",
                });
            }
        } catch (e) {
            console.warn("PortWatch: overview pagination init failed:", e);
        }

        return;   // nothing else needed in the overview state
    }


    // ================================================================ //
    // ---------------------------------------------------------------- //
    // STATE 2: MANAGE VIEW                                              //
    // ---------------------------------------------------------------- //
    // ================================================================ //

    const entriesTableBody = document.getElementById("entriesTableBody");
    const searchInput      = document.getElementById("entrySearch");
    const noEntryResults   = document.getElementById("noEntryResults");
    const clearSearchBtn   = document.getElementById("clearEntrySearch");


    // ---------------------------------------------------------------- //
    // 4. LIVE SEARCH FILTER                                             //
    // ---------------------------------------------------------------- //
    function applySearch() {
        if (!entriesTableBody) return;

        const term = searchInput ? searchInput.value.toLowerCase().trim() : "";
        const rows = entriesTableBody.querySelectorAll(".pw-entry-row");
        let count  = 0;

        rows.forEach(function (row) {
            const text    = row.dataset.search || "";
            const matches = !term || text.includes(term);

            if (matches) {
                row.classList.remove("pw-filtered-out");
                count++;
            } else {
                row.classList.add("pw-filtered-out");
                row.style.display = "none";
            }
        });

        if (noEntryResults) {
            noEntryResults.style.display = (count === 0 && term) ? "flex" : "none";
        }

        // Reset to page 1 on every search change
        if (window.refreshPagination && window.refreshPagination["entriesTable"]) {
            window.refreshPagination["entriesTable"]();
        }
    }

    if (searchInput)  searchInput.addEventListener("input", applySearch);
    if (clearSearchBtn) {
        clearSearchBtn.addEventListener("click", function () {
            if (searchInput) searchInput.value = "";
            applySearch();
        });
    }


    // ---------------------------------------------------------------- //
    // 5. PAGINATION — 8 entries per page                               //
    // ---------------------------------------------------------------- //
    try {
        if (typeof initTablePagination === "function") {
            initTablePagination("entriesTable", {
                pageSize:     8,
                itemWord:     "entries",
                paginationId: "entriesPagination",
            });
        }
    } catch (e) {
        console.warn("PortWatch: entries pagination init failed:", e);
    }


    // ---------------------------------------------------------------- //
    // 6. NEW-ENTRY HIGHLIGHT                                            //
    // ---------------------------------------------------------------- //
    if (S.newEntryId) {
        // Clear any active search so the highlighted row is visible
        if (searchInput) searchInput.value = "";
        applySearch();

        const newRow = entriesTableBody
            ? entriesTableBody.querySelector(`tr[data-entry-id="${S.newEntryId}"]`)
            : null;

        if (newRow) {
            requestAnimationFrame(function () {
                newRow.scrollIntoView({ behavior: "smooth", block: "center" });
            });
        }

        // Remove ?new_entry=... from the URL without a reload
        history.replaceState(null, "",
            window.location.pathname + "?device_id=" + S.deviceId);
        S.newEntryId = null;
    }


    // ---------------------------------------------------------------- //
    // 7. ADD / EDIT ENTRY MODAL                                         //
    // ---------------------------------------------------------------- //
    const entryModal = document.getElementById("entryFormModal");
    const portRef    = S.portReference || {};

    // Helper: show/hide the port hint and risky warning box
    function updatePortHints(portVal, svcEl, autoFill) {
        const portHint  = document.getElementById("portHint");
        const riskyBox  = document.getElementById("riskyWarning");
        const riskyText = document.getElementById("riskyWarningText");
        const port      = parseInt(portVal, 10);

        if (!port || port < 1 || port > 65535) {
            if (portHint) portHint.style.display = "none";
            if (riskyBox) riskyBox.style.display = "none";
            return;
        }

        const info = portRef[port];
        if (!info) {
            if (portHint) portHint.style.display = "none";
            if (riskyBox) riskyBox.style.display = "none";
            return;
        }

        // Port hint line
        if (portHint) {
            portHint.textContent =
                "Common service: " + info.service + " — " + info.description;
            portHint.style.display = "";
        }

        // Auto-fill service name only when the field is still empty
        if (autoFill && svcEl && !svcEl.value.trim()) {
            svcEl.value = info.service;
        }

        // Risky warning
        if (riskyBox && riskyText) {
            if (info.is_risky) {
                riskyText.textContent =
                    "Port " + port + " (" + info.service +
                    ") is a high-risk service: " + info.risk_reason + " ";
                riskyBox.style.display = "";
            } else {
                riskyBox.style.display = "none";
            }
        }
    }

    function hidePortHints() {
        const portHint = document.getElementById("portHint");
        const riskyBox = document.getElementById("riskyWarning");
        if (portHint) portHint.style.display = "none";
        if (riskyBox) riskyBox.style.display = "none";
    }

    if (entryModal) {
        const entryForm = document.getElementById("entryForm");

        // Store the Add URL once so Edit mode can change action and we can restore it
        if (entryForm) entryForm.dataset.addUrl = entryForm.action;

        // -------------------------------------------------------------- //
        // show.bs.modal fires before the modal becomes visible.           //
        // event.relatedTarget is the button that triggered the modal.     //
        // -------------------------------------------------------------- //
        entryModal.addEventListener("show.bs.modal", function (event) {
            const btn  = event.relatedTarget;
            // btn is null when we call bsModal.show() programmatically (auto-open)
            if (!btn) return;

            const mode = btn.dataset.mode;   // "add" or "edit"

            const titleEl    = document.getElementById("entryFormModalLabel");
            const subtitleEl = document.getElementById("entryFormSubtitle");
            const submitText = document.getElementById("entryFormBtnText");
            const portInput  = document.getElementById("entryPort");
            const protoSel   = document.getElementById("entryProtocol");
            const svcInput   = document.getElementById("entryService");
            const expToggle  = document.getElementById("entryExpected");
            const notesArea  = document.getElementById("entryNotes");
            const counter    = document.getElementById("entryNotesCounter");
            const form       = document.getElementById("entryForm");

            if (mode === "edit") {
                // ---- EDIT: prefill every field from data-* attributes ---- //
                if (titleEl)    titleEl.textContent    = "Edit Approved Port";
                if (subtitleEl) subtitleEl.textContent =
                    "for " + S.deviceName + " (" + S.deviceIp + ")";
                if (submitText) submitText.innerHTML   =
                    '<i class="bi bi-check-lg me-1"></i> Save Changes';

                // Point the form at this specific entry's edit route
                if (form) form.action = btn.dataset.editUrl || form.action;

                // Prefill fields
                if (portInput) portInput.value  = btn.dataset.entryPort     || "";
                if (svcInput)  svcInput.value   = btn.dataset.entryService  || "";
                if (notesArea) notesArea.value  = btn.dataset.entryNotes    || "";
                if (counter)   counter.textContent = notesArea ? notesArea.value.length : 0;

                // Expected-open toggle
                // data-entry-expected is the string "true" or "false"
                if (expToggle) {
                    expToggle.checked = (btn.dataset.entryExpected === "true");
                }

                // Protocol select
                if (protoSel) {
                    const proto = btn.dataset.entryProtocol || "tcp";
                    for (let i = 0; i < protoSel.options.length; i++) {
                        if (protoSel.options[i].value === proto) {
                            protoSel.selectedIndex = i;
                            break;
                        }
                    }
                }

                // Show port hint / risky warning for the prefilled port
                // Pass false for autoFill — service is already prefilled
                if (portInput) updatePortHints(portInput.value, svcInput, false);

                // Clear previous Bootstrap validation state
                if (form) {
                    form.classList.remove("was-validated");
                    form.querySelectorAll(".is-invalid").forEach(el =>
                        el.classList.remove("is-invalid"));
                    form.querySelectorAll(".invalid-feedback.d-block").forEach(el =>
                        el.classList.remove("d-block"));
                }

            } else {
                // ---- ADD: reset everything to empty defaults ---- //
                if (titleEl)    titleEl.textContent    = "Add Approved Port";
                if (subtitleEl) subtitleEl.textContent =
                    "for " + S.deviceName + " (" + S.deviceIp + ")";
                if (submitText) submitText.innerHTML   =
                    '<i class="bi bi-check-lg me-1"></i> Save Port';

                // Restore the Add URL
                if (form) form.action = form.dataset.addUrl || form.action;

                // Only reset if there are no server validation errors already shown.
                // When S.openEntryModal is true, Jinja already pre-filled the form.
                if (!S.openEntryModal) {
                    if (form) {
                        form.reset();
                        form.classList.remove("was-validated");
                        form.querySelectorAll(".is-invalid").forEach(el =>
                            el.classList.remove("is-invalid"));
                        form.querySelectorAll(".invalid-feedback.d-block").forEach(el =>
                            el.classList.remove("d-block"));
                        if (counter) counter.textContent = "0";
                        hidePortHints();
                    }
                }
            }
        });

        // ---- Notes live counter ---- //
        const notesArea = document.getElementById("entryNotes");
        const counter   = document.getElementById("entryNotesCounter");
        if (notesArea && counter) {
            notesArea.addEventListener("input", function () {
                counter.textContent = notesArea.value.length;
            });
        }

        // ---- Port input → auto-fill + hints ---- //
        const portInput = document.getElementById("entryPort");
        const svcInput  = document.getElementById("entryService");
        if (portInput) {
            portInput.addEventListener("input", function () {
                // autoFill = true: fill service name when typing in Add mode
                updatePortHints(portInput.value, svcInput, true);
            });
        }

        // ---- Submit spinner (prevent double-click) ---- //
        const submitBtn  = document.getElementById("entryFormSubmitBtn");
        const btnText    = document.getElementById("entryFormBtnText");
        const btnSpinner = document.getElementById("entryFormBtnSpinner");

        if (entryForm) {
            entryForm.addEventListener("submit", function (event) {
                if (!entryForm.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                    entryForm.classList.add("was-validated");
                    return;
                }
                entryForm.classList.add("was-validated");
                if (submitBtn)  submitBtn.disabled = true;
                if (btnText)    btnText.classList.add("d-none");
                if (btnSpinner) btnSpinner.classList.remove("d-none");
            });
        }

        // ---- Auto-open on server validation error ---- //
        if (S.openEntryModal) {
            const bsModal = new bootstrap.Modal(entryModal);
            bsModal.show();
            S.openEntryModal = false;
            // Re-show port hints for the server-preserved value
            if (portInput) updatePortHints(portInput.value, svcInput, false);
        }
    }


    // ---------------------------------------------------------------- //
    // 8. DELETE ENTRY MODAL                                             //
    // ---------------------------------------------------------------- //
    const deleteModal = document.getElementById("deleteEntryModal");
    if (deleteModal) {
        deleteModal.addEventListener("show.bs.modal", function (event) {
            const btn = event.relatedTarget;
            if (!btn) return;

            const portEl   = document.getElementById("deleteEntryPort");
            const protoEl  = document.getElementById("deleteEntryProtocol");
            const svcEl    = document.getElementById("deleteEntryService");
            const devEl    = document.getElementById("deleteEntryDevice");
            const delForm  = document.getElementById("deleteEntryForm");

            if (portEl)  portEl.textContent  = btn.dataset.entryPort     || "";
            if (protoEl) protoEl.textContent  = (btn.dataset.entryProtocol || "").toUpperCase();
            if (svcEl)   svcEl.textContent   = btn.dataset.entryService  || "";
            if (devEl)   devEl.textContent   = btn.dataset.deviceName    || "this device";

            // Set the form action to this entry's specific delete URL
            if (delForm) delForm.action = btn.dataset.deleteUrl || "#";
        });
    }


    // ---------------------------------------------------------------- //
    // 9. COPY MODAL                                                     //
    // ---------------------------------------------------------------- //
    const copyModal      = document.getElementById("copyModal");
    const sourceSel      = document.getElementById("copySourceDevice");
    const previewWrap    = document.getElementById("copyPreviewWrap");
    const previewBody    = document.getElementById("copyPreviewBody");
    const previewEmpty   = document.getElementById("copyPreviewEmpty");
    const replaceWarn    = document.getElementById("replaceWarning");
    const modeReplace    = document.getElementById("modeReplace");
    const modeMerge      = document.getElementById("modeMerge");
    const allEntries     = window.allowlistEntriesByDevice || {};

    if (sourceSel) {
        sourceSel.addEventListener("change", function () {
            const srcId   = parseInt(sourceSel.value, 10);
            const entries = allEntries[srcId] || [];

            if (!previewBody) return;
            previewBody.innerHTML = "";

            if (entries.length === 0) {
                if (previewWrap)  previewWrap.style.display  = "none";
                if (previewEmpty) previewEmpty.style.display = "";
                return;
            }

            if (previewEmpty) previewEmpty.style.display = "none";
            if (previewWrap)  previewWrap.style.display  = "";

            entries.forEach(function (e) {
                const tr = document.createElement("tr");
                tr.innerHTML =
                    `<td class="pw-mono fw-bold">${e.port}</td>` +
                    `<td><span class="pw-proto-badge pw-proto-${e.protocol}">${e.protocol.toUpperCase()}</span></td>` +
                    `<td class="pw-mono">${e.service}</td>` +
                    `<td>${e.expected_open
                        ? '<span class="pw-badge-required">Required</span>'
                        : '<span class="pw-text-muted small">Optional</span>'}</td>`;
                previewBody.appendChild(tr);
            });
        });
    }

    if (modeReplace) {
        modeReplace.addEventListener("change", function () {
            if (replaceWarn) replaceWarn.style.display = modeReplace.checked ? "" : "none";
        });
    }
    if (modeMerge) {
        modeMerge.addEventListener("change", function () {
            if (replaceWarn) replaceWarn.style.display = "none";
        });
    }

    if (copyModal) {
        copyModal.addEventListener("hidden.bs.modal", function () {
            if (sourceSel)   sourceSel.value         = "";
            if (previewBody) previewBody.innerHTML   = "";
            if (previewWrap) previewWrap.style.display = "none";
            if (previewEmpty) previewEmpty.style.display = "none";
            if (replaceWarn) replaceWarn.style.display = "none";
            if (modeMerge)   modeMerge.checked       = true;
        });

        if (S.openCopyModal) {
            const bsCopy = new bootstrap.Modal(copyModal);
            bsCopy.show();
        }
    }

});
