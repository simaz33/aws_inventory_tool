import boto3
import logging

logging.basicConfig(level="INFO")
log = logging.getLogger(__name__)


class ReaderAws:
    def __init__(self, aws_credentials):
        self.aws_login = aws_credentials.aws_login
        self.aws_pass = aws_credentials.aws_pass
        self.aws_region = aws_credentials.aws_region

    def set_boto3_client(self, service_name):

        log.info("Setting boto3 client for service: %s", service_name)

        if self.aws_login != 'not_set' and self.aws_pass != 'not_set':
            self.client = boto3.client(
                service_name,
                aws_access_key_id=self.aws_login,
                aws_secret_access_key=self.aws_pass,
                region_name=self.aws_region
                )
        else:
            self.client = boto3.client(
                service_name,
                region_name=self.aws_region
                )

    def get_ec2_instance_info(self):
        self.set_boto3_client('ec2')

        log.info("Querying EC2 instances info")

        ec2_client = self.client
        ec2_request = ec2_client.describe_instances()
        ec2_instance_reservations = ec2_request['Reservations']

        ec2_info_list = []

        for ec2_instance_reservation in ec2_instance_reservations:
            instance_info = ec2_instance_reservation['Instances'][0]

            try:
                instance_tags = instance_info['Tags']
            except BaseException:
                log.info("No tags: " + instance_info["InstanceId"])
                instance_tags = {}

            if "name" not in instance_info:
                try:
                    name_dict = next(
                        item for item in instance_tags if item["Key"] == "Name")
                    instance_name = name_dict["Value"]
                except StopIteration:
                    instance_name = "Not set"

                instance_info["name"] = instance_name

            if "autoscaling_group_name" not in instance_info:
                try:
                    asg_name_dict = next(
                        item for item in instance_tags if item["Key"] == "aws:autoscaling:groupName")
                    instance_asg_name = asg_name_dict["Value"]
                except StopIteration:
                    instance_asg_name = "Not found or not in asg"

                instance_info["autoscaling_group_name"] = instance_asg_name

            ec2_info_list.append(instance_info)

        return ec2_info_list

    def get_rds_info(self):
        self.set_boto3_client('rds')

        log.info("Querying RDS instances info")

        rds_client = self.client
        rds_client_response = rds_client.describe_db_instances()
        rds_instances_info = rds_client_response['DBInstances']

        rds_info_list = []

        for rds_instance_reservation in rds_instances_info:
            #custom values for consistancy with aurora response
            instance_create_time = rds_instance_reservation["InstanceCreateTime"]
            instance_endpoint = rds_instance_reservation['Endpoint']["Address"]
            instance_status = rds_instance_reservation["DBInstanceStatus"]
                        
            rds_instance_reservation["DatabaseCreateTime"] = instance_create_time
            rds_instance_reservation["DatabaseAddress"] = instance_endpoint
            rds_instance_reservation["DatabaseStatus"] = instance_status

            if 'DBName' in rds_instance_reservation:
                instance_db_name = rds_instance_reservation['DBName']
            else:
                instance_db_name = "Not found"

            rds_instance_reservation["DatabaseName"] = instance_db_name

            rds_info_list.append(rds_instance_reservation)

        log.info("Querying Aurora instances info")
        rds_aurora_instances = rds_client.describe_db_clusters()
        rds_aurora_instances_info = rds_aurora_instances['DBClusters']

        for aurora_instance_reservation in rds_aurora_instances_info:
            #custom values for consistancy with rds response
            instance_create_time = aurora_instance_reservation['ClusterCreateTime']
            instance_endpoint = aurora_instance_reservation['Endpoint']
            instance_status = aurora_instance_reservation["Status"]

            aurora_instance_reservation["DatabaseCreateTime"] = instance_create_time
            aurora_instance_reservation["DatabaseAddress"] = instance_endpoint
            aurora_instance_reservation["DatabaseStatus"] = instance_status

            rds_info_list.append(rds_instance_reservation)

        return rds_info_list

    def get_route53_info(self):
        self.set_boto3_client('route53')

        log.info("Querying Route53 instances info")

        r53_client = self.client
        r53_client_response = r53_client.list_hosted_zones_by_name()
        r53_hosted_zones = r53_client_response['HostedZones']

        r53_info_list = []

        for r53_hosted_zone in r53_hosted_zones:
            r53_hosted_zoneid = r53_hosted_zone["Id"]
            r53_zone_record_sets = r53_client.list_resource_record_sets(HostedZoneId=r53_hosted_zoneid)

            ignored_record_types = set(["SOA", "NS" , "TXT"])

            for zone_record_set in r53_zone_record_sets["ResourceRecordSets"]:

                if zone_record_set["Type"] in ignored_record_types:
                    continue

                if zone_record_set["Type"] == "A":
                    if 'AliasTarget' in zone_record_set:
                        target_list = []
                        target_list.append(zone_record_set["AliasTarget"]["DNSName"])
                        zone_record_set["Target"] = target_list

                    if 'ResourceRecords' in zone_record_set:
                        zone_record_set["Target"] = [list_of_targets['Value'] for list_of_targets in zone_record_set["ResourceRecords"]]

                if zone_record_set["Type"] == "CNAME":
                    zone_record_set["Target"] = [list_of_targets['Value'] for list_of_targets in zone_record_set["ResourceRecords"]]

                r53_info_list.append(zone_record_set)

        return r53_info_list

    def get_elb_info(self):
        self.set_boto3_client('elbv2')

        log.info("Querying ELB instances info")

        elb_client = self.client

        elb_instances = elb_client.describe_load_balancers()
        elb_instances_info = elb_instances['LoadBalancers']

        return elb_instances_info

    def get_s3_info(self):
        self.set_boto3_client('s3')

        log.info("Querying S3 instances info")

        s3_client = self.client
        s3_buckets = s3_client.list_buckets()

        return s3_buckets['Buckets']
