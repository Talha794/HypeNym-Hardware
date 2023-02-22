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
        # print('Raw Received Data: () ""', len(rawTCPData), rawTCPData.rstrip())
        rawHexData = binascii.hexlify(rawTCPData).decode()
        print("Raw Hex Data: ", rawHexData , ", Len: ", len(rawHexData))
        self.data_parsing(rawHexData)

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
        url = "http://" + PROVISIONER_SERVER + ":" + PROVISIONER_PORT + "/data/iol?&data=" + dataToSend
        try:
            asyncio.run(self.sendAsyncReq(url))
        except:
            print("Data Sending Exception occurred: ", self.id)
        self.parsedData = {}

    def data_parsing(self, rawHexData):
        # rawHexData raw data parsing
        pass

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
