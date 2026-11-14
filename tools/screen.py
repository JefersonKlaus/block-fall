"""Draw the app's current screen into an image, from the real controls.

Every position, size, color, and text comes from the live view (and the
layout's own paddings and spacings), laid out the way the app's Flet layout
places them (see src/ui/app.py). Text uses Roboto, Flutter's default font.
"""

import os
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

import config

# Roboto (Flutter's default font), shipped with the tools (Apache 2.0).
FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
# Flutter's default line height for Roboto, relative to the font size.
LINE_HEIGHT = 1.17


class Canvas:
    """Drawing in the app's logical pixels, scaled to the image's pixels."""

    def __init__(self, width: float, height: float, scale: float, background: Optional[str]):
        """`background=None`: a transparent picture (e.g. the launch screen's)."""
        self.scale = scale
        size = (round(width * scale), round(height * scale))
        self.image = Image.new("RGBA", size) if background is None else Image.new("RGB", size, background)
        self.draw = ImageDraw.Draw(self.image)

    def font(self, size: float, weight: str) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(os.path.join(FONT_DIR, f"Roboto-{weight}.ttf"), round(size * self.scale))

    def box(self, x: float, y: float, w: float, h: float, radius: float, color: str) -> None:
        s = self.scale
        # At least one pixel, even when the picture is drawn very small.
        x0, y0 = x * s, y * s
        x1, y1 = max(x0, (x + w) * s - 1), max(y0, (y + h) * s - 1)
        self.draw.rounded_rectangle([x0, y0, x1, y1], radius=min(radius * s, (x1 - x0) / 2), fill=color)

    def text_width(self, text: str, size: float, weight: str) -> float:
        return self.draw.textlength(text, font=self.font(size, weight)) / self.scale

    def text(self, text: str, x: float, y: float, size: float, weight: str, color: str) -> None:
        """Text whose line box starts at (x, y)."""
        s = self.scale
        font = self.font(size, weight)
        ascent, descent = font.getmetrics()
        baseline = y * s + (LINE_HEIGHT * size * s + ascent - descent) / 2
        self.draw.text((x * s, baseline), text, font=font, fill=color, anchor="ls")

    def centered(self, text: str, cx: float, y: float, size: float, weight: str, color: str) -> None:
        self.text(text, cx - self.text_width(text, size, weight) / 2, y, size, weight, color)

    def lock(self, cx: float, cy: float, size: float, color: str) -> None:
        """The Material "lock" icon."""
        s = self.scale
        body_w, body_h = 0.62 * size, 0.44 * size
        self.box(cx - body_w / 2, cy - 0.02 * size, body_w, body_h, 0.08 * size, color)
        r = 0.2 * size
        self.draw.arc([(cx - r) * s, (cy - 0.34 * size) * s, (cx + r) * s, (cy + 0.06 * size) * s],
                      180, 360, fill=color, width=max(1, round(0.09 * size * s)))
        for side in (-1, 1):
            x = cx + side * r - (0.09 * size if side > 0 else 0)
            self.box(x, cy - 0.15 * size, 0.09 * size, 0.14 * size, 0, color)

    def help(self, cx: float, cy: float, size: float, color: str, background: str) -> None:
        """The Material "help_outline" icon: a ring with a question mark."""
        r = 0.42 * size
        self.box(cx - r, cy - r, 2 * r, 2 * r, r, color)
        inner = r - 0.09 * size
        self.box(cx - inner, cy - inner, 2 * inner, 2 * inner, inner, background)
        self.centered("?", cx, cy - LINE_HEIGHT * 0.6 * size / 2, 0.6 * size, "Bold", color)

    def restart(self, cx: float, cy: float, size: float, color: str) -> None:
        """The Material "restart_alt" icon: a circular arrow."""
        s, r = self.scale, 0.32 * size
        self.draw.arc([(cx - r) * s, (cy - r + 0.06 * size) * s, (cx + r) * s, (cy + r + 0.06 * size) * s],
                      -60, 250, fill=color, width=max(1, round(0.1 * size * s)))
        tip = (cx - 0.02 * size, cy - r + 0.06 * size)
        self.draw.polygon([((tip[0] + 0.2 * size) * s, (tip[1] - 0.16 * size) * s),
                           ((tip[0] + 0.2 * size) * s, (tip[1] + 0.16 * size) * s),
                           ((tip[0] - 0.06 * size) * s, tip[1] * s)], fill=color)


def wrap(canvas: Canvas, text: str, width: float, size: float, weight: str) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if line and canvas.text_width(candidate, size, weight) > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    return lines + [line]


def render(view, width: float, height: float, scale: float) -> Image.Image:
    """The whole screen: header, final score, level bar, message, grid, game-over button."""
    page = view.page
    canvas = Canvas(width, height, scale, config.COLOR_BG)
    layout = view.layout
    x0 = y0 = page.padding + layout.padding
    content_w = width - 2 * x0
    _draw_header(canvas, view, x0, y0, content_w)

    column = layout.content
    slot = column.controls[-1]
    slot_top = height - y0 - slot.height
    body = view.swipe_area.control.content.content
    board_h = view.board.stack.height + 2 * view.board.frame.padding
    board_top = slot_top - column.spacing - board_h
    status_top = board_top - body.spacing - view.status_box.height
    levels_top = status_top - body.spacing - view.level_bar.blocks[0].height

    banner = view.game_end.banner
    if banner.visible:
        _draw_final_score(canvas, banner, x0 + content_w / 2, levels_top - body.spacing - banner.height)
    _draw_level_bar(canvas, view, width, levels_top)
    _draw_status(canvas, view, x0, content_w, status_top)
    _draw_board(canvas, view, x0 + (content_w - view.board.outer_width) / 2, board_top)
    if view.help_button.control.visible:
        _draw_help_button(canvas, view.help_button.control, x0 + content_w / 2, slot_top + slot.height / 2)
    button = view.game_end.button
    if button.visible:
        left = x0 + (content_w - button.width) / 2  # centered, like the grid above it
        canvas.box(left, slot_top, button.width, button.height, button.border_radius, button.bgcolor)
        label = button.content
        canvas.centered(label.value, left + button.width / 2, slot_top + (button.height - LINE_HEIGHT * label.size) / 2,
                        label.size, "Bold", label.color)
    return canvas.image


def _draw_header(canvas: Canvas, view, x0: float, y0: float, content_w: float) -> None:
    header = view.header
    _, blocks_column = header.control.controls
    top_row = blocks_column.controls[0]
    block_w, block_h = header.blocks[0].width, header.blocks[0].height
    header_h = 2 * block_h + blocks_column.spacing
    # Logo: the mark, then the two-line name, centered on the header's height.
    mark, name = header.logo.controls
    cell = mark.controls[0].controls[0].width
    gap = mark.controls[0].spacing
    mark_h = 3 * cell + 2 * mark.spacing
    mark_top = y0 + (header_h - mark_h) / 2
    for r, row in enumerate(mark.controls):
        for c, tile in enumerate(row.controls):
            canvas.box(x0 + c * (cell + gap), mark_top + r * (cell + mark.spacing), cell, cell,
                       tile.border_radius, tile.bgcolor)
    line = name.controls[0].size * name.controls[0].style.height
    name_top = y0 + (header_h - 2 * line) / 2
    for i, text in enumerate(name.controls):
        canvas.text(text.value, x0 + 3 * cell + 2 * gap + header.logo.spacing,
                    name_top + i * line - (LINE_HEIGHT - text.style.height) * text.size / 2,
                    text.size, "Black", text.color)
    # Blocks: SCORE BEST / LEVEL RESTART, on the right.
    right = x0 + content_w
    for i, block in enumerate(header.blocks):
        col, row = i % 2, i // 2
        x = right - (2 - col) * block_w - (1 - col) * top_row.spacing
        y = y0 + row * (block_h + blocks_column.spacing)
        canvas.box(x, y, block_w, block_h, block.border_radius, block.bgcolor)
        label, value = block.content.controls
        value_h = value.size if not hasattr(value, "value") else LINE_HEIGHT * value.size
        top = y + (block_h - LINE_HEIGHT * label.size - value_h) / 2
        canvas.centered(label.value, x + block_w / 2, top, label.size, "Regular", label.color)
        if hasattr(value, "value"):
            canvas.centered(value.value, x + block_w / 2, top + LINE_HEIGHT * label.size,
                            value.size, "Bold", value.color)
        else:
            canvas.restart(x + block_w / 2, top + LINE_HEIGHT * label.size + value.size / 2,
                           value.size, value.color)


def _draw_level_bar(canvas: Canvas, view, width: float, top: float) -> None:
    blocks = view.level_bar.blocks
    size, spacing = blocks[0].width, view.level_bar.control.spacing
    left = (width - (len(blocks) * size + (len(blocks) - 1) * spacing)) / 2
    for i, block in enumerate(blocks):
        x = left + i * (size + spacing)
        canvas.box(x, top, size, size, block.border_radius, block.bgcolor)
        if block.content is not None:
            canvas.lock(x + size / 2, top + size / 2, block.content.size, block.content.color)


def _draw_status(canvas: Canvas, view, x0: float, content_w: float, top: float) -> None:
    text = view.status_display
    lines = wrap(canvas, text.value, content_w, text.size, "Bold")[: text.max_lines]
    line_h = LINE_HEIGHT * text.size
    first = top + (view.status_box.height - line_h * len(lines)) / 2
    for i, line in enumerate(lines):
        canvas.centered(line, x0 + content_w / 2, first + i * line_h, text.size, "Bold", text.color)


def _draw_help_button(canvas: Canvas, button, cx: float, cy: float) -> None:
    """HOW TO PLAY: a pill with the Material "help_outline" icon and its label."""
    icon, label = button.content.controls
    pad = button.padding
    content_w = icon.size + button.content.spacing + canvas.text_width(label.value, label.size, "Bold")
    w, h = pad.left + content_w + pad.right, pad.top + icon.size + pad.bottom
    left = cx - w / 2
    canvas.box(left, cy - h / 2, w, h, button.border_radius, button.bgcolor)
    canvas.help(left + pad.left + icon.size / 2, cy, icon.size, icon.color, button.bgcolor)
    canvas.text(label.value, left + pad.left + icon.size + button.content.spacing,
                cy - LINE_HEIGHT * label.size / 2, label.size, "Bold", label.color)


def _draw_final_score(canvas: Canvas, box, cx: float, top: float) -> None:
    """The points of this game and GAME OVER under them, centered in their box
    (above its bottom padding: the gap before the level blocks)."""
    column = box.content
    lines = column.controls
    height = sum(LINE_HEIGHT * text.size for text in lines) + (len(lines) - 1) * column.spacing
    y = top + (box.height - box.padding.bottom - height) / 2
    for text in lines:
        canvas.centered(text.value, cx, y, text.size, "Bold", text.color)
        y += LINE_HEIGHT * text.size + column.spacing


def _draw_board(canvas: Canvas, view, left: float, top: float) -> None:
    board = view.board
    frame = board.frame
    canvas.box(left, top, board.outer_width, board.stack.height + 2 * frame.padding,
               frame.border_radius, frame.bgcolor)
    for tile in board.stack.controls:
        size = tile.width * (tile.scale if tile.scale is not None else 1)
        offset = (tile.width - size) / 2
        canvas.box(left + frame.padding + tile.left + offset, top + frame.padding + tile.top + offset,
                   size, size, tile.border_radius, tile.bgcolor)
