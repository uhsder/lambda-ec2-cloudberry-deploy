def lambda_handler(event, context):
    import boto3

    # Parametrs to change *DESIRED_TAG*, *DESIRED_TAG_VALUE*,


    #Searching for instances w CBL tag and Installed key and removing key on success
    ec2test = boto3.client('ec2')
    instances = ec2test.describe_instances(Filters=[{'Name': 'tag: *DESIRED_TAG*', 'Values': ['*DESIRED_TAG_value*']}])
    iamProfile = ec2test.describe_iam_instance_profile_associations()
    #Preparing two arrays for Windows and Linux instances
    idsWindows = []
    idsLinux = []
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
    #Tricky part cause only Windows instances have Platform property
            try:
                if instance['Platform'] == 'windows':
                    print ('Yes')
                    idsWindows.append(instance['InstanceId'])
            except KeyError:
                print ('No')
                idsLinux.append(instance['InstanceId'])
            print (idsWindows)
            print (idsLinux)
    print ("Changing tags for %d instances" % (len(idsWindows)+len(idsLinux)))
    #Removing CBL build from Windows based EC2s
    if not idsWindows:
        print("List of Windows instances to change is empty")
    else:
        ssm_client = boto3.client('ssm')
        response = ssm_client.send_command(
                InstanceIds=idsWindows,
                DocumentName="AWS-RunPowerShellScript",
                TimeoutSeconds = 240,
                Parameters={'commands': ['$inst_path=((Get-Process -Name Cloud.Backup.RM.Service).path | Split-Path)',
                                         'Start-Process $inst_path/uninst.exe /S'] }, )
        print(response['Command']['CommandId'])
        ec2 = boto3.resource('ec2')
        #Removing CBL tag
        ec2test.delete_tags(
                Resources=idsWindows,
                Tags=[
                    {
                        'Key': '*DESIRED_TAG*',
                        'Value': '*DESIRED_TAG_VALUE*'
                    }
                ]
            )
        print("Changed")
    #Removing CBL build from Linux based EC2s
    if not idsLinux:
        print("List of Linux instances to change is empty")
    else:
        ssm_client = boto3.client('ssm')
        response = ssm_client.send_command(
                InstanceIds=idsLinux,
                DocumentName='AWS-RunShellScript',
                TimeoutSeconds = 240,
                #This part done for particular product called "Backup ABC", in case there is no space in name you would only need path1 in both lines and remove path2
                Parameters={'commands': ['#!/usr/bin/env bash',
                                         'a=`pidof cbbRemoteManagement`',
                                         'path1=`sudo ls -l /proc/$a/exe | awk \'{ print $11 }\'`',
                                         'path2=`sudo ls -l /proc/$a/exe | awk \'{ print $12 }\'`',
                                         'pname=`rpm -qf $path1\ $path2`',
                                         'rpm -e $pname'] }, )
        print(response['Command']['CommandId'])
        ec2 = boto3.resource('ec2')
        #Removing CBL tag
        ec2test.delete_tags(
                Resources=idsLinux,
                Tags=[
                    {
                        'Key': '*DESIRED_TAG*',
                        'Value': '*DESIRED_TAG_VALUE*'
                    }
                ]
            )
        print("Changed")
    #Deassociating AllowSSM role from this instances
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            for i in iamProfile['IamInstanceProfileAssociations']:
                        if instance['InstanceId'] == i['InstanceId']:
                            response = ec2test.disassociate_iam_instance_profile(
                                AssociationId=i['AssociationId']
                            )