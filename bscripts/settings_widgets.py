from PyQt5                  import QtCore, QtGui, QtWidgets
from bscripts.preset_colors import *
from bscripts.tricks        import tech as t
import os
import random

class GOD:
    def __init__(self,
                 place=None,
                 main=None,
                 type=None,
                 signal=False,
                 reset=True,
                 parent=None,
                 load=False,
                 inherit_type=False,
                 *args, **kwargs
                 ):

        self.activated = False
        self.main = main or False
        self.parent = parent or place or False
        self.determine_type(inherit_type, place, type)
        self.setup_signal(signal, reset)
        self.load_settings(load)

    def load_settings(self, load):
        if not load or not self.type:
            return

        rv = t.config(self.type)
        if rv == True:
            self.activation_toggle(force=True, save=False)

    def setup_signal(self, signal, reset):
        if signal:
            if signal == True:
                self.signal = t.signals(self.type, reset=reset)
            elif type(signal) != str:
                self.signal = signal
            else:
                self.signal = t.signals(signal, reset=reset)
        else:
            self.signal = False

    def determine_type(self, inherit_type, place, type):
        if type:
            self.type = type
        elif inherit_type and place and 'type' in dir(place) and place.type not in ['main']: # blacklist
            self.type = place.type
        else:
            self.type = '_' + t.md5_hash_string()

    def save(self, type=None, data=None):
        if data:
            if type:
                t.save_config(type, data)
            else:
                t.save_config(self.type, data)

    def activation_toggle(self, force=None, save=True):
        if force == False:
            self.activated = False
        elif force == True:
            self.activated = True
        else:
            if self.activated:
                self.activated = False
            else:
                self.activated = True

        if save:
            t.save_config(self.type, self.activated)

class DragDroper(GOD):
    def __init__(self, drops=False, mouse=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(drops)
        self.setMouseTracking(mouse)

    def dragEnterEvent(self, a0: QtGui.QDragEnterEvent) -> None:
        if a0.mimeData().hasUrls() and a0.mimeData().urls() and len(a0.mimeData().urls()) == 1:
            file = a0.mimeData().urls()[0]
            file = file.path()
            if os.path.isfile(file):
                a0.accept()
        return

    def dropEvent(self, a0: QtGui.QDropEvent) -> None:
        if a0.mimeData().hasUrls() and a0.mimeData().urls()[0].isLocalFile():

            if len(a0.mimeData().urls()) == 1:
                a0.accept()

                files = [x.path() for x in a0.mimeData().urls()]
                self.filesdropped(files, a0)

class GODLabel(QtWidgets.QLabel, GOD):
    def __init__(self, center=False, qframebox=False, linewidth=1, *args, **kwargs):
        super().__init__(kwargs['place'], *args, **kwargs)

        if qframebox:
            self.setFrameShape(QtWidgets.QFrame.Box)
            self.setLineWidth(linewidth)

        self.old_position = False
        if center:
            self.setAlignment(QtCore.Qt.AlignVCenter|QtCore.Qt.AlignHCenter)
        self.show()

    def filesdropped(self, files):
        pass

class GODLE(QtWidgets.QLineEdit, GOD):
    def __init__(self, *args, **kwargs):
        super().__init__(kwargs['place'], *args, **kwargs)
        self.textChanged.connect(self.text_changed)
        self.show()

    def text_changed(self):
        text = self.text().strip()
        if not text:
            return

class GODLEPath(GODLE):
    def __init__(self, autoinit=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if autoinit:
            self.set_saved_path()

    def filesdropped(self, files):
        if not files:
            return

        self.setText(files[0])

    def text_changed(self):
        text = self.text().strip()

        if text and os.path.exists(text):
            self.save(data=text)
            if not self.activated:
                t.style(self, color='white')
                self.activation_toggle(force=True, save=False) # already saved
                if self.signal:
                    self.signal.activated.emit()
        else:
            if self.activated:
                t.style(self, color='gray')
                self.activation_toggle(force=False, save=False)
                if self.signal:
                    self.signal.deactivated.emit()

    def set_saved_path(self):
        rv = t.config(self.type)
        if rv:
            self.setText(rv)
            self.activation_toggle(force=True, save=False)
            self.signal.activated.emit()

class GLOBALHighLight(DragDroper, GOD):
    def __init__(self,
                 signal=True,
                 reset=False,
                 activated_on=None,
                 activated_off=None,
                 deactivated_on=None,
                 deactivated_off=None,
                 *args, **kwargs
                 ):

        if signal == True:
            signal = '_global'

        super().__init__(signal=signal, reset=reset, *args, **kwargs)
        self.signal.highlight.connect(self.highlight_toggle)

        self.activated_on = activated_on or dict(background=HIGH_GREEN)
        self.activated_off = activated_off or dict(background=ACTIVE_GREEN)
        self.deactivated_on = deactivated_on or dict(background=HIGH_RED)
        self.deactivated_off = deactivated_off or dict(background=DEACTIVE_RED)
        self.swap_presets_backup = {}

    def swap_preset(self, variable, new_value=None, restore=False):
        if variable not in self.swap_presets_backup: # makes a backup
            self.swap_presets_backup[variable] = getattr(self, variable)

        if new_value and new_value != getattr(self, variable):
            setattr(self, variable, new_value)

        if restore and getattr(self, variable) != self.swap_presets_backup[variable]:
            setattr(self, variable, self.swap_presets_backup[variable])

    def highlight_toggle(self, string=None, force=None):
        if force:
            string = self.type
        elif force == False:
            string = '_' + t.md5_hash_string()

        if string == self.type:
            if self.activated:
                t.style(self, **self.activated_on)
            else:
                t.style(self, **self.deactivated_on)
        else:
            if self.activated:
                t.style(self, **self.activated_off)
            else:
                t.style(self, **self.deactivated_off)

    def mouseMoveEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.signal.highlight.emit(self.type)

class Canvas(GODLabel):
    def __init__(self,
                 edge,
                 width,
                 height,
                 button_width=0,
                 canvas_border=0,
                 canvas_background='transparent',
                 *args, **kwargs
                 ):
        super().__init__(*args, **kwargs)
        self.edge = edge
        self.canvas_border = canvas_border
        self.button_width = button_width
        t.pos(self, size=[height, width])
        t.style(self, background=canvas_background)

    def build_lineedit(self, immutable=False, **kwargs):
        self.lineedit = self.LineEdit(place=self, main=self.main, parent=self, **kwargs)
        if immutable:
            self.lineedit.setReadOnly(True)

    def build_label(self, **kwargs):
        self.label = self.Label(place=self, main=self.main, parent=self, **kwargs)

    def build_button(self, **kwargs):
        self.button = self.Button(place=self, main=self.main, parent=self, **kwargs)

    def build_tiplabel(self, text, fontsize=None, width=None):
        if not 'lineedit' in dir(self):
            return

        self.tiplabel = t.pos(new=self.lineedit, inside=self.lineedit)
        self.tiplabel.width_size = width
        self.tiplabel.setText(text)

        if fontsize:
            t.style(self.tiplabel, font=fontsize)
            self.tiplabel.font_size = fontsize
        else:
            self.tiplabel.font_size = t.correct_broken_font_size(self.tiplabel)

        t.style(self.tiplabel, color=TIPTEXT, background='transparent')

    def button_and_lineedit_reactions(self):
        if not 'button' in dir(self) or not 'lineedit' in dir(self):
            return

        if not self.lineedit.signal:
            return

        self.lineedit.signal.activated.connect(
            lambda: t.style(self.button, background=ACTIVE_GREEN))

        self.lineedit.signal.activated.connect(
            lambda: t.style(self.button.activation_toggle(force=True, save=False)))

        self.lineedit.signal.deactivated.connect(
            lambda: t.style(self.button, background=DEACTIVE_RED))

        self.lineedit.signal.deactivated.connect(
            lambda: t.style(self.button.activation_toggle(force=False, save=False)))

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        if self.width() < 100:
            return

        self.set_positions()

    def set_positions(self):
        """
        self.button_width locks button at that width, else it will be symetric square from self.height()
        :return:
        """
        if 'canvas_border' in dir(self):
            cb = self.canvas_border
        else:
            cb = 0

        if 'button' in dir(self):
            hw = self.height() - (cb * 2)

            if self.button_width:
                bw = self.button_width
            else:
                bw = hw
            t.pos(self.button, height=hw, width=bw, left=cb, top=cb)

        if 'lineedit' in dir(self):
            if 'button' in dir(self):
                t.pos(self.lineedit, after=self.button, x_margin=self.edge, height=self.height() - (cb * 2), top=cb)
                t.pos(self.lineedit, left=self.lineedit, right=self.width() - cb - 1)
            else:
                t.pos(self.lineedit, inside=self, margin=cb)

            if 'tiplabel' in dir(self):
                if self.tiplabel.width_size:
                    t.pos(self.tiplabel, width=self.tiplabel.width_size)

                t.pos(self.tiplabel, height=self.lineedit.height() - (cb * 2), right=self.lineedit.width() - cb, x_margin=self.edge)

        if 'label' in dir(self):
            if 'button' in dir(self):
                t.pos(self.label, inside=self, left=dict(right=self.button), x_margin=self.edge, right=self.width() - cb)
                t.pos(self.label, height=self.label, sub=cb * 2, move=[0,cb])
            else:
                t.pos(self.label, inside=self, margin=cb)

    class LineEdit(DragDroper, GODLEPath):
        def __init__(self,
                    activated_on=None,
                    activated_off=None,
                    deactivated_on=None,
                    deactivated_off=None,
                    lineedit_foreground = 'white',
                    lineedit_background = 'black',
                    *args, **kwargs
                    ):
            super().__init__(
                             activated_on=activated_on or dict(color=TEXT_ON),
                             activated_off=activated_off or dict(color=TEXT_WHITE),
                             deactivated_on=deactivated_on or dict(color=TEXT_ON),
                             deactivated_off=deactivated_off or dict(color=TEXT_OFF),
                             *args, **kwargs)

            t.style(self, background=lineedit_background, color=lineedit_foreground, font=14)

    class Label(GODLabel, GLOBALHighLight):
        def __init__(self,
                        activated_on=None,
                        activated_off=None,
                        deactivated_on=None,
                        deactivated_off=None,
                        label_background='white',
                        label_foreground='black',
                        *args, **kwargs
                    ):
            super().__init__(
                             activated_on=activated_on or dict(color=TEXT_ON),
                             activated_off=activated_off or dict(color=TEXT_WHITE),
                             deactivated_on=deactivated_on or dict(color=TEXT_ON),
                             deactivated_off=deactivated_off or dict(color=TEXT_OFF),
                             *args, **kwargs)

            t.style(self, background=label_background, color=label_foreground, font=14)

    class Button(GODLabel, GLOBALHighLight):
        def __init__(self, *args, **kwargs):
            super().__init__(
                deactivated_on=dict(background=HIGH_RED, color=DARK_BACK),
                deactivated_off=dict(background=DEACTIVE_RED, color=BLACK),
                activated_on=dict(background=HIGH_GREEN, color=DARK_BACK),
                activated_off=dict(background=ACTIVE_GREEN, color=BLACK),
                *args, **kwargs)
            self.setFrameShape(QtWidgets.QFrame.Box)
            self.setLineWidth(self.parent.edge)

def create_indikator(
                        place,
                        edge=1,
                        button=False,
                        lineedit=False,
                        label=False,
                        tiplabel=None,
                        height=30,
                        width=300,
                        tipfont=None,
                        tipwidth=None,
                        tooltip=None,
                        button_listen=False,
                        type=None,
                        post_init_signal=True,
                        Special=None,
                        *args, **kwargs
                    ):

    if Special:
        canvas = Special(place=place, edge=edge, width=width, height=height, type=type, *args, **kwargs)
    else:
        canvas = Canvas(place=place, edge=edge, width=width, height=height, type=type, *args, **kwargs)

    if lineedit:
        canvas.build_lineedit(**kwargs)
    if label:
        canvas.build_label(**kwargs)
    if button:
        canvas.build_button(**kwargs)
    if tiplabel:
        canvas.build_tiplabel(text=tiplabel, fontsize=tipfont, width=tipwidth)
    if button_listen:
        canvas.button_and_lineedit_reactions()
    if tooltip:
        canvas.setToolTip(tooltip)
        t.style(canvas, tooltip=True, background='black', color='white', font=14)

    if post_init_signal and lineedit and canvas.lineedit.activated:
        canvas.lineedit.signal.activated.emit()

    return canvas


class MovableScrollWidget(GODLabel):
    def __init__(self, *args, **kwargs):

        self.title = False
        self.crown = False
        self.old_position = False
        self.widgets = []

        super().__init__(*args, **kwargs)

        self.make_toolplate()
        self.make_backplate()
        self.make_scrollarea()

        self.show()

        t.style(self, background=TRANSPARENT)
        t.style(self.scrollarea, background=TRANSPARENT)
        t.style(self.backplate, background=TRANSPARENT)

    def make_toolplate(self):
        self.toolplate = QtWidgets.QLabel(self)
        self.toolplate.widgets = []
        t.style(self.toolplate, background=TRANSPARENT)
        self.toolplate.show()

    def make_backplate(self):
        self.backplate = QtWidgets.QWidget(self)
        t.style(self.backplate, background=TRANSPARENT)
        t.pos(self.backplate, height=0)
        self.backplate.show()

    def make_scrollarea(self):
        self.scrollarea = QtWidgets.QScrollArea(self)
        self.scrollarea.setWidget(self.backplate)
        self.scrollarea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scrollarea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scrollarea.setLineWidth(0)
        self.scrollarea.setFrameShape(QtWidgets.QScrollArea.Box)
        self.scrollarea.show()

    def drag_widget(self, ev):
        if not self.old_position:
            self.old_position = ev.globalPos()

        delta = QtCore.QPoint(ev.globalPos() - self.old_position)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.old_position = ev.globalPos()

        if self.crown:
            self.position_crown()

    def position_crown(self):
        t.pos(self.crown, above=self, move=[self.crown.random, 0])

    def raise_us(self):
        self.raise_()
        if self.crown:
            self.crown.raise_()

    class TITLE(GODLabel, DragDroper):
        def __init__(self, text, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            self.setText(text)
            self.setLineWidth(1)
            self.setFrameShape(QtWidgets.QFrame.Box)
            self.freeze = False
            t.style(self, background=TOOLTIP_DRK_BG, color=TITLE_WHITE)
            self.show()

        def mouseMoveEvent(self, ev: QtGui.QMouseEvent) -> None:
            self.parent.drag_widget(ev)

        def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
            if ev.button() == 2 and self.parent.signal:
                self.parent.signal.killswitch.emit()

        def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
            self.parent.old_position = ev.globalPos()
            if ev.button() == 1:
                self.parent.raise_us()

    def make_title(self, text, height=28, width=500, font=14):
        self.title = self.TITLE(place=self.toolplate, text=text, parent=self, main=self.main, drops=True)
        self.title.filesdropped = self.filesdropped
        self.title.setText(text)
        self.toolplate.widgets.append(self.title)
        t.style(self.title, font=font)

        w = t.shrink_label_to_text(self.title, no_change=True, x_margin=12)
        if w < width * 0.65:
            w = width * 0.65

        t.pos(self.title, height=height)
        t.pos(self, width=w)

    def load_crown(self):
        pixmap = t.config(self.url, image=True)
        if pixmap:
            path = t.tmp_file(self.url, hash=True, reuse=True)
            if not os.path.exists(path) or not os.path.getsize(path):
                with open(path, 'wb') as f:
                    f.write(pixmap)

            factor = t.config(self.url)
            if factor:
                self.set_this_add_crown(path, width_percentage=factor)
            else:
                self.set_this_add_crown(path)

            self.position_crown()

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        self.set_positions()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if self.crown:
            self.crown.close()

    class CROWN(QtWidgets.QLabel):
        def __init__(self, place, path, width, partner):
            super().__init__(place)
            self.partner = partner
            pixmap = QtCore.QPixmap(path).scaledToWidth(width, QtCore.Qt.SmoothTransformation)
            playspace = partner.width() - width
            self.random = random.randint(0, playspace)
            t.pos(self, size=pixmap)
            t.style(self, background=TRANSPARENT)
            self.setPixmap(pixmap)
            self.show()

        def mouseMoveEvent(self, ev: QtGui.QMouseEvent) -> None:
            self.partner.drag_widget(ev)

        def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
            self.partner.old_position = ev.globalPos()
            if ev.button() == 1:
                self.partner.raise_us()

        def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
            self.partner.title.mouseReleaseEvent(ev)

    def set_this_add_crown(self, path, width_percentage=0.5):
        if not os.path.exists(path):
            return

        width = int(self.width() * width_percentage)
        self.crown = self.CROWN(self.main.scrollcanvas_main, path, width, partner=self)

    def filesdropped(self, filelist, ev, heightfactor=False):
        loc = t.separate_file_from_folder(filelist[0])
        if loc.ext.lower() not in {'webp', 'jpeg', 'jpg', 'png', 'bmp'}:
            return

        t.tmp_file(self.url, hash=True, delete=True)
        blob = t.make_image_into_blob(image_path=loc.full_path, width=self.title.width())
        t.save_config(self.url, blob, image=True)

        if not heightfactor:
            heightfactor = ev.pos().x() / self.width()

        if self.crown:
            self.crown.close()
            self.crown = False

        self.set_this_add_crown(loc.full_path, heightfactor)
        self.position_crown()

        t.save_config(self.url, heightfactor)

    def set_positions(self, y=0):
        if not self.title:
            return

        if not self.title.freeze:
            t.pos(self.title, width=self)

        height = self.toolplate.widgets[-1].geometry().bottom() +1
        t.pos(self.toolplate, height=height, width=self)
        t.pos(self.backplate, below=self.toolplate, width=self, y_margin=y)
        t.pos(self.scrollarea, below=self.toolplate, width=self, y_margin=y)

    def expand_me(self):
        maxheight = self.main.height() * 0.7
        if not self.widgets:
            childspace = 0
        else:
            childspace = self.widgets[-1].geometry().bottom() + 1

        t.pos(self.backplate, height=childspace)
        add = self.scrollarea.lineWidth() * 4

        if self.backplate.geometry().bottom() > maxheight:
            t.pos(self, height=maxheight)
            t.pos(self.scrollarea, height=maxheight - self.toolplate.height())
        else:
            t.pos(self, height=self.toolplate, add=childspace + add)
            t.pos(self.scrollarea, coat=self.backplate)
            t.pos(self.scrollarea, height=self.scrollarea, add=add)
