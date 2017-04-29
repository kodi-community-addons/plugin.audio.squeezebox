#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    service.squeezelite
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
    

ADDON_ID = "service.squeezelite"
KODI_VERSION = int(xbmc.getInfoLabel("System.BuildVersion").split(".")[0])
KODILANGUAGE = xbmc.getLanguage(xbmc.ISO_639_1)


def log_msg(msg, loglevel=xbmc.LOGNOTICE):
    '''log message to kodi log'''
    if isinstance(msg, unicode):
        msg = msg.encode('utf-8')
    xbmc.log("Squeezelite Service --> %s" % msg, level=loglevel)


def log_exception(modulename, exceptiondetails):
    '''helper to properly log an exception'''
    log_msg(format_exc(sys.exc_info()), xbmc.LOGWARNING)
    log_msg("Exception in %s ! --> %s" % (modulename, exceptiondetails), xbmc.LOGERROR)

def get_json(url, params):
    '''get info from json api'''
    log_msg("get json - url: %s  - params: %s" %(url, params))
    result = {}
    try:
        response = requests.get(url, data=json.dumps(params), timeout=20)
        if response and response.content and response.status_code == 200:
            result = json.loads(response.content.decode('utf-8', 'replace'))
            if "result" in result:
                result = result["result"]
        else:
            log_msg("Invalid or empty reponse from server - command: %s - server response: %s" %(cmd, response.status_code))
    except Exception as exc:
        log_exception(__name__, exc)
    return result
    
def get_json2(url, params):
    import urllib2
    req = urllib2.Request(url)
    req.add_header('Content-Type', 'application/json')

    try:
        response = urllib2.urlopen(req, json.dumps(params))
        return json.loads(response.read())["result"]

    except Exception as exc:
        log_exception(__name__, exc)
        log_msg("Could not connect to server.")
        return None


def get_mac():
    '''helper to obtain the mac address of the kodi machine'''
    count = 0
    mac = ""
    while (not mac or "busy" in mac) and count < 100:
        log_msg("Waiting for mac address...")
        mac = xbmc.getInfoLabel("Network.MacAddress").lower()
        count += 1
        xbmc.sleep(1000)
    if not mac:
        log_msg("Mac detection failed!")
    else:
        log_msg("Detected Mac-Address: %s" % mac)
    return mac


def try_encode(text, encoding="utf-8"):
    '''helper to encode a string to utf-8'''
    try:
        return text.encode(encoding, "ignore")
    except Exception:
        return text


def try_decode(text, encoding="utf-8"):
    '''helper to decode a string into unicode'''
    try:
        return text.decode(encoding, "ignore")
    except Exception:
        return text


def urlencode(text):
    '''urlencode a string'''
    blah = urllib.urlencode({'blahblahblah': try_encode(text)})
    blah = blah[13:]
    return blah
    