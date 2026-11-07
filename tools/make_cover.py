"""Render the StrayWatch cover image (docs/cover.png, 1280x720)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
F = "C:/Windows/Fonts/"
W, H = 1280, 720
BG, CARD, TEAL, WHITE, GREY, AMBER, GREEN, RED = (
    "#0b0f14", "#141b23", "#6fc3c9", "#f4f6f8", "#9aa7b3", "#f2b84b", "#4cc38a", "#e5534b")


def font(name, size):
    return ImageFont.truetype(F + name, size)


img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

# subtle road lanes on the right
for x in (900, 1100):
    for y in range(0, H, 60):
        d.rectangle([x, y, x + 8, y + 30], fill="#1d2630")

d.text((70, 70), "FLIP THE SWITCH HACKATHON · TRACK 01", font=font("segoeuib.ttf", 22), fill=TEAL)
d.text((70, 110), "StrayWatch", font=font("segoeuib.ttf", 112), fill=WHITE)
d.text((76, 250), "Help the animal, clear the road.", font=font("segoeui.ttf", 40), fill=GREY)
d.text((76, 310), "Rescue dispatch for stray animals on Indian roads:\n3 AI agents + real responders in one Telegram group,\nconnected by Switch.",
       font=font("segoeui.ttf", 28), fill=WHITE, spacing=10)

# chat-style cards
cards = [
    ("sw-triage", "SW-0046 · HIGH · cow lying in lane, Ratu Road", RED),
    ("sw-dispatch", "Alerted NGO + traffic police · accepted in 4 min", AMBER),
    ("sw-dispatch", "Closed with photo proof · 22 min to clear", GREEN),
    ("sw-hotspot", "Ratu Road 6–7 PM: send cattle team at 5 PM", TEAL),
]
y = 470
for who, text, col in cards:
    d.rounded_rectangle([70, y, 760, y + 50], radius=12, fill=CARD)
    d.ellipse([86, y + 17, 102, y + 33], fill=col)
    d.text((114, y + 11), who, font=font("segoeuib.ttf", 21), fill=col)
    d.text((114 + 150, y + 11), text, font=font("segoeui.ttf", 21), fill=WHITE)
    y += 58

# emoji badge
try:
    emoji = ImageFont.truetype(F + "seguiemj.ttf", 150)
    d.text((930, 180), "🐄", font=emoji, embedded_color=True)
    d.text((960, 380), "🐕", font=ImageFont.truetype(F + "seguiemj.ttf", 110), embedded_color=True)
except Exception:
    pass

d.text((830, 640), "Switch · Telegram · Claude Code", font=font("segoeuib.ttf", 22), fill=GREY)

out = ROOT / "docs" / "cover.png"
out.parent.mkdir(exist_ok=True)
img.save(out)
print(out)
