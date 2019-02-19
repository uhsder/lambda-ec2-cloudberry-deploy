def lambda_handler(event, context):
    from urllib.parse import urlparse
    from posixpath import basename, dirname
    from collections import defaultdict
    import boto3
    from botocore.vendored import requests
    import json

    # Parametrs to change *YOUR_CBL_TOKEN*, *DESIRED_TAG*, *ROLE_ARN*, *ROLE_NAME*, *LOGIN*, *PASSWORD*, *INSTALLED_TAG*, *INSTALLED_TAG_VALUE*

    #Getting download links and filenames for future
    listAvailableBuilds = requests.get('https://api.mspbackups.com/api/Builds', headers = {"Accept" : "application/json", "Authorization" : *YOUR_CBL_TOKEN*})
    print ("Builds: " + str(listAvailableBuilds.status_code) + "\n")
    getJsonData = listAvailableBuilds.json()
    for i in range (0, len (getJsonData)):
        #Windows
        if getJsonData[i]['Type']=='Windows':
            dLinkWindows = getJsonData[i]['DownloadLink']
            print (dLinkWindows)
            winFileName = basename((urlparse(dLinkWindows)).path)
            print (winFileName)
        #Linux
        if getJsonData[i]['Type']=='Red Hat, Fedora, CentOS, SUSE, Oracle Linux':
            dLinkLinux = getJsonData[i]['DownloadLink']
            print (dLinkLinux)
            linFileName = basename((urlparse(dLinkLinux)).path)
            print (linFileName)
            
    #Searching for instances w CBL tag and True key and changing key to Installed on success
    ec2c = boto3.client('ec2')
    ec2r = boto3.resource('ec2')
    instances = ec2c.describe_instances(Filters=[{'Name': 'tag: *DESIRED_TAG*', 'Values': ['*DESIRED_TAG_value*']}])
    #Preparing two arrays for Windows and Linux instances
    idsWindows = []
    idsLinux = []
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            #Attaching AllowSSM policy to every instance that got tag before splitting them into two arrays (no checks here, uninstall lambda shoud deattach AllowSSM role)
            response = ec2c.associate_iam_instance_profile(
            IamInstanceProfile={
                'Arn': *ROLE_ARN*,
                'Name': *ROLE_NAME*
            },
            InstanceId = instance['InstanceId']
            )
            #Tricky part, cause only Windows instances have Platform property
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
    #Installing CBL biuld on Windows based EC2s
    if not idsWindows:
        print("List of Windows instances to change is empty")
    else:
        ssm_client = boto3.client('ssm')
        response = ssm_client.send_command(
                InstanceIds=idsWindows,
                DocumentName="AWS-RunPowerShellScript",
                TimeoutSeconds = 240,
                Parameters={'commands': ['Invoke-WebRequest -outfile C:/'+winFileName+ ' -Uri ' + dLinkWindows,
                                         'start-process -FilePath C:/'+winFileName+ ' -ArgumentList /S -Wait','Remove-Item C:/'+winFileName,
                                         '$path_to_cbb=((Get-Process -Name Cloud.Backup.RM.Service).path | Split-Path)+"/"+"cbb.exe"',
                                         '$reg_args="addAccount -e *LOGIN* -p *PASSWORD*"',
                                         'start-process -FilePath "$path_to_cbb" -ArgumentList $reg_args'] }, )
        print(response['Command']['CommandId'])
        ec2r.create_tags(
                Resources=idsWindows,
                Tags=[
                    {
                        'Key': 'CBL',
                        'Value': 'Installed'
                    }
                ]
            )
        print("Changed")
    #Installing CBL biuld on Linux based EC2s
    if not idsLinux:
        print("List of Linux instances to change is empty")
    else:
        ssm_client = boto3.client('ssm')
        response = ssm_client.send_command(
                InstanceIds=idsLinux,
                DocumentName='AWS-RunShellScript',
                TimeoutSeconds = 240,
                Parameters={'commands': ['#!/usr/bin/env bash','sudo su','curl -o /tmp/'+linFileName+' '+dLinkLinux, 'rpm -i /tmp/'+linFileName, 'sudo rm /tmp/'+linFileName] }, )
        print(response['Command']['CommandId'])
        ec2r.create_tags(
                Resources=idsLinux,
                Tags=[
                    {
                        'Key': '*INSTALLED_TAG*',
                        'Value': '*INSTALLED_TAG_VALUE*'
                    }
                ]
            )
        print("Changed")