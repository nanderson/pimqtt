#!/usr/bin/env python2

# combine the MQTT and RF receive codes 
import paho.mqtt.client as mqtt 
import paho.mqtt.publish as publish 
import picamera 
import sys 
import random
import time 
import logging 
from datetime import datetime
import configparser

logging.basicConfig(level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S', format='%(asctime)-15s - [%(levelname)s] %(module)s: %(message)s', ) 

config = configparser.ConfigParser()
config.read('pimqtt.conf')
MQTT_HOST = config.get("mqtt_host", "host")
MQTT_PORT = config.get("mqtt_host", "port")
MQTT_USERNAME = config.get("mqtt_host", "username")
MQTT_PASSWORD = config.get("mqtt_host","password")


# MQTT Topics
DATA_TOPIC_BASE = "SENSOR/picamera/data/"
STATUS_TOPIC_BASE = "SENSOR/picamera/status/"
COMMAND_TOPIC = "COMMAND/picamera/take_photo"

# tmp directory for the camera images
CAMERA_FILES = "/tmp/picmqtt/"

mqttQos = 0 
mqttRetained = False 

def process_trigger(payload): 
    logging.info('ON triggered') 


def on_connect(mqttc, obj, flags, rc):
    client.subscribe(COMMAND_TOPIC) 
    logging.info("Event Connect: " + str(rc))

def on_message(mqttc, obj, msg):
    payload = str(msg.payload.decode('ascii'))  # decode the binary string 
    logging.info(msg.topic + " " + payload) 
    process_trigger(payload) 
    logging.info("Event Message: " + msg.topic + " " + str(msg.qos) + " " + str(msg.payload.decode('utf-8')))

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




client_id_random = "picamera-" + str(random.randint(0, 1000000))
client = mqtt.Client(client_id=client_id_random)
#client.username_pw_set(username='user',password='pass')  # need this 

client.on_message = on_message
client.on_connect = on_connect
client.on_publish = on_publish
client.on_subscribe = on_subscribe
client.on_disconnect = on_disconnect
client.on_log = on_log


client.connect(broker) 
client.loop_forever()    #  don't get past this 

# For testing only, tke a photo and exit
#client.loop_start()    #  run in background and free up main thread 
#post_image() 

client.disconnect()
client.loop_stop()
