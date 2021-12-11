from bscripts.database_stuff import DB, sqlite
import sys, subprocess, os

def api_calls(self):
    orders = sys.argv[1:]
    if '-save-skiplist' in orders and '--pastebinner-path' in orders:
        for count, i in enumerate(orders[0:-1]):
            if i == '--pastebinner-path':
                path = orders[count+1]
                if not os.path.exists(path):
                    print(f'Error: "{path}" does not exists')
                    return False

                text = []
                data = sqlite.execute('select * from skiplist', all=True)
                for i in data:

                    if i[DB.skiplist.tconst] and i[DB.skiplist.tconst] not in text:
                        text.append(i[DB.skiplist.tconst])
                    if i[DB.skiplist.torrent_id] and i[DB.skiplist.torrent_id] not in text:
                        text.append(str(i[DB.skiplist.torrent_id]))

                if text:
                    print(f"Found {len(text)} skipdatas that's being sent to Pastebinner title: _bithdtv_skiplist")
                    text = ",".join(text)
                    subprocess.call(f'python3 "{path}" -r -n --header "_bithdtv_skiplist" --text "{text}"', shell=True)
                    print("JOBS DONE!")
                    break
                else:
                    print("Skiplist empty?")


def api_help_print():
    longlen = 0
    d = []
    d.append(dict(key='USAGE', text='python3 bithdtv.py -save-skiplist --pastebinner-path "/home/user/pb.py"'))
    d.append(dict(key='-save-skiplist', text='saves skiplist to pastebinner'))
    d.append(dict(key='--pastebinner-path', text='pastebinners script path (python file)'))

    for dd in d:
        if len(dd['key']) >= longlen:
            longlen = len(dd['key']) + 1

    for dd in d:
        print(dd['key'], " " * (longlen - len(dd['key'])), dd['text'])