#!/usr/bin/env python3
# pylint: disable=c0111,c0103,c0301
import os
import subprocess as sp
from time import sleep

from charms.reactive import (
    endpoint_from_flag,
    is_flag_set,
    set_flag,
    when,
    when_any,
    when_not,
)
from charmhelpers.core.hookenv import (
    application_version_set,
    config,
    network_get,
    open_port,
    status_set,
)
from charmhelpers.core.host import (
    service_restart,
    service_running,
    service_start,
)

from charmhelpers.core import unitdata

from charms.layer.nginx import configure_site

from charms.layer.kibana import (
    # pylint: disable=E0611,E0401,C0412
    start_restart,
    kibana_version,
    render_file,
    KIBANA_YML_PATH,
)

import charms.leadership


PRIVATE_IP = network_get('http')['ingress-addresses'][0]
NGINX_LISTEN_HTTP_PORT = 80


kv = unitdata.kv()


def start_restart(service):
    if service_running(service):
        service_restart(service)
    else:
        service_start(service)


def kibana_active_status():
    status_set('active', 'Kibana available')


def render_kibana_yml():
    if is_flag_set('leadership.set.elasticsearch_username') and\
       is_flag_set('leadership.set.elasticsearch_password'):
        elasticsearch_user = \
            charms.leadership.leader_get('elasticsearch_username')
        elasticsearch_pass = \
            charms.leadership.leader_get('elasticsearch_password')
        ctxt = {
            'elasticsearch_username': elasticsearch_user,
            'elasticsearch_password': elasticsearch_pass
        }
    else:
        ctxt = {}
    render_file('kibana.yml.j2', KIBANA_YML_PATH, ctxt)


@when('kibana.init.running',
      'endpoint.kibana-credentials.available',
      'endpoint.kibana-credentials.changed')
@when_not('credentialed.config.rendered')
def render_kibana_conifg_with_creds():
    """Render set kibana-credsentials to leader when available.
    """
    endpoint = endpoint_from_flag('endpoint.kibana-credentials.available')
    elasticsearch_creds = endpoint.list_unit_data()[0]

    charms.leadership.leader_set(
        elasticsearch_username=elasticsearch_creds['username']
    )
    charms.leadership.leader_set(
        elasticsearch_password=elasticsearch_creds['password']
    )
    render_kibana_yml()
    start_restart('kibana')
    set_flag('credentialed.config.rendered')
    kibana_active_status()


@when('elasticsearch.client.available',
      'elastic.base.available')
@when_not('kibana.init.running')
def ensure_kibana_config_and_started():
    """Ensure kibana is configured and started
    """

    render_kibana_yml()

    sp.call("systemctl daemon-reload".split())
    sp.call("systemctl enable kibana.service".split())

    start_restart('kibana')

    # Wait 100 seconds for kibana to restart, then break out of the loop
    # and blocked wil be set below
    cnt = 0
    while not service_running('kibana') and cnt < 100:
        status_set('waiting', 'Waiting for Kibana to start')
        sleep(1)
        cnt += 1

    if service_running('kibana'):
        set_flag('kibana.init.running')
        kibana_active_status()
    else:
        # If kibana wont start, set blocked
        status_set('blocked',
                   "There are problems with kibana, please debug")
        return


@when('kibana.init.running')
@when_not('kibana.version.set')
def get_set_kibana_version():
    """Set kibana version
    """
    application_version_set(kibana_version())
    set_flag('kibana.version.set')


# Kibana initialization should be complete at this point
# The following ops are all post init phase
@when('nginx.available',
      'kibana.version.set')
@when_not('kibana.nginx.conf.available')
def render_kibana_nginx_conf():
    """Render NGINX conf and write out htpasswd file
    """

    status_set('maintenance', 'Configuring NGNX')
    configure_site('kibana-front-end', 'nginx.conf.j2')
    open_port(NGINX_LISTEN_HTTP_PORT)
    set_flag('kibana.nginx.conf.available')
    kibana_active_status()


@when('kibana.nginx.conf.available',
      'endpoint.http.joined')
def provide_http_relation_data():
    endpoint = endpoint_from_flag('endpoint.http.joined')
    status_set('maintenance', "Sending host:port to requirer ...")
    endpoint.configure(
        host=PRIVATE_IP,
        port=NGINX_LISTEN_HTTP_PORT
    )
    kibana_active_status()
