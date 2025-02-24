from kazoo.client import KazooClient
import json
import datetime

ZK_SERVER = 'zookeeper:2181'

class ConfigManager:
    def __init__(self):
        self.zk = KazooClient(hosts=ZK_SERVER)
        self.zk.start()

    def create_node(self, path, value):
        if not self.zk.exists(path):
            self.zk.create(path, json.dumps(value).encode('utf-8'), makepath=True)
        else:
            self.update_node(path, value)

    def read_node(self, path):
        if self.zk.exists(path):
            data, _ = self.zk.get(path)
            return json.loads(data.decode('utf-8'))
        else:
            return None

    def update_node(self, path, value):
        if self.zk.exists(path):
            self.zk.set(path, json.dumps(value).encode('utf-8'))
        else:
            self.create_node(path, value)

    def delete_node(self, path):
        if self.zk.exists(path):
            self.zk.delete(path, recursive=True)

    def close(self):
        self.zk.stop()

    def create_versioned_node(self, base_path, value):
        current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        versioned_path = f"{base_path}/{current_time}"
        self.create_node(versioned_path, value)
        self.update_node(base_path, value)  # Update the latest version at the base path

    def read_versioned_node(self, base_path, version=None):
        if version:
            path = f"{base_path}/{version}"
        else:
            path = base_path
        return self.read_node(path)

    def watch_node(self, path, callback):
        @self.zk.DataWatch(path)
        def watch_node(data, stat):
            if data:
                callback(json.loads(data.decode('utf-8')))
            else:
                print(f"Node {path} does not exist or has been deleted.")

def config_change_callback(data):
    print(f"Configuration changed: {data}")

if __name__ == "__main__":
    cm = ConfigManager()
    config_path = "/app/config"
    initial_config = {"database": {"host": "localhost", "port": 5432}}

    # Create initial configuration
    cm.create_versioned_node(config_path, initial_config)

    # Read and print current configuration
    config = cm.read_versioned_node(config_path)
    print("Current Configuration:", config)

    # Update configuration
    updated_config = {"database": {"host": "localhost", "port": 3306}}
    cm.create_versioned_node(config_path, updated_config)

    # Read and print updated configuration
    config = cm.read_versioned_node(config_path)
    print("Updated Configuration:", config)

    # Set the watch
    cm.watch_node(config_path, config_change_callback)

    # Simulate a change to trigger the watch
    another_update = {"database": {"host": "localhost", "port": 6380}}
    cm.create_versioned_node(config_path, another_update)

    # Keep the script running to observe changes
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    # Clean up by deleting the node
    cm.delete_node(config_path)
    cm.close()
