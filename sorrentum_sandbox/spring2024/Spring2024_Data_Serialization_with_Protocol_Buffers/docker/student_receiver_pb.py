
import time
import socket
import random
import string
from student_pb2 import Student, StudentList

SERVER_PORT = 8888

def receive_students():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', SERVER_PORT))
    server_socket.listen(1)

    client_socket, client_address = server_socket.accept()

    all_data = b''
    total_bytes = 0
    while True:
        data = client_socket.recv(4096)
        if not data:
            break
        total_bytes += len(data)
        all_data += data

    client_socket.close()
    server_socket.close()

    start_time = time.time()
    studentList = StudentList()
    studentList.ParseFromString(all_data)

    end_time = time.time()
    deserialization_time = (end_time - start_time) * (1e6)

    num_students = len(studentList.students)
    
    print(f"Deserialize {num_students} students in {deserialization_time:.2f} microseconds")
    print(f"Average deserialization time per student: {deserialization_time  / num_students:.2f} microseconds")

    print(f"Total bytes received: {total_bytes} bytes")
    print(f"Average bytes per student: {total_bytes / num_students:.2f} bytes")

if __name__ == "__main__":
    receive_students()
