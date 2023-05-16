# Selectel backup

Simple script for create image of VM on Selectel OpenStack platform.
Actual when your VM use a "local disk" instead of "network disk"

> Only one last image will be saved, other private images __will be deleted__ by default! 
> See `main()` func for ditails
> __!!! BE CAREFULY !!!__

1. `sudo -i`
2. `apt install python3-requests`
3. `cd /root`
4. `git clone git@github.com:ros0x5Ft/selectel-backup.git`
5. `cd selectel-backup`
6. `touch backup_runner.sh`

```bash

#!/usr/bin/env bash

export OS_USERNAME=
export OS_PASSWORD=''
export OS_PROJECT_DOMAIN_NAME=
export OS_PROJECT_NAME=
export OS_VM_NAME=
export OS_REGION_NAME=

python3 ./backup.py

```
7. `chmod +x backup_runner.sh`
8. `touch /etc/cron.d/backupvm`
```bash
0 20 * * * root /root/selectel-backup/backup_runner.sh  

```