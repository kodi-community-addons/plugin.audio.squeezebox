#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    plugin.audio.squeezebox
    Squeezelite Player for Kodi
    main_service.py
    Background service which launches the squeezelite binary and monitors the player
'''

from utils import log_msg, ADDON_ID, log_exception, get_mac, get_squeezelite_binary, get_audiodevice
from player_monitor import KodiPlayer
from httpproxy import ProxyRunner
from lmsserver import LMSServer, LMSDiscovery
import xbmc
import xbmcaddon
import xbmcgui
import subprocess
import os
import sys
import xbmcvfs
import stat


class MainService:
    '''our main background service running the various threads'''
    sl_exec = None
    prev_checksum = ""
    temp_power_off = False
    addon = None

    def __init__(self):
        win = xbmcgui.Window(10000)
        kodimonitor = xbmc.Monitor()
        win.clearProperty("lmsexit")
        self.addon = xbmcaddon.Addon(id=ADDON_ID)
        kodiplayer = None

        # start the webservice (which hosts our silenced audio tracks)
        proxy_runner = ProxyRunner(host='127.0.0.1', allow_ranges=True)
        proxy_runner.start()
        webport = proxy_runner.get_port()
        log_msg('started webproxy at port {0}'.format(webport))

        # get playerid based on mac address
        if self.addon.getSetting("disable_auto_mac") == "true" and self.addon.getSetting("manual_mac"):
            playerid = self.addon.getSetting("manual_mac").decode("utf-8")
        else:
            playerid = get_mac()

        # discover server
        lmsserver = None
        if self.addon.getSetting("disable_auto_lms") == "true":
            # manual server
            lmshost = self.addon.getSetting("lms_hostname")
            lmsport = self.addon.getSetting("lms_port")
            lmsserver = LMSServer(lmshost, lmsport, playerid)
        else:
            # auto discovery
            while not lmsserver and not kodimonitor.abortRequested():
                servers = LMSDiscovery().all()
                log_msg("discovery: %s" % servers)
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

            # report player as awake
            lmsserver.send_command("power 1")

            # mainloop
            while not kodimonitor.abortRequested():
                # monitor the LMS state changes
                self.monitor_lms(kodiplayer, lmsserver)
                # sleep for 1 second
                kodimonitor.waitForAbort(1)

        # Abort was requested while waiting. We should exit
        log_msg('Shutdown requested !', xbmc.LOGNOTICE)
        win.setProperty("lmsexit", "true")
        if lmsserver:
            lmsserver.send_command("power 0")  # report player as powered off
            xbmc.sleep(250)
            kodiplayer.close()
        
        # stop the extra threads and cleanup
        self.stop_squeezelite()
        proxy_runner.stop()
        proxy_runner = None
        del win
        del kodimonitor
        del kodiplayer
        del self.addon
        log_msg('stopped', xbmc.LOGNOTICE)

    def monitor_lms(self, kodiplayer, lmsserver):
        '''monitor the state of the lmsserver/player'''
        # poll the status every interval
        lmsserver.update_status()
        # make sure that the status is not actually changing right now
        if not lmsserver.state_changing and not kodiplayer.is_busy:

            # monitor LMS player and server details
            if self.sl_exec and (lmsserver.power == 1 or not self.temp_power_off) and xbmc.getCondVisibility("Player.HasVideo"):
                # turn off lms player when kodi is playing video
                lmsserver.send_command("power 0")
                self.temp_power_off = True
                kodiplayer.is_playing = False
                log_msg("Kodi started playing video - disabled the LMS player")
            elif self.temp_power_off and not xbmc.getCondVisibility("Player.HasVideo"):
                # turn on player again when video playback was finished
                lmsserver.send_command("power 1")
                self.temp_power_off = False
            elif kodiplayer.is_playing and self.prev_checksum != lmsserver.timestamp:
                # the playlist was modified
                self.prev_checksum = lmsserver.timestamp
                log_msg("playlist changed on lms server")
                kodiplayer.update_playlist()
                kodiplayer.play(kodiplayer.playlist, startpos=lmsserver.cur_index)
            elif not kodiplayer.is_playing and lmsserver.mode == "play":
                    # playback started
                log_msg("play started by lms server")
                if not len(kodiplayer.playlist):
                    kodiplayer.update_playlist()
                kodiplayer.play(kodiplayer.playlist, startpos=lmsserver.cur_index)

            elif kodiplayer.is_playing:
                # monitor some conditions if the player is playing
                if kodiplayer.is_playing and lmsserver.mode == "stop":
                    # playback stopped
                    log_msg("stop requested by lms server")
                    kodiplayer.stop()
                elif xbmc.getCondVisibility("Playlist.IsRandom"):
                    # make sure that the kodi player doesnt have shuffle enabled
                    log_msg("Playlist is randomized! Reload to unshuffle....")
                    kodiplayer.playlist.unshuffle()
                    kodiplayer.update_playlist()
                    kodiplayer.play(kodiplayer.playlist, startpos=lmsserver.cur_index)
                elif xbmc.getCondVisibility("Player.Paused") and lmsserver.mode == "play":
                    # playback resumed
                    log_msg("resume requested by lms server")
                    xbmc.executebuiltin("PlayerControl(play)")
                elif not xbmc.getCondVisibility("Player.Paused") and lmsserver.mode == "pause":
                    # playback paused
                    log_msg("pause requested by lms server")
                    kodiplayer.pause()
                elif kodiplayer.playlist.getposition() != lmsserver.cur_index:
                    # other track requested
                    log_msg("other track requested by lms server")
                    kodiplayer.play(kodiplayer.playlist, startpos=lmsserver.cur_index)
                elif lmsserver.status["title"] != xbmc.getInfoLabel("MusicPlayer.Title").decode("utf-8"):
                    # monitor if title still matches
                    log_msg("title mismatch - updating playlist...")
                    kodiplayer.update_playlist()
                    kodiplayer.play(kodiplayer.playlist, startpos=lmsserver.cur_index)
                elif lmsserver.mode == "play" and not lmsserver.status["current_title"]:
                    # check if seeking is needed - if current_title has value, it means it's a radio stream so we ignore that
                    # we accept a difference of max 2 seconds
                    cur_time_lms = int(lmsserver.time)
                    cur_time_kodi = kodiplayer.cur_time()
                    if cur_time_kodi > 2:
                        if cur_time_kodi != cur_time_lms and abs(
                                cur_time_lms - cur_time_kodi) > 2 and not xbmc.getCondVisibility("Player.Paused"):
                            # seek started
                            log_msg("seek requested by lms server - kodi-time: %s  - lmstime: %s" %
                                    (cur_time_kodi, cur_time_lms))
                            kodiplayer.is_busy = True
                            kodiplayer.seekTime(cur_time_lms)
                            xbmc.sleep(250)
                            kodiplayer.is_busy = False

    def start_squeezelite(self, lmsserver):
        '''On supported platforms we include squeezelite binary'''
        playername = xbmc.getInfoLabel("System.FriendlyName").decode("utf-8")
        if self.addon.getSetting("disable_auto_squeezelite") != "true":
            sl_binary = get_squeezelite_binary()
            if sl_binary:
                try:
                    sl_output = get_audiodevice(sl_binary)
                    self.kill_squeezelite()
                    log_msg("Starting Squeezelite binary - Using audio device: %s" % sl_output)
                    args = [sl_binary, "-s", lmsserver.host, "-a", "80", "-C", "1", "-m",
                            lmsserver.playerid, "-n", playername, "-M", "Kodi", "-o", sl_output]
                    startupinfo = None
                    if os.name == 'nt':
                        startupinfo = subprocess.STARTUPINFO()
                        startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
                    self.sl_exec = subprocess.Popen(args, startupinfo=startupinfo, stderr=subprocess.STDOUT)
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
    def kill_squeezelite():
        '''make sure we don't have any (remaining) squeezelite processes running before we start one'''
        if xbmc.getCondVisibility("System.Platform.Windows"):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
            subprocess.Popen(["taskkill", "/IM", "squeezelite-win.exe"], startupinfo=startupinfo, shell=True)
            subprocess.Popen(["taskkill", "/IM", "squeezelite.exe"], startupinfo=startupinfo, shell=True)
        else:
            os.system("killall squeezelite")
            os.system("killall squeezelite-i64")
            os.system("killall squeezelite-x86")
        xbmc.sleep(2000)

