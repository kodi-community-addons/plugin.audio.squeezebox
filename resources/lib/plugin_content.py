#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    service.squeezelite
    Squeezelite Player for Kodi
    plugin_content.py
    plugin entry point t 
'''

import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
from utils import log_msg, KODI_VERSION, log_exception, urlencode, get_mac
from LMSTools import LMSServer, LMSPlayer, LMSCallbackServer, LMSMenuHandler, LMSDiscovery
from LMSTools import LMSTags as tags
from LMSTools.menuitems import AudioMenuItem, NextMenuItem, SearchMenuItem, PlaylistMenuItem
import urlparse
import sys
import os


class PluginContent:
    '''Hidden plugin entry point providing some helper features'''
    params = {}
    win = None
    lmsplayer = None

    def __init__(self):
        self.win = xbmcgui.Window(10000)
        
        # initialize lms server and player object
        try:
            playerid = get_mac()
            server = LMSDiscovery().all()[0]
            lmsserver = LMSServer(server.get("host"), server.get("port"))
            self.lmsplayer = LMSPlayer(playerid, lmsserver)
            log_msg('lmsplayer {0}'.format(self.lmsplayer))
        except Exception as exc:
            log_exception(__name__, exc)
            xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        
        # initialize plugin listing
        try:
            self.params = dict(urlparse.parse_qsl(sys.argv[2].replace('?', '').lower().decode("utf-8")))
            log_msg("plugin called with parameters: %s" % self.params)
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
            menuhandler = LMSMenuHandler(self.lmsplayer)
            homemenu = menuhandler.getHomeMenu()
            
            for item in homemenu:
                self.create_listitem(item)
                
                
            xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
            
    def create_listitem(self, menu_item):
        '''Create Kodi listitem from LMS song details'''
        thumb = menu_item.icon
        label = menu_item.text
        listitem = xbmcgui.ListItem(label, iconImage=thumb)
        log_msg('label: %s - cmd: %s' %(label, menu_item.cmd ))
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),
                                        url="", listitem=listitem, isFolder=False)
            
            