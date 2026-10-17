from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QImage, QPainter

from app.renderers import ImageSource, MascotSource, SpriteRenderer
from app.theme import THEMES
from tests.conftest import write_png


def render(renderer: SpriteRenderer, t: float = 0.3) -> QImage:
    image = QImage(280, 360, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    renderer.paint(painter, QRectF(0, 0, 280, 360), t=t)
    painter.end()
    return image


def opaque_pixels(image: QImage) -> int:
    return sum(
        1 for y in range(0, image.height(), 6) for x in range(0, image.width(), 6)
        if image.pixelColor(x, y).alpha() > 0
    )


def test_mascot_paints_in_every_theme(qapp):
    for theme in THEMES.values():
        image = render(SpriteRenderer(MascotSource(), theme))
        assert opaque_pixels(image) > 200


def test_image_source_uses_blink_frame(qapp, tmp_path):
    idle = write_png(tmp_path / "idle.png", "#FF0000")
    blink = write_png(tmp_path / "blink.png", "#0000FF")
    source = ImageSource(idle, [blink])
    assert source.has_blink
    renderer = SpriteRenderer(source)
    renderer.set_animated(False)
    centre = render(renderer).pixelColor(140, 300)
    assert centre.red() > 200 and centre.blue() < 50
    # force the closed-eye frame
    image = QImage(280, 360, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    source.paint(painter, QRectF(0, 0, 280, 360), 0.0, THEMES["sweet"])
    painter.end()
    assert image.pixelColor(140, 300).blue() > 200


def test_image_source_rejects_unreadable(tmp_path):
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"not an image")
    try:
        ImageSource(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_hop_moves_the_sprite(qapp):
    renderer = SpriteRenderer()
    before = render(renderer, t=0.0)
    renderer._hop_started = 0.0
    during = render(renderer, t=0.2)
    assert before != during
