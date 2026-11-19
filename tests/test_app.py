"""Integration smoke tests. Run with: python -m unittest discover -s tests -v"""
import io
import os
import tempfile
import unittest
from pathlib import Path
from PIL import Image
import app as civicfix

class CivicFixFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        civicfix.DB_PATH = Path(self.temp.name) / "test.db"
        civicfix.app.config.update(TESTING=True, SECRET_KEY="test-secret", UPLOAD_FOLDER=str(Path(self.temp.name)/"uploads"))
        os.makedirs(civicfix.app.config["UPLOAD_FOLDER"], exist_ok=True)
        civicfix.create_database()
        self.client = civicfix.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def token(self):
        with self.client.session_transaction() as sess:
            return sess.get("csrf_token")

    def test_end_to_end_admin_status_and_logout(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/admin").status_code, 302)
        token = self.token()
        img = io.BytesIO()
        Image.new("RGB", (8, 8), "blue").save(img, format="PNG")
        img.seek(0)
        response = self.client.post("/report", data={
            "csrf_token": token, "name": "Test Citizen", "category": "Road Damage",
            "description": "Pothole near test road", "location": "Test Road",
            "photo": (img, "road.png")
        }, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/track?report_id=1").status_code, 200)
        response = self.client.post("/admin/login", data={
            "csrf_token": self.token(), "username": civicfix.ADMIN_USERNAME,
            "password": civicfix.ADMIN_PASSWORD
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        export_response = self.client.get("/admin/export.csv")
        self.assertEqual(export_response.status_code, 200)
        self.assertIn(b"Complaint ID", export_response.data)
        response = self.client.post("/update_status/1", data={
            "csrf_token": self.token(), "status": "In Progress", "admin_remarks": "Inspection scheduled"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        tracked = self.client.get("/track?report_id=1")
        self.assertIn(b"In Progress", tracked.data)
        self.assertIn(b"Status update history", tracked.data)
        self.assertIn(b"Inspection scheduled", tracked.data)
        self.client.post("/admin/logout", data={"csrf_token": self.token()})
        self.assertEqual(self.client.get("/admin").status_code, 302)


    def test_citizen_registration_dashboard_profile_and_logout(self):
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 302)
        token = self.token()
        response = self.client.post("/register", data={
            "csrf_token": token, "name": "Citizen One", "email": "citizen@example.com", "password": "secure-pass-123"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"My complaints", response.data)
        self.assertEqual(self.client.get("/profile").status_code, 200)
        token = self.token()
        response = self.client.post("/logout", data={"csrf_token": token}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/dashboard").status_code, 302)

    def test_duplicate_registration_is_rejected_gracefully(self):
        token = self.token()
        self.client.post("/register", data={"csrf_token":token,"name":"Citizen","email":"same@example.com","password":"secure-pass-123"})
        token = self.token()
        response = self.client.post("/register", data={"csrf_token":token,"name":"Citizen Two","email":"same@example.com","password":"secure-pass-123"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"already exists", response.data)

    def test_csrf_required(self):
        self.assertEqual(self.client.post("/admin/login", data={"username":"admin","password":"x"}).status_code, 400)

    def test_invalid_image_rejected(self):
        token = self.token()
        response = self.client.post("/report", data={
            "csrf_token": token, "name":"A", "category":"Other", "description":"Something",
            "location":"Somewhere", "photo": (io.BytesIO(b"not really an image"), "fake.png")
        }, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 400)


    def test_duplicate_complaint_warning_requires_confirmation(self):
        token = self.token()
        data = {"csrf_token": token, "name": "Test Citizen", "category": "Road Damage",
                "description": "Large pothole near bus stop", "location": "Main Road"}
        first = self.client.post("/report", data=data)
        self.assertEqual(first.status_code, 200)
        token = self.token()
        data["csrf_token"] = token
        second = self.client.post("/report", data=data)
        self.assertEqual(second.status_code, 200)
        self.assertIn(b"similar complaint", second.data)
        token = self.token()
        data["csrf_token"] = token
        data["confirm_possible_duplicate"] = "yes"
        third = self.client.post("/report", data=data)
        self.assertEqual(third.status_code, 200)
        self.assertIn(b"REPORT RECEIVED", third.data)

    def test_admin_dashboard_contains_monthly_analytics(self):
        token = self.token()
        self.client.post("/admin/login", data={"csrf_token": token,
            "username": civicfix.ADMIN_USERNAME, "password": civicfix.ADMIN_PASSWORD})
        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Monthly complaint activity", response.data)

if __name__ == "__main__":
    unittest.main()
