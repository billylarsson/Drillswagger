from bscripts.sqlite_handler import SQLite
import os

sqlite = SQLite(
    DATABASE_FILENAME=os.environ['DATABASE_FILENAME'],
    DATABASE_FOLDER=os.environ['DATABASE_FOLDER'],
    DATABASE_SUBFOLDER=os.environ['DATABASE_SUBFOLDER'],
    INI_FILENAME=os.environ['INI_FILENAME'],
    INI_FILE_DIR=os.environ['INI_FILE_DIR'],
)

class DB:
    class titles:
        tconst = sqlite.db_sqlite('titles', 'tconst')
        type = sqlite.db_sqlite('titles', 'type')
        title = sqlite.db_sqlite('titles', 'title')
        start_year = sqlite.db_sqlite('titles', 'start_year', 'integer')
        end_year = sqlite.db_sqlite('titles', 'end_year', 'integer')
        runtime = sqlite.db_sqlite('titles', 'runtime', 'integer')
        # title_org = sqlite.db_sqlite('titles', 'title_org') # seems unnessesary atm
        # is_adult = sqlite.db_sqlite('titles', 'is_adult', 'bint') # genre/Adult ALMOST provides same knowledge

    class ratings:
        tconst = sqlite.db_sqlite('ratings', 'tconst')
        average = sqlite.db_sqlite('ratings', 'average', 'float')
        votes = sqlite.db_sqlite('ratings', 'votes', 'integer')

    class settings:
        config = sqlite.db_sqlite('settings', 'config', 'blob')

    class cache:
        torrent_id = sqlite.db_sqlite('cache', 'torrent_id', 'integer')
        tconst = sqlite.db_sqlite('cache', 'tconst')

    class covers:
        cover = sqlite.db_sqlite('covers', 'cover', 'blob')
        tconst = sqlite.db_sqlite('covers', 'tconst')

    class skiplist:
        tconst = sqlite.db_sqlite('skiplist', 'tconst')
        torrent_id = sqlite.db_sqlite('skiplist', 'torrent_id', 'integer')

class Translate:
    class titles:
        tconst = DB.titles.tconst
        titleType = DB.titles.type
        primaryTitle = DB.titles.title
        startYear = DB.titles.start_year
        endYear = DB.titles.end_year
        runtimeMinutes = DB.titles.runtime

    class ratings:
        tconst = DB.ratings.tconst
        averageRating = DB.ratings.average
        numVotes = DB.ratings.votes