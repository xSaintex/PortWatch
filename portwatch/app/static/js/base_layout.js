/*
 * base_layout.js
 * JavaScript that runs on every page of PortWatch.
 * Responsibilities:
 *   1. Initialise Bootstrap tooltips and expose a helper to hide all tooltips.
 *   2. Handle the mobile hamburger menu toggle in the top navigation bar.
 *
 * WHY THE TOOLTIP HELPER:
 *   Bootstrap tooltips stay visible if the element they are attached to is
 *   hidden or moved by pagination / sorting / filtering. Without explicit
 *   cleanup, a tooltip can get "stuck" on screen with nothing below it.
 *   We expose window.hideAllTooltips() so pagination and filter scripts
 *   can call it whenever rows are reordered or hidden, and we also hide all
 *   tooltips when the user clicks any link or button inside a table row so
 *   the tooltip does not overlap the next page.
 */

document.addEventListener("DOMContentLoaded", function () {

    // ---------------------------------------------------------------- //
    // 1. BOOTSTRAP TOOLTIPS
    // Bootstrap tooltips are not auto-initialised — we must do it manually.
    // Any element with data-bs-toggle="tooltip" gets a tooltip instance.
    // ---------------------------------------------------------------- //

    function initTooltips() {
        document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
            // Only create a new instance if one doesn't already exist
            if (!bootstrap.Tooltip.getInstance(el)) {
                new bootstrap.Tooltip(el, {
                    delay: { show: 300, hide: 100 },
                });
            }
        });
    }

    initTooltips();

    // Expose globally so pagination and other scripts can re-run it
    // after DOM changes (e.g. after pagination injects new button elements).
    window.initTooltips = initTooltips;

    // Hide ALL visible tooltip instances immediately.
    // Called by table_pagination.js and by the icon click handler below.
    window.hideAllTooltips = function () {
        document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
            const tip = bootstrap.Tooltip.getInstance(el);
            if (tip) tip.hide();
        });
    };

    // Hide all tooltips when the user clicks any link or button inside a
    // table row — prevents the tooltip from lingering while the browser
    // navigates or downloads a file.
    document.addEventListener("click", function (event) {
        const target = event.target.closest("a[data-bs-toggle='tooltip'], button[data-bs-toggle='tooltip']");
        if (target) {
            const tip = bootstrap.Tooltip.getInstance(target);
            if (tip) tip.hide();
        }
        // Also hide all other tooltips when any <a> or <button> is clicked
        if (event.target.closest("a, button")) {
            window.hideAllTooltips();
        }
    }, true);  // capture phase so it fires before Bootstrap's own handlers


    // ---------------------------------------------------------------- //
    // 2. MOBILE HAMBURGER MENU
    // ---------------------------------------------------------------- //
    const toggler   = document.getElementById("pw-nav-toggler");
    const navCenter = document.getElementById("pw-nav-center");

    if (toggler && navCenter) {
        toggler.addEventListener("click", function () {
            navCenter.classList.toggle("show");
            const isExpanded = navCenter.classList.contains("show");
            toggler.setAttribute("aria-expanded", isExpanded.toString());
        });

        document.addEventListener("click", function (event) {
            const clickedInsideNav = navCenter.contains(event.target) || toggler.contains(event.target);
            if (!clickedInsideNav && navCenter.classList.contains("show")) {
                navCenter.classList.remove("show");
                toggler.setAttribute("aria-expanded", "false");
            }
        });
    }

});
