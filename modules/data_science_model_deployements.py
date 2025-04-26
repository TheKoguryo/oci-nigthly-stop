import oci
from modules.utils import *

SERVICE_NAME = 'Data Science - Model Deployment'

def stop_data_science_model_deployments(config, signer, compartments, filter_tz, filter_mode):
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

                created_by = ""
                try:
                    created_by = str(resource.defined_tags['Oracle-Tags']['CreatedBy'])
                except Exception as ex:
                    print("ERROR: ", ex, flush=True)
                        
                if (created_by.startswith("ocid1.datasciencenotebooksession")):
                    notebook_session_created_by = _get_notebook_session_created_by(config, signer, created_by)
                    resource.defined_tags['Oracle-Tags']['CreatedBy'] = notebook_session_created_by

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

def _get_resources(config, signer, compartment_id):
    client = oci.data_science.DataScienceClient(config=config, signer=signer)
    resources = oci.pagination.list_call_get_all_results(
        client.list_model_deployments,
        compartment_id
    )
    return resources.data

def _perform_resource_action(config, signer, resource_id, action):
    client = oci.data_science.DataScienceClient(config=config, signer=signer)

    if (action == 'STOP'):
        stop_response = client.deactivate_model_deployment(
            resource_id
        )

        response = client.get_model_deployment(
            resource_id
        )  

    return response.data, stop_response.headers['Date']

def _get_notebook_session_created_by(config, signer, notebook_session_id):
    client = oci.data_science.DataScienceClient(config=config, signer=signer)
    get_notebook_session_response = client.get_notebook_session(notebook_session_id)

    created_by = ""
    try:
        created_by = str(get_notebook_session_response.data.defined_tags['Oracle-Tags']['CreatedBy'])
    except Exception as ex:   
        print("ERROR: ", ex, flush=True)
        user_id = get_notebook_session_response.data.created_by

        domain_display_name = "default"

        user_name = get_user_name_by_user_id(config, signer, signer.tenancy_id, domain_display_name, user_id)
        created_by = user_name
    
    return created_by
