#!/bin/bash

# 1. Stop the DATA collection service to free the Modbus port
sudo systemctl stop omron-data.service
sudo systemctl stop omron-monitoring.service

# 2. Wait for the hardware port to clear
sleep 5

# 3. RUN THE RESET
# Using system python as per your requirement
/usr/bin/python3 /home/reigicad/DenryokuKanshi/omron_reset.py

sleep 5

# 4. Start the data collection service back up
sudo systemctl start omron-data.service
sudo systemctl start omron-monitoring.service
