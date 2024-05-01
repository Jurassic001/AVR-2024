# AVR-2024/VMC
<!--
Once again this stuff is already done for us (setup.py has been run on the drone)

## Setup

Run the following commands:

```bash
git clone --recurse-submodules https://github.com/bellflight/AVR-2022 ~/AVR-2022
cd ~/AVR-2022/VMC/scripts
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
-->
## Usage

**IMPORTANT**: Use `./start.py -h` to see the full syntax & config options

To view currently running containers, run:
```bash
docker ps
```
Add `-a` to the end of this command to view all containers, active and inactive

<br/>

To build the AVR software on the Jetson, run:
```bash
./start.py build -a
```
Note the `-a` option, this means that all modules will be built. **If you make changes to a module, you'll need to rebuild it.** See specific examples below.

<br/>

To start the AVR software, run:
```bash
./start.py run -a
```

<br/>

To stop the AVR software hit <kbd>Ctrl</kbd>+<kbd>C</kbd>, or run:
```bash
./start.py stop -a
```
This will stop all active AVR software modules when run. Use caution, the stop command and stop keybind are ever-so-slightly different in their effect.
<br/><br/><br/>
Once you've built/run the software once, the software will automatically start running when the Jetson is turned on.<br/>

### Building from local

`./start.py` has the option `-l`, or `--local`. This option makes it so that containers will be built/run from the files inside of the VMC folder, instead of using the pre-built containers from GitHub from GitHub. <br/>
Sandbox is automatically built and run from the local files, so don't worry about that. I've noticed some weird behavior with this option, i.e. the Apriltags module might build locally even when the option isn't used. <br/>
For the most part you don't really need to use this option, and I personally advise against making any changes to the AVR software modules. <br/>
Note that you shouldn't overuse this option, only locally build containers that you've made changes to. Locally building containers that you haven't made any changes to will take longer than using pre-build images and could lead to bugs and other issues.

### Examples
You can specify certain containers by declaring them as folows:
```bash
./start.py run thermal status -m
```
this will run all of the minimum modules required for flight `-m = [fcm, fusion, mavp2p, mqtt, vio]` in addition to the thermal & status modules.

<br/>

If you made changes to the sandbox module, you can update the container using the following steps: <br/>
1. Use `git fetch` while in the AVR-2024 repository root to download the changes from GitHub..
2. Use the stop command to stop all software modules. This is imperative to updating the software.
3. Use the commands listed in the usage section to build/run every module. Since you stopped every module, you need to restart every module. The terminal should be flooded with feedback from the AVR software.

Here is an all-in-one command for updating all software modules, from the root of the Jetson:
```bash
cd AVR-2024
git fetch
cd VMC
./start.py stop -a
./start.py build -a
./start.py run -a
```
Beware this might not work with your system. Make sure that you understand `./start.py`, docker containers, and the AVR software before running this command, and consult your team captain.

<!--
## Misc

Not sure if this is reffering to an update that bell might implement or an update that the user makes. So far I've seen no indication that you need to re-run the setup script after every update to the software.

If you ever need to update the AVR software, run:

```bash
# Update the git repo
git pull
# Re-run the setup script
./setup.py
```
-->