#!/usr/bin/env python3

# combine the MQTT and RF receive codes 
import paho.mqtt.client as mqtt 
import paho.mqtt.publish as publish 
#import picamera 
import sys 
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
HEARTBEAT_FREQ_MIN = int(config.get("mqtt_data","heartbeat_frequency"))

# Camera configs
CAMERA_ENABLED = config.getboolean("pi_camera","enabled")
CAMERA_TOPIC_BASE = config.get("pi_camera","response_topic")
CAMERA_IMAGE_PATH = config.get("pi_camera","temp_folder")
CAMERA_IMAGE_RETENTION_MIN = int(config.get("pi_camera","image_cache_retention"))

mqttQos = 0 
mqttRetained = False 

uname = platform.uname()

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
        client.publish(RESPONSE_TOPIC_BASE, json.dumps(response), mqttQos, mqttRetained)
    elif payload=='get-photo':
        logging.info("COMMAND: get-photo")
        response = {}
        response["camera"] = "To-Do: Implement camera"
        if CAMERA_ENABLED:
            response["enabled"] = True
        else:
            response["enabled"] = False
        client.publish(RESPONSE_TOPIC_BASE, json.dumps(response), mqttQos, mqttRetained)
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
            for address in interface_addresses:
                response["net"][interface_name] = {}
                response["net"][interface_name]["family"] = af_map.get(address.family)
                response["net"][interface_name]["address"] = f"{address.address}"
                response["net"][interface_name]["netmask"] = f"{address.netmask}"
                response["net"][interface_name]["broadcast"] = f"{address.broadcast}"
        net_io = psutil.net_io_counters()
        response["net"]["total_bytes_sent"] = f"{get_size(net_io.bytes_sent)}"
        response["net"]["total_bytes_received"] = f"{get_size(net_io.bytes_recv)}"

        client.publish(RESPONSE_TOPIC_BASE, json.dumps(response), mqttQos, mqttRetained)
    elif payload=='reboot':
        logging.info("COMMAND: reboot")
        response = {}
        response["reboot"] = "To-Do: Implement reboot"
        client.publish(RESPONSE_TOPIC_BASE, json.dumps(response), mqttQos, mqttRetained)
    elif payload=='flush-images':
        logging.info("COMMAND: flush-images")
        response = {}
        response["flush-images"] = "To-Do: Implement flush-images"
        client.publish(RESPONSE_TOPIC_BASE, json.dumps(response), mqttQos, mqttRetained)
    else:
        logging.info("COMMAND: -unknown-")
        response = {}
        client.publish(RESPONSE_TOPIC_BASE, json.dumps(response), mqttQos, mqttRetained)



def on_connect(mqttc, obj, flags, rc):
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
    mqttc.subscribe(COMMAND_TOPIC_BASE) 
    logging.info("Event Connect: " + str(rc))

def on_message(mqttc, obj, msg):
    payload = str(msg.payload.decode('ascii'))  # decode the binary string 
    logging.info("Event Message: " + msg.topic + " " + str(msg.qos) + " " + payload)
    process_trigger(payload) 

def on_publish(mqttc, obj, mid):
    logging.info("Event Publish: " + str(mid))
    #time.sleep(10)
    #client.disconnect()
    #client.stop_loop()

def on_subscribe(mqttc, obj, mid, granted_qos):
    logging.info("Event Subscribed: " + str(mid) + " " + str(granted_qos))

def on_log(mqttc, obj, level, string):
    logging.info("Event Log: " + string)

def on_disconnect(mqttc, obj, rc):
    logging.info("Event Disconnect: %s" % rc)


uname = platform.uname()
client_id_random = f"{uname.node}-" + str(random.randint(0, 1000000))
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
client.connect(MQTT_HOST, port=MQTT_PORT, keepalive=60)
client.loop_forever()    #  don't get past this 


# For testing only, tke a photo and exit
#client.loop_start()    #  run in background and free up main thread 
#post_image() 

client.disconnect()
client.loop_stop()
