from PIL import Image, ImageDraw
from pathlib import Path

folder = Path("runs/detect/runs/runway_validation/high_conf_test")
frames = ["0079", "0164", "0058", "0196"]

sheet = Image.new("RGB", (1320, 880), "white")
draw = ImageDraw.Draw(sheet)

for i, frame in enumerate(frames):
    matches = list(folder.glob(f"*-{frame}_jpg*"))

    if not matches:
        print(f"Frame {frame} not found")
        continue

    img = Image.open(matches[0]).convert("RGB")
    img.thumbnail((640, 400))

    x = (i % 2) * 660
    y = (i // 2) * 440

    sheet.paste(img, (x + (660 - img.width) // 2, y + 30))
    draw.text((x + 10, y + 8), f"Frame {frame}", fill="black")
    print(f"Added frame {frame}: {matches[0].name}")

output = Path("selected_predictions.jpg")
sheet.save(output)
print(f"Saved contact sheet: {output.resolve()}")
