from app import create_app
app = create_app()
with app.test_client() as c:
    r = c.get("/admin/devices")
    print("Status:", r.status_code)
    if r.status_code != 200:
        print(r.data.decode()[:2000])
    else:
        body = r.data.decode()
        # Check modal is present
        print("Modal div present:", "id=\"deviceFormModal\"" in body)
        print("data-bs-toggle on Add btn:", 'data-bs-toggle="modal"' in body)
        # Check for JS errors — look for unterminated strings or bad Jinja output
        import re
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', body, re.DOTALL)
        for i, s in enumerate(scripts):
            print(f"Script {i} (first 120 chars):", s.strip()[:120])
