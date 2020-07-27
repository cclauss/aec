import boto3
import pytest
from moto import mock_ec2
from moto.ec2 import ec2_backends
from moto.ec2.models import AMIS

from tools.ec2 import delete_image, describe, describe_images, launch, modify, share_image, start, stop, terminate


@pytest.fixture
def mock_aws_config():
    mock = mock_ec2()
    mock.start()
    region = "ap-southeast-2"

    return {
        "region": region,
        "additional_tags": {"Owner": "alice@testlab.io", "Project": "test project a"},
        "key_name": "test_key",
        "vpc": {
            "name": "test vpc",
            "subnet": next(ec2_backends[region].get_all_subnets()).id,
            "security_group": "default",
        },
        "iam_instance_profile_arn": "test_profile",
    }


def test_launch(mock_aws_config):
    instances = launch("alice", AMIS[0]["ami_id"], config=mock_aws_config)
    assert "amazonaws.com" in instances[0]["DnsName"]


def test_launch_multiple_security_groups(mock_aws_config):
    mock_aws_config["vpc"]["security_group"] = ["one", "two"]
    print(launch("alice", AMIS[0]["ami_id"], config=mock_aws_config))


def test_launch_without_instance_profile(mock_aws_config):
    del mock_aws_config["iam_instance_profile_arn"]
    print(launch("alice", AMIS[0]["ami_id"], config=mock_aws_config))


@pytest.mark.skip(reason="failing because of https://github.com/spulec/moto/pull/2651")
def test_launch_without_public_ip_address(mock_aws_config):
    mock_aws_config["vpc"]["associate_public_ip_address"] = False
    instances = launch("alice", AMIS[0]["ami_id"], config=mock_aws_config)
    assert "ec2.internal" in instances[0]["DnsName"]


def test_override_key_name(mock_aws_config):
    instances = launch("alice", AMIS[0]["ami_id"], key_name="magic-key", config=mock_aws_config)
    instance_id = instances[0]["InstanceId"]

    actual_key_name = describe_instance0(mock_aws_config["region"], instance_id)

    assert "magic-key" in actual_key_name["KeyName"]


def test_launch_has_userdata(mock_aws_config):
    print(
        launch(
            "test_userdata",
            AMIS[0]["ami_id"],
            userdata="config-example/userdata/amzn-install-docker.yaml",
            config=mock_aws_config,
        )
    )


def test_describe(mock_aws_config):
    launch("alice", AMIS[0]["ami_id"], config=mock_aws_config)
    launch("sam", AMIS[0]["ami_id"], config=mock_aws_config)

    instances = describe(config=mock_aws_config)
    print(instances)

    assert len(instances) == 2
    assert instances[0]["Name"] == "alice"
    assert instances[1]["Name"] == "sam"


def test_describe_instance_without_tags(mock_aws_config):
    # create instance without tags
    ec2_client = boto3.client("ec2", region_name=mock_aws_config["region"])
    ec2_client.run_instances(MaxCount=1, MinCount=1)

    instances = describe(config=mock_aws_config)
    print(instances)

    assert len(instances) == 1


def test_describe_by_name(mock_aws_config):
    launch("alice", AMIS[0]["ami_id"], config=mock_aws_config)

    instances = describe(name="alice", config=mock_aws_config)
    print(instances)

    assert len(instances) == 1
    assert instances[0]["Name"] == "alice"


def describe_instance0(region_name, instance_id):
    ec2_client = boto3.client("ec2", region_name=region_name)
    instances = ec2_client.describe_instances(InstanceIds=[instance_id])
    return instances["Reservations"][0]["Instances"][0]


def test_describe_images(mock_aws_config):
    # describe images defined by moto
    # see https://github.com/spulec/moto/blob/master/moto/ec2/resources/amis.json
    canonical_account_id = "099720109477"
    mock_aws_config["describe_images_owners"] = canonical_account_id
    images = describe_images(config=mock_aws_config)

    assert len(images) == 2
    assert images[0]["Name"] == "ubuntu/images/hvm-ssd/ubuntu-trusty-14.04-amd64-server-20170727"


def test_stop_start(mock_aws_config):
    launch("alice", AMIS[0]["ami_id"], config=mock_aws_config)

    stop(name="alice", config=mock_aws_config)

    start(name="alice", config=mock_aws_config)


def test_modify(mock_aws_config):
    launch("alice", AMIS[0]["ami_id"], config=mock_aws_config)

    instances = modify(name="alice", type="c5.2xlarge", config=mock_aws_config)

    assert len(instances) == 1
    assert instances[0]["Name"] == "alice"
    assert instances[0]["Type"] == "c5.2xlarge"


def test_delete_image(mock_aws_config):
    delete_image(AMIS[0]["ami_id"], config=mock_aws_config)


def test_terminate(mock_aws_config):
    launch("alice", AMIS[0]["ami_id"], config=mock_aws_config)

    response = terminate(name="alice", config=mock_aws_config)

    print(response)


def test_share_image(mock_aws_config):
    share_image(AMIS[0]["ami_id"], "123456789012", config=mock_aws_config)
