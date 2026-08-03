"""
ProtonAI - FHIR HTTP Client (Live Integration)
عميل FHIR حي يتكلم HTTP (urllib) + خادم وهمي محلي للاختبارات (http.server)
POST bundle/مورد ← GET مريض ← is_reachable. نفس العقد لخادم مستشفى حقيقي
"""

import json
import logging
import threading
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

logger = logging.getLogger("ProtonAI.FHIRClient")


class _MockFHIRHandler(BaseHTTPRequestHandler):
    """خادم FHIR وهمي محلي: يخزن المورده ويرجعها"""
    store = {}

    def _send(self, code: int, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}")
        rid = str(body.get("id", "auto"))
        key = f"{body.get('resourceType', 'Unknown')}/{rid}"
        type(self).store[key] = body
        self._send(201, {"id": rid, "status": "created"})

    def do_GET(self):
        key = self.path.lstrip("/")
        if key in type(self).store:
            self._send(200, type(self).store[key])
        else:
            self._send(404, {"error": "not found"})

    def log_message(self, *args):  # كتم الضجيج بالاختبارات
        pass


def start_mock_server():
    """تشغيل خادم وهمي على منفذ عشوائي، يرجع (server, base_url)"""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _MockFHIRHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]
    return server, f"http://127.0.0.1:{port}"


class FHIRClient:
    """
    عميل FHIR حي.
    - post_resource / post_bundle: إرسال (POST) → (status, body).
    - get_patient: جلب مريض (GET) → dict أو None.
    - is_reachable: هل الخادم يستجيب؟
    """

    def __init__(self, base_url: str, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, obj=None):
        url = self.base_url + path
        data = json.dumps(obj).encode("utf-8") if obj is not None else None
        req = urllib.request.Request(
            url, data=data, method=method,
            headers={"Content-Type": "application/fhir+json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")
        except Exception:
            return None, None  # غير قابل للوصول

    def post_resource(self, resource) -> tuple:
        """إرسال مورد لـ /{resourceType}"""
        return self._request("POST", f"/{resource.get('resourceType')}", resource)

    def post_bundle(self, bundle) -> tuple:
        """إرسال Bundle"""
        return self._request("POST", "/Bundle", bundle)

    def get_patient(self, patient_id: str):
        """جلب مريض، أو None إن غاب/تعذّر"""
        status, body = self._request("GET", f"/Patient/{patient_id}")
        return body if status == 200 else None

    def is_reachable(self) -> bool:
        """هل الخادم يستجيب؟"""
        status, _ = self._request("GET", "/metadata")
        return status is not None
