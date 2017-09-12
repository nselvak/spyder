# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
"""
This module contains the Scroll Flag panel
"""

from qtpy.QtCore import QSize, Qt, QRect
from qtpy.QtGui import QPainter, QBrush, QColor, QCursor
from qtpy.QtWidgets import (QStyle, QStyleOptionSlider, QApplication)

from spyder.api.panel import Panel


class ScrollFlagArea(Panel):
    """Source code editor's scroll flag area"""
    WIDTH = 12
    FLAGS_DX = 4
    FLAGS_DY = 2

    def __init__(self, editor):
        Panel.__init__(self, editor)
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.scrollable = True
        self.setMouseTracking(True)

        editor.focus_changed.connect(self.update)
        editor.key_pressed.connect(self.keyPressEvent)
        editor.key_released.connect(self.keyReleaseEvent)
        editor.alt_left_mouse_pressed.connect(self.mousePressEvent)
        editor.alt_mouse_moved_over.connect(self.mouseMoveEvent)
        editor.flags_changed.connect(self.update)

    @property
    def slider(self):
        """This property holds whether the vertical scrollbar is visible."""
        return self.editor.verticalScrollBar().isVisible()

    @property
    def offset(self):
        """This property holds the vertical offset of the scroll flag area
        relative to the top of the text editor."""
        vsb = self.editor.verticalScrollBar()
        style = vsb.style()
        opt = QStyleOptionSlider()
        vsb.initStyleOption(opt)

        # Get the area in which the slider handle may move.
        groove_rect = style.subControlRect(
                QStyle.CC_ScrollBar, opt, QStyle.SC_ScrollBarGroove, self)

        return groove_rect.y()

    def sizeHint(self):
        """Override Qt method"""
        return QSize(self.WIDTH, 0)

    def paintEvent(self, event):
        """
        Override Qt method.
        Painting the scroll flag area
        """
        make_flag = self.make_flag_qrect

        # Fill the whole painting area
        painter = QPainter(self)
        painter.fillRect(event.rect(), self.editor.sideareas_color)

        # Paint warnings and todos
        block = self.editor.document().firstBlock()
        for line_number in range(self.editor.document().blockCount()+1):
            data = block.userData()
            if data:
                if data.code_analysis:
                    # Paint the warnings
                    color = self.editor.warning_color
                    for _message, error in data.code_analysis:
                        if error:
                            color = self.editor.error_color
                            break
                    self.set_painter(painter, color)
                    painter.drawRect(make_flag(line_number))
                if data.todo:
                    # Paint the todos
                    self.set_painter(painter, self.editor.todo_color)
                    painter.drawRect(make_flag(line_number))
                if data.breakpoint:
                    # Paint the breakpoints
                    self.set_painter(painter, self.editor.breakpoint_color)
                    painter.drawRect(make_flag(line_number))
            block = block.next()

        # Paint the occurrences
        if self.editor.occurrences:
            self.set_painter(painter, self.editor.occurrence_color)
            for line_number in self.editor.occurrences:
                painter.drawRect(make_flag(line_number))

        # Paint the found results
        if self.editor.found_results:
            self.set_painter(painter, self.editor.found_results_color)
            for line_number in self.editor.found_results:
                painter.drawRect(make_flag(line_number))

        # Paint the slider range
        alt = QApplication.queryKeyboardModifiers() & Qt.AltModifier
        cursor_pos = self.mapFromGlobal(QCursor().pos())
        if ((self.rect().contains(cursor_pos) or alt) and self.slider):
            pen_color = QColor(Qt.gray)
            pen_color.setAlphaF(.85)
            painter.setPen(pen_color)
            brush_color = QColor(Qt.gray)
            brush_color.setAlphaF(.5)
            painter.setBrush(QBrush(brush_color))
            painter.drawRect(self.make_slider_range(cursor_pos))

    def enterEvent(self, event):
        """Override Qt method"""
        self.update()

    def leaveEvent(self, event):
        """Override Qt method"""
        self.update()

    def mouseMoveEvent(self, event):
        """Override Qt method"""
        self.update()

    def mousePressEvent(self, event):
        """Override Qt method"""
        vsb = self.editor.verticalScrollBar()
        value = self.position_to_value(event.pos().y())
        vsb.setValue(value-vsb.pageStep()/2)

    def keyReleaseEvent(self, event):
        """Override Qt method."""
        if event.key() == Qt.Key_Alt:
            self.update()

    def keyPressEvent(self, event):
        """Override Qt method"""
        if event.key() == Qt.Key_Alt:
            self.update()

    def get_scrollbar_position_height(self):
        """Return the pixel span height of the scrollbar area in which
        the slider handle may move"""
        vsb = self.editor.verticalScrollBar()
        style = vsb.style()
        opt = QStyleOptionSlider()
        vsb.initStyleOption(opt)

        # Get the area in which the slider handle may move.
        groove_rect = style.subControlRect(
                QStyle.CC_ScrollBar, opt, QStyle.SC_ScrollBarGroove, self)

        return float(groove_rect.height())

    def get_scrollbar_value_height(self):
        """Return the value span height of the scrollbar"""
        vsb = self.editor.verticalScrollBar()
        return vsb.maximum()-vsb.minimum()+vsb.pageStep()

    def get_scale_factor(self):
        """Return scrollbar's scale factor:
        ratio between pixel span height and value span height"""
        return (self.get_scrollbar_position_height() /
                self.get_scrollbar_value_height())

    def value_to_position(self, y):
        """Convert value to position in pixels"""
        vsb = self.editor.verticalScrollBar()
        return (y-vsb.minimum())*self.get_scale_factor()+self.offset

    def position_to_value(self, y):
        """Convert position in pixels to value"""
        vsb = self.editor.verticalScrollBar()
        return vsb.minimum()+max([0, (y-self.offset)/self.get_scale_factor()])

    def make_flag_qrect(self, value):
        """Make flag QRect"""
        if self.slider:
            position = self.value_to_position(value+0.5)
            # The 0.5 offset is used to align the flags with the center of
            # their corresponding text edit block before scaling.

            return QRect(self.FLAGS_DX/2, position-self.FLAGS_DY/2,
                         self.WIDTH-self.FLAGS_DX, self.FLAGS_DY)
        else:
            # When the vertical scrollbar is not visible, the flags are
            # vertically aligned with the center of their corresponding
            # text block with no scaling.
            block = self.editor.document().findBlockByLineNumber(value)
            top = self.editor.blockBoundingGeometry(block).translated(
                      self.editor.contentOffset()).top()
            bottom = top + self.editor.blockBoundingRect(block).height()
            middle = (top + bottom)/2

            return QRect(self.FLAGS_DX/2, middle-self.FLAGS_DY/2,
                         self.WIDTH-self.FLAGS_DX, self.FLAGS_DY)

    def make_slider_range(self, cursor_pos):
        """Make slider range QRect"""
        # The slider range indicator position follows the mouse vertical
        # position while its height corresponds to the part of the file that
        # is currently visible on screen.

        vsb = self.editor.verticalScrollBar()
        groove_height = self.get_scrollbar_position_height()
        slider_height = self.value_to_position(vsb.pageStep())

        # Calcul the minimum and maximum y-value to constraint the slider
        # range indicator position to the height span of the scrollbar area
        # where the slider may move.
        min_ypos = self.offset
        max_ypos = groove_height + self.offset - slider_height

        # Determine the bounded y-position of the slider rect.
        slider_y = max(min_ypos, min(max_ypos, cursor_pos.y()-slider_height/2))

        return QRect(1, slider_y, self.WIDTH-2, slider_height)

    def wheelEvent(self, event):
        """Override Qt method"""
        self.editor.wheelEvent(event)

    def set_painter(self, painter, light_color):
        """Set scroll flag area painter pen and brush colors"""
        painter.setPen(QColor(light_color).darker(120))
        painter.setBrush(QBrush(QColor(light_color)))

    def set_enabled(self, state):
        """Toggle scroll flag area visibility"""
        self.enabled = state
        self.setVisible(state)
