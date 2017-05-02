#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    plugin.audio.squeezebox
    Squeezelite Player for Kodi
    main_service.py
    Background service which launches the squeezelite binary and monitors the player
'''

from utils import log_msg, ADDON_ID, log_exception, get_mac
from player_monitor import KodiPlayer
from httpproxy import ProxyRunner
from discovery import LMSDiscovery
from lmsserver import LMSServer
import xbmc
import xbmcaddon
import xbmcgui
import subprocess
import os
import sys
from shoutserver import ShoutServer


class MainService:
    '''our main background service running the various threads'''
    sl_exec = None

    def __init__(self):
        win = xbmcgui.Window(10000)
        kodimonitor = xbmc.Monitor()

        # start the webservice (which hosts our silenced audio tracks)
        proxy_runner = ProxyRunner(host='127.0.0.1', allow_ranges=True)
        proxy_runner.start()
        webport = proxy_runner.get_port()
        log_msg('started webproxy at port {0}'.format(webport))

        # get playerid based on mac address
        playerid = get_mac()

        # discover server
        lmsserver = None
        while not lmsserver and not kodimonitor.abortRequested():
            log_msg("Waiting for LMS Server...")
            servers = LMSDiscovery().all()
            if servers:
                server = servers[0]  # for now, just use the first server discovered
                lmshost = server.get("host")
                lmsport = server.get("port")
                lmsserver = LMSServer(lmshost, lmsport, playerid)
                log_msg("LMS server discovered - host: %s - port: %s" % (lmshost, lmsport))
            else:
                kodimonitor.waitForAbort(1)

        if lmsserver:
            # publish lmsdetails as window properties for the plugin entry
            win.setProperty("lmshost", lmshost)
            win.setProperty("lmsport", str(lmsport))
            win.setProperty("lmsplayerid", playerid)

            # start squeezelite executable
            self.start_squeezelite(lmsserver)

            # initialize kodi player monitor
            kodiplayer = KodiPlayer(lmsserver=lmsserver, webport=webport)

            prev_count = 0
            prev_title = ""

            # monitor the lms player
            while not kodimonitor.abortRequested():

                # poll the status every interval
                lmsserver.update_status()

                # make sure that the status is not actually changing right now
                if not lmsserver.state_changing:
                    # the state is a combi of a few player properties, perform actions if one of them changed
                    player_lms_file = xbmc.getInfoLabel("MusicPlayer.Property(sl_path)").decode("utf-8")
                    cur_title = lmsserver.cur_title

                    # player state changed
                    if kodiplayer.is_playing and player_lms_file and lmsserver.mode == "stop":
                        # playback stopped
                        log_msg("stop requested by lms server")
                        kodiplayer.stop()
                    elif player_lms_file and xbmc.getCondVisibility("Player.Paused") and lmsserver.mode == "play":
                        # playback resumed
                        log_msg("resume requested by lms server")
                        xbmc.executebuiltin("PlayerControl(play)")
                    elif not kodiplayer.is_playing and lmsserver.mode == "play":
                        # playback started
                        log_msg("play requested by lms server")
                        kodiplayer.create_playlist()
                    elif player_lms_file and not xbmc.getCondVisibility("Player.Paused") and lmsserver.mode == "pause":
                        # playback paused
                        log_msg("pause requested by lms server")
                        kodiplayer.pause()
                    elif player_lms_file and player_lms_file != lmsserver.status["url"]:
                        # other track requested
                        log_msg("next track requested by lms server")
                        kodiplayer.create_playlist()

                    # monitor while playing
                    if kodiplayer.is_playing and lmsserver.mode == "play":
                        cur_count = lmsserver.status["playlist_tracks"]
                        if (cur_count != prev_count) or (cur_title != prev_title):
                            # playlist changed
                            log_msg("playlist changed on lms server")
                            if xbmc.getCondVisibility("Player.IsInternetStream"):
                                kodiplayer.create_playlist()
                            else:
                                kodiplayer.create_playlist(True)
                            prev_count = cur_count
                        # monitor seeking
                        if xbmc.getCondVisibility("!Player.IsInternetStream"):
                            cur_time_lms = int(lmsserver.time)
                            cur_time_kodi = kodiplayer.cur_time()
                            if cur_time_kodi != cur_time_lms and abs(
                                    cur_time_lms - cur_time_kodi) > 2 and not xbmc.getCondVisibility("Player.Paused"):
                                # seek started
                                log_msg(
                                    "seek requested by lms server - kodi-time: %s  - lmstime: %s" %
                                    (cur_time_kodi, cur_time_lms))
                                kodiplayer.seekTime(cur_time_kodi)

                prev_title = cur_title

                # sleep for 1 seconds
                kodimonitor.waitForAbort(1)

        # Abort was requested while waiting. We should exit
        log_msg('Shutdown requested !', xbmc.LOGNOTICE)
        win.setProperty("lmsexit", "true")
        kodiplayer.close()

        # stop the extra threads and cleanup
        self.stop_squeezelite()
        proxy_runner.stop()
        proxy_runner = None
        del win
        del kodimonitor
        del kodiplayer
        log_msg('stopped', xbmc.LOGNOTICE)

    def start_squeezelite(self, lmsserver):
        '''On supported platforms we include squeezelite binary'''
        playername = xbmc.getInfoLabel("System.FriendlyName").decode("utf-8")
        proc = self.get_squeezelite_binary()
        if proc:
            log_msg("Starting Squeezelite binary")
            args = [proc, "-s", lmsserver.host, "-C", "2", "-m", lmsserver.playerid, "-n", playername, "-M", "Kodi"]
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
            try:
                self.sl_exec = subprocess.Popen(args, startupinfo=startupinfo)
            except Exception as exc:
                log_exception(__name__, exc)
        if not self.sl_exec:
            log_msg("The Squeezelite binary was not automatically started, "
                    "you should make sure of starting it yourself, e.g. as a service.")
            self.sl_exec = False

    def stop_squeezelite(self):
        '''stop squeezelite if supported'''
        if self.sl_exec:
            self.sl_exec.terminate()

    @staticmethod
    def get_squeezelite_binary():
        '''find the correct squeezelite binary belonging to the platform'''
        sl_binary = ""
        if xbmc.getCondVisibility("System.Platform.Windows"):
            sl_binary = os.path.join(os.path.dirname(__file__), "bin", "win32", "squeezelite-win.exe")
        elif xbmc.getCondVisibility("System.Platform.OSX"):
            sl_binary = os.path.join(os.path.dirname(__file__), "bin", "osx", "squeezelite")
        elif xbmc.getCondVisibility("System.Platform.Linux.RaspberryPi"):
            sl_binary = os.path.join(os.path.dirname(__file__), "bin", "linux", "squeezelite-arm")
        elif xbmc.getCondVisibility("System.Platform.Linux"):
            if sys.maxsize > 2**32:
                sl_binary = os.path.join(os.path.dirname(__file__), "bin", "linux", "squeezelite-i64")
            else:
                sl_binary = os.path.join(os.path.dirname(__file__), "bin", "linux", "squeezelite-x86")
        else:
            log_msg("Unsupported platform! - for iOS and Android you need to install a squeezeplayer app yourself and mure sure it's running in the background.")
        return sl_binary
