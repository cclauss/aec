import pytest
from moto import mock_ec2
from moto.ec2 import ec2_backends
from moto.ec2.models import AMIS

from tools.ec2 import launch, describe, stop


@pytest.fixture
def mock_aws_configs():
    mock = mock_ec2()
    mock.start()
    region = 'ap-southeast-2'

    return {"region": region,
            "amis": {"gami": AMIS[0]["ami_id"]},
            "key_name": "test_key",
            "security_group": "default",
            "subnet": next(ec2_backends[region].get_all_subnets()).id,
            "iam_instance_profile_arn": "test_profile"}


def test_launch(mock_aws_configs):
    print(launch("alice", "alice@testlab.io", config=mock_aws_configs))


def test_launch_has_userdata(mock_aws_configs):
    mock_aws_configs["userdata"] = {"gami": "conf/userdata/amzn-install-docker.yaml"}
    print(launch("userdata", "alice@testlab.io", config=mock_aws_configs))


def test_describe(mock_aws_configs):
    launch("alice", "alice@testlab.io", config=mock_aws_configs)
    launch("sam", "sam@testlab.io", config=mock_aws_configs)

    instances = describe(config=mock_aws_configs)
    print(instances)

    assert len(instances) == 2
    assert instances[0]["Name"] == "alice"
    assert instances[1]["Name"] == "sam"


def test_describe_by_name(mock_aws_configs):
    launch("alice", "alice@testlab.io", config=mock_aws_configs)

    instances = describe(name="alice", config=mock_aws_configs)
    print(instances)

    assert len(instances) == 1
    assert instances[0]["Name"] == "alice"


def test_stop(mock_aws_configs):
    launch("alice", "alice@testlab.io", config=mock_aws_configs)

    response = stop(name="alice", config=mock_aws_configs)

    print(response)
