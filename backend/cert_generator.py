"""
BugHunter Lab — Certificate Generator
Generates PDF/PNG certificates for challenge completions
"""

import os, uuid
from datetime import datetime

CERTS_DIR = "certs"
os.makedirs(CERTS_DIR, exist_ok=True)

def generate_certificate(username: str, challenge_name: str, points: int) -> str:
    """
    Generate a certificate PNG using PIL.
    Returns relative path to the certificate file.
    Falls back to HTML cert if PIL not available.
    """
    filename = f"{uuid.uuid4().hex}.png"
    filepath = os.path.join(CERTS_DIR, filename)

    try:
        from PIL import Image, ImageDraw, ImageFont
        _generate_png(filepath, username, challenge_name, points)
    except ImportError:
        filename = filename.replace(".png", ".html")
        filepath = os.path.join(CERTS_DIR, filename)
        _generate_html(filepath, username, challenge_name, points)

    return filename


def _generate_png(filepath, username, challenge_name, points):
    from PIL import Image, ImageDraw, ImageFont

    W, H = 900, 620
    img  = Image.new("RGB", (W, H), "#080d1a")
    draw = ImageDraw.Draw(img)

    # Border
    for i in range(4):
        draw.rectangle([i, i, W-i-1, H-i-1], outline="#00ff88")

    # Corner accents
    for x, y in [(20,20),(W-70,20),(20,H-70),(W-70,H-70)]:
        draw.rectangle([x, y, x+50, y+50], outline="#00ff88", width=2)

    # Title
    try:
        font_big   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
        font_med   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        font_mono  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 16)
    except Exception:
        font_big = font_med = font_small = font_mono = ImageFont.load_default()

    # AgniProtocol header
    draw.text((W//2, 70),  "AGNIPROTOCOL",      font=font_big,   fill="#00ff88", anchor="mm")
    draw.text((W//2, 115), "BugHunter Lab",       font=font_small, fill="#8896b0", anchor="mm")

    # Divider
    draw.line([(80, 145), (W-80, 145)], fill="#1a2d1a", width=1)

    # Certificate of Achievement
    draw.text((W//2, 185), "Certificate of Achievement", font=font_med, fill="#e0e6ff", anchor="mm")
    draw.text((W//2, 230), "This certifies that",        font=font_small, fill="#8896b0", anchor="mm")

    # Name
    draw.text((W//2, 290), username.upper(), font=font_big, fill="#00ff88", anchor="mm")

    # Challenge
    draw.text((W//2, 350), "has successfully completed",       font=font_small, fill="#8896b0", anchor="mm")
    draw.text((W//2, 390), f'"{challenge_name}"',              font=font_med,   fill="#e0e6ff", anchor="mm")
    draw.text((W//2, 430), f"earning {points} points",         font=font_small, fill="#ffd32a", anchor="mm")

    # Date & ID
    date    = datetime.now().strftime("%B %d, %Y")
    cert_id = uuid.uuid4().hex[:12].upper()
    draw.text((W//2, 500), f"Issued: {date}",                  font=font_mono, fill="#8896b0", anchor="mm")
    draw.text((W//2, 525), f"Certificate ID: AGNI-{cert_id}", font=font_mono, fill="#8896b0", anchor="mm")

    # Signature line
    draw.line([(W//2-100, 570), (W//2+100, 570)], fill="#00ff88", width=1)
    draw.text((W//2, 585), "Ganpat N. Darade — Founder, AgniProtocol", font=font_mono, fill="#8896b0", anchor="mm")

    img.save(filepath, "PNG", quality=95)


def _generate_html(filepath, username, challenge_name, points):
    date    = datetime.now().strftime("%B %d, %Y")
    cert_id = uuid.uuid4().hex[:12].upper()

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>Certificate — {username}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;600&display=swap');
  body {{ margin:0; background:#080d1a; display:flex; align-items:center; justify-content:center; min-height:100vh; }}
  .cert {{ width:860px; border:3px solid #00ff88; padding:60px; text-align:center; font-family:'Inter',sans-serif; position:relative; }}
  .cert::before,.cert::after {{ content:''; position:absolute; width:50px; height:50px; border:2px solid #00ff88; }}
  .cert::before {{ top:16px; left:16px; border-right:none; border-bottom:none; }}
  .cert::after  {{ bottom:16px; right:16px; border-left:none; border-top:none; }}
  h1 {{ color:#00ff88; font-family:'JetBrains Mono',monospace; font-size:2.4rem; margin:0 0 4px; letter-spacing:.1em; }}
  .sub {{ color:#8896b0; font-size:.9rem; margin-bottom:30px; }}
  hr {{ border:none; border-top:1px solid #1a2d1a; margin:20px 60px; }}
  .label {{ color:#8896b0; font-size:.85rem; margin:8px 0 4px; }}
  .name {{ color:#00ff88; font-size:2rem; font-weight:700; margin:8px 0; letter-spacing:.05em; }}
  .challenge {{ color:#e0e6ff; font-size:1.3rem; font-weight:600; margin:8px 0; }}
  .pts {{ color:#ffd32a; font-size:1rem; margin:4px 0 20px; }}
  .meta {{ color:#8896b0; font-family:'JetBrains Mono',monospace; font-size:.75rem; margin-top:30px; }}
  .sig-line {{ border-top:1px solid #00ff88; width:200px; margin:30px auto 6px; }}
</style></head>
<body><div class="cert">
  <h1>AGNIPROTOCOL</h1>
  <div class="sub">BugHunter Lab</div>
  <hr>
  <div class="label">Certificate of Achievement</div>
  <div class="label" style="margin-top:16px">This certifies that</div>
  <div class="name">{username.upper()}</div>
  <div class="label">has successfully completed</div>
  <div class="challenge">"{challenge_name}"</div>
  <div class="pts">earning {points} points</div>
  <div class="sig-line"></div>
  <div class="meta">Ganpat N. Darade — Founder, AgniProtocol</div>
  <div class="meta">Issued: {date} &nbsp;|&nbsp; ID: AGNI-{cert_id}</div>
</div></body></html>"""

    with open(filepath, "w") as f:
        f.write(html)
