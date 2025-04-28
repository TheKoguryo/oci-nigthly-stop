import oci
from modules.utils import *

SERVICE_NAME = 'Analytics Cloud'

def stop_analytics(config, signer, compartments, filter_tz, filter_mode):
    target_resources = []

    print("Listing all {}... (* is marked for stop)".format(SERVICE_NAME))
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
                    
        print("  compartment: {}".format(compartment.name))
        resources = _get_resources(config, signer, compartment.id)
        for resource in resources:
            action_required = False
            nightly_stop_tag = resource.defined_tags.get('Control', {}).get('Nightly-Stop', '').upper()            
            if (resource.lifecycle_state == 'ACTIVE'):
                if IS_FIRST_FRIDAY:
                    action_required = True
                                    
                if nightly_stop_tag != 'FALSE':   
                    action_required = True

            if action_required:
                print("    * {} ({}) in {}".format(resource.name, resource.lifecycle_state, compartment.name))
                resource.compartment_name = compartment.name
                resource.service_name = SERVICE_NAME
                resource.region = config["region"]
                target_resources.append(resource)
            else:
                if nightly_stop_tag != '':      
                    print("      {} ({}) in {} - {}:{}".format(resource.name, resource.lifecycle_state, compartment.name, 'Control.Nightly-Stop', nightly_stop_tag))
                else:
                    print("      {} ({}) in {}".format(resource.name, resource.lifecycle_state, compartment.name))


    print('\nStopping * marked {}...'.format(SERVICE_NAME))
    for resource in target_resources:
        try:
            response, request_date = _perform_resource_action(config, signer, resource.id, 'STOP')
        except oci.exceptions.ServiceError as e:
            print("---------> error. status: {}".format(e))
            pass
        else:
            if response.lifecycle_state == 'UPDATING':
                print("    stop requested: {} ({}) in {}".format(response.name, response.lifecycle_state, resource.compartment_name))
            else:
                print("---------> error stopping {} ({})".format(response.name, response.lifecycle_state))

    print("\nAll {} stopped!".format(SERVICE_NAME))

    return target_resources    


def change_analytics_license(config, signer, compartments):
    target_resources = []

    print("Listing all {}... (* is marked for change)".format(SERVICE_NAME))

    for compartment in compartments:
        print("  compartment: {}".format(compartment.name))
        resources = _get_resources(config, signer, compartment.id)
        for resource in resources:

            action_required = False
            byol_tag = resource.defined_tags.get('Control', {}).get('BYOL', '').upper()
            if byol_tag != 'FALSE':   
                action_required = True

            if action_required:
                if (resource.license_type == 'LICENSE_INCLUDED'):
                    print("    * {} ({}) in {}".format(resource.name, resource.license_type, compartment.name))
                    resource.compartment_name = compartment.name
                    resource.region = config["region"]                
                    target_resources.append(resource)
                else:
                    print("      {} ({}) in {}".format(resource.name, resource.license_type, compartment.name))
            else:
                if byol_tag != '':       
                    print("      {} ({}) in {} - {}:{}".format(resource.name, resource.license_type, compartment.name, 'Control.BYOL', byol_tag))
                else:
                    print("      {} ({}) in {}".format(resource.name, resource.license_type, compartment.name))


    print("\nChanging * marked {}'s license model...".format(SERVICE_NAME))
    for resource in target_resources:
        try:
            response, request_date = _change_license_model(config, signer, resource.id, 'BRING_YOUR_OWN_LICENSE')
        except oci.exceptions.ServiceError as e:
            print("---------> error. status: {}".format(e))
            pass
        else:
            print("    changed to: {} ({})".format(response.name, response.license_type))
            send_license_type_change_notification(config, signer, SERVICE_NAME, resource, request_date, 'BYOL')


    print("\nAll {} changed!".format(SERVICE_NAME))


def _get_resources(config, signer, compartment_id):
    resources = []

    client = oci.analytics.AnalyticsClient(config=config, signer=signer)
    summary = oci.pagination.list_call_get_all_results(
        client.list_analytics_instances,
        compartment_id
    )

    for inst in summary.data:
        resource = client.get_analytics_instance(analytics_instance_id=inst.id)

        resources.append(resource.data)

    return resources


def _perform_resource_action(config, signer, resource_id, action):
    client = oci.analytics.AnalyticsClient(config=config, signer=signer)

    if (action == 'STOP'):
        stop_response = client.stop_analytics_instance(
            resource_id
        )

        response = client.get_analytics_instance(
            resource_id
        )

    return response.data, stop_response.headers['Date']


def _change_license_model(config, signer, resource_id, license_type):
    client = oci.analytics.AnalyticsClient(config=config, signer=signer)
    details = oci.analytics.models.UpdateAnalyticsInstanceDetails(license_type = license_type)
    
    response = client.update_analytics_instance(
        resource_id,
        details
    )
    return response.data, response.headers['Date']