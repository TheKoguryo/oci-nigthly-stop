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


def get_email(config, signer, tenancy_id, domain_display_name, user_name):
    user_email = ""

    if domain_display_name == "" or domain_display_name is None:
        domain_display_name = "default"

    identity_client = oci.identity.IdentityClient(config, signer=signer)   

    list_domains_response = identity_client.list_domains(
        compartment_id=tenancy_id,
        display_name=domain_display_name,
        lifecycle_state="ACTIVE")

    domain_endpoint = list_domains_response.data[0].url

    identity_domains_client = oci.identity_domains.IdentityDomainsClient(config, domain_endpoint, signer=signer)

    list_users_response = identity_domains_client.list_users(
        filter="userName eq \"" + user_name + "\"")        

    if len(list_users_response.data.resources) > 0:
        user = list_users_response.data.resources[0]

        for email in user.emails:
            if email.primary == True:
                user_email = email.value
                break

    print("user_email: " + user_email)

    return user_email


def get_user_name_by_user_id(config, signer, tenancy_id, domain_display_name, user_id):
    user_email = ""
    user_name = ""

    if domain_display_name == "" or domain_display_name is None:
        domain_display_name = "default"

    identity_client = oci.identity.IdentityClient(config, signer=signer)   

    list_domains_response = identity_client.list_domains(
        compartment_id=tenancy_id,
        display_name=domain_display_name,
        lifecycle_state="ACTIVE")

    domain_endpoint = list_domains_response.data[0].url;

    identity_domains_client = oci.identity_domains.IdentityDomainsClient(config, domain_endpoint, signer=signer)

    try:
        user = identity_domains_client.get_user(user_id=user_id).data
    except oci.exceptions.ServiceError as e:
        print("---------> error. status: {}".format(e))
        pass
    else:
        user_name = domain_display_name + "/" + user.display_name
        print("user_id: " + user_id)
        print("user_name: " + user_name)   

    return user_name