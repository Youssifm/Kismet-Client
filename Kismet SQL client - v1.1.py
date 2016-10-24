# ----------------------------------------------------------------- #
#                                                                   #
#   University of North Texas                                       #
#   Department of Electrical Engineering                            #
#                                                                   #
#   Professor:  Dr. Xinrong Li                                      #
#   Name:       Youssif Mahjoub, Casey Nalley                       #
#                                                                   #
#   Date:       03/05/2016                                          #
#                                                                   #
#   Title:      Kismet Client With SQL Integration                  #
#   Version:    1.1                                                 #
#                                                                   #
#   Description:                                                    #
#       This script connects to a kismet server, and to a SQL       #
#       database. The script then requests data from the server,    #
#       parses the data, and uploads the data the SQL database.     #
#                                                                   #
#   Issues:                                                         #
#                                                                   #
#                                                                   #
#   Change Log:                                                     #
#       1. The code to handel the SQL DB has been organized         #
#           and put into its own class.                             #
#       2. More comments have been added                            #
#                                                                   #
# ----------------------------------------------------------------- #

import MySQLdb
import socket
import sys
import time

class Kismet:

    s = socket

    # Initialization function
    def __init__(self, host, port):
        self.host = host
        self.port = port
        return

    # Creates a socket and connect the socket to the
    # host a port specified in the initialization.
    # if the connection fails print out the error message.
    def k_connect(self):

        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.connect((self.host, self.port))
            status = "---- Socket Connected ----\nHost: {}\nPort: {}\n".format(self.host, self.port)
        except:
            status = sys.exc_info()[1]                  # Gets the system error thrown

        print status
        return status

    # Send data to the server. If something goes wrong
    # print out the error message.
    def k_sendCMD(self, str_cmd):

        try:
            self.s.sendall(str_cmd)
            status = "CMD SENT SUCCESSFULLY: {}".format(str_cmd.strip(' \n\r\t'))
        except:
            status = sys.exc_info()[1]                  # Gets the system error thrown

        print status
        return status

    # Read data 1 character at a time from the socket stream.
    # The loop will read the stream untill the message string
    # ends with the specified delimiter.
    def k_recvData(self, str_delimiter):

        temp = ''
        while not temp.endswith(str_delimiter):
            recv_char = k.s.recv(1)
            temp = temp + recv_char

        return temp


class SQL_Database():

    db = MySQLdb
    cursor = MySQLdb

    # Initialization function
    def __init__(self, db_host, db_port, db_user, db_passwd, db_database):
       self.db_host = db_host
       self.db_port = db_port
       self.db_user = db_user
       self.dbpasswd = db_passwd
       self.db_database = db_database
       return

    # Connects to the SQL DB specified in the initialization.
    # if the connection fails print out the error message.
    def db_connect(self):
        try:
            # Open database connection
            self.db = MySQLdb.connect(host = db_host, port = db_port, user = db_user, passwd = db_passwd, db = db_database)

            self.cursor = self.db.cursor()                       # Prepare a cursor object using cursor() method
            self.cursor.execute("SELECT VERSION()")              # Execute SQL query using execute() method.
            db_version = self.cursor.fetchone()                  # Fetch a single row using fetchone() method.

            status = '---- Connected to SQL DB ----\nHost: {}\nPort: {}\nDatabase: {}\nDatabase version : {}\n'.format(db_host, db_port, db_database, db_version)
        except:
            status = status = sys.exc_info()[1]

        print status

        return status


    # Insert a new entry into the SQL DB
    # If the insert fails and exception is thrown
    def db_insert(self, mac_address, signal_strength, client_type, curr_date, curr_time):
        try:
            # Execute the SQL command
            self.cursor.execute("""INSERT INTO kismet_data VALUES (%s, %s, %s, %s, %s)""", (mac_address, signal_strength, client_type, curr_date, curr_time))

            # Commit your changes in the database
            self.db.commit()
            status = 'NEW DB ENTRY SUBMITTED --- MAC: {} | dB: {} | Type {} | Date {} | Time {}'.format(mac_address, signal_strength, client_type, curr_date, curr_time)

        except:
            # Rollback in case there is any error
            status = "ERROR --- DB ENTRY FAILED\n\tSQL ERROR 1: {} \n\tSQL ERROR 2: {}\n\tSQL ERROR 3: {}".format(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2])
            self.db.rollback()

        print status

        return

    def db_remove(self):

        return

    # This function returns the entire database as an array.
    # Each array element contains 1 entry from the database.
    # Currently this function is only being used for debugging purposes (3-5-16)
    def db_read(self):
        try:
            # Execute the SQL command
            self.cursor.execute("""SELECT * FROM kismet_data""")
            db_data = self.cursor.fetchall()
            #print(db_data)

        except:
            db_data = "Something went wrong"

        return db_data


# ------ Open Socket For Kismet -------------------------------- #
k_host = "96.226.49.219"                        # Remote kismet server IP address
k_port = 2501

k = Kismet(k_host, k_port)                      # Remote kismet server
#k = Kismet("localhost", 2501)                  # local kisment server

k.k_connect()
# ------ End Open Socket For Kismet ---------------------------- #

# ------ Connect To SQL DB ------------------------------------- #
db_host = 'IP Address'
db_port = 3306
db_user = 'User'
db_passwd = 'Password'
db_database = 'Database name'

sql = SQL_Database(db_host, db_port, db_user, db_passwd, db_database)
sql.db_connect()
# ------ End Connect To SQL DB --------------------------------- #

# ------ Initial Connection Information ------------------------ #
k.k_sendCMD('!0 REMOVE TIME\r\n')                               # Deactivates the default once per second timestamp Kismet sends
k.k_sendCMD('!0 ENABLE CLIENT mac,signal_dbm,type\r\n')         # Tell Kismet we want to enable a socket client and receive the mac address, signal strength, connection type

k_message = k.k_recvData("*ACK: 0 OK ")

print "-------------KISMET INTRO-------------"
print k_message
print "------ END - KISMET INTRO - END ------\n"
# ------ End Initial Connection Information -------------------- #

# ------ Main Loop --------------------------------------------- #
i = 0
while (i < 5):

    #k.k_sendCMD('!0 REMOVE TIME\r\n')
    #k.k_sendCMD('!0 ENABLE CLIENT mac,signal_dbm,type\r\n')

    # Receive data from the socket.
    k_message = k.k_recvData('\n')

    if(k_message.startswith('*CLIENT')):
        k_msgSplit = k_message.split(' ')

        mac_address = k_msgSplit[1]
        signal_strength = k_msgSplit[2]
        client_type = k_msgSplit[3]
        curr_date = time.strftime("%Y-%m-%d")   # Get the current date
        curr_time = time.strftime("%H:%M:%S")   # Get the current time

        sql.db_insert(mac_address, signal_strength, client_type, curr_date, curr_time)

    i += 1
# ------ End Main Loop --------------------------------------------- #


print '\n\n---------- READ DB ------------\n'
for r in sql.db_read():
    print r


k.s.close()
sql.db.close()


