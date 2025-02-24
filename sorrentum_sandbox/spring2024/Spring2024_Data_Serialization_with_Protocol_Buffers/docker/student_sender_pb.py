import time
import socket
import random
import string
from student_pb2 import Student, StudentList

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 8888

def generate_random_student():
    user_id = random.randint(1000, 9999)
    username = ''.join(random.choices(string.ascii_lowercase, k=8))
    num_emails = random.randint(1, 3)
    emails = [f"{username}@example.{random.choice(['com', 'org', 'net'])}" for _ in range(num_emails)]
    graduated = random.choice([True, False])
    gender = random.choice([Student.Gender.MALE, Student.Gender.FEMALE])
    first_name = ''.join(random.choices(string.ascii_letters, k=random.randint(3, 8)))
    last_name = ''.join(random.choices(string.ascii_letters, k=random.randint(3, 10)))
    middle_name = ''.join(random.choices(string.ascii_letters, k=random.randint(3, 8))) if random.choice([True, False]) else None
    degree_type = random.choice([Student.DegreeType.BACHELOR, Student.DegreeType.MASTER, Student.DegreeType.DOCTOR])

    student = Student(
        user_id=user_id,
        username=username,
        emails=emails,
        graduated=graduated,
        gender=gender,
        name=Student.Name(first_name=first_name, last_name=last_name, middle_name=middle_name),
        degree_type=degree_type
    )

    return student

def send_students(num_students = 1000):
    
    students = StudentList(students = [generate_random_student() for _ in range(num_students)])

    start_time = time.time()
    serialized_students = students.SerializeToString()
    end_time = time.time()

    serialization_time = (end_time - start_time) * (1e6)
    total_bytes = len(serialized_students)

    print(f"Serialize {num_students} students in {serialization_time:.2f} microseconds")
    print(f"Average serialization time per student: {serialization_time / num_students:.2f} microseconds")
    print(f"Total Serialization Size: {total_bytes} bytes")
    print(f"Average bytes per student: {total_bytes / num_students:.2f} bytes")
    
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((SERVER_HOST, SERVER_PORT))
    
    client_socket.sendall(serialized_students)
    client_socket.close()

if __name__ == "__main__":
    random.seed(0)
    send_students(num_students = 10000)

