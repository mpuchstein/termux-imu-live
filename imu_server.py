#!/usr/bin/env python3
"""IMU-Live-Demo: Handy (Termux) -> Laptop -> Browser.

Laptop:   python3 imu_server.py            # dann http://localhost:8000 im Browser
Handy:    termux-sensor -s "Accelerometer,Gyroscope,Linear" -d 20 > /dev/tcp/LAPTOP-IP/9000
  per USB statt WLAN:  adb reverse tcp:9000 tcp:9000   und als LAPTOP-IP 127.0.0.1

termux-sensor gibt mehrzeiliges JSON aus ({"Sensorname": {"values": [x, y, z]}, ...});
der Server sammelt bis die Klammern aufgehen und schickt jedes Objekt als Server-Sent Event weiter.
Nur Standardbibliothek.
"""
import json
import queue
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HTTP_PORT, TCP_PORT = 8000, 9000
HTML = Path(__file__).with_name("imu.html")
clients: list[queue.Queue] = []
lock = threading.Lock()


def broadcast(msg: str) -> None:
    with lock:
        for q in clients:
            if q.qsize() < 200:  # langsame Clients verlieren lieber alte Werte
                q.put(msg)


def split_objects(chunks):
    """Zerlegt einen Textstrom in vollständige JSON-Objekte (Klammern zählen)."""
    buf, depth, in_str, esc = [], 0, False, False
    for chunk in chunks:
        for ch in chunk:
            if depth == 0 and ch != "{":
                continue
            buf.append(ch)
            if in_str:
                esc = (ch == "\\") and not esc
                if ch == '"' and not esc:
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    yield "".join(buf)
                    buf = []


def handle_phone(conn: socket.socket, addr) -> None:
    print(f"Handy verbunden: {addr[0]}", flush=True)
    broadcast(json.dumps({"_status": f"verbunden mit {addr[0]}"}))
    chunks = iter(lambda: conn.recv(4096).decode("utf-8", "replace"), "")
    n = 0
    for obj in split_objects(chunks):
        try:
            json.loads(obj)
        except ValueError:
            continue
        broadcast(obj)
        n += 1
        if n == 1:
            print("erste Messwerte:", obj[:300].replace("\n", " "), flush=True)
    print(f"Handy getrennt ({n} Messungen)", flush=True)
    broadcast(json.dumps({"_status": "Handy getrennt"}))


def tcp_loop() -> None:
    srv = socket.create_server(("0.0.0.0", TCP_PORT), reuse_port=False)
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle_phone, args=(conn, addr), daemon=True).start()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            q: queue.Queue = queue.Queue()
            with lock:
                clients.append(q)
            try:
                while True:
                    try:
                        msg = q.get(timeout=5)
                    except queue.Empty:
                        msg = None
                    data = ": ping\n\n" if msg is None else "data: " + msg.replace("\n", " ") + "\n\n"
                    self.wfile.write(data.encode())
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                with lock:
                    clients.remove(q)
        else:
            body = HTML.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        s = '{"a": {"values": [1, 2]}}\nmüll {"b": {"x": "}{"}}{"c":{}}'
        assert list(split_objects([s[:7], s[7:]])) == ['{"a": {"values": [1, 2]}}', '{"b": {"x": "}{"}}', '{"c":{}}']
        print("selftest ok")
        sys.exit()
    threading.Thread(target=tcp_loop, daemon=True).start()
    print(f"Browser: http://localhost:{HTTP_PORT}   Handy -> TCP-Port {TCP_PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", HTTP_PORT), Handler).serve_forever()
