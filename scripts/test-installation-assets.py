#!/usr/bin/env python3
"""Check the built Nginx installation assets (not the Vite dev server)."""

import json
import struct
import sys
from urllib.error import HTTPError
from urllib.request import urlopen

origin = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5173").rstrip("/")
with urlopen(origin + "/manifest.webmanifest") as response:
    assert response.headers.get_content_type() == "application/manifest+json"
    assert "no-cache" in response.headers.get("Cache-Control", "")
    manifest = json.load(response)
assert manifest["start_url"] == "/overview"
assert manifest["scope"] == "/"
assert manifest["display"] == "standalone"
for icon in manifest["icons"] + [
    {"src": "/app-icons/apple-touch-icon.png", "sizes": "180x180"}
]:
    with urlopen(origin + icon["src"]) as response:
        assert response.headers.get_content_type() == "image/png"
        png = response.read()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", png[16:24])
    assert f"{width}x{height}" == icon["sizes"]
try:
    urlopen(origin + "/app-icons/does-not-exist.png")
except HTTPError as error:
    assert error.code == 404
else:
    raise AssertionError("Missing icon must return 404, not SPA HTML")
print(
    "PASS: manifest MIME/revalidation, launch, PNG sizes, Apple icon and missing-icon 404"
)
