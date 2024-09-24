import argparse
import os
import subprocess
import sys
from pathlib import Path

# set up color codes
RED = "\033[0;31m"
LIGHTRED = "\033[1;31m"
GREEN = "\033[0;32m"
LIGHTGREEN = "\033[1;32m"
CYAN = "\033[0;36m"
NC = "\033[0m"  # No color


# set up method for formatting terminal output
def disp_added_sidebars(text: str = "", color_code: str = NC) -> None:
    """Adds "sidebars" in the form of `=` to each side of a string and prints it

    Args:
        text (str, optional): The string blessed with "sidebars". Leaving this blank will print a full line of `=`
        color_code (str, optional): Escape code of a certain color to wrap the text in. Leaving this blank will not color the text
    """
    # Check to see if standard output is connected to a terminal. If yes get the terminal width, otherwise set a default value
    terminal_width = os.get_terminal_size().columns if os.isatty(sys.stdout.fileno()) else 80

    if not text:
        msg = "=" * terminal_width
    else:
        void_len = len(text) + 2  # Define the "void" area where the string will go
        sidebar_len = (terminal_width - void_len) // 2  # Define the length of a single sidebar
        sidebar = "=" * sidebar_len  # Make the sidebars
        msg = f"{sidebar} {color_code}{text}{NC} {sidebar}"
    print(msg)


def main(directory: str, strict: bool = False) -> None:
    # define the parent directory path, which is used to represent the location of each requirements.txt file relative to the specified directory
    PARENT_PATH = Path(os.path.join(os.path.dirname(directory), ".")).resolve()

    # make sure pip and wheel are up-to-date
    disp_added_sidebars("Pre-execution checks", CYAN)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "wheel", "pip", "--upgrade"],
        check=True,
    )

    # check if we're outside a virtual environment and container and CI
    if (
        sys.base_prefix == sys.prefix  # no virtual environment
        and not os.path.exists("/.dockerenv")  # no container
        and os.getenv("CI") is None  # no github actions
        and os.getenv("BUILD_BUILDID") is None  # no azure pipelines
    ):
        print("Not inside a docker container or virtual environment, exiting")
        sys.exit(1)

    # install dev tools
    disp_added_sidebars("Installing dev tools", CYAN)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            os.path.join(os.path.dirname(__file__), "..", "requirements.txt"),
        ],
        check=True,
    )

    # Install requirements.txt recursively
    for filepath in Path(directory).glob("**/requirements*.txt"):
        # don't install any requirements.txt files that may be in the virtual env
        # or in the PX4 temp directory
        if ".venv" in str(filepath):
            continue

        local_path = f"{filepath.relative_to(PARENT_PATH)}"

        disp_added_sidebars(local_path, CYAN)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-r",
                str(filepath.absolute()),
            ],
            check=strict,
        )
    disp_added_sidebars("Requirement installation successful", GREEN)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--directory",
        "-d",
        type=str,
        default=os.path.join(os.path.dirname(__file__), ".."),
        help="Directory to walk. Defaults to repo root",
    )
    parser.add_argument(
        "--strict",
        "-s",
        action="store_true",
        help="Fail if requirements.txt could not installed",
    )

    args = parser.parse_args()
    args.directory = os.path.abspath(args.directory)

    main(args.directory, args.strict)
