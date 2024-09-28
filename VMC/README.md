# AVR-2024/VMC
## Connecting to the Jetson
1. Make sure you have [Putty](https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html) installed
1. Connect to the `Varsity Bells` wifi network
    - Password is `May152006!`
2. Open the run dialogue on Windows or your terminal on any other machine
    - The run dialogue (<kbd>Windows</kbd> + <kbd>R</kbd>) keeps a history of previous commands, so if you value efficiency and automation I highly recommend using it
3. Run `putty.exe -ssh avr@drone -pw bellavr22`
4. You're in :sunglasses:

## Setting things up
This section contains instructions for setting up the repository on the **Jetson**. For the 2024 team, this has already been done. <br/><br/>
Run the following commands:

```bash
git clone --recurse-submodules https://github.com/Jurassic001/AVR-2024 ~/AVR-2024
cd ~/AVR-2024/VMC/scripts
chmod +x setup.py
./setup.py
```

Please note, this setup script WILL take a while the first time
(depending on your download speed).

<details>
<summary>If you have problems with the setup script, ensure that the following
domains are not blocked. Some schools or networks may restrict these:</summary>

```bash
# created with `sudo tcpdump -w dnsrequests.pcap -i any udp and port 53`
# and loaded into Wireshark

# code distribution
github.com
*.githubusercontent.com

# stereo labs camera configuration
*.stereolabs.com

# system packages and services
*.ubuntu.com
*.nvidia.com
api.snapcraft.io
*.launchpad.net
deb.nodesource.com

# python packages
pypi.python.org
pypi.org
files.pythonhosted.org

# Docker registries
*.docker.io
*.docker.com
nvcr.io
ghcr.io

# various CDN providers
*.cloudfront.net
*.akamaized.net
*.akamai.net
*.akamaiedge.net
*.fastly.net
*.edgekey.net
```

This may not be an exhaustive list, as upstream sources may change CDNs or domain names.
</details>

## Updating AVR Software on the Jetson
If you made changes to the AVR software, you can update the software using the following steps: <br/>

1. Use `git pull` while in the AVR-2024 repository root to download the changes from GitHub
    - You can use `git log` to verify that the local repository on the Jetson has been updated

2. Use the `start.py` script to run your desired software modules
    - `start.py` is the primary script for preforming actions on the AVR software modules. It is located in `AVR-2024/VMC`.
    - You need to put a `./` before all script names when you are running them in Linux. This would look like `./start.py`
    - `start.py` uses Docker to run our software modules as containers on the Jetson. You can read the AVR documentation on Docker [here](https://the-avr.github.io/AVR-2022/autonomy-and-beyond/docker/).

3. If `start.py` errors, re-run the setup script (`VMC/scripts/setup.py`)

<details><summary>Here is the syntax of start.py:</summary>

<br/>

It might look confusing, but for the most part you'll be sticking to the "build" and "run" actions. If you need to see this explanation again, add the `-h` option to your command execution

```console
start.py [-h] [-l] [-p, -b, -r, -s] [-m | -n | -a | -z | --sim] [modules ...]

options:
  -h, --help      show this help message and exit

  -l, --local     Build containers locally rather than using pre-built ones from GitHub. The apriltag, sandbox, pcm, and fcm modules will be built locally at all times

Action(s):
  The action(s) to perform on the specified modules. More than one action can be preformed in a single script execution (run order is: Pull -> Build -> Run -> Stop)

  -p, --pull      Pull containers that are pre-built by Bell so that they're available locally (has no effect on local-only modules)
  -b, --build     Build modules into runnable containers
  -r, --run       Run built software containers
  -s, --stop      Stop currently running containers. Will also delete docker-compose config files (that's a good thing)

mutually exclusive options:
  -m, --min       Perform action on minimal modules (fcm, fusion, mavp2p, mqtt, vio). Adds to any modules explicitly specified

  -n, --norm      Perform action on normal modules (apriltag, fcm, fusion, mavp2p, mqtt, pcm, status, thermal, vio). Adds to any modules explicitly specified. If nothing else is specified, this is the default

  -a, --all       Perform action on all modules (fcm, fusion, mavp2p, mqtt, pcm, sandbox, thermal, vio). Adds to any modules explicitly specified

  -z, --zephyrus  Perform action on all relevant modules for the 2024-25 Bell AVR Season (fcm, fusion, mavp2p, mqtt, pcm, sandbox,thermal, vio). Subtracts any modules explicitly specified

  --sim           Run system in simulation

positional arguments:
  modules         Explicitly list which module(s) to perform the action on
```
</details>

To stop the AVR software hit <kbd>Ctrl</kbd>+<kbd>C</kbd>

<br/>

#### Examples:
This will run all of the minimum modules required for flight in addition to the thermal & status modules
```sh
./start.py --run -m thermal status
```

This will pull, build, and run ALL modules
```sh
./start/py -pbr --all
```

This will build and run every module except for the apriltag and thermal modules
```sh
./start.py -br -m pcm status sandbox
```

<br/>

***

<!--
This stuff is finicky so its up to you if you use it or not
start.py will display the output of the containers while it is active, so I would just use that if you want to see logger commands and the like

### Viewing the output of software modules
To view currently running containers, run:
```bash
sudo docker ps
```
Add `-a` to the end of this command to view all containers, active and inactive

<br/>

To prune unused Docker containers, run:
```bash
sudo docker image prune
```
-->
