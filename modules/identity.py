import oci

def login(config, signer):
    identity = oci.identity.IdentityClient(config, signer=signer)
    user = identity.get_user(config['user']).data
    print("Logged in as: {} @ {}".format(user.description, config['region']))

def get_compartment_list(config, signer, compartment_id, excluded_parent_compartments):
    identity = oci.identity.IdentityClient(config, signer=signer)

    target_compartments = []
    all_compartments = []

    top_level_compartment_response = identity.get_compartment(compartment_id)
    target_compartments.append(top_level_compartment_response.data)
    all_compartments.append(top_level_compartment_response.data)

    while len(target_compartments) > 0:
        target = target_compartments.pop(0)

        if target.name in excluded_parent_compartments:
            continue

        child_compartment_response = oci.pagination.list_call_get_all_results(
            identity.list_compartments,
            compartment_id=target.id,
            lifecycle_state="ACTIVE"
        )
        target_compartments.extend(child_compartment_response.data)
        all_compartments.extend(child_compartment_response.data)

    return all_compartments

    #active_compartments = []
    #for compartment in all_compartments:
    #    if compartment.lifecycle_state== 'ACTIVE':
    #        active_compartments.append(compartment)

    #return active_compartments

def get_region_subscription_list(config, signer, tenancy_id):
    identity = oci.identity.IdentityClient(config, signer=signer)
    response = identity.list_region_subscriptions(
        tenancy_id
    )
    return response.data

def get_tenancy_name(config, signer, tenancy_id):
    identity = oci.identity.IdentityClient(config, signer=signer)

    tenancy_name = identity.get_tenancy(tenancy_id).data.name

    return tenancy_name
