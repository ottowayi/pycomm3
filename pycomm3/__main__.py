import sys


def register_COM_server():
    if '--register' in sys.argv or '--unregister' in sys.argv:
        from pycomm3.com_server import CLXDriverCOMServer
        import win32com.server.register

        win32com.server.register.UseCommandLine(CLXDriverCOMServer)


if __name__ == '__main__':
    register_COM_server()
