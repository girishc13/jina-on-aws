from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    core,
)


class CustomECSClusterStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, vpc_name="MyVPC", cluster_name="MyCluster", **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create a VPC
        self.vpc_name = vpc_name
        vpc = ec2.Vpc(
            self,
            self.vpc_name,
            max_azs=2,
            nat_gateways=1,
        )

        # Create an ECS cluster
        self.cluster_name = cluster_name
        cluster = ecs.Cluster(
            self,
            self.cluster_name,
            vpc=vpc,
        )

        # Output the ECS cluster name
        core.CfnOutput(
            self,
            "ClusterNameOutput",
            value=cluster.cluster_name,
        )
