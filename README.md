# migrate-glance-backend
Migrate Glance images from a backend to the other

# Disclaimer
This script makes several assumptions and **is** rough around the edges right now.
It does what I need it to do and it is open-sourced as-is without any guarantee.
Do **NOT** run this in your production before testing it and what it does in a development environment first.

You can not hold anyone or anything accountable if this script breaks something.

# Contributing
Contributions and feedback are welcome ! Feel free to open issues or open pull requests.
The context in which this script was created is explained on my [blog post](https://dmsimard.com/2015/07/18/migrating-glance-images-to-a-different-backend/).

# Current assumptions
- All current images are assumed to be on the original backend (not idempotent, don't run this twice!)
- The Glance default store has been configured for the new backend (unless you want to create new images on the same backend...?)

# What this script does
- Authenticate a session through Openstackclient. The usual [environment variables](http://docs.openstack.org/cli-reference/content/cli_openrc.html) are fine.
- List all current images
- Download each image and create a new one (in the new backend) with the same properties (except [UUID](https://bugs.launchpad.net/glance/+bug/1176978))
- Delete the original image at the orginal location (glance location-delete)
-- This effectively deletes the image at the original location
- Update the location of the original image to the location of the new image
- Protect both images to prevent them from being deleted and orphaned
- Deletes the temporary copy of the downloaded image

The result is that all of your original images are created as new images on the new backend and
the original images' location point to the new image. You end up with two images but one location (file).

# Configuration
Things you might want to modify are the attributes and the properties you want to keep when creating the new images.
These can be configured in the script with the variables `properties` and `copy_attrs` until there's a dynamic way of configuring them.

# Pre-requisites
- Enough disk space to download the images (they are deleted immediately when no longer necessary)
- Glance API v2 enabled
- Glance locations API enabled through configuration (*/etc/glance/glance-api.conf*):

```
show_multiple_locations = True
location_strategy = location_order
```

- Recent-enough version of [python-openstackclient](https://github.com/openstack/python-openstackclient) installed (pip should be good)
-- This script leverages python-openstackclient as a library

# Running the script

```
./python migrate-glance-backend.py --os-image-api-version 2
2015-07-16 14:15:12,202 - INFO - Found 2 image(s).
2015-07-16 14:15:12,202 - INFO - Retrieving properties for 42422cab-27f1-4606-a95f-54c49935c5ca
2015-07-16 14:15:12,366 - INFO - Downloading CentOS 7 (42422cab-27f1-4606-a95f-54c49935c5ca) to /tmp/42422cab-27f1-4606-a95f-54c49935c5ca
2015-07-16 14:15:19,232 - INFO - Creating new image based on CentOS 7 (42422cab-27f1-4606-a95f-54c49935c5ca)
2015-07-16 14:15:45,603 - INFO - New image created: CentOS 7 (9c984ba0-d411-4e0e-bdde-3d4fcbb0fdb3)
2015-07-16 14:15:45,603 - INFO - Deleting original image location and setting the new one...
2015-07-16 14:15:48,770 - INFO - Protecting both images to prevent them from being deleted...
2015-07-16 14:15:49,101 - INFO - Deleting temporary image file at /tmp/42422cab-27f1-4606-a95f-54c49935c5ca    2015-07-16 14:15:49,314 - INFO - Retrieving properties for 363c2724-2fc5-4278-bc21-8218f9a27d06
2015-07-16 14:15:49,349 - INFO - Downloading Ubuntu 14.04 LTS (Trusty Tahr) (363c2724-2fc5-4278-bc21-8218f9a27d06) to /tmp/363c2724-2fc5-4278-bc21-8218f9a27d06
2015-07-16 14:15:55,783 - INFO - Creating new image based on Ubuntu 14.04 LTS (Trusty Tahr) (363c2724-2fc5-4278-bc21-8218f9a27d06)
2015-07-16 14:16:16,312 - INFO - New image created: Ubuntu 14.04 LTS (Trusty Tahr) (fe25d93d-5107-4618-88d4-6e59a9a0a74c)
2015-07-16 14:16:16,312 - INFO - Deleting original image location and setting the new one...
2015-07-16 14:16:19,639 - INFO - Protecting both images to prevent them from being deleted...
2015-07-16 14:16:19,745 - INFO - Deleting temporary image file at /tmp/363c2724-2fc5-4278-bc21-8218f9a27d06
```
