import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from fastapi.testclient import TestClient
from backend.main import app
from backend.api.documents import indexing_jobs

class TestAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_check(self):
        """Verifies that the /health endpoint is operational and returns standard content."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy", "service": "DocMind Backend"})

    def test_auth_check_unauthenticated(self):
        """Checks that accessing auth check with no credentials returns a standard 401 response."""
        response = self.client.get("/api/auth/check")
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertNotIn("authenticated", data.get("data", {}))

    def test_login_success(self):
        """Validates that login returns standard status data and registers sessions."""
        response = self.client.post(
            "/api/login",
            data={"email": "tester@docmind.local", "password": "demo-access"}
        )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertTrue(res_data["success"])
        self.assertEqual(res_data["data"]["session_id"], "tester@docmind.local")
        self.assertEqual(res_data["data"]["redirect"], "/dashboard")

    def test_documents_fetch(self):
        """Verifies document list fetches return standardized document schema structures."""
        response = self.client.get("/api/documents")
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertTrue(res_data["success"])
        self.assertIn("documents", res_data["data"])
        self.assertIsInstance(res_data["data"]["documents"], list)

    def test_status_invalid_job_id(self):
        """Checks that polling for an invalid job ID returns a standard 404 response."""
        response = self.client.get("/api/upload/status/invalid-uuid-format")
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["message"], "Background indexing job not found")

    def test_status_valid_job_id(self):
        """Pre-populates a mock background job and verifies polling retrieves standard status format."""
        mock_job_id = "mock-uuid-12345"
        indexing_jobs[mock_job_id] = {
            "job_id": mock_job_id,
            "filename": "test-document.pdf",
            "status": "processing",
            "progress": 45,
            "pages": 0,
            "error": None
        }
        
        response = self.client.get(f"/api/upload/status/{mock_job_id}")
        self.assertEqual(response.status_code, 200)
        
        res_data = response.json()
        self.assertTrue(res_data["success"])
        self.assertEqual(res_data["data"]["job_id"], mock_job_id)
        self.assertEqual(res_data["data"]["status"], "processing")
        self.assertEqual(res_data["data"]["progress"], 45)
        
        # Clean up mock job
        indexing_jobs.pop(mock_job_id, None)

if __name__ == "__main__":
    unittest.main()
