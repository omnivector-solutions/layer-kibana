# Kibana

## Deployment
To deploy this charm you must couple it with elasticsearch. You can do this in one of two ways; 1) you can relate
this charm to the elasticsearch charm and let juju do the work of letting kibana know were elasticsearch is at, 2) you can
supply the `es-hosts` configuration parameter and the charm will take care of putting the elasticsearch ip address where
it needs to go.


### Manual Elasticsearch Hosts Configuration Deployment
Sometime you have a pre-existing elasticsearch deploy and just want to put kibana in fron of it.

    juju deploy cs:~omnivector/kibana --config es-hosts="10.10.70.1:9200,10.10.70.2:9200,10.10.70.3:9200"

### Automatic Service Discovery Deployment
If both elasticseartch and kibana are deployed via Juju, it may behoove you to take advantage of the 
service discovery engine inherent to juju and relate the two charms after deploying them.

    juju deploy cs:~omnivector/kibana
    juju deploy cs:~omnivector/elasticsearch
    juju relate kibana:elasticsearch elasticsearch:client

### Bundle Deployment
To deploy elasticsearch and kibana with just a single command.

    juju deploy cs:~omnivector/bundle/elk



## Access
Following deployment and the exposing of the kibana application (`juju expose kibana`)
access the kibana dashboard at the ip address of the kibana instance with the username 'admin'.
Find the password in the kibana configuration with:

    juju config kibana kibana-password


# Copyright
* AGPLv3 (see `copyright` file in this directory)

# Contact Information
* James Beedy <jamesbeedy@gmail.com>

### Kibana
- [Kibana website](https://www.elastic.co/products/kibana)
