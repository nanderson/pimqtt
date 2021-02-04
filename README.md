# pimqtt
Basic RaspberryPi to MQTT command client. Technically this could be used on any system.


The idea for this was inspired by the building of a remotely installed RPi that only has a 3/4G data connection. I wanted something that 



- Listen for commands
- Respond
- Use PiCamera (respond on different topic)


# Installation
- apt-get install rpi.gpio python3 python3-pip
- sudo install.sh
- edit /etc/pimqtt.conf
- systemctl start pimqtt.service


# To-Do:
- [ ] mqtt birth & death messsages
- [ ] installer argument to skip pip3 installs
- [ ] move logging config into config file
- [ ] implement missing commands
- [ ] implement scheduled data purging
- [ ] implement periodic simple health messages
- [ ] investigate service auto-restart?
- [ ] add a "hello" message when the service starts
- [ ] code clean-up: abstractions, classes, style etc. the codebase is a mess
- [ ] etc/tmpfiles.d/pimqtt.conf assum,ed a forced tmp file target, make this more dynamic


# commands to listen for:
- ping
- get-photo (get photo using RPi Camera, optional parameters)
- status (uptime, load, network, disk/memory usage, temperature/sensors, and any basic stuff)
- reboot (shutdown -r now)
- flush-images (remove all images in configured tmp image folder just in case disk is full)


# config entries:
- mqtt connection details
- mqtt topic to listen for commands
- mqtt topic to respond to commands
- enable/disable picamera (disabled by default)
- mqtt topic to respond with picamera images (different from command responses because of binary) (also put a command response message)
- tmp folder to store picamera images
- max days to keep picamera images (used by crontab script for daily cleanup)
- heartbeat frequency in minutes (0 = disable)


# Inspiration from:
- Install script inspired by https://gist.github.com/m-radzikowski/53e0b39e9a59a1518990e76c2bff8038
- Basics of the mqtt code inspired by: https://www.hackster.io/robin-cole/pi-camera-doorbell-with-notifications-408d3d
- Systemd confis stuff from: https://tecadmin.net/setup-autorun-python-script-using-systemd/
