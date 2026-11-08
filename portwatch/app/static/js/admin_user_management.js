/*
 * admin_user_management.js
 * Client-side logic for the User Management page (/admin/users).
 *
 * Responsibilities:
 *   1. Filter table rows by name/username search, role, and status.
 *   2. Pagination via the shared initTablePagination (8 per page).
 *   3. New-user row highlight + scroll + URL cleanup (same pattern as Device Registry).
 *   4. Add/Edit user modal:
 *      - show.bs.modal reads event.relatedTarget to decide Add vs Edit mode.
 *      - Add mode: always resets the form fully (title, icon, fields, passwords).
 *      - Edit mode: prefills name, role cards, status toggle; username is read-only;
 *        password row is hidden; for own account, role/status are disabled.
 *      - Role radio cards: clicking a card checks its radio and toggles the
 *        "selected" CSS class so the red border follows.
 *      - Password strength checklist: updates live as the user types.
 *      - Confirm password: shows a match/mismatch hint in real time.
 *      - Show/hide password toggle buttons.
 *      - Submit spinner.
 *      - Auto-opens on server validation error (window.userMgmtData.openModal).
 *   5. Reset Password modal: JS fills in the target user's name/username and
 *      the form action; password fields are never pre-filled.
 *   6. Delete User modal: fills in name, username, form action.
 *   7. Tooltip cleanup on every filter/pagination change (same fix as Scan History).
 */

document.addEventListener("DOMContentLoaded", function () {

    const D = window.userMgmtData || {};

    // ---------------------------------------------------------------- //
    // ELEMENT REFERENCES
    // ---------------------------------------------------------------- //
    const searchInput  = document.getElementById("userSearch");
    const filterRole   = document.getElementById("filterRole");
    const filterStatus = document.getElementById("filterStatus");
    const clearBtn     = document.getElementById("clearFilters");
    const clearBtn2    = document.getElementById("clearFilters2");
    const tableBody    = document.getElementById("usersTableBody");
    const noResults    = document.getElementById("noFilterResults");


    // ================================================================ //
    // 1. FILTER LOGIC
    // ================================================================ //
    function applyFilters() {
        if (!tableBody) return;

        const search = searchInput  ? searchInput.value.toLowerCase().trim() : "";
        const role   = filterRole   ? filterRole.value.toLowerCase()          : "";
        const status = filterStatus ? filterStatus.value.toLowerCase()        : "";

        const rows = tableBody.querySelectorAll(".pw-user-row");
        let count  = 0;

        rows.forEach(function (row) {
            const rName     = row.dataset.name     || "";
            const rUsername = row.dataset.username || "";
            const rRole     = row.dataset.role     || "";
            const rStatus   = row.dataset.status   || "";

            const matchSearch = !search || rName.includes(search) || rUsername.includes(search);
            const matchRole   = !role   || rRole   === role;
            const matchStatus = !status || rStatus === status;

            if (matchSearch && matchRole && matchStatus) {
                row.classList.remove("pw-filtered-out");
                count++;
            } else {
                row.classList.add("pw-filtered-out");
                row.style.display = "none";
            }
        });

        if (noResults) {
            noResults.style.display = count === 0 ? "flex" : "none";
        }

        if (window.refreshPagination && window.refreshPagination["usersTable"]) {
            window.refreshPagination["usersTable"]();
        }
    }

    if (searchInput)  searchInput.addEventListener("input",  applyFilters);
    if (filterRole)   filterRole.addEventListener("change",  applyFilters);
    if (filterStatus) filterStatus.addEventListener("change", applyFilters);


    // ================================================================ //
    // 2. CLEAR FILTERS
    // ================================================================ //
    function clearAllFilters() {
        if (searchInput)  searchInput.value  = "";
        if (filterRole)   filterRole.value   = "";
        if (filterStatus) filterStatus.value = "";
        applyFilters();
    }

    if (clearBtn)  clearBtn.addEventListener("click",  clearAllFilters);
    if (clearBtn2) clearBtn2.addEventListener("click", clearAllFilters);


    // ================================================================ //
    // 3. PAGINATION — 8 rows per page
    // ================================================================ //
    try {
        if (typeof initTablePagination === "function") {
            initTablePagination("usersTable", {
                pageSize:     8,
                itemWord:     "users",
                paginationId: "usersPagination",
            });
        }
    } catch (e) {
        console.warn("PortWatch: users pagination init failed:", e);
    }


    // ================================================================ //
    // 3b. NEW-USER HIGHLIGHT — same pattern as Device Registry
    // ================================================================ //
    if (D.newUserId) {
        clearAllFilters();  // ensure the new row is visible

        const newRow = tableBody
            ? tableBody.querySelector(`tr[data-user-id="${D.newUserId}"]`)
            : null;
        if (newRow) {
            requestAnimationFrame(function () {
                newRow.scrollIntoView({ behavior: "smooth", block: "center" });
            });
        }

        history.replaceState(null, "", window.location.pathname);
        D.newUserId = null;
    }


    // ================================================================ //
    // 4. ADD / EDIT USER MODAL
    // ================================================================ //
    const userFormModal = document.getElementById("userFormModal");

    if (userFormModal) {
        const userForm     = document.getElementById("userForm");
        if (userForm) userForm.dataset.addUrl = userForm.action;

        userFormModal.addEventListener("show.bs.modal", function (event) {
            const btn  = event.relatedTarget;
            if (!btn) return;   // programmatic open (server error) — keep as-is

            const mode = btn.dataset.mode;

            const titleEl    = document.getElementById("userFormModalLabel");
            const subtitleEl = document.getElementById("userFormSubtitle");
            const iconEl     = document.getElementById("userFormIcon");
            const submitText = document.getElementById("userFormBtnText");
            const nameInput  = document.getElementById("userFullName");
            const unameInput = document.getElementById("userUsername");
            const unameHint  = document.getElementById("usernameHint");
            const unameReq   = document.getElementById("usernameRequired");
            const pwRow      = document.getElementById("passwordRow");
            const roleCards  = document.getElementById("roleCards");
            const selfWarn   = document.getElementById("selfRoleWarning");
            const statusChk  = document.getElementById("userStatus");
            const form       = document.getElementById("userForm");

            if (mode === "edit") {
                // ---- EDIT MODE ----
                if (titleEl)    titleEl.textContent  = "Edit User";
                if (iconEl)     iconEl.className     = "bi bi-person-gear pw-modal-title-icon";
                const uname = btn.dataset.userUsername || "";
                if (subtitleEl) subtitleEl.textContent = `Update account details for @${uname}`;
                if (submitText) submitText.innerHTML =
                    '<i class="bi bi-check-lg me-1"></i> Save Changes';

                // Point the form at the edit route
                if (form) form.action = btn.dataset.editUrl || form.action;

                // Prefill name
                if (nameInput) nameInput.value = btn.dataset.userFullName || "";

                // Username is READ-ONLY in edit mode
                if (unameInput) {
                    unameInput.value    = uname;
                    unameInput.readOnly = true;
                    unameInput.removeAttribute("required");
                    unameInput.removeAttribute("pattern");
                }
                if (unameHint) unameHint.textContent = "Usernames cannot be changed.";
                if (unameReq)  unameReq.style.display = "none";

                // Hide password fields — use Reset Password for that
                if (pwRow) pwRow.style.display = "none";
                // Remove required from hidden password inputs so form submits
                const pwInputs = pwRow ? pwRow.querySelectorAll("input") : [];
                pwInputs.forEach(function (i) { i.removeAttribute("required"); });

                // Set role cards
                const roleValue = btn.dataset.userRole || "viewer";
                _setRoleCard(roleValue);

                // Status toggle
                if (statusChk) {
                    statusChk.checked = (btn.dataset.userStatus === "active");
                }

                // Disable role/status for own account
                const isSelf = (btn.dataset.isSelf === "true");
                if (roleCards) {
                    roleCards.querySelectorAll("label, input").forEach(function (el) {
                        el.disabled = isSelf;
                    });
                }
                if (statusChk) statusChk.disabled = isSelf;
                if (selfWarn)  selfWarn.style.display = isSelf ? "" : "none";

                // Show admin password row only when promoting Viewer → Admin
                _editOriginalRole = btn.dataset.userRole || "viewer";
                _syncAdminPasswordRow("edit", _editOriginalRole);

                // Clear validation state from previous open
                _resetValidation(form);

            } else {
                // ---- ADD MODE ----
                if (titleEl)    titleEl.textContent  = "Add User";
                if (iconEl)     iconEl.className     = "bi bi-person-plus pw-modal-title-icon";
                if (subtitleEl) subtitleEl.textContent = "Create an account for lab staff or IT personnel.";
                if (submitText) submitText.innerHTML =
                    '<i class="bi bi-check-lg me-1"></i> Create User';

                // Restore the Add URL
                if (form) form.action = form.dataset.addUrl || form.action;

                // Only reset if no server errors are showing
                if (!D.openModal) {
                    if (form) form.reset();
                    _resetValidation(form);
                    _setRoleCard("administrator");   // default role
                    // Admin adds default to admin role — show the password row immediately
                    _syncAdminPasswordRow("add", null);
                    if (pwRow) pwRow.style.display  = "";
                    const pwInputs2 = pwRow ? pwRow.querySelectorAll("input") : [];
                    pwInputs2.forEach(function (i) { i.setAttribute("required", ""); });
                    if (unameInput) {
                        unameInput.readOnly = false;
                        unameInput.setAttribute("required", "");
                        unameInput.setAttribute("pattern", "^[a-z][a-z0-9_.]*$");
                    }
                    if (unameHint) unameHint.textContent = "3–20 characters: lowercase letters, numbers, _ or .";
                    if (unameReq)  unameReq.style.display = "";
                    if (roleCards) {
                        roleCards.querySelectorAll("label, input").forEach(function (el) {
                            el.disabled = false;
                        });
                    }
                    if (statusChk) { statusChk.disabled = false; statusChk.checked = true; }
                    if (selfWarn)  selfWarn.style.display = "none";
                    _updatePwChecklist("pwLen","pwLet","pwNum", "");
                    const confirmMsg = document.getElementById("confirmMatchMsg");
                    if (confirmMsg) confirmMsg.style.display = "none";
                }
            }
        });

        // ---- Role card click → check the radio + toggle selected class ----
        const roleCardAdmin  = document.getElementById("roleCardAdmin");
        const roleCardViewer = document.getElementById("roleCardViewer");
        const radioAdmin     = document.getElementById("roleAdmin");
        const radioViewer    = document.getElementById("roleViewer");

        function _setRoleCard(roleValue) {
            if (roleCardAdmin && roleCardViewer) {
                if (roleValue === "administrator") {
                    roleCardAdmin.classList.add("selected");
                    roleCardViewer.classList.remove("selected");
                    if (radioAdmin)  radioAdmin.checked  = true;
                    if (radioViewer) radioViewer.checked = false;
                } else {
                    roleCardViewer.classList.add("selected");
                    roleCardAdmin.classList.remove("selected");
                    if (radioViewer) radioViewer.checked = true;
                    if (radioAdmin)  radioAdmin.checked  = false;
                }
            }
        }

        if (roleCardAdmin)  roleCardAdmin.addEventListener("click",  function () {
            _setRoleCard("administrator");
            _syncAdminPasswordRow("add", null);
        });
        if (roleCardViewer) roleCardViewer.addEventListener("click", function () {
            _setRoleCard("viewer");
            _syncAdminPasswordRow("viewer", null);
        });

        // ---- Password strength checklist ----
        const pwInput = document.getElementById("userPassword");
        if (pwInput) {
            pwInput.addEventListener("input", function () {
                _updatePwChecklist("pwLen","pwLet","pwNum", pwInput.value);
            });
        }

        // ---- Confirm password match hint ----
        const confirmInput = document.getElementById("userConfirmPassword");
        const confirmMsg   = document.getElementById("confirmMatchMsg");
        if (confirmInput && pwInput && confirmMsg) {
            function checkMatch() {
                if (!confirmInput.value) { confirmMsg.style.display = "none"; return; }
                confirmMsg.style.display = "";
                if (confirmInput.value === pwInput.value) {
                    confirmMsg.textContent   = "✓ Passwords match";
                    confirmMsg.style.color   = "#4CAF50";
                } else {
                    confirmMsg.textContent   = "✗ Passwords do not match";
                    confirmMsg.style.color   = "var(--pw-red)";
                }
            }
            confirmInput.addEventListener("input", checkMatch);
            if (pwInput) pwInput.addEventListener("input", checkMatch);
        }

        // ---- Submit spinner ----
        const submitBtn  = document.getElementById("userFormSubmitBtn");
        const btnText    = document.getElementById("userFormBtnText");
        const btnSpinner = document.getElementById("userFormBtnSpinner");

        if (userForm) {
            userForm.addEventListener("submit", function (event) {
                if (!userForm.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                    userForm.classList.add("was-validated");
                    return;
                }
                userForm.classList.add("was-validated");
                if (submitBtn)  submitBtn.disabled = true;
                if (btnText)    btnText.classList.add("d-none");
                if (btnSpinner) btnSpinner.classList.remove("d-none");
            });
        }

        // ---- Auto-open on server error ----
        if (D.openModal === "add") {
            const bsModal = new bootstrap.Modal(userFormModal);
            bsModal.show();
            D.openModal = null;
            // Show password fields (they may be needed)
            const pwRow = document.getElementById("passwordRow");
            if (pwRow) pwRow.style.display = "";
            // Re-sync admin password row based on current role selection
            _syncAdminPasswordRow("add", null);
        } else if (D.openModal === "edit" && D.editingUserId) {
            // Find the Edit button for that user and trigger it
            const editBtn = tableBody
                ? tableBody.querySelector(`button[data-mode="edit"][data-user-id="${D.editingUserId}"]`)
                : null;
            if (editBtn) {
                const bsModal = new bootstrap.Modal(userFormModal);
                // Pre-fire the show event with the button as relatedTarget via programmatic show
                userFormModal.addEventListener("show.bs.modal", function handler(e) {
                    e.relatedTarget = editBtn;
                    userFormModal.removeEventListener("show.bs.modal", handler);
                }, true);
                bsModal.show();
            }
            D.openModal = null;
        }
    }


    // ================================================================ //
    // 5. RESET PASSWORD MODAL
    // ================================================================ //
    const resetModal = document.getElementById("resetPasswordModal");
    if (resetModal) {
        resetModal.addEventListener("show.bs.modal", function (event) {
            const btn = event.relatedTarget;
            if (!btn) return;

            const nameEl    = document.getElementById("resetTargetName");
            const form      = document.getElementById("resetPasswordForm");
            const pwInput   = document.getElementById("resetNewPassword");
            const confInput = document.getElementById("resetConfirmPassword");

            if (nameEl) nameEl.textContent =
                `${btn.dataset.userFullName || ""} (@${btn.dataset.userUsername || ""})`;
            if (form)   form.action = btn.dataset.resetUrl || "#";

            // Never prefill password fields — clear them every time
            if (pwInput)   pwInput.value   = "";
            if (confInput) confInput.value = "";

            _updatePwChecklist("rpwLen","rpwLet","rpwNum","");
            const rConMsg = document.getElementById("resetConfirmMsg");
            if (rConMsg) rConMsg.style.display = "none";

            // Wire checklist for the reset password input
            const rPwInput = document.getElementById("resetNewPassword");
            const rConInput = document.getElementById("resetConfirmPassword");
            const rConMsgEl = document.getElementById("resetConfirmMsg");

            if (rPwInput) {
                rPwInput.oninput = function () {
                    _updatePwChecklist("rpwLen","rpwLet","rpwNum", rPwInput.value);
                    _checkResetMatch(rPwInput, rConInput, rConMsgEl);
                };
            }
            if (rConInput) {
                rConInput.oninput = function () {
                    _checkResetMatch(rPwInput, rConInput, rConMsgEl);
                };
            }
        });

        // Auto-open if server returned a reset error
        if (D.openModal === "reset" && D.resetUserId) {
            const resetBtn = tableBody
                ? tableBody.querySelector(`button[data-bs-target="#resetPasswordModal"][data-user-id="${D.resetUserId}"]`)
                : null;
            if (resetBtn) {
                const bsModal = new bootstrap.Modal(resetModal);
                bsModal.show();
            }
            D.openModal = null;
        }
    }


    // ================================================================ //
    // 6. DELETE USER MODAL
    // ================================================================ //
    const deleteModal = document.getElementById("deleteUserModal");
    if (deleteModal) {
        deleteModal.addEventListener("show.bs.modal", function (event) {
            const btn = event.relatedTarget;
            if (!btn) return;

            const nameEl = document.getElementById("deleteUserFullName");
            const unEl   = document.getElementById("deleteUserUsername");
            const form   = document.getElementById("deleteUserForm");

            if (nameEl) nameEl.textContent = btn.dataset.userFullName || "this user";
            if (unEl)   unEl.textContent   = "@" + (btn.dataset.userUsername || "");
            if (form)   form.action        = btn.dataset.deleteUrl || "#";
        });
    }


    // ================================================================ //
    // 6b. STATUS CONFIRMATION MODAL (Activate / Deactivate)
    // ================================================================ //
    const statusModal = document.getElementById("userStatusModal");
    if (statusModal) {
        statusModal.addEventListener("show.bs.modal", function (event) {
            const btn = event.relatedTarget;
            if (!btn) return;

            const fullName   = btn.dataset.userFullName    || "this user";
            const username   = btn.dataset.userUsername    || "";
            const curStatus  = btn.dataset.userStatus      || "active";
            const userRole   = btn.dataset.userRole        || "viewer";
            const toggleUrl  = btn.dataset.toggleUrl       || "#";
            const isActive   = curStatus === "active";
            const isAdmin    = userRole === "administrator";

            // Title
            const titleEl = document.getElementById("userStatusModalLabel");
            if (titleEl) titleEl.textContent = isActive ? "Deactivate User" : "Activate User";

            // Body text
            const bodyEl = document.getElementById("userStatusModalBody");
            if (bodyEl) {
                if (isActive) {
                    bodyEl.innerHTML =
                        `Deactivate <strong>${esc(fullName)}</strong> (@${esc(username)})?
                         They will not be able to log in until reactivated.`;
                } else {
                    bodyEl.innerHTML =
                        `Activate <strong>${esc(fullName)}</strong> (@${esc(username)})?
                         They will be able to log in again.`;
                }
            }

            // Form action
            const form = document.getElementById("userStatusForm");
            if (form) form.action = toggleUrl;

            // Submit button label
            const submitBtn = document.getElementById("userStatusSubmitBtn");
            if (submitBtn) submitBtn.textContent = isActive ? "Deactivate" : "Activate";

            // Show "Your Password" field only when ACTIVATING an ADMIN account
            const statusPwRow = document.getElementById("statusAdminPasswordRow");
            const statusPwInput = document.getElementById("statusAdminGrantPassword");
            const needsReauth = !isActive && isAdmin;   // activating an admin

            if (statusPwRow) statusPwRow.style.display = needsReauth ? "" : "none";
            if (statusPwInput) {
                statusPwInput.value = "";   // never pre-fill
                if (needsReauth) {
                    statusPwInput.setAttribute("required", "");
                } else {
                    statusPwInput.removeAttribute("required");
                }
            }

            // Before the form submits, copy the visible password into the hidden field
            if (form) {
                form.onsubmit = function () {
                    const hidden = document.getElementById("statusAdminGrantHidden");
                    if (hidden && statusPwInput) hidden.value = statusPwInput.value;
                };
            }
        });

        // Clear the password field when the modal closes
        statusModal.addEventListener("hidden.bs.modal", function () {
            const pwInput = document.getElementById("statusAdminGrantPassword");
            const hidden  = document.getElementById("statusAdminGrantHidden");
            if (pwInput) pwInput.value = "";
            if (hidden)  hidden.value  = "";
        });
    }


    // ================================================================ //
    // 7. SHOW / HIDE PASSWORD TOGGLES
    // ================================================================ //
    document.querySelectorAll(".pw-show-hide-btn").forEach(function (btn) {
        btn.addEventListener("click", function () {
            const targetId = btn.dataset.target;
            const input    = document.getElementById(targetId);
            if (!input) return;
            const isHidden = input.type === "password";
            input.type = isHidden ? "text" : "password";
            const icon = btn.querySelector("i");
            if (icon) {
                icon.classList.toggle("bi-eye",      !isHidden);
                icon.classList.toggle("bi-eye-slash", isHidden);
            }
        });
    });


    // ================================================================ //
    // HELPERS
    // ================================================================ //

    /*
     * Show or hide the "Your Password" re-authentication field in the
     * Add/Edit User modal.
     *
     * mode:        "add"  → show when admin role is selected
     *              "edit" → show only when role is CHANGING to admin
     *              "viewer" → always hide (not needed for Viewer)
     * originalRole: the user's current role before editing (Edit mode only)
     */
    function _syncAdminPasswordRow(mode, originalRole) {
        const pwRow   = document.getElementById("adminPasswordRow");
        const pwInput = document.getElementById("adminGrantPassword");
        if (!pwRow) return;

        let show = false;
        if (mode === "viewer") {
            show = false;
        } else if (mode === "add") {
            // In Add mode, show when Administrator card is selected
            const radioAdmin = document.getElementById("roleAdmin");
            show = radioAdmin ? radioAdmin.checked : false;
        } else if (mode === "edit") {
            // In Edit mode, show only when changing FROM viewer TO admin
            const radioAdmin = document.getElementById("roleAdmin");
            const nowAdmin = radioAdmin ? radioAdmin.checked : false;
            show = (nowAdmin && originalRole !== "administrator");
        }

        pwRow.style.display = show ? "" : "none";
        if (pwInput) {
            if (!show) {
                pwInput.value = "";                     // clear when hidden
                pwInput.removeAttribute("required");
            } else {
                pwInput.setAttribute("required", "");
            }
        }
    }

    // Also re-evaluate when role cards are clicked in Edit mode
    // (the current original role is stored in _editOriginalRole by the modal handler)
    let _editOriginalRole = null;

    // Patch the role-card listeners to re-sync after the modal handler sets them up
    const roleCardAdmin2  = document.getElementById("roleCardAdmin");
    const roleCardViewer2 = document.getElementById("roleCardViewer");
    if (roleCardAdmin2) {
        roleCardAdmin2.addEventListener("click", function () {
            // Determine mode from whether username is read-only
            const unInput = document.getElementById("userUsername");
            const isEdit  = unInput && unInput.readOnly;
            _syncAdminPasswordRow(isEdit ? "edit" : "add", _editOriginalRole);
        });
    }
    if (roleCardViewer2) {
        roleCardViewer2.addEventListener("click", function () {
            _syncAdminPasswordRow("viewer", _editOriginalRole);
        });
    }

    function _updatePwChecklist(lenId, letId, numId, value) {
        function _tick(id, ok) {
            const el = document.getElementById(id);
            if (!el) return;
            const icon = el.querySelector("i");
            if (ok) {
                el.style.color = "#4CAF50";
                el.classList.remove("pw-text-muted");
                if (icon) { icon.className = "bi bi-check-circle me-1"; }
            } else {
                el.style.color = "";
                el.classList.add("pw-text-muted");
                if (icon) { icon.className = "bi bi-circle me-1"; }
            }
        }
        _tick(lenId, value.length >= 8);
        _tick(letId, /[a-zA-Z]/.test(value));
        _tick(numId, /[0-9]/.test(value));
    }

    // Minimal HTML escaping — prevents XSS when inserting user-supplied text
    // into innerHTML (used by the status confirmation modal body).
    function esc(str) {
        return String(str || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function _checkResetMatch(pwEl, confirmEl, msgEl) {
        if (!pwEl || !confirmEl || !msgEl) return;
        if (!confirmEl.value) { msgEl.style.display = "none"; return; }
        msgEl.style.display = "";
        if (confirmEl.value === pwEl.value) {
            msgEl.textContent = "✓ Passwords match";
            msgEl.style.color = "#4CAF50";
        } else {
            msgEl.textContent = "✗ Passwords do not match";
            msgEl.style.color = "var(--pw-red)";
        }
    }

    function _resetValidation(form) {
        if (!form) return;
        form.classList.remove("was-validated");
        form.querySelectorAll(".is-invalid").forEach(function (el) {
            el.classList.remove("is-invalid");
        });
        form.querySelectorAll(".invalid-feedback.d-block").forEach(function (el) {
            el.classList.remove("d-block");
        });
    }

});
