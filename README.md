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

- Diagnose sandbox errors
- ~~Fix error when enabling all servos on VMC control page~~
- ~~Add stop buttons to VMC control page~~
- Overhaul the Docker instructions

### Brainstorming

- Change auto-aim logic to use real math (need a cheeky distance sensor)
- Add support for multiple lasers in auto-aim (need to factor in laser position for auto aim calcs)

## Repo Setup
<!--
All this should already be done

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
### VSCode Setup

<!--
We recommend setting `git.pullTags` to `false` in VS Code workspace settings
to prevent tag errors when doing `git pull`, along with installing the
recommended extensions.
-->
Install the recommended extensions. If you don't see a popup in the bottom right corner of your screen, go to the VSCode extensions tab and type `@recommended` into the search bar

### Python Setup

You can run these commands in sequence, in the VSCode Powershell terminal <br/>
(Make sure you're in the AVR-2024 repo, NOT HPBell_2024-25. Come talk to Max if you have any questions) <br/>
Note: This will take 10-15 minutes
```bash
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

## Developer Setup
To do development work, you'll want to have Docker setup, along with Python 3.9
with the `venv` module.

If you want to build/run Docker images not on a Jetson, run

```bash
docker run --rm --privileged docker.io/multiarch/qemu-user-static --reset -p yes
```

once first.

Refer to individual module README files for specific instructions.

## Running Containers on a Jetson

If on a Jetson, clone the repository and check out the git branch you want.
You can now follow the instructions inside
[VMC/README.md](VMC/README.md) to run the `setup.py`
script and add `--dev` for development.

Note, with `start.py` commands, make sure to add `--local` to the command.
This builds the Docker images locally rather than using prebuilt ones from GitHub CR.