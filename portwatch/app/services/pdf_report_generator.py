# app/services/pdf_report_generator.py
# Generates a PDF scan report using xhtml2pdf.
#
# generate_scan_report_pdf(scan) renders app/templates/reports/admin_scan_report_pdf.html
# through Jinja2 (using the Flask app context) and converts it to PDF bytes.
# Returns None if anything goes wrong so the caller can flash an error.

import io
import traceback


def generate_scan_report_pdf(scan):
    """
    Generate a PDF report for a single scan record.

    Args:
        scan (dict): A full scan record from admin_scans_mock.

    Returns:
        bytes: The PDF file contents, or None if generation failed.
    """
    try:
        from xhtml2pdf import pisa
        from flask import render_template, current_app
        from datetime import datetime as _dt

        from app.mock_data.admin_scans_mock import get_previous_scan
        from app.services.scan_comparator    import compare_scans
        from app.utils.remediation_tips      import get_recommendation
        from app.utils.port_reference        import get_port_info

        # ── Previous scan for the Changes section ──────────────────────
        prev    = get_previous_scan(scan)
        changes = compare_scans(
            scan.get("findings", []),
            prev.get("findings", []) if prev else None,
        )

        # ── Attach recommendation to every finding ──────────────────────
        enriched_findings = []
        for f in scan.get("findings", []):
            enriched_findings.append({
                **f,
                "recommendation": get_recommendation(f),
                "port_info":      get_port_info(f.get("port", 0)),
            })

        # ── Logo path (absolute filesystem path for xhtml2pdf) ──────────
        import os
        logo_path = os.path.join(
            current_app.root_path, "static", "img",
            "portwatch_logo", "portwatch_logo.png"
        )
        logo_exists = os.path.isfile(logo_path)

        # ── Render the HTML template ────────────────────────────────────
        html_string = render_template(
            "reports/admin_scan_report_pdf.html",
            scan=scan,
            findings=enriched_findings,
            changes=changes,
            prev_scan=prev,
            logo_path=logo_path if logo_exists else None,
            now=_dt.now(),
        )

        # ── Convert HTML → PDF ──────────────────────────────────────────
        pdf_buffer = io.BytesIO()
        result = pisa.CreatePDF(
            src=html_string,
            dest=pdf_buffer,
            encoding="utf-8",
        )

        if result.err:
            current_app.logger.error(
                f"xhtml2pdf reported errors for scan {scan.get('id')}: {result.err}"
            )
            return None

        return pdf_buffer.getvalue()

    except Exception:
        # Print the full traceback to the terminal so the developer can see it
        traceback.print_exc()
        return None
