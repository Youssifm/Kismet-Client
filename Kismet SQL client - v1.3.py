# --------------------------------------------------------------------------------------------- #
#                                                                                               #
#   University of North Texas                                                                   #
#   Department of Electrical Engineering                                                        #
#                                                                                               #
#   Professor:  Dr. Xinrong Li                                                                  #
#   Name:       Youssif Mahjoub, Casey Nalley                                                   #
#                                                                                               #
#   Date:       03/17/2016                                                                      #
#                                                                                               #
#   Title:      Kismet Client With SQL Integration                                              #
#   Version:    1.3                                                                             #
#                                                                                               #
#   Description:                                                                                #
#       This script connects to a kismet server, and to a SQL database. The                     #
#       script then requests data from the server, parses the data, and                         #
#       uploads the data the SQL database. The kismet socket, data-parser,                      #
#       and SQL database on in 3 separate threads. This allows us to scan for                   #
#       MAC addresses, processes them, and then upload them to the database                     #
#       at the same time without missing any MAC address data.                                  #
#                                                                                               #
#   Notes:                                                                                      #
#       The previous versions had a major issue which did not clear the                         #
#       previous dictionary data after the specified timeout. This cause                        #
#       our data to count incorrectly. Even though a device was gone it would                   #
#       still count it. Which is the reason there were not dips in the                          #
#       graphed data.                                                                           #
#                                                                                               #
#   Issues:                                                                                     #
#       1. For some reason whe the code first executes it takes a while to                      #
#           get the first device data. after that the code runs normally.                       #
#                                                                                               #
#   Change Log:                                                                                 #
#       v1.3 (03/17/16)                                                                         #
#           1. Kismet logs everything. The devices are not removed from the                     #
#               cache so that is the reason in the previous code we were                        #
#               getting 1k+ devices. To fix this we retrieved the last seen                     #
#               time-stamp and compared it to the timeout so we only get the                    #
#               devices that has showed up in the past timeout minutes.                         #
#           2. A data-handler thread was added to eliminate duplicates when                     #
#               uploading.                                                                      #
#                                                                                               #
#       v1.2 (03/10/2016)                                                                       #
#           1. Added support for multi-processing. (aka multi-threading)                        #
#           2. Added very basic support for a queue so data can be shared                       #
#               across threads.                                                                 #
#                                                                                               #
#       v1.1 (03/05/2016)                                                                       #
#           1. The code to handel the SQL DB has been organized and put into                    #
#               its onw class.                                                                  #
#           2. More comments have been added                                                    #
#                                                                                               #
# --------------------------------------------------------------------------------------------- #

import datetime
import MySQLdb
import Queue
import socket
import sys
import threading
import time

class Kismet:

    s = socket
    k_close = False
    hostname = ''

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
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)                                      # Create the TCP socket
            self.s.connect((self.host, self.port))                                                          # Connect to the socket
            self.hostname = socket.gethostname()
            status = "---- Socket Connected ----\n\tHost: {}\n\tPort: {}\n".format(self.host, self.port)    # Status message
        except:
            status = "KISMET SOCKET ERROR: socket connection failed.\n\t"                                   # Error status message
            for index, msg in enumerate(sys.exc_info()):                                                    # For each error message in the system error exceptions
                status += "SYS ERROR {}: {}\n\t".format(index, msg)                                         # Append error to status message

        print status
        return status

    # Send data to the server. If something goes wrong
    # print out the error message.
    def k_sendCMD(self, str_cmd):
        try:
            self.s.sendall(str_cmd)                                                                         # Send all characters in the str_cmd string
            status = "KISMET SOCKET: cmd sent successfully. --- {}".format(str_cmd.strip(' \n\r\t'))        # Status message
        except:
            status = "ERROR - KISMET SOCKET: cmd failed to send.\n\t"                                       # Error status message
            for index, msg in enumerate(sys.exc_info()):                                                    # For each error message in the system error exceptions
                status += "SYS ERROR {}: {}\n\t".format(index, msg)                                         # Append error to status message

        print status
        return status

    # Read data 1 character at a time from the socket stream.
    # The loop will read the stream untill the message string
    # ends with the specified delimiter.
    def k_recvData(self, str_delimiter):
        temp = ''                                                           # Clear previous data
        while not temp.endswith(str_delimiter):                             # Check ending characters with delimiter
            recv_char = self.s.recv(1)                                      # Get 1 byte from socket
            temp = temp + recv_char                                         # Append received byte to the buffer temp

        return temp

    def run(self, data_queue):

        self.k_connect()                                                    # Connect to Kismet socket

        print "------------ KISMET INTRO ------------"
        self.k_sendCMD('!0 REMOVE TIME\r\n')                                # Deactivates the default timestamp Kismet sends
        self.k_sendCMD('!0 ENABLE CLIENT mac,signal_dbm,type,firsttime,lasttime\r\n')      # Tell Kismet we want to enable a socket client and receive the mac address, signal strength, connection type
        k_msg = self.k_recvData("*ACK: 0 OK \n")                          # Retrive the intro data kismet sends
        print k_msg                                                         # Display the intro message to the console

        while not self.k_close:                                             # Loop while we want the socket open

            k_msg = self.k_recvData('\n').strip(" \n")                      # Get 1 line of data from Kismet socket.

            if(k_msg.startswith('*CLIENT')):                                # Check if the received data is a client

                temp = k_msg.split(' ')

                k_msg = "{} {} {} {}".format(temp[0], temp[1], temp[2], temp[3])
                k_lastseen = datetime.datetime.fromtimestamp(int(temp[5]))
                curr_date = str(k_lastseen).split(' ')[0]                  # Get the current date
                curr_time = str(k_lastseen).split(' ')[1]                  # Get the current time

                ### DEBUGGING - #print "{} --- sub 1 ---> {}".format(str(datetime.datetime.fromtimestamp(int(temp[5]))), str(datetime.datetime.fromtimestamp(int(temp[5]))-datetime.timedelta(minutes=1)))
                ### DEBUGGING - #print datetime.datetime.now()

                if(k_lastseen >= datetime.datetime.now()-datetime.timedelta(minutes=2) ):
                    data_queue.put("{} {} {} {}".format(k_msg, curr_date, curr_time, self.hostname))      # Put the client, along with time/date info, in the queue

            threading._sleep(0.1)                                           # Slow down the execution of the thread so its not going crazy

        self.s.close()                                                      # Once loop is over close the kismet socket
        print "KISMET SOCKET: socket closed."
        return

class Data_Handler():

    dh_quit = False

    # Initialization function
    def __init__(self):
        return

    def run(self, kismet_queue, sql_queue):

        d = dict()                                                      # Create dictionary (a.k.a Open hash-table (separate chaining))

        while not self.dh_quit:                                         # Loop while we want to process data

            timeout = time.time() + 60*2                                # 60*x min timeout
            d.clear()                                                   # Clear the dictionary for the next sql_queue put
            mac_array = []                                              # Clear the mac_array for the next sql_queue put

            while True:                                                 # nested while loop that runs for the timeout mins specified above.

                q_data = kismet_queue.get()                             # Get data from the queue. The data is 1 client. (mac, signal_dbm, conn_type, date, time, host_name)
                mac_key = q_data.split(' ')[1]                          # Split the mac address so we can use the mac address as a index address for the dictionary

                if mac_key not in d:                                    # if MAC Address is not in table. Add it
                    d[mac_key] = q_data                                 # Set the mac index address value equal to the queue data which contains the rest of the information on that client

                if(time.time() >= timeout):                             # if it has been X mins put the the mac_array on the SQL queue
                    for item in d:                                      # Lopp through each item in the dictionary. each item is 1 clients data.
                        split = d[item].split(' ')                      # Split the data for each client so we can append the data to the mac_array as a tuple.

                        if(split[3] == '2'):                            # if the conn_type = '2' then its a probe request. append to mac_array for the sql_queue.
                            mac_array.append((split[1], split[2], split[3], split[4], split[5], split[6]))      # append it.
                    break                                               # Break out of the nested while loop. This will allow the main while loop to put the data to the sql_queue
                else:
                    threading._sleep(0.02)                              # Slow down the execution of the thread so its not going crazy
                    ### Debigging - print q_data

            sql_queue.put(mac_array)                                    # Add the mac_array to the sql_queue


        print "DATA HANDLER: STOPPED"
        return

class SQL_Database():

    db = MySQLdb
    cursor = MySQLdb
    db_close = False

    db_table = ''

    # Initialization function
    def __init__(self, db_host, db_port, db_user, db_passwd, db_database):
        self.db_host = db_host
        self.db_port = db_port
        self.db_user = db_user
        self.db_passwd = db_passwd
        self.db_database = db_database
        return

    # Connects to the SQL DB specified in the initialization.
    # if the connection fails print out the error message.
    def db_connect(self):
        try:
            # Open database connection
            self.db = MySQLdb.connect(host = self.db_host, port = self.db_port, user = self.db_user, passwd = self.db_passwd, db = self.db_database)

            self.cursor = self.db.cursor()                       # Prepare a cursor object using cursor() method
            self.cursor.execute("SELECT VERSION()")              # Execute SQL query using execute() method.
            db_version = self.cursor.fetchone()[0]               # Fetch a single row using fetchone() method as a tuple.


            status = '---- Connected to SQL DB ----\n\tHost: {}\n\tPort: {}\n\tDatabase: {}\n\tDatabase version : {}\n\t'.format(self.db_host, self.db_port, self.db_database, db_version)
        except:
            status = "ERROR - SQL DB: connection to SQLDB failed.\n\t"
            for index, msg in enumerate(sys.exc_info()):
                status += "SYS ERROR {}: {}\n\t".format(index, msg)

        print status

    # Insert a new entry into the SQL DB
    # If the insert fails and exception is thrown
    def db_insert(self, data_array):
        try:
            status = ''

            stmt = """INSERT INTO {} (mac, signal_dbm, conn_type, date, time, host_name) VALUES (%s, %s, %s, %s, %s, %s)""".format(self.db_table)
            self.cursor.executemany(stmt, data_array)
            self.db.commit()                    # Commit your changes in the database

            status += "MAC Count: {} - Date: {} - Time {}".format(str(len(data_array)).zfill(5), time.strftime("%Y-%m-%d"), time.strftime("%H:%M"))
        except:
            # Rollback in case there is any error
            status = "ERROR - SQL DB: insert failed.\n\t"
            for index, msg in enumerate(sys.exc_info()):
                status += "SYS ERROR {}: {}\n\t".format(index, msg)
            self.db.rollback()

        print status

    def db_clear(self):
        try:
            stmt = """TRUNCATE TABLE {}""".format(self.db_table)
            self.cursor.execute(stmt)
            status = "SQL DB: {} table cleared.".format(self.db_table)
        except:
            # Rollback in case there is any error
            status = "ERROR - SQL DB: table clear failed.\n\t"
            for index, msg in enumerate(sys.exc_info()):
                status += "SYS ERROR {}: {}\n\t".format(index, msg)
            self.db.rollback()
        print status

    # This function returns the entire database as an array.
    # Each array element contains 1 entry from the database.
    # Currently this function is only being used for debugging purposes (3-5-16)
    def db_read(self):
        try:
            # Execute the SQL command
            self.cursor.execute("""SELECT * FROM {}""".format(self.db_table))
            db_data = self.cursor.fetchall()
        except:
            db_data = "Something went wrong"

        return db_data

    def run(self, data_queue):

        self.db_connect()
        threading._sleep(1)

        while not self.db_close:
            if not data_queue.empty():
                mac_data = data_queue.get()
                self.db_insert(mac_data)

        self.db.close()
        print 'SQL DB: CLOSED'


#if __name__ == '__main__': # If statement is only requires in windows. MAYBE!!! do more research

kismet_queue    = Queue.Queue()
sql_queue       = Queue.Queue()

workerThreads   = []

k_host          = "youssif-home.ddns.net"
k_port          = 2501
db_host         = 'youssifprojects.com'
db_port         = 3306
db_user         = 'youssifp_kismetU'
db_passwd       = 'EENG4910'
db_database     = 'youssifp_kismet'


kismet          = Kismet(k_host, k_port)
data_handler    = Data_Handler()
sql             = SQL_Database(db_host, db_port, db_user, db_passwd, db_database)

sql.db_table    = db_table = 'kismet_data2'

t_kismet        = threading.Thread(name="kismet", target=kismet.run, args=(kismet_queue,))
t_data_handler  = threading.Thread(name="data_handler", target=data_handler.run, args=(kismet_queue, sql_queue,))
t_sql           = threading.Thread(name="SQL_DB", target=sql.run, args=(sql_queue,))

workerThreads.append(t_kismet)
workerThreads.append(t_data_handler)
workerThreads.append(t_sql)

for t in workerThreads:
    t.start()
    print "THREAD: {} thread started.".format(t.name)
print "\n"

'''
    while True:
        print "Actions Menu\n\tQ. Quit\n\t1. Print SQLDB\n\t2. Clear SQLDB\n"
        user_input = raw_input("Enter action number: ")

        if user_input == 'q' or user_input == 'Q':
            kismet.k_close = True
            data_handler.dh_quit = True
            sql.db_close = True
            break
        elif user_input == '1':
            print sql.db_read()
        elif user_input == '2':
            sql.db_clear()
'''