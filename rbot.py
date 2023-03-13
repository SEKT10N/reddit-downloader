from http.client import NON_AUTHORITATIVE_INFORMATION
import os, sys
import re
import requests
import urllib.request
import json
from tempfile import gettempdir
from subprocess import DEVNULL, STDOUT, check_call
import webbrowser

WIDTH = os.get_terminal_size().columns
EXISTS = os.path.exists
MKDIR = os.makedirs
OAUTH_URL = 'https://oauth.reddit.com/'

OPTIONS = {
    1 : "Download Saved Posts",
    2 : "Download Wallpapers",
    3 : "Random Joke from r/jokes",
    4 : "Download Posts from a Subreddit/User Account",
    5 : "Download from Link",
}
OPTIONS2 = {
    1 : "New Posts",
    2 : "Hot Posts",
}

def authenticate(client_id, secret, appname, username, password):
    global headers
    auth = requests.auth.HTTPBasicAuth(client_id, secret)
    creds = {
        'grant_type':'password',
        'username': username,
        'password': password,
    }
    headers = {'User-Agent': appname}
    req = requests.post('https://www.reddit.com/api/v1/access_token', auth=auth, data=creds, headers=headers)
    TOKEN = req.json()['access_token']
    headers = {**headers, **{'Authorization': f"bearer {TOKEN}"}}

def postType(post):
    try:
        if post["selftext"] == "[deleted]":
            return 'deleted!'
        if 'post_hint' in post:
            if 'image' in post['post_hint']:
                return 'image'
            if 'link' in post['post_hint']:
                if post['url'].endswith('.gifv') or post['url'].endswith('.mp4'):
                    return 'video'
                elif post['url'].endswith('.jpg') or post['url'].endswith('.jpeg') or post['url'].endswith('.png'):
                    return 'image'
                return 'link'
            if 'video' in post['post_hint']:
                return 'video'
            return "Text"
        elif post['is_video']:
            if post['preview']['reddit_video_preview']['is_gif'] or post['media']['reddit_video']['is_gif']:
                return 'gif'
            return "video"
        elif post['is_gallery']:
            return "gallery"
        else:
            return "text"
    except KeyError:
        pass
    return "text"

def download(link, rname, index):
    os.chdir(download_path)
    if not EXISTS(rname.capitalize()):
        MKDIR(rname)
    post_type = postType(link['data'])
    name = re.sub('[<>:"/\|?*.]', '', link['data']['title'])
    name = re.sub('amp;', '', name)
    global url
    
    if post_type == 'image':
        url = link['data']['url']
        extension = os.path.basename(url).split('.')[1]
        extension = extension.split('?')[0] if '?' in extension else extension
        if not EXISTS(f"{rname}\{name}.{extension}"):
            print(f"Downloading {index}: {rname}\{name}.{extension}")
            urllib.request.urlretrieve(url, f"{rname}\{name}.{extension}")
    
    elif post_type == 'gallery':
        items = link['data']['gallery_data']['items']
        if not EXISTS(f"{rname}\{name}"):
            MKDIR(f"{rname}\{name}")
        for i in range(len(items)):
            media_id = items[i]['media_id']
            url = re.sub('amp;', '', link['data']['media_metadata'][media_id]['s']['u'])
            file_name = os.path.basename(url).split('?')[0]
            if not EXISTS(f"{rname}\{name}\{file_name}"):
                print(f"Downloading {index}=>{i+1}: {rname}\{name}\{file_name}")
                urllib.request.urlretrieve(url, f"{rname}\{name}\{file_name}")
    
    elif post_type == 'video' or post_type == 'gif':
        if not EXISTS(f"{rname}\Videos"):
            MKDIR(f"{rname}\Videos")
        try:
            url = link['data']['preview']['reddit_video_preview']['fallback_url'] or link['data']['media']['reddit_video']['fallback_url'].split('?')[0]
        except KeyError:
            #url = link['data']['media']['reddit_video']['fallback_url'].split('?')[0]
            pass
        extension = os.path.basename(url).split('.')[-1]
        if not EXISTS(f"{rname}\Videos\{name}.{extension}"):
            print(f"Downloading {index}: {rname}\Videos\{name}.{extension}")
            urllib.request.urlretrieve(url, f"{rname}\Videos\{name}.{extension}")
    
    elif post_type == 'link':
        if open_links == 'true':
            webbrowser.open(link['data']['url'], new=2)
        else:
            print(link['data']['url'])
    else:
        return None
    
    return True

def tellJoke(link):
    post_type = postType(link['data'])
    if post_type == "text":
        os.system('cls')
        title = re.sub('amp;', '', link['data']['title'])
        selftext = re.sub('amp;', '', link['data']['selftext'])
        print(f"{title}\n\n{selftext}")
    
def main():
    os.system('cls || clear')
    os.chdir(os.path.dirname(__file__))

    with open('config.json', 'r') as f:
        CONFIG = json.load(f)

    authenticate(CONFIG['client_id'], CONFIG['secret'], CONFIG['appname'], CONFIG['username'], CONFIG['password'])
    global open_links, download_path 
    open_links = CONFIG['options']['open_imgur_links'].lower()
    download_path = CONFIG['download_path']
    if not EXISTS(download_path):
        MKDIR(download_path)
        
    print("".center(WIDTH // 2, "="))
    print(" Welcome to Reddit Bot ".center(WIDTH // 2, "="))
    print("".center(WIDTH // 2, "="))

    while True:
        IN_URL = ""
        print("\nSelect an option:")
        for i, val in OPTIONS.items():
            print(f" {i}: {val}")
        
        choice = input("> ").strip()
        if choice == '1':
            IN_URL = f"{OAUTH_URL}/user/{CONFIG['username']}/saved"
            subr = "saved"
        elif choice == '2':
            IN_URL = f"{OAUTH_URL}r/wallpapers/new"
            subr = "wallpapers"
            limit = int(input("Maximum number of posts to download [Default: 25]: ") or 25)
        elif choice == '3':
            IN_URL = f"{OAUTH_URL}r/jokes/random"
            response = requests.get(IN_URL, headers=headers).json()[0]['data']['children']
            tellJoke(response[0])
            continue
        elif choice == '4':
            subr = input('Enter Subreddit/Username [prefixed with r/ and u/ respectively]: ').lower()
            for i, val in OPTIONS2.items():
                print(f"{i}: {val}")
            choice = int(input("> "))
            if choice == 1:
                IN_URL = f"{OAUTH_URL}{subr}/new"
                limit = int(input("Maximum number of posts to download [Default: 25]: ") or 25)
            elif choice == 2:
                IN_URL = f"{OAUTH_URL}{subr}/hot"
                limit = int(input("Maximum number of posts to download [Default: 25]: ") or 25)    
            response = requests.get(IN_URL, headers=headers, params={'limit': limit}).json()['data']['children']
            for i, r in enumerate(response, start=1):
                if subr.startswith('u'):
                    subr = subr.replace('u/','')
                download(r, subr, i)
            continue
        elif choice == '5':
            rlink = input("Post Link: ")
            rlink = re.sub(r'//www.', '//oauth.', rlink)
            response = requests.get(rlink, headers=headers).json()[0]['data']['children']
            for r in response:
                download(r, r['data']['subreddit'], 1)
            continue
        elif choice.lower() == 'clear':
            os.system('cls')
        elif choice.lower() == 'exit':
            sys.exit()
        else:
            continue
        
        if IN_URL:
            response = requests.get(IN_URL, headers=headers, params={'limit': '100'}).json()['data']['children']
            for i, r in enumerate(response, start=1):
                try:
                    download(r, subr, i)
                except KeyboardInterrupt:
                    continue

try:
    if __name__ == "__main__":
        main()
except KeyboardInterrupt:
    pass