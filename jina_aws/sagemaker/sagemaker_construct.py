# For consistency with other languages, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
import copy
from typing import Any, Dict

from aws_cdk import aws_sagemaker
from constructs import Construct

"""
The Jina custom Gateway from a Jina Deployment is mapped to a SageMaker EndpointConstruct.
The Gateway is represented as the SageMaker model which is then exposed by the EndpointConstruct.
"""


class SageMakerEndpointConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        jina_deployment_args: Dict[str, Any],
        execution_role_arn: str,
        instance_type: str,
        model_name: str,
        endpoint_config_name: str,
        endpoint_name: str,
    ) -> None:
        super().__init__(scope, construct_id)
        cargs = copy.copy(jina_deployment_args)

        # defines and creates container configuration for deployment
        container = aws_sagemaker.CfnModel.ContainerDefinitionProperty(environment=cargs.env, image=cargs.uses)

        # creates SageMaker Model Instance
        model = aws_sagemaker.CfnModel(
            self,
            model_name,
            execution_role_arn=execution_role_arn,
            primary_container=container,
            model_name=model_name,
        )

        # Creates SageMaker Endpoint configurations
        endpoint_configuration = aws_sagemaker.CfnEndpointConfig(
            self,
            endpoint_config_name,
            endpoint_config_name=endpoint_config_name,
            production_variants=[
                aws_sagemaker.CfnEndpointConfig.ProductionVariantProperty(
                    initial_instance_count=1,
                    instance_type=instance_type,
                    model_name=model.model_name,
                    initial_variant_weight=1.0,
                    variant_name=model.model_name,
                )
            ],
        )
        # Creates Real-Time Endpoint
        endpoint = aws_sagemaker.CfnEndpoint(
            self,
            endpoint_name,
            endpoint_name=endpoint_name,
            endpoint_config_name=endpoint_configuration.endpoint_config_name,
        )

        # adds depends on for different resources
        endpoint_configuration.node.add_dependency(model)
        endpoint.node.add_dependency(endpoint_configuration)

        # construct export values
        self.endpoint_name = endpoint.endpoint_name
