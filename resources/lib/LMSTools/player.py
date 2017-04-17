# LMSTools: A suite of python tools for use with a Logitech Media Server
#
# by elParaguayo
#
# This set of tools was inspired by the PyLMS library.

from artworkresolver import LMSArtworkResolver
from tags import LMSTags as tags
from utils import LMSUtils


DETAILED_TAGS = [tags.ARTIST,
                 tags.COVERID,
                 tags.DURATION,
                 tags.COVERART,
                 tags.ARTWORK_URL,
                 tags.ALBUM,
                 tags.REMOTE,
                 tags.ARTWORK_TRACK_ID]


class LMSPlayerError(Exception):
    pass


class LMSPlayer(LMSUtils):
    """
    The LMSPlayer class represents an individual squeeze player connected to
    your Logitech Media Server.

    Instances of this class are generated from the LMSServer object and it is
    not expected that you would create an instance directly. However, it is
    posible to create instances directly:

    .. code-block:: python

        server = LMSServer("192.168.0.1")

        # Get player instance with MAC address of player
        player = LMSPlayer("12:34:56:78:90:AB", server)

        # Get player based on index of player on server
        player = LMSPlayer.from_index(0, server)

    Upon intialisation, basic information about the player is retrieved from the
    server:

    ::

        >>>player = LMSPlayer("12:34:56:78:90:AB", server)
        >>>player.name
        u'Living Room'
        >>>player.model
        u'squeezelite'

    """

    def __init__(self, ref, server):
        self.server = server
        self.ref = ref
        self._name = None
        self._model = None
        self._ip = None
        self._art = LMSArtworkResolver.from_server(self.server)
        self.update()

    @classmethod
    def from_index(cls, index, server):
        """
        Create an instance of LMSPlayer when the MAC address of the player is \
        unknown.

        This class method uses the index of the player (as registered on the \
        server) to identify the player.

        :rtype: LMSPlayer
        :returns: Instance of squeezeplayer
        """
        ref = server.request(params="player id {} ?".format(index))["_id"]
        return cls(ref, server)

    def __repr__(self):
        return "LMSPlayer: {} ({})".format(self.name, self.ref)

    def __eq__(self, other):
        # Useful to have a method to test for equality.
        # Test will match player instances and also MAC address string.

        try:
            return self.ref == other.ref
        except AttributeError:
            if type(other) in (str, unicode):
                return self.ref.lower() == str(other).lower()
            else:
                return False

    def update(self):
        """
        Retrieve some basic info about the player.

        Retrieves the name, model and ip attributes. This method is called on \
        initialisation.
        """
        self._name = self.name
        self._model = self.parse_request("player model ?", "_model")
        self._ip = self.parse_request("player ip ?", "_ip")

    def request(self, command):
        """
        :type command: str, list
        :param command: command to be sent to server
        :rtype: dict
        :returns: JSON response received from server

        Send the request to the server."""
        return self.server.request(self.ref, command)

    def parse_request(self, command, key):
        """
        :type command: str, list
        :param command: command to be sent to server
        :type key: str
        :param key: key to retrieve desired info from JSON response
        :returns: value from JSON response

        Send the request and extract the info from the JSON response.

        This is the same as player.request(command).get(key)
        """
        return self.request(command).get(key)

    def play(self):
        """Start playing the current item"""
        self.request("play")

    def stop(self):
        """Stop the player"""
        self.request("stop")

    def pause(self):
        """
        Pause the player. This does not unpause the player if already paused.
        """
        self.request("pause 1")

    def unpause(self):
        """Unpause the player."""
        self.request("pause 0")

    def toggle(self):
        """Play/Pause Toggle"""
        self.request("pause")

    def next(self):
        """Play next item in playlist"""
        self.request("playlist jump +1")

    def prev(self):
        """Play previous item in playlist"""
        self.request("playlist jump -1")

    def mute(self):
        """Mute player"""
        self.muted = True

    def unmute(self):
        """Unmute player"""
        self.muted = False

    def seek_to(self, seconds):
        """
        :type seconds: int, float
        :param seconds: position (in seconds) that player should seek to

        Move player to specified position in current playlist item"""
        try:
            seconds = float(seconds)
            self.request("time {}".format(seconds))
        except TypeError:
            pass

    def forward(self, seconds=10):
        """
        :type seconds: int, float
        :param seconds: number of seconds to jump forwards in current track.

        Jump forward in current track. Number of seconds will be converted to \
        integer.
        """
        try:
            seconds = int(seconds)
            self.request("time +{}".format(seconds))
        except TypeError:
            pass

    def rewind(self, seconds=10):
        """
        :type seconds: int, float
        :param seconds: number of seconds to jump backwards in current track.

        Jump backwards in current track. Number of seconds will be converted to \
        integer.
        """
        try:
            seconds = int(seconds)
            self.request("time -{}".format(seconds))
        except TypeError:
            pass

    @property
    def name(self):
        """
        Player name.

        :getter: retrieve name of player
        :rtype: unicode, str
        :returns: name of player

        :setter: update name of player on server

        ::

            >>>p.name
            u"elParaguayo's Laptop"
            >>>p.name = "New name"
            >>>p.name
            'New name'

        """
        if self._name is None:
            self._name = self.parse_request("name ?", "_value")

        return self._name

    @name.setter
    def name(self, name):
        """
        Set the player name.
        """
        try:
            self.request("name {}".format(name))
            self._name = name
        except:
            pass

    @property
    def model(self):
        """
        :rtype: str, unicode
        :returns: model name of the current player.
        """
        return self._model

    @property
    def mode(self):
        """
        :rtype: str, unicode
        :returns: curent mode (e.g. "play", "pause")
        """
        return self.parse_request("mode ?", "_mode")

    @property
    def muted(self):
        """
        Muting

        :getter: retrieve current muting status
        :rtype: bool
        :returns: True if muted, False if not.

        :setter: set muting status (True = muted)

        """
        muted = self.parse_request("mixer muting ?", "_muting")
        if muted is None:
            return False
        else:
            return muted == 1

    @muted.setter
    def muted(self, muting):
        try:
            self.request("mixer muting {}".format(int(muting)))
        except:
            pass

    @property
    def wifi_signal_strength(self):
        """
        :rtype: int
        :returns: Wifi signal strength
        """
        return self.parse_request("signalstrength ?", "_signalstrength")

    @property
    def track_artist(self):
        """
        :rtype: unicode, str
        :returns: name of artist for current playlist item

        ::

            >>>player.track_artist
            u'Kiasmos'

        """
        return self.parse_request("artist ?", "_artist")

    @property
    def track_album(self):
        """
        :rtype: unicode, str
        :returns: name of album for current playlist item

        ::

            >>>player.track_album
            u'Kiasmos'

        """
        return self.parse_request("album ?", "_album")

    @property
    def track_title(self):
        """
        :rtype: unicode, str
        :returns: name of track for current playlist item

        ::

            >>>player.track_artist
            u'Lit'

        """
        return self.parse_request("title ?", "_title")

    @property
    def track_duration(self):
        """
        :rtype: float
        :returns: duration of track in seconds

        ::

            >>>player.track_duration
            384.809

        """
        return float(self.parse_request("duration ?", "_duration"))

    @property
    def track_elapsed_and_duration(self):
        """
        :rtype: tuple (float, float)
        :returns: tuple of elapsed time and track duration

        ::

            >>>player.track_elapsed_and_duration
            (4.86446976280212, 384.809)

        """
        try:
            duration = self.track_duration
            elapsed = self.time_elapsed
        except:
            duration = 0.0
            elapsed = 0.0

        return elapsed, duration

    @property
    def track_artwork(self):
        """
        Get URL for current track artwork

        :rtype: str
        :returns: url to artwork if available. Returns empty string if no URL.
        """
        track = self.playlist_get_current_detail(amount=1)
        art = str(self._art.getURL(track[0]))

        if self._art.is_default(art):
            return ""
        else:
            return art

    def percentage_elapsed(self, upper=100):
        """
        :type upper: float, int
        :param upper: (optional) scale - returned value is between 0 and upper \
        (default 100)
        :rtype: float
        :returns: current percentage elapsed

        ::

            >>>player.percentage_elapsed()
            29.784033576552005
            >>>p.percentage_elapsed(upper=1)
            0.31738374576051237

        """
        try:
            elapsed, duration = self.track_elapsed_and_duration
            return (elapsed / duration) * upper
        except:
            return 0.0

    @property
    def time_elapsed(self):
        """
        :rtype: float
        :returns: elapsed time in seconds. Returns 0.0 if an exception is \
        encountered.

        """
        try:
            elapsed = float(self.parse_request("time ?", "_time"))
        except TypeError:
            elapsed = 0.0

        return elapsed

    @property
    def time_remaining(self):
        """
        :rtype: float
        :returns: remaining time in seconds. Returns 0.0 if an exception is \
        encountered.

        """
        try:
            return self.track_duration - self.time_elapsed
        except:
            return 0.0

    @property
    def track_count(self):
        """
        :rtype: int
        :returns: number of tracks in playlist

        """
        try:
            return int(self.parse_request("playlist tracks ?", "_tracks"))
        except:
            return 0

    def playlist_play_index(self, index):
        """
        :type index: int
        :param index: index of playlist track to play (zero-based index)

        """
        return self.request('playlist index {}'.format(index))

    @property
    def playlist_position(self):
        """
        :rtype:     int
        :returns: position of current track in playlist

        """
        try:
            return int(self.parse_request("playlist index ?", "_index"))
        except:
            return 0

    def playlist_get_current_detail(self, amount=None, taglist=None,
                                    local_art=True):
        """
        :type amount: int
        :param amount: number of tracks to query
        :type taglist: list
        :param taglist: list of tags (NEED LINK)
        :type local_art: bool
        :param local_art: generate URL for local tracks
        :rtype: list
        :returns: server result

        If amount is None, all remaining tracks will be displayed.

        If not taglist is provided, the default list is:
        [tags.ARTIST, tags.COVERID, tags.DURATION, tags.COVERART, \
        tags.ARTWORK_URL, tags.ALBUM, tags.REMOTE, tags.ARTWORK_TRACK_ID]

        ::

            >>>player.playlist_get_current_detail(amount=1)
            [{u'album': u'Jake Bugg',
              u'artist': u'Jake Bugg',
              u'artwork_url': u'https://i.scdn.co/image/6ba50b26867613b100281669ff1a917c5a020534',
              u'coverart': u'0',
              u'coverid': u'-161090728',
              u'duration': u'144',
              u'id': u'-161090728',
              u'playlist index': 7,
              u'remote': 1,
              u'title': u'Lightning Bolt'}]
            >>>player.playlist_get_current_detail(amount=1, taglist=[tags.DURATION])
            [{u'duration': u'144',
              u'id': u'-161090728',
              u'playlist index': 7,
              u'title': u'Lightning Bolt'}]

        """
        if taglist is None:
            taglist = DETAILED_TAGS
        return self.playlist_get_info(start=self.playlist_position,
                                      amount=amount,
                                      taglist=taglist,
                                      local_art=local_art)

    def playlist_get_detail(self, start=None, amount=None, taglist=None,
                            local_art=True):
        """
        :type start: int
        :param start: playlist index of first track to query
        :type amount: int
        :param amount: number of tracks to query
        :type taglist: list
        :param taglist: list of tags (NEED LINK)
        :type local_art: bool
        :param local_art: generate URL for local tracks
        :rtype: list
        :returns: server result

        If start is None, results will start with the first track in the playlist.

        If amount is None, all playlist tracks will be returned.

        If not taglist is provided, the default list is:
        [tags.ARTIST, tags.COVERID, tags.DURATION, tags.COVERART, \
        tags.ARTWORK_URL, tags.ALBUM, tags.REMOTE, tags.ARTWORK_TRACK_ID]

        ::

            >>>player.playlist_get_detail(start=1, amount=1, taglist=[tags.URL])
            [{u'id': u'-137990288',
             u'playlist index': 1,
             u'title': u"Mardy Bum by Arctic Monkeys from Whatever People Say I Am, That's What I'm Not",
             u'url': u'spotify://track:2fyIS6GXMgUcSv4oejx63f'}]

        """
        if taglist is None:
            taglist = DETAILED_TAGS
        return self.playlist_get_info(start=start,
                                      amount=amount,
                                      taglist=taglist,
                                      local_art=local_art)

    def playlist_get_info(self, taglist=None, start=None, amount=None,
                          local_art=True):
        """
        :type start: int
        :param start: playlist index of first track to query
        :type amount: int
        :param amount: number of tracks to query
        :type taglist: list
        :param taglist: list of tags (NEED LINK)
        :type local_art: bool
        :param local_art: generate URL for local tracks
        :rtype: list
        :returns: server result

        If start is None, results will start with the first track in the \
        playlist.

        If amount is None, all playlist tracks will be returned.

        Unlike playlist_get_detail, no default taglist is provided.

        ::

            >>>player.playlist_get_info(start=1, amount=1)
            [{u'id': u'-137990288',
              u'playlist index': 1,
              u'title': u'Mardy Bum'}]

        """
        """Get info about the tracks in the current playlist"""
        if amount is None:
            amount = self.track_count

        # We need to see if we want to get local artwork url
        # But we should only do this if the user has requested ARTWORK_URL
        if taglist and tags.ARTWORK_URL in taglist and local_art:
            reqs = [tags.REMOTE, tags.ARTWORK_TRACK_ID, tags.COVERART]
            for req in reqs:
                if req not in taglist:
                    taglist += req
            update_art = True
        else:
            update_art = False

        if start is None:
            start = 0

        tagstr = " tags:{}".format(",".join(taglist)) if taglist else ""
        command = "status {} {} {}".format(start, amount, tagstr)

        try:
            info =  self.parse_request(command, "playlist_loop")
        except:
            info = []

        # If we're getting local art then we just need to edit local tracks
        if update_art:
            for track in info:
                if not int(track["remote"]):
                    track[u"artwork_url"] = self._art.getURL(track)

        return info

    def playlist_play(self, item):
        """
        Play item

        :type item: str
        :param item: link to playable item

        """
        # item = self.quote(item)
        self.request("playlist play {}".format(item))

    def playlist_add(self, item):
        """
        Add item to playlist

        :type item: str
        :param item: link to playable item

        """
        # item = self.quote(item)
        self.request("playlist add {}".format(item))

    def playlist_insert(self, item):
        """
        Insert item into playlist (after current track)

        :type item: str
        :param item: link to playable item

        """
        # item = self.quote(item)
        self.request("playlist insert {}".format(item))

    def playlist_delete(self, item):
        """
        Delete item

        :type item: str
        :param item: link to playable item

        """
        # item = self.quote(item)
        self.request("playlist deleteitem {}".format(item))

    def playlist_clear(self):
        """Clear the entire playlist. Will also stop the player."""
        self.request("playlist clear")

    def playlist_move(self, from_index, to_index):
        """
        Move items in playlist

        :type from_index: int
        :param from_index: index of item to move
        :type to_index: int
        :param to_index: new playlist position

        """
        self.request("playlist move {} {}" % (from_index, to_index))

    def playlist_erase(self, index):
        """
        Remove item from playlist by index

        :type findex: int
        :param index: index of item to delete

        """
        self.request("playlist delete {}".format(index))

    @property
    def volume(self):
        """
        Volume information

        :getter: Get current volume
        :rtype: int
        :returns: current volume
        :setter: change volume

        ::

            >>>player.volume
            95
            >>>player.volume = 50

        Min: 0, Max: 100
        """
        try:
            return int(self.parse_request("mixer volume ?", "_volume"))
        except:
            return 0

    @volume.setter
    def volume(self, volume):
        """Set Player Volume"""
        try:
            volume = int(volume)
            if volume < 0:
                volume = 0
            if volume > 100:
                volume = 100
            self.request("mixer volume {}".format(volume))
        except TypeError:
            pass

    def volume_up(self, interval=5):
        """
        Increase volume

        :type interval: int
        :param interval: amount to increase volume (default 5)

        """
        self.request("mixer volume +{}".format(interval))

    def volume_down(self, interval=5):
        """
        Decrease volume

        :type interval: int
        :param interval: amount to decrease volume (default 5)

        """
        self.request("mixer volume -{}".format(interval))

    def sync(self, player=None, ref=None, index=None, master=True):
        """
        Synchronise squeezeplayers

        :type player: LMSPlayer
        :param player: Instance of player
        :type ref: str
        :param ref: MAC address of player
        :type index: int
        :param index: server index of squeezeplayer
        :type master: bool
        :param master: whether current player should be the master player in \
        sync group
        :raises: LMSPlayerError

        You must provide one of player, ref or index otherwise an exception \
        will be raised. If master is set to True then you must provide either \
        player or ref.

        """
        if not any([player, ref, index is not None]):
            raise LMSPlayerError("You must provide a LMSPlayer object, "
                                 "player reference or player index.")

        if not master and not any([player, ref]):
            raise LMSPlayerError("You must provide a player object or reference"
                                 " if you wish player to be added to existing "
                                 "group.")

        if player:
            target = player.ref
        elif ref:
            target = ref
        else:
            target = index

        if master:
            self.request(["sync", target])

        else:
            self.server.request(player=target, params=["sync", self.ref])

    def unsync(self):
        """Remove player from syncgroup."""
        self.request("sync -")

    def get_synced_players(self, refs_only=False):
        """
        Retrieve list of players synced to current player.

        :type refs_only: bool
        :param refs_only: whether the method should return list of MAC \
        references or list of LMSPlayer instances.
        :rtype: list
        """
        sync = self.parse_request("sync ?", "_sync")

        if str(sync) == "-":
            return list()

        else:
            if refs_only:
                return sync.split(",")

            else:
                return [LMSPlayer(ref, self.server) for ref in sync.split(",")]

    def check_event_player(self, event):
        """
        :type event: str
        :param event: event payload received from server
        :rtype: bool
        :returns: True if event belongs to the player.

        Check if an event payload belongs to the current player.
        """
        try:
            event_player = event.split(" ")[0]
        except AttributeError:
            raise LMSPlayerError("Invalid event received.")

        return event_player == self.ref

    def check_event_sync_group(self, event):
        """
        :type event: str
        :param event: event payload received from server
        :rtype: bool
        :returns: True if event belongs to the player or a player in the same \
        sync group as the current player.

        Check if an event payload belongs to the current player or a player in \
        the same sync group as the current player..
        """
        try:
            event_player = event.split(" ")[0]
        except AttributeError:
            raise LMSPlayerError("Invalid event received.")

        return any((event_player == self.ref,
                    event_player in self.get_synced_players()))
