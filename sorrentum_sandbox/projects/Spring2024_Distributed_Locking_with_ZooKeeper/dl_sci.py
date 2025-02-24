#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import logging
import os
import time
from kazoo.client import KazooClient
from kazoo.recipe.lock import Lock

zookeeper_hosts = 'zookeeper1:2181,zookeeper2:2181,zookeeper3:2181'

class ZooKeeperLock:
    def __init__(self, hosts, lock_name, logger=None, timeout=1):
        self.hosts = hosts
        self.timeout = timeout
        self.zk_client = KazooClient(hosts=self.hosts, logger=logger, timeout=self.timeout)
        self.lock_name = lock_name
        self.lock_handle = None
        self.logger = logger or logging.getLogger(__name__)

    def create_lock(self):
        try:
            self.zk_client.start(timeout=self.timeout)
            lock_path = os.path.join("/", "locks", self.lock_name)
            self.lock_handle = Lock(self.zk_client, lock_path)
        except Exception as ex:
            self.logger.error("Failed to create lock: %s", ex)
            raise

    def acquire(self, blocking=True, timeout=None):
        if self.lock_handle is None:
            return False
        try:
            return self.lock_handle.acquire(blocking=blocking, timeout=timeout)
        except Exception as ex:
            self.logger.error("Failed to acquire lock: %s", ex)
            return False

    def release(self):
        if self.lock_handle is None:
            return False
        try:
            self.lock_handle.release()
            return True
        except Exception as ex:
            self.logger.error("Failed to release lock: %s", ex)
            return False

    def __del__(self):
        self.destroy_lock()

    def destroy_lock(self):
        if self.zk_client is not None:
            self.zk_client.stop()
            self.zk_client.close()

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    lock_name = "test"
    lock = ZooKeeperLock(zookeeper_hosts, lock_name, logger=logging.getLogger())
    lock.create_lock()
    ret = lock.acquire()
    if not ret:
        logging.info("Failed to acquire lock!")
        return

    logging.info("Lock acquired! Doing something! Sleeping for 10 seconds.")
    for i in range(1, 11):
        time.sleep(1)
        print(i)

    lock.release()
    logging.info("Lock released.")

if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        print("An exception occurred: {}".format(ex))

