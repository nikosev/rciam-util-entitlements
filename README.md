# rciam-util-entitlements
Utilities for RCIAM entitlements.  
This script synchronizes the entitlement table of MITREiD and COmanage Registry.

## Installation
This script has developed and tested using Python version 3.4.2.
Here are the instractions to install and use virtualenv with Python 3:
1. Install *Python 3* and *pip3*
    ```
    apt-get update
    apt-get install --no-install-recommends python3-dev python3-pip
    ```
2. Install *virtualenv*
    ```
    pip3 install virtualenv
    ```
3. Create *virtualenv*
    ```
    mkvirtualenv -p /usr/bin/python3 <path>
    ```
4. Activate *virtualenv*
    ```
    source <path>/bin/activate
    ```
    Deactivate *virtualenv*
    ```
    deactivate
    ```
5. Install modules
    ```
    pip3 install psycopg2-binary requests
    ```
6. Run script
    ```
    python <path to>/syncEntitlements.py
    ```
