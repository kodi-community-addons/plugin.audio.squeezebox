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

            # mainloop
            while not kodimonitor.abortRequested():
                # monitor the LMS state changes
                self.monitor_lms(kodiplayer, lmsserver)
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
        del self.addon
        log_msg('stopped', xbmc.LOGNOTICE)

    def monitor_lms(self, kodiplayer, lmsserver):
        '''monitor the state of the lmsserver/player'''
        # poll the status every interval
        lmsserver.update_status()
        # make sure that the status is not actually changing right now
        if not lmsserver.state_changing and not kodiplayer.is_busy:

            # monitor LMS player and server details
            if (lmsserver.power == 1 or not self.temp_power_off) and xbmc.getCondVisibility("Player.HasVideo"):
                # turn off lms player when kodi is playing video
                lmsserver.send_command("power 0")
                self.temp_power_off = True
            elif self.temp_power_off and not xbmc.getCondVisibility("Player.HasVideo"):
                # turn on player again when video playback was finished
                lmsserver.send_command("power 1")
                self.temp_power_off = False
            elif self.prev_checksum != lmsserver.timestamp:
                # the playlist was modified
                self.prev_checksum = lmsserver.timestamp
                log_msg("playlist changed on lms server")
                kodiplayer.update_playlist()
                if kodiplayer.is_playing:
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
            sl_binary = self.get_squeezelite_binary()
            if sl_binary:
                sl_output = self.get_audiodevice(sl_binary)
                log_msg("Starting Squeezelite binary - Using audio device: %s" %sl_output)
                args = [sl_binary, "-s", lmsserver.host, "-C", "1", "-m", lmsserver.playerid, "-n", playername, "-M", "Kodi", "-o", sl_output]
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
                self.sl_exec = subprocess.Popen(args, startupinfo=startupinfo, stderr=subprocess.STDOUT)
        if not self.sl_exec:
            log_msg("The Squeezelite binary was not automatically started, "
                    "you should make sure of starting it yourself, e.g. as a service.")
            self.sl_exec = False

    def stop_squeezelite(self):
        '''stop squeezelite if supported'''
        if self.sl_exec:
            self.sl_exec.terminate()

    def get_squeezelite_binary(self):
        '''find the correct squeezelite binary belonging to the platform'''
        sl_binary = ""
        if self.addon.getSetting("squeezelite_path"):
            sl_binary = self.addon.getSetting("squeezelite_path").decode("utf-8")
        elif xbmc.getCondVisibility("System.Platform.Windows"):
            sl_binary = os.path.join(os.path.dirname(__file__), "bin", "win32", "squeezelite-win.exe")
        elif xbmc.getCondVisibility("System.Platform.OSX"):
            sl_binary = os.path.join(os.path.dirname(__file__), "bin", "osx", "squeezelite")
            st = os.stat(sl_binary)
            os.chmod(sl_binary, st.st_mode | stat.S_IEXEC)
        elif xbmcvfs.exists("/storage/.kodi/addons/virtual.multimedia-tools/bin/squeezelite"):
            # libreelec has squeezelite preinstalled with the multimedia tools
            sl_binary = "/storage/.kodi/addons/virtual.multimedia-tools/bin/squeezelite"
        elif xbmc.getCondVisibility("System.Platform.Linux.RaspberryPi"):
            sl_binary = os.path.join(os.path.dirname(__file__), "bin", "linux", "squeezelite-arm")
            st = os.stat(sl_binary)
            os.chmod(sl_binary, st.st_mode | stat.S_IEXEC)
        elif xbmc.getCondVisibility("System.Platform.Linux"):
            if sys.maxsize > 2**32:
                sl_binary = os.path.join(os.path.dirname(__file__), "bin", "linux", "squeezelite-i64")
            else:
                sl_binary = os.path.join(os.path.dirname(__file__), "bin", "linux", "squeezelite-x86")
            st = os.stat(sl_binary)
            os.chmod(sl_binary, st.st_mode | stat.S_IEXEC)
        else:
            log_msg("Unsupported platform! - for iOS and Android you need to install a squeezeplayer app yourself and make sure it's running in the background.")
        return sl_binary
        
    @staticmethod
    def get_audiodevice(sl_binary):
        # guess the audio device to use
        # todo: make user configurable ?
        args = [sl_binary, "-l"]
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
        sl_exec = subprocess.Popen(args, startupinfo=startupinfo, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        stdout, stderr = sl_exec.communicate()
        for line in stdout.splitlines():
            line = line.strip().split(" ")[0]
            if "default" in line:
                log_msg("Using audio device: %s" %line)
                return line
        return "default"
        