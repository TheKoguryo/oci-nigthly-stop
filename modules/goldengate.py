import oci
from modules.utils import *

service_name = 'Golden Gate'

def stop_goldengate(config, signer, compartments, filter_tz, filter_mode):
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
            
        resources = _get_resource_list(config, signer, compartment.id)
        for resource in resources:
            go = 0

            if (resource.lifecycle_state == 'ACTIVE' or resource.lifecycle_state == 'NEEDS_ATTENTION'):
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
                resource.service_name = service_name
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
            if response.lifecycle_sub_state == 'STOPPING':
                print("    stop requested: {} ({}) in {}".format(response.display_name, response.lifecycle_sub_state, resource.compartment_name))              
            else:
                print("---------> error stopping {} ({})".format(response.display_name, response.lifecycle_sub_state))

    print("\nAll {} stopped!".format(service_name))

    return target_resources        

def change_goldengate_license(config, signer, compartments):
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
                if (resource.license_model == 'LICENSE_INCLUDED'):
                    print("    * {} ({}) in {}".format(resource.display_name, resource.license_model, compartment.name))
                    resource.compartment_name = compartment.name
                    resource.region = config["region"]                
                    target_resources.append(resource)
                else:
                    print("      {} ({}) in {}".format(resource.display_name, resource.license_model, compartment.name))
            else:
                if ('Control' in resource.defined_tags) and ('BYOL' in resource.defined_tags['Control']):   
                    print("      {} ({}) in {} - {}:{}".format(resource.display_name, resource.license_model, compartment.name, 'Control.BYOL', resource.defined_tags['Control']['BYOL'].upper()))
                else:
                    print("      {} ({}) in {}".format(resource.display_name, resource.license_model, compartment.name))

    print("\nChanging * marked {}'s lisence model...".format(service_name))
    for resource in target_resources:
        try:
            response, request_date = _change_license_model(config, signer, resource.id, 'BRING_YOUR_OWN_LICENSE')
        except oci.exceptions.ServiceError as e:
            print("---------> error. status: {}".format(e))
            pass
        else:
            if response.lifecycle_state == 'UPDATING':
                print("    change requested: {} ({}) - {}".format(response.display_name, response.lifecycle_state, response.license_model))
                send_license_type_change_notification(config, signer, service_name, resource, request_date, 'BYOL')                 
            else:
                print("---------> error changing {} ({}) - {}".format(response.display_name, response.lifecycle_state, response.license_model))

    print("\nAll {} changed!".format(service_name))

def _get_resource_list(config, signer, compartment_id):
    object = oci.golden_gate.GoldenGateClient(config=config, signer=signer)
    resources = oci.pagination.list_call_get_all_results(
        object.list_deployments,
        compartment_id
    )
    return resources.data

def _resource_action(config, signer, resource_id, action):
    object = oci.golden_gate.GoldenGateClient(config=config, signer=signer)
    details = oci.golden_gate.models.StopDeploymentDetails(type="DEFAULT")

    if (action == 'STOP'):
        stop_response = object.stop_deployment(
            resource_id,
            details
        )

        response = object.get_deployment(
            resource_id
        )        

    return response.data, stop_response.headers['Date']

def _change_license_model(config, signer, resource_id, license_model):
    object = oci.golden_gate.GoldenGateClient(config=config, signer=signer)
    details = oci.golden_gate.models.UpdateDeploymentDetails(license_model = license_model)
    
    stop_response = object.update_deployment(
        resource_id,
        details
    )

    response = object.get_deployment(
        resource_id
    )

    return response.data, stop_response.headers['Date']