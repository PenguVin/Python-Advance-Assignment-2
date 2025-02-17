import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Any
import statistics

class AWSResourceOptimizer:
    def __init__(self):
        self.ec2 = boto3.client('ec2')
        self.rds = boto3.client('rds')
        self.cloudwatch = boto3.client('cloudwatch')
        self.lambda_client = boto3.client('lambda')
        self.s3 = boto3.client('s3')
        
    def get_ec2_low_utilization(self, cpu_threshold: float = 10.0, days: int = 30) -> List[Dict[str, Any]]:
        """Identify EC2 instances with low CPU utilization."""
        try:
            low_utilization_instances = []
            instances = self.ec2.describe_instances()
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    if instance['State']['Name'] != 'running':
                        continue
                        
                    response = self.cloudwatch.get_metric_statistics(
                        Namespace='AWS/EC2',
                        MetricName='CPUUtilization',
                        Dimensions=[{'Name': 'InstanceId', 'Value': instance['InstanceId']}],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=3600,  # 1-hour periods
                        Statistics=['Average']
                    )
                    
                    if response['Datapoints']:
                        avg_cpu = statistics.mean([point['Average'] for point in response['Datapoints']])
                        if avg_cpu < cpu_threshold:
                            low_utilization_instances.append({
                                'InstanceId': instance['InstanceId'],
                                'InstanceType': instance['InstanceType'],
                                'AverageCPU': round(avg_cpu, 2),
                                'Name': next((tag['Value'] for tag in instance.get('Tags', []) 
                                           if tag['Key'] == 'Name'), 'No Name')
                            })
                            
            return low_utilization_instances
        except Exception as e:
            print(f"Error checking EC2 utilization: {str(e)}")
            return []

    def get_idle_rds_instances(self, days: int = 7) -> List[Dict[str, Any]]:
        """Identify RDS instances with no connections."""
        try:
            idle_instances = []
            instances = self.rds.describe_db_instances()
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            for instance in instances['DBInstances']:
                response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/RDS',
                    MetricName='DatabaseConnections',
                    Dimensions=[{'Name': 'DBInstanceIdentifier', 
                               'Value': instance['DBInstanceIdentifier']}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,
                    Statistics=['Maximum']
                )
                
                if response['Datapoints']:
                    max_connections = max([point['Maximum'] for point in response['Datapoints']])
                    if max_connections == 0:
                        idle_instances.append({
                            'DBInstanceIdentifier': instance['DBInstanceIdentifier'],
                            'Engine': instance['Engine'],
                            'InstanceClass': instance['DBInstanceClass'],
                            'Status': instance['DBInstanceStatus']
                        })
                        
            return idle_instances
        except Exception as e:
            print(f"Error checking RDS utilization: {str(e)}")
            return []

    def get_unused_lambda_functions(self, days: int = 30) -> List[Dict[str, Any]]:
        """Identify Lambda functions with no invocations."""
        try:
            unused_functions = []
            paginator = self.lambda_client.get_paginator('list_functions')
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            for page in paginator.paginate():
                for function in page['Functions']:
                    response = self.cloudwatch.get_metric_statistics(
                        Namespace='AWS/Lambda',
                        MetricName='Invocations',
                        Dimensions=[{'Name': 'FunctionName', 
                                   'Value': function['FunctionName']}],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=days * 24 * 3600,
                        Statistics=['Sum']
                    )
                    
                    if not response['Datapoints'] or response['Datapoints'][0]['Sum'] == 0:
                        unused_functions.append({
                            'FunctionName': function['FunctionName'],
                            'Runtime': function['Runtime'],
                            'LastModified': function['LastModified']
                        })
                        
            return unused_functions
        except Exception as e:
            print(f"Error checking Lambda utilization: {str(e)}")
            return []

    def get_unused_s3_buckets(self, days: int = 30) -> List[Dict[str, Any]]:
        """Identify unused S3 buckets."""
        try:
            unused_buckets = []
            buckets = self.s3.list_buckets()['XXXXXXX']
            
            for bucket in buckets:
                try:
                    objects = self.s3.list_objects_v2(
                        Bucket=bucket['Name'],
                        MaxKeys=1
                    )
                    
                    if 'Contents' not in objects:
                        unused_buckets.append({
                            'BucketName': bucket['Name'],
                            'CreationDate': bucket['CreationDate'],
                            'Reason': 'Empty bucket'
                        })
                        continue
                    
                    metrics = self.cloudwatch.get_metric_statistics(
                        Namespace='AWS/S3',
                        MetricName='NumberOfObjects',
                        Dimensions=[{'Name': 'BucketName', 'Value': bucket['Name']}],
                        StartTime=datetime.utcnow() - timedelta(days=days),
                        EndTime=datetime.utcnow(),
                        Period=days * 24 * 3600,
                        Statistics=['Average']
                    )
                    
                    if not metrics['Datapoints']:
                        unused_buckets.append({
                            'BucketName': bucket['Name'],
                            'CreationDate': bucket['CreationDate'],
                            'Reason': 'No recent access'
                        })
                        
                except Exception as e:
                    print(f"Error checking bucket {bucket['Name']}: {str(e)}")
                    continue
                    
            return unused_buckets
        except Exception as e:
            print(f"Error checking S3 buckets: {str(e)}")
            return []

def main():
    optimizer = AWSResourceOptimizer()
    
    print("\nAWS Resource Optimization Report")
    print("=" * 50)
    
    print("\nEC2 Instances with Low CPU Utilization (<10%):")
    print("-" * 50)
    low_util_ec2 = optimizer.get_ec2_low_utilization()
    for instance in low_util_ec2:
        print(f"Instance ID: {instance['InstanceId']}")
        print(f"Name: {instance['Name']}")
        print(f"Type: {instance['InstanceType']}")
        print(f"Average CPU: {instance['AverageCPU']}%")
        print("-" * 30)
    
    print("\nIdle RDS Instances (No connections in 7 days):")
    print("-" * 50)
    idle_rds = optimizer.get_idle_rds_instances()
    for instance in idle_rds:
        print(f"Instance: {instance['DBInstanceIdentifier']}")
        print(f"Engine: {instance['Engine']}")
        print(f"Class: {instance['InstanceClass']}")
        print("-" * 30)
    
    print("\nUnused Lambda Functions (No invocations in 30 days):")
    print("-" * 50)
    unused_lambdas = optimizer.get_unused_lambda_functions()
    for function in unused_lambdas:
        print(f"Function: {function['FunctionName']}")
        print(f"Runtime: {function['Runtime']}")
        print(f"Last Modified: {function['LastModified']}")
        print("-" * 30)
    
    print("\nUnused S3 Buckets:")
    print("-" * 50)
    unused_buckets = optimizer.get_unused_s3_buckets()
    for bucket in unused_buckets:
        print(f"Bucket: {bucket['BucketName']}")
        print(f"Creation Date: {bucket['CreationDate']}")
        print(f"Reason: {bucket['Reason']}")
        print("-" * 30)
    
    print("\nSummary:")
    print("=" * 50)
    print(f"Low Utilization EC2 Instances: {len(low_util_ec2)}")
    print(f"Idle RDS Instances: {len(idle_rds)}")
    print(f"Unused Lambda Functions: {len(unused_lambdas)}")
    print(f"Unused S3 Buckets: {len(unused_buckets)}")

if __name__ == "__main__":
    main()
