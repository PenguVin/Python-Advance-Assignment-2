# Q3. Write a python script which will fetch all the regions in which a customer billed for any resources. Or a customer has any resources.


import boto3
from datetime import datetime, timedelta
from typing import Set, Tuple
from botocore.exceptions import ClientError

def get_active_regions_from_cost_explorer() -> Tuple[Set[str], str]:
    """Get regions where costs were incurred in the last 30 days."""
    try:
        ce_client = boto3.client('ce')
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date.isoformat(),
                'End': end_date.isoformat()
            },
            Granularity='MONTHLY',
            Metrics=['UnblendedCost'],
            GroupBy=[
                {'Type': 'DIMENSION', 'Key': 'REGION'}
            ]
        )
        
        active_regions = {
            group['Keys'][0] 
            for result in response['ResultsByTime']
            for group in result['Groups']
            if float(group['Metrics']['UnblendedCost']['Amount']) > 0
        }
        
        return active_regions, "Success"
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        return set(), f"Cost Explorer Error: {error_code} - {error_message}"
    except Exception as e:
        return set(), f"Cost Explorer Error: {str(e)}"

def get_active_regions_from_resource_explorer() -> Tuple[Set[str], str]:
    """Get regions where resources exist using Resource Explorer."""
    try:
        re_client = boto3.client('resource-explorer-2')
        indexes = re_client.list_indexes()
        
        if not indexes['Indexes']:
            return set(), "No Resource Explorer indexes found. Please set up Resource Explorer first."
            
        primary_region = indexes['Indexes'][0]['Region']
        re_client = boto3.client('resource-explorer-2', region_name=primary_region)
        
        active_regions = set()
        paginator = re_client.get_paginator('search')
        
        for page in paginator.paginate(
            QueryString='*',
            MaxResults=1000
        ):
            for resource in page['Resources']:
                if 'Region' in resource:
                    active_regions.add(resource['Region'])
        
        return active_regions, "Success"
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        return set(), f"Resource Explorer Error: {error_code} - {error_message}"
    except Exception as e:
        return set(), f"Resource Explorer Error: {str(e)}"

def get_active_regions_from_config() -> Tuple[Set[str], str]:
    """Get regions where resources exist using AWS Config."""
    try:
        active_regions = set()
        
        ec2_client = boto3.client('ec2')
        all_regions = [region['RegionName'] for region in ec2_client.describe_regions()['Regions']]
        
        for region in all_regions:
            try:
                regional_config = boto3.client('config', region_name=region)
                response = regional_config.describe_configuration_recorders()
                
                if response['ConfigurationRecorders']:
                    aggregator_response = regional_config.get_discovered_resource_counts()
                    if aggregator_response['TotalDiscoveredResources'] > 0:
                        active_regions.add(region)
                        
            except ClientError as e:
                if e.response['Error']['Code'] != 'AccessDeniedException':
                    print(f"Skipping region {region}: {str(e)}")
                continue
                
        return active_regions, "Success"
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        return set(), f"Config Error: {error_code} - {error_message}"
    except Exception as e:
        return set(), f"Config Error: {str(e)}"

def main():
    print("Checking permissions and fetching active regions...")
    print("\nPermission Check Results:")
    print("-" * 50)
    
    cost_regions, cost_status = get_active_regions_from_cost_explorer()
    resource_regions, resource_status = get_active_regions_from_resource_explorer()
    config_regions, config_status = get_active_regions_from_config()
    
    print(f"Cost Explorer Status: {cost_status}")
    print(f"Resource Explorer Status: {resource_status}")
    print(f"AWS Config Status: {config_status}")
    
    all_active_regions = cost_regions.union(resource_regions).union(config_regions)
    
    print("\nRegions with active resources or billing:")
    print("-" * 50)
    
    if not all_active_regions:
        print("No active regions found or insufficient permissions.")
    else:
        for region in sorted(all_active_regions):
            print(region)
            
    print("\nSummary:")
    print(f"Total active regions found: {len(all_active_regions)}")
    print(f"Regions from Cost Explorer: {len(cost_regions)}")
    print(f"Regions from Resource Explorer: {len(resource_regions)}")
    print(f"Regions from AWS Config: {len(config_regions)}")

if __name__ == "__main__":
    main()
