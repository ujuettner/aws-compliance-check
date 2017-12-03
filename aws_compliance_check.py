#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4

"""Checks running EC2 instances for compliance."""

from __future__ import print_function
from optparse import OptionParser
import sys
from pprint import pprint
# pylint: disable=import-error
import boto3


def check_for_all_volumes_encrypted(instance, check_root_volume=True):
    """Checks whether all volumes are encrypted."""
    volumes = [__ec2__.Volume(mapping["Ebs"]["VolumeId"]).encrypted
               for mapping in instance.block_device_mappings
               if (check_root_volume or mapping["DeviceName"] !=
                   instance.root_device_name)]
    return (reduce(lambda a, b: a and b, volumes, True), len(volumes))


def check_for_name_tag_set(instance):
    "Checks whether a name tag is set."""
    return (instance.tags is not None) and \
        len([tags for tags in instance.tags if tags is not None and
             tags["Key"] == "Name"]) > 0


def check_for_public_ip_not_set(instance):
    """Checks whether the instance has no public IP."""
    return instance.public_ip_address is None


def _find_latest_image_id_of_kind(filters):
    if __options__.verbose:
        pprint(filters)
    matching_images = __ec2__.images.filter(Filters=filters)
    image_id_and_creation_date = []
    for image in matching_images:
        image_id_and_creation_date.append({image.creation_date: image.id})
    if __options__.verbose:
        pprint(image_id_and_creation_date)
    return sorted(image_id_and_creation_date)[-1].values()[0]


def check_for_image_up_to_date(instance):
    """Checks whether the instance's AMI is the latest available."""
    image = __ec2__.Image(instance.image_id)
    filters = [
        {"Name": "architecture", "Values": [image.architecture]},
        {"Name": "owner-id", "Values": [image.owner_id]},
        {"Name": "root-device-type", "Values": [image.root_device_type]},
        {"Name": "state", "Values": ["available"]},
        {"Name": "virtualization-type", "Values": [image.virtualization_type]},
    ]
    if image.root_device_type == "ebs":
        filters.append(
            {"Name": "block-device-mapping.volume-type",
             "Values": [image.block_device_mappings[0]["Ebs"]["VolumeType"]]}
        )
    latest_image_id = _find_latest_image_id_of_kind(filters)
    return instance.image_id == latest_image_id


if __name__ == "__main__":
    __parser__ = OptionParser()
    __parser__.add_option("-p", "--profile",
                          dest="aws_profile",
                          default="default",
                          help="Use given AWS profile. Default: default")
    __parser__.add_option("-r", "--region",
                          dest="aws_region",
                          default="us-east-1",
                          help="Use given AWS region. Default: us-east-1")
    __parser__.add_option("-c", "--check-root-volume",
                          action="store_true",
                          dest="check_root_volume",
                          default=False,
                          help="Check root volume encryption. Default: False")
    __parser__.add_option("-v", "--verbose",
                          action="store_true",
                          dest="verbose",
                          default=False,
                          help="Be verbose. Default: False")
    (__options__, __args__) = __parser__.parse_args()

    __session__ = boto3.session.Session(
        profile_name=__options__.aws_profile,
        region_name=__options__.aws_region
    )
    __ec2__ = __session__.resource("ec2")

    __query_result__ = {}
    for ec2_instance in __ec2__.instances.all():
        __query_result__[ec2_instance.id] = {}
        __query_result__[ec2_instance.id]["state"] = ec2_instance.state["Name"]
        __query_result__[ec2_instance.id]["compliant?"] = None
        if __query_result__[ec2_instance.id]["state"] == "running":
            volumes_encrypted, volumes_checked = \
                check_for_all_volumes_encrypted(
                    ec2_instance,
                    __options__.check_root_volume
                )
            __query_result__[ec2_instance.id]["all_volumes_encrypted?"] = \
                volumes_encrypted
            __query_result__[ec2_instance.id]["volumes_checked"] = \
                volumes_checked
            __query_result__[ec2_instance.id]["name_tag_set?"] = \
                check_for_name_tag_set(ec2_instance)
            __query_result__[ec2_instance.id]["no_public_ip?"] = \
                check_for_public_ip_not_set(ec2_instance)
            __query_result__[ec2_instance.id]["ami_up_to_date?"] = \
                check_for_image_up_to_date(ec2_instance)
            __query_result__[ec2_instance.id]["compliant?"] = reduce(
                lambda a, b: a and b,
                [res for res in __query_result__[ec2_instance.id].values()
                 if res is not None and isinstance(res, bool)],
                True
            )

    __overall_result__ = reduce(lambda a, b: a and b,
                                [__query_result__[instance_id]["compliant?"]
                                 for instance_id in __query_result__.keys()
                                 if __query_result__[instance_id]["compliant?"]
                                 is not None],
                                True)
    __perfdata_msg__ = \
        "all_instances={0} running_instances={1} compliant_instances={2}"\
        .format(
            len(__query_result__.keys()),
            len([__query_result__[instance_id]["state"]
                 for instance_id in __query_result__.keys()
                 if __query_result__[instance_id]["state"] == "running"]),
            len([__query_result__[instance_id]["state"]
                 for instance_id in __query_result__.keys()
                 if __query_result__[instance_id]["compliant?"]])
        )

    if __options__.verbose:
        pprint(__query_result__)

    if __overall_result__:
        print("OK | {0}".format(__perfdata_msg__))
        sys.exit(0)
    else:
        print("CRITICAL | {0}".format(__perfdata_msg__))
        sys.exit(2)
