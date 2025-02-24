import socket
import json
from dataclasses import dataclass
from typing import List, Optional
import time

@dataclass
class Name:
    first_name: str
    last_name: str
    middle_name: Optional[str] = None

@dataclass
class Student:
    user_id: int
    username: str
    emails: List[str]
    graduated: bool
    gender: str
    name: Name
    degree_type: str

class StudentDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        if 'first_name' in obj and 'last_name' in obj:
            return Name(
                first_name=obj['first_name'],
                last_name=obj['last_name'],
                middle_name=obj.get('middle_name')
            )
        else:
            return Student(
                user_id=obj['user_id'],
                username=obj['username'],
                emails=obj['emails'],
                graduated=obj['graduated'],
                gender=obj['gender'],
                name=obj['name'],
                degree_type=obj['degree_type']
            )

SERVER_PORT = 8888

def receive_students():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', SERVER_PORT))
    server_socket.listen(1)

    conn, addr = server_socket.accept()
    data = b''
    while True:
        chunk = conn.recv(4096)
        if not chunk:
            break
        data += chunk

    start_time = time.time()
    students = json.loads(data.decode(), cls=StudentDecoder)
    end_time = time.time()
    deserialization_time = (end_time - start_time) * (1e6)

    conn.close()
    server_socket.close()

    num_students = len(students)
    total_bytes = len(data)
    
    print(f"Deserialize {num_students} students in {deserialization_time:.2f} microseconds")
    print(f"Average deserialization time per student: {deserialization_time  / num_students:.2f} microseconds")

    print(f"Total bytes received: {total_bytes} bytes")
    print(f"Average bytes per student: {total_bytes / num_students:.2f} bytes")

if __name__ == "__main__":
    receive_students()
