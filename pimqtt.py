#!/usr/bin/env python3

# combine the MQTT and RF receive codes 
import paho.mqtt.client as mqtt 
import paho.mqtt.publish as publish 
import sys 
import os
import random
import time 
import logging 
from datetime import datetime
import configparser
#import urlparse
import ssl
import platform
import psutil
import socket
import json

logging.basicConfig(level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S', format='%(asctime)-15s - [%(levelname)s] %(module)s: %(message)s', ) 

try:
    import picamera 
    logging.info("Successfully imported picamera")
except ImportError:
    # must not be on a pi or can't find library, need to disable the camera in the config
    logging.error("Error importing picamera")
    pass


try:
    camera = picamera.PiCamera()
except NameError:
    pass
except PiCameraError as err:
    logging.error("Error loading picamera: " + err)
    camera = False
    pass

config = configparser.ConfigParser()
config.read('/etc/pimqtt.conf')

# MQTT Connection
MQTT_HOST = config.get("mqtt_host", "host")
MQTT_PORT = int(config.get("mqtt_host", "port"))
MQTT_TLS = config.getboolean("mqtt_host", "tls")
MQTT_AUTH = config.getboolean("mqtt_host", "auth")
MQTT_USERNAME = config.get("mqtt_host", "username")
MQTT_PASSWORD = config.get("mqtt_host","password")

# MQTT Topics
COMMAND_TOPIC_BASE = config.get("mqtt_data","command_topic")
RESPONSE_TOPIC_BASE = config.get("mqtt_data","response_topic")
WILLANDTESTIMENT_TOPIC_BASE = config.get("mqtt_data","will_and_testiment_topic")
HEARTBEAT_FREQ_MIN = int(config.get("mqtt_data","heartbeat_frequency"))

# Camera configs
CAMERA_ENABLED = config.getboolean("pi_camera","enabled")
CAMERA_TOPIC_BASE = config.get("pi_camera","response_topic")
CAMERA_IMAGE_PATH = config.get("pi_camera","temp_folder")
CAMERA_IMAGE_RETENTION_MIN = int(config.get("pi_camera","image_cache_retention"))

mqttQos = 0 
mqttRetained = False 

def get_size(bytes, suffix="B"):
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor

af_map = {
    socket.AF_INET: 'IPv4',
    socket.AF_INET6: 'IPv6',
    psutil.AF_LINK: 'MAC',
}

def process_trigger(payload): 
    logging.info('ON triggered') 
    if payload=='ping':
        logging.info("COMMAND: ping")
        response = {}
        response["ping"] = "pong"
        client.publish(RESPONSE_TOPIC_BASE + "/ping", json.dumps(response), mqttQos, mqttRetained)
    elif payload=='get-photo':
        logging.info("COMMAND: get-photo")

        if CAMERA_ENABLED and camera:
            file_name = 'image_' + str(datetime.now().strftime("%Y-%m-%d_%H:%M:%S.%f")) + '.jpg'
            full_file_name = CAMERA_IMAGE_PATH + "/" + file_name
            #camera = picamera.PiCamera()
            camera.hflip = False
            camera.vflip = False
            # disabling because of: picamera.exc.PiCameraRuntimeError: GPIO library not found, or not accessible; please install RPi.GPIO and run the script as root
            camera.led = False
            # Valid values are 0, 90, 180, and 270
            camera.rotation = 0
            camera.capture(full_file_name)
            with open(full_file_name, "rb") as imageFile:
                myFile = imageFile.read()
                data = bytearray(myFile)
            file_stat = os.stat(full_file_name)

            client.publish(CAMERA_TOPIC_BASE + "/" + file_name, data, mqttQos, mqttRetained)

            response = {}
            response["get-photo"] = {}
            response["get-photo"]["file_name"] = file_name
            response["get-photo"]["full_file_name"] = full_file_name
            response["get-photo"]["file_size"] = file_stat.st_size
            response["get-photo"]["file_size_readable"] = f"{get_size(file_stat.st_size)}"
            client.publish(RESPONSE_TOPIC_BASE + "/get-photo", json.dumps(response), mqttQos, mqttRetained)
            logging.info(full_file_name + ' image published')
        else:
            response = {}
            response["get-photo"] = "disabled"
            client.publish(RESPONSE_TOPIC_BASE + "/get-photo", json.dumps(response), mqttQos, mqttRetained)
            logging.info('get-photo disabled')
    elif payload=='status':
        logging.info("COMMAND: status")
        response = {}
        response["system"] = uname.system
        response["node_name"] = uname.node
        response["release"] = uname.release
        response["version"] = uname.version
        response["machine"] = uname.machine
        response["processor"] = uname.processor

        boot_time_timestamp = psutil.boot_time()
        bt = datetime.fromtimestamp(boot_time_timestamp)
        response["boot_time"] = f"{bt.year}/{bt.month}/{bt.day} {bt.hour}:{bt.minute}:{bt.second}"

        response["cpu"] = {}
        response["cpu"]["physical_cores"] = psutil.cpu_count(logical=False)
        response["cpu"]["total_cores"] = psutil.cpu_count(logical=True)
        response["cpu"]["temperatures"] = {}
        if hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures(fahrenheit=True)
            if temps:
                for name, entries in temps.items():
                    response["cpu"]["temperatures"][name] = {}
                    for entry in entries:
                        response["cpu"]["temperatures"][name][entry.label or name] = {}
                        response["cpu"]["temperatures"][name][entry.label or name]["current"] = f"{entry.current}°F"
                        response["cpu"]["temperatures"][name][entry.label or name]["high"] = f"{entry.high}°F"
                        response["cpu"]["temperatures"][name][entry.label or name]["critical"] = f"{entry.critical}°F"
        cpufreq = psutil.cpu_freq()
        response["cpu"]["max_frequency"] = f"{cpufreq.max:.2f}Mhz"
        response["cpu"]["min_frequency"] = f"{cpufreq.min:.2f}Mhz"
        response["cpu"]["current_frequency"] = f"{cpufreq.current:.2f}Mhz"
        for i, percentage in enumerate(psutil.cpu_percent(percpu=True, interval=1)):
            # TO-DO: Make this an array or nested deeper perhaps?
            response["cpu"][f"core_{i}"] = f"{percentage}%"
        response["cpu"]["total_cpu_usage"] = f"{psutil.cpu_percent()}%"
        
        load = psutil.getloadavg()
        response["load"] = {}
        response["load"]["1min"] = load[0]
        response["load"]["5min"] = load[1]
        response["load"]["15min"] = load[2]

        svmem = psutil.virtual_memory()
        response["memory"] = {}
        response["memory"]["total"] = f"{get_size(svmem.total)}"
        response["memory"]["available"] = f"{get_size(svmem.available)}"
        response["memory"]["used"] = f"{get_size(svmem.used)}"
        response["memory"]["percentage"] = f"{svmem.percent}%"
        swap = psutil.swap_memory()
        response["memory"]["swap_total"] = f"{get_size(swap.total)}"
        response["memory"]["swap_free"] = f"{get_size(swap.free)}"
        response["memory"]["swap_used"] = f"{get_size(swap.used)}"
        response["memory"]["swap_percentage"] = f"{swap.percent}%"
        
        response["disk"] = {}
        partitions = psutil.disk_partitions()
        for partition in partitions:
            response["disk"][partition.device] = {}
            response["disk"][partition.device]["mountpoint"] = partition.mountpoint
            response["disk"][partition.device]["fstype"] = partition.fstype
            try:
                partition_usage = psutil.disk_usage(partition.mountpoint)
                response["disk"][partition.device]["total_size"] = get_size(partition_usage.total)
                response["disk"][partition.device]["used"] = get_size(partition_usage.used)
                response["disk"][partition.device]["free"] = get_size(partition_usage.free)
                response["disk"][partition.device]["percentage"] = f"{partition_usage.percent}%"
            except PermissionError:
                # this can be catched due to the disk that isn't ready
                continue
        disk_io = psutil.disk_io_counters()
        response["disk"]["total_read"] = f"{get_size(disk_io.read_bytes)}"
        response["disk"]["total_write"] = f"{get_size(disk_io.write_bytes)}"

        response["net"] = {}
        if_addrs = psutil.net_if_addrs()
        for interface_name, interface_addresses in if_addrs.items():
            response["net"][interface_name] = {}
            for address in interface_addresses:
                response["net"][interface_name][af_map.get(address.family)] = {}
                response["net"][interface_name][af_map.get(address.family)]["address"] = f"{address.address}"
                response["net"][interface_name][af_map.get(address.family)]["netmask"] = f"{address.netmask}"
                response["net"][interface_name][af_map.get(address.family)]["broadcast"] = f"{address.broadcast}"
        net_io = psutil.net_io_counters()
        response["net"]["total_bytes_sent"] = net_io.bytes_sent
        response["net"]["total_bytes_recv"] = net_io.bytes_recv
        response["net"]["total_packets_sent"] = net_io.packets_sent
        response["net"]["total_packets_recv"] = net_io.packets_recv
        response["net"]["total_errin"] = net_io.errin
        response["net"]["total_errout"] = net_io.errout
        response["net"]["total_dropin"] = net_io.dropin
        response["net"]["total_dropout"] = net_io.dropout

        # To-Do: Add picamera status
        # To-Do: Add other temperature sensors

        client.publish(RESPONSE_TOPIC_BASE + "/status", json.dumps(response), mqttQos, mqttRetained)
    elif payload=='reboot':
        logging.info("COMMAND: reboot")
        response = {}
        response["reboot"] = "To-Do: Implement reboot"
        client.publish(RESPONSE_TOPIC_BASE + "/reboot", json.dumps(response), mqttQos, mqttRetained)
    elif payload=='flush-images':
        logging.info("COMMAND: flush-images")
        
        response = {}
        response["flush-images"] = {}
        response["flush-images"]["deleted_files"] = []
        for entry in os.scandir(CAMERA_IMAGE_PATH):
            if (entry.path.endswith(".jpg") and entry.is_file()):
                response["flush-images"]["deleted_files"].append(entry.path)
        #CAMERA_IMAGE_RETENTION_MIN

        client.publish(RESPONSE_TOPIC_BASE + "/flush-images", json.dumps(response), mqttQos, mqttRetained)
    elif payload=='die':
        logging.info("COMMAND: die")
        # is there a better way to do this un-gracefully?
        foo.bar
    else:
        logging.info("COMMAND: -unknown-")
        response = {}
        client.publish(RESPONSE_TOPIC_BASE + "/unknown", json.dumps(response), mqttQos, mqttRetained)



def on_connect(client, obj, flags, rc):
    if rc==0:
        logging.info("connected OK Returned code=%s" % rc)
    else:
        logging.info("Bad connection Returned code= %s " % rc)
    #0 - success, connection accepted
    #1 - connection refused, bad protocol
    #2 - refused, client-id error
    #3 - refused, service unavailable
    #4 - refused, bad username or password
    #5 - refused, not authorized

    # To-Do: implement last will and testiment
    client.publish(WILLANDTESTIMENT_TOPIC, payload="Online", qos=0, retain=True)

    client.subscribe(COMMAND_TOPIC_BASE) 
    logging.info("Event Connect: " + str(rc))

def on_message(mqttc, obj, msg):
    payload = str(msg.payload.decode('ascii'))  # decode the binary string 
    logging.info("Event Message: " + msg.topic + " " + str(msg.qos) + " " + payload)
    process_trigger(payload) 

def on_publish(mqttc, obj, mid):
    logging.info("Event Publish: " + str(mid))

def on_subscribe(mqttc, obj, mid, granted_qos):
    logging.info("Event Subscribed: " + str(mid) + " " + str(granted_qos))

def on_log(mqttc, obj, level, string):
    logging.info("Event Log: " + string)

def on_disconnect(mqttc, obj, rc):
    logging.info("Event Disconnect: %s" % rc)


uname = platform.uname()
client_id_random = f"{uname.node}-" + str(random.randint(0, 1000000))
WILLANDTESTIMENT_TOPIC = WILLANDTESTIMENT_TOPIC_BASE + "/" + uname.node

client = mqtt.Client(client_id=client_id_random, clean_session=True, userdata=None, transport="tcp")
# if MQTT_AUTH
client.username_pw_set(username=MQTT_USERNAME, password=MQTT_PASSWORD)  # need this 

client.on_message = on_message
client.on_connect = on_connect
client.on_publish = on_publish
client.on_subscribe = on_subscribe
client.on_disconnect = on_disconnect
client.on_log = on_log

# if MQTT_TLS
client.tls_set()

# To-Do: implement last will and testiment
client.will_set(WILLANDTESTIMENT_TOPIC, payload="Offline", qos=0, retain=True)
client.connect(MQTT_HOST, port=MQTT_PORT, keepalive=60)

response = {}
response["hello"] = "pimqqt daemon starting up"
client.publish(RESPONSE_TOPIC_BASE + "/hello", json.dumps(response), mqttQos, mqttRetained)

client.loop_forever()    #  don't get past this 

client.disconnect()
client.loop_stop()
