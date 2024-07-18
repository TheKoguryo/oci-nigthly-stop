import re
import pytz
from datetime import datetime, timedelta

import smtplib
import email.utils
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import configuration

def notify(config, signer, service_name, resource, request_date_string, type):
    title = None
    resource_name = None
    to = None

    if hasattr(resource, 'name'):
        resource_name = resource.name
    else:
        resource_name = resource.display_name

    if ('Oracle-Tags' in resource.defined_tags) and ('CreatedBy' in resource.defined_tags['Oracle-Tags']):     
        created_by = str(resource.defined_tags['Oracle-Tags']['CreatedBy'])
        created_by = created_by.rsplit('/', 1)[1]
        print("created_by: " + created_by)

        if _isEmailFormat(created_by) == True:
            to = created_by

    if to is None:
        to = configuration.bcc
    
    KST = pytz.timezone('Asia/Seoul')
    date_string = request_date_string
    datetime_object = datetime.strptime(date_string, '%a, %d %b %Y %H:%M:%S %Z')
    request_date_string = str(datetime_object.astimezone(KST))

    if (type == 'BYOL'):
        warningMessage = service_name + " Internal Tenancy 절약 모드"
        title = "[" + signer.tenancy_name + "] " + resource_name + " 라이센스 정책 변경 - BYOL"        
        main_message = signer.tenancy_name + " 테넌시 관리자가 설정한 Nightly Stop 자원 관리 정책에 따라, 스케줄러에 의해 아래 자원은 BYOL 라이센스로 변경되었습니다. <br>기존 라이센스 정책 사용을 원하는 경우, 해당 자원 태그에 Control.BYOL=FALSE로 설정 후, 원하는 라이센스로 변경하여 하여 사용하시기 바랍니다."
    else:
        warningMessage = "Nightly Stop - " + service_name + " 서비스 심야 절약 모드"     
        title = "[" + signer.tenancy_name + "] " + resource_name + " 일시 중지"
        main_message = signer.tenancy_name + " 테넌시 관리자가 설정한 Nightly Stop 자원 관리 정책에 따라, 스케줄러에 의해 아래 자원은 중지(Stop) 또는 비활성화(Deactivate) 되었습니다. <br>필요하신 시점에 시작(Start) 또는 활성화(Activate)하여 사용하시기 바랍니다."

    template = Path('mail-template/notify.html').read_text()

    redirectUrl = "https://cloud.oracle.com"

    if resource.id.startswith("ocid1.instance"):
        redirectUrl = "https://cloud.oracle.com/compute/instances/" + resource.id +"?region=" + resource.region
    elif resource.id.startswith("ocid1.dbnode"):
        redirectUrl = "https://cloud.oracle.com/dbaas/dbsystems/" + resource.db_system_id +"/nodes?region=" + resource.region
    elif resource.id.startswith("ocid1.dbsystem"):
        redirectUrl = "https://cloud.oracle.com/dbaas/dbsystems/" + resource.id +"/nodes?region=" + resource.region      
    elif resource.id.startswith("ocid1.autonomousdatabase"):
        redirectUrl = "https://cloud.oracle.com/db/adbs/" + resource.id +"?region=" + resource.region    
    elif resource.id.startswith("ocid1.odainstance"):
        redirectUrl = "https://cloud.oracle.com/digital-assistant/oda-instances/" + resource.id +"?region=" + resource.region
    elif resource.id.startswith("ocid1.analyticsinstance"):
        redirectUrl = "https://cloud.oracle.com/analytics/instances/" + resource.id +"?region=" + resource.region
    elif resource.id.startswith("ocid1.visualbuilderinstance"):
        redirectUrl = "https://cloud.oracle.com/vb/instances/" + resource.id +"?region=" + resource.region
    elif resource.id.startswith("ocid1.mysqldbsystem"):
        redirectUrl = "https://cloud.oracle.com/mysqlaas/db-systems/" + resource.id +"?region=" + resource.region
    elif resource.id.startswith("ocid1.integrationinstance"):
        redirectUrl = "https://cloud.oracle.com/oic/integration-instances/" + resource.id +"?region=" + resource.region
    elif resource.id.startswith("ocid1.datasciencenotebooksession"):
        redirectUrl = "https://cloud.oracle.com/data-science/notebook-sessions/" + resource.id +"?region=" + resource.region
    elif resource.id.startswith("ocid1.datasciencemodeldeployment"):
        redirectUrl = "https://cloud.oracle.com/data-science/model-deployments/" + resource.id +"?region=" + resource.region   
    elif resource.id.startswith("ocid1.disworkspace"):
        redirectUrl = "https://cloud.oracle.com/dis/" + resource.id +"/home?region=" + resource.region  
    elif resource.id.startswith("ocid1.goldengatedeployment"):
        redirectUrl = "https://cloud.oracle.com/goldengate/deployments/" + resource.id +"?region=" + resource.region  

    html_body = template.replace("${title}", title)
    html_body = html_body.replace("${companyName}", signer.tenancy_name)
    html_body = html_body.replace("${headerImage}", "https://ci3.googleusercontent.com/meips/ADKq_NbPxsLyenwFfmz-f6Je7pVsAipkskSYJASeBzieNgGFsW0GYaHme6TCvbb6LDKTtN1E227iYqEXEmxtk_mFau2muY15hrzfcKjujIjdDJEA6OprriPEMzNBy0HM2u_-UYnp7JtczGEDhcxa73WiwAlWk6JSNkWpOJC8wYwSoZk2A1UnjMN9q4tk7YIvbgFJ2oxjEEGQvDRY3-fIuQFteTqWqQI=s0-d-e1-ft#https://idcs-545bcf5ba488439e82f6294f0fc978bb.identity.oraclecloud.com:443/ui/v1/public/common/asset/defaultBranding/oracle-email-header.png")
    html_body = html_body.replace("${warningMessage}", warningMessage)
    html_body = html_body.replace("${mainMessage}", main_message)
    html_body = html_body.replace("${tenancyName}", signer.tenancy_name)
    html_body = html_body.replace("${region}", resource.region)
    html_body = html_body.replace("${compartmentName}", resource.compartment_name)
    html_body = html_body.replace("${serviceName}", service_name)
    html_body = html_body.replace("${resourceName}", resource_name)
    html_body = html_body.replace("${requestDate}", request_date_string)
    html_body = html_body.replace("${redirectUrl}", redirectUrl)

    send_email(configuration.sender_email, configuration.sender_name, to, configuration.cc, configuration.bcc, title, html_body)


def send_email(sender_email, sender_name, to, cc, bcc, subject, body):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = email.utils.formataddr((sender_name, sender_email))
    msg['To'] = to      # 'john.doe@example.com,john.smith@example.co.uk'
    recipients = to   

    if cc:
        msg['Cc'] = cc  # 'john.doe@example.com,john.smith@example.co.uk'
        recipients += ',' + cc

    if bcc:
        msg['Bcc'] = bcc  # 'john.doe@example.com,john.smith@example.co.uk'
        recipients += ',' + bcc        

    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP(configuration.smtp_host, configuration.smtp_port)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(configuration.smtp_username, configuration.smtp_password)
        server.sendmail(sender_email, recipients.split(','), msg.as_string())
        server.close()
    except Exception as ex:
        print("ERROR: ", ex, flush=True)
    else:
        print ("INFO: Email successfully sent!", flush=True)

def _isEmailFormat(value):
    obj = re.search(r'[\w.]+\@[\w.]+', value)
    if not obj:
        return False

    return True

def is_first_friday_today():
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
   
    first_day = datetime(today.year, today.month, 1).replace(hour=0, minute=0, second=0, microsecond=0)

    if first_day.weekday() <= 4:
        first_friday = first_day + timedelta(days=(4 - first_day.weekday()))
    else:
        first_friday = first_day + timedelta(days=(11 - first_day.weekday()))

    first_day_next_month = datetime(today.year, today.month+1, 1).replace(hour=0, minute=0, second=0, microsecond=0)

    if first_day_next_month.weekday() <= 4:
        first_friday_next_month = first_day_next_month + timedelta(days=(4 - first_day_next_month.weekday()))
    else:
        first_friday_next_month = first_day_next_month + timedelta(days=(11 - first_day_next_month.weekday()))


    print("                     Today: " + today.strftime("%Y-%m-%d %A"))
    print("First Friday of This Month: " + first_friday.strftime("%Y-%m-%d %A"))
    print("First Friday of Next Month: " + first_friday_next_month.strftime("%Y-%m-%d %A"))

    if today.weekday() != 4:  # 0: Monday, ..., 4: Friday
        return False
       
    if today == first_friday:
        return True
    else:
        return False    

IS_FIRST_FRIDAY = is_first_friday_today()        