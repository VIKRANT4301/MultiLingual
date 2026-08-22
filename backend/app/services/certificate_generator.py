import os
import io
import base64
import secrets
import string
import logging
import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session
from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "templates"
)
CERTIFICATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "synthetic"
)
os.makedirs(CERTIFICATES_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)


def _generate_cert_no(service_id: str) -> str:
    suffix = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    code_map = {
        "income_certificate": "INC",
        "caste_certificate": "CASTE",
        "domicile_certificate": "DOM",
        "ncl_certificate": "NCL",
        "obc_ncl_certificate": "NCL",
    }
    code = code_map.get(service_id, "CERT")
    year = datetime.datetime.now().year
    return f"CERT-MH-{year}-{code}-{suffix}"


def _generate_qr_base64(data: str) -> str:
    """Generate a QR code PNG as base64 string for embedding in HTML."""
    try:
        import qrcode
        qr = qrcode.make(data)
        buf = io.BytesIO()
        qr.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        logger.warning(f"QR code generation failed: {e}")
        return ""


class CertificateGenerator:
    """
    Generates styled HTML certificate documents.
    For POC: Generates an HTML file served as a web page (no WeasyPrint needed).
    For production: Add WeasyPrint to convert HTML → PDF.
    """

    @staticmethod
    def generate_certificate(
        service_id: str,
        state_data: Dict[str, Any],
        tracking_id: str,
        db: Session = None,
    ) -> Dict[str, Any]:
        """
        Generate a certificate HTML document for the given service type.
        Returns: {cert_no, file_path, cert_url, template_data}
        """
        from backend.app.services.service_loader import ServiceLoader

        cert_no = _generate_cert_no(service_id)
        issue_date = datetime.datetime.now().strftime("%d/%m/%Y")
        service_data = ServiceLoader.load_service(service_id)
        cert_name_en = service_data.get("name", {}).get("en", service_id.replace("_", " ").title())
        cert_name_mr = service_data.get("name", {}).get("mr", cert_name_en)
        issuing_authority = service_data.get("issuing_authority", {}).get("primary", "Tahsildar")
        processing_days = ServiceLoader.get_processing_days(service_id)

        # Validity
        valid_years = 3 if service_id == "ncl_certificate" else 5
        valid_until = (datetime.datetime.now() + datetime.timedelta(days=365 * valid_years)).strftime("%d/%m/%Y")

        qr_data = f"https://revenue.maharashtra.gov.in/track/{tracking_id}"
        qr_b64 = _generate_qr_base64(qr_data)

        template_data = {
            "cert_name_en": cert_name_en,
            "cert_name_mr": cert_name_mr,
            "cert_no": cert_no,
            "tracking_id": tracking_id,
            "issue_date": issue_date,
            "valid_until": valid_until,
            "issuing_authority": issuing_authority,
            "qr_base64": qr_b64,
            "full_name": state_data.get("full_name", "N/A"),
            "father_name": state_data.get("father_name", "N/A"),
            "date_of_birth": state_data.get("date_of_birth") or state_data.get("dob", "N/A"),
            "gender": state_data.get("gender", "N/A"),
            "district": state_data.get("district", "N/A"),
            "address": state_data.get("address", state_data.get("village", "N/A")),
            "annual_income": state_data.get("annual_income"),
            "income_source": state_data.get("income_source"),
            "caste_name": state_data.get("caste_name"),
            "caste_category": state_data.get("caste_category"),
            "years_of_residence": state_data.get("years_of_residence"),
            "certificate_purpose": state_data.get("certificate_purpose", "N/A"),
        }

        # Load Jinja2 template
        template_path = os.path.join(TEMPLATES_DIR, f"{service_id}.html")
        generic_template_path = os.path.join(TEMPLATES_DIR, "certificate_generic.html")

        try:
            env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=select_autoescape(["html"]))
            template_name = f"{service_id}.html" if os.path.exists(template_path) else "certificate_generic.html"
            template = env.get_template(template_name)
            html_content = template.render(**template_data)
        except Exception as e:
            logger.warning(f"Template loading failed ({e}), using inline HTML")
            html_content = CertificateGenerator._inline_html(template_data)

        # Save HTML file
        file_name = f"{cert_no}.html"
        file_path = os.path.join(CERTIFICATES_DIR, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Save to DB
        if db:
            try:
                from backend.app.models.models import Certificate, Application
                from sqlalchemy import func
                app_state_q = db.query(__import__("backend.app.models.models", fromlist=["ApplicationState"]).ApplicationState).filter(
                    func.json_extract(__import__("backend.app.models.models", fromlist=["ApplicationState"]).ApplicationState.state_data, "$.tracking_id") == tracking_id
                ).first()
                if app_state_q:
                    cert_record = Certificate(
                        application_id=app_state_q.application_id,
                        certificate_no=cert_no,
                        file_path=file_path,
                        status="ISSUED",
                    )
                    db.add(cert_record)
                    db.commit()
            except Exception as e:
                logger.warning(f"Could not save certificate record to DB: {e}")

        return {
            "cert_no": cert_no,
            "file_path": file_path,
            "cert_url": f"/static/certificates/{file_name}",
            "template_data": template_data,
        }

    @staticmethod
    def _inline_html(data: Dict[str, Any]) -> str:
        """Fallback inline HTML certificate if no template found."""
        qr_img = f'<img src="data:image/png;base64,{data["qr_base64"]}" width="80" height="80"/>' if data.get("qr_base64") else ""
        income_row = f"<tr><td><b>Annual Income</b></td><td>₹{data['annual_income']:,.0f}</td></tr>" if data.get("annual_income") else ""
        caste_row = f"<tr><td><b>Caste</b></td><td>{data.get('caste_name')} ({data.get('caste_category')})</td></tr>" if data.get("caste_name") else ""
        return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>{data['cert_name_en']}</title>
<style>
  body {{ font-family: 'Georgia', serif; background: #f8f9fa; color: #222; margin: 0; padding: 0; }}
  .cert {{ max-width: 800px; margin: 40px auto; background: white; border: 4px double #8B4513; padding: 40px; box-shadow: 0 0 30px rgba(0,0,0,0.2); }}
  .header {{ text-align: center; border-bottom: 2px solid #8B4513; padding-bottom: 20px; margin-bottom: 24px; }}
  .header h1 {{ color: #8B4513; font-size: 28px; margin: 8px 0; }}
  .header h2 {{ color: #333; font-size: 20px; margin: 4px 0; }}
  .subtitle {{ color: #666; font-size: 13px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #eee; font-size: 15px; }}
  td:first-child {{ width: 40%; color: #555; font-weight: bold; }}
  .footer {{ display: flex; justify-content: space-between; align-items: center; margin-top: 40px; border-top: 1px solid #ccc; padding-top: 20px; }}
  .cert-no {{ font-size: 12px; color: #888; text-align: center; margin-top: 10px; }}
  .seal {{ text-align: center; }}
  .seal p {{ font-size: 12px; color: #555; margin: 4px; }}
  h3 {{ color: #8B4513; }}
</style>
</head>
<body>
<div class="cert">
  <div class="header">
    <p class="subtitle">🏛️ Government of Maharashtra — Revenue Department</p>
    <h1>{data['cert_name_en']}</h1>
    <h2>{data['cert_name_mr']}</h2>
    <p class="subtitle">This is to certify that the following information has been verified.</p>
  </div>
  <h3>Applicant Details</h3>
  <table>
    <tr><td>Full Name</td><td>{data['full_name']}</td></tr>
    <tr><td>Father's Name</td><td>{data['father_name']}</td></tr>
    <tr><td>Date of Birth</td><td>{data['date_of_birth']}</td></tr>
    <tr><td>Gender</td><td>{data['gender']}</td></tr>
    <tr><td>District</td><td>{data['district']}</td></tr>
    <tr><td>Address</td><td>{data['address']}</td></tr>
    {income_row}
    {caste_row}
    <tr><td>Purpose</td><td>{data['certificate_purpose']}</td></tr>
    <tr><td>Valid Until</td><td>{data['valid_until']}</td></tr>
  </table>
  <div class="footer">
    <div>
      <p><b>Issued by:</b> {data['issuing_authority']}</p>
      <p><b>Date:</b> {data['issue_date']}</p>
      <p><b>Tracking ID:</b> {data['tracking_id']}</p>
    </div>
    <div class="seal">
      {qr_img}
      <p>Scan to verify</p>
      <p>🔏 Digitally Signed</p>
    </div>
  </div>
  <div class="cert-no">Certificate No: {data['cert_no']}</div>
</div>
</body>
</html>"""
