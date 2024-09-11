# Peripheral Control Computer Firmware

## Setup

Run

```bash
python setup.py
```

## Building

To build the firmware, run

```bash
python build.py
```

This will create a `pcc_firmware.<hash>.bin` file in `PCC/.pio/build/adafruit_feather_m4`.

## Flashing

Follow the instructions in the documentation, or use the upload functionality
in PlatformIO directly.

## Firmware .bin files
I've taken the liberty of storing PCC firmware in the `Firmware .bin files` directory. These files are copies of built firmware, in case you need to rollback from a bad firmware build. I'll document each firmware version here. To write the firmware file of your choosing into the PCC, read [this page from the AVR assembly guide](https://the-avr.github.io/AVR-2022/peripheral-control-computer/flash-the-pcc/).

### Stored firmware docs
#### [bell_firmware.09-22-2022](<Firmware .bin files/bell_firmware.09-22-2022.bin>)
This is copy of the Bell-provided firmware from [AVR release page](https://github.com/The-AVR/AVR-2022/releases/tag/stable). It is the most recent firmware as of 9/10/2024, and **DOES NOT** support features like PCC stacking or magnet control.
#### [stacked_pcc_firmware.final](<Firmware .bin files/stacked_pcc_firmware.final.bin>)
This is the firmware written by [Quentin Balestri](https://github.com/Aias0) for the 2023 Bell AVR competition. This version of the firmware enables stacking two PCCs on top of each other, for a total of 16 servo pins instead of the usual 8.
#### [magnet_control_firmware.v1](<Firmware .bin files/magnet_control_firmware.v1.bin>)
This is the first version of the firmware written by [Max Haberer (that's me!)](https://github.com/Jurassic001). This version supports "magnet control", which lets you grant uninterrupted power passthrough to the high power load terminals of the MOSFET, unlike the regular "pulsing" operation of the terminal which controls the rate of the AVR laser's firing. This is intended to be used to control a magnet attached to the drone, allowing you to pick up and place magnetic objects at will.