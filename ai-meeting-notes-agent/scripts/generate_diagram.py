from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT = 1200, 720
BACKGROUND_COLOR = "#ffffff"
BORDER_COLOR = "#2f4f4f"
ACCENT_COLOR = "#f78c40"
TEXT_COLOR = "#1f2933"
SECONDARY_TEXT_COLOR = "#617283"

BOX_STYLE = {
    "fill": "#f1f5f9",
    "outline": BORDER_COLOR,
    "width": 3,
    "radius": 20,
}

CONNECTOR_COLOR = "#2563eb"
CONNECTOR_WIDTH = 4

def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


FONT_TITLE = _load_font("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 32)
FONT_LABEL = _load_font("/System/Library/Fonts/Supplemental/Arial.ttf", 24)
FONT_SMALL = _load_font("/System/Library/Fonts/Supplemental/Arial.ttf", 20)


def rounded_rectangle(draw: ImageDraw.ImageDraw, xy, style):
    radius = style.get("radius", 0)
    draw.rounded_rectangle(xy, radius=radius, fill=style["fill"], outline=style["outline"], width=style["width"])


def center_text(draw: ImageDraw.ImageDraw, text: str, box, font, color=TEXT_COLOR):
    x1, y1, x2, y2 = box
    w, h = draw.textbbox((0, 0), text, font=font)[2:]
    draw.text((x1 + (x2 - x1 - w) / 2, y1 + (y2 - y1 - h) / 2), text, fill=color, font=font)


def draw_box(draw: ImageDraw.ImageDraw, top_left, size, title, lines):
    x, y = top_left
    width, height = size
    box = (x, y, x + width, y + height)
    rounded_rectangle(draw, box, BOX_STYLE)
    draw.text((x + 20, y + 20), title, fill=TEXT_COLOR, font=FONT_LABEL)
    for idx, line in enumerate(lines):
        draw.text((x + 20, y + 70 + idx * 26), line, fill=SECONDARY_TEXT_COLOR, font=FONT_SMALL)
    return box


def draw_connector(draw: ImageDraw.ImageDraw, start, end, dashed=False):
    if dashed:
        draw.line([start, end], fill=CONNECTOR_COLOR, width=CONNECTOR_WIDTH)
    else:
        draw.line([start, end], fill=CONNECTOR_COLOR, width=CONNECTOR_WIDTH)

    arrow_size = 14
    direction = (end[0] - start[0], end[1] - start[1])
    length = (direction[0] ** 2 + direction[1] ** 2) ** 0.5
    if length == 0:
        return
    unit = (direction[0] / length, direction[1] / length)
    left = (end[0] - unit[0] * arrow_size - unit[1] * arrow_size / 2,
            end[1] - unit[1] * arrow_size + unit[0] * arrow_size / 2)
    right = (end[0] - unit[0] * arrow_size + unit[1] * arrow_size / 2,
             end[1] - unit[1] * arrow_size - unit[0] * arrow_size / 2)
    draw.polygon([end, left, right], fill=CONNECTOR_COLOR)


def main():
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)

    draw.text((WIDTH / 2, 40), "AI Meeting Notes Agent", fill=TEXT_COLOR, font=FONT_TITLE, anchor="mm")

    s3_box = draw_box(draw, (60, 140), (240, 220), "Amazon S3", ["Upload transcript", "or media file"])
    lambda_box = draw_box(draw, (360, 140), (290, 220), "AWS Lambda", ["Retrieve input", "Transcribe if needed", "Call Bedrock", "Translate summary", "Email participants"])
    services_box = draw_box(draw, (700, 120), (200, 260), "AI Services", ["Amazon Transcribe", "Amazon Bedrock", "Amazon Translate", "Amazon Comprehend"])
    ses_box = draw_box(draw, (960, 140), (220, 220), "Amazon SES", ["Localized summary", "HTML + text email"])

    agentcore_box = draw_box(draw, (360, 420), (290, 180), "AgentCore", ["Orchestrates flow", "Expose agent interface"])
    participants_box = draw_box(draw, (700, 420), (300, 180), "Participants", ["Receive summary", "with action items"])

    draw_connector(draw, (s3_box[2], s3_box[1] + 110), (lambda_box[0], lambda_box[1] + 110))
    draw_connector(draw, (lambda_box[2], lambda_box[1] + 90), (services_box[0], services_box[1] + 90))
    draw_connector(draw, (services_box[2], services_box[1] + 90), (ses_box[0], ses_box[1] + 90))
    draw_connector(draw, (ses_box[0] + 110, ses_box[3]), (participants_box[0] + 150, participants_box[1]))
    draw_connector(draw, (lambda_box[0] + 145, lambda_box[3]), (agentcore_box[0] + 145, agentcore_box[1]))
    draw_connector(draw, (agentcore_box[2], agentcore_box[1] + 90), (participants_box[0], participants_box[1] + 90))

    output_path = Path(__file__).resolve().parent.parent / "diagram.png"
    image.save(output_path, format="PNG", optimize=True)
    print(f"Diagram saved to {output_path}")


if __name__ == "__main__":
    main()
