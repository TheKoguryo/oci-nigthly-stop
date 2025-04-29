import oci
from modules.utils import *

SERVICE_NAME = 'Golden Gate'

def stop_goldengate(config, signer, compartments, filter_tz, filter_mode):
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
            nightly_stop_tag = resource.defined_tags.get('Control', {}).get('Nightly-Stop', '').upper()               

            if (resource.lifecycle_state == 'ACTIVE' or resource.lifecycle_state == 'NEEDS_ATTENTION'):
                if IS_FIRST_FRIDAY:
                    action_required = True

                if nightly_stop_tag != 'FALSE':   
                    action_required = True

            if action_required:
                print("    * {} ({}) in {}".format(resource.display_name, resource.lifecycle_state, compartment.name))
                resource.compartment_name = compartment.name
                resource.service_name = SERVICE_NAME
                resource.region = config["region"]                
                target_resources.append(resource)
            else:
                if nightly_stop_tag != '':      
                    print("      {} ({}) in {} - {}:{}".format(resource.display_name, resource.lifecycle_state, compartment.name, 'Control.Nightly-Stop', nightly_stop_tag))
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
            if response.lifecycle_sub_state == 'STOPPING':
                print("    stop requested: {} ({}) in {}".format(response.display_name, response.lifecycle_sub_state, resource.compartment_name))              
            else:
                print("---------> error stopping {} ({})".format(response.display_name, response.lifecycle_sub_state))

    print("\nAll {} stopped!".format(SERVICE_NAME))

    return target_resources        


def change_goldengate_license(config, signer, compartments):
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
                if (resource.license_model == 'LICENSE_INCLUDED'):
                    print("    * {} ({}) in {}".format(resource.display_name, resource.license_model, compartment.name))
                    resource.compartment_name = compartment.name
                    resource.region = config["region"]                
                    target_resources.append(resource)
                else:
                    print("      {} ({}) in {}".format(resource.display_name, resource.license_model, compartment.name))
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
            if response.lifecycle_state == 'UPDATING':
                print("    change requested: {} ({}) - {}".format(response.display_name, response.lifecycle_state, response.license_model))
                send_license_type_change_notification(config, signer, SERVICE_NAME, resource, request_date, 'BYOL')                 
            else:
                print("---------> error changing {} ({}) - {}".format(response.display_name, response.lifecycle_state, response.license_model))

    print("\nAll {} changed!".format(SERVICE_NAME))

def _get_resources(config, signer, compartment_id):
    client = oci.golden_gate.GoldenGateClient(config=config, signer=signer)
    resources = oci.pagination.list_call_get_all_results(
        client.list_deployments,
        compartment_id
    )
    return resources.data

def _perform_resource_action(config, signer, resource_id, action):
    client = oci.golden_gate.GoldenGateClient(config=config, signer=signer)
    details = oci.golden_gate.models.StopDeploymentDetails(type="DEFAULT")

    if (action == 'STOP'):
        stop_response = client.stop_deployment(
            resource_id,
            details
        )

        response = client.get_deployment(
            resource_id
        )        

    return response.data, stop_response.headers['Date']


def _change_license_model(config, signer, resource_id, license_model):
    client = oci.golden_gate.GoldenGateClient(config=config, signer=signer)
    details = oci.golden_gate.models.UpdateDeploymentDetails(license_model = license_model)
    
    update_response = client.update_deployment(
        resource_id,
        details
    )

    response = client.get_deployment(
        resource_id
    )

    oci.wait_until(
        client, 
        response, 
        evaluate_response=lambda r: r.data.lifecycle_state == 'ACTIVE'
    )     

    return response.data, update_response.headers['Date']