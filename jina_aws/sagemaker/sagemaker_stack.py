import os
from pathlib import Path

from aws_cdk import (
    aws_iam as iam,
    aws_lambda,
    aws_apigateway,
    Stack,
    Duration,
)
from constructs import Construct
from jina import Deployment as JinaDeployment

from jina_aws.sagemaker.sagemaker_construct import SageMakerEndpointConstruct

# policies based on https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-roles.html#sagemaker-roles-createmodel-perms
iam_sagemaker_actions = [
    "sagemaker:*",
    "ecr:GetDownloadUrlForLayer",
    "ecr:BatchGetImage",
    "ecr:BatchCheckLayerAvailability",
    "ecr:GetAuthorizationToken",
    "cloudwatch:PutMetricData",
    "cloudwatch:GetMetricData",
    "cloudwatch:GetMetricStatistics",
    "cloudwatch:ListMetrics",
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:DescribeLogStreams",
    "logs:PutLogEvents",
    "logs:GetLogEvents",
    "s3:CreateBucket",
    "s3:ListBucket",
    "s3:GetBucketLocation",
    "s3:GetObject",
    "s3:PutObject",
]


class JinaSageMakerStack(Stack):
    def __init__(self,
                 scope: Construct,
                 id: str,
                 jina_deployment: JinaDeployment,
                 instance_type: str = 'ml.m5.xlarge',
                 model_name: str = 'custom_inference',
                 endpoint_config_name: str = 'custom-inference-endpoint-config',
                 endpoint_name: str = 'custom-inference',
                 **kwargs
                 ) -> None:
        super().__init__(scope, id, **kwargs)

        # creates new iam role for sagemaker using `iam_sagemaker_actions` as permissions or uses provided arn
        execution_role = iam.Role(
            self, "sagemaker_execution_role", assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com")
        )
        execution_role.add_to_policy(iam.PolicyStatement(resources=["*"], actions=iam_sagemaker_actions))
        execution_role_arn = execution_role.role_arn

        endpoint = SageMakerEndpointConstruct(
            self,
            "SagemakerEndpoint",
            jina_deployment_args=jina_deployment.args,
            execution_role_arn=execution_role_arn,
            instance_type=instance_type,
            model_name=model_name,
            endpoint_config_name=endpoint_config_name,
            endpoint_name=endpoint_name,
        )

        # lambda function that will be exposed by the API Gateway
        lambda_handler_path = os.path.join(Path(__file__).absolute().parent, "lambda_src")
        # create function
        lambda_fn = aws_lambda.Function(
            self,
            "sm_invoke",
            code=aws_lambda.Code.from_asset(lambda_handler_path),
            handler="handler.proxy",
            timeout=Duration.seconds(60),
            runtime=aws_lambda.Runtime.PYTHON_3_10,
            environment={"ENDPOINT_NAME": endpoint.endpoint_name},
        )

        # add policy for invoking
        lambda_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "sagemaker:InvokeEndpoint",
                ],
                resources=[
                    f"arn:aws:sagemaker:{self.region}:{self.account}:endpoint/{endpoint.endpoint_name.lower()}",
                ],
            )
        )

        api = aws_apigateway.LambdaRestApi(self, "api_gateway", proxy=True, handler=lambda_fn)
