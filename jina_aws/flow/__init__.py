import copy

from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_iam as iam,
    Stack,
    CfnOutput,
    aws_autoscaling as autoscaling,
    aws_ecs_patterns as ecs_patterns,
)
from constructs import Construct
from jina import Flow as JinaFlow
from jina.helper import ArgNamespace
from jina.parsers import set_deployment_parser, set_gateway_parser
from jina.serve.networking import GrpcConnectionPool

"""
The Jina Flow containing the Gateway and Executors are mapped to a ECS Container running on EC2 instances.
"""


class JinaFlowStack(Stack):
    def __init__(self,
                 scope: Construct,
                 id: str,
                 jina_flow: JinaFlow,
                 cluster_name: str = 'MyCluster',
                 **kwargs
                 ) -> None:
        super().__init__(scope, id, **kwargs)

        # Create a VPC
        self.vpc_name = f'{cluster_name}_vpc'
        vpc = ec2.Vpc(
            self,
            self.vpc_name,
            max_azs=2,
            nat_gateways=1,
        )

        # Create an ECS cluster
        cluster_name = cluster_name
        cluster = ecs.Cluster(
            self,
            cluster_name,
            vpc=vpc,
        )

        asg = autoscaling.AutoScalingGroup(
            self, 'DefaultAutoScalingGroup',
            instance_type=ec2.InstanceType('t4.medium'),
            machine_image=ecs.EcsOptimizedImage.amazon_linux2(),
            vpc=vpc,
            min_capacity=1,
            max_capacity=10,
        )
        capacity_provider = ecs.AsgCapacityProvider(self, 'AsgCapacityProvider', auto_scaling_group=asg)
        cluster.add_asg_capacity_provider(capacity_provider)

        asg.connections.allow_from_any_ipv4(port_range=ec2.Port.tcp_range(32768, 65535),
                                            description='allow incoming traffic from ALB')

        # Create an IAM role for ECS task execution
        task_execution_role = iam.Role(
            self,
            'TaskExecutionRole',
            assumed_by=iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    'service-role/AmazonECSTaskExecutionRolePolicy'
                )
            ],
        )

        self.transform_gateway_to_ecs_service(cluster, jina_flow.gateway_args, task_execution_role)

        for node_name, deployment in jina_flow._deployment_nodes.items():
            self.transform_deployments_to_ecs_service(cluster, node_name, deployment, task_execution_role)

        # Output the ECS cluster name
        CfnOutput(
            self,
            'ClusterNameOutput',
            value=cluster.cluster_name,
        )

    def transform_gateway_to_ecs_service(self, cluster, gateway_args, task_execution_role):
        cargs = copy.copy(gateway_args)
        # Create a task definition
        task_definition = ecs.Ec2TaskDefinition(
            self,
            f'{cargs.name}_TaskDefinition',
            task_role=task_execution_role,
        )

        # Create a container definition
        taboo = {
            'uses_metas',
            'volumes',
            'uses_before',
            'uses_after',
            'workspace',
            'workspace_id',
            'noblock_on_start',
            'env',
        }
        non_defaults = ArgNamespace.get_non_defaults_args(
            cargs, set_gateway_parser(), taboo=taboo
        )
        _args = ArgNamespace.kwargs2list(non_defaults)
        container_definition = task_definition.add_container(
            cargs.name,
            image=ecs.ContainerImage.from_registry(cargs.uses or ''),
            memory_limit_mib=512,
            cpu=1,
            port_mappings=[
                {'containerPort': GrpcConnectionPool.K8S_PORT, 'hostPort': GrpcConnectionPool.K8S_PORT},
                {'containerPort': cargs.port_monitoring[0],
                 'hostPort': cargs.port_monitoring[0]}
            ],
            command=['jina'],
            entry_point=['gateway'] + _args,
            environment=cargs.env,

        )

        ecs_service = ecs_patterns.NetworkLoadBalancedEc2Service(
            self, f'{cargs.name}_Ec2Service',
            cluster=cluster,
            memory_limit_mib=512,
            task_definition=task_definition,
            desired_count=cargs.replicas,
            service_name=cargs.name,
        )

        if 'volumes' in cargs:
            # Create an EBS volume
            ebs_volume = ec2.Volume(
                self,
                f'{cargs.name}-ebs-volume',
                size=10,
            )

            # Mount the EBS volume to the container
            mount_path = cargs.volumes[0]
            container_definition.add_mount_points(
                ecs.MountPoint(
                    container_path=mount_path,
                    source_volume=ebs_volume.volume_id,
                    read_only=False,
                )
            )

        CfnOutput(
            self, f'{cargs.name}_LoadBalancerDNS',
            value='http://' + ecs_service.load_balancer.load_balancer_dns_name
        )

    def transform_deployments_to_ecs_service(self, cluster, node_name, deployment, task_execution_role):
        # Create a task definition
        task_definition = ecs.Ec2TaskDefinition(
            self,
            f'{node_name}_TaskDefinition',
            task_role=task_execution_role,
        )
        # Create a container definitions
        taboo = {
            'uses_metas',
            'volumes',
            'uses_before',
            'uses_after',
            'workspace',
            'workspace_id',
            'noblock_on_start',
            'env',
        }
        cargs = copy.copy(deployment.args)
        non_defaults = ArgNamespace.get_non_defaults_args(
            cargs, set_deployment_parser(), taboo=taboo
        )
        _args = ArgNamespace.kwargs2list(non_defaults)
        entry_point_sub_command = 'gateway' if node_name == 'gateway' else 'executor'
        container_definition = task_definition.add_container(
            deployment.args.name,
            image=ecs.ContainerImage.from_registry(deployment.args.uses),
            memory_limit_mib=512,
            cpu=1,
            port_mappings=[
                {'containerPort': GrpcConnectionPool.K8S_PORT, 'hostPort': GrpcConnectionPool.K8S_PORT},
                {'containerPort': deployment.args.port_monitoring,
                 'hostPort': deployment.args.port_monitoring}
            ],
            command=['jina'],
            entry_point=[entry_point_sub_command] + _args,
            environment=cargs.env,

        )
        if deployment.args.volumes:
            # Create an EBS volume
            ebs_volume = ec2.Volume(
                self,
                f'{node_name}-ebs-volume',
                size=10,
            )

            # Mount the EBS volume to the container
            mount_path = deployment.args.volumes[0]
            container_definition.add_mount_points(
                ecs.MountPoint(
                    container_path=mount_path,
                    source_volume=ebs_volume.volume_id,
                    read_only=False,
                )
            )
        ecs_service = ecs_patterns.NetworkLoadBalancedEc2Service(
            self, f'{node_name}_Ec2Service',
            cluster=cluster,
            memory_limit_mib=512,
            task_definition=task_definition,
            desired_count=deployment.args.replicas,
            service_name=node_name,
        )
        CfnOutput(
            self, f'{node_name}_LoadBalancerDNS',
            value='http://' + ecs_service.load_balancer.load_balancer_dns_name
        )


if '__name__' == '__main__':
    from aws_cdk import App

    app = App()
    JinaFlowStack(scope=app, id='JinaFlowStack',
                  # If you don't specify 'env', this stack will be environment-agnostic.
                  # Account/Region-dependent features and context lookups will not work,
                  # but a single synthesized template can be deployed anywhere.

                  # Uncomment the next line to specialize this stack for the AWS Account
                  # and Region that are implied by the current CLI configuration.

                  # env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),

                  # Uncomment the next line if you know exactly what Account and Region you
                  # want to deploy the stack to. */

                  # env=cdk.Environment(account='123456789012', region='us-east-1'),

                  # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
                  )
    app.synth()
