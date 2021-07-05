import logging
import re
import subprocess
import time


logger = logging.getLogger(__name__)


def do_icmp_ping(targets, count=1, ipv6=False, batch_size=8):
    print("targets: %s" % (len(targets)))
    tic = time.time()
    if ipv6:
        cmd = ["ping6"]
    else:
        cmd = ["ping"]

    cmd += ["-c", str(count)]

    results = {}

    jobs = {}
    for target in targets[:batch_size]:
        jobs[target] = subprocess.Popen(
            cmd + [target], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

    targets = targets[batch_size:]
    while True:
        key = None
        for k, proc in jobs.items():
            if proc.poll() is not None:
                results[k] = proc
                key = k
                break
        else:
            continue

        if key:
            del jobs[key]

        if targets:
            target = targets.pop()
            jobs[target] = subprocess.Popen(
                cmd + [target], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
        else:
            for k, proc in jobs.items():
                proc.wait()
                results[k] = proc
            break

    print("time: %s" % (time.time() - tic))
    return {k: (proc.returncode,) + proc.communicate() for k, proc in results.items()}


def do_http_ping():
    pass


def order_ping_results_by_rtt(results):
    regex = re.compile(r"time=(\d+(?:\.\d+)?)\sms")
    new_results = []
    for target, result in results.items():
        return_code, std_out, std_err = result
        if return_code == 0:
            rtt_list = [float(rtt) for rtt in regex.findall(std_out.decode()) if rtt]
            if not rtt_list:
                logger.warning(f"no rtt for {target!r}")
                continue
            avg_rtt = sum(rtt_list) / len(rtt_list)
            new_results.append({"domain": target, "rtt": avg_rtt})
        else:
            logger.debug(f"icmp ping failed for {target!r}")

    return sorted(new_results, key=lambda k: k["rtt"])


def _get_rtt_from_icmp_ping_results():
    pass
