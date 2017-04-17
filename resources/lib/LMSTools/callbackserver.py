# LMSCallbackServer
#
# by elParaguayo
#
# This is based on the "server" class from the PyLMS module by JingleManSweep
# so plenty of credit due to him for his work.

"""
An asynchronous client that listens to messages broadcast by the server.

The client also accepts callback functions which are triggered whenever a \
matching event is received.

The client subclasses python threading so methods are built-in to the class
object.
"""
from threading import Thread
from telnetlib import IAC, NOP, Telnet
import socket
from time import sleep


class CallbackServerError(Exception):
    pass


class LMSCallbackServer(Thread):
    """
    :type hostname: str
    :param hostname: (optional) ip address/name of the server (excluding "http://" prefix)
    :type port: int
    :param port: (optional) port on which the telent interface is running (default 9090)
    :type username: str
    :param username: (optional) username for access on telnet port
    :type password: str
    :param password: (optional) password for access on telnet port

    If the class is initialised without the hostname parameter then the
    "set_server" method must be called before starting the server otherwise a
    CallbackServerError will be raised.

    **Events**

    The following events are currently define in the class.

    :const MIXER_ALL: Captures all mixer events
    :const VOLUME_CHANGE: Captures volume events
    :const PLAYLIST_ALL: Captures all playlist events
    :const PLAY_PAUSE: Captures play/pause events
    :const PLAY: Captures play event
    :const PAUSE: Captures pause event
    :const PLAYLIST_OPEN: Captures playlist open event
    :const PLAYLIST_CHANGE_TRACK: Captures track changes
    :const PLAYLIST_LOAD_TRACKS: Captures loadtracks event
    :const PLAYLIST_ADD_TRACKS: Captures addtracks event
    :const PLAYLIST_LOADED: Captures "playlist load_done" event
    :const PLAYLIST_REMOVE: Captures "playlist delete" event
    :const PLAYLIST_CLEAR: Captures playlist clear event
    :const PLAYLIST_CHANGED: Captures PLAYLIST_LOAD_TRACKS, PLAYLIST_LOADED, PLAYLIST_ADD_TRACKS, PLAYLIST_REMOVE, PLAYLIST_CLEAR
    :const CLIENT_ALL: Captures all client events
    :const CLIENT_NEW: Captures new client events
    :const CLIENT_DISCONNECT: Captures client disconnect events
    :const CLIENT_RECONNECT: Captures client reconnect events
    :const CLIENT_FORGET: Captures client forget events
    :const SYNC: Captures sync events
    :const SERVER_ERROR: Custom event for server errors
    :const SERVER_CONNECT: Custom event for server connection

    """

    MIXER_ALL = "mixer"
    VOLUME_CHANGE = "mixer volume"

    PLAYLIST_ALL = "playlist"
    PLAY_PAUSE = "playlist pause"
    PLAY = "playlist pause 0"
    PAUSE = "playlist pause 1"
    PLAYLIST_OPEN = "playlist open"
    PLAYLIST_CHANGE_TRACK = "playlist newsong"
    PLAYLIST_LOAD_TRACKS = "playlist loadtracks"
    PLAYLIST_ADD_TRACKS = "playlist addtracks"
    PLAYLIST_LOADED = "playlist load_done"
    PLAYLIST_REMOVE = "playlist delete"
    PLAYLIST_CLEAR = "playlist clear"
    PLAYLIST_CHANGED = [PLAYLIST_LOAD_TRACKS,
                        PLAYLIST_LOADED,
                        PLAYLIST_ADD_TRACKS,
                        PLAYLIST_REMOVE,
                        PLAYLIST_CLEAR]

    CLIENT_ALL = "client"
    CLIENT_NEW = "client new"
    CLIENT_DISCONNECT = "client disconnect"
    CLIENT_RECONNECT = "client reconnect"
    CLIENT_FORGET = "client forget"

    SERVER_ERROR = "server_error"
    SERVER_CONNECT = "server_connect"

    SYNC = "sync"

    def __init__(self,
                 hostname=None,
                 port=9090,
                 username="",
                 password=""):

        super(LMSCallbackServer, self).__init__()
        self.callbacks = {}
        self.notifications = []
        self.abort = False
        self.charset = "utf8"
        self.ending = "\n".encode(self.charset)
        self.connected = False
        self.daemon = True
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.is_connected = False
        self.cb_class = None

    def __connect(self, update=True):
        if not self.hostname:
            raise CallbackServerError("No server details provided.")

        self.__telnet_connect()
        self.__login()
        self.is_connected = True

    def __disconnect(self):
        self.telnet.close()
        self.is_connected = False

    def __telnet_connect(self):
        """
        Telnet Connect
        """
        self.telnet = Telnet(self.hostname, self.port, timeout=2)

    def __login(self):
        """
        Login
        """
        result = self.__request("login %s %s" % (self.username, self.password))
        self.logged_in = (result == "******")
        if not self.logged_in:
            raise CallbackServerError("Unable to login. Check username and "
                                      "password.")

    def __request(self, command_string, preserve_encoding=False):
        """
        Send a request to the Telnet interface.
        """
        # self.logger.debug("Telnet: %s" % (command_string))
        self.telnet.write(self.__encode(command_string + "\n"))
        # Include a timeout to stop unnecessary blocking
        response = self.telnet.read_until(self.__encode("\n"),timeout=1)[:-1]
        if not preserve_encoding:
            response = self.__decode(self.__unquote(response))
        else:
            command_string_quoted = \
                command_string[0:command_string.find(':')] + \
                command_string[command_string.find(':'):].replace(
                    ':', self.__quote(':'))
        start = command_string.split(" ")[0]
        if start in ["songinfo", "trackstat", "albums", "songs", "artists",
                     "rescan", "rescanprogress"]:
            if not preserve_encoding:
                result = response[len(command_string)+1:]
            else:
                result = response[len(command_string_quoted)+1:]
        else:
            if not preserve_encoding:
                result = response[len(command_string)-1:]
            else:
                result = response[len(command_string_quoted)-1:]
        return result

    def __encode(self, text):
        return text.encode(self.charset)

    def __decode(self, bytes):
        return bytes.decode(self.charset)

    def __quote(self, text):
        try:
            import urllib.parse
            return urllib.parse.quote(text, encoding=self.charset)
        except ImportError:
            import urllib
            return urllib.quote(text)

    def __unquote(self, text):
        try:
            import urllib.parse
            return urllib.parse.unquote(text, encoding=self.charset)
        except ImportError:
            import urllib
            return urllib.unquote(text)

    def unquote(self, text):
        return self.__unquote(text)

    def set_server(self, hostname, port=9090, username="", password="",
                   parent_class=None):
        """
        :type hostname: str
        :param hostname: (required) ip address/name of the server (excluding \
        "http://" prefix)
        :type port: int
        :param port: (optional) port on which the telent interface is running \
        (default 9090)
        :type username: str
        :param username: (optional) username for access on telnet port
        :type password: str
        :param password: (optional) password for access on telnet port
        :type parent_class: object
        :param parent_class: (optional) reference to a class instance. \
        Required where decorators have been used on class methods prior to \
        initialising the class.

        Provide details of the server if not provided when the class is
        initialised (e.g. if you are using decorators to define callbacks).

        """
        if self.is_connected:
            raise CallbackServerError("Server already logged in.")

        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        if parent_class:
            self.set_parent_class(parent_class)

        #self.connect()

    def set_parent_class(self, parent):
        self.cb_class = parent

    def event(self, eventname):

        def decorator(func):
            self.add_callback(eventname, func)

            return func

        return decorator

    def add_callback(self, event, callback):
        """
        Define a callback.

        :type event: event
        :param event: Event type
        :type callback: function/method
        :param callback: Reference to the function/method to be called if \
        matching event is received. The function/method must accept one \
        parmeter which is the event string.
        """
        if type(event) == list:
            for ev in event:
                self.__add_callback(ev, callback)

        else:
            self.__add_callback(event, callback)

    def __add_callback(self, event, callback):
        self.callbacks[event] = callback
        notification = event.split(" ")[0]
        if notification not in self.notifications:
            self.notifications.append(notification)

    def remove_callback(self, event):
        """
        Remove a callback.

        :type event: event
        :param event: Event type
        """
        if type(event) == list:
            for ev in event:
                self.__remove_callback(ev)

        else:
            self.__remove_callback(event)

    def __remove_callback(self, event):
        del self.callbacks[event]

    def __check_event(self, event):
        """Checks whether any of the requested notification types match the
           received notification. If there's a match, we run the requested
           callback function passing the notification as the only parameter.
        """
        for cb in self.callbacks:
            if cb in event:
                callback = self.callbacks[cb]
                if self.cb_class:
                    callback(self.cb_class, self.unquote(event))
                else:
                    callback(self.unquote(event))
                break

    def __check_connection(self):
        """Method to check whether we can still connect to the server.

           Sets the flag to stop the server if no collection is available.
        """
        # Create a socket object
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Set a timeout - we don't want this to block unnecessarily
        s.settimeout(2)

        try:
            # Try to connect
            s.connect((self.hostname, self.port))

        except socket.error:
            # We can't connect so stop the server
            self.abort = True

        # Close our socket object
        s.close()

    def stop(self):
        """Stop the callack server thread."""
        self.abort = True

    def run(self):

        while not self.abort:
            try:
                self.__connect()
                self.connected = True
                self.__check_event(LMSCallbackServer.SERVER_CONNECT)
                break
            except CallbackServerError:
                raise
            except:
                sleep(5)

        if self.abort:
            return

        # If we've already defined callbacks then we know which events we're
        # listening out for
        if self.notifications:
            nots = ",".join(self.notifications)
            self.__request("subscribe {}".format(nots))

        # If not, let's just listen for everything.
        else:
            self.__request("listen")

        while not self.abort:
            try:
                # Include a timeout to stop blocking if no server
                data = self.telnet.read_until(self.ending, timeout=1)[:-1]

                # We've got a notification, so let's see if it's one we're
                # watching.
                if data:
                    self.__check_event(data)

            # Server is unavailable so exit gracefully
            except EOFError:
                self.__check_event(CallbackServer.SERVER_ERROR)
                self.run()

        self.__disconnect()
        del self.telnet
