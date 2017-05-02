#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    plugin.audio.squeezebox
    Squeezelite Player for Kodi
    player_monitor.py
    monitor both LMS and Kodi player
'''

from utils import log_msg, log_exception, ADDON_ID
import xbmc
import xbmcgui
import xbmcvfs

DATA_PATH = xbmc.translatePath("special://profile/addon_data/%s/" % ADDON_ID).decode("utf-8")


class KodiPlayer(xbmc.Player):
    '''Monitor all player events in Kodi'''
    playlist = None
    trackchanging = False
    exit = False
    is_playing = False

    def __init__(self, **kwargs):
        self.lmsserver = kwargs.get("lmsserver")
        self.webport = kwargs.get("webport")
        self.playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        xbmc.Player.__init__(self)
        log_msg("Start Monitoring events for playerid %s" % self.lmsserver.playerid)

    def close(self):
        '''cleanup on exit'''
        exit = True
        del self.playlist

    def onPlayBackPaused(self):
        '''Kodi event fired when playback is paused'''
        if self.isPlayingAudio() and self.lmsserver.mode == "play" and xbmc.getInfoLabel("MusicPlayer.getProperty(sl_path)"):
            self.lmsserver.pause()
            log_msg("Playback paused")

    def onPlayBackResumed(self):
        '''Kodi event fired when playback is resumed after pause'''
        if self.isPlayingAudio() and self.lmsserver.mode == "pause" and xbmc.getInfoLabel("MusicPlayer.getProperty(sl_path)"):
            self.lmsserver.unpause()
            log_msg("Playback unpaused")

    def onPlayBackEnded(self):
        log_msg("onPlayBackEnded")
        self.is_playing = False

    def onPlayBackStarted(self):
        '''Kodi event fired when playback is started (including next tracks)'''
        if self.is_playing and not self.lmsserver.state_changing:
            player_lms_file = xbmc.getInfoLabel("MusicPlayer.Property(sl_path)").decode("utf-8")
            if player_lms_file and player_lms_file != self.lmsserver.status["url"]:
                # next song requested
                log_msg("next track requested by kodi player")
                self.lmsserver.next_track()
        self.is_playing = True

    def onQueueNextItem(self):
        log_msg("onQueueNextItem")

    def onPlayBackSpeedChanged(self, speed):
        '''Kodi event fired when player is fast forwarding/rewinding'''
        log_msg("onPlayBackSpeedChanged")
        if self.isPlayingAudio() and self.lmsserver.mode == "play":
            if speed > 1:
                self.lmsserver.send_command("time +10")
            elif speed < 0:
                self.lmsserver.send_command("time -10")

    def cur_time(self):
        '''current time of the player - if fails return lms player time'''
        try:
            cur_time_kodi = int(self.getTime())
        except Exception:
            cur_time_kodi = self.lmsserver.time
        return cur_time_kodi

    def onPlayBackSeekChapter(self):
        log_msg("onPlayBackSeekChapter")

    def onPlayBackSeek(self, seekTime, seekOffset):
        if self.is_playing and not self.lmsserver.state_changing:
            log_msg("onPlayBackSeek time: %s - seekOffset: %s" % (seekTime, seekOffset))
            self.lmsserver.send_command("time %s" % (int(seekTime) / 1000))

    def onPlayBackStopped(self):
        '''Kodi event fired when playback is stopped'''
        if self.isPlayingAudio():
            if self.lmsserver.mode == "play" or self.lmsserver.mode == "pause":
                self.lmsserver.stop()
                log_msg("playback stopped")
        self.is_playing = False

    def create_listitem(self, lms_song):
        '''Create Kodi listitem from LMS song details'''
        thumb = self.lmsserver.get_thumb(lms_song)
        listitem = xbmcgui.ListItem('Squeezelite')
        artists = " / ".join(lms_song.get("trackartist", "").split(", "))
        if not artists:
            artists = " / ".join(lms_song.get("artist", "").split(", "))
        genres = " / ".join(lms_song.get("genres", "").split(", "))
        if not genres:
            genres = " / ".join(lms_song.get("genre", "").split(", "))

        listitem.setInfo('music',
                         {
                             'title': lms_song.get("title"),
                             'artist': artists,
                             'album': lms_song.get("album"),
                             'duration': lms_song.get("duration"),
                             'discnumber': lms_song.get("disc"),
                             'rating': lms_song.get("rating"),
                             'genre': genres,
                             'tracknumber': lms_song.get("track_number"),
                             'lyrics': lms_song.get("lyrics"),
                             'year': lms_song.get("year")
                         })
        listitem.setArt({"thumb": thumb})
        listitem.setIconImage(thumb)
        listitem.setThumbnailImage(thumb)
        if lms_song.get("remote_title") or not lms_song.get("duration"):
            # workaround for radio streams
            file_name = "http://127.0.0.1:%s/track/radio" % (self.webport)
        else:
            file_name = "http://127.0.0.1:%s/track/%s" % (self.webport, "%s" % int(lms_song.get("duration")))
        listitem.setProperty("sl_path", lms_song["url"])
        listitem.setContentLookup(False)
        listitem.setProperty('do_not_analyze', 'true')
        return listitem, file_name

    def create_playlist(self, skipplay=False):
        '''Create Kodi playlist from items in the LMS playlist'''
        self.playlist.clear()
        squeezeplaylist = self.lmsserver.cur_playlist()
        if squeezeplaylist:
            # add first item with full details and start playing
            li = self.create_listitem(squeezeplaylist[0])
            self.playlist.add(li[1], li[0])
            if not skipplay:
                self.play(self.playlist, startpos=0)
                self.do_seek()
            # add remaining items with basic details to the playlist while already playing
            if len(squeezeplaylist) > 1:
                for item in squeezeplaylist[1:]:
                    li, file_name = self.create_listitem(item)
                    self.playlist.add(file_name, li)

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
