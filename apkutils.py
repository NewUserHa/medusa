#!/usr/bin/env python3
import sys
import readline
import os
import shutil
import frida
import subprocess
import cmd
import pty
from libraries.xmlUtils import *
from libraries.libapkutils import *
from xml.dom import minidom
from xml.etree import ElementTree
from libraries.APKEnum import performRecon
import fileinput

RED   = "\033[1;31m"  
BLUE  = "\033[1;34m"
CYAN  = "\033[1;36m"
GREEN = "\033[0;32m"
RESET = "\033[0;0m"
BOLD    = "\033[;1m"
REVERSE = "\033[;7m"

APK = False
INSTALL = False

#enumerate classes
# js = """Java.perform(function(){Java.enumerateLoadedClasses({"onMatch":function(c){send(c);}});});"""
apktool=os.getcwd()+"/dependencies/apktool.jar"
apksigner = os.getcwd()+"/dependencies/apksigner"
zipallign = os.getcwd()+ "/dependencies/zipalign"
debuggable_apk = os.getcwd()+"/debuggable.apk";
alligned_apk = os.getcwd()+"/debuggable_alligned_signed.apk"
tmp_folder = os.getcwd()+"/tmp"


classes = []
shell = os.environ.get('SHELL', 'sh')

def patch_debuggable(filename):

    text_to_search = "<application" 
    replacement_text ='<application android:debuggable="true" '

    with open(filename) as f:
        if 'android:debuggable="true"' in f.read():
            print(RED+"[!] Application is debuggable !"+RESET)
            return False

    with fileinput.FileInput(filename, inplace=True, backup='.bak') as file:
        for line in file:
            print(line.replace(text_to_search, replacement_text), end='')
    return True


def print_usage():
    print("\nInput file is missing ! \nUsage: \n\t{} path_to_AndroidManifest.xml OR ".format(sys.argv[0]))
    print('\t{} path_to_apk (--patch to set android:debuggable to true) \n\n'.format(sys.argv[0]))

def extract_manifest(file):
    print(GREEN+'[+] Unpacking apk....'+RESET)
    subprocess.run('java -jar '+ apktool +' d {} -o {}'.format(file,tmp_folder), shell=True)

    if len(sys.argv) > 2 and "--patch" in sys.argv[2]:

        print(GREEN+'[+] Setting debuggable flag....'+RESET)
        if patch_debuggable(tmp_folder+'/AndroidManifest.xml'):
            subprocess.run('java -jar '+ apktool +' b tmp -o {}'.format(debuggable_apk), shell=True)
            print(GREEN+'[+] Running Zipallign.....'+RESET)
            subprocess.run(zipallign +' -f 4 {} {}'.format(debuggable_apk,alligned_apk),shell=True)
            print(GREEN+'[+] Signing the apk.....'+RESET)
            subprocess.run(apksigner +' sign --ks ./dependencies/common.jks -ks-key-alias common --ks-pass pass:password --key-pass pass:password  {}'.format(alligned_apk),shell=True)
            print(GREEN+'[+] Removing the unsigned apk.....'+RESET)
            os.remove(debuggable_apk)
            print(GREEN+'[+] Backing up the original...'+RESET)
            shutil.move(file,file+'.back')
            shutil.move(alligned_apk,file)


    subprocess.run('cp tmp/AndroidManifest.xml ./manifest.xml', shell=True)
    performRecon("./tmp")
    shutil.rmtree('./tmp')


# def on_message(message, data):
#     try:
#         if message["type"] == "send":
#             classes.append( message["payload"].split(":")[0].strip())
#     except Exception as e:
#         print('exception: ' + e) 



try:
    if len(sys.argv[1:]) < 1:
        print_usage()
        exit()

    extension = sys.argv[1].split('.')[-1]

    if extension == 'xml':
        xmlDoc = minidom.parse(sys.argv[1])
        filters = get_elements_sub(sys.argv[1])
    elif extension == 'apk':
        APK = True
        print('APK file given as an input')
        extract_manifest(sys.argv[1])
        xmlDoc = minidom.parse('manifest.xml')
        filters = get_elements_sub('manifest.xml')
    else:
        print_usage()
        exit()

except Exception as e:
    print(e)

    

print(GREEN+"""\n-----------Package Details-------------:
Name            :{}
Version code    :{}
Version Name    :{}
Mimimum SDK     :{}
Target  SDK     :{}
App     Name    :{}
Allow   Backup  :{}
---------------------------------------
Debuggable      :{}         

Exported Components:
""".format(get_elements(xmlDoc,'manifest','package')
            ,get_elements(xmlDoc,'manifest','android:versionCode')
            ,get_elements(xmlDoc,'manifest','android:versionName')
            ,get_elements(xmlDoc,'uses-sdk','android:minSdkVersion')
            ,get_elements(xmlDoc,'uses-sdk','android:targetSdkVersion')
            ,get_elements(xmlDoc,'application','android:name')
            ,get_elements(xmlDoc,'application','android:allowBackup')
            ,get_elements(xmlDoc,'application','android:debuggable')))




package = get_elements(xmlDoc,'manifest','package')
permissions = get_element_list(xmlDoc,'uses-permission','android:name')
activities = get_element_list(xmlDoc,'activity','android:name')
services = get_element_list(xmlDoc, 'service','android:name')
receivers = get_element_list(xmlDoc,'receiver','android:name')
providers = get_element_list(xmlDoc,'provider','android:name')
deeplinks = get_deeplinks(xmlDoc,'activity','data','android:scheme')


p = parser()
p.deeplinks = deeplinks
p.package = package
p.permissions = permissions
p.activities = activities
p.services = services
p.receivers = receivers
p.providers = providers
p.filters = filters

p.printDeepLinksMap()

# print(deeplinks)


print(RESET)

pty.openpty()

try:
    print('Availlable devices:\n')
    devices = frida.enumerate_devices()
    i = 0

    for dv in devices:
        print('{}) {}'.format(i,dv))
        i += 1
    j = input('\nEnter the index of device to use:')
    device = devices[int(j)] 
    print('[+] Starting adb as root\n\n')
    os.popen("""adb -s {} root""".format(device.id))

    if APK == True:
        install = input("Do you want to install the apk ? (yes/no)")
        if 'yes' in install:
            subprocess.run('adb -s {} install {}'.format(device.id,sys.argv[1]),shell=True)
            INSTALL = True
except Exception as e:
    print(e)

p.INSTALL = INSTALL
p.device = device
# p.classes = classes
p.cmdloop()

print('\nBye !!')