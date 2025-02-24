import mysql.connector

def connect_db():
    #connect to the mariadb database
    return mysql.connector.connect(
        host = "mydb",
        port = 3306,
        user = "bot",
        password = "maria",
        database = "db",
    )
def login(username,password):
  #login to the account if correct username and password
  lg = False

  try:
    conn = connect_db()
    cursor = conn.cursor()
    sql = "SELECT * FROM users WHERE username = %s AND password = %s"
    cursor.execute(sql,(username,password))
    user = cursor.fetchall()
    if user:
      print("login successful")
      print(f"Hi {username}\n")
      lg = True
    else:
      print("invalid username or password")
      lg = False

  except mysql.connector.Error as e:
    print(f"Error: {e}")

  if conn.is_connected():
    cursor.close()
    conn.close()
  return lg 

def register(username,password):
  #register a new account to the database

  lg = False
  if len(password)<4:
     print("password too short")
     return lg
  try:
    conn = connect_db()
    cursor = conn.cursor()
    sql = "INSERT INTO users (username, password) VALUES (%s, %s)"
    cursor.execute(sql,(username,password))
    
    print("register success")
    print(f"welcome {username}\n")
    lg = True


  except mysql.connector.Error as e:
    if e.errno==1062:
       print("username already exist, try again\n")
    else:
        print(f"Error: {e}")

  if conn.is_connected():
    conn.commit()
    cursor.close()
    conn.close()

  return lg

def create_tab():
    #create the account table for the first time in case it is not exist
    try:
        conn = connect_db()
        cursor = conn.cursor()
        sql = """
        CREATE TABLE IF NOT EXISTS users (
        username VARCHAR(255) PRIMARY KEY,
        password VARCHAR(255) NOT NULL
        )
        """
        cursor.execute(sql)
        cursor.close()
        conn.close()
    except mysql.connector.Error as e:
       print(f"Error: {e}")


def main():
    no_exit = True
    while no_exit:

        option = input("login press 1\nregister press 2\nexit press 3\n")

        if option == '3': #exit option
            break
        create_tab()
        username  = input("username: ")
        password = input("password(4 characters or above): ")

        if option == '1': #login option
            
            lg = login(username,password)
        elif option == '2': #register option
            lg = register(username,password)
        else: #press other key
           print("invalid option, try again\n")
           continue

        while lg: #choose to logout or exit the app while login
           option = input("logout press 1\nexit press 2\n")
           if option == '2':
              no_exit = False
              break
           elif option == '1':
              break
           else:
              print("invalid option, try again")

if __name__ == "__main__":
   main()