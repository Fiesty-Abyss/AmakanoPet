"""Original procedural placeholder mascot "糯糯 (Nuonuo)".

A round mochi-like creature drawn entirely with QPainter primitives. It is an
original design for this project and intentionally does not resemble any
character or logo from the Amakano series or its publisher.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QRadialGradient

from app.theme import Theme


def _round_pen(color: QColor | str, width: float) -> QPen:
    pen = QPen(QColor(color), width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    return pen


def _heart_path(cx: float, cy: float, size: float) -> QPainterPath:
    s = size
    path = QPainterPath(QPointF(cx, cy + s * 0.35))
    path.cubicTo(cx - s * 0.9, cy - s * 0.25, cx - s * 0.45, cy - s * 0.95, cx, cy - s * 0.4)
    path.cubicTo(cx + s * 0.45, cy - s * 0.95, cx + s * 0.9, cy - s * 0.25, cx, cy + s * 0.35)
    return path


def _season_mark(painter: QPainter, theme: Theme, cx: float, cy: float, r: float) -> None:
    painter.save()
    accent = QColor(theme.accent)
    if theme.key == "winter":  # simple six-line snowflake
        painter.setPen(_round_pen("#FFFFFF", max(1.5, r * 0.18)))
        for i in range(3):
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(60 * i)
            painter.drawLine(QPointF(-r, 0), QPointF(r, 0))
            painter.restore()
    elif theme.key == "autumn":  # rounded leaf
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(accent)
        leaf = QPainterPath(QPointF(cx, cy - r))
        leaf.quadTo(cx + r, cy - r * 0.2, cx, cy + r)
        leaf.quadTo(cx - r, cy - r * 0.2, cx, cy - r)
        painter.drawPath(leaf)
    elif theme.key == "summer":  # five-petal flower
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#FFFFFF"))
        for i in range(5):
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(72 * i)
            painter.drawEllipse(QRectF(-r * 0.32, -r * 1.05, r * 0.64, r * 0.8))
            painter.restore()
        painter.setBrush(QColor("#F9C126"))
        painter.drawEllipse(QPointF(cx, cy), r * 0.32, r * 0.32)
    else:  # sweet: small heart
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawPath(_heart_path(cx, cy + r * 0.1, r * 1.1))
    painter.restore()


def paint_mascot(painter: QPainter, rect: QRectF, theme: Theme, eye_openness: float = 1.0) -> None:
    """Draw the mascot fitted inside ``rect`` (anchored to the bottom centre)."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    w = min(rect.width(), rect.height() * 0.95)
    cx = rect.center().x()
    bottom = rect.bottom() - w * 0.04
    body = QRectF(cx - w * 0.44, bottom - w * 0.86, w * 0.88, w * 0.86)

    # soft ground shadow
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(75, 40, 20, 40))
    painter.drawEllipse(QRectF(cx - w * 0.36, bottom - w * 0.05, w * 0.72, w * 0.09))

    # body: squashed mochi with a radial gradient
    grad = QRadialGradient(body.center().x() - w * 0.12, body.top() + w * 0.2, w * 0.7)
    grad.setColorAt(0.0, QColor("#FFFFFF"))
    grad.setColorAt(0.75, QColor("#FFF6EC"))
    grad.setColorAt(1.0, QColor("#F3E2D3"))
    path = QPainterPath()
    path.moveTo(body.left(), body.bottom() - w * 0.12)
    path.cubicTo(body.left(), body.top() - w * 0.02, body.right(), body.top() - w * 0.02,
                 body.right(), body.bottom() - w * 0.12)
    path.quadTo(body.right(), body.bottom(), body.center().x(), body.bottom())
    path.quadTo(body.left(), body.bottom(), body.left(), body.bottom() - w * 0.12)
    painter.setBrush(QBrush(grad))
    painter.setPen(QPen(QColor(theme.ink).lighter(260), max(1.0, w * 0.008)))
    painter.drawPath(path)

    # heart-shaped tuft on top
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(theme.primary))
    painter.drawPath(_heart_path(cx + w * 0.02, body.top() + w * 0.12, w * 0.1))

    # eyes
    eye_y = body.top() + body.height() * 0.46
    eye_dx = w * 0.15
    eye_w, eye_h = w * 0.07, w * 0.095
    ink = QColor(theme.ink)
    for sign in (-1, 1):
        ex = cx + sign * eye_dx
        if eye_openness > 0.35:
            h = eye_h * max(0.25, eye_openness)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(ink)
            painter.drawEllipse(QRectF(ex - eye_w / 2, eye_y - h / 2, eye_w, h))
            painter.setBrush(QColor("#FFFFFF"))
            hl = eye_w * 0.18
            painter.drawEllipse(QPointF(ex - hl, eye_y - h * 0.22), hl, hl)
        else:  # closed: gentle arc
            painter.setPen(_round_pen(ink, max(1.5, w * 0.014)))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            arc = QRectF(ex - eye_w * 0.7, eye_y - eye_h * 0.35, eye_w * 1.4, eye_h * 0.7)
            painter.drawArc(arc, 200 * 16, 140 * 16)

    # blush
    painter.setPen(Qt.PenStyle.NoPen)
    blush = QColor(theme.primary)
    blush.setAlpha(80)
    painter.setBrush(blush)
    for sign in (-1, 1):
        painter.drawEllipse(QPointF(cx + sign * w * 0.25, eye_y + w * 0.075), w * 0.06, w * 0.032)

    # mouth "ω"
    painter.setPen(_round_pen(ink, max(1.2, w * 0.01)))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    my = eye_y + w * 0.07
    mw = w * 0.035
    painter.drawArc(QRectF(cx - mw * 2, my - mw * 0.6, mw * 2, mw * 1.4), 180 * 16, 180 * 16)
    painter.drawArc(QRectF(cx, my - mw * 0.6, mw * 2, mw * 1.4), 180 * 16, 180 * 16)

    # scarf band in the theme colour + seasonal mark
    scarf_y = body.bottom() - body.height() * 0.26
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(theme.primary))
    scarf = QPainterPath()
    scarf.moveTo(body.left() + w * 0.06, scarf_y)
    scarf.quadTo(cx, scarf_y + w * 0.07, body.right() - w * 0.06, scarf_y)
    scarf.lineTo(body.right() - w * 0.07, scarf_y + w * 0.06)
    scarf.quadTo(cx, scarf_y + w * 0.13, body.left() + w * 0.07, scarf_y + w * 0.06)
    scarf.closeSubpath()
    painter.drawPath(scarf)
    tail = QPainterPath(QPointF(cx + w * 0.16, scarf_y + w * 0.08))
    tail.lineTo(cx + w * 0.24, scarf_y + w * 0.2)
    tail.lineTo(cx + w * 0.11, scarf_y + w * 0.19)
    tail.closeSubpath()
    painter.drawPath(tail)
    _season_mark(painter, theme, cx - w * 0.17, scarf_y + w * 0.06, w * 0.045)
    painter.restore()
