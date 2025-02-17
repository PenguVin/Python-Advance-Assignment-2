'''Q1. Write a python program using boto3 to list all available types of ec2 instances in each region. Make sure the instance type won’t repeat in a region. Put it in a csv with these columns.
Region, InstanceType
'''
import boto3
import csv
from typing import List, Dict

def get_all_regions() -> List[str]:
    """Get list of all AWS regions."""
    ec2_client = boto3.client('ec2')
    regions = [region['RegionName'] 
              for region in ec2_client.describe_regions()['Regions']]
    return regions

def get_instance_types(region: str) -> List[str]:
    try:
        ec2_client = boto3.client('ec2', region_name=region)
        paginator = ec2_client.get_paginator('describe_instance_type_offerings')
        instance_types = set()  
        
        for page in paginator.paginate(LocationType='region'):
            for offering in page['InstanceTypeOfferings']:
                instance_types.add(offering['InstanceType'])
                
        return sorted(list(instance_types))
    except Exception as e:
        print(f"Error getting instance types for region {region}: {str(e)}")
        return []

def main():
    regions = get_all_regions()
    
    with open('ec2_instance_types.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Region', 'InstanceType'])
        
        for region in regions:
            print(f"Processing region: {region}")
            instance_types = get_instance_types(region)
            
            for instance_type in instance_types:
                writer.writerow([region, instance_type])

if __name__ == "__main__":
    main()


