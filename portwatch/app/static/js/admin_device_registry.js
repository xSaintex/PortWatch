/*
 * admin_device_registry.js
 * Client-side logic for the Device Registry page (/admin/devices).
 *
 * Responsibilities:
 *   1. Live filter — search by name/IP, dropdown by lab and status.
 *   2. Clear filters.
 *   3. Auto-open the Add Device modal on page load when the server
 *      re-renders after a validation error (window.openDeviceModalOnLoad).
 *   4. Add/Edit modal setup — prefill fields for Edit mode, reset for Add mode,
 *      submit-spinner to prevent double-clicks, per-field client-side validation.
 *   5. Delete modal prefill.
 *
 * FILTER + PAGINATION INTEGRATION:
 *   Filters must NOT use row.style.display directly. Instead they add/remove
 *   the class "pw-filtered-out" on non-matching rows. The pagination script
 *   (table_pagination.js) reads that class to know which rows are eligible.
 *   After every filter change we call:
 *       window.refreshPagination["devicesTable"]()
 *   which tells pagination to re-slice from page 1 using only eligible rows.
 */

document.addEventListener("DOMContentLoaded", function () {

    // ================================================================ //
    // ELEMENT REFERENCES
    // ================================================================ //
    const searchInput  = document.getElementById("deviceSearch");
    const filterLab    = document.getElementById("filterLab");
    const filterStatus = document.getElementById("filterStatus");
    const clearBtn     = document.getElementById("clearFilters");
    const clearBtn2    = document.getElementById("clearFilters2");
    const countLabel   = document.getElementById("deviceCount");
    const tableBody    = document.getElementById("devicesTableBody");
    const noResults    = document.getElementById("noFilterResults");

    const totalCount = window.totalDeviceCount || 0;


    // ================================================================ //
    // 1. FILTER LOGIC
    // Mark non-matching rows with "pw-filtered-out" (NOT display:none).
    // Pagination will then only count/show rows without that class.
    // ================================================================ //

    function applyFilters() {
        if (!tableBody) return;

        const searchTerm   = searchInput  ? searchInput.value.toLowerCase().trim() : "";
        const labFilter    = filterLab    ? filterLab.value.toLowerCase()           : "";
        const statusFilter = filterStatus ? filterStatus.value.toLowerCase()        : "";

        const rows = tableBody.querySelectorAll(".pw-device-row");
        let matchCount = 0;

        rows.forEach(function (row) {
            const name   = row.dataset.name   || "";
            const ip     = row.dataset.ip     || "";
            const lab    = row.dataset.lab    || "";
            const status = row.dataset.status || "";

            const matchesSearch = !searchTerm   || name.includes(searchTerm) || ip.includes(searchTerm);
            const matchesLab    = !labFilter    || lab === labFilter;
            const matchesStatus = !statusFilter || status === statusFilter;

            if (matchesSearch && matchesLab && matchesStatus) {
                // Row passes all filters — remove the exclusion class
                row.classList.remove("pw-filtered-out");
                matchCount++;
            } else {
                // Row does not pass — mark it so pagination skips it
                row.classList.add("pw-filtered-out");
                // Also hide it immediately so it is not visible
                row.style.display = "none";
            }
        });

        // Update the "Showing X of Y" label in the filter bar
        if (countLabel) {
            countLabel.textContent =
                `Showing ${matchCount} of ${totalCount} device${totalCount !== 1 ? "s" : ""}`;
        }

        // Show the "no results" empty state only when everything is filtered out
        if (noResults) {
            noResults.style.display = matchCount === 0 ? "flex" : "none";
        }

        // Tell pagination to rebuild from page 1 using the new eligible set
        if (window.refreshPagination && window.refreshPagination["devicesTable"]) {
            window.refreshPagination["devicesTable"]();
        }
    }

    if (searchInput)  searchInput.addEventListener("input",  applyFilters);
    if (filterLab)    filterLab.addEventListener("change",   applyFilters);
    if (filterStatus) filterStatus.addEventListener("change", applyFilters);


    // ================================================================ //
    // 2. CLEAR FILTERS
    // ================================================================ //

    function clearAllFilters() {
        if (searchInput)  searchInput.value  = "";
        if (filterLab)    filterLab.value    = "";
        if (filterStatus) filterStatus.value = "";
        applyFilters();
    }

    if (clearBtn)  clearBtn.addEventListener("click",  clearAllFilters);
    if (clearBtn2) clearBtn2.addEventListener("click", clearAllFilters);


    // ================================================================ //
    // 3. PAGINATION INIT
    // Called after filter setup so the initial render is correct.
    // Guard with try/catch so a pagination error never breaks the modal.
    // ================================================================ //
    try {
        if (typeof initTablePagination === "function") {
            initTablePagination("devicesTable", {
                pageSize:     8,
                itemWord:     "devices",
                paginationId: "devicesPagination",
            });
        }
    } catch (e) {
        console.warn("PortWatch: pagination init failed:", e);
    }


    // ================================================================ //
    // 3b. NEW DEVICE HIGHLIGHT
    // When the page loads after a successful add, window.newDeviceId is
    // set to the new device's id (passed from Flask via the template).
    //
    // Steps:
    //   1. Clear all active filters so nothing is hidden.
    //   2. Force pagination to show page 1 (the new row is first because
    //      get_all_devices() sorts by created_at DESC).
    //   3. Scroll the highlighted row smoothly into view.
    //   4. Remove ?new_device=... from the browser URL without a page
    //      reload (history.replaceState) so a refresh does not re-highlight.
    // ================================================================ //
    if (window.newDeviceId) {
        // Step 1: clear any active search / filter values and re-apply
        // so every row is eligible before pagination slices them.
        clearAllFilters();   // already defined above; resets inputs + calls applyFilters

        // Step 2: pagination was already initialised above. After
        // clearAllFilters() called applyFilters() which called
        // refreshPagination, so page 1 is already active. Nothing extra needed.

        // Step 3: find the highlighted row by its data-device-id attribute
        // and scroll it into view once the browser has painted.
        const newRow = tableBody
            ? tableBody.querySelector(`tr[data-device-id="${window.newDeviceId}"]`)
            : null;

        if (newRow) {
            // requestAnimationFrame waits for the layout to settle before scrolling
            requestAnimationFrame(function () {
                newRow.scrollIntoView({ behavior: "smooth", block: "center" });
            });
        }

        // Step 4: strip ?new_device=... from the address bar.
        // history.replaceState changes what the URL bar shows without
        // triggering a page load or a back-button entry.
        const cleanUrl = window.location.pathname;   // /admin/devices (no query string)
        history.replaceState(null, "", cleanUrl);

        // Clear the JS variable so nothing runs again if other code
        // happens to call DOMContentLoaded logic a second time.
        window.newDeviceId = null;
    }


    // ================================================================ //
    // 4. ADD / EDIT MODAL
    // ================================================================ //

    const deviceFormModal = document.getElementById("deviceFormModal");

    if (deviceFormModal) {

        // Store the Add URL on the form so we can restore it after Edit mode
        const form = document.getElementById("deviceForm");
        if (form) form.dataset.addUrl = form.action;

        deviceFormModal.addEventListener("show.bs.modal", function (event) {
            const triggerBtn = event.relatedTarget;
            // relatedTarget is null when we open programmatically (auto-open on error)
            if (!triggerBtn) return;

            const mode = triggerBtn.dataset.mode;

            const titleEl    = document.getElementById("deviceFormModalLabel");
            const subtitleEl = document.getElementById("deviceFormSubtitle");
            const submitText = document.getElementById("deviceFormBtnText");
            const nameInput  = document.getElementById("deviceName");
            const ipInput    = document.getElementById("deviceIp");
            const labInput   = document.getElementById("deviceLab");
            const typeSelect = document.getElementById("deviceType");
            const statusChk  = document.getElementById("deviceStatus");
            const notesArea  = document.getElementById("deviceNotes");
            const counter    = document.getElementById("notesCounter");

            if (mode === "edit") {
                // ---- EDIT MODE ----
                if (titleEl)    titleEl.textContent    = "Edit Device";
                if (subtitleEl) subtitleEl.textContent = "Update the details for this registered device.";
                if (submitText) submitText.innerHTML   =
                    '<i class="bi bi-check-lg me-1"></i> Save Changes';

                // Point the form at this device's edit URL
                if (form) form.action = triggerBtn.dataset.editUrl || form.action;

                // Prefill fields from data-* attributes on the Edit button
                if (nameInput)  nameInput.value  = triggerBtn.dataset.deviceName  || "";
                if (ipInput)    ipInput.value    = triggerBtn.dataset.deviceIp    || "";
                if (labInput)   labInput.value   = triggerBtn.dataset.deviceLab   || "";
                if (notesArea)  notesArea.value  = triggerBtn.dataset.deviceNotes || "";
                if (counter)    counter.textContent = notesArea ? notesArea.value.length : 0;

                // Set the correct device type option
                if (typeSelect) {
                    const typeValue = triggerBtn.dataset.deviceType || "";
                    for (let i = 0; i < typeSelect.options.length; i++) {
                        if (typeSelect.options[i].value === typeValue) {
                            typeSelect.selectedIndex = i;
                            break;
                        }
                    }
                }

                // Set status toggle
                if (statusChk) {
                    statusChk.checked = (triggerBtn.dataset.deviceStatus === "active");
                }

            } else {
                // ---- ADD MODE ----
                if (titleEl)    titleEl.textContent    = "Add Device";
                if (subtitleEl) subtitleEl.textContent =
                    "Register a lab device so PortWatch is authorized to scan it.";
                if (submitText) submitText.innerHTML   =
                    '<i class="bi bi-check-lg me-1"></i> Save Device';

                // Restore the Add URL
                if (form) form.action = form.dataset.addUrl || form.action;

                // Only reset the form in Add mode if there are no server errors already
                // shown (those were pre-filled by Jinja on the server side).
                if (!window.openDeviceModalOnLoad) {
                    if (form) {
                        form.reset();
                        form.classList.remove("was-validated");
                        form.querySelectorAll(".is-invalid").forEach(function (el) {
                            el.classList.remove("is-invalid");
                        });
                        form.querySelectorAll(".invalid-feedback.d-block").forEach(function (el) {
                            el.classList.remove("d-block");
                        });
                        if (counter) counter.textContent = "0";
                    }
                }
            }
        });

        // Live notes counter (works for both add and edit)
        const notesArea = document.getElementById("deviceNotes");
        const counter   = document.getElementById("notesCounter");
        if (notesArea && counter) {
            notesArea.addEventListener("input", function () {
                counter.textContent = notesArea.value.length;
            });
        }

        // Client-side per-field validation on blur (when a field loses focus)
        const fieldsToValidate = [
            { id: "deviceName", check: v => v.trim().length > 0 && v.length <= 50 },
            { id: "deviceIp",   check: v => /^(\d{1,3}\.){3}\d{1,3}$/.test(v.trim()) },
            { id: "deviceLab",  check: v => v.trim().length > 0 },
            { id: "deviceType", check: v => v.length > 0 },
        ];
        fieldsToValidate.forEach(function ({ id, check }) {
            const el = document.getElementById(id);
            if (!el) return;
            el.addEventListener("blur", function () {
                if (!check(el.value)) {
                    el.classList.add("is-invalid");
                } else {
                    el.classList.remove("is-invalid");
                    el.classList.add("is-valid");
                }
            });
        });

        // Submit: show spinner, disable button, run full validation
        const form2      = document.getElementById("deviceForm");
        const submitBtn  = document.getElementById("deviceFormSubmitBtn");
        const btnText    = document.getElementById("deviceFormBtnText");
        const btnSpinner = document.getElementById("deviceFormBtnSpinner");

        if (form2) {
            form2.addEventListener("submit", function (event) {
                if (!form2.checkValidity()) {
                    // Block submission and show Bootstrap validation styles
                    event.preventDefault();
                    event.stopPropagation();
                    form2.classList.add("was-validated");
                    return;
                }
                form2.classList.add("was-validated");

                // Valid — show spinner to prevent double-click
                if (submitBtn)  submitBtn.disabled = true;
                if (btnText)    btnText.classList.add("d-none");
                if (btnSpinner) btnSpinner.classList.remove("d-none");
            });
        }

        // AUTO-OPEN on validation error:
        // If the server re-rendered this page with open_device_modal=True,
        // programmatically open the modal so the user sees their errors.
        if (window.openDeviceModalOnLoad) {
            const bsModal = new bootstrap.Modal(deviceFormModal);
            bsModal.show();
            // Mark as done so subsequent manual opens use Add mode (reset)
            window.openDeviceModalOnLoad = false;
        }
    }


    // ================================================================ //
    // 5. DELETE MODAL PREFILL
    // ================================================================ //

    const deleteModal = document.getElementById("deleteDeviceModal");

    if (deleteModal) {
        deleteModal.addEventListener("show.bs.modal", function (event) {
            const triggerBtn = event.relatedTarget;
            if (!triggerBtn) return;

            const nameEl = document.getElementById("deleteDeviceName");
            const ipEl   = document.getElementById("deleteDeviceIp");
            const delForm = document.getElementById("deleteDeviceForm");

            if (nameEl)  nameEl.textContent = triggerBtn.dataset.deviceName || "this device";
            if (ipEl)    ipEl.textContent   = triggerBtn.dataset.deviceIp   || "";
            if (delForm) delForm.action     = triggerBtn.dataset.deleteUrl  || "#";
        });
    }

});
