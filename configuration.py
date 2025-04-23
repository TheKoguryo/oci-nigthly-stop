########## Configuration ####################
# Specify your config file
configfile = '~/.oci/config'

# Specify your profile name
profile = 'default'

# Set true if using instance principal signing
use_instance_principal = 'TRUE'

# Set true if using Oracle internal tenancy for BYOL
is_internal_tenancy = 'FALSE'

# Set top level compartment OCID. Tenancy OCID will be set if null.
top_level_compartment_id = 'ocid1.compartment..'

# List compartment names to exclude
excluded_parent_compartments = ['ManagedCompartmentForPaaS', 'TEMP_COMPARTMENT_TO_BE_DELETED'] # Include sub compartments
excluded_compartments = []

# List target regions. All regions will be counted if null.
target_region_names = []
excluded_region_names = []

# List resource ids to exclude
excluded_resource_ids = []
excluded_resource_ids.append('ocid1.autonomousdatabase..')

# Set Email SMTP Server Info
smtp_username = "ocid1.user..@ocid1.tenancy.."
smtp_password = ""
smtp_host = "smtp.email.."
smtp_port = "587"

# Set Email Sender Info
sender_email = ""
sender_name = "Nightly Stop"
cc = None
bcc = ""
langugage="Korean"
#langugage="English"
