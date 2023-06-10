# Welcome to your CDK Python project!

This is a blank project for CDK development with Python.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project. The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory. To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Useful commands

* `cdk ls`          list all stacks in the app
* `cdk synth`       emits the synthesized CloudFormation template
* `cdk deploy`      deploy this stack to your default AWS account/region
* `cdk diff`        compare deployed stack with current state
* `cdk docs`        open CDK documentation

Enjoy!

# Jina Deployment (work in progress)

Transform a `Deployment` which uses a Jina custom Gateway to an ECS deployment running on EC2.

[JinaDeploymentStack](jina_aws/deployment/__init__.py)
[Jina Deployment CDK App](deployment.py)

Synthesize the CloudFormation template:

```shell
cdk synth --app ./deployment.py
```

# Jina SageMaker (work in progress)

Transform a `Deployment` which uses a Jina custom Gateway to a SageMaker inference deployment that is exposed by an API
Gateway which triggers a lambda function on the inference endpoint.

[JinaSageMakerStack](jina_aws/sagemaker/sagemaker_stack.py)
[Jina SageMaker CDK App](sagemaker.py)

Synthesize the CloudFormation template:

```shell
cdk synth --app ./sagemaker.py
```

# Jina Flow (work in progress)

Transform a `Flow` to an ECS deployment running on EC2. Each Executor is mapped to a EC2 TaskDefinition with its own
network load balancer.

[JinaFlowStack](jina_aws/flow/__init__.py)
[Jina Flow CDK App](flow.py)

Synthesize the CloudFormation template:

```shell
cdk synth --app ./flow.py
```
