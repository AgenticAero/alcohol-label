"""Render the synthetic starter label images (development tool, not application code).

Run from the repository root:

    poetry run python tests/fixtures/render_starter_labels.py

Both labels are fictional. They are identical except for one deliberately
changed word in the government warning. The committed PNGs are the source of
truth: output depends on the installed DejaVu fonts, so re-rendering on another
machine may differ slightly. Check hashes in manifest.json after re-rendering.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
OUT_DIR = Path(__file__).parent / "labels"

WARNING_HEADING = "GOVERNMENT WARNING:"
WARNING_BODY = (
    "(1) According to the Surgeon General, women should not drink alcoholic "
    "beverages during pregnancy because of the risk of birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability to drive a car "
    "or operate machinery, and may cause health problems."
)
# One word changed: "impairs" -> "affects".
CHANGED_WARNING_BODY = WARNING_BODY.replace("impairs", "affects")

INK = (35, 30, 28)
PAPER = (244, 238, 222)
ACCENT = (120, 40, 30)
SIZE = (1200, 900)


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size)


def _centered(draw, y, text, font, fill=INK):
    width = draw.textlength(text, font=font)
    draw.text(((SIZE[0] - width) / 2, y), text, font=font, fill=fill)


def _warning(draw, body: str, top: int) -> None:
    """Wrapped paragraph: bold uppercase heading, regular-weight body."""
    bold = _font("DejaVuSans-Bold.ttf", 22)
    regular = _font("DejaVuSans.ttf", 22)
    words = [(WARNING_HEADING.split()[0], bold), (WARNING_HEADING.split()[1], bold)]
    words += [(word, regular) for word in body.split()]
    left, right, line_height = 110, SIZE[0] - 110, 34
    x, y = left, top
    space = draw.textlength(" ", font=regular)
    for word, font in words:
        width = draw.textlength(word, font=font)
        if x + width > right:
            x, y = left, y + line_height
        draw.text((x, y), word, font=font, fill=INK)
        x += width + space


def render(warning_body: str) -> Image.Image:
    image = Image.new("RGB", SIZE, PAPER)
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 30, SIZE[0] - 30, SIZE[1] - 30), outline=ACCENT, width=6)

    _centered(draw, 90, "OLD TOM", _font("DejaVuSerif-Bold.ttf", 120), ACCENT)
    _centered(draw, 250, "Straight Bourbon Whiskey", _font("DejaVuSerif-Bold.ttf", 46))
    _centered(draw, 340, "45% Alc./Vol. (90 Proof)", _font("DejaVuSerif.ttf", 40))
    _centered(draw, 410, "750 mL", _font("DejaVuSerif.ttf", 40))
    small = _font("DejaVuSerif.ttf", 30)
    _centered(draw, 500, "Distilled and bottled by Example Distillery", small)
    _centered(draw, 545, "Louisville, KY", small)
    _warning(draw, warning_body, top=650)
    return image


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    render(WARNING_BODY).save(OUT_DIR / "starter-clear.png")
    render(CHANGED_WARNING_BODY).save(OUT_DIR / "starter-warning-changed.png")


if __name__ == "__main__":
    main()
