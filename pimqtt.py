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

logging.basicConfig(level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S', format='%(asctime)-15s - [%(levelname)s] %(module)s: %(message)s', ) 

config = configparser.ConfigParser()
config.read('/etc/pimqtt.conf')
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




def process_trigger(payload): 
    logging.info('ON triggered') 
    if payload=='ping':
        logging.info("COMMAND: ping")
        client.publish(RESPONSE_TOPIC_BASE, "pong", mqttQos, mqttRetained)
    elif payload=='get-photo':
        logging.info("COMMAND: get-photo")
        if CAMERA_ENABLED:
            client.publish(RESPONSE_TOPIC_BASE, "To-Do: implement photos (ENABLED)", mqttQos, mqttRetained)
        else:
            client.publish(RESPONSE_TOPIC_BASE, "To-Do: implement photos (DISABLED)", mqttQos, mqttRetained)
    elif payload=='status':
        logging.info("COMMAND: status")
        client.publish(RESPONSE_TOPIC_BASE, "To-Do: implement status", mqttQos, mqttRetained)
    elif payload=='reboot':
        logging.info("COMMAND: reboot")
        client.publish(RESPONSE_TOPIC_BASE, "To-Do: implement reboot", mqttQos, mqttRetained)
    elif payload=='flush-images':
        logging.info("COMMAND: flush-images")
        client.publish(RESPONSE_TOPIC_BASE, "To-Do: implement flush-images", mqttQos, mqttRetained)
    else:
        logging.info("COMMAND: -unknown-")
        client.publish(RESPONSE_TOPIC_BASE, "unknown command", mqttQos, mqttRetained)



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



client_id_random = "laptop-" + str(random.randint(0, 1000000))
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
