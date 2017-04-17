class LMSTags(object):
    """
    :const ARTIST: Artist name.
    :const ALBUM_ID: Album ID. Only if known.
    :const ALBUM_REPLAY_GAIN: Replay gain of the album (in dB), if any
    :const ALBUM: Album name. Only if known.
    :const ARTIST_ID: Artist ID.
    :const ARTIST_ROLE_IDS: For each role as defined above, the list of ids.
    :const ARTIST_ROLE: a comma separated list of names.
    :const ARTWORK_TRACK_ID: Identifier of the album track used by the server to display the album's artwork. Not listed if artwork is not available for this album.
    :const ARTWORK_URL: A full URL to remote artwork. Only available for certain plugins such as Pandora and Rhapsody.
    :const BITRATE: Song bitrate. Only if known.
    :const BPM: Beats per minute. Only if known.
    :const BUTTONS: A hash with button definitions. Only available for certain plugins such as Pandora.
    :const COMMENT: Song comments, if any.
    :const COMPILATION: 1 if the album this track belongs to is a compilation
    :const CONTENT_TYPE: Content type. Only if known.
    :const COVERART: 1 if coverart is available for this song. Not listed otherwise.
    :const COVERID: coverid to use when constructing an artwork URL, such as /music/$coverid/cover.jpg
    :const DISC_COUNT: Number of discs. Only if known.
    :const DISC: Disc number. Only if known.
    :const DURATION: Song duration in seconds.
    :const FILESIZE: Song file length in bytes. Only if known.
    :const GENRE_ID_LIST: Genre IDs, separated by commas (only useful if the server is set to handle multiple items in tags).
    :const GENRE_ID: Genre ID. Only if known.
    :const GENRE_LIST: Genre names, separated by commas (only useful if the server is set to handle multiple items in tags).
    :const GENRE: Genre name. Only if known.
    :const INFO_LINK: A custom link to use for trackinfo. Only available for certain plugins such as Pandora.
    :const LYRICS: Lyrics. Only if known.
    :const MODIFICATION_TIME: Date and time song file was last changed.
    :const MUSICMAGIC_MIXABLE: 1 if track is mixable, otherwise 0.
    :const RATING: Song rating, if known and greater than 0.
    :const REMOTE_TITLE: Title of the internet radio station.
    :const REMOTE: If 1, this is a remote track.
    :const REPLAY_GAIN: Replay gain (in dB), if any
    :const SAMPLERATE: Song sample rate (in KHz)
    :const SAMPLESIZE: Song sample size (in bits)
    :const TAG_VERSION: Version of tag information in song file. Only if known.
    :const TRACK_NUMBER: Track number. Only if known.
    :const URL: Song file url.
    :const YEAR: Song year. Only if known.

    """

    ARTIST = "a"
    ARTIST_ROLE = "A"
    BUTTONS = "B"
    COVERID = "c"
    COMPILATION = "C"
    DURATION = "d"
    ALBUM_ID = "e"
    FILESIZE = "f"
    GENRE = "g"
    GENRE_LIST = "G"
    DISC = "i"
    SAMPLESIZE = "I"
    COVERART = "j"
    ARTWORK_TRACK_ID = "J"
    COMMENT = "k"
    ARTWORK_URL = "K"
    ALBUM = "l"
    INFO_LINK = "L"
    BPM = "m"
    MUSICMAGIC_MIXABLE = "M"
    MODIFICATION_TIME = "n"
    REMOTE_TITLE = "N"
    CONTENT_TYPE = "o"
    GENRE_ID = "p"
    GENRE_ID_LIST = "P"
    DISC_COUNT = "q"
    BITRATE = "r"
    RATING = "R"
    ARTIST_ID = "s"
    ARTIST_ROLE_IDS = "S"
    TRACK_NUMBER = "t"
    SAMPLERATE = "T"
    URL = "u"
    TAG_VERSION = "v"
    LYRICS = "w"
    REMOTE = "x"
    ALBUM_REPLAY_GAIN = "X"
    YEAR = "y"
    REPLAY_GAIN = "Y"
