# coding: utf-8

import oci
from datetime import timedelta
from datetime import datetime
import argparse
import pytz
from oci.signer import Signer
from modules.identity import *
from modules.compute import *
from modules.autonomous_database import *
from modules.base_database import *
from modules.digital_assitant import *
from modules.analytics import *
from modules.visual_builder import *
from modules.mysql import *
from modules.integration_cloud import *
from modules.data_science_notebook_sessions import *
from modules.data_science_model_deployements import *
from modules.data_integration import *
from modules.goldengate import *
from modules.utils import *
from configuration import *

class Compartment:
    def __init__(self, id, name):
        self.id = id 
        self.name = name        

    def __str__(self):
        return f"id: {self.id}, name: {self.name}"

    def __eq__(self, other):
        return (self.id == other.id) and (self.name == other.name)
    
##########################################################################
# set parser
##########################################################################
def set_parser_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument('-regions', nargs="*", default="", dest='regions', help='List target regions. All regions will be counted if null')
    parser.add_argument('-excl_regions', nargs="*", default="", dest='excl_regions', help='List excluded regions.')

    result = parser.parse_args()
   
    return result 

##########################################################################
# Main
##########################################################################
print("\nIS_FIRST_FRIDAY: " + str(IS_FIRST_FRIDAY))
if IS_FIRST_FRIDAY:
    print ("===============[ Today is First Friday of This Month ]=================")
    print ("Stop the World")


args = set_parser_arguments()
if args is None:
    exit()

if args.regions:
    print("regions: %r" % args.regions)
    target_region_names = args.regions

if args.excl_regions:
    print("excl_regions: %r" % args.excl_regions)
    excluded_region_names = args.excl_regions


config = None
tenancy_id = None

if use_instance_principal == 'TRUE':
    signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    config = {'region': signer.region, 'tenancy': signer.tenancy_id, 'user': 'instance_principal'}
    tenancy_id = signer.tenancy_id
    
    tenancy_name=get_tenancy_name(config, signer, signer.tenancy_id)
    signer.tenancy_name = tenancy_name
else:
    config = oci.config.from_file(configfile, profile)

    signer = Signer(
        tenancy = config['tenancy'],
        user = config['user'],
        fingerprint = config['fingerprint'],
        private_key_file_location = config['key_file'],
        pass_phrase = config['pass_phrase']
    )

    tenancy_id = config['tenancy']    
    tenancy_name=get_tenancy_name(config, signer, signer.tenancy_id)
    signer.tenancy_name = tenancy_name

    print ("\n===========================[ Login check ]=============================")
    login(config, signer)


print ("\n==========================[ Target regions ]===========================")
all_regions = get_region_subscription_list(config, signer, tenancy_id)
target_regions=[]
target_regions_names=[]
for region in all_regions:
    if ((not target_region_names) or (region.region_name in target_region_names)) and (region.region_name not in excluded_region_names):
        target_regions.append(region)
        target_regions_names.append(region.region_name)
        print (region.region_name)

print ("\n========================[ Target compartments ]========================")
if not top_level_compartment_id:
    top_level_compartment_id = tenancy_id
compartments = get_compartment_list(config, signer, top_level_compartment_id, excluded_parent_compartments)
#target_compartments=[]
target_compartments_ids=[]
for compartment in compartments:
    if compartment.name not in excluded_compartments:
        #target_compartments.append(compartment)
        target_compartments_ids.append(compartment.id)
        print (compartment.name)

print ("\n==============[ Usage Based Target regions&compartments ]==============")
usage_api_client = oci.usage_api.UsageapiClient(config=config, signer=signer)

timezone = pytz.timezone('UTC')
today = datetime.now(timezone).replace(hour=0, minute=0, second=0, microsecond=0)
d_day_started = today - timedelta(days=10)

usages = usage_api_client.request_summarized_usages(
            request_summarized_usages_details=oci.usage_api.models.RequestSummarizedUsagesDetails(
                tenant_id=tenancy_id,
                time_usage_started=d_day_started,
                time_usage_ended=today,
                granularity="MONTHLY",
                group_by=["region", "service", "compartmentName", "compartmentId"],
                compartment_depth=6
            )
        ).data

target = dict()
for item in usages.items:
    if item.region not in target_regions_names:
        continue

    if item.compartment_id not in target_compartments_ids:
        continue

    if item.computed_amount is None or item.computed_amount == 0.0:
        continue

    compartment = Compartment(item.compartment_id, item.compartment_name)

    isNew = False
    if item.region in target:
        if item.service in target[item.region]:
            if compartment not in target[item.region][item.service]:
                target[item.region][item.service].append(compartment)
                isNew = True
        else:
            target[item.region][item.service]=[]
            target[item.region][item.service].append(compartment)    
            isNew = True        
    else:
        target[item.region] = dict()
        target[item.region][item.service] = []
        target[item.region][item.service].append(compartment)
        isNew = True

    if isNew:
        print("region: {:15s} compartment_name: {:35s} service: {}".format(item.region, item.compartment_name, item.service))        


for region in target:
    print ("\n============[ {} ]================".format(region))

    config["region"] = region

    if "Compute" in target[region]:
        service_name = "Compute"
        print ("\n>>> {}".format(service_name))
        target_compartments = target[region][service_name]
    
        stop_compute_instances(config, signer, target_compartments)

    if "Database" in target[region]:
        service_name = "Database"
        print ("\n>>> {}".format(service_name))
        target_compartments = target[region][service_name]


        stop_base_database_systems(config, signer, target_compartments)
        if is_internal_tenancy == 'TRUE':
            change_base_database_license(config, signer, target_compartments)

        stop_autonomous_database(config, signer, target_compartments)
        if is_internal_tenancy == 'TRUE':
            change_autonomous_database_license(config, signer, target_compartments)    

    if "Digital Assistant" in target[region]:
        service_name = "Digital Assistant"
        print ("\n>>> {}".format(service_name))
        target_compartments = target[region][service_name]

        stop_digital_assitants(config, signer, target_compartments)

    if "Analytics" in target[region]:
        service_name = "Analytics"
        print ("\n>>> {}".format(service_name))
        target_compartments = target[region][service_name]

        stop_analytics(config, signer, target_compartments)
        if is_internal_tenancy == 'TRUE':
            change_analytics_license(config, signer, target_compartments) 

    if "Visual Builder" in target[region]:
        service_name = "Visual Builder"
        print ("\n>>> {}".format(service_name))
        target_compartments = target[region][service_name]

        stop_visual_builder(config, signer, target_compartments)

    if "MySQL" in target[region]:
        service_name = "MySQL"
        print ("\n>>> {}".format(service_name))
        target_compartments = target[region][service_name]

        stop_mysql(config, signer, target_compartments)

    if "Integration Service" in target[region]:
        service_name = "Integration Service"
        print ("\n>>> {}".format(service_name))
        target_compartments = target[region][service_name]

        stop_integration_cloud(config, signer, target_compartments)
        if is_internal_tenancy == 'TRUE':
            change_integration_cloud_license(config, signer, target_compartments)

    if "Data Science" in target[region]:
        service_name = "Data Science"
        print ("\n>>> {}".format(service_name))
        target_compartments = target[region][service_name]

        stop_data_science_notebook_sessions(config, signer, target_compartments)
        stop_data_science_model_deployments(config, signer, target_compartments)

    if "GoldenGate" in target[region]:
        service_name = "GoldenGate"
        print ("\n>>> {}".format(service_name))
        target_compartments = target[region][service_name]

        stop_goldengate(config, signer, target_compartments)
        if is_internal_tenancy == 'TRUE':
            change_goldengate_license(config, signer, target_compartments)

    if "Data Integration" in target[region]:
        service_name = "Data Integration"
        print ("\n>>> {}".format(service_name))
        target_compartments = target[region][service_name]

        stop_data_integration(config, signer, target_compartments)