import json
import os

import boto3

client = boto3.client("sagemaker-runtime")

ENDPOINT_NAME = os.environ.get("ENDPOINT_NAME", None)


def proxy(event, context):
    print(event)
    if ENDPOINT_NAME is None:
        return {"error": "Environment variable `ENDPOINT_NAME` not defined"}
    try:
        body = json.loads(event["body"])
        print(body)

        sagemaker_response = client.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType="application/json",
            Accept="application/json",
            Body=json.dumps(body),
        )
        sagemaker_response = json.loads(sagemaker_response["Body"].read().decode("utf-8"))[0]

        print(sagemaker_response)
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": True,
            },
            "body": json.dumps({"data": sagemaker_response}),
        }
    except Exception as e:
        print(repr(e))
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": True,
            },
            "body": json.dumps({"error": repr(e)}),
        }
