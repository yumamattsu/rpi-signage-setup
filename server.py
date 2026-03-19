import http.server
import json
import os

PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class AdminHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        if self.path == '/api/list-assets':
            assets_dir = os.path.join(DIRECTORY, 'assets')
            files = []
            if os.path.exists(assets_dir):
                files = [f for f in os.listdir(assets_dir) 
                         if os.path.isfile(os.path.join(assets_dir, f)) 
                         and not f.startswith('.')]
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(files).encode())
        else:
            return super().do_GET()

    def do_POST(self):
        if self.path == '/api/save-config':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                config_data = json.loads(post_data.decode('utf-8'))
                config_path = os.path.join(DIRECTORY, 'config.json')
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress log spam

if __name__ == '__main__':
    print(f"\n========================================")
    print(f"  Signage Server Started on port {PORT}")
    print(f"  Player: http://localhost:{PORT}/player.html")
    print(f"  Admin:  http://localhost:{PORT}/admin.html")
    print(f"========================================\n")
    http.server.HTTPServer(('', PORT), AdminHandler).serve_forever()
