import boto3
import csv
from typing import List, Dict, Any
from datetime import datetime

class AWSSecurityAuditor:
    def __init__(self):
        self.iam = boto3.client('iam')
        self.ec2 = boto3.client('ec2')
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def check_iam_roles_permissions(self) -> None:
        """Check IAM roles for overly permissive permissions."""
        try:
            with open(f'iam_roles_audit_{self.timestamp}.csv', 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['IAMRoleName', 'PolicyName'])
                
                paginator = self.iam.get_paginator('list_roles')
                for page in paginator.paginate():
                    for role in page['Roles']:
                        role_name = role['RoleName']
                        
                        # Check attached managed policies
                        attached_policies = self.iam.list_attached_role_policies(RoleName=role_name)
                        for policy in attached_policies['AttachedPolicies']:
                            if self._is_overly_permissive_policy(policy['PolicyArn']):
                                writer.writerow([role_name, policy['PolicyName']])
                        
                        # Check inline policies
                        inline_policies = self.iam.list_role_policies(RoleName=role_name)
                        for policy_name in inline_policies['PolicyNames']:
                            policy = self.iam.get_role_policy(
                                RoleName=role_name,
                                PolicyName=policy_name
                            )
                            if self._is_overly_permissive_inline_policy(policy):
                                writer.writerow([role_name, policy_name])
                                
            print(f"IAM roles audit completed. Results saved to iam_roles_audit_{self.timestamp}.csv")
        except Exception as e:
            print(f"Error checking IAM roles: {str(e)}")

    def _is_overly_permissive_policy(self, policy_arn: str) -> bool:
        """Check if a managed policy is overly permissive."""
        try:
            policy = self.iam.get_policy(PolicyArn=policy_arn)
            policy_version = self.iam.get_policy_version(
                PolicyArn=policy_arn,
                VersionId=policy['Policy']['DefaultVersionId']
            )
            
            # Check for AdministratorAccess or similar overly permissive policies
            for statement in policy_version['PolicyVersion']['Document']['Statement']:
                if (statement.get('Effect') == 'Allow' and 
                    statement.get('Action') == '*' and 
                    statement.get('Resource') == '*'):
                    return True
            return False
        except Exception:
            return False

    def _is_overly_permissive_inline_policy(self, policy: Dict) -> bool:
        """Check if an inline policy is overly permissive."""
        for statement in policy['PolicyDocument']['Statement']:
            if (statement.get('Effect') == 'Allow' and 
                statement.get('Action') == '*' and 
                statement.get('Resource') == '*'):
                return True
        return False

    def check_mfa_status(self) -> None:
        """Check MFA status for all IAM users."""
        try:
            with open(f'mfa_status_{self.timestamp}.csv', 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['IAMUserName', 'MFAEnabled'])
                
                paginator = self.iam.get_paginator('list_users')
                for page in paginator.paginate():
                    for user in page['Users']:
                        mfa_devices = self.iam.list_mfa_devices(UserName=user['UserName'])
                        mfa_enabled = len(mfa_devices['MFADevices']) > 0
                        writer.writerow([user['UserName'], mfa_enabled])
                        
            print(f"MFA status check completed. Results saved to mfa_status_{self.timestamp}.csv")
        except Exception as e:
            print(f"Error checking MFA status: {str(e)}")

    def check_security_groups(self) -> None:
        """Check security groups for public access."""
        try:
            with open(f'security_groups_audit_{self.timestamp}.csv', 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['SGName', 'Port', 'AllowedIP'])
                
                security_groups = self.ec2.describe_security_groups()
                sensitive_ports = [22, 80, 443, 3306, 1433, 5432]  # SSH, HTTP, HTTPS, MySQL, MSSQL, PostgreSQL
                
                for sg in security_groups['SecurityGroups']:
                    for rule in sg['IpPermissions']:
                        # Check if port is in sensitive list
                        from_port = rule.get('FromPort', 0)
                        to_port = rule.get('ToPort', 0)
                        
                        for ip_range in rule.get('IpRanges', []):
                            cidr = ip_range.get('CidrIp', '')
                            if cidr == '0.0.0.0/0' and (from_port in sensitive_ports or to_port in sensitive_ports):
                                writer.writerow([sg['GroupName'], f"{from_port}-{to_port}", cidr])
                                
            print(f"Security groups audit completed. Results saved to security_groups_audit_{self.timestamp}.csv")
        except Exception as e:
            print(f"Error checking security groups: {str(e)}")

    def check_unused_key_pairs(self) -> None:
        """Check for unused EC2 key pairs."""
        try:
            key_pairs = {key['KeyName']: False for key in self.ec2.describe_key_pairs()['KeyPairs']}
            
            # Check which key pairs are in use
            instances = self.ec2.describe_instances()
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    if 'KeyName' in instance:
                        key_pairs[instance['KeyName']] = True
            
            # Write unused key pairs to CSV
            with open(f'unused_key_pairs_{self.timestamp}.csv', 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['KeyPairName', 'InUse'])
                
                for key_name, in_use in key_pairs.items():
                    writer.writerow([key_name, in_use])
                    
            print(f"Key pairs audit completed. Results saved to unused_key_pairs_{self.timestamp}.csv")
        except Exception as e:
            print(f"Error checking key pairs: {str(e)}")

def main():
    auditor = AWSSecurityAuditor()
    
    print("Starting AWS Security Audit...")
    print("=" * 50)
    
    print("\nChecking IAM roles permissions...")
    auditor.check_iam_roles_permissions()
    
    print("\nChecking MFA status...")
    auditor.check_mfa_status()
    
    print("\nChecking security groups...")
    auditor.check_security_groups()
    
    print("\nChecking unused key pairs...")
    auditor.check_unused_key_pairs()
    
    print("\nAudit complete. Please check the CSV files for detailed results.")

if __name__ == "__main__":
    main()
