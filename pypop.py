import json
import PySimpleGUI as sg
from PIL import Image, ImageDraw
from urllib.request import urlopen, Request
import urllib.parse as urlparse
from qbittorrent import Client
import time, io, concurrent.futures
import os
import re





setting_column_limit = 10
setting_row_limit = 5
setting_limit = setting_column_limit * setting_row_limit
ip = 'http://192.168.1.66'
port = 8080
qb_username='admin'
qb_password='adminadmin'

def make_column(img_list,name_list):
    col = [None]*(len(img_list)+len(name_list))
    col[::2] = img_list
    col[1::2] = name_list
    return col

def parall(func, array, size, n_process=16):
    executor = concurrent.futures.ThreadPoolExecutor(n_process)
    futures = [executor.submit(func, group, size) for group in array]
    concurrent.futures.wait(futures)
    return [future.result() for future in futures]

def get_img(url, size):
    req_img = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        img = Image.open(urlopen(req_img))
        img = img.resize(size)
        imgio=io.BytesIO()
        img.save(imgio, quality=20, format="PNG")
        del img
        return imgio.getvalue()
    except:
        img = Image.new('RGB', size, color = "red")
        d = ImageDraw.Draw(img)
        d.text((10,10), "Can't find image", fill=(0,0,0))
        imgio=io.BytesIO()
        img.save(imgio, quality=20, format="PNG")
        del img, d
        return imgio.getvalue()

def list_movies(query_term='0', quality='all', limit=setting_limit, genre='all', sort_by="date_added", page=1):
    query_url = urlparse.quote('https://yts.mx/api/v2/list_movies.json?query_term='+query_term+'&quality='+quality+'&limit='+str(limit)+'&genre='+genre+'&sort_by='+sort_by+'&page='+str(page),
    safe='/:&=?')
    req_db = Request(query_url, headers={'User-Agent': 'Mozilla/5.0'})
    rep_db = urlopen(req_db)
    db = json.load(rep_db)
    #print(db)
    if db['data']['movie_count']==0 or (page!=1 and db['data']['movie_count']/(limit * (page - 1)) < 1):
        return []
    else:
        return [movies for movies in db['data']['movies']]

def qb_connect(ip_address=ip, port=port, username=qb_username, password= qb_password):
    qb = Client(str(ip_address) + ':' + str(port) + '/')
    qb.login(qb_username, qb_password)
    return qb

def download_torrent(url, category='', **kwargs):
    qb = qb_connect(**kwargs)
    qb.download_from_link(url, savepath=cache_path, category=category)
    time.sleep(1.5)
    qb.toggle_sequential_download([torrent['hash'] for torrent in qb.torrents(category=category)])

def get_torrents(category='',**kwargs):
    qb = qb_connect(**kwargs)
    return qb.torrents(category=category)

def get_movie(id):
    query_url = urlparse.quote('https://yts.mx/api/v2/movie_details.json?movie_id='+str(id),
    safe='/:&=?')
    req_db = Request(query_url, headers={'User-Agent': 'Mozilla/5.0'})
    rep_db = urlopen(req_db)
    db = json.load(rep_db)
    return db

def search_movie(query_term, url_api='https://sg.media-imdb.com/suggests/'):
    url= url_api + query_term[0] + '/' + urlparse.quote(query_term) + '.json'
    search_req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    search_db = urlopen(search_req)
    text_db = [line.decode('utf-8') for line in search_db][0]
    db = json.loads(text_db[len(re.search('(imdb\$[a-zA-Z_1-9]*)\w', text_db).group(0))+1:-1])
    movie_db = [list_movies(query_term=movie['id'], limit=1) for movie in db['d']]
    return [movies[0] for movies in movie_db if len(movies)>0]

def update_table(window, db):
    db_img = parall(get_img, [movie['medium_cover_image'] for movie in db], (int(img_width) , int(img_width * 1.5)))
    for key, movie in enumerate(db):
        window["text_"+str(key)].update(movie['title'], visible=True)
        window["img_"+str(key)].update(image_data=db_img[key], visible=True)
    for i in range(len(db), setting_limit):
        window["text_"+str(i)].update(visible=False)
        window["img_"+str(i)].update(visible=False)

def create_movie_window(movie):
    layout_popup = [
            [
                sg.T(movie['title'], font = 'helvetica 30')
            ],
            [
                sg.Image(data=get_img(movie['large_cover_image'], (500,750))),
                sg.Multiline(movie['summary'], size = (33,10), disabled=True, background_color=sg.theme_background_color(),autoscroll=True,font=30,)
            ],
            [
                sg.B('close'), sg.B('download')
            ]
        ]
    window = sg.Window(title=movie['title'], layout=layout_popup)
    return window

def create_quality_popup(movie):
    qual_disp = [torrent['quality'] for torrent in movie['torrents']]
    window = sg.Window('Choose a quality', [
        [
            sg.Text('Select one->'),
            sg.Combo(qual_disp, size=(20, 1), key='quality', background_color=sg.theme_background_color(), default_value=qual_disp[-1])
        ],
        [
            sg.B('ok'),
            sg.B('Cancel')
        ]
    ])
    return window



window = sg.Window('temp',layout=[[]])
screen_size = [1920, 1080] #window.get_screen_dimensions()
window.close()
del window
db = list_movies()
page = 1
img_width = (float(screen_size[0]) * 0.85) / float(setting_column_limit)
db_img = parall(get_img, [movie['medium_cover_image'] for movie in db], size=(int(img_width) , int(img_width * 1.5)))



layout = [
    [
        sg.InputText(key='_QUERY_TERM_'),
        sg.Button('search'),
        sg.T('quality'),
        sg.Combo(['720p', '1080p', '2160p', '3D', 'all'], key='_QUALITY_', default_value='all', enable_events=True),
        sg.T('genre'),
        sg.Combo(['Action','Adventure','Animation','Biography','Comedy','Crime','Documentary','Drama','Family','Fantasy','Film Noir',
        'History','Horror','Music','Musical','Mystery','Romance','Sci-Fi','Short','Sport','Superhero','Thriller','War','Western','all'],
        key='_GENRE_', default_value='all', enable_events=True),
        sg.T('sort by'),
        sg.Combo(['title', 'year', 'rating', 'peers', 'seeds', 'download_count', 'like_count', 'date_added'],
        default_value='date_added', key='_SORT_', enable_events=True),
        sg.Button('previous'),
        sg.Button('next'),
        sg.Button('downloading')
    ],
        [sg.Column([
                [sg.Column(make_column(
        [[sg.B(image_data=db_img[col_ind + row_ind * setting_column_limit], key = "img_" + str(col_ind + row_ind * setting_column_limit))] for row_ind in range(setting_row_limit)],
        [[sg.Text(db[col_ind + row_ind * setting_column_limit]['title'], key = "text_" + str(col_ind + row_ind * setting_column_limit),size=(20,2) , auto_size_text=True , justification='center')] for row_ind in range(setting_row_limit)]
        )) for col_ind in range(setting_column_limit)]], size=(screen_size[0],screen_size[1]), scrollable=True, vertical_scroll_only=True, key="scroller")]
            
    ,
    ]


window = sg.Window(title='pypop', layout=layout, size=screen_size, return_keyboard_events=True, resizable=True).finalize()

while True:

    event, values = window.read()
    
    if event == 'next':
        page += 1
    
    if event == 'previous' and page != 1:
        page -= 1

    if event not in ['next', 'previous']:
        page = 1

    if event == sg.WIN_CLOSED:
        break

    elif event in ['search', 'Return:36', '_GENRE_', 'next', 'previous', '_QUALITY_', '_SORT_']:
        db = list_movies(query_term=values['_QUERY_TERM_'],quality=values['_QUALITY_'], genre=values['_GENRE_'], sort_by=values['_SORT_'], page=page)

        if len(db) == 0:
            db = search_movie(values['_QUERY_TERM_'])
            if len(db) == 0:
                sg.popup('no movie found')
            else:
                update_table(window, db)
        else:
            update_table(window, db)
    

    elif event[0:3] == 'img':
        movie = db[int(event.split('_')[-1])]
        window_popup = create_movie_window(movie)
        event, values_popup = window_popup.read()

        if event == 'close':
            window_popup.close()
        elif event == 'download':
            window_qual = create_quality_popup(movie)
            event, values = window_qual.read(close=True)

            if event == 'ok':
                torrent = [torrent for torrent in movie['torrents'] if torrent['quality'] in values['quality']][0]
                download_torrent(torrent['url'], category='movie')
                print(torrent['hash'])
                window_qual.close()
                window_popup.close()

            else:
                window_qual.close()
                window_popup.close()


    if event == 'downloading':
        torrents = get_torrents()
        layout = [[sg.B('close')],
            [sg.Column([[sg.T(torrent['name'], size=(40,2)), sg.ProgressBar(100,key='progbar_'+str(ind), size=(60,10))] for ind, torrent in enumerate(torrents)])]
        ]
        window_down = sg.Window(title="downloading", layout=layout,).Finalize()
        closed=False
        while closed==False:
            event, values = window_down.read(timeout=1000)
            torrents = get_torrents()
            for ind, torrent in enumerate(torrents):
                window_down['progbar_'+str(ind)].update_bar(torrent['progress']*100)
            if event in ['close', sg.WIN_CLOSED]:
                closed=True
                window_down.close()
                break
            

            
        

##https://yts.mx/api/v2/list_movies.json?quality=3D
