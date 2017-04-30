#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    plugin.audio.squeezebox
    Squeezelite Player for Kodi
    utils.py
    Various helper methods
'''

import xbmc
import xbmcvfs
import os
import sys
import urllib
from traceback import format_exc
import requests

try:
    import simplejson as json
except Exception:
    import json


ADDON_ID = "plugin.audio.squeezebox"
KODI_VERSION = int(xbmc.getInfoLabel("System.BuildVersion").split(".")[0])
KODILANGUAGE = xbmc.getLanguage(xbmc.ISO_639_1)


def log_msg(msg, loglevel=xbmc.LOGNOTICE):
    '''log message to kodi log'''
    if isinstance(msg, unicode):
        msg = msg.encode('utf-8')
    xbmc.log("%s --> %s" % (ADDON_ID, msg), level=loglevel)


def log_exception(modulename, exceptiondetails):
    '''helper to properly log an exception'''
    log_msg(format_exc(sys.exc_info()), xbmc.LOGWARNING)
    log_msg("Exception in %s ! --> %s" % (modulename, exceptiondetails), xbmc.LOGERROR)


def get_json(url, params):
    '''get info from json api'''
    result = {}
    try:
        response = requests.get(url, data=json.dumps(params), timeout=20)
        if response and response.content and response.status_code == 200:
            result = json.loads(response.content.decode('utf-8', 'replace'))
            if "result" in result:
                result = result["result"]
        else:
            log_msg(
                "Invalid or empty reponse from server - command: %s - server response: %s" %
                (cmd, response.status_code))
    except Exception as exc:
        log_exception(__name__, exc)
    return result


def get_mac():
    '''helper to obtain the mac address of the kodi machine'''
    count = 0
    mac = ""
    while ":" not in mac and count < 100:
        log_msg("Waiting for mac address...")
        mac = xbmc.getInfoLabel("Network.MacAddress").lower()
        count += 1
        xbmc.sleep(1000)
    if not mac:
        log_msg("Mac detection failed!")
    else:
        log_msg("Detected Mac-Address: %s" % mac)
    return mac


