import oci
from modules.utils import *

service_name = 'Analytics Cloud'

def stop_analytics(config, signer, compartments, filter_tz, filter_mode):
    target_resources = []

    print("Listing all {}... (* is marked for stop)".format(service_name))
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
        resources = _get_resource_list(config, signer, compartment.id)
        for resource in resources:
            go = 0
            if (resource.lifecycle_state == 'ACTIVE'):
                if IS_FIRST_FRIDAY:
                    go = 1
                                    
                if ('Control' in resource.defined_tags) and ('Nightly-Stop' in resource.defined_tags['Control']):     
                    if (resource.defined_tags['Control']['Nightly-Stop'].upper() != 'FALSE'):    
                        go = 1
                else:
                    go = 1

            if (go == 1):
                print("    * {} ({}) in {}".format(resource.name, resource.lifecycle_state, compartment.name))
                resource.compartment_name = compartment.name
                resource.service_name = service_name
                resource.region = config["region"]
                target_resources.append(resource)
            else:
                if ('Control' in resource.defined_tags) and ('Nightly-Stop' in resource.defined_tags['Control']):  
                    print("      {} ({}) in {} - {}:{}".format(resource.name, resource.lifecycle_state, compartment.name, 'Control.Nightly-Stop', resource.defined_tags['Control']['Nightly-Stop'].upper()))
                else:
                    print("      {} ({}) in {}".format(resource.name, resource.lifecycle_state, compartment.name))

    print('\nStopping * marked {}...'.format(service_name))
    for resource in target_resources:
        try:
            response, request_date = _resource_action(config, signer, resource.id, 'STOP')
        except oci.exceptions.ServiceError as e:
            print("---------> error. status: {}".format(e))
            pass
        else:
            if response.lifecycle_state == 'UPDATING':
                print("    stop requested: {} ({}) in {}".format(response.name, response.lifecycle_state, resource.compartment_name))
            else:
                print("---------> error stopping {} ({})".format(response.name, response.lifecycle_state))

    print("\nAll {} stopped!".format(service_name))

    return target_resources    

def change_analytics_license(config, signer, compartments):
    target_resources = []

    print("Listing all {}... (* is marked for change)".format(service_name))

    for compartment in compartments:
        print("  compartment: {}".format(compartment.name))
        resources = _get_resource_list(config, signer, compartment.id)
        for resource in resources:

            go = 0
            if ('Control' in resource.defined_tags) and ('BYOL' in resource.defined_tags['Control']):     
                if (resource.defined_tags['Control']['BYOL'].upper() != 'FALSE'):    
                    go = 1
            else:
                go = 1

            if (go == 1):
                if (resource.license_type == 'LICENSE_INCLUDED'):
                    print("    * {} ({}) in {}".format(resource.name, resource.license_type, compartment.name))
                    resource.compartment_name = compartment.name
                    resource.region = config["region"]                
                    target_resources.append(resource)
                else:
                    print("      {} ({}) in {}".format(resource.name, resource.license_type, compartment.name))
            else:
                if ('Control' in resource.defined_tags) and ('BYOL' in resource.defined_tags['Control']):   
                    print("      {} ({}) in {} - {}:{}".format(resource.name, resource.license_type, compartment.name, 'Control.BYOL', resource.defined_tags['Control']['BYOL'].upper()))
                else:
                    print("      {} ({}) in {}".format(resource.name, resource.license_type, compartment.name))


    print("\nChanging * marked {}'s lisence model...".format(service_name))
    for resource in target_resources:
        try:
            response, request_date = _change_license_model(config, signer, resource.id, 'BRING_YOUR_OWN_LICENSE')
        except oci.exceptions.ServiceError as e:
            print("---------> error. status: {}".format(e))
            pass
        else:
            print("    changed to: {} ({})".format(response.name, response.license_type))
            send_license_type_change_notification(config, signer, service_name, resource, request_date, 'BYOL')


    print("\nAll {} changed!".format(service_name))

def _get_resource_list(config, signer, compartment_id):
    resources = []

    object = oci.analytics.AnalyticsClient(config=config, signer=signer)
    summary = oci.pagination.list_call_get_all_results(
        object.list_analytics_instances,
        compartment_id
    )

    for inst in summary.data:
        resource = object.get_analytics_instance(analytics_instance_id=inst.id)

        resources.append(resource.data)

    return resources

def _resource_action(config, signer, resource_id, action):
    object = oci.analytics.AnalyticsClient(config=config, signer=signer)

    if (action == 'STOP'):
        stop_response = object.stop_analytics_instance(
            resource_id
        )

        response = object.get_analytics_instance(
            resource_id
        )

    return response.data, stop_response.headers['Date']

def _change_license_model(config, signer, resource_id, license_type):
    object = oci.analytics.AnalyticsClient(config=config, signer=signer)
    details = oci.analytics.models.UpdateAnalyticsInstanceDetails(license_type = license_type)
    
    response = object.update_analytics_instance(
        resource_id,
        details
    )
    return response.data, response.headers['Date']