import oci
from modules.utils import *

service_name = 'Data Science - Notebook session'

def stop_data_science_notebook_sessions(config, signer, compartments):
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

def _get_resource_list(config, signer, compartment_id):
    object = oci.data_science.DataScienceClient(config=config, signer=signer)
    resources = oci.pagination.list_call_get_all_results(
        object.list_notebook_sessions,
        compartment_id
    )
    return resources.data

def _resource_action(config, signer, resource_id, action):
    object = oci.data_science.DataScienceClient(config=config, signer=signer)

    if (action == 'STOP'):
        stop_response = object.deactivate_notebook_session(
            resource_id
        )

        response = object.get_notebook_session(
            resource_id
        )  

    return response.data, stop_response.headers['Date']
