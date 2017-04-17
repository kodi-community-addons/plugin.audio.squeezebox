#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.skin.helper.service
    kodi_monitor.py
    monitor all kodi events
'''

from utils import log_msg, log_exception, ADDON_ID
from LMSTools import LMSServer, LMSPlayer, LMSCallbackServer
from LMSTools import LMSTags as tags
import xbmc
import xbmcgui
import xbmcvfs

squeeze = LMSCallbackServer()
DATA_PATH = xbmc.translatePath("special://profile/addon_data/%s/" % ADDON_ID).decode("utf-8")


class KodiPlayer(xbmc.Player):
    '''Monitor all player events in Kodi'''
    lmsplayer = None
    playlist = None
    trackchanging = False
    initialized = False
    exit = False

    def __init__(self, **kwargs):
        self.win = kwargs.get("win")
        self.playerid = kwargs.get("playerid")
        self.lmsserver = kwargs.get("lmsserver")
        self.webport = kwargs.get("webport")
        self.lmsplayer = self.get_lmsplayer(self.playerid, self.lmsserver)
        self.squeeze = squeeze
        self.squeeze.set_server(self.lmsserver.host, parent_class=self)
        self.squeeze.start()
        self.playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        xbmc.Player.__init__(self)
        if self.lmsplayer:
            log_msg("Start Monitoring events for playerid %s" % self.playerid)
            self.initialized = True

    def onPlayBackPaused(self):
        '''Kodi event fired when playback is paused'''
        if self.initialized and self.isPlayingAudio() and self.lmsplayer.mode == "play" and xbmc.getInfoLabel("MusicPlayer.getProperty(sl_path)"):
            self.lmsplayer.pause()
            log_msg("Playback paused")

    def onPlayBackResumed(self):
        '''Kodi event fired when playback is resumed after pause'''
        if self.initialized and self.isPlayingAudio() and self.lmsplayer.mode == "pause" and xbmc.getInfoLabel("MusicPlayer.getProperty(sl_path)"):
            self.lmsplayer.unpause()
            log_msg("Playback unpaused")

    def onPlayBackStarted(self):
        '''Kodi event fired when playback is started (including next tracks)'''
        if self.initialized and self.isPlayingAudio() and self.lmsplayer.mode == "play" and xbmc.getInfoLabel("MusicPlayer.getProperty(sl_path)"):
            if xbmc.getInfoLabel("MusicPlayer.Title").decode("utf-8") != self.lmsplayer.track_title:
                # the user requested a different song by using kodi controls
                log_msg("NEXT TRACK REQUESTED")
                self.lmsplayer.next()

    def onPlayBackSpeedChanged(self, speed):
        '''Kodi event fired when player is fast forwarding/rewinding'''
        log_msg("onPlayBackSpeedChanged", xbmc.LOGDEBUG)
        if self.initialized and self.isPlayingAudio() and self.lmsplayer.mode == "play":
            if speed > 1:
                self.lmsplayer.forward()
            elif speed < 0:
                self.lmsplayer.rewind()

    def onPlayBackStopped(self):
        '''Kodi event fired when playback is stopped'''
        if self.initialized and self.isPlayingAudio():
            if self.lmsplayer.mode == "play" or self.lmsplayer.mode == "pause":
                self.lmsplayer.stop()
                log_msg("playback stopped")

    def create_listitem(self, lms_song):
        '''Create Kodi listitem from LMS song details'''
        thumb = lms_song.get("artwork_url", "")
        listitem = xbmcgui.ListItem('Squeezelite')
        listitem.setInfo('music',
                         {
                             'title': lms_song.get("title"),
                             'artist': lms_song.get("artist"),
                             'album': lms_song.get("album"),
                             'duration': lms_song.get("duration"),
                             'discnumber': lms_song.get("disc"),
                             'rating': lms_song.get("rating"),
                             'genre': lms_song.get("genre"),
                             'tracknumber': lms_song.get("track_number"),
                             'lyrics': lms_song.get("lyrics"),
                             'year': lms_song.get("year")
                         })
        listitem.setArt({"thumb": thumb})
        listitem.setIconImage(thumb)
        listitem.setThumbnailImage(thumb)
        if lms_song.get("remote_title"):
            # workaround for radio streams - todo: fix this properly
            duration_str = "3600"
        else:
            duration_str = "%s" % int(lms_song.get("duration"))
        file_name = "http://127.0.0.1:%s/track/%s.wav" % (self.webport, duration_str)
        listitem.setProperty("sl_path", file_name)
        return listitem, file_name

    def create_playlist(self, skipplay=False):
        '''Create Kodi playlist from items in the LMS playlist'''
        self.playlist.clear()
        taglist = [tags.ARTIST, tags.COVERID, tags.DURATION, tags.COVERART, tags.ARTWORK_URL,
                   tags.ALBUM, tags.REMOTE, tags.ARTWORK_TRACK_ID, tags.DISC, tags.GENRE, tags.RATING,
                   tags.YEAR, tags.TRACK_NUMBER, tags.REMOTE_TITLE, tags.URL]
        # we only grab the first 10 items for speed reasons
        try:
            squeezeplaylist = self.lmsplayer.playlist_get_current_detail(amount=10, taglist=taglist)
        except Exception as exc:
            # in some situations the extended details fail and we need to fallback to the basic details
            log_exception(__name__, exc)
            squeezeplaylist = self.lmsplayer.playlist_get_current_detail(amount=10)
        # add first item and start playing
        li = self.create_listitem(squeezeplaylist[0])
        if self.lmsplayer.time_elapsed:
            li[0].setProperty("StartOffset", str(int(self.lmsplayer.time_elapsed)))
        self.playlist.add(li[1], li[0])
        if not skipplay:
            self.play(self.playlist, startpos=0)
            self.do_seek()
        # add remaining items to the playlist while already playing
        if len(squeezeplaylist) > 1:
            for item in squeezeplaylist[1:]:
                li = self.create_listitem(item)
                self.playlist.add(li[1], li[0])

    @squeeze.event(squeeze.CLIENT_ALL)
    def client_event(self, event=None):
        log_msg("CLIENT Event received: {}".format(event))

    @squeeze.event(squeeze.PLAYLIST_ALL)
    def play_event(self, event=None):
        '''LMS event fired when there is an update for one of the players'''
        if self.initialized:
            dest_player = event.split(" ")[0]
            synced_players = self.lmsplayer.get_synced_players(True)
            if (not self.lmsplayer.mode == "stop" and
                    (self.playerid in dest_player or
                     (dest_player in synced_players and not "stop" in self.lmsplayer.mode))):
                log_msg("Player event received targeted for this machine: {}".format(event))
                if "stop" in event or "clear" in event:
                    if not self.trackchanging:
                        self.stop()
                        self.playlist.clear()
                    self.trackchanging = False
                elif "jump" in event or "newsong" in event:
                    self.trackchanging = True
                    self.create_playlist()
                elif "seek" in event:
                    self.do_seek()
                elif "pause 1" in event and not xbmc.getCondVisibility("Player.Paused"):
                    self.pause()
                elif "pause 0" in event and xbmc.getCondVisibility("Player.Paused"):
                    xbmc.executebuiltin("Action(Play)")
                elif "pause 0" in event and xbmc.getCondVisibility("!Player.HasAudio"):
                    self.create_playlist()
                elif "delete" in event or "load_done" in event or "move" in event:
                    # playlist reordered
                    self.create_playlist(True)

    def do_seek(self):
        # seek requested
        # ignore as seek is not implemented in the webserver (accept-ranges)
        pass
        # if self.lmsplayer.time_elapsed:
        # seektime = int(self.lmsplayer.time_elapsed)*1000
        # log_msg("seek requested... %s" %seektime)
        # self.wait_for_player()
        # self.seekTime(seektime)

    def wait_for_player(self):
        count = 0
        while not xbmc.getCondVisibility("Player.HasAudio") and count < 10:
            xbmc.sleep(250)
            count += 1

    def get_lmsplayer(self, playerid, lmsserver):
        # wait for player arrival in server response
        lmsplayer = None
        while not lmsplayer:
            log_msg("Waiting for squeezelite player...")
            if self.exit:
                return None
            try:
                lmsplayer = LMSPlayer(playerid, lmsserver)
                log_msg('lmsplayer {0}'.format(lmsplayer))
            except:
                pass
            xbmc.sleep(1000)
        log_msg("player available on server")
        return lmsplayer
