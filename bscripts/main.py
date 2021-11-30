from PyQt5                     import QtCore, QtGui, QtWidgets
from PyQt5.QtCore              import Qt
from PyQt5.QtGui               import QKeySequence
from PyQt5.QtWidgets           import QShortcut
from bscripts.cover_widget     import CoverWidget
from bscripts.database_stuff   import DB, sqlite
from bscripts.imdb_database    import RefreshImdb
from bscripts.preset_colors    import *
from bscripts.settings_widgets import Canvas, GLOBALHighLight, GODLE, GODLabel
from bscripts.settings_widgets import create_indikator
from bscripts.tricks           import tech as t
from functools                 import partial
import datetime
import json
import math
import os
import requests
import screeninfo
import subprocess

class MainClaw(QtWidgets.QMainWindow):

    def __init__(self):
        self.batcher = False
        self.update_db_button = False
        self.category_widgets = []
        super(MainClaw, self).__init__()
        t.style(self, name='main')
        self.setWindowTitle(os.environ['PROGRAM_NAME'] + ' ' + os.environ['VERSION'])
        self.token, self.apikey = t.config('token'), t.config('apikey')
        self.children = []
        self.draw_que = []

        if self.has_stored_login_and_password():
            self.check_credentials()

        self.show()
        self.position_mainwindow()
        self.draw_more_shortcut = QShortcut(QKeySequence(Qt.Key_Space), self)
        self.draw_more_shortcut.activated.connect(self.draw_results)
        t.start_thread(dummy=True, slave_args=0.25, master_fn=self.post_init)

    def setup_gui(self):
        """ creates scroll area """
        self.centralwidget = QtWidgets.QWidget(self)

        self._gridlayout = QtWidgets.QGridLayout(self.centralwidget)
        self._gridlayout.setContentsMargins(0, 32, 0, 0)
        self._gridlayout.setSpacing(0)

        self.back = QtWidgets.QFrame(self.centralwidget)
        self.back.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.back.setFrameShadow(QtWidgets.QFrame.Plain)
        self.back.setLineWidth(0)

        self.grid_layout = QtWidgets.QGridLayout(self.back)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(0)

        self.scroll_area = QtWidgets.QScrollArea(self.back)

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.scroll_area.sizePolicy().hasHeightForWidth())

        self.scroll_area.setSizePolicy(sizePolicy)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll_area.setFrameShadow(QtWidgets.QFrame.Plain)
        self.scroll_area.setLineWidth(0)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.scroll_area.setWidgetResizable(True)

        self.scrollcanvas_main = QtWidgets.QWidget()

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.scrollcanvas_main.sizePolicy().hasHeightForWidth())

        self.scrollcanvas_main.setSizePolicy(sizePolicy)

        self.__gridlayout = QtWidgets.QGridLayout(self.scrollcanvas_main)
        self.__gridlayout.setContentsMargins(0, 0, 0, 0)
        self.__gridlayout.setSpacing(0)

        self.scroll_area.setWidget(self.scrollcanvas_main)

        self.grid_layout.addWidget(self.scroll_area, 0, 0, 1, 1)

        self._gridlayout.addWidget(self.back, 0, 0, 1, 1)
        self.setCentralWidget(self.centralwidget)

    class Batcher(GODLabel):
        """
        a little widget that hovers at the bottom corner of the screen containing the current page we're
        viewing and how many pages there's in total. if you click the label 1/3 to the left you'll change
        the 100's, in the middle for changing the 10's and at the 1/3 right for changing the single's.
        left click for up, right click for down. then press arrows LEFT/RIGHT to turn to next/previous page.
        middle click for going to the "current" showing page, not found of the middle click solution but
        seems to be such rare usage for some extraordinary measure.
        """
        def __init__(self, *args, **kwargs):
            self.children = []
            self.status_code = False
            self.current_page = False
            self.que = t.config('batch_size')
            super().__init__(*args, **kwargs)
            t.style(self, background=TRANSPARENT, color=TRANSPARENT)
            self.current_page = self.NextPage(place=self, center=True, qframebox=True, parent=self)
            self.current_page.change_page = self.change_page
            self.children.append(self.current_page)
            t.style(self.current_page, background=DARK_BACK, color=GRAY, font=12)
            self.current_page.setToolTip('USE LEFT/RIGHT ARROWS TO TURN PAGE OR MIDDLECLICK FOR "CURRENT/REFRESH"')
            self.status_code = GODLabel(place=self, center=True, qframebox=True)
            self.children.append(self.status_code)
            self.advanced_search = self.parent.advanced_search

            self.page_call_previous = QShortcut(QKeySequence('left'), self)
            self.page_call_next = QShortcut(QKeySequence('right'), self)

            self.page_call_previous.activated.connect(lambda: self.change_page(-1))
            self.page_call_next.activated.connect(lambda: self.change_page(+1))

        def change_page(self, modify=0):
            """
            :param modify: 0 meaning we "refresh" current page, else turn left/right among pages if possible
            """
            if modify == -1:
                if self.searchdict['pageIndex'] != 0:
                    self.searchdict['pageIndex'] += modify
                    self.advanced_search(self.searchdict)
            elif modify == +1:
                pageindex, pagesize, totalpages = self.get_currents()
                if self.searchdict['pageIndex'] +1 < totalpages:
                    self.searchdict['pageIndex'] += modify
                    self.advanced_search(self.searchdict)
            elif modify == 0:
                self.advanced_search(self.searchdict)

        def exapns_self(self):
            """
            uses geometry() from all widgets in self.children and expaning base accordingly
            """
            if not self.status_code:
                return

            t.pos(self.status_code, left=0, top=0)
            t.pos(self.current_page, below=self.status_code, y_margin=1)

            right, bottom = 0, 0
            for i in self.children:
                if i.geometry().right() >= right:
                    right = i.geometry().right() +1
                if i.geometry().bottom() >= bottom:
                    bottom = i.geometry().bottom() +1
            t.pos(self, size=[right, bottom])

        def show_results(self, curldata, searchdict):
            """
            keeps the curldata and searchdict inside self, we're passing altered searchdict to
            fn:advanced_serach when turning pages
            :param curldata: response object
            :param searchdict: fn:advanced_search dictionary
            """
            self.curldata = curldata
            self.searchdict = searchdict
            self.set_current_page()
            self.set_status_code()

        def set_status_code(self):
            """
            a small plate on the top shoping status_code from response, red color/error never tested
            """
            self.status_code.setText(f"STATUS CODE: {self.curldata['statusCode']}")
            if self.curldata['statusCode'] < 211:
                t.style(self.status_code, background='darkGreen', color=WHITE, font=8)
            else:
                t.style(self.status_code, background=DEACTIVE_RED, color=GRAY, font=8)
            t.shrink_label_to_text(self.status_code, x_margin=4, y_margin=2, height=True)

        def get_currents(self):
            pageindex = self.searchdict['pageIndex']
            pagesize = self.searchdict['pageSize']
            totalpages = math.ceil(self.curldata['total'] / pagesize)
            return pageindex, pagesize, totalpages

        def set_current_page(self):
            pageindex, pagesize, totalpages = self.get_currents()
            text = f"Showing page: {pageindex+1} of {totalpages}"
            self.current_page.setText(text)
            t.shrink_label_to_text(self.current_page, x_margin=8, y_margin=2, height=True)

        def counter(self, reset=False, sub=None, add=None):
            """
            self.que is counting downwards from 50 to 0 and if zero is going to break False is returned instead of True.
            :param reset self.que back to default ie 50
            :param sub currently not used but the idea is to quickly refill the que if one is discarded
            :param add when "asking" to add one, self.que is actually subracted, not sure if this dump or smart yet
            """
            if reset:
                self.que = t.config('batch_size')

            if sub:
                self.que += sub
                return True
            elif add:
                if self.que - add >= 0:
                    self.que -= add
                    return True

            return False

        class NextPage(GODLabel):
            def mouseMoveEvent(self, ev: QtGui.QMouseEvent) -> None:
                pass

            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                """
                button() == 4 is a middle click, requesting "current" page number from the label
                else if changing page numbers depending on what area you clicked, mouse 1 up, mouse 2 down
                """
                if ev.button() == 4:
                    self.change_page(modify=0)
                    return

                searchdict = self.parent.searchdict
                curldata = self.parent.curldata

                if ev.pos().x() < self.width() * 0.33:
                    add = 100
                elif ev.pos().x() < self.width() * 0.66:
                    add = 10
                else:
                    add = 1

                if ev.button() == 2:
                    add -= add *2

                pageindex = searchdict['pageIndex'] + add
                pagesize = searchdict['pageSize']
                totalpages = math.ceil(curldata['total'] / pagesize)

                if pageindex < 0:
                    pageindex = 0
                elif pageindex > totalpages:
                    pageindex = totalpages - 1

                searchdict['pageIndex'] = pageindex
                text = f"Start from: {pageindex + 1} of {totalpages}"
                self.setText(text)
                t.shrink_label_to_text(self, x_margin=8, y_margin=2, height=True)

        def set_position(self):
            """
            currently at the bottom-left of self.main on top of scrollarea widgets
            """
            self.exapns_self()
            t.pos(self, bottom=self.main.height() - 4, left=3)

        def drag_widget(self, ev):
            if not self.old_position:
                self.old_position = ev.globalPos()

            delta = QtCore.QPoint(ev.globalPos() - self.old_position)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_position = ev.globalPos()

        def mouseMoveEvent(self, ev: QtGui.QMouseEvent) -> None:
            self.drag_widget(ev)

        def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
            self.raise_()
            self.old_position = ev.globalPos()

    def create_batcher(self):
        self.batcher = self.Batcher(place=self, main=self)
        t.pos(self.batcher, size=[0,0])

    class Searcher(Canvas):
        """
        if button is activated we're ignoring cache and re-requesting all queries without looking into cache
        sc:returnPressed is set during creation
        """
        class Button(Canvas.Button):
            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                if ev.button() == 1:
                    self.activation_toggle()
                    t.signal_highlight()

                    if self.activated:
                        self.tiplabel.setText('IGNORING CACHE')
                    else:
                        self.tiplabel.setText('MASTERS WISHES')
                else:
                    self.advanced_search()

    def create_searcher(self):
        self.searcher = create_indikator(
            place=self,
            button=True,
            lineedit=True,
            lineedit_foreground=TITLE_WHITE,
            lineedit_background=DARK_BACK,
            mouse=True,
            Special=self.Searcher,
            tiplabel='SEARCH...',
            tipfont=8,
            tipwidth=120,
        )
        search = t.config('last_search')
        if type(search) != str:
            search = ""

        self.searcher.lineedit.setText(search)
        t.pos(self.searcher, size=[400,30], move=[1,0])
        self.searcher.button.activation_toggle(force=False)
        self.searcher.lineedit.returnPressed.connect(self.advanced_search)
        self.searcher.button.tiplabel = self.searcher.tiplabel
        self.searcher.button.advanced_search = self.advanced_search

    class Category(GODLabel, GLOBALHighLight):
        """
        when you click a category-item it is lit and activated, and a subcategory blinds can show
        default sub-categories are not used and not removed from code, perhaps they'll be usefull later on
        """
        def __init__(self, supress=False, *args, **kwargs):
            super().__init__(
                deactivated_on=dict(background=LIGHTPURPLE, color=GRAY),
                deactivated_off=dict(background=LIGHT_GRAY, color=GRAY),
                activated_on=dict(background=LIGHTPURPLE, color=BLACK),
                activated_off=dict(background=TEXT_WHITE, color=BLACK),
                *args, **kwargs
            )
            self.set_pointers()
            self.supress = supress
            self.children = []
            if t.config(self.type):
                self.activation_toggle(force=True, save=False)
            else:
                self.activation_toggle(force=False, save=False)

        def set_pointers(self):
            self.Category = self.main.Category
            self.get_all_subcategories = self.main.get_all_subcategories
            self.searcher = self.main.searcher

        def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
            """
            the code below is not used but still kept for future explorations
            """
            self.activation_toggle()

            if self.supress:
                return

            if self.activated:
                if self.children:
                    [x.show() for x in self.children]

                else:
                    rv = self.get_all_subcategories()
                    if rv:
                        sub = [x for x in rv if x['catid'] == self.data['id']]
                        for d in sub:
                            name = d['name']
                            label = self.Category(

                                place=self.main,
                                main=self.main,
                                type = name + '_sub_' + self.type,
                                mouse=True,
                                center=True,
                            )
                            label.setText(name)

                            if not self.children:
                                t.pos(label, coat=self.searcher, below=self.searcher, y_margin=1, width=150)
                            else:
                                t.pos(label, coat=self.children[-1], after=self.children[-1], x_margin=1)

                            self.children.append(label)

            elif not self.activated and self.children:
                [x.hide() for x in self.children]


    class Resolution(Category):
        """
        showing 720p, 1080p etc in the subcategories
        """
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.deactivated_on = dict(background=DARK_BACK, color=TEXT_WHITE)
            self.deactivated_off = dict(background=GRAY, color=BLACK)
            self.activated_on = dict(background=DARK_BACK, color=TEXT_WHITE)
            self.activated_off = dict(background=DARK_BACK, color=TEXT_WHITE)

        class Res(GODLabel, GLOBALHighLight):
            def __init__(self, *args, **kwargs):
                super().__init__(
                    deactivated_on=dict(background=LIGHTPURPLE, color=GRAY),
                    deactivated_off=dict(background=LIGHT_GRAY, color=GRAY),
                    activated_on=dict(background=LIGHTPURPLE, color=BLACK),
                    activated_off=dict(background=TEXT_WHITE, color=BLACK),
                    *args, **kwargs
                )

            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                self.activation_toggle()
                if 'Any' in self.type:
                    [x.activation_toggle(force=self.activated) for x in self.parent.children]

        def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
            self.activation_toggle()

            if self.supress:
                return

            if self.activated:
                if self.children:
                    [x.show() for x in self.children]

                else:
                    self.master_signal = t.signals()
                    for k,v in self.data.items():
                        label = self.Res(
                            place=self.main,
                            main=self.main,
                            parent=self,
                            type=self.type + k,
                            mouse=True,
                            center=True,
                            load=True,
                            qframebox=True,
                        )
                        label.setText(k)

                        if not self.children:
                            t.pos(label, size=self, below=self, y_margin=1)
                        else:
                            t.pos(label, coat=self.children[-1], below=self.children[-1])

                        self.children.append(label)

            elif not self.activated and self.children:
                [x.hide() for x in self.children]

            t.signal_highlight()

    class LeechSettings(Resolution):
        """
        free, yellow, green etc, currently we can only request on or all in the same request
        """
        class Res(GODLabel, GLOBALHighLight):
            def __init__(self, *args, **kwargs):
                super().__init__(
                    deactivated_on=dict(background=LIGHTPURPLE, color=GRAY),
                    deactivated_off=dict(background=LIGHT_GRAY, color=GRAY),
                    activated_on=dict(background=LIGHTPURPLE, color=BLACK),
                    activated_off=dict(background=TEXT_WHITE, color=BLACK),
                    *args, **kwargs
                )
            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                self.activation_toggle(force=True)
                [x.activation_toggle(force=False) for x in self.parent.children if x != self]

    class Config(Resolution):
        """
        currently only Login and Password
        """
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.config = False

        class ConfBackplate(GODLabel):
            def drag_widget(self, ev):
                if not self.old_position:
                    self.old_position = ev.globalPos()

                delta = QtCore.QPoint(ev.globalPos() - self.old_position)
                self.move(self.x() + delta.x(), self.y() + delta.y())
                self.old_position = ev.globalPos()

            def mouseMoveEvent(self, ev: QtGui.QMouseEvent) -> None:
                self.drag_widget(ev)

            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                self.raise_()
                self.old_position = ev.globalPos()
                if ev.button() == 2:
                    self.parent.activation_toggle(force=False, save=False)
                    self.hide()

        class Login(Canvas):
            class LineEdit(GODLE):

                def text_changed(self):
                    button = self.parent.button
                    text = self.text().strip()
                    if text != '***' and text != t.config(self.type, curious=True):
                        self.parent.tiplabel.setText('SAVE')
                        button.activated_on = dict(background=YELLOW, color=BLACK)
                        button.activated_off = dict(background=ORANGE, color=BLACK)
                        button.deactivated_on = dict(background=HIGH_RED, color=BLACK)
                        button.deactivated_off = dict(background=DEACTIVE_RED, color=BLACK)
                    else:
                        button.activated_on = dict(background=HIGH_GREEN, color=BLACK)
                        button.activated_off = dict(background=ACTIVE_GREEN, color=BLACK)
                        button.deactivated_on = dict(background=HIGH_RED, color=BLACK)
                        button.deactivated_off = dict(background=DEACTIVE_RED, color=BLACK)
                        button.restore_tiplabel()
                    t.signal_highlight()

            def restore_tiplabel(self, text, before_restoring='SAVED', quick=False):
                if quick:
                    self.tiplabel.setText(text)
                    return

                if before_restoring:
                    self.tiplabel.setText(before_restoring)

                t.start_thread(dummy=True, slave_args=3, master_fn=lambda: self.tiplabel.setText(text))

            class Button(Canvas.Button):
                def restore_tiplabel(self):
                    self.parent.restore_tiplabel('LOGIN', quick=True)

                def save(self):
                    text = self.parent.lineedit.text().strip()
                    if text:
                        t.save_config('login', text)
                        self.restore_tiplabel()

                def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                    self.save()
                    self.save_refresh_fn()

        class Password(Login):
            class Button(Canvas.Button):
                def restore_tiplabel(self):
                    self.parent.restore_tiplabel('PASSWD', quick=True)

                def save(self):
                    text = self.parent.lineedit.text().strip()
                    if text and text != '***':
                        t.save_config('password', text)
                        self.restore_tiplabel()

                def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                    self.save()
                    self.save_refresh_fn()

        class ShowS01E01(Login):
            def post_init(self):
                t.style(self.label, background=DARK_BACK, color=WHITE, font=12)
                self.label.setIndent(3)
                self.label.activated_on = dict(color=WHITE)
                self.label.activated_off = dict(color=LIGHT_GRAY)
                self.label.deactivated_on = dict(color=LIGHT_GRAY)
                self.label.deactivated_off = dict(color=GRAY)

            class Button(Canvas.Button):
                def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                    self.activation_toggle(save=True)
                    self.parent.label.activation_toggle(force=self.activated, save=False)
                    self.save()

        def show_configs(self):
            if self.config:
                self.config.show()
                return

            def save_refresh_fn():
                """ lazy working solution, each time login/pwd is updated credentials and categories overlooked """
                if self.main.has_stored_login_and_password():
                    self.main.check_credentials()
                    self.main.create_categories()
                    t.signal_highlight()

            self.config = self.ConfBackplate(place=self.main, parent=self)
            self.config.setFrameShape(QtWidgets.QFrame.Box)
            self.config.setLineWidth(1)

            self.config.login = create_indikator(
                place=self.config,
                type='login',
                mouse=True,
                button=True,
                lineedit=True,
                tiplabel = 'LOGIN',
                tipfont=10,
                tipwidth=80,
                load=True,
                Special=self.Login,
                inherit_type=True,
                button_listen=True,
            )
            t.style(self.config.login.lineedit, background=DARK_BACK, color=WHITE)
            self.config.login.button.save_refresh_fn = save_refresh_fn

            self.config.password = create_indikator(
                place=self.config,
                type='password',
                mouse=True,
                button=True,
                lineedit=True,
                tiplabel='PASSWD',
                tipfont=10,
                tipwidth=80,
                Special=self.Password,
                inherit_type=True,
            )
            t.style(self.config.password.lineedit, background=DARK_BACK, color=WHITE)
            self.config.password.button.save_refresh_fn = save_refresh_fn

            self.config.s01e01 = create_indikator(
                place=self.config,
                type='show_s01e01',
                mouse=True,
                button=True,
                label=True,
                Special=self.ShowS01E01,
                inherit_type=True,
                load=True,
            )
            self.config.s01e01.label.setText('SHOW S01E01 DETAILS-BOX')
            self.config.s01e01.post_init()

            self.config.dev_mode = create_indikator(
                place=self.config,
                type='dev_mode',
                mouse=True,
                button=True,
                label=True,
                Special=self.ShowS01E01,
                inherit_type=True,
                load=True,
            )
            self.config.dev_mode.label.setText('DEVELOPER FEATURES')
            self.config.dev_mode.post_init()

            t.pos(self.config.login, size=[300,30], move=[10,10])
            rv = t.config('login', curious=True)
            if rv:
                self.config.login.lineedit.setText(rv)
                self.config.login.button.activation_toggle(force=True, save=False)

            t.pos(self.config.password, coat=self.config.login, below=self.config.login, y_margin=1)
            rv = t.config('password', curious=True)
            if rv:
                self.config.password.lineedit.setText('***')
                self.config.password.button.activation_toggle(force=True, save=False)

            t.pos(self.config.s01e01, coat=self.config.password, below=self.config.password, y_margin=1)
            t.pos(self.config.dev_mode, coat=self.config.s01e01, below=self.config.s01e01, y_margin=1)

            t.pos(self.config,
                  width=self.config.login.geometry().right() + 10,
                  height=self.config.dev_mode.geometry().bottom() + 10,
                  move=[200,200]
                  )
            t.style(self.config, background=GRAY, color=BLACK)

        def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
            self.activation_toggle()
            if self.activated:
                self.show_configs()
            elif self.config:
                self.config.hide()

    def create_config(self):
        """ currently only login and password, so the plate is currently to much, but in case we expand its good """
        self.config = self.Config(place=self, main=self, mouse=True, center=True)
        self.config.activation_toggle(force=False, save=False)
        self.config.setText('CONFIG')
        t.shrink_label_to_text(self.config, x_margin=10)
        t.pos(self.config, height=self.searcher, after=self.searcher, x_margin=1)

    def create_resolutions(self):
        RV = self.get_fields()
        self.resolutions = self.Resolution(place=self, main=self, type='resolutions_', mouse=True, center=True)
        self.resolutions.activation_toggle(force=False, save=False)
        self.resolutions.data = RV.resolution
        self.resolutions.setText('RESOLUTIONS')
        t.shrink_label_to_text(self.resolutions, x_margin=10)
        t.pos(self.resolutions, height=self.searcher, after=self.leech_config, x_margin=1)

    def create_leech_categories(self):
        RV = self.get_fields()
        self.leech_config = self.LeechSettings(place=self, main=self, type='free_', mouse=True, center=True)
        self.leech_config.activation_toggle(force=False, save=False)
        self.leech_config.data = RV.free
        self.leech_config.setText('LEECH FILTER')
        t.shrink_label_to_text(self.leech_config, x_margin=10)
        t.pos(self.leech_config, height=self.searcher, after=self.config, x_margin=1)

    def get_current_resolutions(self):
        """ Any is not really used, instead we just push "nothing" for that effect """
        fields = self.get_fields()
        rv = []
        for k,v in fields.resolution.items():
            if 'Any' in k:
                continue

            if t.config('resolutions_' + k):
                rv.append(v)

        return rv

    def get_current_leech(self):
        """ api takes single filter only for free-types therefore first result is immediately returned """
        fields = self.get_fields()
        for k, v in fields.free.items():
            if 'Any' in k:
                continue

            if t.config('free_' + k):
                return v

    def get_current_categories(self):
        rv = self.get_all_categories()
        if rv:
            rv = [x['id'] for x in rv if t.config(x['name'])]

        return rv

    def create_categories(self):
        """ creates categories, movies, tv, xxx etc... """
        if self.category_widgets:
            return

        rv = self.get_all_categories()
        if not rv:
            return

        for d in rv:
            name = d['name']
            label = self.Category(place=self, main=self, type=name, mouse=True, center=True, supress=True)
            label.setText(name)
            label.data = d

            if not self.category_widgets:
                t.pos(label, after=self.resolutions, height=self.searcher, x_margin=1)
            else:
                t.pos(label, after=self.category_widgets[-1], height=self.searcher, x_margin=1)

            t.shrink_label_to_text(label, x_margin=10)
            self.category_widgets.append(label)

    def create_update_db_button(self):
        """
        maybe this can be improved in a lot of ways.
        at every run one title is queried if such isnt returned, updated of local IMDb will be initied
        else the idea is that you manually update local IMDb whenever you feel like its time to do so
        """
        self.update_db_button = RefreshImdb(place=self, main=self, mouse=True)
        self.update_db_button.setText('UPDATE IMDB')
        t.shrink_label_to_text(self.update_db_button, x_margin=50)
        t.pos(self.update_db_button, height=self.searcher, right=self.width(), x_margin=1)
        one_title = sqlite.execute('select * from titles')
        if not one_title:
            self.update_db_button.start_update_process()

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        """ some widgets reyly on mainwindows resizeevents """
        if self.update_db_button:
            t.pos(self.update_db_button, right=self.width(), x_margin=1)
        if self.batcher:
            self.batcher.set_position()

    def post_init(self):
        self.setup_gui() # scrollarea
        self.create_searcher() # search bar
        self.create_update_db_button() # IMDb
        self.create_config() # login/password
        self.create_leech_categories() # free leech stuff
        self.create_resolutions() # 720p 1080p etc
        if self.has_stored_login_and_password(): self.create_categories() # only works if we have working login
        self.create_batcher() # keeps track on where we are
        self.advanced_search() # autoinits the previous search upon launch, feel this is ok but can be improved

    def position_mainwindow(self, primary=True):
        """ starts by centering the window on primary screen """
        if primary:
            primary_monitor = [x for x in screeninfo.get_monitors() if x.is_primary]
            if primary_monitor:
                primary = primary_monitor[0]

                x = int(primary.x)
                y = int(primary.y)
                w = int(primary.width * 0.8)
                h = int(primary.height * 0.8)

                self.move(x + int(primary.width * 0.1), y + (int(primary.height * 0.1)))
                self.resize(w, h)
            else:
                self.resize(1000, 700)
                self.move(100,100)

    def has_stored_login_and_password(self):
        login = t.config('login')
        pwd = t.config('password')

        if not login or not pwd:
            return False
        else:
            return True

    def check_credentials(self):
        """
        THIS HAPPENS DURING EACH LAUNCH

        this is a bit dissoriented but currently working, if we have a token we try it, if that token isnt
        working we ask for a new one. later we try the apikey, if that isnt working or none is present
        we ask for a new one or ask for the generation of one.

        :return: bool
        """
        if not self.token:
            self.get_token(force=True)

        def token(self):
            url = 'https://api.bit-hdtv.com/user/check'
            rv = self.api(url, token=True, post=True, apikey=False, force=True)

            if not rv:
                self.get_token(force=True)
                rv = self.api(url, token=True, post=True, apikey=False, force=True)

            if rv:
                self.token = rv
                t.save_config('token', rv)
                return True

        if not self.token or not token(self):
            print("TOKEN ERROR!")
            return False

        def apikey(self):
            url = 'https://api.bit-hdtv.com/user/apikey'
            rv = self.api(url=url, get=True, apikey=False, token=True, force=True)
            if not rv:
                url = 'https://api.bit-hdtv.com/user/apikey/generate'
                rv = self.api(url=url, post=True, apikey=False, token=True, force=True)
                print('GENERATED NEW APIKey:', rv)

            if rv:
                self.apikey = rv
                t.save_config('apikey', rv)
                return True

        if not apikey(self):
            print("APIKey ERROR!")
            return False

    def get_token(self, force=False):
        if not self.token or force:
            login = t.config('login')
            pwd = t.config('password')
            param = dict(username=login, password=pwd)
            url = 'https://api.bit-hdtv.com/user/login'
            rv = self.api(url=url, data=param, post=True, token=False, apikey=False, force=force)
            if rv:
                self.token = rv['token']
                t.save_config('token', self.token)

        return self.token

    def api(self, url, data=None, token=True, apikey=True, post=False, get=False, method='get', force=False):
        """ i assume we understand whats going on here """
        def check_cache(url, data):
            tmp = url
            if data:
                tmp += json.dumps(data)
            tmpfile = t.tmp_file(file_of_interest=tmp, days=1, hash=True, reuse=True, extension='json')
            if os.path.exists(tmpfile):
                with open(tmpfile) as f:
                    return json.loads(f.read())

        def save_cache(url, data, response):
            tmp = url
            if data:
                tmp += json.dumps(data)
            tmpfile = t.tmp_file(file_of_interest=tmp, delete=True, hash=True, extension='json')
            with open(tmpfile, 'w') as f:
                f.write(json.dumps(response))

        def get_method(method, post, get):
            if post:
                return 'post'
            elif get:
                return 'get'
            else:
                return method

        def generate_job(self, method, url, data, token, apikey):
            job = dict(method=method, url=url, headers=t.header_generator())
            if data:
                job.update(dict(data=data))

            if token:
                job['headers'].update(dict(Authorization='Bearer ' + self.token))

            if apikey:
                job['headers'].update({'X-EGEN-AccessTokenID': self.apikey})
            return job

        if token and not self.token: return False
        if apikey and not self.apikey: return False

        method = get_method(method, post, get)
        job = generate_job(self, method, url, data, token, apikey)

        if not force:
            cache = check_cache(url, data)
            if cache:
                return cache['data']

        response = requests.request(**job)

        if response.status_code in [200, 201, 202]:
            response = response.json()
            save_cache(url, data, response)
            return response['data']
        else:
            print(url, response.json(), job)

    def get_all_categories(self):
        rv = self.api(url='https://api.bit-hdtv.com/category/all', token=True, apikey=True)
        if rv:
            rv.sort(key=lambda x:x['name'])
            return rv

    def get_all_subcategories(self):
        rv = self.api(url='https://api.bit-hdtv.com/subcategory/all', token=True, apikey=True)
        if rv:
            rv.sort(key=lambda x:x['name'])
            return rv

    def get_fields(self):
        """ there's no need to rewrite, but this was made early and would be different if done now """
        class RV:
            sort = dict(
                Name='name',
                Files='files',
                Comments='comments',
                Added='added',
                Size='size',
                Completed='completed',
                Seeders='seeders',
                Leechers='leechers',
                Rating='rating',
                Id='id'
            )
            sort_direction = dict(
                Ascending='asc',
                Decending='desc',
            )
            resolution = {
                'Any': 0,
                '720p': 1,
                '1080i': 2,
                '1080p': 3,
                '2160p': 4,
            }
            free = dict(
                Any=0,
                Normal=1,
                Yellow=2,
                Grey=3,
                Green=4
            )
        return RV()

    def genereate_searchdictionary(self, search=None):
        """ saves search and catches nessesary field components """
        text = self.searcher.lineedit.text().strip()
        t.save_config('last_search', text)
        RV = self.get_fields()

        searchdict = dict(
        pageIndex=0,
        pageSize=50,
        sortField=RV.sort['Id'],
        sortDirection=RV.sort_direction['Decending'],
        search=search or self.searcher.lineedit.text().strip(),
        )
        for k,v in dict(
                resolutions=self.get_current_resolutions(),
                categories=self.get_current_categories(),
                free=self.get_current_leech()).items():
            if v:
                searchdict.update({k:v})

        return searchdict

    def advanced_search(self, searchdict=None, draw_results=True, search=None):
        """
        this has been a bit messy to deal with in many ways, currently we need to save the request paramas
        as a local json file to later include as an argument when using curl in a subprocess. curl saves
        the results into a local file wich we load after the subprocess is completed and the result from
        that file is the jackpot itself.
        :param searchdict: dictionary (when turning pages we reuse previous dictionary)
        :param draw_results: bool, sometime we just want the data it self without showing it
        :param search: string
        :return: dictionary from fn: generate_job_from_response
        """
        if not searchdict:
            searchdict = self.genereate_searchdictionary(search=search)

        tmpfile = t.tmp_file(file_of_interest=str(searchdict), days=1, hash=True, reuse=True, extension='json')
        if self.token and self.apikey:
            if not os.path.exists(tmpfile) or self.searcher.button.activated:

                jsontmp = t.tmp_file(file_of_interest='curl_tmp.json', delete=True)
                with open(jsontmp, 'w') as f:
                    json.dump(searchdict, f)

                curlstr = 'curl -X POST "https://api.bit-hdtv.com/torrent/search/advanced" -H "accept: application/json" '
                curlstr += '-H  "Authorization: Bearer ' + self.token + '" -H  "X-API-KEY: ' + self.apikey
                curlstr += f'" -H  "Content-Type: application/json" -d @"{jsontmp}" > "{tmpfile}"'
                subprocess.call(curlstr, shell=True)

        if not os.path.exists(tmpfile):
            return

        with open(tmpfile, 'r') as f:
            content = f.read()
            rv_org = json.loads(content)
            if rv_org and rv_org['statusCode'] < 210:
                rv_org['skipped'] = 0
                rv = rv_org['data']
            else:
                print("DEEP ERROR!", rv_org['statusCode'])
                return

        tmp = self.generate_job_from_response(rv, rv_org, searchdict, draw_results=draw_results)
        return tmp

    def generate_job_from_response(self, rv, rv_org, searchdict, draw_results=True):
        """
        SELF.DRAW_QUE is generated from here

        theres two skipping methods going on here, the first one is if the torrent_id is in the
        skiplist and the second one is if the IMDb tconst is awalible from torrent the information
        itself AND that tconst is blacklisted.

        otherwise a dictionary is generated that later on becomes self.draw_que

        dictionary setup:
        dict['results'] = list[torrent_data, torrent_data...] where each key is IMDb-tconst or what "link"
        is present from the torrentdata. this is because offen there's many releases of the same tconst,
        such as 720p, 1080p and so on, these are all baked into one "key/input".

        :param rv: basically rv_org['data']
        :param rv_org: jsonloaded content
        note: breaking up the fn:advanced_search into smaller parts, thats why confusing params
        """
        if rv:
            tmp = {}
            for i in rv:

                if not i['url']:
                    rv_org['skipped'] += 1
                    continue

                skip = sqlite.execute('select * from skiplist where torrent_id = (?)', i['id'])
                if skip:
                    rv_org['skipped'] += 1
                    continue

                link = i['url'].strip().rstrip('/')
                target = 'imdb.com/title/tt'
                if target in link:
                    tconst = 'tt' + link[link.find(target) + len(target):]
                    link = 'http://imdb.com/title/' + tconst

                    skip = sqlite.execute('select * from skiplist where tconst = (?)', tconst)
                    if skip:
                        rv_org['skipped'] += 1
                        continue

                episode, _ = self.get_episode(path=i['name'], cut=0)
                if episode: sep = link + episode[0]
                else: sep = link

                if sep not in tmp:
                    tmp.update({sep: dict(results=[], used=False, link=link, count=len(tmp))})

                tmp[sep]['results'].append(i)

            if tmp and draw_results:
                self.draw_que = [tmp[x] for x in tmp]

                for i in self.draw_que:
                    i['results'].sort(key=lambda x:x['resolution'], reverse=True)

                self.batcher.show_results(rv_org, searchdict)
                self.batcher.set_position()
                t.close_and_pop(self.children)
                self.draw_fortified()
                self.draw_results(reset_que=True)

            return tmp

    def draw_fortified(self):
        """
        fortified widgets are not closed, they are instead kept inside self.children and redrawn at
        every refresh and new results follow the fortified ones, very prooud of this effect!
        """
        tmp = []
        for widget in [x for x in self.children if x.fortified]:
            if not tmp:
                t.pos(widget, left=1, top=1)
            else:
                if tmp[-1].geometry().right() + widget.width() > self.width():

                    if tmp[-1].rating_widget.children:
                        y = 1
                    else:
                        y = t.config('cover_height') * 0.02 + 1

                    t.pos(widget, below=tmp[-1], left=tmp[0], y_margin=y)
                    t.pos(self, width=tmp[-1].geometry().right() + 2)
                else:
                    t.pos(widget, after=tmp[-1], x_margin=1)

            tmp.append(widget)

    def draw_results(self, reset_que=True):
        """
        Covers are NOT drawn here, this is just recognizing IMDb and visualising other datas such
        as resolition, filesize and free leech.

        iters the list for the first not-used object to draw later markes it as used, positions
        it next to the previous widget or at a new row if row is full, then have a thread check
        once GUI is updated to request new object.

        :param reset_que: bool (thread sends False)
        """
        if reset_que:
            self.batcher.counter(reset=True)
            self.scrollcanvas_main.setMinimumHeight(0)

        for data in self.draw_que:
            if data['used']:
                continue

            if not self.batcher.counter(add=1):
                break

            widget = CoverWidget(place=self.scrollcanvas_main, main=self, data=data)
            if not self.children:
                t.pos(widget, left=1, top=1)
            else:
                if self.children[-1].geometry().right() + widget.width() > self.width():

                    if self.children[-1].rating_widget.children: y = 1
                    else: y = t.config('cover_height') * 0.02 + 1

                    t.pos(widget, below=self.children[-1], left=self.children[0], y_margin=y)
                    t.pos(self, width=self.children[-1].geometry().right() + 2)
                else:
                    t.pos(widget, after=self.children[-1], x_margin=1)

            data['used'] = True
            self.children.append(widget)

            t.start_thread(dummy=True, slave_args=0.025, master_fn=self.draw_results, master_args=(False,))
            return

        self.draw_covers()

    def draw_covers(self):
        def draw_one(self):
            """ gets the first widget that hasnt tried their cover and inits its showing cover fn """
            if self.children:
                undone = [x for x in self.children if not x.showing_pixmap]
                if undone:
                    undone[0].identify_imdb_by_filename()

        def exclude_me(self, errordict):
            """
            rather much fn for such rare effect, but once we reject a widget, offen due to after its IMDb
            tconst is identified and later on finding out it beeing inside the skiplist, we pop that widget
            and therefore we need to reorganize all remaning widgets to fill that gap.

            :param errordict: signal emits who to kill -> dict(exclude=self)
            """
            if self.children:
                exclude = [x for x in self.children if x == errordict['exclude']]
                tmp_x, tmp_y = exclude[0].geometry().right(), exclude[0].geometry().bottom()
                exclude[0].close()
                self.children = [x for x in self.children if x != errordict['exclude']]

                for count, widget in enumerate(self.children):

                    if widget.geometry().bottom() < tmp_y:
                        continue
                    elif widget.geometry().bottom() == tmp_y and widget.geometry().right() < tmp_x:
                        continue

                    if count == 0:
                        t.pos(widget, left=1, top=1)
                    else:
                        if self.children[count-1].geometry().right() + widget.width() > self.width():

                            if self.children[count-1].rating_widget.children:
                                y = 1
                            else:
                                y = t.config('cover_height') * 0.02 + 1

                            t.pos(widget, below=self.children[count-1], left=self.children[0], y_margin=y)
                            t.pos(self, width=self.children[count-1].geometry().right() + 2)
                        else:
                            t.pos(widget, after=self.children[count-1], x_margin=1)

                draw_one(self) # we need to init the draw one manually from here, forgot why

        # kills old
        signal = t.signals(name='primary')
        try: signal.disconnect()
        except TypeError: pass

        signal = t.signals(name='primary', reset=True)
        signal.finished.connect(partial(draw_one, self))
        signal.error.connect(partial(exclude_me, self))
        signal.finished.emit()

    def resize_scrollcanvas(self):
        bottom = 0
        for i in self.children:
            if i.geometry().bottom() > bottom:
                bottom = i.geometry().bottom()

        if self.scrollcanvas_main.width() != self.width():
            t.pos(self.scrollcanvas_main, width=self)

        if self.scrollcanvas_main.height() != bottom +1:
            self.scrollcanvas_main.setMinimumHeight(bottom +1)

    def get_leading_widget(self, widgetlist):
        """ not used, but i'm keeping it """
        leading_widget = None

        for i in widgetlist:

            if not leading_widget:
                leading_widget = i
                continue

            if i.geometry().top() < leading_widget.geometry().top():
                continue

            if i.geometry().top() > leading_widget.geometry().top():
                leading_widget = i

            if i.geometry().left() > leading_widget.geometry().left():
                leading_widget = i

        return leading_widget

    def get_cover_from_cache(self, db_input, download=True):
        """ :param downloading of the cover if not found in cache, focus when using threads here """
        query, values = 'select * from covers where tconst = (?)', db_input[DB.titles.tconst]
        data = sqlite.execute(query=query, values=values)

        if not data and download:
            self.store_cover_as_blob(db_input, download=download)
            data = sqlite.execute(query=query, values=values)

        if data:
            cover_image = t.blob_image_from_database(data)
            if cover_image and os.path.exists(cover_image):
                return cover_image

    def store_cover_as_blob(self, db_input, path=None, download=True):
        if not path and download:
            path = self.download_imdb_cover(db_input)

        if path:
            blob = t.make_image_into_blob(path, height=t.config('cover_height'))
            t.store_blob_into_database(db_input[DB.titles.tconst], blob=blob)

    def download_imdb_cover(self, db_input):
        """ scrapping the coverfile from www.imdb.com using db_inputs tconst """
        url = 'https://www.imdb.com/title/' + db_input[DB.titles.tconst] + '/'
        cover_image = t.tmp_file(url, hash=True, reuse=True, extension='webp')

        if os.path.exists(cover_image):
            return cover_image

        left = '<meta property="og:image" content="'
        right = '"/>'
        file = t.download_file(url)
        if file:
            with open(file) as f:
                content = f.read()
                content = content.split('\n')
                for i in content:
                    if left in i:
                        cut1 = i.find(left)
                        cut2 = i[cut1:].find(right) + cut1
                        if cut1 < cut2:
                            image_url = i[cut1 + len(left):cut2]
                            rv = t.download_file(url=image_url, file=cover_image)
                            return rv

    def get_years(self, path, cut, lie=False):
        """ made early, not sure if this needs re-thinking """
        years = []
        for year in range(1950, 2050):

            if str(year) in path:

                if path.find(str(year)) < cut:
                    cut = path.find(str(year))
                if year not in years:
                    years.append(year)

        if not years and lie:
            now = datetime.datetime.now()
            years.append(now.year)

        return years, cut

    def get_episode(self, path, cut):
        """
        this is a two part method, first we try s01e01 if such isnt found we try
        just the s03 thingey since large season-releases use that logic
        :param path: string
        :param cut: int (this is later for finding out where to focus when finding name)
        :return: string(episode) and int(cut)
        """
        episode = []
        if len(path) - len('S01E01') < len('S01E01'):
            return episode

        for c in range(0, len(path) - len('S01E01')):

            if path[c].lower() != 's':
                continue
            if path[c+3].lower() != 'e':
                continue
            for digit in [1,2,4,5]:
                if not path[c+digit].isdigit():
                    break
                elif digit == 5:
                    if path[c:c+6] not in episode:
                        episode.append(path[c:c+6])
                    if c < cut:
                        cut = c

        if not episode:
            for c in range(0, len(path) - len('S01')):

                if path[c].lower() != 's':
                    continue
                for digit in [1, 2]:
                    if not path[c + digit].isdigit():
                        break
                    elif digit == 2:
                        if path[c:c + 3] not in episode:
                            episode.append(path[c:c + 3])
                        if c < cut:
                            cut = c

        return episode, cut

    def get_name(self, path, cut):
        """ made early, not sure if this needs re-thinking """
        name = path[0:cut].replace(' ', '.').split('.')
        name = [x for x in name if x] # kills empty
        name = ' '.join(name)
        if '(' in name: # assuming we dont need anything after a '('
            name = name[0:name.find('(')]
        return name

    def fetch_data(self, years, episode):
        """
        assuming if we dont have episode its a Movie-something
        :param years: list
        :param episode: anything
        :return: list with all yearly data from categories Movies or not Movies depending on episode param
        """
        data = []

        if not years:
            if episode:
                query = 'select * from titles where type != (?) and type != (?)'
            else:
                query = 'select * from titles where type is (?) or type is (?)'
            data = sqlite.execute(query=query, values=('movie', 'video',), all=True)

        else:
            for year in years:
                if episode:
                    query = 'select * from titles where start_year = (?) and type != "movie" and type != "video"'
                else:
                    query = 'select * from titles where start_year = (?) and type is "movie" or type is "video"'

                all = sqlite.execute(query=query, values=year, all=True)
                data += all

        return data
