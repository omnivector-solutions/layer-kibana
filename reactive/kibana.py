#!/usr/bin/env python3
# pylint: disable=c0111,c0103,c0301
import subprocess as sp
from time import sleep


from charms.reactive import (
    clear_flag,
    endpoint_from_flag,
    register_trigger,
    set_flag,
    when,
    when_any,
    when_not,
)
from charmhelpers.core.hookenv import (
    application_version_set,
    # config,
    network_get,
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
    kibana_version,
    render_file,
    KIBANA_YML_PATH,
)


PRIVATE_IP = network_get('http')['ingress-addresses'][0]


kv = unitdata.kv()


register_trigger(when='kibana.version.set',
                 set_flag='kibana.init.complete')

# register_trigger(when='elasticsearch.grafana.available',
#                  clear_flag='elasticsearch.grafana.unavailable')

# register_trigger(when='elasticsearch.grafana.unavailable',
#                  clear_flag='elasticsearch.grafana.available')


# Utility Handlers
@when('kibana.needs.restart')
def restart_kibana():
    """Restart kibana
    """
    service_restart('kibana')
    clear_flag('kibana.needs.restart')


@when_any('apt.installed.kibana',
          'deb.installed.kibana')
@when_not('kibana.yml.available')
def render_kibana_conifg():
    """Render /etc/kibana/kibana.yml
    """
    render_file(
        'kibana.yml.j2', KIBANA_YML_PATH, {})
    set_flag('kibana.yml.available')


@when_not('kibana.init.running')
@when('kibana.yml.available',
      'elasticsearch.client.available')
def ensure_kibana_started():
    """Ensure kibana is started
    """

    sp.call("systemctl daemon-reload".split())
    sp.call("systemctl enable kibana.service".split())

    # If kibana isn't running start it
    if not service_running('kibana'):
        service_start('kibana')
    # If elasticsearch is running restart it
    else:
        service_restart('kibana')

    # Wait 100 seconds for kibana to restart, then break out of the loop
    # and blocked wil be set below
    cnt = 0
    while not service_running('kibana') and cnt < 100:
        status_set('waiting', 'Waiting for Kibana to start')
        sleep(1)
        cnt += 1

    if service_running('kibana'):
        set_flag('kibana.init.running')
        status_set('active', 'Kibana running')
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
    status_set('active', 'Kibana running - init complete')
    set_flag('kibana.version.set')


# Kibana initialization should be complete at this point
# The following ops are all post init phase
@when('nginx.available',
      'kibana.init.complete')
@when_not('kibana.nginx.conf.available')
def render_kibana_nginx_conf():
    status_set('maintenance', 'Configuring NGNX')
    # render_file(
    #    'users.j2',
    #    '/etc/nginx/htpasswd.users',
    #    {'password': config('kibana-password')})

    configure_site('kibana-front-end', 'nginx.conf.j2')
    status_set('active', 'NGINX Configured')

    set_flag('kibana.nginx.conf.available')


@when('kibana.nginx.conf.available',
      'endpoint.http.joined')
@when_not('http.relation.data.available')
def provide_http_relation_data():
    endpoint = endpoint_from_flag('endpoint.http.joined')
    status_set('maintenance', "Configuring http endpoint")
    endpoint.configure(port=80)
    status_set('active', "Http relation joined")
    set_flag('http.relation.data.available')
