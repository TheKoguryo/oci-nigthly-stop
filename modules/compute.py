import oci
import socket
import traceback
from modules.utils import *

SERVICE_NAME = 'Compute'

def stop_compute_instances(config, signer, compartments, filter_tz, filter_mode):
    target_resources = []

    print("Listing all {} instances... (* is marked for stop)".format(SERVICE_NAME))
    for compartment in compartments:
        print("  compartment: {}, timezone: {}".format(compartment.name, compartment.timezone))

        if filter_mode == "include":
            if compartment.timezone not in filter_tz:
                print("      (skipped) Target timezones: {}".format(filter_tz))
                continue
        else:
            if compartment.timezone in filter_tz:
                print("      (skipped) Target timezones: all timezone excluding {}".format(filter_tz))
                continue

        resources = _get_resources(config, signer, compartment.id)
        for resource in resources:
            action_required = False
            nightly_stop_tag = resource.defined_tags.get('Control', {}).get('Nightly-Stop', '').upper()
            if (resource.lifecycle_state == 'RUNNING'):
                if IS_FIRST_FRIDAY:
                    action_required = True
                
                if nightly_stop_tag != 'FALSE':   
                    action_required = True

                # Don't stop the VM that run this nightly-stop.
                if resource.display_name == socket.gethostname():
                    action_required = False                    

            if action_required:
                if "-instance-pool-" in str(resource.display_name):
                    continue
                
                print("    * {} ({}) in {}".format(resource.display_name, resource.lifecycle_state, compartment.name))
                resource.compartment_name = compartment.name
                resource.service_name = SERVICE_NAME
                target_resources.append(resource)
            else:
                if nightly_stop_tag != '':      
                    print("      {} ({}) in {} - {}:{}".format(resource.display_name, resource.lifecycle_state, compartment.name, 'Control.Nightly-Stop', nightly_stop_tag))
                else:
                    print("      {} ({}) in {}".format(resource.display_name, resource.lifecycle_state, compartment.name))

    print('\nStopping * marked {} instances...'.format(SERVICE_NAME))
    for resource in target_resources:
        try:
            response, request_date = _perform_resource_action(config, signer, resource.id, 'STOP')
        except oci.exceptions.ServiceError as e:
            print("---------> error. status: {}".format(e))
            traceback.print_exc()
        else:
            if response.lifecycle_state == 'STOPPING':
                print("    stop requested: {} ({}) in {}".format(response.display_name, response.lifecycle_state, resource.compartment_name))
            else:
                print("---------> error stopping {} ({})".format(response.display_name, response.lifecycle_state))

    print("\nAll {} instances stopped!".format(SERVICE_NAME))

    return target_resources


def _get_resources(config, signer, compartment_id):
    client = oci.core.ComputeClient(config=config, signer=signer)
    resources = oci.pagination.list_call_get_all_results(
        client.list_instances,
        compartment_id
    )
    return resources.data


def _perform_resource_action(config, signer, resource_id, action):
    client = oci.core.ComputeClient(config=config, signer=signer)
    response = client.instance_action(
        resource_id,
        action
    )

    return response.data, response.headers['Date']
