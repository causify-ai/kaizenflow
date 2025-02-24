import socket
import xml.etree.ElementTree as ET
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

def xml_to_student(xml_str: str) -> Student:
    root = ET.fromstring(xml_str)
    user_id = int(root.find('user_id').text)
    username = root.find('username').text
    emails = [email.text for email in root.find('emails').findall('email')]
    graduated = bool(root.find('graduated').text)
    gender = root.find('gender').text
    name_elem = root.find('name')
    first_name = name_elem.find('first_name').text
    last_name = name_elem.find('last_name').text
    middle_name = name_elem.find('middle_name').text if name_elem.find('middle_name') is not None else None
    degree_type = root.find('degree_type').text

    return Student(
        user_id=user_id,
        username=username,
        emails=emails,
        graduated=graduated,
        gender=gender,
        name=Name(first_name=first_name, last_name=last_name, middle_name=middle_name),
        degree_type=degree_type
    )

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 8888

def receive_students():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen(1)

    conn, addr = server_socket.accept()
    data = b''
    while True:
        chunk = conn.recv(4096)
        if not chunk:
            break
        data += chunk

    start_time = time.time()
    students = [xml_to_student(xml_str) for xml_str in data.decode().split('\n')]
    end_time = time.time()
    deserialization_time = (end_time - start_time) * (1e6)

    conn.close()
    server_socket.close()

    num_students = len(students)
    total_bytes = len(data)

    print(f"Deserialize {num_students} students in {deserialization_time:.2f} microseconds")
    print(f"Average deserialization time per student: {deserialization_time / num_students:.2f} microseconds")

    print(f"Total bytes received: {total_bytes} bytes")
    print(f"Average bytes per student: {total_bytes / num_students:.2f} bytes")

if __name__ == "__main__":
    receive_students()
