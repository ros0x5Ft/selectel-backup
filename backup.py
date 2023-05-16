import json
import os
import requests
from datetime import date
import time
import sys
import syslog

# Settings
OS_AUTH_URL = 'https://api.selvpc.ru/identity/v3/auth/tokens'
USER = os.getenv('OS_USERNAME', '')
PASS = os.getenv('OS_PASSWORD', '')
DOMAIN = os.getenv('OS_PROJECT_DOMAIN_NAME', '')
PROJECT = os.getenv('OS_PROJECT_NAME','')
VM_NAME = os.getenv('OS_VM_NAME', 'Dev')
VM_REGION = os.getenv('OS_REGION_NAME','')
DEBUG_REQUESTS = False

if DEBUG_REQUESTS:
    import logging
    import http.client as http_client
    http_client.HTTPConnection.debuglevel = 1
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True

def errorMsg(message, error):
    print(" ERROR ".center(80, "-"))
    print(error, file=sys.stderr)
    print("~~> {}".format(message))
    syslog.syslog(syslog.LOG_ERR, str(error))
    sys.exit(1)

def getToken():
    headers = {'Content-Type': 'application/json'}
    req = {"auth":
           { "identity":
             { "methods": ["password"],
              "password": {
                  "user": {
                      "name": USER,
                      "domain": {
                          "name": DOMAIN
                          },
                          "password": PASS
                           }
                            }
                            },
                            "scope": {
                                "project": {
                                    "name": PROJECT,
                                    "domain": {
                                        "name": DOMAIN }}}}}

    try:
        r = requests.post(url=OS_AUTH_URL,
                        data=json.dumps(req),
                        headers=headers)
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
         errorMsg("make sure you have valid creds in settings", e)

    except requests.exceptions.RequestException as e:
         errorMsg("Network issue maybe", e)

    return r.headers['x-subject-token']

def getVmUUID(token):
    headers = {'Content-Type': 'application/json',
               'X-Auth-Token': '{}'.format(token)
               }
    try:
         r = requests.get(url='https://api.{}.selvpc.ru/{}'.format(VM_REGION,'compute/v2.1/servers/detail'),
                          headers=headers)
         r.raise_for_status()
    except requests.exceptions.HTTPError as e:
         errorMsg("make sure you have valid creds in settings", e)

    except requests.exceptions.RequestException as e:
         errorMsg("Network issue maybe", e)
    
    for srv in r.json()["servers"]:
         if srv["name"] == VM_NAME:
              return srv["id"]
         else:
              errorMsg("VM {} not found!".format(VM_NAME), None)

     
def startBackup(token, vm_uuid):
    headers = {
                'X-Auth-Token': '{}'.format(token),
                'authority': 'api.{}.selvpc.ru'.format(VM_REGION),
                'content-type': 'application/json;charset=UTF-8',
                'openstack-api-version': 'compute latest',
                'origin': 'https://my.selectel.ru',
                'referer': 'https://my.selectel.ru/'
               }
    req = {'createImage':
           {
               'name':'Backup {}'.format(date.today().strftime("%d.%m.%Y"))
               }
           }
    try:
         r = requests.post(url='https://api.{}.selvpc.ru/{}/{}/action'.format(VM_REGION,'compute/v2.1/servers', vm_uuid),
                    data=json.dumps(req),
                    headers=headers)
         r.raise_for_status()
    except requests.exceptions.HTTPError as e:
         errorMsg("make sure you have valid creds in settings", e)

    except requests.exceptions.RequestException as e:
         errorMsg("Network issue maybe", e)
    image_uuid = r.json()["image_id"]
    
    print(r.content, r.headers, r.status_code, image_uuid)
    
    return image_uuid

def checkBackupState(token, image_uuid):
        headers = {'Content-Type': 'application/json',
               'X-Auth-Token': '{}'.format(token)
               }
        checkProcessed = True
        attempt = 0

        while(checkProcessed):
            time.sleep(60)
            r = requests.get(url='https://api.{}.selvpc.ru/{}/{}'.format(VM_REGION,'image/v2/images', image_uuid),
                         headers=headers)
            attempt = attempt + 1
            status = r.json()["status"]
            msg = 'Wait for image done - Attempt: {} Status: {}'.format(attempt, status)
            print(msg)
            syslog.syslog(syslog.LOG_INFO, msg)
            if status == "active":
                 checkProcessed = False
            elif attempt >= 120:
                 errorMsg("Image creates too long!!!!", None)


def deleteBackup(token, image_uuid):
        headers = {'Content-Type': 'application/json',
               'X-Auth-Token': '{}'.format(token)
               }
        try:
             r = requests.delete(url='https://api.{}.selvpc.ru/{}/{}'.format(VM_REGION,'image/v2/images', image_uuid),
                            headers=headers
                            )
             r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            errorMsg("make sure you have valid creds in settings", e)

        except requests.exceptions.RequestException as e:
            errorMsg("Network issue maybe", e)

def delAllOtherImagesExcludeLast(token, image_uuid):
        headers = {'Content-Type': 'application/json',
               'X-Auth-Token': '{}'.format(token)
               }
        payload = {'limit':'1000000', 'visibility':'private'}
        currentImageUUID = image_uuid
        
        try:
             r = requests.get(url='https://api.{}.selvpc.ru/{}'.format(VM_REGION,'image/v2/images'),
                         headers=headers,
                         params=payload)
             r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            errorMsg("make sure you have valid creds in settings", e)

        except requests.exceptions.RequestException as e:
            errorMsg("Network issue maybe", e)

        for img in r.json()["images"]:
             if img["id"] == currentImageUUID and img["status"] == 'active':
                  for i in r.json()["images"]:
                       if i["id"] != currentImageUUID:
                            deleteBackup(token, i["id"])
        
def main():
    token = getToken()
    vm_uuid = getVmUUID(token)
    image_uuid = startBackup(token, vm_uuid)

    checkBackupState(token, image_uuid)
    delAllOtherImagesExcludeLast(token, image_uuid)

if __name__ == '__main__':
     main()
