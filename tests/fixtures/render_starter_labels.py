"""Render the synthetic starter label images (development tool, not application code).

Run from the repository root:

    poetry run python tests/fixtures/render_starter_labels.py

Regeneration requires Pillow and these DejaVu font files: DejaVuSans.ttf,
DejaVuSans-Bold.ttf, DejaVuSerif.ttf and DejaVuSerif-Bold.ttf. The default
directory is /usr/share/fonts/truetype/dejavu. For another installation, use:

    poetry run python tests/fixtures/render_starter_labels.py --font-dir "/path/to/fonts"

Using the committed PNG fixtures does not require these fonts.

All labels are fictional. Starter variants exercise a changed warning word and a
title-case warning heading; the others vary one printed statement (origin, net
contents, alcohol, producer lines) for comparison rules.
The committed PNGs are the source of truth: output depends on the installed DejaVu fonts, so re-rendering on another
machine may differ slightly. Check hashes in manifest.json after re-rendering.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DEFAULT_FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
REQUIRED_FONTS = (
    "DejaVuSans.ttf",
    "DejaVuSans-Bold.ttf",
    "DejaVuSerif.ttf",
    "DejaVuSerif-Bold.ttf",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render the synthetic starter label fixtures."
    )
    parser.add_argument(
        "--font-dir",
        type=Path,
        default=DEFAULT_FONT_DIR,
        help=f"Directory containing the required DejaVu TTF files (default: {DEFAULT_FONT_DIR}).",
    )
    args = parser.parse_args()

    args.font_dir = args.font_dir.expanduser()
    missing = [name for name in REQUIRED_FONTS if not (args.font_dir / name).is_file()]
    if missing:
        parser.error(
            f"Missing fonts in {args.font_dir}: {', '.join(missing)}. "
            "Install the DejaVu fonts or pass --font-dir PATH."
        )

    return args


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


def _font(font_dir: Path, name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(font_dir / name), size)


def _centered(draw, y, text, font, fill=INK, canvas_width=SIZE[0]):
    width = draw.textlength(text, font=font)
    draw.text(((canvas_width - width) / 2, y), text, font=font, fill=fill)


def _warning(
    draw,
    heading: str,
    body: str,
    top: int,
    font_dir: Path,
    heading_bold: bool = True,
    body_bold: bool = False,
    *,
    family: str = "DejaVuSans",
    size: int = 22,
    left: int = 110,
    right: int = SIZE[0] - 110,
    line_height: int = 34,
) -> None:
    """Wrapped paragraph; the heading and body weights are set independently."""
    bold = _font(font_dir, f"{family}-Bold.ttf", size)
    regular = _font(font_dir, f"{family}.ttf", size)
    words = [(word, bold if heading_bold else regular) for word in heading.split()]
    words += [(word, bold if body_bold else regular) for word in body.split()]
    x, y = left, top
    space = draw.textlength(" ", font=regular)
    for word, font in words:
        width = draw.textlength(word, font=font)
        if x + width > right:
            x, y = left, y + line_height
        draw.text((x, y), word, font=font, fill=INK)
        x += width + space


@dataclass(frozen=True)
class LabelSpec:
    """Printed statements for one synthetic label; the heading is bold by default."""

    filename: str
    brand: str = "OLD TOM"
    class_type: str = "Straight Bourbon Whiskey"
    alcohol: str | None = "45% Alc./Vol. (90 Proof)"
    net_contents: str = "750 mL"
    producer_lines: tuple[str, ...] = (
        "Distilled and bottled by Example Distillery",
        "Louisville, KY",
    )
    origin: str | None = None
    warning_heading: str = WARNING_HEADING
    warning_body: str = WARNING_BODY
    heading_bold: bool = True
    body_bold: bool = False
    statements: bool = True
    warning: bool = True


SPECS = (
    LabelSpec("starter-clear.png"),
    LabelSpec("starter-warning-changed.png", warning_body=CHANGED_WARNING_BODY),
    LabelSpec("starter-warning-title-case.png", warning_heading="Government Warning:"),
    LabelSpec("warning-heading-regular.png", heading_bold=False),
    LabelSpec("warning-all-bold.png", body_bold=True),
    LabelSpec(
        "import-product-of.png",
        brand="HIGHLAND REEL",
        class_type="Single Malt Scotch Whisky",
        alcohol="43% Alc./Vol. (86 Proof)",
        net_contents="700 mL",
        producer_lines=("Imported by Example Imports", "New York, NY"),
        origin="Product of Scotland",
    ),
    LabelSpec(
        "import-no-origin.png",
        brand="HIGHLAND REEL",
        class_type="Single Malt Scotch Whisky",
        alcohol="43% Alc./Vol. (86 Proof)",
        net_contents="700 mL",
        producer_lines=("Imported by Example Imports", "New York, NY"),
    ),
    LabelSpec("net-metric-and-floz.png", net_contents="750 mL / 25.4 FL. OZ."),
    LabelSpec("net-floz-only.png", net_contents="25.4 FL. OZ."),
    LabelSpec("abv-proof-only.png", alcohol="90 Proof"),
    LabelSpec(
        "producer-street.png",
        producer_lines=("Bottled by Example Distillery", "123 Main St, Louisville, KY"),
    ),
    LabelSpec(
        "producer-new-louisville.png",
        producer_lines=("Bottled by Example Distillery", "New Louisville, KY"),
    ),
    # Front/back pair: every statement on the front, the warning alone on the back.
    LabelSpec("front-no-warning.png", warning=False),
    LabelSpec("back-warning-only.png", statements=False),
)


def render(spec: LabelSpec, font_dir: Path) -> Image.Image:
    image = Image.new("RGB", SIZE, PAPER)
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 30, SIZE[0] - 30, SIZE[1] - 30), outline=ACCENT, width=6)

    lines = (*spec.producer_lines, *((spec.origin,) if spec.origin else ()))
    if spec.statements:
        size = 120
        while (
            draw.textlength(spec.brand, _font(font_dir, "DejaVuSerif-Bold.ttf", size))
            > 1000
        ):
            size -= 4
        _centered(
            draw, 90, spec.brand, _font(font_dir, "DejaVuSerif-Bold.ttf", size), ACCENT
        )
        _centered(
            draw, 250, spec.class_type, _font(font_dir, "DejaVuSerif-Bold.ttf", 46)
        )
        medium = _font(font_dir, "DejaVuSerif.ttf", 40)
        if spec.alcohol:
            _centered(draw, 340, spec.alcohol, medium)
        _centered(draw, 410, spec.net_contents, medium)
        small = _font(font_dir, "DejaVuSerif.ttf", 30)
        for index, line in enumerate(lines):
            _centered(draw, 500 + 45 * index, line, small)
    if spec.warning:
        _warning(
            draw,
            spec.warning_heading,
            spec.warning_body,
            top=(650 if len(lines) <= 3 else 700) if spec.statements else 380,
            font_dir=font_dir,
            heading_bold=spec.heading_bold,
            body_bold=spec.body_bold,
        )
    return image


def render_wide_two_column(font_dir: Path) -> Image.Image:
    """Held-out layout: landscape, left-aligned text in two columns, serif warning."""
    image = Image.new("RGB", (1500, 800), (238, 244, 232))
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 30, 1470, 770), outline=(30, 70, 50), width=6)
    serif_bold = _font(font_dir, "DejaVuSerif-Bold.ttf", 72)
    draw.text((70, 80), "BLACK HEATH", font=serif_bold, fill=(30, 70, 50))
    draw.text(
        (70, 210),
        "Rye Whiskey",
        font=_font(font_dir, "DejaVuSerif-Bold.ttf", 44),
        fill=INK,
    )
    medium = _font(font_dir, "DejaVuSerif.ttf", 34)
    draw.text((70, 300), "50% Alc./Vol. (100 Proof)", font=medium, fill=INK)
    draw.text((70, 360), "1 L", font=medium, fill=INK)
    small = _font(font_dir, "DejaVuSerif.ttf", 28)
    draw.text((780, 90), "Bottled by Heath Spirits Co.", font=small, fill=INK)
    draw.text((780, 130), "Frankfort, KY", font=small, fill=INK)
    _warning(
        draw,
        WARNING_HEADING,
        WARNING_BODY,
        top=250,
        font_dir=font_dir,
        family="DejaVuSerif",
        size=24,
        left=780,
        right=1430,
        line_height=36,
    )
    return image


def render_tall_narrow(font_dir: Path) -> Image.Image:
    """Held-out layout: portrait, centered sans text, imported, regular-weight heading."""
    image = Image.new("RGB", (800, 1200), (232, 236, 246))
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 30, 770, 1170), outline=(40, 50, 110), width=6)
    sans = "DejaVuSans.ttf"
    _centered(
        draw,
        100,
        "Northgate",
        _font(font_dir, "DejaVuSans-Bold.ttf", 84),
        (40, 50, 110),
        800,
    )
    _centered(draw, 230, "Blended Scotch Whisky", _font(font_dir, sans, 36), INK, 800)
    for y, text in (
        (320, "40% Alc./Vol."),
        (380, "700 mL"),
        (450, "Product of Scotland"),
    ):
        _centered(draw, y, text, _font(font_dir, sans, 34), INK, 800)
    for y, text in ((540, "Imported by Northgate Imports"), (585, "Chicago, IL")):
        _centered(draw, y, text, _font(font_dir, sans, 28), INK, 800)
    _warning(
        draw,
        WARNING_HEADING,
        WARNING_BODY,
        top=700,
        font_dir=font_dir,
        heading_bold=False,
        size=20,
        left=70,
        right=730,
        line_height=30,
    )
    return image


HELD_OUT = (
    ("held-out-wide-two-column.png", render_wide_two_column),
    ("held-out-tall-narrow.png", render_tall_narrow),
)


def main() -> None:
    args = parse_args()
    OUT_DIR.mkdir(exist_ok=True)
    for spec in SPECS:
        render(spec, args.font_dir).save(OUT_DIR / spec.filename)
    for filename, draw_label in HELD_OUT:
        draw_label(args.font_dir).save(OUT_DIR / filename)


if __name__ == "__main__":
    main()
