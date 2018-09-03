## Copyright 2018 RCIAM
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
## http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.

import psycopg2
import urllib.parse
import requests
import xml.etree.ElementTree as ET
import sys
import configparser as config

def sync(dry_run):
    #
    # Initialize connection to MITREiD Connect Database
    #
    connect_oidc_str = "dbname='" + config.oidc_config['dbname'] + "' user='" + config.oidc_config['user'] + "' host='" + config.oidc_config['host'] + "' password='" + config.oidc_config['password'] + "'"
    try:
        # use our connection values to establish a connection
        connOIDC = psycopg2.connect(connect_oidc_str)
    except Exception as e:
        print("Uh oh, can't connect. Invalid dbname, user or password?")
        print(e)
        sys.stderr.write('Can"'"t connect to MITREiD Database!)

    # create a psycopg2 cursor that can execute queries
    cursorOIDC = connOIDC.cursor()

    #
    # Initialize connection to COManage Registry Database
    #
    connect_comanage_str = "dbname='" + config.comanage_config['dbname'] + "' user='" + config.comanage_config['user'] + "' host='" + config.comanage_config['host'] + "' password='" + config.comanage_config['password'] + "'"
    try:
        # use our connection values to establish a connection
        connCO = psycopg2.connect(connect_comanage_str)
    except Exception as e:
        print("Uh oh, can't connect. Invalid dbname, user or password?")
        print(e)
        sys.stderr.write('Can"'"t connect to COManage Database!)

    # create a psycopg2 cursor that can execute queries
    cursorCO = connCO.cursor()

    #
    # Select MITREiD users
    #
    try:
        cursorOIDC.execute("""SELECT id, sub FROM user_info;""")
    except Exception as e:
        print("Uh oh, can't execute query.")
        print(e)
        sys.stderr.write('Can"'"t execute "'"Select MITREiD users"'" query!)

    userInfo = [{'user_id': row[0], 'sub': row[1]} for row in cursorOIDC.fetchall()]

    for user in userInfo:
        isGocdbUp = True

        #
        # Select COManage CoPersonId
        #
        try:
            cursorCO.execute("""SELECT person.id
                                FROM cm_identifiers AS id, cm_co_people AS person
                                WHERE id.identifier='%s'
                                AND id.co_person_id=person.id
                                AND id.identifier_id IS NULL AND NOT id.deleted AND id.org_identity_id IS NULL AND id.type='epuid'
                                AND person.co_person_id IS NULL AND NOT person.deleted AND person.status='A';""" % (user['sub']))
        except Exception as e:
            print("Uh oh, can't execute query.")
            print(e)
            sys.stderr.write('Can"'"t execute "'"Select COManage CoPersonId"'" query!)
    
        coPersonId = cursorCO.fetchone()

        if coPersonId[0] == None:
            continue

        #
        # Select COManage Subject DN
        #
        try:
            cursorCO.execute("""SELECT cert.subject
                                FROM cm_co_people AS person
                                INNER JOIN cm_co_org_identity_links AS link
                                ON person.id = link.co_person_id
                                INNER JOIN cm_org_identities AS org
                                ON link.org_identity_id = org.id
                                INNER JOIN cm_certs AS cert
                                ON org.id = cert.org_identity_id
                                WHERE person.id = %s
                                AND NOT link.deleted
                                AND org.org_identity_id IS NULL
                                AND NOT org.deleted
                                AND cert.cert_id IS NULL
                                AND NOT cert.deleted;""" % (coPersonId[0]))
        except Exception as e:
            print("Uh oh, can't execute query.")
            print(e)
            sys.stderr.write('Can"'"t execute "'"Select COManage Subject DN"'" query!)
    
        certs = [row[0] for row in cursorCO.fetchall()]
        certs = list(dict.fromkeys(certs))

        #
        # Select MITREiD entitlements
        #
        current_entitlements = []
        try:
            cursorOIDC.execute("""SELECT edu_person_entitlement FROM user_edu_person_entitlement WHERE user_id=%s;""" % user['user_id'])
        except Exception as e:
            print("Uh oh, can't execute query.")
            print(e)
            sys.stderr.write('Can"'"t execute "'"Select MITREiD entitlements"'" query!)

        current_entitlements = [row[0] for row in cursorOIDC.fetchall()]

        #
        # Select COManage COUs
        #
        try:
            cursorCO.execute("""SELECT DISTINCT (cou.name)
                                FROM cm_cous AS cou
                                INNER JOIN cm_co_person_roles AS role
                                ON cou.id = role.cou_id
                                WHERE role.co_person_id = %s
                                AND role.co_person_role_id IS NULL
                                AND role.affiliation = 'member'
                                AND role.status = 'A'
                                AND NOT role.deleted
                                ORDER BY
                                cou.name DESC;""" % (coPersonId[0]))

        except Exception as e:
            print("Uh oh, can't execute query.")
            print(e)
            sys.stderr.write('Can"'"t execute "'"Select COManage COUs"'" query!)
    
        cous = [row[0] for row in cursorCO.fetchall()]

        #DEBUG LOG
        # print('\nCOUs')
        # for cou in cous:
        #     print(cou)

        #
        # Select COManage VO groups from vo_members table
        #
        try:
            cursorCO.execute("""SELECT vo.vo_id
                                FROM vo_members AS vo
                                WHERE vo.epuid = '%s'
                                AND vo.status = 'Active';""" % (user['sub']))
        except Exception as e:
            print("Uh oh, can't execute query.")
            print(e)
            sys.stderr.write('Can"'"t execute "'"Select COManage VO groups from vo_members table"'" query!)
    
        vos = [row[0] for row in cursorCO.fetchall()]

        # DEBUG LOG
        # print('\nVOs')
        # for vo in vos:
        #     print(vo)
        
        #
        # Select COManage VO groups from voms_members table
        #
        try:
            cursorCO.execute("""SELECT voms.vo_id
                                FROM voms_members AS voms
                                WHERE voms.subject IN (%s)""" % (', '.join("'" + item + "'" for item in certs)))
        except Exception as e:
            print("Uh oh, can't execute query.")
            print(e)
            sys.stderr.write('Can"'"t execute "'"Select COManage VO groups from voms_members table"'" query!)
    
        voms = [row[0] for row in cursorCO.fetchall()]

        # DEBUG LOG
        # print('\nVOMs')
        # for vom in vos:
        #     print(vom)

        #
        # GET GOCDB user_roles
        #
        # DEBUG LOG
        # print('\nGOCDB roles')
        gocdb_roles = []
        for cert in certs:
            try:
                response = requests.get(config.gocdb_config['api_base_path'] + '?method=get_user&dn=' + urllib.parse.quote_plus(cert), cert=(config.gocdb_config['cert_path'], config.gocdb_config['key_path']), verify=config.gocdb_config['trusted_ca_path'])
            except requests.exceptions.ConnectionError as e:
                print("OOPS!! Connection Error. Make sure you are connected to Internet. Technical Details given below.\n")
                print(str(e))
                sys.stderr.write('Can"'"t execute "'"get_user"'" REST API request!)
            # DEBUG LOG
            # print('Status code: %s' % response.status_code)
            if response.status_code == 200:
                # DEBUG LOG
                # print('Response\n' + response.text)
                content = ET.fromstring(response.text)
                gocdb_user = content.find('EGEE_USER')
                if gocdb_user is not None:
                    for value in content.findall('./EGEE_USER/USER_ROLE'):
                        gocdb_role = (config.gocdb_entitlement['role_urn_namespace'] + ":" + urllib.parse.quote_plus(value.find('PRIMARY_KEY').text) + ":" + urllib.parse.quote_plus(value.find('ON_ENTITY').text) + ":" + urllib.parse.quote_plus(value.find('USER_ROLE').text))
                        if config.gocdb_config['role_scope'] is not None:
                            gocdb_role += "@" + config.gocdb_entitlement['role_scope']
                        gocdb_roles.append(gocdb_role)
                        # DEBUG LOG
                        # print(gocdb_role)
            else:
                isGocdbUp = False
                break
        isGocdbUp = False #TODOremove

        voNames = vos + voms

        titles = cous + voNames
        titles = list(dict.fromkeys(titles))

        # DEBUG LOG
        # print('\nTitles')
        # for title in titles:
        #     print(title)

        #
        # Translate COUs to entitlements
        #
        new_entitlements = []
        for title in titles:
            if title:
                if title == "training.egi.eu" or title == "vo.geoss.eu" or title in voNames:
                    roles = ['member','vm_operator']
                else:
                    roles = ['member']
                for role in roles:
                    new_entitlements.append("""%s:%s@%s""" % (config.vo_entitlement['urn_namespace_old'], role, urllib.parse.quote_plus(title)))
                    new_entitlements.append("""%s:group:%s:role=%s#%s""" % (config.vo_entitlement['urn_namespace'], urllib.parse.quote_plus(title), role, config.vo_entitlement['urn_group_authority']))
        
        new_entitlements += gocdb_roles 

        #
        # Common entitlements in MITREiD and COManage
        #
        entitlements_intersection = []
        entitlements_intersection = set(current_entitlements).intersection(new_entitlements)

        if len(set(current_entitlements) - set(entitlements_intersection)) > 0 or len(set(new_entitlements) - set(entitlements_intersection)) > 0:
            print('\n======================================== USER ========================================\n') # DEBUG LOG
            print("sub: %s" % user['sub']) # DEBUG LOG
            print("user_id: %s" % user['user_id']) # DEBUG LOG
            print('CoPersonId: %s' % coPersonId[0]) # DEBUG LOG
            print('Certificates') # DEBUG LOG
            for cert in certs:
                print(cert)
            
            print('\nCurrent Entitlements') # DEBUG LOG
            for current in sorted(current_entitlements):
                print(current)
            
            print('\nNew Entitlements') # DEBUG LOG
            for new in sorted(new_entitlements):
                print(new)
            
            print('\nIntersection of the Entitlements') # DEBUG LOG
            for intersection in sorted(entitlements_intersection):
                print(intersection)

        #
        # Delete outdated(non common) MITREiD entitlements
        #
        delete_entitlements = set()
        if isGocdbUp is False:
            tmp = set()
            for d_title in delete_entitlements:
                if not config.gocdb_entitlement['role_urn_namespace'] in d_title:
                    tmp.add(d_title)
            delete_entitlements = tmp
        if len(set(current_entitlements) - set(entitlements_intersection)) > 0:
            delete_entitlements = set(current_entitlements) - set(entitlements_intersection)
            print('\nDelete') # DEBUG LOG
            try:
                cursorOIDC.execute("""DELETE FROM user_edu_person_entitlement
                                    WHERE user_id=%s AND edu_person_entitlement IN (%s);""" % (user['user_id'], ', '.join("'" + item + "'" for item in delete_entitlements)))
                print("""DELETE FROM user_edu_person_entitlementWHERE user_id=%s AND edu_person_entitlement IN (%s);""" % (user['user_id'], ', '.join("'" + item + "'" for item in delete_entitlements)))
            except Exception as e:
                print("Uh oh, can't execute query.")
                print(e)
                sys.stderr.write('Can"'"t execute "'"Delete entitlements"'" query!)

        #
        # Insert new(non common) COManage entitlements
        #
        insert_entitlements = []
        if len(set(new_entitlements) - set(entitlements_intersection)) > 0:
            insert_entitlements = set(new_entitlements) - set(entitlements_intersection)
            print('\nInsert') # DEBUG LOG
            for insert in insert_entitlements:
                try:
                    cursorOIDC.execute("""INSERT INTO user_edu_person_entitlement (user_id, edu_person_entitlement)
                                        VALUES (%s, '%s');""" % (user['user_id'], insert))
                    print("""INSERT INTO user_edu_person_entitlement (user_id, edu_person_entitlement) VALUES (%s, '%s');""" % (user['user_id'], insert))
                except Exception as e:
                    print("Uh oh, can't execute query.")
                    print(e)
                    sys.stderr.write('Can"'"t execute "'"Insert entitlements"'" query!)
        
        # DEBUG LOG
        try:
            cursorOIDC.execute("""SELECT edu_person_entitlement FROM user_edu_person_entitlement WHERE user_id=%s;""" % user['user_id'])
        except Exception as e:
            print("Uh oh, can't execute query.")
            print(e)
            sys.stderr.write('Can"'"t execute "'"Select updated entilements"'" query!)

        result = [row[0] for row in cursorOIDC.fetchall()]

        if len(delete_entitlements) > 0 or len(insert_entitlements) > 0:
            print('\nEntitlement Results') # DEBUG LOG
            results = sorted(result)
            for res in results:
                print(res)

    if not dry_run:
        connOIDC.commit()

    cursorOIDC.close()
    cursorCO.close()

    connOIDC.close()
    connCO.close()

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "-n":
        dry_run_flag = True
    else:
        dry_run_flag = False
    sync(dry_run_flag)
