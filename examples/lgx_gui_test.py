'''
Connection/Read Test App by GitHubDragonFly (see the screenshots here: https://github.com/ottowayi/pycomm3/issues/98)

- A simple Tkinter window to display discovered devices, tags and their values.
- Adjust the resolution by changing the values in this line below: root.geometry('800x600')
- Designed for reading only, either a single or multiple tags.
- Make sure to set the correct path for your PLC (https://pycomm3.readthedocs.io/en/latest/logixdriver.html).
- The Connection, Device Discovery and Get Tags are all set to work on separate threads.
- Double clicking the device discovery window line with the IP Address will copy that IP to the clipboard.
- Non-traditional "Paste" option was provided for the Path and Tag entry boxes.
- Since the addressing is in the Tag format then it follows the rules of the pycomm3 library itself.
  For requesting multiple values use a tag format like this:
  - CT_STRINGArray[0]{5} - request 5 consecutive values from this string array starting at index 0.
  - CT_STRING; CT_DINT; CT_REAL - read each of these semicolon separated tags (this is the app's default startup option).
  This is applicable for both LogixDriver and SLCDriver.
- The code itself will attempt to extract all the values from the received responses (which are in the dictionary format).
- The bottom corners listboxes are designed to show successful connection (left box) and errors (right box).

Notes:
- Minimum python version required is 3.6.1 (using tkinter only while Tkinter was removed).
- Tested in Windows 10 with python 3.6.8 and Raspbian Buster / Kali Linux with python 3.7.x.
- If the discover() function is not a part of the library then the Discover Devices button will be disabled.

Window/widget resizing
Reference: https://stackoverflow.com/questions/22835289/how-to-get-tkinter-canvas-to-dynamically-resize-to-window-width
'''

import os.path
import datetime
import platform
import threading
from struct import *

from pycomm3 import *
import pycomm3

from tkinter import *
import tkinter.font as tkfont

# width wise resizing of the tag label (window)
class LabelResizing(Label):
    def __init__(self,parent,**kwargs):
        Label.__init__(self,parent,**kwargs)
        self.bind("<Configure>", self.on_resize)
        self.width = self.winfo_reqwidth()

    def on_resize(self,event):
        if self.width > 0:
            self.width = int(event.width)
            self.config(width=self.width, wraplength=self.width)

# width wise resizing of the tag entry box (window)
class EntryResizing(Entry):
    def __init__(self,parent,**kwargs):
        Entry.__init__(self,parent,**kwargs)
        self.bind("<Configure>", self.on_resize)
        self.width = self.winfo_reqwidth()

    def on_resize(self,event):
        if self.width > 0:
            self.width = int(event.width)
            self.config(width=self.width)

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

class update_thread(threading.Thread):
   def __init__(self):
      threading.Thread.__init__(self)
   def run(self):
      startUpdateValue()

# startup default values
myTag = ['CT_STRING', 'CT_DINT', 'CT_REAL']
path = '192.168.1.15/3'
headerAdded = False

ver = pycomm3.__version__

def main():
    '''
    Create the main window and initiate connection
    '''
    global root
    global comm
    global driverSelection
    global selectedPath
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
    global tbPath
    global tbTag
    global popup_menu_drivers
    global popup_menu_tbTag
    global popup_menu_tbPath
    global checkVarLogTagValues
    global checkVarBoolDisplay
    global checkVarSaveTags
    global chbSaveTags
    global popup_menu_save_tags_list
    global previousLogHeader
    global chbLogTagValues
    global chbBoolDisplay
    global checkVarBoolDisplay
    global app_closing

    root = Tk()
    root.config(background='navy')
    root.title('Pycomm3 GUI - Connection/Read Tester (Python v' + platform.python_version() + ')')
    root.geometry('800x600')
    root.bind('<Destroy>', on_exit)

    previousLogHeader = ''

    app_closing = False

    # variable used for the Get Tags listbox to iterate through structures
    currentTagLine = IntVar()

    # boolean variables used to enable/disable buttons and initiate connection
    connected = False
    updateRunning = True

    # bind the "q" keyboard key to quit
    root.bind('q', lambda event:root.destroy())

    #----------------------------------------------------------------------------------------

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

    #----------------------------------------------------------------------------------------

    # add a frame to hold the pycomm3 version label, 'Log Tags Values' + 'Save Tags List' checkboxes and driver choices OptionMenu (combobox)
    frame2 = Frame(root, background='navy')
    frame2.pack(fill=X)

    # create a label to show pycomm3 version
    lblVersion = Label(frame2, text='pycomm3 version ' + ver, fg='grey', bg='navy', font='Helvetica 9')
    lblVersion.pack(side=LEFT, padx=3)

    # add 'Log tag values' checkbox
    checkVarLogTagValues = IntVar()
    chbLogTagValues = Checkbutton(frame2, text='Log Tags Values', variable=checkVarLogTagValues, command=setBoolDisplayForLogging)
    checkVarLogTagValues.set(0)
    chbLogTagValues.pack(side='left', padx=45, pady=4)

    # create the driver selection variable
    driverSelection = StringVar()
    driverChoices = ['LogixDriver','SLCDriver']
    driverSelection.set('LogixDriver')
    driverSelection.trace('w', driver_selector)

    # create the driver selection popup menu
    popup_menu_drivers = OptionMenu(frame2, driverSelection, *driverChoices)
    popup_menu_drivers['width'] = 10 # set fixed width to avoid automatic re-sizing
    popup_menu_drivers.pack(side=RIGHT, padx=3)

    # add 'Save Tags List' checkbox
    checkVarSaveTags = IntVar()
    chbSaveTags = Checkbutton(frame2, text='Save Tags List', variable=checkVarSaveTags)
    checkVarSaveTags.set(0)
    chbSaveTags.pack(side='right', padx=85, pady=4)

    # add the tooltip menu on the mouse right-click
    popup_menu_save_tags_list = Menu(chbSaveTags, bg='lightblue', tearoff=0)
    popup_menu_save_tags_list.add_command(label='Click \'Get Tags\' button to save the list', command=set_checkbox_state)
    chbSaveTags.bind('<Button-1>', lambda event: save_tags_list(event, chbSaveTags))

    #----------------------------------------------------------------------------------------

    # add a frame to hold bottom widgets (pack these before the tag value label to limit its expansion)
    frame5 = Frame(root, background='navy')
    frame5.pack(side=BOTTOM, fill=X)

    # add a list box for PLC connection messages
    lbPLCMessage = Listbox(frame5, justify=CENTER, height=1, width=48, fg='blue', bg='lightgrey')
    lbPLCMessage.pack(side=LEFT, padx=3, pady=3)

    # add the Connect button
    btnConnect = Button(frame5, text = 'Connect', fg ='green', height=1, width=9, command=start_connection)
    btnConnect.pack(side=LEFT, padx=15, pady=3)

    # add a list box for PLC error messages
    lbPLCError = Listbox(frame5, justify=CENTER, height=1, width=48, fg='red', bg='lightgrey')
    lbPLCError.pack(side=RIGHT, padx=3, pady=3)

    # add the Exit button
    btnExit = Button(frame5, text = 'Exit', fg ='red', height=1, width=9, command=root.destroy)
    btnExit.pack(side=RIGHT, padx=15, pady=3)

    #----------------------------------------------------------------------------------------

    # add a frame to hold the tag label, tag entry box and the update buttons
    frame3 = Frame(root, background='navy')
    frame3.pack(fill=X)

    # create a label for the Tag entry
    lblTag = Label(frame3, text='Tags to Read (semicolon separated)', fg='white', bg='navy', font='Helvetica 9 italic')
    lblTag.pack(anchor=CENTER, pady=10)

    # add a button to start updating tag value
    btnStart = Button(frame3, text = 'Start Update', state='normal', bg='lightgrey', fg ='blue', height=1, width=10, relief=RAISED, command=start_update)
    btnStart.pack(side=LEFT, padx=5, pady=1)

    # add a button to stop updating tag value
    btnStop = Button(frame3, text = 'Stop Update', state='disabled', bg='lightgrey', fg ='blue', height=1, width=10, relief=RAISED, command=stop_update)
    btnStop.pack(side=RIGHT, padx=5, pady=1)

    # create a text box for the Tag entry
    fnt = tkfont.Font(family="Helvetica", size=11, weight="normal")
    char_width = fnt.measure("0")
    selectedTag = StringVar()
    tbTag = EntryResizing(frame3, justify=CENTER, textvariable=selectedTag, font='Helvetica 11', width=(int(800 / char_width) - 24), relief=RAISED)
    selectedTag.set((str(myTag).replace(',', ';'))[1:-1].replace('\'', ''))

    # add the 'Paste' menu on the mouse right-click
    popup_menu_tbTag = Menu(tbTag, tearoff=0)
    popup_menu_tbTag.add_command(label='Paste', command=tag_paste)
    tbTag.bind('<Button-3>', lambda event: tag_menu(event, tbTag))

    tbTag.pack(side=LEFT, fill=X)

    #----------------------------------------------------------------------------------------

    # add a frame to hold the tag value label
    frame4 = Frame(root, height=30, background='navy')
    frame4.pack(fill=X)

    # create a label to display the received tag(s) value(s)
    fnt = tkfont.Font(family="Helvetica", size=18, weight="normal")
    char_width = fnt.measure("0")
    tagValue = LabelResizing(frame4, text='~', fg='yellow', bg='black', font='Helvetica 18', width=(int(800 / char_width - 4.5)), wraplength=800, relief=SUNKEN)
    tagValue.pack(anchor=CENTER, side=TOP, padx=3, pady=6)

    #----------------------------------------------------------------------------------------

    # create a label and a text box for the path entry
    lblPath = Label(root, text='Path', fg='white', bg='navy', font='Helvetica 9')
    lblPath.place(anchor=CENTER, relx=0.5, rely=0.1)
    selectedPath = StringVar()
    tbPath = Entry(root, justify=CENTER, textvariable=selectedPath, width=32)
    selectedPath.set(path)

    # add the "Paste" menu on the mouse right-click
    popup_menu_tbPath = Menu(tbPath, tearoff=0)
    popup_menu_tbPath.add_command(label='Paste', command=path_paste)
    tbPath.bind('<Button-3>', lambda event: path_menu(event, tbPath))

    tbPath.place(anchor=CENTER, relx=0.5, rely=0.135)

    # add a frame to hold the Boolean Display checkbox
    frameBoolDisplay = Frame(root, background='navy')
    frameBoolDisplay.place(anchor='center', relx=0.5, rely=0.2)

    # add 'Boolean Display' checkbox
    checkVarBoolDisplay = IntVar()
    chbBoolDisplay = Checkbutton(frameBoolDisplay, text='Boolean Display 1 : 0', variable=checkVarBoolDisplay)
    checkVarBoolDisplay.set(0)
    chbBoolDisplay.pack(side='top', anchor='center', pady=3)

    #----------------------------------------------------------------------------------------

    # set the minimum window size to the current size
    root.update()
    root.minsize(root.winfo_width(), root.winfo_height())

    comm = None
    
    start_connection()

    root.mainloop()

    try:
        if not comm is None:
            comm.close()
            comm = None
    except:
        pass

def on_exit(*args):
    global app_closing

    app_closing = True

def driver_selector(*args):
    lbTags.delete(0, 'end') #clear the tags listbox

    if driverSelection.get() == 'SLCDriver':
        selectedPath.set('192.168.1.10')
    else:
        selectedPath.set('192.168.1.15/3')

    lbPLCMessage.delete(0, 'end') #clear the connection message listbox
    lbPLCError.delete(0, 'end') #clear the error message listbox

    selectedTag.set('')

    start_connection()

def setBoolDisplayForLogging():
    global checkVarBoolDisplay

    if checkVarLogTagValues.get() == 1: # force logging bool/bit values as True/False for uniformity
        checkVarBoolDisplay.set(0)
        chbBoolDisplay['state'] = 'disabled'
    else:
        chbBoolDisplay['state'] = 'normal'

def start_connection():
    try:
        thread1 = connection_thread()
        thread1.setDaemon(True)
        thread1.start()
    except Exception as e:
        print('unable to start connection_thread, ' + str(e))

def start_discover_devices():
    try:
        thread2 = device_discovery_thread()
        thread2.setDaemon(True)
        thread2.start()
    except Exception as e:
        print('unable to start device_discovery_thread, ' + str(e))

def start_get_tags():
    try:
        thread3 = get_tags_thread()
        thread3.setDaemon(True)
        thread3.start()
    except Exception as e:
        print('unable to start get_tags_thread, ' + str(e))

def start_update():
    try:
        thread4 = update_thread()
        thread4.setDaemon(True)
        thread4.start()
    except Exception as e:
        print('unable to start update_thread, ' + str(e))

def discoverDevices():
    try:
        lbDevices.delete(0, 'end')

        commDD = None

        try:
            if driverSelection.get() == 'SLCDriver':
                commDD = SLCDriver(path)
            else:
                commDD = LogixDriver(path, init_tags=False, init_program_tags=False)

            commDD.open()

            if commDD.connected:
                devices = commDD.discover()

                if str(devices) == '[]':
                    lbDevices.insert(1, 'No Devices Discovered')
                else:
                    i = 0
                    for device in devices:
                        lbDevices.insert(i * 10 + 1, 'IP Address: ' + device['ip_address'])
                        lbDevices.insert(i * 10 + 2, 'Vendor: ' + device['vendor'])
                        lbDevices.insert(i * 10 + 3, 'Product Name: ' + device['product_name'])
                        lbDevices.insert(i * 10 + 4, 'Product Type: ' + device['product_type'])
                        lbDevices.insert(i * 10 + 5, 'Product Code: ' + str(device['product_code']))
                        lbDevices.insert(i * 10 + 6, 'Revision: ' +  str(device['revision']['major']) + '.' + str(device['revision']['minor']))
                        lbDevices.insert(i * 10 + 7, 'Serial: ' + str(int(device['serial'], 16)))
                        lbDevices.insert(i * 10 + 8, 'State: ' + str(device['state']))
                        lbDevices.insert(i * 10 + 9, 'Status: ' + str(int.from_bytes(device['status'], byteorder='little')))
                        lbDevices.insert(i * 10 + 10, '----------------------------------')
                        i += 1

                if btnConnect['state'] == 'normal':
                    start_connection()
            else:
                lbDevices.insert(1, 'No Devices Discovered')
        except Exception as e:
            lbDevices.insert(1, 'No Devices Discovered')
            if not commDD is None:
                commDD.close()
                commDD = None
    except Exception as e:
        if app_closing:
            pass
        else:
            print(str(e))

def getTags():
    try:
        lbTags.delete(0, 'end') #clear the tags listbox

        commGT = None

        try:
            if driverSelection.get() == 'SLCDriver':
                commGT = SLCDriver(path)
                commGT.open()

                tags = comm.get_file_directory()

                currentTagLine.set(1) #start at the first line of the tags listbox

                if not tags is None:
                    for tag in tags:
                        lbTags.insert(currentTagLine.get(), tag + ' {elements: ' + str(tags[tag]['elements']) + ', length: ' + str(tags[tag]['length']) + '}')
                        currentTagLine.set(currentTagLine.get() + 1)
                else:
                    lbTags.insert(1, 'No Tags Retrieved')

                commGT.close()
                commGT = None
            else:
                commGT = LogixDriver(path)
                commGT.open()

                tags = commGT.get_tag_list('*') #get all tags

                currentTagLine.set(1) #start at the first line of the tags listbox

                if not tags is None:
                    j = 1

                    for tag, _def in commGT.tags.items():
                        #-----------------------------------------------------------------------
                        # Extract dimensions and format them for displaying
                        #-----------------------------------------------------------------------

                        dimensions = ''
                        dim = _def['dim']

                        if dim != 0:
                            dims = str(_def['dimensions'])[1:-1].split(',')

                            if dim == 1:
                                if _def['data_type'] == 'DWORD':
                                    dimensions = '[' + str(int(dims[0]) * 32) + ']'
                                else:
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

                        if btnConnect['state'] == 'normal':
                            start_connection()
                else:
                    lbTags.insert(1, 'No Tags Retrieved')

                commGT.close()
                commGT = None

            # save tags to a file inside the application folder
            if checkVarSaveTags.get() == 1:
                with open('tags_list.txt', 'w') as f:
                    for i in range(0, lbTags.size()):
                        f.write(str(lbTags.get(i)) + '\n')

        except Exception as e:
            lbPLCMessage.delete(0, 'end')
            lbPLCError.insert(1, e)
            lbTags.insert(1, 'No Tags Retrieved')
            if not commGT is None:
                commGT.close()
                commGT = None
    except Exception as e:
        if app_closing:
            pass
        else:
            print(str(e))

def struct_members(it, i, j):
    try:
        # internal tags keys
        keys = it.keys()

        for key in keys:
            tag = it[key]

            if tag['tag_type'] == 'struct':
                structureDataType = tag['data_type']['name']
                structureSize = tag['data_type']['template']['structure_size']

                if tag['array'] > 0:
                    add_Tag(j, '- ' + key + '[' + str(tag['array']) + ']' + ' (' + structureDataType + ')' + ' (' + str(structureSize) + ' bytes)')
                else:
                    add_Tag(j, '- ' + key + ' (' + structureDataType + ')' + ' (offset ' + str(tag['offset']) + ')' + ' (' + str(structureSize) + ' bytes)')

                currentTagLine.set(i + 1)

                i = struct_members(tag['data_type']['internal_tags'], currentTagLine.get() + 1, j + 1)
            else:
                if tag['data_type'] == 'BOOL':
                    add_Tag(j, '- ' + key + ' (offset ' + str(tag['offset']) + ')' + ' (bit ' + str(tag['bit']) + ')' + ' (' + tag['data_type'] + ')')
                else:
                    if tag['array'] > 0:
                        if tag['data_type'] == 'DWORD':
                            add_Tag(j, '- ' + key + '[' + str(tag['array'] * 32) + ']' + ' (offset ' + str(tag['offset']) + ')' + ' (' + tag['data_type'] + ')')
                        else:
                            add_Tag(j, '- ' + key + '[' + str(tag['array']) + ']' + ' (offset ' + str(tag['offset']) + ')' + ' (' + tag['data_type'] + ')')
                    else:
                        add_Tag(j, '- ' + key + ' (offset ' + str(tag['offset']) + ')' + ' (' + tag['data_type'] + ')')

                currentTagLine.set(currentTagLine.get() + 1)

        return currentTagLine.get()
    except Exception as e:
        if app_closing:
            pass
        else:
            print(str(e))

def add_Tag(j, string):
    try:
        #insert multiple of 2 spaces, depending on the structure depth, to simulate the tree appearance
        k = 2 * j + len(string)
        lbTags.insert(currentTagLine.get(), (' ' * k + string)[-k:])
    except Exception as e:
        if app_closing:
            pass
        else:
            print(str(e))

def comm_check():
    global comm
    global connected
    global path

    try:
        pth = selectedPath.get()

        if not comm is None:
            comm.close()
            comm = None

        if (path != pth):
            path = pth

        try:
            if driverSelection.get() == 'LogixDriver':
                comm = LogixDriver(path)
                comm.open()

                lbPLCMessage.insert(1, 'Connected: ' + comm.info['product_name'] + ' , ' + comm.info['keyswitch'])
            else:
                comm = SLCDriver(path)
                comm.open()
                info = comm.list_identity(path)
                lbPLCMessage.insert(1, 'Connected to: ' + info['ip_address'] + '  [' + info['product_name'] + ']')

            connected = True
            lbPLCError.delete(0, 'end')
            btnConnect['state'] = 'disabled'
            if btnStop['state'] == 'disabled':
                btnStart['state'] = 'normal'
                btnStart['bg'] = 'lime'
        except Exception as e:
            connected = False
            lbPLCMessage.delete(0, 'end')
            lbPLCError.insert(1, e)
            btnConnect['state'] = 'normal'
            btnStart['state'] = 'disabled'
            btnStart['bg'] = 'lightgrey'
    except Exception as e:
        if app_closing:
            pass
        else:
            print(str(e))

def startUpdateValue():
    global updateRunning
    global previousLogHeader
    global chbLogTagValues
    global headerAdded

    '''
    Call ourself to update the screen
    '''

    try:
        if (path != selectedPath.get()):
            start_connection()
        else:
            displayTag = (selectedTag.get()).replace(' ', '')

            if displayTag != '':
                logHeader = ''
                logValues = ''

                myTag = []

                if ';' in displayTag:
                    tags = displayTag.split(';')
                    for tag in tags:
                        if not str(tag) == '':
                            myTag.append(str(tag))
                            logHeader += tag + ', '
                else:
                    myTag.append(displayTag)
                    logHeader = displayTag + ', '

                if not updateRunning:
                    updateRunning = True
                else:
                    try:
                        if btnStart['state'] == 'normal':
                            btnStart['state'] = 'disabled'
                            btnStart['bg'] = 'lightgrey'
                            btnStop['state'] = 'normal'
                            btnStop['bg'] = 'lime'
                            tbPath['state'] = 'disabled'
                            tbTag['state'] = 'disabled'
                            popup_menu_drivers['state'] = 'disabled'
                            chbLogTagValues['state'] = 'disabled'

                        results = comm.read(*myTag)

                        allValues = ''

                        if len(myTag) == 1:
                            if myTag[0].endswith('}') and '{' in myTag[0]:
                                tempList = []

                                for val in results.value:
                                    if isinstance(val, str):
                                        tempList.append(str(val).strip('\x00'))
                                    else:
                                        if (checkVarBoolDisplay.get() == 1) and (val == True or val == False):
                                            tempList.append(1 if val else 0)
                                        else:
                                            tempList.append(val)

                                tagValue['text'] = str(tempList)

                                if checkVarLogTagValues.get() == 1:
                                    logValues = str(tempList).replace(',', ';') + ', '
                            else:
                                if isinstance(results.value, str):
                                    tagValue['text'] = str(results.value).strip('\x00')
                                else:
                                    if (checkVarBoolDisplay.get() == 1) and (results.value == True or results.value == False):
                                        tagValue['text'] = '1' if results.value else '0'
                                    else:
                                        tagValue['text'] = str(results.value)

                                if checkVarLogTagValues.get() == 1:
                                    logValues = tagValue['text'] + ', '
                        else:
                            for tag in results:
                                if isinstance(tag.value, list):
                                    tempList = []

                                    for val in tag.value:
                                        if isinstance(val, str):
                                            tempList.append(str(val).strip('\x00'))
                                        else:
                                            if (checkVarBoolDisplay.get() == 1) and (val == True or val == False):
                                                tempList.append(1 if val else 0)
                                            else:
                                                tempList.append(val)

                                    allValues += str(tempList) + '\n'

                                    if checkVarLogTagValues.get() == 1:
                                        logValues += str(tempList).replace(',', ';') + ', '
                                else:
                                    if isinstance(tag.value, str):
                                        allValues += str(tag.value).strip('\x00') + '\n'

                                        if checkVarLogTagValues.get() == 1:
                                            logValues += str(tag.value).strip('\x00') + ', '
                                    else:
                                        if (checkVarBoolDisplay.get() == 1) and (tag.value == True or tag.value == False):
                                            allValues += '1' if tag.value else '0' + '\n'
                                        else:
                                            allValues += str(tag.value) + '\n'

                                        if checkVarLogTagValues.get() == 1:
                                            logValues += str(tag.value) + ', '

                            tagValue['text'] = allValues[:-1]

                        # log tags values
                        if checkVarLogTagValues.get() == 1:
                            if not os.path.exists('tag_values_log.txt') or previousLogHeader != logHeader:
                                if previousLogHeader != logHeader:
                                    previousLogHeader = logHeader
                                    logValues = ''

                                headerAdded = False

                            if headerAdded:
                                with open('tag_values_log.txt', 'a') as log_file:
                                    strValue = str(datetime.datetime.now()).replace(' ', '/') + ', ' + logValues[:-2] + '\n'
                                    log_file.write(strValue)
                            else:
                                with open('tag_values_log.txt', 'w') as log_file:
                                    # add header with 'Date / Time' and all the tags being read
                                    header = 'Date / Time, ' + logHeader[:-2] + '\n'
                                    log_file.write(header)
                                    headerAdded = True

                        root.after(500, startUpdateValue)
                    except Exception as e:
                        lbPLCMessage.delete(0, 'end')
                        lbPLCError.insert(1, e)
                        tagValue['text'] = '~'
                        connected = False
                        start_connection()
                        root.after(2000, startUpdateValue)
    except:
        pass

def stop_update():
    global updateRunning

    try:
        if updateRunning:
            updateRunning = False
            tagValue['text'] = '~'
            btnStart['state'] = 'normal'
            btnStart['bg'] = 'lime'
            btnStop['state'] = 'disabled'
            btnStop['bg'] = 'lightgrey'
            tbPath['state'] = 'normal'
            tbTag['state'] = 'normal'
            popup_menu_drivers['state'] = 'normal'
            chbLogTagValues['state'] = 'normal'
    except:
        pass

def save_tags_list(event, chbSaveTags):
    if checkVarSaveTags.get() == 0:
        popup_menu_save_tags_list.post(event.x_root, event.y_root)
        # Windows users can also click outside of the popup so set the checkbox state here
        if platform.system() == 'Windows':
            chbSaveTags.select()

def set_checkbox_state():
    chbSaveTags.select()

def tag_menu(event, tbTag):
    try:
        old_clip = root.clipboard_get()
    except:
        old_clip = None

    if (not old_clip is None) and (type(old_clip) is str) and tbTag['state'] == 'normal':
        tbTag.select_range(0, 'end')
        popup_menu_tbTag.post(event.x_root, event.y_root)

def tag_paste():
    # user clicked the "Paste" option so paste the tag from the clipboard
    selectedTag.set(root.clipboard_get())
    tbTag.select_range(0, 'end')
    tbTag.icursor('end')

def ip_copy():
    if (lbDevices.get(ANCHOR)).split(' ')[0] == 'IP':
        root.clipboard_clear()
        listboxSelectedPath = (lbDevices.get(ANCHOR)).split(' ')[2]
        root.clipboard_append(listboxSelectedPath)

def path_menu(event, tbPath):
    try:
        old_clip = root.clipboard_get()
    except:
        old_clip = None

    if (not old_clip is None) and (type(old_clip) is str) and tbPath['state'] == 'normal':
        tbPath.select_range(0, 'end')
        popup_menu_tbPath.post(event.x_root, event.y_root)

def path_paste():
    # user clicked the "Paste" option so paste the clipboard contents
    selectedPath.set(root.clipboard_get())
    tbPath.select_range(0, 'end')
    tbPath.icursor('end')

if __name__=='__main__':
    main()
