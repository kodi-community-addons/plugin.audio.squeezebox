"""
Logitech Media Server discovery
===============================

.. NOTE::

    Unfortunately I don't remember where I found this script so I can't give the \
    credit it deserves.

    My updates were very very minor!
"""
import socket
import threading
import re

DISCOVERY_PORT = 3483
DEFAULT_DISCOVERY_TIMEOUT = 5


class LMSDiscovery(object):
    """Class to discover Logitech Media Servers connected to your network."""

    def __init__(self):
        self.entries = []
        self.last_scan = None
        self._lock = threading.RLock()

    def scan(self):
        """
        Scan the network for servers.

        After running, any servers will be stored in :attr:`entries`.
        """
        with self._lock:
            self.update()

    def all(self):
        """
        Scan and return all found entries.

        :rtype: list
        :returns: list of servers found. Each server is a dict.

        Example:

        .. code-block:: python

          >>>from LMSTools import LMSDiscovery
          >>>LMSDiscovery().all()
          [{'data': 'EJSON\x049000',
            'from': ('192.168.0.1', 3483),
            'host': '192.168.0.1',
            'port': 9000}]

        """
        self.scan()
        return list(self.entries)

    def update(self):
        lms_ip = '<broadcast>'
        lms_port = DISCOVERY_PORT

        # JSON tag has the port number, it's all we need here.
        lms_msg = "eJSON\0"
        lms_timeout = DEFAULT_DISCOVERY_TIMEOUT

        entries = []

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(lms_timeout)
        sock.bind(('', 0))

        try:
            sock.sendto(lms_msg, (lms_ip, lms_port))

            while True:
                try:
                    data, server = sock.recvfrom(1024)
		    host, _ = server
                    if data.startswith(b'E'):
                        port = data.split("\x04")[1]
                        entries.append({'port': int(port),
                                        'data': data,
                                        'from': server,
                                        'host': host})
                except socket.timeout:
                    break
        finally:
            sock.close()
        self.entries = entries
