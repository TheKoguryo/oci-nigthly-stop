import oci
from modules.utils import *

service_name = 'Integration Cloud'

def stop_integration_cloud(config, signer, compartments):
    target_resources = []

    print("Listing all {}... (* is marked for stop)".format(service_name))
    for compartment in compartments:
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
                print("    * {} ({}) in {}".format(resource.display_name, resource.lifecycle_state, compartment.name))
                resource.compartment_name = compartment.name
                resource.region = config["region"]
                target_resources.append(resource)
            else:
                if ('Control' in resource.defined_tags) and ('Nightly-Stop' in resource.defined_tags['Control']):  
                    print("      {} ({}) in {} - {}:{}".format(resource.display_name, resource.lifecycle_state, compartment.name, 'Control.Nightly-Stop', resource.defined_tags['Control']['Nightly-Stop'].upper()))
                else:
                    print("      {} ({}) in {}".format(resource.display_name, resource.lifecycle_state, compartment.name))

    print('\nStopping * marked {}...'.format(service_name))
    for resource in target_resources:
        try:
            response, request_date = _resource_action(config, signer, resource.id, 'STOP')
        except oci.exceptions.ServiceError as e:
            print("---------> error. status: {}".format(e))
            pass
        else:
            if response.lifecycle_state == 'UPDATING':
                print("    stop requested: {} ({}) in {}".format(response.display_name, response.lifecycle_state, resource.compartment_name))
                notify(config, signer, service_name, resource, request_date, 'STOP')
            else:
                print("---------> error stopping {} ({})".format(response.display_name, response.lifecycle_state))

    print("\nAll {} stopped!".format(service_name))

def change_integration_cloud_license(config, signer, compartments):
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

    print("\nChanging * marked {}'s lisence model...".format(service_name))
    for resource in target_resources:
        try:
            response, request_date = _change_license_model(config, signer, resource.id, True)
        except oci.exceptions.ServiceError as e:
            print("---------> error. status: {}".format(e))
            pass
        else:
            if response.lifecycle_state == 'UPDATING':
                print("    change requested: {} ({})".format(response.display_name, response.lifecycle_state))
                notify(config, signer, service_name, resource, request_date, 'BYOL')                
            else:
                print("---------> error changing {} ({})".format(response.display_name, response.lifecycle_state))

    print("\nAll {} changed!".format(service_name))

def _get_resource_list(config, signer, compartment_id):
    resources = []

    object = oci.integration.IntegrationInstanceClient(config=config, signer=signer)
    summary = oci.pagination.list_call_get_all_results(
        object.list_integration_instances,
        compartment_id
    )

    for inst in summary.data:
        resource = object.get_integration_instance(inst.id)

        resources.append(resource.data)

    return resources    

def _resource_action(config, signer, resource_id, action):
    object = oci.integration.IntegrationInstanceClient(config=config, signer=signer)

    if (action == 'STOP'):      
        stop_response = object.stop_integration_instance(
            resource_id
        )

        response = object.get_integration_instance(
            resource_id
        )

    return response.data, stop_response.headers['Date']

def _change_license_model(config, signer, resource_id, is_byol):
    object = oci.integration.IntegrationInstanceClient(config=config, signer=signer)
    details = oci.integration.models.UpdateIntegrationInstanceDetails(is_byol = is_byol)

    response = object.get_integration_instance(
        resource_id
    )

    if response.data.lifecycle_state == 'INACTIVE':
        return response.data
    
    stop_response = object.update_integration_instance(
        resource_id,
        details
    )

    response = object.get_integration_instance(
        resource_id
    )

    return response.data, stop_response.headers['Date']