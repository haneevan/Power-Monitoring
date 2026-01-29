#!/bin/bash

# 1. Stop the service so the port is free
# This is critical to avoid the "Slave Device Busy" (Exception 6) error.
sudo systemctl stop omron-monitoring.service

# 2. Wait for the hardware port to clear
sleep 2

# 3. RUN THE RESET using the SYSTEM Python
# We are NOT using the venv here because the library version inside 
# the venv is incompatible with your current omron_reset.py code.
/usr/bin/python3 /home/reigicad/DenryokuKanshi/omron_reset.py

# 4. Start the service back up
sudo systemctl start omron-monitoring.service
