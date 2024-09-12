#!/usr/bin/python3

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import warnings
from typing import Any, List

import yaml

IMAGE_BASE = "ghcr.io/bellflight/avr/2022/"
THIS_DIR = os.path.abspath(os.path.dirname(__file__))


def check_sudo() -> None:
    # region sudo check
    # skip these checks on Windows
    if sys.platform == "win32":
        return

    # Check if Docker requires sudo
    result = subprocess.run(
        ["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    if result.returncode == 0:
        # either we have permission to run docker as non-root or we have sudo
        return

    # re run ourselves with sudo
    print("Needing sudo privileges to run docker, re-launching")

    try:
        sys.exit(
            subprocess.run(["sudo", sys.executable, __file__] + sys.argv[1:]).returncode
        )
    except PermissionError:
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(1)


def apriltag_service(compose_services: dict) -> None:
    # region apriltag
    apriltag_data = {
        "depends_on": ["mqtt"],
        "build": os.path.join(THIS_DIR, "apriltag"),
        "restart": "unless-stopped",
        "volumes": ["/tmp/argus_socket:/tmp/argus_socket"],
    }

    compose_services["apriltag"] = apriltag_data


def fcm_service(compose_services: dict, simulation=False) -> None:
    # region fcm
    fcm_data = {
        "depends_on": ["mqtt", "simulator" if simulation else "mavp2p"],
        "restart": "unless-stopped",
        "network_mode": "host",
        "privileged": True,
        "build": os.path.join(THIS_DIR, "fcm"),
        "volumes": ["/etc/machine-id:/etc/machine-id"],
    }

    compose_services["fcm"] = fcm_data

def simulator_service(compose_services: dict, local: bool = False) -> None:
    # region simulator
    sim_data = {
        "restart": "unless-stopped",
        "tty": True,
        "stdin_open": True,
        "ports": ["5760:5760/tcp","5761:5761/tcp", "14541:14541/udp"],
    }

    if local:
        sim_data["build"] = os.path.join(THIS_DIR, "simulator")
    else:
        sim_data["image"] = f"{IMAGE_BASE}simulator:latest"

    compose_services["simulator"] = sim_data


def fusion_service(compose_services: dict, local: bool = False) -> None:
    # region fusion
    fusion_data = {
        "depends_on": ["mqtt", "vio"],
        "restart": "unless-stopped",
    }

    if local:
        fusion_data["build"] = os.path.join(THIS_DIR, "fusion")
    else:
        fusion_data["image"] = f"{IMAGE_BASE}fusion:latest"

    compose_services["fusion"] = fusion_data


def mavp2p_service(compose_services: dict, local: bool = False) -> None:
    # region mavp2p
    mavp2p_data = {
        "restart": "unless-stopped",
        "devices": ["/dev/ttyTHS1:/dev/ttyTHS1"],
        "ports": ["5760:5760/tcp","5761:5761/tcp", "14541:14541/udp"],
        "command": "serial:/dev/ttyTHS1:500000 tcps:0.0.0.0:5760 tcps:0.0.0.0:5761 udps:0.0.0.0:14541",
    }

    if local:
        mavp2p_data["build"] = os.path.join(THIS_DIR, "mavp2p")
    else:
        mavp2p_data["image"] = f"{IMAGE_BASE}mavp2p:latest"

    compose_services["mavp2p"] = mavp2p_data


def mqtt_service(compose_services: dict, local: bool = False) -> None:
    # region mqtt
    mqtt_data = {
        "ports": ["18830:18830"],
        "restart": "unless-stopped",
    }

    if local:
        mqtt_data["build"] = os.path.join(THIS_DIR, "mqtt")
    else:
        mqtt_data["image"] = f"{IMAGE_BASE}mqtt:latest"

    compose_services["mqtt"] = mqtt_data


def pcm_service(compose_services: dict) -> None:
    # region pcm
    pcm_data = {
        "depends_on": ["mqtt"],
        "restart": "unless-stopped",
        "devices": ["/dev/ttyACM0:/dev/ttyACM0"],
        "build": os.path.join(THIS_DIR, "pcm"),
    }

    compose_services["pcm"] = pcm_data


def sandbox_service(compose_services: dict) -> None:
    # region sandbox
    sandbox_data = {
        "depends_on": ["mqtt"],
        "build": os.path.join(THIS_DIR, "sandbox"),
        "restart": "unless-stopped",
    }

    compose_services["sandbox"] = sandbox_data


def status_service(compose_services: dict, local: bool = False) -> None:
    # region status
    # don't create a volume for nvpmodel if it's not available
    nvpmodel_source = shutil.which("nvpmodel")

    status_data = {
        "depends_on": ["mqtt"],
        "restart": "unless-stopped",
        "privileged": True,
        "volumes": [
            {
                "type": "bind",
                "source": "/etc/nvpmodel.conf",
                "target": "/app/nvpmodel.conf",
            },
        ],
    }

    if nvpmodel_source:
        status_data["volumes"].append(
            {
                "type": "bind",
                "source": nvpmodel_source,
                "target": "/app/nvpmodel",
            }
        )
    else:
        warnings.warn("nvpmodel is not found")

    if local:
        status_data["build"] = os.path.join(THIS_DIR, "status")
    else:
        status_data["image"] = f"{IMAGE_BASE}status:latest"

    compose_services["status"] = status_data


def thermal_service(compose_services: dict, local: bool = False) -> None:
    # region thermal
    thermal_data = {
        "depends_on": ["mqtt"],
        "restart": "unless-stopped",
        "privileged": True,
    }

    if local:
        thermal_data["build"] = os.path.join(THIS_DIR, "thermal")
    else:
        thermal_data["image"] = f"{IMAGE_BASE}thermal:latest"

    compose_services["thermal"] = thermal_data


def vio_service(compose_services: dict, local: bool = False) -> None:
    # region vio
    vio_data = {
        "depends_on": ["mqtt"],
        "restart": "unless-stopped",
        "privileged": True,
        "volumes": [
            f"{os.path.join(THIS_DIR, 'vio', 'settings')}:/usr/local/zed/settings/"
        ],
    }

    if local:
        vio_data["build"] = os.path.join(THIS_DIR, "vio")
    else:
        vio_data["image"] = f"{IMAGE_BASE}vio:latest"

    compose_services["vio"] = vio_data

def prepare_compose_file(local: bool = False, simulation=False) -> str:
    # region prep compose
    # prepare compose services dict
    compose_services = {}

    apriltag_service(compose_services)
    fcm_service(compose_services, simulation)
    fusion_service(compose_services, local)
    mavp2p_service(compose_services, local)
    mqtt_service(compose_services, local)
    pcm_service(compose_services)
    sandbox_service(compose_services)
    thermal_service(compose_services, local)
    vio_service(compose_services, local)
    simulator_service(compose_services, local)

    # nvpmodel not available on Windows
    if os.name != "nt":
        status_service(compose_services, local)

    # construct full dict
    compose_data = {"version": "3", "services": compose_services}

    # write compose file
    compose_file = tempfile.mkstemp(prefix="docker-compose-", suffix=".yml")[1]

    with open(compose_file, "w") as fp:
        yaml.dump(compose_data, fp)

    # return file path
    return compose_file


def main(action: str, modules: List[str], local: bool = False, simulation: bool = False) -> None:
    # region main
    compose_file = prepare_compose_file(local, simulation)

    # run docker-compose
    project_name = "avr2024"
    if os.name == "nt":
        # for some reason on Windows docker-compose doesn't like upper case???
        project_name = project_name.lower()

    cmd = ["docker-compose", "--project-name", project_name, "--file", compose_file]

    if action == "build":
        cmd += ["build"] + modules
    elif action == "pull":
        cmd += ["pull"] + modules
    elif action == "run":
        cmd += ["up", "--remove-orphans", "--force-recreate"] + modules
    elif action == "stop":
        cmd += ["down", "--remove-orphans", "--volumes"]
    else:
        # shouldn't happen
        raise ValueError(f"Unknown action: {action}")

    print(f"Running command: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, cwd=THIS_DIR)

    def signal_handler(sig: Any, frame: Any) -> None:
        if sys.platform == "win32":
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            proc.send_signal(signal.SIGINT)

    signal.signal(signal.SIGINT, signal_handler)
    proc.wait()

    # cleanup
    # try:
    #     os.remove(compose_file)
    # except PermissionError:
    #     pass

    sys.exit(proc.returncode)


# sourcery skip: merge-duplicate-blocks, remove-redundant-if
if __name__ == "__main__":
    # region runtime
    check_sudo()

    min_modules = ["fcm", "fusion", "mavp2p", "mqtt", "vio"]
    norm_modules = min_modules + ["apriltag", "pcm", "status", "thermal"]
    all_modules = norm_modules + ["sandbox"]

    zephyrus_modules = all_modules
    zephyrus_modules.remove("apriltag")


    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-l",
        "--local",
        action="store_true",
        help="Build containers locally rather than using pre-built ones from GitHub",
    )

    parser.add_argument(
        "action", choices=["run", "build", "pull", "stop"], help="Action to perform"
    )
    parser.add_argument(
        "modules",
        nargs="*",
        help="Explicitly list which module(s) to perform the action one",
    )

    exgroup = parser.add_mutually_exclusive_group()
    exgroup.add_argument(
        "-m",
        "--min",
        action="store_true",
        help=f"Perform action on minimal modules ({', '.join(sorted(min_modules))}). Adds to any modules explicitly specified.",
    )
    exgroup.add_argument(
        "-n",
        "--norm",
        action="store_true",
        help=f"Perform action on normal modules ({', '.join(sorted(norm_modules))}). Adds to any modules explicitly specified. If nothing else is specified, this is the default.",
    )
    exgroup.add_argument(
        "-a",
        "--all",
        action="store_true",
        help=f"Perform action on all modules ({', '.join(sorted(all_modules))}). Adds to any modules explicitly specified.",
    )
    exgroup.add_argument(
        "-z",
        "--zephyrus",
        action="store_true",
        help=f"Perform action on all relevant modules for the 2024-25 Bell AVR Season ({', '.join(sorted(zephyrus_modules))}). Subtracts any modules explicitly specified.",
    )

    exgroup.add_argument(
        "-s",
        "--sim",
        action="store_true",
        help="Run system in simulation",
    )

    args = parser.parse_args()

    if args.zephyrus:
        # Modules specifically for the 2024-25 Bell AVR Season
        args.modules = [module for module in zephyrus_modules if module not in args.modules] # Remove modules in args.modules from zephyrus_modules
    elif args.min:
        # minimal modules selected
        args.modules += min_modules
    elif args.norm:
        # normal modules selected
        args.modules += norm_modules
    elif args.all:
        # all modules selected
        args.modules += all_modules
    elif not args.modules:
        # nothing specified, default to normal
        args.modules = norm_modules

    if args.sim:
        min_modules.remove("mavp2p")
        min_modules.append("simulator")

    args.modules = list(set(args.modules))  # remove duplicates
    main(action=args.action, modules=args.modules, local=args.local, simulation=args.sim)
