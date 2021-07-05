import json
import logging
import time
import urllib.parse

import requests
import requests.exceptions

import librespeed.constants
import librespeed.errors
import librespeed.utils


logger = logging.getLogger(__name__)


def get_remote_servers(
    url=None,
    server_allow_list=None,
    server_deny_list=None,
    force_https=False,
    retry=False,
):
    """
    fetches remote server list

    :return: list of remote servers.
    """

    server_allow_list = set(server_allow_list or [])
    server_deny_list = set(server_deny_list or [])
    if server_allow_list.intersection(server_deny_list):
        raise librespeed.errors.ParameterConflictError(
            "specifying servers both in the allow list and in the deny list is not allowed."
        )

    url = url or librespeed.constants.SERVER_LIST_URL

    if retry:
        well_known_part = "/.well-known/librespeed"
        url += well_known_part
        logger.info(f"retry with {well_known_part!r}")
    else:
        logger.info(f"retrieving server list from {url!r}")

    response = requests.get(url)

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise librespeed.errors.HttpError(e)

    servers = []
    for server in response.json():
        if server_allow_list and server["id"] not in server_allow_list:
            continue
        if server["id"] in server_deny_list:
            continue

        if force_https:
            server["server"] = librespeed.utils.change_scheme(server["server"], "https")
        servers.append(server)
    return servers


def get_isp_info(server):
    url = urllib.parse.urljoin(server["server"], "getIP.php")
    response = requests.get(url, params={"isp": "true", "distance": "km"})
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise librespeed.errors.HttpError(str(e))
    return response.json()


def do_speed_test(servers):
    logger.info(f"doing speed tests on server(s): {servers!r}")
    results = []
    for server in servers:
        server["server"] = librespeed.utils.insert_scheme(server["server"], "https")
        result = {"server": {"url": server["server"], "name": server["name"]}}
        isp_info = get_isp_info(server)
        if isp_info and isp_info.get("rawIspInfo"):
            isp_info["rawIspInfo"].pop("asn", None)
            result["client"] = isp_info["rawIspInfo"]

        stats = []
        for _ in range(5):
            stats.append(download(server))
            time.sleep(0.1)

        result.update(
            {
                "download_speed_mbps": sum(s["download_speed_mbps"] for s in stats)
                / len(stats),
                "bytes_received": sum(s["bytes_received"] for s in stats),
            }
        )

        results.append(result)
    return results


def download(server):
    url = urllib.parse.urljoin(server["server"], server["dlURL"])
    headers = {"Accept-Encoding": "identity"}

    start = time.time()
    response = requests.get(url, headers=headers, stream=True)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise librespeed.errors.HttpError(str(e))

    byte_count = 0
    tic = time.time()
    mini = []
    for chunk in response.iter_content(chunk_size=2048):
        toc = time.time()
        duration = toc - tic
        mini += [((len(chunk) * 8) / duration) * 1e-6]
        byte_count += len(chunk)
        if not chunk:
            break
        tic = time.time()

    download_time = time.time() - start
    return {
        "download_speed_mbps": round(((byte_count * 8) / download_time) * 1e-6, 2),
        "bytes_received": byte_count,
    }
