from eip import EipBase

if __name__ == '__main__':
    c = EipBase()
    c.open('192.168.1.10')
    c.close()



