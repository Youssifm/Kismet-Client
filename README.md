!!! DO NOT USE THIS VERSION !!!
  I will leave this code up for anybody that is interested, however this code is very inefficiant when trying to capture large amount of probe request. Please use my new method with uses Scapy to capture probe request.
  
  Link to Scapy-SQL-Script: 

# Kismet-Client
This script connects to a kismet server, and to a SQL database. The script then requests data from the server, parses the data, and uploads the data the SQL database. The kismet socket, data-parser, and SQL database on in 3 separate threads. This allows us to scan for MAC addresses, processes them, and then upload them to the database at the same time without missing any MAC address data.
