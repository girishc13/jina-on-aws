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
from jina import Deployment
from jina.helper import ArgNamespace
from jina.parsers import set_gateway_parser
from jina.serve.networking import GrpcConnectionPool


class JinaDeploymentStack(Stack):
    def __init__(self,
                 scope: Construct,
                 id: str,
                 jina_deployment: Deployment,
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
            instance_type=ec2.InstanceType('t2.micro'),
            machine_image=ecs.EcsOptimizedImage.amazon_linux2(),
            vpc=vpc,
            min_capacity=1,
            max_capacity=jina_deployment.args.replicas,
        )
        capacity_provider = ecs.AsgCapacityProvider(self, 'AsgCapacityProvider',
                                                    auto_scaling_group=asg
                                                    )
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

        # Create a task definition
        task_definition = ecs.Ec2TaskDefinition(
            self,
            'MyTaskDefinition',
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
        cargs = copy.copy(jina_deployment.args)
        non_defaults = ArgNamespace.get_non_defaults_args(
            cargs, set_gateway_parser(), taboo=taboo
        )
        _args = ArgNamespace.kwargs2list(non_defaults)
        container_definition = task_definition.add_container(
            jina_deployment.args.name,
            image=ecs.ContainerImage.from_registry(jina_deployment.args.uses),
            memory_limit_mib=512,
            cpu=1,
            port_mappings=[
                {'containerPort': GrpcConnectionPool.K8S_PORT, 'hostPort': GrpcConnectionPool.K8S_PORT},
                {'containerPort': jina_deployment.args.port_monitoring,
                 'hostPort': jina_deployment.args.port_monitoring}
            ],
            command=['jina'],
            entry_point=['executor'] + _args,
            environment=cargs.env,

        )

        ecs_service = ecs_patterns.NetworkLoadBalancedEc2Service(
            self, 'Ec2Service',
            cluster=cluster,
            memory_limit_mib=512,
            task_definition=task_definition,
            desired_count=jina_deployment.args.replicas,
            service_name='executor',
        )

        if jina_deployment.args.volumes:
            # Create an EBS volume
            ebs_volume = ec2.Volume(
                self,
                f'{id}-ebs-volume',
                size=10,
            )

            # Mount the EBS volume to the container
            mount_path = jina_deployment.args.volumes[0]
            container_definition.add_mount_points(
                ecs.MountPoint(
                    container_path=mount_path,
                    source_volume=ebs_volume.volume_id,
                    read_only=False,
                )
            )

        # Output the ECS cluster name
        CfnOutput(
            self,
            'ClusterNameOutput',
            value=cluster.cluster_name,
        )
        CfnOutput(
            self, 'LoadBalancerDNS',
            value='http://' + ecs_service.load_balancer.load_balancer_dns_name
        )


if '__name__' == '__main__':
    from aws_cdk import App

    app = App()
    JinaDeploymentStack(scope=app, id='JinaDeploymentStack',
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
