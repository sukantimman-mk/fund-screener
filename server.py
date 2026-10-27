"""
Finnomena Fund Screener — Local Server & API
=============================================
เซิร์ฟเวอร์แบบเบาพิเศษ (Zero Dependencies) สำหรับรันหน้าเว็บ Fund Screener
พร้อมรองรับ API อัพเดทข้อมูลกองทุนแบบเรียลไทม์
"""

import http.server
import socketserver
import threading
import json
import os
import sys
import webbrowser
import time

from update_data import run_update

# Ensure utf-8 output on Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

update_state = {
    "status": "idle",       # "idle", "updating", "done", "error"
    "progress": 0,
    "message": "พร้อมใช้งาน",
    "stats": None,
    "error": None
}
state_lock = threading.Lock()

def progress_callback(pct, msg):
    with state_lock:
        if pct is not None:
            update_state["progress"] = pct
        update_state["message"] = msg

def perform_background_update():
    global update_state
    try:
        with state_lock:
            update_state["status"] = "updating"
            update_state["progress"] = 0
            update_state["message"] = "กำลังเริ่มดึงข้อมูล..."
            update_state["error"] = None
            
        stats = run_update(base_dir=BASE_DIR, progress_cb=progress_callback)
        
        with state_lock:
            update_state["status"] = "done"
            update_state["progress"] = 100
            update_state["message"] = f"อัพเดทสำเร็จ! ทั้งหมด {stats['total_funds']:,} กอง (+{stats['new_funds']:,} ใหม่)"
            update_state["stats"] = stats
    except Exception as e:
        import traceback
        traceback.print_exc()
        with state_lock:
            update_state["status"] = "error"
            update_state["message"] = f"เกิดข้อผิดพลาด: {str(e)}"
            update_state["error"] = str(e)

class FundScreenHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def end_headers(self):
        # Enable CORS for local cross-origin access (e.g. if opened via file://)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            with state_lock:
                data = json.dumps(update_state, ensure_ascii=False)
            self.wfile.write(data.encode('utf-8'))
            return
            
        if self.path == '/api/funds':
            funds_file = os.path.join(BASE_DIR, 'funds.json')
            if os.path.exists(funds_file):
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                with open(funds_file, 'rb') as f:
                    self.wfile.write(f.read())
                return

        return super().do_GET()

    def do_POST(self):
        if self.path == '/api/update':
            with state_lock:
                if update_state["status"] == "updating":
                    self.send_response(409)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.end_headers()
                    resp = json.dumps({"status": "busy", "message": "ระบบกำลังทำการอัพเดทอยู่แล้ว"}, ensure_ascii=False)
                    self.wfile.write(resp.encode('utf-8'))
                    return
                
                # Start update
                t = threading.Thread(target=perform_background_update, daemon=True)
                t.start()
                
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            resp = json.dumps({"status": "started", "message": "เริ่มการอัพเดทข้อมูลในเบื้องหลังแล้ว"}, ensure_ascii=False)
            self.wfile.write(resp.encode('utf-8'))
            return

        self.send_response(404)
        self.end_headers()

def run_server():
    port = PORT
    for attempt in range(5):
        try:
            handler = FundScreenHandler
            server = socketserver.TCPServer(("", port), handler)
            break
        except OSError:
            port += 1
            
    url = f"http://localhost:{port}/index.html"
    print("=" * 60)
    print("  🚀 Finnomena Fund Screener Local Server")
    print(f"  🌐 URL: {url}")
    print("  💡 กด Ctrl+C ที่หน้าต่างนี้เมื่อต้องการปิดเซิร์ฟเวอร์")
    print("=" * 60)
    
    server.serve_forever()

if __name__ == '__main__':
    run_server()
