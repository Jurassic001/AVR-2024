# AVR-2024/VMC
## Setup
This section contains instructions for setting up the repository on the Jetson. For the 2024 team, this has already been done. <br/><br/>
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
### Updating AVR Software
If you made changes to the AVR software, you can update the container using the following steps: <br/>
1. Use `git pull` while in the AVR-2024 repository root to download the changes from GitHub
2. Re-run the `./setup.py` script. This will automatically build the software modules. Once this script finishes you can (optionally) reboot your Jetson
3. Use `./start.py run -a` (documentation below) to run the AVR software
<!-- Here is the official AVR documentation on updating your software. I've modified the ./setup.py command to build/run all modules instead of just the "normal" modules. I might modify it again in the future so you can select what modules you want to build/run, similar to the way that the start.py command works.

If you ever need to update the AVR software, run:
```bash
# Update the git repo
git pull
# Re-run the setup script
./setup.py
```
-->
***
### Building, running, and viewing software containers
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
Note the `-a` option, this means that all modules will be built

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
This will stop all active AVR software modules <!--Use caution, the stop command and stop keybind are ever-so-slightly different in their effect.-->
<br/>
<!--
**IMPORTANT**: Use `./start.py -h` to see the full start.py syntax
-->
***

### Making changes to the AVR software
`./setup.py` has the option `--dev`. This option makes it so that containers will be built/run from the files inside of the VMC folder, instead of using the pre-built containers from GitHub from GitHub. <br/>
Sandbox is automatically built and run from the local files, so don't worry about that. I've noticed some weird behavior with this option, i.e. the Apriltags module might build locally even when the option isn't used. <br/>
For the most part you don't really need to use this option, and I personally advise against making any changes to the AVR software modules. <br/><br/>
`./start.py` also has a similar option, `-l`, or `--local`. If you do modify the AVR software modules (other than sandbox), you should only locally build containers that you've made changes to. Locally building containers that you haven't made any changes to will take longer than using pre-build images and could lead to bugs and other issues. <br/><br/>
For this reason, I **advise against** using the `--dev` option. Instead, run `./setup.py` normally, and locally build/run the modified software modules using the `./start.py` command after.
***
### Examples
You can specify certain containers by declaring them as folows:
```bash
./start.py run thermal status -m
```
this will run all of the minimum modules required for flight `-m = [fcm, fusion, mavp2p, mqtt, vio]` in addition to the thermal & status modules.