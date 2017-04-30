# -*- coding: utf8 -*-
import threading
import time
import StringIO
import re
import struct
import cherrypy
from cherrypy import wsgiserver
from cherrypy.process import servers
from datetime import datetime
import random
import sys
import platform
import logging
import os
from utils import log_msg
import xbmc


class HTTPProxyError(Exception):
    pass


class Track:
    __is_playing = None
    __allowed_ips = None
    __allow_ranges = None

    def __init__(self, allowed_ips, allow_ranges=True):
        self.__allowed_ips = allowed_ips
        self.__is_playing = False
        self.__allow_ranges = allow_ranges

    def _get_wave_header(self, duration):
        '''generate a wave header for our silence stream'''
        file = StringIO.StringIO()
        
        # always add 10 seconds of additional duration to solve crossfade issues
        duration += 10
        numsamples = 44100 * duration
        channels = 2
        samplerate = 44100
        bitspersample = 16

        # Generate format chunk
        format_chunk_spec = "<4sLHHLLHH"
        format_chunk = struct.pack(
            format_chunk_spec,
            "fmt ",  # Chunk id
            16,  # Size of this chunk (excluding chunk id and this field)
            1,  # Audio format, 1 for PCM
            channels,  # Number of channels
            samplerate,  # Samplerate, 44100, 48000, etc.
            samplerate * channels * (bitspersample / 8),  # Byterate
            channels * (bitspersample / 8),  # Blockalign
            bitspersample,  # 16 bits for two byte samples, etc.
        )
        # Generate data chunk
        data_chunk_spec = "<4sL"
        datasize = numsamples * channels * (bitspersample / 8)
        data_chunk = struct.pack(
            data_chunk_spec,
            "data",  # Chunk id
            int(datasize),  # Chunk size (excluding chunk id and this field)
        )
        sum_items = [
            #"WAVE" string following size field
            4,
            #"fmt " + chunk size field + chunk size
            struct.calcsize(format_chunk_spec),
            # Size of data chunk spec + data size
            struct.calcsize(data_chunk_spec) + datasize
        ]
        # Generate main header
        all_cunks_size = int(sum(sum_items))
        main_header_spec = "<4sL4s"
        main_header = struct.pack(
            main_header_spec,
            "RIFF",
            all_cunks_size,
            "WAVE"
        )
        # Write all the contents in
        file.write(main_header)
        file.write(format_chunk)
        file.write(data_chunk)

        return file.getvalue(), all_cunks_size + 8

    def _write_file_content(self, filesize, wave_header=None, max_buffer_size=65535):

        # Initialize some loop vars
        output_buffer = StringIO.StringIO()
        bytes_written = 0
        has_frames = True

        # Write wave header
        if wave_header is not None:
            output_buffer.write(wave_header)
            bytes_written = output_buffer.tell()
            yield wave_header
            output_buffer.truncate(0)
        
        # this is where we would normally stream packets from an audio input
        # In this case we stream only silence until the end is reached
        while bytes_written < filesize:

            # The buffer size fits into the file size
            if bytes_written + max_buffer_size < filesize:
                yield '\0' * max_buffer_size
                bytes_written += max_buffer_size

            # Does not fit, just generate the remaining bytes
            else:
                yield '\0' * (filesize - bytes_written)
                bytes_written = filesize

    def _check_request(self):
        method = cherrypy.request.method.upper()
        headers = cherrypy.request.headers

        # Fail for other methods than get or head
        if method not in ("GET", "HEAD"):
            raise cherrypy.HTTPError(405)

        # Error if the requester is not allowed
        if headers['Remote-Addr'] not in self.__allowed_ips:
            raise cherrypy.HTTPError(403)
            
        # for now we do not accept range requests
        # todo: implement range requests so seek works
        if headers.get('Range','') and headers.get('Range','') != "bytes=0-":
            xbmc.executebuiltin("SetProperty(sb-seekworkaround, true, Home)")
            raise cherrypy.HTTPError(416)

        return method

    def _write_http_headers(self, filesize):
        cherrypy.response.headers['Content-Type'] = 'audio/x-wav'
        cherrypy.response.headers['Content-Length'] = filesize
        cherrypy.response.headers['Accept-Ranges'] = 'none'

    @cherrypy.expose
    def default(self, track_id, **kwargs):
        # Check sanity of the request
        self._check_request()

        # get duration from track id
        track_id = track_id.split(".")[0]
        duration = 60
        try:
            duration = int(track_id)
        except:
            pass

        # Calculate file size, and obtain the header
        file_header, filesize = self._get_wave_header(duration)

        self._write_http_headers(filesize)

        # If method was GET, write the file content
        if cherrypy.request.method.upper() == 'GET':
            return self._write_file_content(filesize, file_header)

    default._cp_config = {'response.stream': True}


class Root:
    track = None

    def __init__(self, allowed_ips, allow_ranges=True):
        self.track = Track(
            allowed_ips, allow_ranges
        )

    def cleanup(self):
        self.__session = None
        self.track = None


class ProxyRunner(threading.Thread):
    __server = None
    __base_token = None
    __allowed_ips = None
    __cb_stream_ended = None
    __root = None

    def _find_free_port(self, host, port_list):
        '''find a free tcp port we can use for our webserver'''
        for port in port_list:
            try:
                servers.check_port(host, port, .1)
                return port
            except:
                pass
        list_str = ','.join([str(item) for item in port_list])
        raise HTTPProxyError("Cannot find a free port. Tried: %s" % list_str)

    def __init__(self, host='localhost', try_ports=range(8090, 8100), allowed_ips=['127.0.0.1'], allow_ranges=True):
        port = self._find_free_port(host, try_ports)
        self.__allowed_ips = allowed_ips
        self.__root = Root(
            self.__allowed_ips, allow_ranges
        )
        app = cherrypy.tree.mount(self.__root, '/')
        # Don't log to the screen by default
        log = cherrypy.log
        log.access_file = ''
        log.error_file = ''
        log.screen = False

        self.__server = wsgiserver.CherryPyWSGIServer((host, port), app)
        threading.Thread.__init__(self)

    def run(self):
        self.__server.start()

    def get_port(self):
        return self.__server.bind_addr[1]

    def get_host(self):
        return self.__server.bind_addr[0]

    def ready_wait(self):
        while not self.__server.ready:
            time.sleep(.1)

    def stop(self):
        self.__server.stop()
        self.join(10)
        self.__root.cleanup()
