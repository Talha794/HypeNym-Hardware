#!/usr/bin/env python
''' Async TCP server to make first tests of newly received GPS trackers '''

import asyncore
import socket
import binascii
import datetime
#from iso6709 import Location
import json
import requests
import time
import asyncio
import httpx
import math
from constants import *

requestsToSend = []


class Server(asyncore.dispatcher):
    def __init__(self, address):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(address)
        self.address = self.socket.getsockname()
        print('TCP Server Initialized, Details: ', self.address)
        print('Provissioner Address:', PROVISIONER_SERVER, "Port: ", PROVISIONER_PORT)
        self.listen(5)

    def handle_accept(self):
        # Called when a client connects to our socket
        client_info = self.accept()
        if client_info is not None:
            ClientHandler(client_info[0], client_info[1])

class ClientHandler(asyncore.dispatcher):
    def __init__(self, sock, address):
        asyncore.dispatcher.__init__(self, sock)
        self.logger = logging.getLogger('Client ' + str(address))
        self.data_to_write = []
        print('Client Remote Address: ', str(address))
        self.address = address
        self.id = None
        self.parsedData = {}
        self.previousSpeed = 0
        self.previousDrivingAnalysisTime = 0

    def writable(self):
        return bool(self.data_to_write)

    def handle_write(self):
        data = self.data_to_write.pop()
        sent = self.send(data[:1024])
        if sent < len(data):
            remaining = data[sent:]
            self.data.to_write.append(remaining)
        # print('Responded to Client: ', sent, data[:sent].rstrip())

    def handle_read(self):
        rawTCPData = self.recv(1024*3)
        print('Raw Received Data: () ""', len(rawTCPData), rawTCPData.rstrip())
        self.data_parsing(rawTCPData)
        self.calling_provisioner_to_send_data()
        self.parsedData = {}
       # rawHexData = binascii.hexlify(rawTCPData).decode()
       # print("Raw Hex Data: ", rawHexData , ", Len: ", len(rawHexData))
       

    def handle_close(self):
        print('Closing the TCP Socket, handling close!')
        self.close()

    async def sendAsyncReq(self, request):
        async with httpx.AsyncClient() as client:
            client = httpx.AsyncClient()
            print("Packet to Send: ", request)
            response = await client.get(request)
            if response.status_code == 204:
                print("Packet Sent successfully for: ", self.id)
            else:
                print("Packet Sending Failure for: , Response: ", self.id, response.status_code)
            await client.aclose()

    def calling_provisioner_to_send_data(self):
        dataToSend = json.dumps(self.parsedData)
        print(dataToSend)
        url = "http://" + PROVISIONER_SERVER + ":" + PROVISIONER_PORT + "/data/straight2IoTHub?&data=" + dataToSend
        try:
            asyncio.run(self.sendAsyncReq(url))
        except:
            print("Data Sending Exception occurred: ", self.id)
        self.parsedData = {}


    def data_parsing(self, rawTCPData):
        raw = rawTCPData.decode('utf-8')
        print('Raw Received: ', raw, "length:", len(raw))
        splittedData = raw.split(',')
        print(splittedData)
        comType = splittedData[0].split('*')
        print(comType[3])
        print(comType[1])
        if comType[3] == "WAD":
            locationRequestResponse = "[SG*8800000015*000C*RAD,GPS,EH]"
            #locationRequestResponse = "01"
            hex = bytes(locationRequestResponse,'utf-8')
            hex2 = binascii.hexlify(hex)
            self.data_to_write.insert(0, binascii.unhexlify(hex2))
            speed = splittedData[9]
            direction = splittedData[10]
            altitude = splittedData[11]
            battery = splittedData[14]
            walkStep = splittedData[16]
            lat = splittedData[5]
            latDir = splittedData[6] 
            lon = splittedData[7] 
            lonDir = splittedData[8] 
            #print(lat,",",latDir,",",lon,",",lonDir)
            self.id = comType[1]
            self.parsedData['id'] = self.id
            self.parsedData['lat'] = lat
            self.parsedData['lon'] = lon
            self.parsedData['spd'] = speed
            self.parsedData['alt'] = altitude
            self.parsedData['dir'] = direction
            self.parsedData['b'] = battery
            self.parsedData['sc'] = walkStep
        
            #self.parsedData['latDir'] = latDir
            #self.parsedData['lonDir'] = lonDir
            #print(self.parsedData)
            #json_object = json.dumps(self.parsedData, indent = 4)
            #print(json_object)
        elif comType[3] == "LK":
            if comType[2] == "0002":
                locationRequestResponse = "[SG*8800000015*0002*LK]"
                #locationRequestResponse = "01"
                hex = bytes(locationRequestResponse,'utf-8')
                hex2 = binascii.hexlify(hex)
                self.data_to_write.insert(0, binascii.unhexlify(hex2))
            elif comType[2] == "000D":
                locationRequestResponse = "[SG*8800000015*0002*LK]"
                #locationRequestResponse = "01"
                hex = bytes(locationRequestResponse,'utf-8')
                hex2 = binascii.hexlify(hex)
                self.data_to_write.insert(0, binascii.unhexlify(hex2))
                steps = splittedData[1] 
                turnOver = splittedData[2] 
                battery = splittedData[3] 
                self.id = comType[1]
                self.parsedData['id'] = self.id
                self.parsedData['steps'] = steps            
                self.parsedData['to'] = turnOver            
                self.parsedData['b'] = battery
        elif comType[3] == "UD":
            locationRequestResponse = "NO"
            #locationRequestResponse = "01"
            hex = bytes(locationRequestResponse,'utf-8')
            hex2 = binascii.hexlify(hex)
            self.data_to_write.insert(0, binascii.unhexlify(hex2))
            speed = splittedData[8]
            direction = splittedData[9]
            altitude = splittedData[10]
            battery = splittedData[13]
            walkStep = splittedData[15]
            lat = splittedData[4]
            latDir = splittedData[5] 
            lon = splittedData[6] 
            lonDir = splittedData[7] 
            #print(lat,",",latDir,",",lon,",",lonDir)
            self.id = comType[1]
            self.parsedData['id'] = self.id
            self.parsedData['lat'] = lat
        elif comType[3] == "UD2":
            locationRequestResponse = "NO"
            #locationRequestResponse = "01"
            hex = bytes(locationRequestResponse,'utf-8')
            hex2 = binascii.hexlify(hex)
            self.data_to_write.insert(0, binascii.unhexlify(hex2))
            speed = splittedData[8]
            direction = splittedData[9]
            altitude = splittedData[10]
            battery = splittedData[13]
            walkStep = splittedData[15]
            lat = splittedData[4]
            latDir = splittedData[5] 
            lon = splittedData[6] 
            lonDir = splittedData[7] 
            #print(lat,",",latDir,",",lon,",",lonDir)
            self.id = comType[1]
            self.parsedData['id'] = self.id
            self.parsedData['lat'] = lat
            self.parsedData['lon'] = lon
            self.parsedData['spd'] = speed
            self.parsedData['alt'] = altitude
            self.parsedData['dir'] = direction
            self.parsedData['b'] = battery
            self.parsedData['sc'] = walkStep 
            self.parsedData['spd'] = speed
            self.parsedData['alt'] = altitude
            self.parsedData['dir'] = direction
            self.parsedData['b'] = battery
            self.parsedData['sc'] = walkStep
        elif comType[3] == "AL":
            locationRequestResponse = "[SG*8800000015*0002*AL]"
            #locationRequestResponse = "01"
            hex = bytes(locationRequestResponse,'utf-8')
            hex2 = binascii.hexlify(hex)
            self.data_to_write.insert(0, binascii.unhexlify(hex2))
            speed = splittedData[8]
            direction = splittedData[9]
            altitude = splittedData[10]
            battery = splittedData[13]
            walkStep = splittedData[15]
            lat = splittedData[4]
            latDir = splittedData[5] 
            lon = splittedData[6] 
            lonDir = splittedData[7] 
            #print(lat,",",latDir,",",lon,",",lonDir)
            self.id = comType[1]
            self.parsedData['id'] = self.id
            self.parsedData['lat'] = lat
            self.parsedData['lon'] = lon
            self.parsedData['spd'] = speed
            self.parsedData['alt'] = altitude
            self.parsedData['dir'] = direction
            self.parsedData['b'] = battery
            self.parsedData['sc'] = walkStep 
            self.parsedData['spd'] = speed
            self.parsedData['alt'] = altitude
            self.parsedData['dir'] = direction
            self.parsedData['b'] = battery
            self.parsedData['sc'] = walkStep
        elif comType[3] == "WG":
            speed = splittedData[8]
            direction = splittedData[9]
            altitude = splittedData[10]
            battery = splittedData[13]
            walkStep = splittedData[15]
            lat = splittedData[4]
            latDir = splittedData[5] 
            lon = splittedData[6] 
            lonDir = splittedData[7] 
            #print(lat,",",latDir,",",lon,",",lonDir)
            self.id = comType[1]
            self.parsedData['id'] = self.id
            self.parsedData['lat'] = lat
            self.parsedData['lon'] = lon
            self.parsedData['spd'] = speed
            self.parsedData['alt'] = altitude
            self.parsedData['dir'] = direction
            self.parsedData['b'] = battery
            self.parsedData['sc'] = walkStep 
            self.parsedData['spd'] = speed
            self.parsedData['alt'] = altitude
            self.parsedData['dir'] = direction
            self.parsedData['b'] = battery
            self.parsedData['sc'] = walkStep
            locationRequestResponse = "SG*8800000015*0021*RG,BASE,"+lat+","+latDir+","+lon+","+lonDir
            #locationRequestResponse = "01"
            hex = bytes(locationRequestResponse,'utf-8')
            hex2 = binascii.hexlify(hex)
            self.data_to_write.insert(0, binascii.unhexlify(hex2))         
                
def dataHandler():
    while True:
        global requestsToSend
        countOfRequests = len(requestsToSend)
        print("Number of Requests: ", countOfRequests)
        while countOfRequests > 0:
            request = requestsToSend[0]
            response = requests.request("GET", request)
            response = response.status_code
            if response == 204:
                print("Removing: ", request)
                requestsToSend.remove(request)
            else:
                print("Error Sending: ", request)
            print("Response from Provissioner: , Pending: ", response,  countOfRequests)
            countOfRequests = len(requestsToSend)
            # print("Remaining Number of Requests: ",countOfRequests)
        time.sleep(DATA_PACKET_SENDING_DELAY)

def main():
    print("SDK is running, please check teltonika.log file for debugging...")
    HOST = '0.0.0.0'
    s = Server((HOST, TCP_SERVER_PORT))
    asyncore.loop()


if __name__ == '__main__':
    main()
