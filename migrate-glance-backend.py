#!/usr/bin/env python
#
# Copyright 2015 iWeb Technologies Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import argparse
import logging
import sys
import os
import io
import common

from openstackclient.common import clientmanager
from openstackclient.common import utils
from glanceclient.common import utils as gc_utils

from os_client_config import config as cloud_config

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)

# Where temporary copies of images will be downloaded to
TMPDIR = '/tmp/'


def migrate_image(glanceclient, image_id):
    """
    Download an image and create a new one with the same properties
    (except UUID)
    Delete the original image at the orginal location
    Update the location of the original image to the location of the new image
    Protect both images to prevent them from being deleted and orphaned
    Prior to running this, the Glance backend should already be changed to the
    new one.
    """
    # Retrieve image object
    LOG.info("Retrieving properties for {0}".format(image_id))
    image = utils.find_resource(
        glanceclient.images,
        image_id,
    )
    image_description = "{0} ({1})".format(image.name, image.id)

    # Download the image locally
    file_path = TMPDIR + image.id
    LOG.info("Downloading {0} to {1}".format(image_description, file_path))
    data = glanceclient.images.data(image.id)
    gc_utils.save_image(data, file_path)

    # Save the properties we want to keep from the current image
    kwargs = {}
    # Note: Owner may not be preserved with Glance API v2 because of
    # https://bugs.launchpad.net/glance/+bug/1420008
    # Otherwise, we'd put "owner" in copy_attrs
    # properties is the custom properties that you have for your images
    properties = ['architecture', 'build_version']
    copy_attrs = ['name', 'container_format', 'disk_format', 'min_disk',
                  'min_ram', 'visibility'] + properties
    for attr in copy_attrs:
        if hasattr(image, attr):
            val = getattr(image, attr, None)
            if val:
                kwargs[attr] = val

    # Create a new image with the same properties except the UUID
    try:
        LOG.info("Creating new image based on {0}".format(image_description))
        new_image = glanceclient.images.create(**kwargs)
        data = io.open(file_path, "rb")
        glanceclient.images.upload(new_image.id, data, None)
    finally:
        # Clean up open file
        if hasattr(data, 'close'):
            data.close()

    # Fetch all properties of the new image
    new_image = utils.find_resource(
        glanceclient.images,
        new_image.id,
    )
    new_image_description = "{0} ({1})".format(new_image.name, new_image.id)
    LOG.info("New image created: {0}".format(new_image_description))

    # Delete the file based location for the original image and
    # set the location to be the new one
    LOG.info("Deleting original image location and setting the new one...")
    glanceclient.images.delete_locations(image.id,
                                         set([image.locations[0]["url"]]))
    glanceclient.images.add_location(image.id,
                                     new_image.locations[0]["url"], {})

    # Protect both images to prevent them from being deleted/orphaned
    LOG.info("Protecting both images to prevent them from being deleted...")
    kwargs = {}
    kwargs['protected'] = True
    glanceclient.images.update(image.id, **kwargs)
    glanceclient.images.update(new_image.id, **kwargs)

    # Delete the local temporary original image file once everything is done
    LOG.info("Deleting temporary image file at {0}".format(file_path))
    os.remove(file_path)

    return


def main(opts):
    """
    Instanciate and authenticate the Openstack clients
    Fetch a list of images and migrate them
    """

    # Configuration file handling
    cc = cloud_config.OpenStackConfig()
    LOG.debug("Defaults: {0}".format(cc.defaults))

    cloud = cc.get_one_cloud(cloud=opts.cloud, argparse=opts)
    LOG.debug("Cloud configuration: {0}".format(cloud.config))

    # Loop through extensions to get API versions
    api_version = {}
    for mod in clientmanager.PLUGIN_MODULES:
        version_opt = getattr(opts, mod.API_VERSION_OPTION, None)
        if version_opt:
            api = mod.API_NAME
            api_version[api] = version_opt

    # Set up certificate verification and CA bundle
    if opts.cacert:
        verify = opts.cacert
    else:
        verify = not opts.insecure

    # Collect the authentication and configuration options together and give
    # them to ClientManager to wrap everything into place..
    client_manager = clientmanager.ClientManager(
        cli_options=cloud,
        verify=verify,
        api_version=api_version,
    )

    # Instanciate glanceclient and retrieve the list of images
    glanceclient = client_manager.image

    marker = None
    kwargs = {}
    image_list = []
    while True:
        page = glanceclient.api.image_list(marker=marker, **kwargs)
        if not page:
            break
        image_list.extend(page)
        # Set the marker to the id of the last item we received
        marker = page[-1]['id']

    LOG.info("Found {0} image(s).".format(str(len(image_list))))
    for image in image_list:
        migrate_image(glanceclient, image['id'])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Glance image backend migration'
    )
    opts = common.base_parser(
        clientmanager.build_plugin_option_parser(parser),
    ).parse_args()

    common.configure_logging(opts)
    sys.exit(common.main(opts, main))
