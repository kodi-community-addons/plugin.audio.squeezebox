#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    plugin.audio.squeezebox
    Squeezelite Player for Kodi
    plugin_content.py
    plugin entry point t
'''

import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
from utils import log_msg, KODI_VERSION, log_exception, get_json
import urlparse
from urllib import quote_plus
import sys
import os
from operator import itemgetter


class PluginContent:
    '''Hidden plugin entry point providing some helper features'''
    params = {}
    win = None
    lmsplayer = None

    def __init__(self):
        self.win = xbmcgui.Window(10000)

        # initialize lms server and player object
        try:
            playerid = self.win.getProperty("lmsplayer").decode("utf-8")
            serverdetails = self.win.getProperty("lmsserver").decode("utf-8")
            while not serverdetails:
                playerid = self.win.getProperty("lmsplayer").decode("utf-8")
                serverdetails = self.win.getProperty("lmsserver").decode("utf-8")
                xbmc.sleep(500)
                log_msg("waiting for serverdetails...")

            self.playerid = playerid
            self.lmsserver = serverdetails

        except Exception as exc:
            log_exception(__name__, exc)
            xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

        # initialize plugin listing
        try:
            self.params = dict(urlparse.parse_qsl(sys.argv[2].replace('?', '').decode("utf-8")))
            log_msg("plugin called with parameters: %s" % self.params, xbmc.LOGDEBUG)
            self.main()
        except Exception as exc:
            log_exception(__name__, exc)
            xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

        # cleanup when done processing
        self.close()

    def close(self):
        '''Cleanup Kodi Cpython instances'''
        del self.win

    def main(self):
        '''main action, load correct function'''
        action = self.params.get("action", "")
        if action and hasattr(self.__class__, action):
            # launch module for action provided by this plugin
            getattr(self, action)()
        else:
            # load main listing
            self.menu()

    def albums(self):
        '''get albums from server'''
        params = self.params.get("params")
        xbmcplugin.setContent(int(sys.argv[1]), "albums")
        request_str = "albums 0 100000 tags:guxcyajlKR"
        if params:
            request_str += " %s" % params
            if "artist_id" in params:
                self.create_generic_listitem("All Tracks", "DefaultMusicSongs.png", "tracks&params=%s" % params)
        result = self.send_request(request_str)
        if result:
            for item in result.get("albums_loop"):
                self.create_album_listitem(item)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def artists(self):
        '''get artists from server'''
        params = self.params.get("params")
        xbmcplugin.setContent(int(sys.argv[1]), "artists")
        request_str = "artists 0 100000 tags:guxcyajlKR"
        if params:
            request_str += " %s" % params
        result = self.send_request(request_str)
        if result:
            for item in result.get("artists_loop"):
                self.create_artist_listitem(item)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def tracks(self):
        '''get tracks from server'''
        params = self.params.get("params","")
        xbmcplugin.setContent(int(sys.argv[1]), "songs")
        if "sql" in params:
            request_str = "tracks 0 100000 tags:dguxcyajlKAG" # somehow the request fails if the rating tag is requested
        else:
            request_str = "tracks 0 100000 tags:dguxcyajlKRAG"
        if params:
            request_str += " %s" % params
        result = self.send_request(request_str)
        if result:
            for item in result.get("titles_loop"):
                self.create_track_listitem(item)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def playlisttracks(self):
        '''get tracks from server'''
        playlistid = self.params.get("playlistid")
        xbmcplugin.setContent(int(sys.argv[1]), "songs")
        request_str = "playlists tracks 0 100000 tags:dguxcyajlKRAG playlist_id:%s" % playlistid
        result = self.send_request(request_str)
        if result:
            for item in result.get("playlisttracks_loop"):
                self.create_track_listitem(item)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def playlists(self):
        '''get playlists from server'''
        xbmcplugin.setContent(int(sys.argv[1]), "files")
        params = self.params.get("params")
        request_str = "playlists 0 100000 tags:guxcyajlKR"
        if params:
            request_str += " %s" % params
        result = self.send_request(request_str)
        if result:
            for item in result.get("playlists_loop"):
                cmd = "playlisttracks&playlistid=%s" % item["id"]
                self.create_generic_listitem(item["playlist"], "DefaultMusicPlaylists.png", cmd)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def genres(self):
        '''get genres from server'''
        xbmcplugin.setContent(int(sys.argv[1]), "files")
        params = self.params.get("params")
        request_str = "genres 0 100000 tags:guxcyajlKR"
        if params:
            request_str += " %s" % params
        result = self.send_request(request_str)
        if result:
            for item in result.get("genres_loop"):
                cmd = "tracks&params=genre_id:%s" % item["id"]
                thumb = self.get_thumb(item)
                self.create_generic_listitem(item["genre"], thumb, cmd)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
    
    def years(self):
        '''get years from server'''
        xbmcplugin.setContent(int(sys.argv[1]), "files")
        params = self.params.get("params")
        request_str = "years 0 100000 tags:guxcyajlKR"
        if params:
            request_str += " %s" % params
        result = self.send_request(request_str)
        if result:
            for item in result.get("years_loop"):
                cmd = "albums&params=year:%s" % item["year"]
                thumb = self.get_thumb(item)
                self.create_generic_listitem("%s"%item["year"], thumb, cmd)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        
    def musicfolder(self):
        '''explore musicfolder on the server'''
        xbmcplugin.setContent(int(sys.argv[1]), "files")
        params = self.params.get("params")
        request_str = "musicfolder 0 100000 tags:dguxcyajlKR"
        if params:
            request_str += " %s" % params
        result = self.send_request(request_str)
        if result:
            for item in result.get("folder_loop"):
                thumb = self.get_thumb(item)
                if item["type"] == "track":
                    item = self.get_songinfo(item["url"])
                    self.create_track_listitem(item)
                elif item["type"] == "playlist":
                    cmd = "command&params=playlist play %s" % item["url"]
                    self.create_generic_listitem("%s"%item["filename"], thumb, cmd, False)
                else:
                    cmd = "musicfolder&params=folder_id:%s" % item["id"]
                    self.create_generic_listitem("%s"%item["filename"], thumb, cmd)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def favorites(self):
        '''get favorites from server'''
        xbmcplugin.setContent(int(sys.argv[1]), "files")
        request_str = "favorites items 0 100000 want_url:1 tags:dguxcyajlKR"
        params = self.params.get("params")
        if params:
            request_str += " %s" % params
        result = self.send_request(request_str)
        if result:
            for item in result.get("loop_loop"):
                thumb = self.get_thumb(item)
                if not thumb and item["isaudio"] and "url" in item:
                    track_details = self.get_songinfo(item["url"])
                    if track_details and not track_details.get("remote"):
                        self.create_track_listitem(track_details)
                        continue
                    elif track_details:
                        thumb = self.get_thumb(track_details)
                if item["isaudio"]:
                    cmd = "command&params=" + quote_plus("favorites playlist play item_id:%s" % item["id"])
                    self.create_generic_listitem(item["name"], thumb, cmd, False)
                else:
                    cmd = "favorites&params=item_id:%s" % item["id"]
                    self.create_generic_listitem(item["name"], thumb, cmd)

        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
    
    def get_menu(self, node):
        '''grabs the menu for this player'''
        menu_items = []
        root_menu = self.send_request("menu items 0 1000 direct:1")
        for item in root_menu["item_loop"]:
            if item["node"] == node or (node == "apps" and "isApp" in item):
                actionstr = ""
                icon = self.get_thumb(item)
                if "isANode" in item and item["isANode"]:
                    actionstr = "menu&node=%s" %item["id"]
                elif "actions" in item and "go" in item["actions"]:
                    
                    # library nodes
                    if "browselibrary" in item["actions"]["go"]["cmd"]:
                        action = item["actions"]["go"]["params"]["mode"]
                        if "albums" in action:
                            action = "albums"
                        elif "tracks" in action:
                            action = "tracks"
                        elif "artists" in action:
                            action = "artists"
                        elif "bmf" in action:
                            action = "musicfolder"
                        elif "filesystem" in action:
                            continue # skip filesystem entry
                        for key, value in item["actions"]["go"]["params"].iteritems():
                            if not key in ["mode", "menu"]:
                                actionstr += "%s:%s " %(key, value.replace("%s", "1").replace(" ","[SP]"))
                        actionstr += " library_id:%s" %item["id"]
                        actionstr = "%s&params=%s" %(action, quote_plus(actionstr))
                    elif "selectVirtualLibrary" in item["actions"]["go"]["cmd"]:
                        continue # skip virtual library entry
                    elif "radios" in item["actions"]["go"]["cmd"]:
                        actionstr = "radios"
                    elif "globalsearch" in item["actions"]["go"]["cmd"]:
                        actionstr = "globalsearch"
                    elif "myapps" in item["actions"]["go"]["cmd"]:
                        actionstr = "apps"
                    elif "appgallery" in item["actions"]["go"]["cmd"]:
                        actionstr = "appgallery"
                    elif "favorites" in item["actions"]["go"]["cmd"]:
                        actionstr = "favorites"
                    else:
                        # other nodes
                        for cmd in item["actions"]["go"]["cmd"]:
                            if cmd == "items":
                                actionstr += "items 0 100000 "
                            else:
                                actionstr += "%s " %cmd
                        if "params" in item["actions"]["go"]:
                            for key, value in item["actions"]["go"]["params"].iteritems():
                                if not "menu" in key:
                                    actionstr += "%s:%s " %(key, value)
                        actionstr = "browse&params=%s" %quote_plus(actionstr)
                if actionstr:
                    menu_item = { 
                        "label": item["text"], 
                        "cmd": actionstr,
                        "icon": icon,
                        "weight": item.get("weight", 0)}
                    menu_items.append(menu_item)
        return sorted(menu_items, key=itemgetter('weight')) 
        
    def menu(self):
        node = self.params.get("node", "home")
        for item in self.get_menu(node):
            thumb = self.get_thumb(item)
            self.create_generic_listitem(item["label"], thumb, item["cmd"])
        # show sync settings in menu
        if node == "home":
            self.create_generic_listitem("Synchroniseren", "", "browse&params=syncsettings 0 100")
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        
    def search(self):
        kb = xbmc.Keyboard('', xbmc.getLocalizedString(16017))
        kb.doModal()
        if kb.isConfirmed():
            searchterm = kb.getText().replace(" ","[SP]")
            result = self.send_request("search 0 1 term:%s" %searchterm)
            if result:
                if result.get("artists_count"): #artist items
                    label = "Artists (%s)" % result["artists_count"]
                    cmd = "artists&params=search:%s" %searchterm
                    self.create_generic_listitem(label, "DefaultMusicArtists.png", cmd)
                elif result.get("contributors_count"): #artist items alt
                    label = "Artists (%s)" % result["contributors_count"]
                    cmd = "artists&params=search:%s" %searchterm
                    self.create_generic_listitem(label, "DefaultMusicArtists.png", cmd)
                if result.get("albums_count"): #album items
                    label = "Albums (%s)" % result["albums_count"]
                    cmd = "albums&params=search:%s" %searchterm
                    self.create_generic_listitem(label, "DefaultMusicAlbums.png", cmd)
                if result.get("tracks_count"): #track items
                    label = "Songs (%s)" % result["tracks_count"]
                    cmd = "tracks&params=search:%s" %searchterm
                    self.create_generic_listitem(label, "DefaultMusicSongs.png", cmd)
                if result.get("genres_count"): #genre items
                    label = "Genres (%s)" % result["genres_count"]
                    cmd = "genres&params=search:%s" %searchterm
                    self.create_generic_listitem(label, "DefaultMusicGenres.png", cmd)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
    
    def globalsearch(self):
        kb = xbmc.Keyboard('', xbmc.getLocalizedString(16017))
        kb.doModal()
        if kb.isConfirmed():
            searchterm = kb.getText().replace(" ","[SP]")
            result = self.send_request("globalsearch items 0 10 search:%s" %searchterm)
            for item in result["loop_loop"]:
                params = "globalsearch items 0 100 item_id:%s" %item["id"]
                cmd = "browse&params=%s" % quote_plus(params)
                self.create_generic_listitem(item["name"], "DefaultMusicSearch.png", cmd)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
    
    def apps(self):
        '''get apps from server'''
        self.params["params"] = "myapps items 0 100000"
        self.browse()
        
    def appgallery(self):
        '''browse appgallery'''
        result = self.send_request("appgallery items 0 100000")
        if result:
            for item in result["loop_loop"]:
                thumb = self.get_thumb(item)
                if "id" in item:
                    item_id = item["id"]
                else:
                    item_id = item["actions"]["go"]["params"]["item_id"]
                params = "appgallery items 0 100000 item_id:%s" % item_id
                cmd = "browse&params=%s" %quote_plus(params)
                self.create_generic_listitem(item["name"], thumb, cmd)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        
    def get_redirect(self, appname):
        '''workaround to get app command redirects'''
        cmd = ""
        all_apps = self.send_request("apps 0 100000")["appss_loop"]
        for app in all_apps:
            if app["name"] == appname:
                # match found
                cmd = app["cmd"]
        return cmd

    def browse(self):
        '''get sublevel entry for an app'''
        request_str = self.params.get("params")
        contenttype = self.params.get("contenttype", "files")
        
        xbmcplugin.setContent(int(sys.argv[1]), contenttype)
        if "__TAGGEDINPUT__" in request_str:
            kb = xbmc.Keyboard('', xbmc.getLocalizedString(16017))
            kb.doModal()
            if kb.isConfirmed():
                search = kb.getText().replace(" ","[SP]")
            request_str = request_str.replace("__TAGGEDINPUT__", search)
        if not "tags:" in request_str:
            request_str += " tags:dguxcyajlKRAG wantMetadata:1"
        result = self.send_request(request_str)
        if "item_loop" in result:
            result = result["item_loop"]
        else:
            result = result["loop_loop"]
        for item in result:
            thumb = self.get_thumb(item)
            app = request_str.split(" ")[0]
            itemtype = item.get("type", "")
            if "actions" in item:
                actionstr = ""
                action_key = "go"
                is_folder = True
                if "do" in item["actions"]:
                    action_key = "do"
                    is_folder = False
                if action_key in item["actions"] and "cmd" in item["actions"][action_key]:
                    for cmd in item["actions"][action_key]["cmd"]:
                        if cmd == "items":
                            actionstr += "items 0 100000 "
                        else:
                            actionstr += "%s " %cmd
                if action_key in item["actions"] and "params" in item["actions"][action_key]:
                    for key, value in item["actions"][action_key]["params"].iteritems():
                        if not "menu" in key:
                            actionstr += "%s:%s " %(key, value)
                if actionstr:
                    if is_folder:
                        cmd = "browse&params=%s" %quote_plus(actionstr)
                    else:
                        cmd = "command&params=%s" %quote_plus(actionstr)
                    thumb = self.get_thumb(item)
                    self.create_generic_listitem(item["text"], thumb, cmd, is_folder)
            elif item.get("isaudio") and not itemtype == "playlist":
                # playable item
                log_msg(item)
                cmd = "%s playlist play item_id:%s" % (app, item["id"])
                cmd = "command&params=%s" % quote_plus(cmd)
                self.create_generic_listitem(item["name"], thumb, cmd, False)
            else:
                # folder item
                contentttype = self.get_app_contenttype(item)
                if itemtype == "redirect":
                    app = self.get_redirect(item["name"])
                    params = "%s items 0 10000" %app
                elif itemtype == "search":
                    params = quote_plus("%s items 0 100000 search:__TAGGEDINPUT__" %app)
                elif "id" in item:
                    # subnode for app/radio
                    params = quote_plus("%s items 0 100000 item_id:%s" %(app, item["id"]))
                elif "text" in item:
                    # text node without any actions ?
                    self.create_generic_listitem(item["text"], thumb, "browse&params=%s" %request_str)
                    continue
                cmd = "browse&params=%s&contentttype=%s" % (params, contentttype)
                self.create_generic_listitem(item["name"], thumb, cmd)

        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def radios(self):
        '''get radio items'''
        request_str = "radios 0 100000 tags:guxcyajlKR"
        result = self.send_request(request_str)
        if result:
            for item in result.get("radioss_loop"):
                if item["cmd"] == "search":
                    params = "%s items 0 100000 search:__TAGGEDINPUT__" % item["cmd"]
                else:
                    params = params = "%s items 0 100000" % item["cmd"]
                cmd = "browse&params=%s" % quote_plus(params)
                thumb = self.get_thumb(item)
                self.create_generic_listitem(item["name"], thumb, cmd)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        
    def get_app_contenttype(self, item):
        '''try to parse the contenttype from the details'''
        contenttype = ""
        if "url" in item:
            url = item["url"]
            if "whatsnew" in url:
                contenttype = "albums"
            elif "spotify:playlist" in url:
                contenttype = "songs"
            elif "categories" in url:
                contenttype = "albums"
            elif "myAlbums" in url:
                contenttype = "albums"
            elif "myArtists" in url:
                contenttype = "artists"
            elif "mySongs" in url:
                contenttype = "songs"
            elif "playlists" in url:
                contenttype = "playlists"
        return contenttype

    def get_thumb(self, item):
        '''get thumb url from the item's properties'''
        thumb = ""
        if item.get("image"):
            thumb = item["image"]
        elif item.get("icon"):
            thumb = item["icon"]
        elif item.get("icon-id"):
            thumb = item["icon-id"]
        elif item.get("artwork_url"):
            thumb = item["artwork_url"]
        elif item.get("coverart") and item.get("coverid"):
            thumb = "music/%s/cover_500x500_p.png" % item["coverid"]
        elif item.get("artwork_track_id"):
            thumb = "music/%s/cover_500x500_p.png" % item["artwork_track_id"]
        elif item.get("album_id"):
            thumb = "imageproxy/mai/album/%s/image.png" %item["album_id"]
        elif item.get("artist_id"):
            thumb = "imageproxy/mai/artist/%s/image.png" %item["artist_id"]
        elif "album" in item and "id" in item:
            thumb = "imageproxy/mai/album/%s/image.png" %item["id"]
        elif "artist" in item and "id" in item:
            thumb = "imageproxy/mai/artist/%s/image.png" %item["id"]
        elif "window" in item and "icon-id" in item["window"]:
            thumb = item["window"]["icon-id"]

        if thumb and not thumb.startswith("http"):
            if thumb.startswith("/"):
                thumb = "http://%s%s" % (self.lmsserver, thumb)
            else:
                thumb = "http://%s/%s" % (self.lmsserver, thumb)

        return thumb

    def create_artist_listitem(self, lms_item):
        '''Create Kodi listitem from LMS artist details'''
        thumb = self.get_thumb(lms_item)
        listitem = xbmcgui.ListItem(lms_item.get("artist"))
        listitem.setInfo('music',
                         {
                             'title': lms_item.get("artist"),
                             'artist': lms_item.get("artist"),
                             'rating': lms_item.get("rating"),
                             'genre': lms_item.get("genre"),
                             'year': lms_item.get("year"),
                             'mediatype': lms_item.get("artist")
                         })
        listitem.setArt({"thumb": thumb})
        listitem.setIconImage(thumb)
        listitem.setThumbnailImage(thumb)
        listitem.setProperty("DBYPE", "song")
        url = "plugin://plugin.audio.squeezebox?action=albums&params=artist_id:%s" % lms_item.get("id")
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),
                                    url=url, listitem=listitem, isFolder=True)

    def get_songinfo(self, url):
        '''get songinfo for given path'''
        result = {}
        track_details = self.send_request("songinfo 0 100 url:%s tags:dguxcyajlKRAG" % url)
        if track_details:
            # songdetails is really weird formatted in the server response
            for item in track_details["songinfo_loop"]:
                if isinstance(item, dict):
                    for key, value in item.iteritems():
                        result[key] = value
        return result

    def create_album_listitem(self, lms_item):
        '''Create Kodi listitem from LMS album details'''
        thumb = self.get_thumb(lms_item)
        listitem = xbmcgui.ListItem(lms_item.get("album"))
        listitem.setInfo('music',
                         {
                             'title': lms_item.get("album"),
                             'artist': lms_item.get("artist"),
                             'album': lms_item.get("album"),
                             'rating': lms_item.get("rating"),
                             'genre': lms_item.get("genre"),
                             'year': lms_item.get("year"),
                             'mediatype': 'album'
                         })
        listitem.setArt({"thumb": thumb})
        listitem.setProperty("DBYPE", "album")
        listitem.setIconImage(thumb)
        listitem.setThumbnailImage(thumb)
        url = "plugin://plugin.audio.squeezebox?action=tracks&params=album_id:%s" % lms_item.get("id")
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),
                                    url=url, listitem=listitem, isFolder=True)

    def create_track_listitem(self, lms_item):
        '''Create Kodi listitem from LMS track details'''
        thumb = self.get_thumb(lms_item)
        listitem = xbmcgui.ListItem(lms_item.get("title"))
        listitem.setInfo('music',
                         {
                             'title': lms_item.get("title"),
                             'artist': "/".join(lms_item.get("trackartist").split(", ")),
                             'album': lms_item.get("album"),
                             'duration': lms_item.get("duration"),
                             'discnumber': lms_item.get("disc"),
                             'rating': lms_item.get("rating"),
                             'genre': "/".join(lms_item.get("genres").split(", ")),
                             'tracknumber': lms_item.get("track_number"),
                             'lyrics': lms_item.get("lyrics"),
                             'year': lms_item.get("year"),
                             'mediatype': lms_item.get("song")
                         })
        listitem.setArt({"thumb": thumb})
        listitem.setIconImage(thumb)
        listitem.setThumbnailImage(thumb)
        listitem.setProperty("isPlayable", "false")
        listitem.setProperty("DBYPE", "song")
        cmd = quote_plus("playlist play %s" % lms_item.get("url"))
        url = "plugin://plugin.audio.squeezebox?action=command&params=%s" % cmd
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),
                                    url=url, listitem=listitem, isFolder=False)

    def create_generic_listitem(self, label, icon, cmd, is_folder=True):
        listitem = xbmcgui.ListItem(label, iconImage=icon)
        url = "plugin://plugin.audio.squeezebox?action=%s" % cmd
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),
                                    url=url, listitem=listitem, isFolder=is_folder)

    def command(self):
        '''play item'''
        cmd = self.params.get("params")
        self.send_request(cmd)
        xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=xbmcgui.ListItem())

    def send_request(self, cmd):
        '''send request to lms server'''
        log_msg(cmd, xbmc.LOGDEBUG)
        if isinstance(cmd, (str, unicode)):
            if "[SP]" in cmd:
                new_cmd = []
                for item in cmd.split():
                    new_cmd.append(item.replace("[SP]"," "))
                cmd = new_cmd
            else:
                cmd = cmd.split()
        url = "http://%s/jsonrpc.js" % self.lmsserver
        cmd = [self.playerid, cmd]
        params = {"id": 1, "method": "slim.request", "params": cmd}
        result = get_json(url, params)
        log_msg(result, xbmc.LOGDEBUG)
        return result
