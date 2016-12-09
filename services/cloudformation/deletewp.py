#!/usr/bin/env python
import os.path
import sys
import os
import boto3

def print_log(msg):
    print("CLIQR_EXTERNAL_SERVICE_LOG_MSG_START")
    print(msg)
    print("CLIQR_EXTERNAL_SERVICE_LOG_MSG_END")

def print_error(msg):
    print("CLIQR_EXTERNAL_SERVICE_ERR_MSG_START")
    print(msg)
    print("CLIQR_EXTERNAL_SERVICE_ERR_MSG_END")

def print_ext_service_result(msg):
    print("CLIQR_EXTERNAL_SERVICE_RESULT_START")
    print(msg)
    print("CLIQR_EXTERNAL_SERVICE_RESULT_END")


# cmd = sys.argv[1]


JOB_NAME = os.environ['parentJobName']

print_log("Job Name: " + str(JOB_NAME))
cft = boto3.client('cloudformation')
delete_cft = cft.delete_stack(StackName=JOB_NAME)
print_log(delete_cft)
