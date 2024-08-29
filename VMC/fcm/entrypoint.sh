#!/bin/bash

# Start device network manager service
service network-manager start &

# Wait for a moment to ensure NetworkManager is up
sleep 5

sleep 10 #to allow sim to finish booting in case where running in sim

python fcc_telemetry.py &

sleep 5

python fcc_control.py &

sleep 5

python fcc_hil_gps.py