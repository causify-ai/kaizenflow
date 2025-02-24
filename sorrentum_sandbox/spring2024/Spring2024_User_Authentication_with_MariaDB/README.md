This project is to create a user authentication with Mariadb. Mariadb is a relational database management system that was developed by original developer of MYSQL. Therefore it shares 
some similarity with MYSQL, for examples Mariadb also use SQL queries, allowing MYSQL application and tools can be used in Mariadb too. While presevre some features of MYSQL, Mariadb also
makes improvement on the its speed. It has a fast read and write operation. They also have optimized the performance for some operation such as queries. Mariadb is also knowned as including
multiple storage engines such as CSV, MEMORY, ARIA, TOKUDB etc. Mariadb has its code open sourced, allowing the developers and user to check their code in GPL, LGPL or BSD. As a relational
database management system, Mariadb is a sutitable database for user authenticationw which provide structured data for user information and have username as the primary key. It also provides
security to protect the users' information.

The project use docker to provide containers for the application. Docker provides a virtual operating system which allows the authentication system and the database can be stored in an isolated
environment. For this application, the docker has two services, the Mariadb and the python script that run the application. The Database use the mariadb as images and create a volume that
act as a database to store all the information of the users. The python script container provide an interactive shell connect to the local terminal and accept the command to access the database.
To allow the python script access the database, docker create a network between the two containers, making the two containers into a whole application

The Database has the username as the primary key which prevent duplicate username and has password as another column. The python app connect to the local terminal as the front end and provide
options including login, register and exit at the start of the application. The operation will fail if you input a wrong password or username, or register with a password that are too short,
and you will need to try again. Once you login or register successfully, you can only choose to logout or exit the application. If you choose to logout, you can choose to login or register
again. The application start with the command docker compose run pythonapp.


Video link: https://drive.google.com/file/d/1xWAWPGlB3BC0AD5TEjJkmJX-_JBRzMZ_/view?usp=drive_link
