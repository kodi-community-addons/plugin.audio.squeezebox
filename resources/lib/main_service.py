#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    service.squeezelite
    Squeezelite Player for Kodi
    main_service.py
    Background service running the various threads
'''

from utils import log_msg, ADDON_ID, log_exception, get_mac
from player_monitor import KodiPlayer
from httpproxy import ProxyRunner
import xbmc
import xbmcaddon
import xbmcgui
from LMSTools import LMSServer, LMSDiscovery
import subprocess
import os


class MainService:
    '''our main background service running the various threads'''

    kodimonitor = None
    kodiplayer = None

    def __init__(self):
        self.win = xbmcgui.Window(10000)
        self.kodimonitor = xbmc.Monitor()

        # start the webservice (which hosts our silenced audio tracks)
        proxy_runner = ProxyRunner(host='127.0.0.1', allow_ranges=True)
        proxy_runner.start()
        webport = proxy_runner.get_port()
        log_msg('started webproxy at port {0}'.format(webport))

        # get playerid based on mac address
        playerid = get_mac()

        # discover server
        servers = LMSDiscovery().all()
        if servers:
            server = servers[0]
            log_msg("LMS server discovered - host: %s - port: %s" % (server.get("host"), server.get("port")))
        else:
            log_msg("No LMS Server could be detected on the network - abort service startup")
            return

        # initialize lms server object
        lmsserver = LMSServer(server.get("host"), server.get("port"))

        # start squeezelite executable
        sl_exec = self.start_squeezelite(lmsserver, playerid)

        # initialize kodi player monitor
        if playerid and lmsserver:
            self.kodiplayer = KodiPlayer(win=self.win, playerid=playerid, lmsserver=lmsserver, webport=webport)
        else:
            log_msg("LMS Player could not be initialized - abort service startup")

        # keep the threads alive
        while not self.kodimonitor.abortRequested():

            # monitor player status on/off
            if self.kodiplayer.initialized:
                # make sure that the player is still alive
                if not self.kodiplayer.lmsplayer:
                    self.kodiplayer.lmsplayer = self.kodiplayer.get_lmsplayer()
                    
                if self.kodiplayer.isPlayingAudio() and self.kodiplayer.lmsplayer.mode == "stop" and xbmc.getInfoLabel(
                        "MusicPlayer.getProperty(sl_path)"):
                    self.kodiplayer.stop()
                elif not self.kodiplayer.isPlayingAudio() and self.kodiplayer.lmsplayer.mode == "play":
                    self.kodiplayer.create_playlist()

            # TODO: check if LMS server is still alive

            # sleep for 5 seconds
            self.kodimonitor.waitForAbort(5)

        # Abort was requested while waiting. We should exit
        log_msg('Shutdown requested !', xbmc.LOGNOTICE)
        self.kodiplayer.exit = True

        # stop the extra threads
        if sl_exec:
            sl_exec.terminate()
        proxy_runner.stop()
        proxy_runner = None

        # cleanup objects
        self.close()

    def start_squeezelite(self, lmsserver, playerid):
        '''On supported platforms (to be extended) we include squeezelite binary'''
        sl_exec = None
        playername = xbmc.getInfoLabel("System.FriendlyName").decode("utf-8")
        proc = self.get_squeezelite_binary()
        if proc:
            log_msg("Starting Squeezelite binary")
            args = [proc, "-s", lmsserver.host, "-C", "2", "-m", playerid, "-n", playername, "-M", "Kodi"]
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
            try:
                sl_exec = subprocess.Popen(args, startupinfo=startupinfo)
            except Exception as exc:
                log_exception(__name__, exc)
        if not sl_exec:
            log_msg("The Squeezelite binary was not automatically started, "
                    "you should make sure of starting it yourself, e.g. as a service.")
        return sl_exec

    @staticmethod
    def get_squeezelite_binary():
        '''find the correct squeezelite binary belonging to the platform'''
        # todo: extend with linux support and/or possibility to manual specify the path
        sl_binary = ""
        if xbmc.getCondVisibility("System.Platform.Windows"):
            sl_binary = os.path.join(os.path.dirname(__file__), "bin", "win32", "squeezelite-win.exe")
        elif xbmc.getCondVisibility("System.Platform.OSX"):
            sl_binary = os.path.join(os.path.dirname(__file__), "bin", "osx", "squeezelite")
        return sl_binary

    def close(self):
        '''Cleanup Kodi Cpython instances'''
        del self.win
        del self.kodimonitor
        del self.kodiplayer.playlist
        del self.kodiplayer
        log_msg('stopped', xbmc.LOGNOTICE)
