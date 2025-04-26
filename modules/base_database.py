import oci
from modules.utils import *

SERVICE_NAME = 'Oracle Base Database'

def stop_base_database_systems(config, signer, compartments, filter_tz, filter_mode):
    target_resources = []

    print("Listing all {} DB systems... (* is marked for stop)".format(SERVICE_NAME))
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
            
        db_systems = _get_db_system_list(config, signer, compartment.id)
        for db_system in db_systems:
            action_required = False
            if (db_system.lifecycle_state == 'AVAILABLE'):
                if IS_FIRST_FRIDAY:
                    action_required = True
                                    
                if ('Control' in db_system.defined_tags) and ('Nightly-Stop' in db_system.defined_tags['Control']):     
                    if (db_system.defined_tags['Control']['Nightly-Stop'].upper() != 'FALSE'):    
                        action_required = True
                else:
                    action_required = True

            if action_required:
                print("      {} ({}) in {}".format(db_system.display_name, db_system.lifecycle_state, compartment.name))

                db_nodes = _get_db_node_list(config, signer, compartment.id, db_system.id)

                for db_node in db_nodes:

                    if (db_node.lifecycle_state == 'AVAILABLE'):
                        print("        * node:{} ({})".format(db_node.hostname, db_node.lifecycle_state))
                        db_node.compartment_name = compartment.name
                        db_node.display_name = db_system.display_name + " - Node: " + db_node.hostname
                        db_node.region = config["region"]
                        db_node.defined_tags = db_system.defined_tags
                        db_node.service_name = SERVICE_NAME
                        target_resources.append(db_node)
                    else:
                        print("          node:{} ({})".format(db_node.hostname, db_node.lifecycle_state))
            else:
                if ('Control' in db_system.defined_tags) and ('Nightly-Stop' in db_system.defined_tags['Control']):  
                    print("      {} ({}) in {} - {}:{}".format(db_system.display_name, db_system.lifecycle_state, compartment.name, 'Control.Nightly-Stop', db_system.defined_tags['Control']['Nightly-Stop'].upper()))
                else:
                    print("      {} ({}) in {}".format(db_system.display_name, db_system.lifecycle_state, compartment.name))


    print('\nStopping * marked {}...'.format(SERVICE_NAME))
    for resource in target_resources:
        try:
            response, request_date = _perform_db_node_action(config, signer, resource.id, 'STOP')
        except oci.exceptions.ServiceError as e:
            print("---------> error. status: {}".format(e))
            pass
        else:
            if response.lifecycle_state == 'STOPPING':
                #print("    stop requested: {} ({})".format(response.hostname, response.lifecycle_state))
                print("    stop requested: {} ({}) in {}".format(response.hostname, response.lifecycle_state, resource.compartment_name))
            else:
                print("---------> error stopping {} ({})".format(response.hostname, response.lifecycle_state))

    print("\nAll {} DB systems stopped!".format(SERVICE_NAME))

    return target_resources    

def change_base_database_license(config, signer, compartments):
    target_resources = []

    print("Listing all {} DB systems ... (* is marked for change)".format(SERVICE_NAME))

    for compartment in compartments:
        print("  compartment: {}".format(compartment.name))
        resources = _get_db_system_list(config, signer, compartment.id)
        for resource in resources:
            if resource.lifecycle_state == 'TERMINATED':
                continue

            action_required = False
            if ('Control' in resource.defined_tags) and ('BYOL' in resource.defined_tags['Control']):     
                if (resource.defined_tags['Control']['BYOL'].upper() != 'FALSE'):    
                    action_required = True
            else:
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
                if ('Control' in resource.defined_tags) and ('BYOL' in resource.defined_tags['Control']):   
                    print("      {} ({}) in {} - {}:{}".format(resource.display_name, resource.license_model, compartment.name, 'Control.BYOL', resource.defined_tags['Control']['BYOL'].upper()))
                else:
                    print("      {} ({}) in {}".format(resource.display_name, resource.license_model, compartment.name))

    print("\nChanging * marked {}'s lisence model...".format(SERVICE_NAME))
    for resource in target_resources:
        try:
            response, request_date = _change_license_model(config, signer, resource.id, 'BRING_YOUR_OWN_LICENSE')
        except oci.exceptions.ServiceError as e:
            print("---------> error. status: {}".format(e))
            pass
        else:
            if response.lifecycle_state == 'UPDATING':
                print("    change requested: {} ({})".format(response.display_name, response.lifecycle_state))
                send_license_type_change_notification(config, signer, SERVICE_NAME, resource, request_date, 'BYOL')
            else:
                print("---------> error changing {} ({})".format(response.display_name, response.lifecycle_state))

    print("\nAll {} DB systems changed!".format(SERVICE_NAME))

def _get_db_system_list(config, signer, compartment_id):
    client = oci.database.DatabaseClient(config=config, signer=signer)
    resources = oci.pagination.list_call_get_all_results(
        client.list_db_systems,
        compartment_id=compartment_id
    )
    return resources.data

def _get_db_node_list(config, signer, compartment_id, db_system_id):
    client = oci.database.DatabaseClient(config=config, signer=signer)
    resources = oci.pagination.list_call_get_all_results(
        client.list_db_nodes,
        compartment_id = compartment_id,
        db_system_id = db_system_id
    )
    return resources.data

def _perform_db_node_action(config, signer, resource_id, action):
    client = oci.database.DatabaseClient(config=config, signer=signer)
    response = client.db_node_action(
        resource_id,
        action
    )

    return response.data, response.headers['Date']

def _change_license_model(config, signer, resource_id, license_model):
    client = oci.database.DatabaseClient(config=config, signer=signer)
    details = oci.database.models.UpdateAutonomousDatabaseDetails(license_model = license_model)
    
    response = client.update_db_system(
        resource_id,
        details
    )

    return response.data, response.headers['Date']