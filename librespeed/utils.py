import logging
import urllib.parse


logger = logging.getLogger(__name__)


def change_scheme(url, new_scheme):
    """
    switch url scheme to the specified scheme

    :param url: url string.
    :param new_scheme: new scheme to switch to.
    :return: new url string.
    """

    allowed_schemes = ["http", "https"]

    if not new_scheme or new_scheme.lower() not in ("http", "https"):
        logger.warning(f"supported schemes are {allowed_schemes}, not {new_scheme!r}")
        new_url = url
    else:
        new_url = urllib.parse.urlunsplit(
            (new_scheme,) + urllib.parse.urlsplit(url)[1:]
        )

    logger.debug(f"switched from {url!r} to {new_url!r}")
    return new_url


def insert_scheme(url, scheme):
    """
    adds scheme on a url that doesnt have a scheme

    :param url:
    :param scheme:
    :return:
    """

    if urllib.parse.urlsplit(url).scheme:
        return url
    return change_scheme(url, scheme)
