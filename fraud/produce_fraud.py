#!/usr/bin/env python

from __future__ import print_function

import json
import os
import random
from random import uniform
import time
import sys

from card_generator import generate_card
from confluent_kafka import Consumer, KafkaError, Producer
from confluent_kafka.admin import AdminClient, NewTopic

KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "fraud")
KAFKA_BROKERS = os.getenv("BOOTSTRAP_SERVERS", "localhost:9092")
SASL_USERNAME = os.getenv("SASL_USERNAME", "Nologin")
SASL_PASSWORD = os.getenv("SASL_PASSWORD", "NoPass")

def make_topic(t, c):
    a = AdminClient(c)
    topics = [KAFKA_TOPIC]
    fs = a.create_topics([NewTopic(topic, num_partitions=3, replication_factor=3) for topic in topics])
    for topic, f in fs.items():
        try:
            f.result()  # The result itself is None
            print("Topic {} created".format(topic))
        except Exception as e:
            print("Failed to create topic, it may exist already {}: {}".format(topic, e))

def get_lat():
    """ return random lat """
    return round(uniform(-180,180), 7)

def get_lon():
    """ return random lon """
    return round(uniform(-90, 90), 7)

def purchase():
    """Return a random amount in cents """
    return random.randrange(1000, 90000)

def get_user():
    """ return a random user """
    return random.randrange(0, 999)

def make_fraud():
    """ return a fraudulent transaction """
    lat = get_lat()
    lon = get_lon()
    user = get_user()
    amount = 94204
    card = generate_card("visa16")
    payload = {"userid": user,
               "amount": amount,
	           "location": {"lat": lat, "lon": lon},
               "card": card
              }
    return payload

def delivery_report(err, msg):
    """ Called once for each message produced to indicate delivery result.
        Triggered by poll() or flush(). """
    if err is not None:
        print('Message delivery failed: {}'.format(err))
    else:
        print('Message delivered to {} [{}]'.format(msg.topic(), msg.partition()))

def main():

    conf = {
      'bootstrap.servers': KAFKA_BROKERS,
      'api.version.request': True,
      'broker.version.fallback': '0.10.0.0',
      'api.version.fallback.ms': 0,
      'sasl.mechanisms': 'PLAIN',
      'security.protocol': 'SASL_SSL',
      'sasl.username': SASL_USERNAME,
      'sasl.password': SASL_PASSWORD,
      'group.id': 'fraud_group',
      'default.topic.config': {'auto.offset.reset': 'smallest'}
    }
    producer = Producer(**conf)
    print("connected to {} topic {}".format(KAFKA_BROKERS, KAFKA_TOPIC))
    make_topic(KAFKA_TOPIC, conf)

    payload = {}
    fraud_trigger = 5
    i = 1

    while True:
        producer.poll(0)

        if i % fraud_trigger == 0:
            print("making fraud")
            payload = make_fraud()
            for r in range(3):
                try:
                    producer.produce(KAFKA_TOPIC, json.dumps(payload).rstrip().encode('utf8'), callback=delivery_report)
                except Exception as ex:
                    print("unable to produce {}".format(ex))
        else:
            payload = {
                "userid": get_user(),
                "amount": purchase(),
    		    "location":{"lat": get_lat(), "lon": get_lon()},
                "card": generate_card("visa16")
            }

        try:
            producer.produce(KAFKA_TOPIC, json.dumps(payload).rstrip().encode('utf8'), callback=delivery_report)
        except Exception as ex:
            print("unable to produce {}".format(ex))
        print(payload)
        producer.flush()
        i += 1
        time.sleep(1)

if __name__== "__main__":
  main()
