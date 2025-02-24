Rationale for the choice of the DB

We are using a financial data obtained from the yfinance library, both PostgreSQL and MongoDB are viable options; however, PostgreSQL is a relational database management system (RDBMS) that supports structured data which the type of data that we are dealing with.

The financial data is highly structured and could require complex queries, such as joining multiple tables or performing aggregations. PostgreSQL provides robust support for SQL and has a rich set of features such as transactions, constraints, and indexes that can ensure data integrity and consistency. It is also known for its superior performance for complex queries that involve multiple tables, while MongoDB excels in read-heavy workloads and can handle large amounts of unstructured data.


Implementation and Results:

Step1:
 
Run a postgres container using the image postgres: Command is given below:
 docker run --name postgres-db -e POSTGRES_PASSWORD=docker -p 5432:5432 -d postgres

![image](https://user-images.githubusercontent.com/125618170/227075434-cbc6ea94-7b20-4f29-9d73-f8a432246524.png)
<img width="452" alt="image" src="https://user-images.githubusercontent.com/125618170/227075556-ab584a2d-2178-4873-80aa-3f0704993399.png">

 
Step2: 
 
Run the below command :
export DOCKER_DEFAULT_PLATFORM=linux/amd64
Some environments might need this command. I needed this before spinning up the python container due to some libraries used in the python code.
 
 
Step3:
Spin up a python container with all the dependencies using the Dockerfile and docker-compose.yml file present in the app folder of the project. Navigate to the below directory and run docker-compose up command in the terminal.
Directory will be something like: “……./sorrentum/sorrentum_sandbox/projects/Issue27_Team8_Implement_sandbox_for_Yahoo_Finance/app”
 
<img width="452" alt="image" src="https://user-images.githubusercontent.com/125618170/227075642-e97c4337-c74b-4bf9-81da-056a05f70759.png">
<img width="452" alt="image" src="https://user-images.githubusercontent.com/125618170/227075659-fe07f328-c80a-4850-8920-83f325699cd1.png">

We now see 2 containers running. One for executing python code and other for hosting the data.

 
Step4: Now we enter the python container using the command:
docker exec -it app-app-1 bash (accessing the terminal)
We can see all our required code is now present in this container under /code/ folder

<img width="385" alt="image" src="https://user-images.githubusercontent.com/125618170/227075801-02b57be8-ae33-420c-a296-17f747c1c4d0.png">
 
Step5:  Now we run the code to generate a sample csv file using the download_to_csv_yahoo.py file present . Command used:
python3 download_to_csv_yahoo.py --start_timestamp "2023-03-19" --end_timestamp "2023-03-20" --target_dir '/code/' --interval '1m'
 
<img width="415" alt="image" src="https://user-images.githubusercontent.com/125618170/227075854-d87f20ed-4fa9-40b3-944f-6dc3ecf59aa1.png">

As you can see the data is getting downloaded and saved in the file name called bulk.manual.download_1min.csv.yahoo.v1_0_0.csv . This file is generated and present at /code/ after downloading the data for 2023-03-19 at minute level.  The granularity is assigned by the argument called “interval” above. We will get data from start_timestamp to end_timestamp-1 date. “target_dir”  : location for the csv can be decided through this argument.

 
Step6:  We generate 6 tables (1m,5m,15m,30m, hourly, daily) in the postgres server started by the above container (‘postgres-db’). The code responsible for this task is download_db_yahoo.py . It makes use of other functions present in the other .py files in the same directory, helper directory and common directory. We pass 4 arguments while running this file. Start_timestamp, end_timestamp, interval and target_table.

1min data (for 21st march): table name :  yahoo_yfinance_spot_downloaded_1min!
<img width="452" alt="image" src="https://user-images.githubusercontent.com/125618170/227076065-ede206da-fb7e-49c5-9cd5-47bb9d276a63.png">

5min data (for 21st march):  table name :  yahoo_yfinance_spot_downloaded_5min!
<img width="452" alt="image" src="https://user-images.githubusercontent.com/125618170/227076128-81f4c28d-ba39-4959-b944-669cc9c50a17.png">

15min data (for 21st march): table name :  yahoo_yfinance_spot_downloaded_15min!
<img width="452" alt="image" src="https://user-images.githubusercontent.com/125618170/227076200-db8575b4-2e09-4d3e-9848-fbf9f603d505.png">

30min data (for 21st march): table name :  yahoo_yfinance_spot_downloaded_30min!
<img width="452" alt="image" src="https://user-images.githubusercontent.com/125618170/227076238-f67036e8-b9c1-4b4d-a9e1-4171df971789.png">

Hourly data (for 21st march): table name :  yahoo_yfinance_spot_downloaded_1hr!
<img width="452" alt="image" src="https://user-images.githubusercontent.com/125618170/227076337-f52aafef-8c6a-4cd9-a79e-ff5c696020c3.png">

Daily data (for 15th ,16th ,17th March): table name :  yahoo_yfinance_spot_downloaded_1d
<img width="452" alt="image" src="https://user-images.githubusercontent.com/125618170/227076404-80c03eda-8664-4e73-aff6-6ab38cd1db20.png">


We can connect to sql in DBeaver and check our database :

Every 1min DB
<img width="452" alt="image" src="https://user-images.githubusercontent.com/125618170/227076490-2e6df561-e8fd-483b-85ca-45d382654a48.png">

Every 5 min DB
<img width="451" alt="image" src="https://user-images.githubusercontent.com/125618170/227076579-c329da4e-8ab7-43cd-9f49-fab45953ae32.png">

Every 15min DB
<img width="452" alt="image" src="https://user-images.githubusercontent.com/125618170/227076647-1b93f7dc-c49e-48b8-b500-eb8aca827720.png">

Every 30min DB
<img width="452" alt="image" src="https://user-images.githubusercontent.com/125618170/227076706-206383f0-7de7-4981-a604-fa9360a33b25.png">

hourly DB
<img width="419" alt="image" src="https://user-images.githubusercontent.com/125618170/227076950-25499ac8-1966-4b68-b81b-e6d9d7b5203d.png">

daily DB
<img width="426" alt="image" src="https://user-images.githubusercontent.com/125618170/227077052-c9a5b3b2-565b-4d47-adb1-797b82641044.png">


Step7:
Now we update the data with latest time period using Latest_data.py file present: 
Here is an example of getting real time 1m data in the 1m table- yahoo_yfinance_spot_downloaded_1min

<img width="452" alt="image" src="https://user-images.githubusercontent.com/125618170/227077081-a64138c2-51a2-432e-a300-6d659cedb157.png">

We can see the latest data now available in the same table. Earlier this table had data till 21st midnight when we created this table above.

<img width="452" alt="image" src="https://user-images.githubusercontent.com/125618170/227077125-7247d398-1d78-4018-ac3d-88bde9006db4.png">


Now we update the data with latest time period using Latest_data.py file present: 
