/*
 * admin_run_scan.js
 * Client-side logic for the Run Scan page (/admin/scan).
 *
 * Responsibilities:
 *   1. Target mode radio cards — toggle between Single and All.
 *   2. Device select → update the preview panel (IP, lab, type, allowlist, last scan).
 *   3. No-allowlist warning for a selected device.
 *   4. Port mode radios — show/hide the custom port input.
 *   5. Custom port range — live client-side validation.
 *   6. Scan Preview card — updates live as the form changes.
 *   7. Nmap command display + copy button.
 *   8. Submit spinner to prevent double-clicks.
 */

document.addEventListener("DOMContentLoaded", function () {

    const D = window.scanPageData || {};   // injected by the template

    // Build a quick lookup by device id
    const deviceMap = {};
    (D.devices || []).forEach(function (dev) {
        deviceMap[dev.id] = dev;
    });

    // ---------------------------------------------------------------- //
    // ELEMENT REFERENCES
    // ---------------------------------------------------------------- //
    const cardSingle       = document.getElementById("card-single");
    const cardAll          = document.getElementById("card-all");
    const modeSingle       = document.getElementById("mode-single");
    const modeAll          = document.getElementById("mode-all");
    const singleSection    = document.getElementById("singleDeviceSection");
    const allSection       = document.getElementById("allDevicesSection");
    const deviceSelect     = document.getElementById("deviceSelect");
    const devicePreview    = document.getElementById("devicePreview");
    const noAllowlistWarn  = document.getElementById("noAllowlistWarn");
    const noAllowlistLink  = document.getElementById("noAllowlistLink");
    const portTop          = document.getElementById("portTop");
    const portCustom       = document.getElementById("portCustom");
    const customPortSec    = document.getElementById("customPortSection");
    const customPortsInput = document.getElementById("customPorts");
    const prevTarget       = document.getElementById("prevTarget");
    const prevPorts        = document.getElementById("prevPorts");
    const prevTime         = document.getElementById("prevTime");
    const nmapCmd          = document.getElementById("nmapCmd");
    const copyNmapBtn      = document.getElementById("copyNmapBtn");
    const startBtn         = document.getElementById("startScanBtn");
    const startBtnText     = document.getElementById("startBtnText");
    const startBtnSpinner  = document.getElementById("startBtnSpinner");

    // ---------------------------------------------------------------- //
    // 1. TARGET MODE RADIO CARDS
    // ---------------------------------------------------------------- //
    function setTargetMode(mode) {
        if (mode === "single") {
            cardSingle.classList.add("selected");
            cardAll.classList.remove("selected");
            modeSingle.checked = true;
            singleSection.style.display = "";
            allSection.style.display    = "none";
        } else {
            cardAll.classList.add("selected");
            cardSingle.classList.remove("selected");
            modeAll.checked = true;
            singleSection.style.display = "none";
            allSection.style.display    = "";
        }
        updatePreview();
    }

    if (cardSingle) cardSingle.addEventListener("click", function () { setTargetMode("single"); });
    if (cardAll)    cardAll.addEventListener("click",    function () { setTargetMode("all"); });

    // Initialise from form_data or preselected device
    const initMode = modeSingle && modeSingle.checked ? "single" : "all";
    setTargetMode(initMode);


    // ---------------------------------------------------------------- //
    // 2 & 3. DEVICE SELECT → PREVIEW PANEL
    // ---------------------------------------------------------------- //
    function updateDevicePreview() {
        if (!deviceSelect || !devicePreview) return;

        const devId = parseInt(deviceSelect.value, 10);
        const dev   = deviceMap[devId];

        if (!dev) {
            devicePreview.style.display = "none";
            return;
        }

        devicePreview.style.display = "";

        const ip = document.getElementById("prevIp");
        const lab  = document.getElementById("prevLab");
        const type = document.getElementById("prevType");
        const al   = document.getElementById("prevAllowlist");
        const ls   = document.getElementById("prevLastScan");

        if (ip)   ip.textContent  = dev.ip_address;
        if (lab)  lab.textContent = dev.lab_location;
        if (type) type.textContent = dev.device_type;
        if (al)   al.textContent  = dev.allowlisted_port_count + " entries";
        if (ls)   ls.textContent  = dev.last_scanned
            ? new Date(dev.last_scanned).toLocaleDateString()
            : "Never";

        // No-allowlist warning
        if (noAllowlistWarn) {
            noAllowlistWarn.style.display = dev.allowlisted_port_count === 0 ? "" : "none";
        }
        if (noAllowlistLink) {
            noAllowlistLink.href = D.allowlistUrl + "?device_id=" + dev.id;
        }

        updatePreview();
    }

    if (deviceSelect) {
        deviceSelect.addEventListener("change", updateDevicePreview);
        // Run on load in case a device is pre-selected
        updateDevicePreview();
    }

    // Pre-select from query param or form_data
    if (deviceSelect && D.preselectedId) {
        deviceSelect.value = D.preselectedId;
        updateDevicePreview();
    }


    // ---------------------------------------------------------------- //
    // 4. PORT MODE RADIOS
    // ---------------------------------------------------------------- //
    function updatePortMode() {
        const isCustom = portCustom && portCustom.checked;
        if (customPortSec) {
            customPortSec.style.display = isCustom ? "" : "none";
        }
        updatePreview();
    }

    if (portTop)    portTop.addEventListener("change",    updatePortMode);
    if (portCustom) portCustom.addEventListener("change", updatePortMode);
    updatePortMode();


    // ---------------------------------------------------------------- //
    // 5. CUSTOM PORT RANGE — live validation
    // ---------------------------------------------------------------- //
    function validateCustomPorts(val) {
        if (!val) return "Port range cannot be empty.";
        if (!/^[\d,\-\s]+$/.test(val)) {
            return "Only digits, commas, and hyphens are allowed.";
        }
        for (const part of val.split(",")) {
            const p = part.trim();
            if (!p) return "Stray comma in port range.";
            if (p.includes("-")) {
                const [lo, hi] = p.split("-").map(Number);
                if (isNaN(lo) || isNaN(hi)) return `'${p}' is not a valid range.`;
                if (lo < 1 || hi > 65535)   return `Ports in '${p}' must be 1–65535.`;
                if (lo >= hi)               return `Range '${p}' must be ascending.`;
            } else {
                const n = Number(p);
                if (isNaN(n) || n < 1 || n > 65535) {
                    return `Port '${p}' is out of range (1–65535).`;
                }
            }
        }
        return null;   // null = valid
    }

    if (customPortsInput) {
        customPortsInput.addEventListener("input", function () {
            const err = validateCustomPorts(customPortsInput.value);
            if (err) {
                customPortsInput.classList.add("is-invalid");
                let fb = customPortsInput.nextElementSibling;
                // skip the form-hint div
                while (fb && !fb.classList.contains("invalid-feedback")) {
                    fb = fb.nextElementSibling;
                }
                if (fb) fb.textContent = err;
            } else {
                customPortsInput.classList.remove("is-invalid");
                customPortsInput.classList.add("is-valid");
            }
            updatePreview();
        });
    }


    // ---------------------------------------------------------------- //
    // 6 & 7. SCAN PREVIEW + NMAP COMMAND
    // ---------------------------------------------------------------- //
    function updatePreview() {
        const isSingle = modeSingle && modeSingle.checked;
        const isCustomPort = portCustom && portCustom.checked;

        let targetText = "—";
        let ipList     = [];

        if (isSingle) {
            const devId = deviceSelect ? parseInt(deviceSelect.value, 10) : NaN;
            const dev   = deviceMap[devId];
            if (dev) {
                targetText = dev.name + " — " + dev.ip_address;
                ipList     = [dev.ip_address];
            }
        } else {
            targetText = D.activeCount + " active devices";
            ipList = D.devices
                .filter(function (d) { return d.status === "active"; })
                .map(function (d) { return d.ip_address; });
        }

        const portText = isCustomPort
            ? (customPortsInput ? customPortsInput.value || "?" : "?")
            : "Top 1,000 TCP";

        const deviceCount = isSingle ? 1 : (D.activeCount || 1);
        const mockSec = (D.mockDuration || 8) * deviceCount;
        const mins    = Math.ceil(mockSec / 60);
        const timeText = mins < 2
            ? "~" + mockSec + " seconds (demo)"
            : "~" + mins + " minutes (demo)";

        if (prevTarget) prevTarget.textContent = targetText;
        if (prevPorts)  prevPorts.textContent  = portText;
        if (prevTime)   prevTime.textContent   = timeText;

        // Build the Nmap command string
        const portArg = isCustomPort
            ? "-p " + (customPortsInput ? customPortsInput.value : "?")
            : "--top-ports 1000";

        let ipStr;
        if (ipList.length <= 3) {
            ipStr = ipList.join(" ");
        } else {
            ipStr = ipList.slice(0, 2).join(" ") +
                    " … (+" + (ipList.length - 2) + " more)";
        }

        const cmd = ipStr
            ? "nmap -sV " + portArg + " " + ipStr
            : "nmap -sV " + portArg + " <select a device>";

        if (nmapCmd) nmapCmd.textContent = cmd;
    }

    // Copy button
    if (copyNmapBtn && nmapCmd) {
        copyNmapBtn.addEventListener("click", function () {
            navigator.clipboard.writeText(nmapCmd.textContent).then(function () {
                copyNmapBtn.innerHTML = '<i class="bi bi-clipboard-check"></i>';
                setTimeout(function () {
                    copyNmapBtn.innerHTML = '<i class="bi bi-clipboard"></i>';
                }, 1500);
            });
        });
    }


    // ---------------------------------------------------------------- //
    // 8. SUBMIT SPINNER
    // ---------------------------------------------------------------- //
    const scanForm = document.getElementById("scanForm");
    if (scanForm && startBtn) {
        scanForm.addEventListener("submit", function () {
            startBtn.disabled = true;
            if (startBtnText)    startBtnText.classList.add("d-none");
            if (startBtnSpinner) startBtnSpinner.classList.remove("d-none");
        });
    }

    // Initial preview render
    updatePreview();
});
