# AVR-2024/VMC
## Setup
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

If you have problems with the setup script, ensure that the following
domains are not blocked. Some schools or networks may restrict these:

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

## Usage
### Updating AVR Software on the Jetson
If you made changes to the AVR software, you can update the software using the following steps: <br/>

1. Use `git pull` while in the AVR-2024 repository root to download the changes from GitHub
    - Use `git log` to verify that the local repository on the Jetson has been updated

2. Run the `setup.py` script. This will automatically build all software modules and apply important updated to your VMC. Once this script finishes you should reboot your Jetson (It will give you the option)
    - This script is located in `AVR-2024/VMC/scripts`
    - You need to put a `./` before all script names when you are running them in Linux. This would look like `./setup.py`

3. Use the `start.py` script to run your desired software modules
    - `start.py` is the primary script for preforming actions on the AVR software modules. It is located in `AVR-2024/VMC`

Here is the syntax of the `start.py` command. It might look confusing, but for the most part you'll be sticking to the "run" action

```bash
start.py {build/run/stop} [MODULES...] [-m | -n | -a]


positional arguments:
    {build/run/stop}             Either build, run, or stop the specified modules

keyword arguments:
    [MODULES...]             You can add specific software modules to your command execution. Just type the module name(s), with a space in between each name

options:
    -m, --min             Perform action on minimual modules (fcm, fusion, mavp2p, mqtt, vio). This is the bare minimum for flight

    -n, --norm            Perform action on normal modules (minimal modules, apriltag, pcm, status, thermal). This is what you will need for scoring. If nothing else is specified, this is the default

    -a, --all             Perform action on all modules (normal modules + sandbox). Sandbox is the module you need for autonomous control and some other functions like apriltag LED flashing
```
<br/>

#### Examples:
This will run all of the minimum modules required for flight in addition to the thermal & status modules
```bash
./start.py run thermal status -m
```
<br/>

This will run every module except for the apriltag and thermal modules
```bash
./start.py run pcm status sandbox -m
```

<br/>

***

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