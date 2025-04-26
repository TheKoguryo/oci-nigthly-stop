import oci
from modules.utils import *
from configuration import *

SERVICE_NAME = 'Autonomous Database'

def stop_autonomous_database(config, signer, compartments, filter_tz, filter_mode):
    target_resources = []

    print("\nListing all {}... (* is marked for stop)".format(SERVICE_NAME))
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
            if (resource.lifecycle_state == 'AVAILABLE'):
                if IS_FIRST_FRIDAY:
                    action_required = True
                                    
                if ('Control' in resource.defined_tags) and ('Nightly-Stop' in resource.defined_tags['Control']):     
                    if (resource.defined_tags['Control']['Nightly-Stop'].upper() != 'FALSE'):    
                        action_required = True
                else:
                    action_required = True

            if action_required:
                if resource.id in excluded_resource_ids:
                    continue

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
            response, request_date = _perform_resource_action(config, signer, resource.id)
        except oci.exceptions.ServiceError as e:
            print("---------> error. status: {}".format(e))
            pass
        else:
            if response.lifecycle_state == 'STOPPING':
                print("    stop requested: {} ({}) in {}".format(response.display_name, response.lifecycle_state, resource.compartment_name))
                send_license_type_change_notification(config, signer, SERVICE_NAME, resource, request_date, 'STOP')
            else:
                print("---------> error stopping {} ({})".format(response.display_name, response.lifecycle_state))

    print("\nAll {} stopped!".format(SERVICE_NAME))

    return target_resources    

def change_autonomous_database_license(config, signer, compartments):
    target_resources = []

    print("Listing all {}... (* is marked for change)".format(SERVICE_NAME))

    for compartment in compartments:
        print("  compartment: {}".format(compartment.name))
        try:
            resources = _get_resources(config, signer, compartment.id)
        except oci.exceptions.ServiceError as e:
            print("  compartment: {}".format(compartment.id))
            print("---------> error. status: {}".format(e))
            continue            

        for resource in resources:
            if resource.lifecycle_state == 'TERMINATED':
                continue

            if resource.db_workload != 'OLTP' and resource.db_workload != 'DW':
                continue

            action_required = False
            if ('Control' in resource.defined_tags) and ('BYOL' in resource.defined_tags['Control']):     
                if (resource.defined_tags['Control']['BYOL'].upper() != 'FALSE'):    
                    action_required = True
            else:
                action_required = True

            if action_required:
                if (resource.license_model == 'LICENSE_INCLUDED'):

                    if (resource.is_dev_tier == True):
                        print("      {} ({}, developer) in {}".format(resource.display_name, resource.license_model, compartment.name))
                    elif (resource.is_free_tier == True):
                        print("      {} ({}, always_free) in {}".format(resource.display_name, resource.license_model, compartment.name))
                    else:
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

    print("\nChanging * marked {}'s lisence model...".format(SERVICE_NAME))
    for resource in target_resources:
        try:
            response, request_date = _change_license_model(config, signer, resource.id, 'BRING_YOUR_OWN_LICENSE')
        except oci.exceptions.ServiceError as e:
            print("---------> error.status: {}".format(e))
            pass
        else:
            if response.lifecycle_state == 'UPDATING':
                print("    change requested: {} ({})".format(response.display_name, response.lifecycle_state))
                send_license_type_change_notification(config, signer, SERVICE_NAME, resource, request_date, 'BYOL')
            else:
                print("---------> error changing {} ({})".format(response.display_name, response.lifecycle_state))

    print("\nAll {} changed!".format(SERVICE_NAME))

def _get_resources(config, signer, compartment_id):
    client = oci.database.DatabaseClient(config=config, signer=signer)

    resources = oci.pagination.list_call_get_all_results(
        client.list_autonomous_databases,
        compartment_id=compartment_id
    )
 
    return resources.data

def _change_license_model(config, signer, resource_id, license_model):
    client = oci.database.DatabaseClient(config=config, signer=signer)
    details = oci.database.models.UpdateAutonomousDatabaseDetails(license_model = license_model)

    if license_model == 'BRING_YOUR_OWN_LICENSE':
        details = oci.database.models.UpdateAutonomousDatabaseDetails(license_model = license_model, database_edition='ENTERPRISE_EDITION')
    
    response = client.update_autonomous_database(
        resource_id,
        details
    )
    return response.data, response.headers['Date']

def _perform_resource_action(config, signer, resource_id):
    client = oci.database.DatabaseClient(config=config, signer=signer)
    response = client.stop_autonomous_database(
        resource_id
    )
    return response.data, response.headers['Date']
