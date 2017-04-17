try:
    import urllib.parse
    urlmodule = urllib.parse
except ImportError:
    import urllib
    urlmodule = urllib


class LMSUtils(object):

        def quote(self, text):
            return urlmodule.quote(text)

        def unquote(self, text):
            return urlmodule.unquote(text)
