namespace py SimpleService

struct Person {
    1: i32 id,
    2: string name,
    3: i32 age,
    4: string email
}

struct Student {
    1: i32 id,
    2: string name,
    3: string department
}

exception PersonNotFound {
    1: string message
}

service SimpleService {
    string sayHello(1: string name),
    i32 addNumbers(1: i32 num1, 2: i32 num2),
    Person getPersonInfo(1: i32 personId),
    list<Student> listStudents(1: string department),
    map<string, i32> countVotes(1: map<string, i32> votes),
    Person findPersonByEmail(1: string email) throws (1: PersonNotFound e),
    oneway void logMessage(1: string message)
}
