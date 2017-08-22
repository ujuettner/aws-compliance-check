#!/usr/bin/env python
# -*- coding: utf-8 -*-

from optparse import OptionParser
import boto3
import sys



def check_for_all_volumes_encrypted(instance, check_root_volume=True):
    volumes = [ec2.Volume(mapping['Ebs']['VolumeId']).encrypted
               for mapping in instance.block_device_mappings
               if (check_root_volume or mapping['DeviceName'] != instance.root_device_name)]
    return (reduce(lambda a, b: a and b, volumes, True), len(volumes))

def check_for_name_tag_set(instance):
    return (instance.tags is not None) and \
        len([tags for tags in instance.tags if tags is not None and tags['Key'] == 'Name']) > 0

def check_for_public_ip_not_set(instance):
    return instance.public_ip_address is None

def _find_latest_image_id_of_kind(filters):
    matching_images = ec2.images.filter(Filters=filters)
    image_id_and_creation_date = []
    for image in matching_images:
        image_id_and_creation_date.append({image.creation_date: image.id})
    return sorted(image_id_and_creation_date)[-1].values()[0]

def check_for_image_up_to_date(instance):
    image = ec2.Image(instance.image_id)
    filters = [
        {'Name': 'architecture', 'Values': [image.architecture]},
        {'Name': 'owner-id', 'Values': [image.owner_id]},
        {'Name': 'root-device-type', 'Values': [image.root_device_type]},
        {'Name': 'state', 'Values': ['available']},
        {'Name': 'virtualization-type', 'Values': [image.virtualization_type]},
    ]
    if image.root_device_type == 'ebs':
        filters.append(
            {'Name': 'block-device-mapping.volume-type',
             'Values': [image.block_device_mappings[0]['Ebs']['VolumeType']]}
        )
    latest_image_id = _find_latest_image_id_of_kind(filters)
    return instance.image_id == latest_image_id

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-r", "--check-root-volume", action="store_true", dest="check_root_volume", default=False,
                      help="Check root volume for encryption, too. Default: False.")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="Be verbose. Default: False.")
    (options, args) = parser.parse_args()

    ec2 = boto3.resource('ec2')

    query_result = {}
    for instance in ec2.instances.all():
        query_result[instance.id] = {}
        query_result[instance.id]['state'] = instance.state['Name']
        query_result[instance.id]['compliant?'] = None
        if query_result[instance.id]['state'] == 'running':
            volumes_encrypted, volumes_checked = check_for_all_volumes_encrypted(instance, options.check_root_volume)
            query_result[instance.id]['all_checked_volumes_encrypted?'] = volumes_encrypted
            query_result[instance.id]['volumes_checked'] = volumes_checked
            query_result[instance.id]['name_tag_set?'] = check_for_name_tag_set(instance)
            query_result[instance.id]['no_public_ip?'] = check_for_public_ip_not_set(instance)
            query_result[instance.id]['ami_up_to_date?'] = check_for_image_up_to_date(instance)
            query_result[instance.id]['compliant?'] = reduce(lambda a, b: a and b,
                                                             [res for res in query_result[instance.id].values() if res is not None and type(res) == type(True)],
                                                             True)

    overall_result = reduce(lambda a, b: a and b,
                            [query_result[instance_id]['compliant?'] for instance_id in query_result.keys() if query_result[instance_id]['compliant?'] is not None],
                            True)
    perfdata_msg = "all_instances={0} running_instances={1} compliant_instances={2}".format(
                       len(query_result.keys()),
                       len([query_result[instance_id]['state'] for instance_id in query_result.keys() if query_result[instance_id]['state'] == 'running']),
                       len([query_result[instance_id]['state'] for instance_id in query_result.keys() if query_result[instance_id]['compliant?']])
                   )

    if overall_result:
        print("OK | {0}".format(perfdata_msg))
        if options.verbose:
            print(query_result)
        sys.exit(0)
    else:
        print("CRITICAL | {0}".format(perfdata_msg))
        if options.verbose:
            print(query_result)
        sys.exit(2)

# vim:ts=4:sw=4:expandtab
