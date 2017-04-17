import json


def menu_type(menu):

    if isinstance(menu, AudioMenuItem):
        return "audio"
    elif isinstance(menu, PlaylistMenuItem):
        return "playlist"
    elif isinstance(menu, SearchMenuItem):
        return "search"
    else:
        return "menu"

class LMSMenuItemBase(object):

    def __init__(self, player=None, menuitem=None, base=None):

        self.player = player
        self.text = None
        self._cmd = None
        self.icon = None
        self.action = None
        self.base = base
        self.menuitem = menuitem
        self.params = []
        self._process_item(menuitem)

    def _process_item(self, menuitem):

        self.text = menuitem.get("text", "")
        self.icon = self._get_icon(menuitem)

    def _get_icon(self, menuitem):

        icon = menuitem.get("icon", None)

        if icon is None:
            icon = menuitem.get("icon-id", None)

        if icon is None:
            icon = menuitem.get("window", dict()).get("icon-id", None)

        if icon is None:
            icon = menuitem.get("commonParams", dict()).get("track_id", None)
            if icon:
                icon = "music/{}/cover".format(icon)

        if icon and not icon.startswith("http"):
            icon = self.player.server.web + str(icon)
        return icon

    def format_dict_cmd(self, item):
        return ["{}:{}".format(x,item[x]) for x in item]

    def build_cmd(self, menuitem):

        act = menuitem.get("actions", dict()).get("go", False)

        if act:
            cmd = act["cmd"] + self.format_dict_cmd(act.get("params", dict()))
            try:
                idx = cmd.index("items")
                cmd.insert(idx+1, 1000)
                cmd.insert(idx+1, 0)
            except ValueError:
                pass
            return cmd

        else:
            return []

    def _list_to_str(self, cmdlist):
        return " ".join(str(x) for x in cmdlist)

    @property
    def cmdstring(self):
        if type(self._cmd) == list:
            return " ".join(str(x) for x in self._cmd)
        else:
            return None

class NextMenuItem(LMSMenuItemBase):
    """Menu item which has no other purpose than to create a new submenu."""

    def __init__(self, player=None, menuitem=None, base=None):
        super(NextMenuItem, self).__init__(player=player,
                                           menuitem=menuitem,
                                           base=base)
        self._cmd = self.build_cmd(menuitem)

    @property
    def cmd(self):
        """
        :rtype: str
        :returns: command string for next menu

        Get command string for submenu.
        """
        return self._cmd


class SearchMenuItem(LMSMenuItemBase):
    """Menu item where a search term is required."""

    def __init__(self, player=None, menuitem=None, base=None):
        super(SearchMenuItem, self).__init__(player=player,
                                             menuitem=menuitem,
                                             base=base)
        self.search_text = None


    def search(self, query):
        """
        :type query: str
        :param query: search terms
        :rtype: list
        :returns: command to generate search results
        """
        cmd = self.build_cmd(self.menuitem)
        cmd = [u"{}".format(x).replace("__TAGGEDINPUT__", query)
               if "__TAGGEDINPUT__" in u"{}".format(x) else x for x in cmd]
        return cmd

    @property
    def cmd_search(self):
        """
        :rtype: str
        :returns: raw command string

        You will need to replace __TAGGEDINPUT__ with your search term before \
        building a menu with this command.
        """
        return self._list_to_str(self.build_cmd(self.menuitem))

class PlaylistMenuItem(LMSMenuItemBase):
    """
    A playlist menu item is one that can be played directly from this link \
    but can also provide a submenu of all the tracks in the playlist.
    """

    def cmd_from_action(self, mode):
        cmd = []

        act = self.menuitem.get("actions", dict()).get(mode)

        if not act:
            act = self.base.get("actions", dict()).get(mode)

        if act:
            cmd += act.get("cmd", list())
            cmd += self.format_dict_cmd(act.get("params", dict()))
            key = act.get("itemsParams")
            if key:
                try:
                    cmd += self.format_dict_cmd(self.menuitem[key])
                except KeyError:
                    pass

        return cmd

    def play(self):
        """Play the selected item."""
        cmd = self.cmd_play
        self.player.request(cmd)

    def play_next(self):
        """Play the selected item after the currently playing item."""
        cmd = self.cmd_play_next
        self.player.request(cmd)

    def add(self):
        """Add the selected item to your playlist."""
        cmd = self.cmd_add
        self.player.request(cmd)

    def go(self):
        """
        :rtype: list
        :returns: command list for submenu

        Go to submenu i.e. list of tracks in playlist.
        """
        return self.cmd_from_action("go")

    @property
    def cmd_play(self):
        """
        :rtype: str
        :returns: command string to play selected item
        """
        return self._list_to_str(self.cmd_from_action("play"))

    @property
    def cmd_play_next(self):
        """
        :rtype: str
        :returns: command string to play selected item after currently \
        playing item
        """
        return self._list_to_str(self.cmd_from_action("add-hold"))

    @property
    def cmd_add(self):
        """
        :rtype: str
        :returns: command string to add selected item to playlist
        """
        cmd = self.cmd_from_action("add")
        #cmd += self.format_dict_cmd(self.menuitem["params"])
        return self._list_to_str(cmd)

    @property
    def show_items_cmd(self):
        """
        :rtype: str
        :returns: command string to show submenu items
        """
        cmd = self.go()
        return " ".join(str(x) for x in cmd)


class AudioMenuItem(PlaylistMenuItem):
    """Audio menu item. Basically the same as a playlist."""
    pass
