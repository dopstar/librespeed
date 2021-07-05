import argparse
import json
import logging
import sys
import urllib.parse

import librespeed.core
import librespeed.errors
import librespeed.ping


def parse_args():
    parser = argparse.ArgumentParser(usage="%(prog)s [options]")
    parser.add_argument(
        "-4", "--ipv4", action="store_true", help="Force IPv4 only (default: false)"
    )
    parser.add_argument(
        "-6", "--ipv6", action="store_true", help="Force IPv6 only (default: False)"
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Do not perform download test (default: False)",
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Do not perform upload test (default: False)",
    )
    parser.add_argument("--no-icmp", action="store_true", help="Do not use ICMP ping")
    parser.add_argument(
        "--concurrent",
        type=int,
        default=3,
        help="Concurrent HTTP requests being made (default: 3)",
    )
    parser.add_argument(
        "--bytes",
        action="store_true",
        help=(
            "Display values in bytes instead of bits. "
            "Does not affect the image generated by --share, "
            "nor output from --json or --csv (default: False)"
        ),
    )
    parser.add_argument(
        "--mebibytes",
        action="store_true",
        help="Use 1024 bytes as 1 kilobyte instead of 1000 (default: False)",
    )
    parser.add_argument(
        "--distance",
        default="km",
        help=(
            "Change distance unit shown in ISP info, "
            "use 'mi' for miles, 'km' for kilometres, 'NM' for nautical miles "
            "(default: 'km')"
        ),
    )
    parser.add_argument(
        "--share",
        action="store_true",
        help=(
            "Generate and provide a URL to the LibreSpeed.org share results image, "
            "not displayed with --csv (default: false)"
        ),
    )
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Suppress verbose output, only show basic information (default: False)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logging. (default: False)",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help=(
            "Show basic information in CSV format. "
            "Speeds listed in bit/s and not affected by --bytes. (default: False)"
        ),
    )
    parser.add_argument(
        "--csv-delimiter",
        default=",",
        help='Single character delimiter (CSV_DELIMITER) to use in CSV output. (default: ",")',
    )
    parser.add_argument(
        "--csv-header", action="store_true", help="Print CSV headers (default: false)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help=(
            "Suppress verbose output, only show basic information in JSON format. "
            "Speeds listed in bit/s and not affected by --bytes (default: false)"
        ),
    )
    parser.add_argument(
        "--list",
        dest="show_server_list",
        action="store_true",
        help="Display a list of LibreSpeed.org servers (default: false)",
    )
    parser.add_argument(
        "--server",
        dest="server_id_allow_list",
        nargs="+",
        type=int,
        help=(
            "Specify a SERVER ID to test against. "
            "Can be supplied multiple times. Cannot be used with --exclude."
        ),
    )
    parser.add_argument(
        "--exclude",
        dest="server_id_deny_list",
        nargs="+",
        type=int,
        help=(
            "Exclude a server from selection. "
            "Can be supplied multiple times. "
            "Cannot be used with --server."
        ),
    )
    parser.add_argument(
        "--server-json", help="Use an alternative server list from remote JSON file"
    )
    parser.add_argument(
        "--local-json",
        help=(
            "Use an alternative server list from local JSON file, "
            'or read from stdin with "--local-json -".'
        ),
    )
    parser.add_argument("--source", help="Source IP address to bind to")
    parser.add_argument(
        "--timeout", type=int, default=15, help="HTTP timeout in seconds (default: 15)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=15,
        help="Upload and download test duration in seconds (default: 15)",
    )
    parser.add_argument(
        "--chunk",
        type=int,
        default=100,
        help=(
            "Chunks to download from server, chunk size depends on server configuration "
            "(default: 100)"
        ),
    )
    parser.add_argument(
        "--upload-size",
        type=float,
        default=1024,
        help="Size of payload being uploaded in KiB (default: 1024)",
    )
    parser.add_argument(
        "--secure",
        dest="force_https",
        action="store_true",
        help=(
            "Use HTTPS instead of HTTP when communicating with LibreSpeed.org operated servers "
            "(default: false)"
        ),
    )
    parser.add_argument(
        "--skip-cert-verify",
        action="store_true",
        help=(
            "Skip verifying SSL certificate for HTTPS connections (self-signed certs) "
            "(default: false)"
        ),
    )
    parser.add_argument(
        "--no-pre-allocate",
        action="store_true",
        help=(
            "Do not pre allocate upload data. "
            "Pre allocation is enabled by default to improve upload performance. "
            "To support systems with insufficient memory, "
            "use this option to avoid out of memory errors "
            "(default: false)"
        ),
    )
    parser.add_argument(
        "--telemetry-json",
        help=(
            "Load telemetry server settings from a JSON file. "
            "This options overrides --telemetry-level, --telemetry-server, --telemetry-path, "
            "and --telemetry-share. Implies --share"
        ),
    )
    parser.add_argument(
        "--telemetry-level",
        help=(
            "Set telemetry data verbosity, available values are: "
            "disabled, basic, full, debug. Implies --share"
        ),
    )
    parser.add_argument(
        "--telemetry-server", help="Set the telemetry server base URL. Implies --share"
    )
    parser.add_argument(
        "--telemetry-path", help="Set the telemetry upload path. Implies --share"
    )
    parser.add_argument(
        "--telemetry-share", help="Set the telemetry share link path. Implies --share"
    )
    parser.add_argument(
        "--telemetry-extra",
        help="Send a custom message along with the telemetry results. Implies --share",
    )

    return parser.parse_args()


def cli():
    args = parse_args()

    if args.simple:
        log_level = logging.WARNING
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(
        stream=sys.stderr,
        level=log_level,
        format="[%(name)s][%(levelname)-8s] %(message)s",
    )

    logger = logging.getLogger(__name__)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)

    if args.show_server_list:
        server_filters = {}
    else:
        server_filters = {
            "server_allow_list": args.server_id_allow_list,
            "server_deny_list": args.server_id_deny_list,
        }

    try:
        server_list = librespeed.core.get_remote_servers(
            force_https=args.force_https, **server_filters
        )
    except librespeed.errors.HttpError:
        server_list = librespeed.core.get_remote_servers(
            force_https=args.force_https, retry=True, **server_filters
        )

    if args.show_server_list:
        for server in server_list:
            sponsor = server.get("sponsorName") or ""
            if sponsor and server.get("sponsorURL"):
                sponsor += f" @ {server['sponsorURL']}"
            if sponsor:
                sponsor = f"[Sponsor: {sponsor}]"
            print("{id}: {name} ({server}) {sponsor}".format(sponsor=sponsor, **server))
        return

    if args.server_id_allow_list:
        librespeed.core.do_speed_test(server_list)
    else:
        logger.info("Selecting the fastest server based on ping")
        results = librespeed.ping.do_icmp_ping(
            [urllib.parse.urlsplit(s["server"]).netloc for s in server_list]
        )
        results = librespeed.ping.order_ping_results_by_rtt(results)
        fastest_domain = results[0]["domain"]
        fastest_servers = [
            s
            for s in server_list
            if urllib.parse.urlsplit(s["server"]).netloc == fastest_domain
        ]
        results = librespeed.core.do_speed_test(fastest_servers)
        logger.info("results: %s", results)


if __name__ == "__main__":
    cli()
