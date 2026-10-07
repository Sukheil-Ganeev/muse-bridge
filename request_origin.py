"""Allow only local browser origins and loopback Host authorities."""

from urllib.parse import urlsplit
import logging


_LOOPBACK_HOSTS = {"localhost", "127.0.0.1"}


def _matches_local_authority(parts, expected_port, default_port):
    if (parts.username is not None or parts.password is not None
            or parts.path or parts.query or parts.fragment):
        return False
    if (parts.hostname or "").lower() not in _LOOPBACK_HOSTS:
        return False
    try:
        actual_port = parts.port
    except ValueError as _exc:
        logging.getLogger(__name__).debug("suppressed %s", _exc)
        return False
    if actual_port is None:
        if default_port is None:
            return True
        actual_port = default_port
    return actual_port == expected_port


def is_trusted_local_request(headers, expected_port):
    """Reject foreign browser origins and non-loopback Host values.

    Native local clients commonly omit Origin, so its absence is allowed. A
    supplied Host or Origin must identify this loopback HTTP service.
    """
    get_all = getattr(headers, "get_all", None)
    if get_all is not None and any(
            len(values) > 1
            for values in (get_all("Host") or [], get_all("Origin") or [])):
        return False

    host = headers.get("Host")
    if host is not None:
        try:
            host_parts = urlsplit("//" + host)
        except ValueError as _exc:
            logging.getLogger(__name__).debug("suppressed %s", _exc)
            return False
        if not _matches_local_authority(host_parts, expected_port, None):
            return False

    origin = headers.get("Origin")
    if origin is None:
        return True
    try:
        origin_parts = urlsplit(origin)
    except ValueError as _exc:
        logging.getLogger(__name__).debug("suppressed %s", _exc)
        return False
    if origin_parts.scheme.lower() != "http" or not origin_parts.netloc:
        return False
    return _matches_local_authority(origin_parts, expected_port, 80)
