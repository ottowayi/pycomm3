'''
Connection/Read Test App by GitHubDragonFly (see the screenshots here: https://github.com/ottowayi/pycomm3/issues/98)

- A simple Tkinter window to display discovered devices, tags and their values.
- Adjust the resolution by changing the values in this line below: root.geometry('800x600')
- Designed for reading only, either a single or multiple tags.
- Make sure to set the correct IP Address and Processor Slot for your network.
- The Connection, Device Discovery and Get Tags are all set to work on separate threads.
- Double clicking the device discovery window line with the IP Address will copy that IP to the clipboard.
- Non-traditional "Paste" option was provided for the IP Adress and Tag entry boxes.
- Since the addressing is in the Tag format then it follows the rules of the pycomm3 library itself.
  For requesting multiple values use a tag format like this:
  - CT_STRINGArray[0]{5} - request 5 consecutive values from this string array starting at index 0.
  - CT_STRING, CT_DINT, CT_REAL - read each of these comma separated tags (this is the app's default startup option).
- The code itself will attempt to extract all the values from the received responses (which are in the dictionary format).
- The bottom corners listboxes are designed to show successful connection (left box) and errors (right box).

Notes:
- Tested in Windows 10 with python 3.9 only.
- If the discover() function is not a part of the library then the Discover Devices button will be disabled.

Tkinter vs tkinter - Reference: https://stackoverflow.com/questions/17843596/difference-between-tkinter-and-tkinter
'''

import threading
import socket
import pycomm3

from struct import *
from pycomm3 import *

try:
    from Tkinter import *
except ImportError:
    from tkinter import *

class device_discovery_thread(threading.Thread):
   def __init__(self):
      threading.Thread.__init__(self)
   def run(self):
      discoverDevices()

class get_tags_thread(threading.Thread):
   def __init__(self):
      threading.Thread.__init__(self)
   def run(self):
      getTags()

class connection_thread(threading.Thread):
   def __init__(self):
      threading.Thread.__init__(self)
   def run(self):
      comm_check()

# startup default values
myTag = ['CT_STRING', 'CT_DINT', 'CT_REAL']
ipAddress = '192.168.1.24'
processorSlot = 3

ver = pycomm3.__version__

def main():
    '''
    Create the main window and initiate connection
    '''
    global root
    global comm
    global driverSelection
    global selectedProcessorSlot
    global selectedIPAddress
    global selectedTag
    global tagValue
    global currentTagLine
    global connected
    global updateRunning
    global btnStart
    global btnStop
    global btnConnect
    global btnDiscoverDevices
    global btnGetTags
    global lbDevices
    global lbTags
    global lbPLCError
    global lbPLCMessage
    global sbProcessorSlot
    global tbIPAddress
    global tbTag
    global popup_menu_drivers
    global popup_menu_tbTag
    global popup_menu_tbIPAddress

    root = Tk()
    root.config(background='navy')
    root.title('Pycomm3 GUI - Connection/Read Tester')
    root.geometry('800x600')

    # variable used for the Get Tags listbox to iterate through structures
    currentTagLine = IntVar()

    # boolean variables used to enable/disable buttons and initiate connection
    connected = False
    updateRunning = True

    # bind the "q" keyboard key to quit
    root.bind('q', lambda event:root.destroy())

    # add a frame to hold top widgets
    frame1 = Frame(root, background='navy')
    frame1.pack(side=TOP, fill=X)

    # add list boxes for Device Discovery and Get Tags
    lbDevices = Listbox(frame1, height=11, width=45, bg='lightblue')
    lbTags = Listbox(frame1, height=11, width=45, bg='lightgreen')

    lbDevices.pack(anchor=N, side=LEFT, padx=3, pady=3)

    # add a scrollbar for the Devices list box
    scrollbarDevices = Scrollbar(frame1, orient='vertical', command=lbDevices.yview)
    scrollbarDevices.pack(anchor=N, side=LEFT, pady=3, ipady=65)
    lbDevices.config(yscrollcommand = scrollbarDevices.set)

    # copy selected IP Address to the clipboard on the mouse double-click
    # this is currently set to work for IP Address only
    lbDevices.bind('<Double-Button-1>', lambda event: ip_copy())

    # add the Discover Devices button
    btnDiscoverDevices = Button(frame1, text = 'Discover Devices', fg ='green', height=1, width=14, command=start_discover_devices)
    btnDiscoverDevices.pack(anchor=N, side=LEFT, padx=3, pady=3)

    # if the discover() function is not included then disable the Discover Devices button (pycomm3 version 0.12.0 or lower)
    if getattr(LogixDriver,'discover', 'not present') == 'not present':
        btnDiscoverDevices['state'] = 'disabled'
        lbDevices.insert(1, 'discover() function unavailable')

    # add a scrollbar for the Tags list box
    scrollbarTags = Scrollbar(frame1, orient='vertical', command=lbTags.yview)
    scrollbarTags.pack(anchor=N, side=RIGHT, padx=3, pady=3, ipady=65)
    lbTags.config(yscrollcommand = scrollbarTags.set)

    lbTags.pack(anchor=N, side=RIGHT, pady=3)

    # add the Get Tags button
    btnGetTags = Button(frame1, text = 'Get Tags', fg ='green', height=1, width=14, command=start_get_tags)
    btnGetTags.pack(anchor=N, side=RIGHT, padx=3, pady=3)

    # create a label to display tag(s) value(s)
    tagValue = Label(root, text='~', fg='yellow', bg='navy', font='Helvetica 18', width=52, relief=SUNKEN)
    tagValue.place(anchor=CENTER, relx=0.5, rely=0.5)

    # create a label and a text box for the IPAddress entry
    lblIPAddress = Label(root, text='IP Address', fg='white', bg='navy', font='Helvetica 9')
    lblIPAddress.place(anchor=CENTER, relx=0.5, rely=0.085)
    selectedIPAddress = StringVar()
    tbIPAddress = Entry(root, justify=CENTER, textvariable=selectedIPAddress)
    selectedIPAddress.set(ipAddress)

    # add the "Paste" menu on the mouse right-click
    popup_menu_tbIPAddress = Menu(tbIPAddress, tearoff=0)
    popup_menu_tbIPAddress.add_command(label='Paste', command=ip_paste)
    tbIPAddress.bind('<Button-3>', lambda event: ip_menu(event, tbIPAddress))

    tbIPAddress.place(anchor=CENTER, relx=0.5, rely=0.12)

    # create a label and a spinbox for the ProcessorSlot entry
    lblProcessorSlot = Label(root, text='Processor Slot', fg='white', bg='navy', font='Helvetica 9')
    lblProcessorSlot.place(anchor=CENTER, relx=0.5, rely=0.165)
    selectedProcessorSlot = StringVar()
    sbProcessorSlot = Spinbox(root, width=10, justify=CENTER, from_ = 0, to = 20, increment=1, textvariable=selectedProcessorSlot, state='readonly')
    selectedProcessorSlot.set(processorSlot)
    sbProcessorSlot.place(anchor=CENTER, relx=0.5, rely=0.2)

    # create a label and a text box for the Tag entry
    lblTag = Label(root, text='Tag(s) To Read', fg='white', bg='navy', font='Helvetica 9')
    lblTag.place(anchor=CENTER, relx=0.5, rely=0.38)
    selectedTag = StringVar()
    tbTag = Entry(root, justify=CENTER, textvariable=selectedTag, font='Helvetica 10', width=90)
    selectedTag.set(str(myTag)[1:-1].replace('\'', ''))

    # add the "Paste" menu on the mouse right-click
    popup_menu_tbTag = Menu(tbTag, tearoff=0)
    popup_menu_tbTag.add_command(label='Paste', command=tag_paste)
    tbTag.bind('<Button-3>', lambda event: tag_menu(event, tbTag))

    tbTag.place(anchor=CENTER, relx=0.5, rely=0.42)

    # add a frame to hold the label for pycomm3 version and the driver choices OptionMenu (combobox)
    frame2 = Frame(root, background='navy')
    frame2.pack(fill=X)

    # create a label to show pycomm3 version
    lblVersion = Label(frame2, text='pycomm3 version ' + ver, fg='grey', bg='navy', font='Helvetica 9')
    lblVersion.pack(side=LEFT, padx=3)

    # create the driver selection variable
    driverSelection = StringVar()
    driverChoices = { 'LogixDriver','SLCDriver'}
    driverSelection.set('LogixDriver')
    driverSelection.trace('w', driver_selector)

    # create the driver selection popup menu
    popup_menu_drivers = OptionMenu(frame2, driverSelection, *driverChoices)
    popup_menu_drivers.pack(side=RIGHT, padx=3)

    # add a frame to hold bottom widgets
    frame3 = Frame(root, background='navy')
    frame3.pack(side=BOTTOM, fill=X)

    # add a list box for PLC error messages
    lbPLCError = Listbox(frame3, justify=CENTER, height=1, width=45, fg='red', bg='lightgrey')
    lbPLCError.pack(anchor=S, side=RIGHT, padx=3, pady=3)

    # add a list box for PLC connection messages
    lbPLCMessage = Listbox(frame3, justify=CENTER, height=1, width=45, fg='blue', bg='lightgrey')
    lbPLCMessage.pack(anchor=S, side=LEFT, padx=3, pady=3)

    # add the Connect button
    btnConnect = Button(root, text = 'Connect', fg ='green', height=1, width=10, command=start_connection)
    btnConnect.place(anchor=CENTER, relx=0.43, rely=0.972)

    # add the Exit button
    btnExit = Button(root, text = 'Exit', fg ='red', height=1, width=10, command=root.destroy)
    btnExit.place(anchor=CENTER, relx=0.57, rely=0.972)

    # add the button to start updating tag value
    btnStart = Button(root, text = 'Start Update', state='normal', fg ='blue', height=1, width=10, command=startUpdateValue)
    btnStart.place(anchor=CENTER, relx=0.44, rely=0.6)

    # add the button to stop updating tag value
    btnStop = Button(root, text = 'Stop Update', state='disabled', fg ='blue', height=1, width=10, command=stopUpdateValue)
    btnStop.place(anchor=CENTER, relx=0.56, rely=0.6)

    start_connection()

    root.mainloop()

    try:
        if not comm is None:
            comm.close()
            comm = None
    except Exception as e:
        pass

def driver_selector(*args):
    if driverSelection.get() == 'SLCDriver':
        lbTags.delete(0, 'end') #clear the tags listbox
        lbPLCMessage.delete(0, 'end') #clear the connection message listbox
        lbPLCError.delete(0, 'end') #clear the error message listbox
        btnGetTags['state'] = 'disabled'
        sbProcessorSlot['state'] = 'disabled'
        selectedIPAddress.set('192.168.1.10')
    else:
        btnGetTags['state'] = 'normal'
        sbProcessorSlot['state'] = 'normal'
        selectedIPAddress.set('192.168.1.24')

    selectedTag.set('')
    start_connection()

def start_connection():
    try:
        thread1 = connection_thread()
        thread1.setDaemon(True)
        thread1.start()
    except Exception as e:
        print('unable to start thread1 - connection_thread, ' + str(e))

def start_discover_devices():
    try:
        thread2 = device_discovery_thread()
        thread2.setDaemon(True)
        thread2.start()
    except Exception as e:
        print('unable to start thread2 - device_discovery_thread, ' + str(e))

def start_get_tags():
    try:
        thread3 = get_tags_thread()
        thread3.setDaemon(True)
        thread3.start()
    except Exception as e:
        print('unable to start thread3 - get_tags_thread, ' + str(e))

def discoverDevices():
    global comm

    lbDevices.delete(0, 'end')

    try:
        if not comm is None:
            if not comm.connected:
                start_connection()

            devices = comm.discover()

            if str(devices) == '[]':
                lbDevices.insert(1, 'No Devices Discovered')
            else:
                i = 0
                for device in devices:
                    lbDevices.insert(i * 8 + 1, 'IP Address: ' + socket.inet_ntoa(pack('<L', unpack_from('<I', device['_socket_address_struct'], 2)[0])))
                    lbDevices.insert(i * 8 + 2, 'Product Name: ' + device['product_name'])
                    lbDevices.insert(i * 8 + 3, 'Product Code: ' + str(device['product_code']))
                    lbDevices.insert(i * 8 + 4, 'Revision: ' +  str(device['revision_major']) + '.' + str(device['revision_minor']))
                    lbDevices.insert(i * 8 + 5, 'Serial: ' + str(device['serial_number']))
                    lbDevices.insert(i * 8 + 6, 'State: ' + str(device['state']))
                    lbDevices.insert(i * 8 + 7, 'Status: ' + str(device['status']))
                    lbDevices.insert(i * 8 + 8, '----------------------------------')
                    i += 1
        else:
            start_connection()
    except Exception as e:
            lbDevices.insert(1, 'No Devices Discovered')

def getTags():
    global comm

    lbTags.delete(0, 'end') #clear the tags listbox

    if not connected:
        start_connection()

    try:
        if not comm is None:
            tags = comm.get_tag_list('*') #get all tags

            currentTagLine.set(1) #start at the first line of the tags listbox

            if not tags is None:
                j = 1

                for tag, _def in comm.tags.items():
                    #-----------------------------------------------------------------------
                    # Extract dimensions and format them for displaying
                    #-----------------------------------------------------------------------

                    dimensions = ''
                    dim = _def['dim']

                    if dim != 0:
                        dims = str(_def['dimensions'])[1:-1].split(',')

                        if dim == 1:
                            dimensions = '[' + dims[0] + ']'
                        elif dim == 2:
                            dimensions = '[' + dims[0] + ',' + dims[1] + ']'
                        else:
                            dimensions = '[' + dims[0] + ',' + dims[1] + ',' + dims[2] + ']'

                    #-----------------------------------------------------------------------
                    # If structure then process this and all subsequent structures
                    #-----------------------------------------------------------------------

                    if _def['tag_type'] == 'struct':
                        structureDataType = _def['data_type']['name']
                        structureSize = _def['data_type']['template']['structure_size']

                        lbTags.insert(currentTagLine.get(), tag + dimensions + ' (' + structureDataType + ')' + ' (' + str(structureSize) + ' bytes)')
                        currentTagLine.set(currentTagLine.get() + 1)

                        struct_members(_def['data_type']['internal_tags'], currentTagLine.get(), j)
                    else:
                        lbTags.insert(currentTagLine.get(), tag + dimensions + ' (' + _def['data_type'] + ')')

                    #-----------------------------------------------------------------------

                    j = 1
                    currentTagLine.set(currentTagLine.get() + 1)
            else:
                lbTags.insert(1, 'No Tags Retrieved')
        else:
            lbTags.insert(1, 'No Tags Retrieved')
    except Exception as e:
        lbPLCMessage.delete(0, 'end')
        lbPLCError.insert(1, e)
        lbTags.insert(1, 'No Tags Retrieved')

def struct_members(it, i, j):
    # internal tags keys
    keys = it.keys()

    for key in keys:
        tag = it[key]

        if tag['tag_type'] == 'struct':
            structureDataType = tag['data_type']['name']
            structureSize = tag['data_type']['template']['structure_size']

            add_Tag(j, '- ' + key + ' (' + structureDataType + ')' + ' (' + str(structureSize) + ' bytes)')

            currentTagLine.set(i + 1)

            struct_members(tag['data_type']['internal_tags'], currentTagLine.get() + 1, j + 1)
        else:
            if tag['data_type'] == 'BOOL':
                add_Tag(j, '- ' + key + ' (offset ' + str(tag['offset']) + ')' + ' (bit ' + str(tag['bit']) + ')' + ' (' + tag['data_type'] + ')')
            else:
                if tag['array'] > 0:
                    add_Tag(j, '- ' + key + '[' + str(tag['array']) + ']' + ' (offset ' + str(tag['offset']) + ')' + ' (' + tag['data_type'] + ')')
                else:
                    add_Tag(j, '- ' + key + ' (offset ' + str(tag['offset']) + ')' + ' (' + tag['data_type'] + ')')

            currentTagLine.set(currentTagLine.get() + 1)

    return None

def add_Tag(j, string):
    #insert multiple of 2 spaces, depending on the structure depth, to simulate the tree appearance
    k = 2 * j + len(string)
    lbTags.insert(currentTagLine.get(), (' ' * k + string)[-k:])

def comm_check():
    global comm
    global connected
    global ipAddress
    global processorSlot

    ip = selectedIPAddress.get()
    port = int(selectedProcessorSlot.get())

    try:
        if not comm is None:
            comm.close()
            comm = None
    except Exception as e:
        pass

    if (ipAddress != ip or processorSlot != port):
        ipAddress = ip
        processorSlot = port

    try:
        if driverSelection.get() == 'LogixDriver':
            comm = LogixDriver(ipAddress + '/' + str(processorSlot))
            comm.open()
            lbPLCMessage.insert(1, 'Connected --> keyswitch:  ' + comm.info['keyswitch'])
        else:
            comm = SLCDriver(ipAddress)
            comm.open()
            lbPLCMessage.insert(1, 'Connected to: ' + ipAddress)

        connected = True
        lbPLCError.delete(0, 'end')
        btnConnect['state'] = 'disabled'
        if btnStop['state'] == 'disabled':
            btnStart['state'] = 'normal'
    except Exception as e:
        connected = False
        lbPLCMessage.delete(0, 'end')
        lbPLCError.insert(1, e)
        btnConnect['state'] = 'normal'
        btnStart['state'] = 'disabled'

def startUpdateValue():
    global updateRunning

    '''
    Call ourself to update the screen
    '''

    if (ipAddress != selectedIPAddress.get() or processorSlot != int(selectedProcessorSlot.get())):
        start_connection()
    else:
        displayTag = selectedTag.get()

        if displayTag != '':
            myTag = []
            if ',' in displayTag:
                tags = displayTag.split(',')
                for tag in tags:
                    myTag.append(str(tag).replace(' ', ''))
            else:
                myTag.append(displayTag.replace(' ', ''))

            if not updateRunning:
                updateRunning = True
            else:
                try:
                    btnStart['state'] = 'disabled'
                    btnStop['state'] = 'normal'
                    tbIPAddress['state'] = 'disabled'
                    sbProcessorSlot['state'] = 'disabled'
                    tbTag['state'] = 'disabled'
                    popup_menu_drivers['state'] = 'disabled'
                    results = comm.read(*myTag)
                    allValues = ''
                    if len(myTag) == 1:
                        tagValue['text'] = results.value
                    else:
                        for tag in results:
                            allValues += str(tag.value) + ', '
                        tagValue['text'] = allValues[:-2]
                    root.after(500, startUpdateValue)
                except Exception as e:
                    lbPLCMessage.delete(0, 'end')
                    lbPLCError.insert(1, e)
                    tagValue['text'] = '~'
                    connected = False
                    start_connection()
                    root.after(2000, startUpdateValue)

def stopUpdateValue():
    global updateRunning
   
    if updateRunning:
        updateRunning = False
        tagValue['text'] = '~'
        btnStart['state'] = 'normal'
        btnStop['state'] = 'disabled'
        tbIPAddress['state'] = 'normal'
        sbProcessorSlot['state'] = 'normal'
        tbTag['state'] = 'normal'
        popup_menu_drivers['state'] = 'normal'

def tag_menu(event, tbTag):
    try:
        old_clip = root.clipboard_get()
        if (not old_clip is None) and (type(old_clip) is str) and (tbTag['state'] == 'normal'):
            tbTag.select_range(0, 'end')
            popup_menu_tbTag.post(event.x_root, event.y_root)
    except TclError:
        print('Not a valid string contents on the clipboard!')

def tag_paste():
    # user clicked the "Paste" option so paste the tag from the clipboard
    selectedTag.set(root.clipboard_get())
    tbTag.select_range(0, 'end')
    tbTag.icursor('end')

def ip_copy():
    if (lbDevices.get(ANCHOR)).split(' ')[0] == 'IP':
        root.clipboard_clear()
        listboxSelectedIPAddress = (lbDevices.get(ANCHOR)).split(' ')[2]
        root.clipboard_append(listboxSelectedIPAddress)

def ip_menu(event, tbIPAddress):
    if (root.clipboard_get() != '') and (type(root.clipboard_get()) is str) and (tbIPAddress['state'] == 'normal'):
        tbIPAddress.select_range(0, 'end')
        popup_menu_tbIPAddress.post(event.x_root, event.y_root)

def ip_paste():
    # user clicked the "Paste" option so paste the IP Address from the clipboard
    selectedIPAddress.set(root.clipboard_get())
    tbIPAddress.select_range(0, 'end')
    tbIPAddress.icursor('end')

if __name__=='__main__':
    main()
