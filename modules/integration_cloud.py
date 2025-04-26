import oci
from modules.utils import *

SERVICE_NAME = 'Integration Cloud'

def stop_integration_cloud(config, signer, compartments, filter_tz, filter_mode):
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
            
        resources = _get_resources(config, signer, compartment.id)
        for resource in resources:
            action_required = False
            if (resource.lifecycle_state == 'ACTIVE'):
                if IS_FIRST_FRIDAY:
                    action_required = True
                                    
                if ('Control' in resource.defined_tags) and ('Nightly-Stop' in resource.defined_tags['Control']):     
                    if (resource.defined_tags['Control']['Nightly-Stop'].upper() != 'FALSE'):    
                        action_required = True
                else:
                    action_required = True

            if action_required:
                print("    * {} ({}) in {}".format(resource.display_name, resource.lifecycle_state, compartment.name))
                resource.compartment_name = compartment.name
                resource.service_name = SERVICE_NAME
                resource.region = config["region"]
                target_resources.append(resource)
            else:
                if ('Control' in resource.defined_tags) and ('Nightly-Stop' in resource.defined_tags['Control']):  
                    print("      {} ({}) in {} - {}:{}".format(resource.display_name, resource.lifecycle_state, compartment.name, 'Control.Nightly-Stop', resource.defined_tags['Control']['Nightly-Stop'].upper()))
                else:
                    print("      {} ({}) in {}".format(resource.display_name, resource.lifecycle_state, compartment.name))

    print('\nStopping * marked {}...'.format(SERVICE_NAME))
    for resource in target_resources:
        try:
            response, request_date = _perform_resource_action(config, signer, resource.id, 'STOP')
        except oci.exceptions.ServiceError as e:
            print("---------> error. status: {}".format(e))
            pass
        else:
            if response.lifecycle_state == 'UPDATING':
                print("    stop requested: {} ({}) in {}".format(response.display_name, response.lifecycle_state, resource.compartment_name))
            else:
                print("---------> error stopping {} ({})".format(response.display_name, response.lifecycle_state))

    print("\nAll {} stopped!".format(SERVICE_NAME))

    return target_resources    

def change_integration_cloud_license(config, signer, compartments):
    target_resources = []

    print("Listing all {}... (* is marked for change)".format(SERVICE_NAME))

    for compartment in compartments:
        print("  compartment: {}".format(compartment.name))
        resources = _get_resources(config, signer, compartment.id)
        for resource in resources:

            action_required = False
            if ('Control' in resource.defined_tags) and ('BYOL' in resource.defined_tags['Control']):     
                if (resource.defined_tags['Control']['BYOL'].upper() != 'FALSE'):    
                    action_required = True
            else:
                action_required = True

            if action_required:
                if (resource.is_byol == False):
                    print("    * {} (BYOL:{}) in {}".format(resource.display_name, resource.is_byol, compartment.name))
                    resource.compartment_name = compartment.name
                    resource.region = config["region"]
                    target_resources.append(resource)
                else:
                    print("      {} (BYOL:{}) in {}".format(resource.display_name, resource.is_byol, compartment.name))
            else:
                if ('Control' in resource.defined_tags) and ('BYOL' in resource.defined_tags['Control']):   
                    print("      {} (BYOL:{}) in {} - {}:{}".format(resource.display_name, resource.is_byol, compartment.name, 'Control.BYOL', resource.defined_tags['Control']['BYOL'].upper()))
                else:
                    print("      {} (BYOL:{}) in {}".format(resource.display_name, resource.is_byol, compartment.name))

    print("\nChanging * marked {}'s lisence model...".format(SERVICE_NAME))
    for resource in target_resources:
        try:
            response, request_date = _change_license_model(config, signer, resource.id, True)
        except oci.exceptions.ServiceError as e:
            print("---------> error. status: {}".format(e))
            pass
        else:
            if response.lifecycle_state == 'UPDATING':
                print("    change requested: {} ({})".format(response.display_name, response.lifecycle_state))
                send_license_type_change_notification(config, signer, SERVICE_NAME, resource, request_date, 'BYOL')                
            else:
                print("---------> error changing {} ({})".format(response.display_name, response.lifecycle_state))

    print("\nAll {} changed!".format(SERVICE_NAME)) 

def _get_resources(config, signer, compartment_id):
    resources = []

    client = oci.integration.IntegrationInstanceClient(config=config, signer=signer)
    summary = oci.pagination.list_call_get_all_results(
        client.list_integration_instances,
        compartment_id
    )

    for inst in summary.data:
        resource = client.get_integration_instance(inst.id)

        resources.append(resource.data)

    return resources    

def _perform_resource_action(config, signer, resource_id, action):
    client = oci.integration.IntegrationInstanceClient(config=config, signer=signer)

    if (action == 'STOP'):      
        stop_response = client.stop_integration_instance(
            resource_id
        )

        response = client.get_integration_instance(
            resource_id
        )

    return response.data, stop_response.headers['Date']

def _change_license_model(config, signer, resource_id, is_byol):
    client = oci.integration.IntegrationInstanceClient(config=config, signer=signer)
    details = oci.integration.models.UpdateIntegrationInstanceDetails(is_byol = is_byol)

    response = client.get_integration_instance(
        resource_id
    )

    if response.data.lifecycle_state == 'INACTIVE':
        return response.data, None
    
    stop_response = client.update_integration_instance(
        resource_id,
        details
    )

    response = client.get_integration_instance(
        resource_id
    )
    
    oci.wait_until(
        client, 
        response, 
        evaluate_response=lambda r: r.data.lifecycle_state == 'ACTIVE'
    )

    return response.data, stop_response.headers['Date']