import serial
import time
import sqlite3
import datetime
import os

enroll_id = 1
portSettings = ['', 0]
bytearr = bytearray()

FINGERPRINT_OK = 0
FINGERPRINT_PACKETRECIEVEERR = 1
FINGERPRINT_NOFINGER = 2
FINGERPRINT_IMAGEFAIL = 3
FINGERPRINT_IMAGEMESS = 6
FINGERPRINT_FEATUREFAIL = 7
FINGERPRINT_INVALIDIMAGE = 0x15
FINGERPRINT_ENROLLMISMATCH = 0x0A
FINGERPRINT_BADLOCATION = 0x0B
FINGERPRINT_FLASHERR = 0x18
#packet = list()

table_present = False
if os.path.exists("./fingerprint.db"):
    table_present = True
conn = sqlite3.connect('fingerprint.db')

c = conn.cursor()

if not table_present:
    c.execute('''CREATE TABLE runtime (datetime, fingerprint)''')


def generatePacket(pid, length, instcode,data=None):
    #TODO: Generate packet
    packet = bytearray(length + 9)
    # print(pid, length, data)
    packet[0] = 0xEF
    packet[1] = 0x01
    packet[2:6] = 0xFFFFFFFF.to_bytes(4, byteorder='big')
    packet[6] = pid
    packet[7:9] = length.to_bytes(2, byteorder='big')
    packet[9] = instcode
    if data is not None:
        packet[10:7+length] = data.to_bytes(length-3, byteorder='big')
        
    # print(len(packet))
    checksum = sum(packet[6:7+length])
    packet[7+length:9+length] = checksum.to_bytes(2, byteorder='big')
    # for p in packet:
    #     print(hex(p))
    return packet
    # pass

def sendGeneratedPacket(packet, receiveLength):
    #TODO: Write the bytearray(packet) over serial.
    # print(packet)
    global bytearr
    _bytearr = bytearray()
    try:
        # open the port; timeout is 1 sec; also resets the arduino
        ser = serial.Serial(portSettings[0], portSettings[1], timeout=1)
        # ser.open()
    except Exception as e:
        print('Invalid port settings!')
        print(e)
        #ser.close()
        return
    while ser.is_open:
        #for i in range(len(packet)):
        try:
            ser.write(packet) 
        except Exception as e:
            print(e)
        for i in range(receiveLength):
            try:
                byte = ser.read()
                # print(byte)
                if not byte:
                    print("Timeout")
                # _bytearr.append(byte.hex())
                _bytearr += byte
                    #ser.close()
                # print(byte)
            except Exception as e:
                print(e)
        ser.close()
        print(_bytearr)
        if receiveLength > 500:
            bytearr = _bytearr
    return _bytearr


def verifyPassword():
    #TODO: Generate and send packet to verify password. 0000 by default.
    packet = generatePacket(0x01, 0x0007, 0x13, 0x00000000)
    rcvdPacket = sendGeneratedPacket(packet, 12)
    if rcvdPacket[9] == 0x00:
        print("Password verified. Device found")
    pass

def configPort():
    #TODO: Configure serial port
    print("Configure port settings")
    portSettings[0] = "/dev/ttyUSB0" #input("Enter serial port number: ")
    portSettings[1] = 9600 #int(input("Enter baud rate: "))
    print(portSettings)
    pass

def getImage():
    #TODO: Get Image on the sensor
    packet = generatePacket(0x01, 0x0003, 0x01)
    rcvdPacket = sendGeneratedPacket(packet, 12)
    # print(rcvdPacket)
    if rcvdPacket[0] == 0:
        return rcvdPacket[11]
    else:
        return rcvdPacket[9]
    # pass

def image2Tz(slot=1):
    #TODO: Convert image to template and store in charbuffer<slot>. Available options are 1 and 2.
    packet = generatePacket(0x01, 0x0004, 0x02, slot)
    rcvdPacket = sendGeneratedPacket(packet, 12)
    return rcvdPacket[9]
    # pass

def createModel():
    #TODO: Create model from template stored in charBuffer1 and charBuffer2
    packet = generatePacket(0x01, 0x0003, 0x05)
    rcvdPacket = sendGeneratedPacket(packet, 12)
    return rcvdPacket[9]
    # pass

def storeModel(eid):
    #TODO: Store the generated model in flash with id eid
    _data = (0x01 << 16) | eid
    print(hex(_data))
    packet = generatePacket(0x01, 0x0006, 0x06, _data)
    rcvdPacket = sendGeneratedPacket(packet, 12)
    return rcvdPacket[9]
    # pass

def enroll():
    #TODO: Get empty location and then enroll fingerprint.
    global enroll_id
    p = -1
    print("Put finger on sensor")
    while(p != FINGERPRINT_OK):
        p = getImage()
        if p == FINGERPRINT_OK:
            print("Image Taken")
        elif p == FINGERPRINT_NOFINGER:
            print(".")
        elif p == FINGERPRINT_PACKETRECIEVEERR:
            print("Communication error")
            return p
        elif p == FINGERPRINT_IMAGEFAIL:
            print("Image error")
            return p
        else:
            print("Unknown Error {}".format(p))
            return p
    
    p = image2Tz(1)
    if p == FINGERPRINT_OK:
        print("Image converted")
    elif p == FINGERPRINT_IMAGEMESS:
        print("Image too messy")
        return p
    elif p == FINGERPRINT_PACKETRECIEVEERR:
        print("Communication error")
        return p
    elif p == FINGERPRINT_FEATUREFAIL:
        print("Could not find fingerprint features")
        return p
    elif p == FINGERPRINT_INVALIDIMAGE:
        print("Invalid Image")
        return p
    else:
        print("Unknown Error {}".format(p))
        return p

    print("Remove Finger")
    time.sleep(2)
    p = 0
    while p is not FINGERPRINT_NOFINGER:
        p = getImage()
    p = -1
    print("Place Same Finger again")
    while(p != FINGERPRINT_OK):
        p = getImage()
        if p == FINGERPRINT_OK:
            print("Image Taken")
        elif p == FINGERPRINT_NOFINGER:
            print(".")
        elif p == FINGERPRINT_PACKETRECIEVEERR:
            print("Communication error")
            return p
        elif p == FINGERPRINT_IMAGEFAIL:
            print("Image error")
            return p
        else:
            print("Unknown Error {}".format(p))
            return p
    
    p = image2Tz(2)
    if p == FINGERPRINT_OK:
        print("Image converted")
    elif p == FINGERPRINT_IMAGEMESS:
        print("Image too messy")
        return p
    elif p == FINGERPRINT_PACKETRECIEVEERR:
        print("Communication error")
        return p
    elif p == FINGERPRINT_FEATUREFAIL:
        print("Could not find fingerprint features")
        return p
    elif p == FINGERPRINT_INVALIDIMAGE:
        print("Invalid Image")
        return p
    else:
        print("Unknown Error {}".format(p))
        return p
    
    print("Creating model")
    p = createModel()
    if p == FINGERPRINT_OK:
        print("Fingerprint matched")
    elif p == FINGERPRINT_PACKETRECIEVEERR:
        print("Communication error")
        return p
    elif p == FINGERPRINT_ENROLLMISMATCH:
        print("Fingerprint did not match")
        return p
    else:
        print("Unknown Error {}".format(p))
        return p
    
    print("Storing model at {}".format(enroll_id))
    p = storeModel(enroll_id)
    if p == FINGERPRINT_OK:
        print("Stored!")
        enroll_id = enroll_id + 1
    elif p == FINGERPRINT_PACKETRECIEVEERR:
        print("Communication error")
        return p
    elif p == FINGERPRINT_BADLOCATION:
        print("Could not save in specified location")
        return p
    elif p == FINGERPRINT_FLASHERR:
        print("Error writing to flash")
        return p
    else:
        print("Unknown Error {}".format(p))
        return p
    
def loadModel(n):
    _data = (0x01 << 16) | int(n)
    print(hex(_data))
    packet = generatePacket(0x01, 0x0006, 0x07, _data)
    rcvdPacket = sendGeneratedPacket(packet, 12)
    return rcvdPacket[9]

def downloadModel(n,slot=1):
    packet = generatePacket(0x01, 0x0004, 0x08, slot)
    print(packet.hex())
    rcvdPacket = sendGeneratedPacket(packet, 1000)
    if rcvdPacket[9] == FINGERPRINT_OK:
        print("Model {} transferring".format(n))
        return 0
    else:
        return -1

def getModel(n):
    #TODO: Retrieve the just saved model from sensor's flash memory
    # _data = 0x01 + enroll_id - 1
    global bytearr
    p = -1
    p = loadModel(n)
    if p == FINGERPRINT_OK:
        print("Model {} loaded".format(n))
    elif p == FINGERPRINT_PACKETRECIEVEERR:
        print("Communication error")
        return p
    else:
        print("Unknown Error {}".format(p))
        return p

    p = downloadModel(n)
    if p == FINGERPRINT_OK:
        print("Model loaded")
    c.execute("INSERT INTO runtime VALUES(?, ?)", (datetime.datetime.utcnow().strftime("%H-%M-%S"), bytearr.hex()))
    bytearr[:] = b'\x00' * len(bytearr)
    conn.commit()
    # pass

def emptyDatabase():
    packet = generatePacket(0x01, 0x0003, 0x0d)
    rcvdPacket = sendGeneratedPacket(packet, 12)
    if rcvdPacket[9] == 0x00:
        print("Database cleared")
    else:
        print("Error {}".format(rcvdPacket[9]))

def moduleSearch():
    packet = generatePacket(0x01, 0x0008, 0x04, 0x0100A3)
    rcvdPacket = sendGeneratedPacket(packet, 16)
    if rcvdPacket[9] == 0x00:
        print("Found match {}, {}".format(rcvdPacket[10:12].hex(), rcvdPacket[12:14].hex()))
    else:
        print("Error {}".format(rcvdPacket[9]))

def search():
    #TODO: Take image, convert to template and search in database.
    global bytearr
    p = -1
    while(p != FINGERPRINT_OK):
        p = getImage()
        if p == FINGERPRINT_OK:
            print("Image Taken")
        elif p == FINGERPRINT_NOFINGER:
            print(".")
        elif p == FINGERPRINT_PACKETRECIEVEERR:
            print("Communication error")
            return p
        elif p == FINGERPRINT_IMAGEFAIL:
            print("Image error")
            return p
        else:
            print("Unknown Error {}".format(p))
            return p
    p=-1
    # time.sleep(2)
    p = image2Tz(1)
    if p == FINGERPRINT_OK:
        print("Image converted")
    elif p == FINGERPRINT_IMAGEMESS:
        print("Image too messy")
        return p
    elif p == FINGERPRINT_PACKETRECIEVEERR:
        print("Communication error")
        return p
    elif p == FINGERPRINT_FEATUREFAIL:
        print("Could not find fingerprint features")
        return p
    elif p == FINGERPRINT_INVALIDIMAGE:
        print("Invalid Image")
        return p
    else:
        print("Unknown Error {}".format(p))
        return p

    moduleSearch()
    print("Getting model 1")
    p = downloadModel(0,1)
    if p == FINGERPRINT_OK:
        print("Model loaded")
    c.execute("INSERT INTO runtime VALUES(?, ?)", (datetime.datetime.utcnow().strftime("%H-%M-%S"), bytearr.hex()))
    bytearr = 0 * len(bytearr)
    conn.commit()
    


while(1):
    print("Choose an option: ")
    choice = int(input())
    if choice == 1:
        configPort()
    elif choice == 2:
        verifyPassword()
    elif choice == 3:
        enroll()
    elif choice == 4:
        n = input("Enter model to load")
        getModel(n)
    elif choice == 5:
        search()
    elif choice == 6:
        emptyDatabase()
    else:
        print("Unknown option {}".format(choice))

conn.close()
