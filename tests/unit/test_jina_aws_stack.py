import aws_cdk as core
import aws_cdk.assertions as assertions

from jina_aws.jina_aws_stack import JinaAwsStack

# example tests. To run these tests, uncomment this file along with the example
# resource in jina_aws/jina_aws_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = JinaAwsStack(app, "jina-aws")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
