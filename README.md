# AVR-2024
## Structure

- `.github`: GitHub Actions files
- `.vscode`: VS Code settings
- `GUI`: All-in-one GUI
- `PCC`: PCC firmware
- `PX4`: PX4 and MAVLink files
- `scripts`: Development scripts
- `VMC`: VMC flight software

## Repo Setup
<!--
This is done when you clone the HPBell repo that contains ALL code for RVR, DEXI, etc.
If you only specifically want the AVR-2024 repo, then follow these steps.

Clone the repository with submodules:

```bash
git clone --recurse-submodules https://github.com/Jurassic001/AVR-2024
cd AVR-2024
```

If you already have the repo cloned, run

```bash
git submodule update --init --recursive
```

to initialize and/or update the submodules.
-->
### VSCode Setup

<!--
Our repo doesn't have tags (we don't do releases) so this point is moot

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

## Development Setup
### Jetson Development
Follow the instructions inside
[VMC/README.md](VMC/README.md) to build & run the AVR software on the Jetson

### Local Development
If you want to build/run Docker images not on a Jetson, look at [VMC/Docker_instructions.md](VMC/Docker_instructions.md)