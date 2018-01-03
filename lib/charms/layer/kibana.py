#!/usr/bin/env python3
# pylint: disable=c0111,c0103,c0301
import yaml
import os
import shutil
import subprocess as sp

from jinja2 import Environment, FileSystemLoader

from charmhelpers.core.hookenv import (
    charm_dir,
    network_get,
)

from charmhelpers.core.host import (
    service_running,
    service_start,
    service_restart
)


PUBLIC_ADDRESS = network_get('public')['ingress-addresses'][0]

ES_NETWORK_ADDRESS = network_get('cluster')['ingress-addresses'][0]

KIBANA_YML_PATH = os.path.join('/', 'etc', 'kibana', 'kibana.yml')


def start_restart(service):
    if service_running(service):
        service_restart(service)
    else:
        service_start(service)


def kibana_version():
    """Return kibana version
    """
    kibana_version = \
        yaml.safe_load(
            sp.check_output(
                "dpkg -s kibana", shell=True).strip().decode())
    return kibana_version['Version']


def render_file(template, file_path, ctxt):
    # Remove file if exists
    if os.path.exists(file_path):
        os.remove(file_path)

    # Spew rendered template into file
    spew(file_path, load_template(template).render(ctxt))

    # Set perms
    chown(os.path.dirname(file_path), user='root',
          group='root', recursive=True)


def load_template(name, path=None):
    """ load template file
    :param str name: name of template file
    :param str path: alternate location of template location
    """
    if path is None:
        path = os.path.join(charm_dir(), 'templates')
    env = Environment(
        loader=FileSystemLoader(path))
    return env.get_template(name)


def spew(path, data):
    """ Writes data to path
    :param str path: path of file to write to
    :param str data: contents to write
    """
    with open(path, 'w') as f:
        f.write(data)


def chown(path, user, group=None, recursive=False):
    """
    Change user/group ownership of file
    :param path: path of file or directory
    :param str user: new owner username
    :param str group: new owner group name
    :param bool recursive: set files/dirs recursively
    """
    try:
        if not recursive or os.path.isfile(path):
            shutil.chown(path, user, group)
        else:
            for root, dirs, files in os.walk(path):
                shutil.chown(root, user, group)
                for item in dirs:
                    shutil.chown(os.path.join(root, item), user, group)
                for item in files:
                    shutil.chown(os.path.join(root, item), user, group)
    except OSError as e:
        print(e)
