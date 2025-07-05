#!/usr/bin/env python3
"""
Simple HTTP server to serve the test map HTML file.
This avoids CORS issues when opening the HTML file directly in a browser.
"""
import http.server
import socketserver
import webbrowser
import sys
from pathlib import Path

PORT = 3000

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=Path(__file__).parent, **kwargs)

def main():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving test map at http://localhost:{PORT}")
        print(f"Opening test map: http://localhost:{PORT}/test_map.html")
        
        # Try to open browser automatically
        try:
            webbrowser.open(f"http://localhost:{PORT}/test_map.html")
        except:
            print("Could not open browser automatically")
        
        print("Press Ctrl+C to stop the server")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")

if __name__ == "__main__":
    main()