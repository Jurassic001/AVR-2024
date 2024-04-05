# AVR-2024
<!--
## Project Management

For Bell employees and partners, work items are tracked on [Trello](https://trello.com/bellavr).
-->
## Structure

- `.github`: GitHub Actions files
- `.vscode`: VS Code settings
- `GUI`: All-in-one GUI
- `PCC`: PCC firmware
- `PX4`: PX4 and MAVLink files
- `scripts`: Development scripts
- `VMC`: VMC flight software

Documentation is located on the `docs` branch.

## To do
- Add ability to toggle between auto-aim and manual laser control
- Change auto-aim logic to use real math (need a cheeky distance sensor)
- Add support for multiple lasers in auto-aim (need to factor in laser position for auto aim calcs)
- Add ability to switch between window size options with +/- keys

## Developer Setup

To do development work, you'll want to have Docker setup, along with Python 3.9
with the `venv` module.

<!--
No Linux users on the team

If you need to install Python 3.9 on Linux, do the following:

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3-pip python3.9 python3.9-venv
sudo -H python3.9 -m pip install pip wheel --upgrade
```
-->
If you want to build/run Docker images not on a Jetson, run

```bash
docker run --rm --privileged docker.io/multiarch/qemu-user-static --reset -p yes
```

once first.

Refer to individual module README files for specific instructions.

<!--
This repo was setup when you setup the parent repo initially

### Repo Setup

Clone the repository with submodules:

```bash
git clone --recurse-submodules https://github.com/bellflight/AVR-2022
cd AVR-2022
```

If you already have the repo cloned, run

```bash
git submodule update --init --recursive
```

to initialize and/or update the submodules.
-->
### VS Code Setup

<!--
Who actually uses git pull? VSCode Source Control anyone?

We recommend setting `git.pullTags` to `false` in VS Code workspace settings
to prevent tag errors when doing `git pull`, along with installing the
recommended extensions.
-->
Install the recommended extensions. If you don't see a popup in the bottom right corner of your screen, go to the VSCode extensions tab and type `@recommended` into the search bar

### Python Setup

You can (perchance) run these commands in sequence, in the VSCode Powershell terminal <br/>
(Make sure you're in the AVR-2024 repo, NOT HPBell_2024-25. The first command will try to open AVR_2024 if you're in HPBell) <br/>
Note: This will take 10-15 minutes
```bash
cd AVR/AVR-2024
py -m venv .venv
.venv\Scripts\Activate
py scripts/install_requirements.py
```
<!--
My way or the high way (jk, I'm reducing visual clutter)

#### The long & hard way:
Create a Python 3.9 virtual environment (Make sure you're creating the venv in AVR-2024, not the parent repo):

```bash
py -m venv .venv # Windows
python3.9 -m venv .venv # Linux
```

Activate the virtual environment:

```powershell
.venv\Scripts\Activate # Windows
source .venv/bin/activate # Linux
```

Finally, you can install all the dependencies so you get autocomplete and type hinting:

```bash
python scripts/install_requirements.py
```
-->
## Running Containers on a Jetson

If on a Jetson, clone the repository and check out the git branch you want.
You can now follow the instructions inside
[VMC/README.md](VMC/README.md) to run the `setup.py`
script and add `--dev` for development.

Note, with `start.py` commands, make sure to add `--local` to the command.
This builds the Docker images locally rather than using prebuilt ones from GitHub CR.
