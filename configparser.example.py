# Configuration for MITREiD OIDC
oidc_config = {
    "dbname" : "mydbname",
    "user" : "myuser",
    "host" : "myhost",
    "password" : "mypassword"
}

# Configuration for COManage 
# connect_comanage_str = "dbname='registryrc' user='postgres' host='83.212.103.124' password='nikos123'"
comanage_config = {
    "dbname" : "mydbname2",
    "user" : "myuser2",
    "host" : "myhost2",
    "password" : "mypassword2"
}

# Configuration for GOCDB
gocdb_config = {
    "api_base_path" : "http://localhost/",
    "cert_path" : "mycertpath",
    "key_path" : "mykeypath",
    "trusted_ca_path" : "mytrustedcapath"
}

vo_entitlement = {
    "urn_namespace_old" : "urn:mace:<organazation>:<department>",
    "urn_namespace" : "urn:mace:<organazation>",
    "urn_group_authority" : "<department>"
}

gocdb_entitlement = {
    "role_urn_namespace" : "urn:mace:<organazation>:<department>",
    "role_scope" : "<organazation>"
}
