from PyQt5                     import QtCore, QtGui, QtWidgets
from PyQt5.QtGui               import QPixmap
from bscripts.database_stuff   import DB, sqlite
from bscripts.preset_colors    import *
from bscripts.settings_widgets import GLOBALHighLight, GODLabel
from bscripts.tricks           import tech as t
import datetime
import os
import time
import webbrowser

class SortingThingey:
    def __init__(self, sortvar=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sortvar = sortvar
        # POINTERS >
        self.change_torrent = self.parent.parent.change_torrent
        self.data = self.parent.parent.data

    def sort_data(self):
        self.data['results'].sort(key=lambda x: x[self.sortvar], reverse=True)
        self.change_torrent(show_current=True)

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.parent.parent.old_position = ev.globalPos()
        if len(self.data['results']) > 1:
            self.sort_data()

class CoverWidget(GODLabel):
    def __init__(self, data, *args, **kwargs):
        self.cover_path = False
        self.data = data
        self.downloadlabel = False
        self.episode_label = False
        self.fortified = False
        self.gather_all_button = False
        self.imdb_link = False
        self.large_name_label = False
        self.more_details = []
        self.old_position = False
        self.showing_pixmap = False
        self.skiplabel = False
        self.tagged = False
        self.vertical_showing = dict(current=1, total=len(data['results']))
        super().__init__(*args, **kwargs)
        self.post_init()

    def post_init(self):
        """ create a vertical label, empty cover and a tooplate with the resolution/filesize data etc """
        self.set_pointers()
        self.vertical_name = self.VerticalName(place=self, filename=self.data['results'][0]['name'], parent=self)
        self.toolplate = self.TOOLPlate(place=self, parent=self)

        self.cover = GODLabel(place=self)
        self.cover.setFrameShape(QtWidgets.QFrame.Box)
        self.cover.setLineWidth(1)

        coverheight = t.config('cover_height')
        coverwidth = coverheight * 0.7

        t.pos(self.cover, width=coverwidth, height=coverheight)
        t.style(self.cover, background=GRAY, color=DARK_BACK)

        self.rating_widget = self.RatingWidget(place=self, parent=self)
        self.change_torrent(show_current=True)

    def set_pointers(self):
        self.advanced_search = self.main.advanced_search
        self.download_imdb_cover = self.main.download_imdb_cover
        self.fetch_data = self.main.fetch_data
        self.get_cover_from_cache = self.main.get_cover_from_cache
        self.get_episode = self.main.get_episode
        self.get_fields = self.main.get_fields
        self.get_name = self.main.get_name
        self.get_years = self.main.get_years
        self.resize_scrollcanvas = self.main.resize_scrollcanvas
        self.store_cover_as_blob = self.main.store_cover_as_blob

    class IMDbLink(GODLabel):
        """ clickable little triangle at the top-left corner that takes you to IMDb.com/tt123.. """
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            t.pos(self, left=self.parent.cover, top=self.parent.cover, size=[10,10])
            t.style(self, background=TRANSPARENT, color=TRANSPARENT)
            self.setToolTip('OPEN LINK IN BROWSER')
            self.draw_button()

        def draw_button(self):
            self.clear()
            # pixmap/background
            pm = QtGui.QPixmap(self.width(), self.height())
            back = QtGui.QColor()
            back.setRgb(0,0,0)
            back.setAlpha(0)
            pm.fill(back)
            # fill
            painter = QtGui.QPainter(pm)
            painter.setPen(QtCore.Qt.darkCyan)
            for c in range(1, self.height()):
                painter.drawLine(1, c, self.height()-c, c)
            # border
            painter.setPen(QtCore.Qt.black)
            painter.drawLine(0, 0, 0, self.height())
            painter.drawLine(0, 0, self.width(), 0)
            painter.drawLine(self.width(), 0, 0, self.height())
            # end
            painter.end()
            self.setPixmap(pm)

        def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
            link = 'http://imdb.com/title/' + self.parent.data['imdb'][0][DB.titles.tconst]
            webbrowser.open(link)

    def add_imdb_link_button(self):
        if 'imdb' in self.data and not self.imdb_link:
            self.imdb_link = self.IMDbLink(place=self, parent=self)

    class GatherAll(GODLabel, GLOBALHighLight):
        """
        pointers will be set ouside this class

        this is a little button on top of the vertical_name-label that once you click it a request is
        beeing sent to BIT-HDTV for all torrents with the same name/epoisode. gathers all the responses
        into this very same widget and make you scroll threw them using the right (next) button, this is
        good when deciding whats best for you
        """
        def __init__(self, name, episode, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.supress = False
            self.deactivated_on = dict(background='cyan', color=BLACK)
            self.deactivated_off = dict(background='darkCyan', color=BLACK)

            if name and episode:
                self.setToolTip(f"Gather all {name} with {episode[0]} from BIT-HDTV.com")
            elif name:
                self.setToolTip(f"Gather all {name} from BIT-HDTV.com")

            self.name = name
            self.episode = episode

            self.set_position()

        def set_position(self):
            t.pos(self, width=self.parent, height=7)

        def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
            if not self.supress: self.supress = True
            else: return

            query = self.name
            if self.episode:
                query += ' ' + self.episode[0]

            tmp = self.advanced_search(draw_results=False, search=query)

            if not tmp:
                return

            for link in tmp:
                for torrent in tmp[link]['results']:
                    if torrent['id'] not in [x['id'] for x in self.data['results']]:
                        self.data['results'].append(torrent)

            self.vertical_showing['total'] = len(self.data['results'])
            self.make_left_right_buttons()
            self.update()

    def add_gather_all_button(self):
        if 'imdb' in self.data and not self.gather_all_button:
            path = self.data['results'][0]['name']
            episode, cut = self.get_episode(path, cut=len(path))
            years, cut = self.get_years(path, cut)
            name = self.get_name(path, cut)
            vn = self.vertical_name
            self.gather_all_button = self.GatherAll(
                place=vn, parent=vn, name=name, episode=episode, mouse=True, qframebox=True
            )
            # POINTERS >
            self.gather_all_button.data = self.data
            self.gather_all_button.advanced_search = self.advanced_search
            self.gather_all_button.update = self.toolplate.update
            self.gather_all_button.make_left_right_buttons = self.toolplate.make_left_right_buttons
            self.gather_all_button.vertical_showing = self.vertical_showing

    # >>======================= [         CLASS.VERTICALNAME         ] }>============BELOW:ME========>>

    class VerticalName(GODLabel):
        """
        a vertical label left of the cover that shows the filename or genres for the torrent, changing
        between those when clicking the label. there might be something better to illustrate these datas
        for the user, but for now they'll be kept as is
        """
        def __init__(self, genre=False, filename=False, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.cycle = [dict(text=genre, type='genre'), dict(text=filename, type='filename')]
            self.setFrameShape(QtWidgets.QFrame.Box)
            self.setLineWidth(1)
            t.pos(self, width=13)
            t.style(self, color=BLACK)

        def generate_text_tooltip(self, pm, text):
            label = GODLabel(place=self)
            label.setText(text)
            t.pos(label, width=pm.height(), height=pm.width())

            if t.correct_broken_font_size(label, shorten=True, maxsize=6):
                self.setToolTip(text)
            else:
                self.setToolTip("")

            text = label.text()
            label.close()
            return text

        def draw_text(self, genre=False, filename=False):
            self.clear()
            # pixmap/background
            pm = QtGui.QPixmap(self.width(), self.height())
            back = QtGui.QColor()

            data = self.parent.data['results'][0]
            if data['download_multiplier'] == 0 and data['upload_multiplier'] == 1: # free
                back.setRgb(*FL_VERTICAL)
            elif data['upload_multiplier'] == 2: # free 2x
                back.setRgb(*FL2x_VERTICAL)
            else:
                back.setRgb(190,190,190)

            back.setAlpha(240)
            pm.fill(back)
            # painter
            painter = QtGui.QPainter(pm)
            painter.setPen(QtCore.Qt.black)
            painter.rotate(-90)
            # font
            font = painter.font()
            font.setPointSize(6)
            painter.setFont(font)
            # text

            gtt = self.generate_text_tooltip
            if genre and [x for x in self.cycle if x['type'] == 'genre' and x['text']]:
                text = [gtt(pm, x['text']) for x in self.cycle if x['type'] == 'genre' and x['text']]
            elif filename:
                text = [gtt(pm, x['text']) for x in self.cycle if x['type'] == 'filename']
            else:
                text = [x for x in self.cycle if x['text']]
                text = gtt(pm, text[0]['text'])

            painter.drawText(4-self.height(), self.width() - 4, text)
            # end
            painter.end()
            self.setPixmap(pm)

        def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
            self.cycle.append(self.cycle[0])
            self.cycle.pop(0)
            self.draw_text()


    # <<======ABOVE:ME=======<{ [          CLASS.VERTICALNAME        ] ==============================<<
    # >>======================= [          CLASS.TOOLPLATE          ] }>============BELOW:ME========>>

    class TOOLPlate(GODLabel):
        """
        the plate above the cover that shows all the data such as resolution, filesize, dates, etc
        """
        def __init__(self, *args, **kwargs):
            self.right = False
            self.next_imdb = False
            super().__init__(*args, **kwargs)
            self.set_pointers()
            self.post_init()

        def set_pointers(self):
            self.change_torrent = self.parent.change_torrent
            self.parent.add_next_imdb_button = self.add_next_imdb_button
            self.parent.change_added_data = self.change_added_data
            self.parent.position_views_comments_timescompleted = self.position_views_comments_timescompleted
            self.parent.update_views_comments_timescompleted = self.update_views_comments_timescompleted

        def post_init(self):
            t.pos(self, height=t.config('cover_height') * 0.12)
            self.make_added_widget()
            self.make_snatch_view_comment()
            self.make_left_right_buttons()
            self.make_resolution_label()
            self.make_filesize_label()
            self.make_seeders_leechers()

        def make_left_right_buttons(self):
            """ there's only a right button, but this cycles threw the bags torrents """
            class TurnPage(GODLabel, GLOBALHighLight):
                def __init__(self, *args, **kwargs):
                    super().__init__(
                        deactivated_on=dict(background=NEXTBUTTON_ON, color=BLACK),
                        deactivated_off=dict(background=NEXTBUTTON_OFF, color=BLACK),
                        *args, **kwargs)
                    self.setFrameShape(QtWidgets.QFrame.Box)
                    self.setLineWidth(1)

                def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                    self.change_torrent(self.forward)

            if len(self.parent.data['results']) > 1 and not self.right:
                self.right = TurnPage(place=self, mouse=True)
                self.right.forward = True
                self.right.change_torrent = self.change_torrent

        def make_resolution_label(self):
            class ShowResolution(SortingThingey, GODLabel):
                """ clickable and sortable """

            self.resolution = ShowResolution(place=self, parent=self, center=True, qframebox=True, sortvar='resolution')
            self.parent.resolution = self.resolution

        def make_filesize_label(self):
            class ShowFileSize(SortingThingey, GODLabel):
                def convert_size_to_float(self, restore=False):
                    for i in self.data['results']:
                        if restore:
                            i.pop('tmp')
                            continue

                        i['tmp'] = ""

                        for ii in i['size']:
                            if ii.isdigit() or ii == '.':
                                i['tmp'] += ii
                        try:
                            i['tmp'] = float(i['tmp'])
                        except:
                            i['tmp'] = 0

                        if i['size'][-2:] == 'GB':
                            i['tmp'] *= 10

                def sort_data(self):
                    self.convert_size_to_float()
                    self.data['results'].sort(key=lambda x:x['tmp'], reverse=True)
                    self.convert_size_to_float(restore=True)
                    self.change_torrent(show_current=True)

            self.filesize = ShowFileSize(place=self, parent=self, center=True, qframebox=True)
            self.parent.filesize = self.filesize

        # <<======ABOVE:ME=======<{ [         RESOLTION/FILESIZE        ] ==============================<<
        # >>======================= [          SEEDERS/LEECERS          ] }>============BELOW:ME========>>

        def make_seeders_leechers(self):
            """
            shows how many seeders and leechers there are on this torrent, there's also a bar thats
            illustrates the proportion of those. if there isnt any from one or both gray colors will
            represent that absence
            """
            class SeedersLeechers(GODLabel):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)

                    self.seeders = GODLabel(place=self)
                    self.leechers = GODLabel(place=self)
                    t.style(self.seeders, background=ACTIVE_GREEN)
                    t.style(self.leechers, background=PURPLE)

                def update(self):
                    t.pos(self, left=dict(right=self.seeders_digit), right=dict(left=self.leechers_digit))
                    t.pos(self, top=dict(bottom=self.resolution), bottom=dict(top=self.filesize))
                    s = self.data['seeders']
                    l = self.data['leechers']
                    if s+l == 0:
                        t.style(self, background=GRAY)
                        for i in [self.seeders, self.leechers]:
                            t.pos(i, width=0)
                    else:
                        pixels_per_unit = self.width() / (s + l)
                        if l == 0:
                            t.pos(self.seeders, height=self, left=self.seeders, right=self)
                            t.pos(self.leechers, width=0)
                        else:
                            t.pos(self.seeders, height=self, width=pixels_per_unit * s)
                            t.pos(self.leechers, height=self, left=dict(right=self.seeders), right=self)

            class Digit(SortingThingey, GODLabel):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    t.pos(self, width=30)

            self.seeders_digit = Digit(place=self, center=True, qframebox=True, sortvar='seeders')
            self.leechers_digit = Digit(place=self, center=True, qframebox=True, sortvar='leechers')

            self.seeders_leechers = SeedersLeechers(place=self, parent=self, center=True, qframebox=True)

            # POINTERS >
            self.parent.leechers_digit = self.leechers_digit
            self.parent.seeders_digit = self.seeders_digit
            self.parent.seeders_leechers = self.seeders_leechers
            self.seeders_leechers.filesize = self.filesize
            self.seeders_leechers.leechers_digit = self.leechers_digit
            self.seeders_leechers.resolution = self.resolution
            self.seeders_leechers.right = self.right
            self.seeders_leechers.seeders_digit = self.seeders_digit
            # POINTERS <

        def update(self):
            """ pretty important, manually called each time something changes that repositions widgets """
            self.position_views_comments_timescompleted()
            t.pos(self.resolution, height=self.height() * 0.5, sub=1)
            t.pos(self.resolution, left=dict(right=self.views), right=self.width(), move=[-1,0])
            t.pos(self.filesize, coat=self.resolution, bottom=self, move=[0,1])
            top, bottom = self.resolution.geometry().bottom() - 5, self.filesize.geometry().top() + 5
            t.pos(self.seeders_digit, after=self.views, top=top, bottom=bottom, move=[-1,0])
            t.pos(self.leechers_digit, top=top, bottom=bottom, right=self.filesize)
            self.seeders_leechers.update()

        # <<======ABOVE:ME=======<{ [           SEEDERS/LEECERS         ] ==============================<<

        class NextIMDb(GODLabel, GLOBALHighLight):
            """
            if there are many different IMDb candidates they're cycleble from a button and the change
            should be autostored into the cache for next time same torrent is used (may be broken)
            """
            def __init__(self, *args, **kwargs):
                super().__init__(
                    deactivated_on=dict(background=SMISK_LIGHT, color=BLACK),
                    deactivated_off=dict(background=SMISK_HARD, color=BLACK),
                    *args, **kwargs
                )
                self.current = 0
                self.setFrameShape(QtWidgets.QFrame.Box)
                self.setLineWidth(1)
                # POINTERS >
                self.update = self.parent.update()
                self.set_cover = self.parent.parent.set_cover
                self.data = self.parent.parent.data
                self.download_imdb_cover = self.parent.parent.download_imdb_cover

            def next_tooltip(self):
                self.current += 1
                if self.current > len(self.parent.parent.data['imdb']):
                    self.current = 1

                tooltip = f"Showing IMDb {self.current} of {len(self.parent.parent.data['imdb'])}"
                self.setToolTip(tooltip)

            def next_data(self):
                self.next_tooltip()
                self.data['imdb'].append(self.data['imdb'][0])
                self.data['imdb'].pop(0)

                query, values = sqlite.empty_insert_query('cache')
                values[DB.cache.torrent_id] = self.data['results'][0]['id']
                values[DB.cache.tconst] = ','.join([x[DB.titles.tconst] for x in self.data['imdb']])

                sqlite.execute('delete from cache where torrent_id = (?)', values[DB.cache.torrent_id])
                sqlite.execute(query, values=values)

                t.start_thread(
                    slave_fn=self.download_imdb_cover,
                    slave_kwargs=dict(db_input=self.data['imdb'][0]),
                    master_fn=self.set_cover,
                    master_args=True,
                )

            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                self.next_data()


        def add_next_imdb_button(self):
            if self.next_imdb:
                return

            if 'imdb' in self.parent.data and len(self.parent.data['imdb']) > 1:
                self.next_imdb = self.NextIMDb(place=self, mouse=True, parent=self, main=self.main)
                self.update()
                self.next_imdb.next_tooltip()

        # >>======================= [      CLASS.SNATCHVIEWCOMMENT      ] }>============BELOW:ME========>>

        def make_snatch_view_comment(self):
            """
            shows how many times the torrent has been downloaded and how many times it has been viewed,
            atm how many comments a torrent have isnt displayed.
            """
            class CVT(SortingThingey, GODLabel):
                """ todo maybe we want to have something that indicates if there are commets present """

            self.views = CVT(place=self, parent=self, center=True, qframebox=True, sortvar="views")
            self.times_completed = CVT(place=self, parent=self, center=True, qframebox=True, sortvar="times_completed")

        def update_views_comments_timescompleted(self, data):
            for k,i in dict(VIEWS='views', COMPLETED='times_completed').items():
                getattr(self, i).setText(str(data[i]))
                getattr(self, i).setToolTip(k)

                data = self.parent.data['results'][0]
                if data['download_multiplier'] == 0 and data['upload_multiplier'] == 1:
                    t.style(getattr(self, i), background=FL_CVT, color=BLACK, font=8)
                elif data['upload_multiplier'] == 2:
                    t.style(getattr(self, i), background=FL2x_CVT, color=BLACK, font=8)
                else:
                    t.style(getattr(self, i), background=NRM_CVT, color=BLACK, font=8)

        def position_views_comments_timescompleted(self):
            """ each time new data is added/changed we reposition/resize a lot of stuff """
            # todo i think there's something here needs to be overlooked, widgets positions differ sometimes

            def lazy_swap(self):  # todo lazy hack
                self.views, self.times_completed = self.times_completed, self.views

            lazy_swap(self)
            viewsheight = self.height() * 0.3 - 1
            epochbottom = (self.height() * 0.5) - 7

            if self.right and self.next_imdb:
                t.pos(self.right, height=self.height() * 0.5, width=10)
                t.pos(self.right, height=self.right, add=1) # overlapping looks better
                t.pos(self.next_imdb, coat=self.right, below=self.right, top=self.next_imdb, bottom=self)
                t.pos(self.next_imdb, move=[0,-1], height=self.next_imdb, add=2)
                t.pos(self.epoch, after=self.right, top=self.resolution, bottom=epochbottom)
                t.pos(self.views, below=self.epoch, height=viewsheight, width=40, y_margin=-1)

            elif self.next_imdb:
                t.pos(self.next_imdb, height=self, width=10)
                t.pos(self.next_imdb, height=self.next_imdb, add=1)  # overlapping looks better
                t.pos(self.epoch, after=self.next_imdb, top=self.resolution, bottom=epochbottom)
                t.pos(self.views, below=self.epoch, height=viewsheight, width=40, y_margin=-1)

            elif self.right:
                t.pos(self.right, height=self, width=10)
                t.pos(self.right, height=self.right, add=1) # overlapping looks better
                t.pos(self.epoch, after=self.right, top=self.resolution, bottom=epochbottom)
                t.pos(self.views, below=self.epoch, height=viewsheight, width=40, y_margin=-1)

            else:
                t.pos(self.epoch, top=self.resolution, bottom=epochbottom)
                t.pos(self.views, below=self.epoch, height=viewsheight, width=40, y_margin=-1)

            t.pos(self.times_completed, coat=self.views, below=self.views)
            t.pos(self.times_completed, top=self.times_completed, bottom=self, height=self.times_completed, add=1)
            t.pos(self.views, height=self.views, add=1)

            lazy_swap(self)

        def make_added_widget(self):
            """
            this indicates when the torrent was posted at BIT-HDTV.com, instead of showing the
            actual date among all other digits that are there that may just make things to noisy.
            i've made it so that there are dots, bars and lines that gives a special kind of view
            for how long the torrent has been up there.

            tooltip gives the exact date
            """
            class AddedBackplate(SortingThingey, GODLabel):
                """ clickable """
            self.epoch = AddedBackplate(place=self, parent=self, qframebox=True, sortvar='added')
            self.epoch.added = False
            t.pos(self.epoch, width=40)

        def change_added_data(self):
            if self.epoch.added:
                [t.close_and_pop(self.epoch.added[k]) for k,v in self.epoch.added.items()]

            data = self.parent.data['results'][0]
            if data['download_multiplier'] == 0 and data['upload_multiplier'] == 1:
                t.style(self.epoch, background=FL_EPOCH, color=BLACK)
            elif data['upload_multiplier'] == 2:
                t.style(self.epoch, background=FL2x_EPOCH, color=BLACK)
            else:
                t.style(self.epoch, background=NRM_RESOLUTION, color=BLACK)

            # generate vars and integers
            added = self.parent.data['results'][0]['added']
            pattern = '%Y-%m-%dT%H:%M:%S'
            epoch = int(time.mktime(time.strptime(added[0:-6], pattern)))
            years = int((time.time() - epoch) / 31556926)
            months = int((time.time() - epoch) / 2629743)
            weeks =  int((time.time() - epoch) / 604800)
            days = int((time.time() - epoch) / 86400)
            hours = int((time.time() - epoch) / 3600)

            class EPOCH(GODLabel):
                def __init__(self, tooltip=None, size=[3,3], *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    t.pos(self, size=size)
                    if tooltip:
                        self.setToolTip(str(tooltip))

            self.added = dict(years=[], months=[], days=[], hours=[])

            def proxy(self, container, size=[0,2], below=None, move=[2,2]):
                if container:
                    return

                tmp = EPOCH(place=self.epoch, size=size)

                if below: t.pos(tmp, below=below)
                else: t.pos(tmp, move=move)

                container.append(tmp)

            def generate_things(epoch, years, months):
                daysleft = epoch + (years * 31556926) + ((months - (years * 12)) * 2629743)
                daysleft = time.time() - daysleft
                days_round = int(daysleft / 86400)
                hours_left = ((daysleft / 86400) - days_round) * 24
                return daysleft, days_round, hours_left

            def make_years(self, years):
                for i in range(years):
                    year = datetime.datetime.now().year
                    year = EPOCH(place=self.epoch, tooltip=year - years + i, qframebox=True)
                    t.style(year, background='cyan', color=BLACK)

                    if not self.added['years']:
                        t.pos(year, move=[2,2])
                    else:
                        t.pos(year, coat=self.added['years'][-1], after=self.added['years'][-1], x_margin=1)

                    self.added['years'].append(year)
                proxy(self, self.added['years'], size=[0,3])

            def make_months(self, months):
                for i in range(months - (years * 12)):
                    month = EPOCH(place=self.epoch, size=[2,2], qframebox=True)
                    t.style(month, color=BLACK)

                    if not self.added['months']:
                        t.pos(month, below=self.added['years'][0], y_margin=1)
                    else:
                        t.pos(month, coat=self.added['months'][-1], after=self.added['months'][-1], x_margin=1)

                    self.added['months'].append(month)
                proxy(self, self.added['months'], size=[0, 3], below=self.added['years'][0])

            def make_days(self, epoch, years, months):
                daysleft, days_round, hours_left = generate_things(epoch, years, months)
                if days_round:
                    w = (36 / 30.5) * days_round
                    day = EPOCH(place=self.epoch, qframebox=True)
                    t.style(day, background=GRAY, color=BLACK)
                    t.pos(day, below=self.added['months'][0], y_margin=1, width=w)
                    self.added['days'].append(day)

                proxy(self, self.added['days'], size=[0, 2], below=self.added['months'][0])

            def make_hours(self, epoch, years, months):
                daysleft, days_round, hours_left = generate_things(epoch, years, months)

                if hours_left:
                    w = (36 / 24) * hours_left
                    hour = EPOCH(place=self.epoch, qframebox=True)
                    t.style(hour, background=GRAY, color=BLACK)
                    t.pos(hour, below=self.added['days'][0], y_margin=1, width=w)
                    self.added['hours'].append(hour)

            make_years(self, years)
            make_months(self, months)
            make_days(self, epoch, years, months)
            make_hours(self, epoch, years, months)

            added = added.split('T')
            self.epoch.setToolTip(added[0] + ' -> ' + added[1][0:-9])
            self.epoch.added = self.added

    # <<======ABOVE:ME=======<{ [       CLASS.SNATCHVIEWCOMMENT     ] ==============================<<
    # <<======ABOVE:ME=======<{ [           CLASS.TOOLPLATE         ] ==============================<<
    # >>======================= [         CLASS.RATINGWIDGET        ] }>============BELOW:ME========>>

    class RatingWidget(GODLabel):
        """ IMDb rating from local database, not from scrapping """
        def __init__(self, *args, **kwargs):
            self.rating = False
            self.children = []
            super().__init__(*args, **kwargs)
            self.parent.show_my_rating = self.show_my_rating
            self.vertical_name = self.parent.vertical_name
            self.expand_self = self.parent.expand_self

        def position_blocks(self):
            each = int((self.width() - (len(self.children) - 1)) / len(self.children))
            rest = (self.width() - (len(self.children) - 1)) - (each * len(self.children))
            for count in range(len(self.children)):

                current = self.children[count]

                if rest < 1:
                    bonus = 0
                else:
                    bonus = 1
                    rest -= 1

                if count == 0:
                    t.pos(current, left=0, top=0, height=self, width=each + bonus)
                else:
                    prev = self.children[count - 1]
                    t.pos(current, height=prev, after=prev, x_margin=1, width=each + bonus)

                if current.extra and current.extra.small_rating:
                    w = current.width() * current.extra.small_rating
                    t.pos(current.extra, inside=current, margin=1, width=w)

        def gather_rating(self, db_input):
            data = sqlite.execute('select * from ratings where tconst = (?)', values=db_input[DB.titles.tconst])
            if data:
                self.rating = data
                t.pos(self, height=t.config('cover_height') * 0.02)
            else:
                self.rating = -1

        def create_rating_blocks(self):
            full_rating = int(self.rating[DB.ratings.average])
            small_rating = self.rating[DB.ratings.average] - full_rating

            for i in range(1, 11):
                label = GODLabel(place=self)
                label.setFrameShape(QtWidgets.QFrame.Box)
                label.setLineWidth(1)
                self.children.append(label)

                if i <= full_rating:
                    t.style(label, background=TEXT_WHITE, color=BLACK)
                else:
                    t.style(label, background=GRAY, color=BLACK)

                if small_rating and full_rating + 1 == i:
                    label.extra = GODLabel(place=label)
                    label.extra.small_rating = small_rating
                    t.style(label.extra, background=TEXT_WHITE)
                else:
                    label.extra = False

        def show_my_rating(self):
            if not self.rating or self.rating == -1: # -1 meaning have tried once to find rating
                self.hide()
                return
            else:
                self.show()

            if not self.children:
                self.create_rating_blocks()

            self.expand_self()
            self.vertical_name.draw_text()
            self.position_blocks()

    # <<======ABOVE:ME=======<{ [         CLASS.RATINGWIDGET        ] ==============================<<
    # >>======================= [               COVER               ] }>============BELOW:ME========>>

    def set_cover(self, refresh=False):
        """ its a bit messy here, the logic is broken but the fn works for now """
        def now_set_cover(self, db_input=None):
            if not self.cover_path and db_input:
                self.cover_path = self.get_cover_from_cache(db_input=db_input)

            if self.cover_path and os.path.exists(self.cover_path):
                size = self.cover.width(), self.cover.height()
                pixmap = QPixmap(self.cover_path).scaled(size[0], size[1], transformMode=QtCore.Qt.SmoothTransformation)
                self.cover.clear()
                self.cover.setPixmap(pixmap)
            else:
                t.style(self.cover, background='rgb(25,25,25)')

            self.showing_pixmap = True  # todo tecnically not always, can also indicate we're done trying
            self.resize_scrollcanvas()

        def download_cover_then_set(self, db_input):
            self.cover_path = self.get_cover_from_cache(db_input, download=True)
            now_set_cover(self, db_input)

        if self.showing_pixmap and not refresh:
            return

        elif 'imdb' in self.data and not self.cover_path or refresh:
            db_input = self.data['imdb'][0]
            self.cover_path = self.get_cover_from_cache(db_input=db_input)

            if not self.cover_path:
                t.start_thread(
                    slave_fn=self.download_imdb_cover,
                    slave_kwargs=dict(db_input=db_input),
                    master_fn=download_cover_then_set,
                    master_args=(self, db_input,)
                )
                return

        now_set_cover(self)


    def identify_imdb_by_filename(self):
        """
        signals back for next job

        this is probably the one fn that needs the most cleaning since to much happens here.

        if IMDb isnt present it tries to figure out what type of IMDb the filename/torrentname should represent
        and if thats figured out its stored into cache so we dont haveto figure out everytime, there can be a
        bad effect from doing this and maybe we should add a way to reset the cache in the future.

        # todo maybe overlook a reset cache thingey
        """
        def identify_from_filename(self):
            imdb = 'imdb.com/title/'

            if self.data['link'].find(imdb) > -1:
                cut = self.data['link'].find(imdb)
                tconst = self.data['link'][cut+len(imdb):].rstrip('/')
                data = sqlite.execute('select * from titles where tconst is (?)', tconst)
                if data:
                    self.data['imdb'] = [data]
                    return [data]

            tmp = sqlite.execute('select * from cache where torrent_id = (?)', self.data['results'][0]['id'])
            if tmp:
                if tmp and not tmp[DB.cache.tconst]:
                    return

                for count, i in enumerate(tmp[DB.cache.tconst].split(',')):
                    if count > 10: break

                    data = sqlite.execute('select * from titles where tconst = (?)', i)
                    if data:
                        if 'imdb' not in self.data: self.data['imdb'] = []
                        self.data['imdb'].append(data)

                if 'imdb' in self.data:
                    return self.data['imdb']

            path = self.data['results'][0]['name']

            episode, cut = self.get_episode(path, cut=len(path))
            years, cut = self.get_years(path, cut)
            name = self.get_name(path, cut)
            data = self.fetch_data(years, episode)
            data = t.straight_search(data, name, DB.titles.title)

            query, values = sqlite.empty_insert_query('cache')
            values[DB.cache.torrent_id] = self.data['results'][0]['id']

            if data:
                # logic is that least None's is good and sorts list so
                tmp = [(x, len([y for y in x if not y])) for x in data]
                tmp.sort(key=lambda x:x[1])
                self.data['imdb'] = [tuple(x[0]) for x in tmp]
                values[DB.cache.tconst] = ','.join([x[DB.titles.tconst] for x in self.data['imdb']]) # saves cache

            sqlite.execute(query, values=values)
            return data

        data = identify_from_filename(self)

        def start_next_job():
            signal = t.signals(name='primary')
            signal.finished.emit()
            t.signal_highlight()

        if data:
            def another_hack(self):
                self.change_genre_figrues()
                self.add_imdb_link_button()
                self.add_gather_all_button()
                self.add_next_imdb_button()
                self.show_my_rating()
                self.set_cover()
                t.start_thread(dummy=True, slave_args=0.025, master_fn=start_next_job)

            tmp = sqlite.execute('select * from skiplist where tconst = (?)', data[0][DB.titles.tconst])
            if tmp:
                signal = t.signals(name='primary')
                signal.error.emit(dict(exclude=self))
                return

            self.rating_widget.gather_rating(data[0]) # todo avoid these hacks

            if not self.get_cover_from_cache(db_input=data[0], download=False): # False, dont want to use main thread
                t.start_thread(self.download_imdb_cover,
                               slave_kwargs=dict(db_input=(data[0])), master_fn=another_hack, master_args=self)
            else:
                another_hack(self)
        else:
            self.set_cover()
            t.start_thread(dummy=True, slave_args=0.025, master_fn=start_next_job)

    # <<======ABOVE:ME=======<{ [                COVER              ] ==============================<<

    def change_torrent(self, forward=True, show_current=False):
        self.expand_self()

        if len(self.data['results']) == 1 or show_current:
            pass # all good showing current or the only one
        elif forward:
            self.data['results'].append(self.data['results'][0])
            self.data['results'].pop(0)

            if self.vertical_showing['current'] >= self.vertical_showing['total']:
                self.vertical_showing['current'] = 1
            else:
                self.vertical_showing['current'] += 1
        else:
            self.data['results'].insert(0, self.data['results'][-1])
            self.data['results'].pop(-1)
            if self.vertical_showing['current'] <= 1:
                self.vertical_showing['current'] = self.vertical_showing['total']
            else:
                self.vertical_showing['current'] -= 1

        if len(self.data['results']) > 1:
            tooltip = f"Showing torrent {self.vertical_showing['current']} of {self.vertical_showing['total']}"
            self.toolplate.right.setToolTip(tooltip)

        for i in self.vertical_name.cycle:
            if i['type'] == 'filename':
                i['text'] = self.data['results'][0]['name']

        self.vertical_name.draw_text()

        self.change_resoution()
        self.show_file_size()
        self.change_added_data()
        self.change_genre_figrues()
        self.change_seeders_leechers()
        self.update_views_comments_timescompleted(data=self.data['results'][0])
        self.show_my_rating()
        self.toolplate.update()
        self.show_episode_badge()
        self.toggle_large_name_label()
        t.signal_highlight()

    def show_episode_badge(self):
        if not t.config('show_s01e01'):
            return

        episode, _ = self.get_episode(self.data['results'][0]['name'], 0)
        if not episode:
            return

        if not self.episode_label:
            self.episode_label = GODLabel(place=self, qframebox=True, center=True)

        self.episode_label.setText(episode[0])
        t.style(self.episode_label, background=YELLOW, color=BLACK, font=12)
        t.shrink_label_to_text(self.episode_label, x_margin=10, y_margin=6)
        t.pos(self.episode_label, right=self.cover, top=self.cover, x_margin=2, y_margin=2)

    def change_genre_figrues(self):
        if not 'imdb' in self.data:
            return

        db_input = self.data['imdb'][0]
        data = sqlite.engine.execute("PRAGMA table_info('titles')")
        columns = [x[1] for x in data]
        self.genres = []

        s = {'id', 'tconst', 'type', 'title', 'start_year', 'end_year', 'runtime'}
        self.genres = [columns[count] for count, x in enumerate(db_input) if x == True and columns[count] not in s]

        if self.genres:
            for i in self.vertical_name.cycle:
                if i['type'] == 'genre':
                    i['text'] = ' / '.join(self.genres)

    def change_resoution(self):
        resolution = self.data['results'][0]['resolution']
        fields = self.get_fields()
        data = self.data['results'][0]

        if data['download_multiplier'] == 0 and data['upload_multiplier'] == 1:
            t.style(self.resolution, background=FL_RESOLUTION, color=BLACK)
        elif data['upload_multiplier'] == 2:
            t.style(self.resolution, background=FL2x_RESOLUTION, color=BLACK)
        else:
            t.style(self.resolution, background=NRM_RESOLUTION, color=BLACK)

        for k,v in fields.resolution.items():
            if v == resolution:
                self.resolution.setText(k)
                return

    def show_file_size(self):
        data = self.data['results'][0]
        if data['download_multiplier'] == 0 and data['upload_multiplier'] == 1:
            t.style(self.filesize, background=FL_FILESIZE, color=BLACK)
        elif data['upload_multiplier'] == 2:
            t.style(self.filesize, background=FL2x_FILESIZE, color=BLACK)
        else:
            t.style(self.filesize, background=NRM_FILESIZE, color=DARK_BACK)

        self.filesize.setText(data['size'])

    def change_seeders_leechers(self):
        data = self.data['results'][0]

        self.seeders_digit.setText(str(data['seeders']))
        if data['seeders']:
            t.style(self.seeders_digit, background=HIGH_GREEN, color=BLACK, font=8)
        else:
            t.style(self.seeders_digit, background=LIGHT_GRAY, color=BLACK, font=8)

        self.leechers_digit.setText(str(data['leechers']))
        if data['leechers']:
            t.style(self.leechers_digit, background='magenta', color=BLACK, font=8)
        else:
            t.style(self.leechers_digit, background=LIGHT_GRAY, color=BLACK, font=8)

        self.seeders_leechers.data = dict(seeders=data['seeders'], leechers=data['leechers'])

    def reposition_large_stuff(self):
        t.pos(self.vertical_name, height=self)
        t.pos(self.toolplate, width=self.cover, after=self.vertical_name)
        t.pos(self.cover, below=self.toolplate)

        if self.rating_widget.children:
            t.pos(self.rating_widget, width=self.cover, below=self.cover)

    def expand_self(self):
        w = self.vertical_name.width() + self.cover.width()
        h = self.cover.height() + self.toolplate.height()

        if self.rating_widget.children:
            h += self.rating_widget.height()

        t.pos(self, size=[w,h])
        self.reposition_large_stuff()

    def toggle_fortification(self):
        """ prevents the widget from closing and upon each redraw fortified widgest are drawn first """
        if self.fortified:
            if self.tagged: self.tagged.close()
            if self.downloadlabel: self.downloadlabel.close()
            if self.skiplabel: self.skiplabel.close()
            self.skiplabel = False
            self.tagged = False
            self.downloadlabel = False
            self.fortified = False
        else:
            self.fortified = True
            self.tagged = GODLabel(place=self.cover, qframebox=True, center=True)
            self.tagged.setText('FORTIFIED')
            self.tagged.setToolTip('Will be kepts and redrawn at each page-refresh')
            t.pos(self.tagged, width=self.cover, height=30, move=[0, self.cover.height() - 60])
            t.style(self.tagged, background=TITLE_WHITE, color=DARK_BACK)
            t.correct_broken_font_size(self.tagged, x_margin=10, y_margin=4)
            self.toggle_download_label()
            self.toggle_skiplabel()

    class DownloadLabel(GODLabel, GLOBALHighLight):
        """ visable above fortified-label """
        def __init__(self, *args, **kwargs):
            super().__init__(
                deactivated_on=dict(background='cyan', color=BLACK),
                deactivated_off=dict(background='darkCyan', color=BLACK),
                *args, **kwargs
            )
            self.setText('DOWNLOAD')
            t.correct_broken_font_size(self, x_margin=10, y_margin=2)

        def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
            webbrowser.open('https://www.bit-hdtv.com/download.php?id=' + str(self.data['results'][0]['id']))

    class SkipLabel(GODLabel, GLOBALHighLight):
        """ visable below fortified-label """
        def __init__(self, *args, **kwargs):
            super().__init__(
                deactivated_on=dict(background=HIGH_RED, color=BLACK),
                deactivated_off=dict(background=DEACTIVE_RED, color=BLACK),
                *args, **kwargs
            )
            self.setText('EXCLUDE FROM FUTURE BROWSING')
            self.setToolTip('Almost irreversable!')
            t.correct_broken_font_size(self, x_margin=10, y_margin=2)

        def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
            query, values = sqlite.empty_insert_query('skiplist')

            if 'imdb' in self.data:
                tconst = self.data['imdb'][0][DB.titles.tconst]
                values[DB.skiplist.tconst] = tconst

            torrent_id = self.data['results'][0]['id']
            values[DB.skiplist.torrent_id] = torrent_id
            sqlite.execute('delete from skiplist where torrent_id = (?)', torrent_id)
            sqlite.execute(query, values=values)
            self.setText('SKIPPED FOREVER!')

    def toggle_download_label(self):
        if self.downloadlabel:
            return

        self.downloadlabel = self.DownloadLabel(place=self.cover, qframebox=True, center=True, mouse=True)
        self.downloadlabel.data = self.data
        t.pos(self.downloadlabel, coat=self.tagged, height=self.tagged.height() * 0.7, above=self.tagged)

    def toggle_skiplabel(self):
        if self.skiplabel:
            return

        self.skiplabel = self.SkipLabel(place=self.cover, qframebox=True, center=True, mouse=True)
        self.skiplabel.data = self.data
        t.pos(self.skiplabel, coat=self.tagged, height=self.tagged.height() * 0.7, below=self.tagged)

    def toggle_large_name_label(self):
        if not t.config('dev_mode') or not self.tagged:
            if self.large_name_label:
                self.large_name_label.close()
            return

        if not self.large_name_label:
            self.large_name_label = GODLabel(place=self.main.scrollcanvas_main, qframebox=True)
            self.large_name_label.setStyleSheet(self.tagged.styleSheet())
            self.tagged.setText("")

        text = self.data['results'][0]['name']
        self.large_name_label.setText(text)
        t.shrink_label_to_text(self.large_name_label, x_margin=10)
        t.pos(self.large_name_label, height=self.tagged)
        self.position_large_name_label()

    def position_large_name_label(self):
        x = (self.large_name_label.width() - self.width()) * 0.5
        y = self.height() - (self.height() - self.tagged.geometry().top() - self.toolplate.height())
        t.pos(self.large_name_label, top=self, left=self, move=[-x, y])
        self.large_name_label.raise_()

    def drag_widget(self, ev):
        if not self.old_position:
            self.old_position = ev.globalPos()

        delta = QtCore.QPoint(ev.globalPos() - self.old_position)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.old_position = ev.globalPos()

        if self.large_name_label and self.tagged:
            self.position_large_name_label()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if self.large_name_label:
            self.large_name_label.close()

    def mouseMoveEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.drag_widget(ev)

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.raise_()
        if self.large_name_label:
            self.large_name_label.raise_()

        self.old_position = ev.globalPos()

        if ev.button() == 2:
            self.toggle_fortification()
            self.toggle_large_name_label()
            t.signal_highlight()

