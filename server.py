"""Eenvoudige HTTP-server met prijs-API."""
from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import ThreadingMixIn
from typing import Any

from pricing_engine import calculate_quote

ROOT = Path(__file__).parent / "site"


class QuoteRequestHandler(SimpleHTTPRequestHandler):
  def __init__(self, *args: Any, **kwargs: Any) -> None:
    super().__init__(*args, directory=str(ROOT), **kwargs)

  def do_POST(self) -> None:  # noqa: N802 (convention inherited from BaseHTTPRequestHandler)
    if self.path != "/api/quote":
      self.send_error(HTTPStatus.NOT_FOUND, "Endpoint bestaat niet")
      return

    length = int(self.headers.get("Content-Length", "0"))
    raw_body = self.rfile.read(length)
    try:
      data = json.loads(raw_body or b"{}")
    except json.JSONDecodeError:
      self.send_error(HTTPStatus.BAD_REQUEST, "Ongeldige JSON payload")
      return

    service = data.get("service")
    payload = data.get("payload") or {}
    if not service:
      self.send_error(HTTPStatus.BAD_REQUEST, "Veld 'service' is verplicht")
      return

    try:
      quote = calculate_quote(str(service), payload)
    except ValueError as exc:
      self.send_error(HTTPStatus.BAD_REQUEST, str(exc))
      return

    response = json.dumps(quote).encode("utf-8")
    self.send_response(HTTPStatus.OK)
    self.send_header("Content-Type", "application/json")
    self.send_header("Content-Length", str(len(response)))
    self.end_headers()
    self.wfile.write(response)

class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
  daemon_threads = True


def serve(port: int) -> None:
  with ThreadingSimpleServer(("0.0.0.0", port), QuoteRequestHandler) as httpd:
    print(f"➜ Server actief op http://localhost:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Start de demo-server met prijs-API")
  parser.add_argument("--port", type=int, default=4173, help="Poort voor de HTTP-server (default: 4173)")
  args = parser.parse_args()
  serve(args.port)
