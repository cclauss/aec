import os
from typing import List

import boto3
import pytest
from moto import mock_ec2
from moto.ec2 import ec2_backends
from moto.ec2.models import AMIS
from mypy_boto3_ec2.type_defs import TagTypeDef
from pytest_mock import MockFixture

from aec.command.ec2 import (
    create_key_pair,
    describe,
    instance_tags,
    launch,
    logs,
    modify,
    start,
    stop,
    terminate,
    volume_tags,
)


@pytest.fixture
def mock_aws_config():
    mock = mock_ec2()
    mock.start()
    region = "ap-southeast-2"

    return {
        "region": region,
        "key_name": "test_key",
        "vpc": {
            "name": "test vpc",
            "subnet": next(ec2_backends[region].get_all_subnets()).id,
            "security_group": "default",
        },
        "iam_instance_profile_arn": "test_profile",
    }


ami_id = AMIS[0]["ami_id"]


def test_launch(mock_aws_config):
    instances = launch(mock_aws_config, "alice", ami=ami_id)
    assert "amazonaws.com" in instances[0]["DnsName"]

    ec2_client = boto3.client("ec2", region_name=mock_aws_config["region"])
    volumes = ec2_client.describe_volumes()
    assert volumes["Volumes"][0]["Size"] == 15


def test_launch_template(mock_aws_config):
    ec2_client = boto3.client("ec2", region_name=mock_aws_config["region"])
    ec2_client.create_launch_template(
        LaunchTemplateName="launchie",
        LaunchTemplateData={
            "ImageId": ami_id,
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/sda1",
                    "Ebs": {
                        "VolumeSize": 20,
                        "DeleteOnTermination": True,
                        "VolumeType": "gp3",
                        "Encrypted": True,
                    },
                }
            ],
        },
    )

    instances = launch(mock_aws_config, "alice", template="launchie")
    assert "amazonaws.com" in instances[0]["DnsName"]

    # moto doesn't yet support launching from a template so
    # this check is disabled until https://github.com/spulec/moto/issues/2003 is implemented

    # ec2_client = boto3.client("ec2", region_name=mock_aws_config["region"])
    # volumes = ec2_client.describe_volumes()
    # assert volumes["Volumes"][0]["Size"] == 20


def test_launch_multiple_security_groups(mock_aws_config):
    mock_aws_config["vpc"]["security_group"] = ["one", "two"]
    print(launch(mock_aws_config, "alice", ami_id))


def test_launch_without_instance_profile(mock_aws_config):
    del mock_aws_config["iam_instance_profile_arn"]
    print(launch(mock_aws_config, "alice", ami_id))


def test_launch_no_region_specified(mock_aws_config):
    del mock_aws_config["region"]
    os.environ["AWS_DEFAULT_REGION"] = "ap-southeast-2"
    instances = launch(mock_aws_config, "alice", ami_id)
    assert "amazonaws.com" in instances[0]["DnsName"]


@pytest.mark.skip(reason="failing because of https://github.com/spulec/moto/issues/2762")
def test_launch_without_public_ip_address(mock_aws_config):
    mock_aws_config["vpc"]["associate_public_ip_address"] = False
    instances = launch(mock_aws_config, "alice", ami_id)
    assert "ec2.internal" in instances[0]["DnsName"]


def test_launch_with_ami_match_string(mock_aws_config):
    instances = launch(mock_aws_config, "alice", ami="ubuntu1604")
    assert "amazonaws.com" in instances[0]["DnsName"]


def test_override_key_name(mock_aws_config):
    instances = launch(mock_aws_config, "alice", ami_id, key_name="magic-key")
    instance_id = instances[0]["InstanceId"]

    instance = describe_instance0(mock_aws_config["region"], instance_id)

    assert "magic-key" in instance["KeyName"]


def test_override_volume_size(mock_aws_config):
    launch(mock_aws_config, "alice", ami=ami_id, volume_size=66)

    ec2_client = boto3.client("ec2", region_name=mock_aws_config["region"])
    volumes = ec2_client.describe_volumes()
    assert volumes["Volumes"][0]["Size"] == 66


def test_config_override_volume_size(mock_aws_config):
    mock_aws_config["volume_size"] = 77
    launch(mock_aws_config, "alice", ami=ami_id)

    ec2_client = boto3.client("ec2", region_name=mock_aws_config["region"])
    volumes = ec2_client.describe_volumes()
    assert volumes["Volumes"][0]["Size"] == 77


def test_launch_has_userdata(mock_aws_config):
    print(
        launch(
            mock_aws_config,
            "test_userdata",
            ami_id,
            userdata="src/aec/config-example/userdata/amzn-install-docker.yaml",
        )
    )


def test_describe(mock_aws_config):
    launch(mock_aws_config, "alice", ami_id)
    launch(mock_aws_config, "sam", ami_id)

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
    launch(mock_aws_config, "alice", ami_id)
    launch(mock_aws_config, "alex", ami_id)

    instances = describe(config=mock_aws_config, name="alice")

    assert len(instances) == 1
    assert instances[0]["Name"] == "alice"


def test_describe_by_name_match(mock_aws_config):
    launch(mock_aws_config, "alice", ami_id)
    launch(mock_aws_config, "alex", ami_id)

    instances = describe(config=mock_aws_config, name_match="lic")

    assert len(instances) == 1
    assert instances[0]["Name"] == "alice"


def test_describe_terminated(mock_aws_config):
    launch(mock_aws_config, "alice", ami_id)
    launch(mock_aws_config, "sam", ami_id)
    terminate(mock_aws_config, "sam")

    # by default don't show terminated instances
    instances = describe(config=mock_aws_config)
    assert len(instances) == 1
    assert instances[0]["Name"] == "alice"

    # when requested, show terminated instances
    instances = describe(config=mock_aws_config, include_terminated=True)
    assert len(instances) == 2


def test_describe_running_only(mock_aws_config):
    launch(mock_aws_config, "alice", ami_id)
    launch(mock_aws_config, "sam", ami_id)
    stop(mock_aws_config, "sam")

    # show only running instances
    instances = describe(config=mock_aws_config, show_running_only=True)
    assert len(instances) == 1
    assert instances[0]["Name"] == "alice"


def test_describe_instance_id(mock_aws_config):
    instances = launch(mock_aws_config, "alice", ami_id)
    instance_id = instances[0]["InstanceId"]

    instances = describe(config=mock_aws_config, name=instance_id)
    assert len(instances) == 1
    assert instances[0]["Name"] == "alice"


def test_describe_sort_by(mock_aws_config):
    launch(mock_aws_config, "sam", ami_id)
    launch(mock_aws_config, "alice", ami_id)

    instances = describe(config=mock_aws_config, sort_by="LaunchTime")
    print(instances)

    assert len(instances) == 2
    assert instances[0]["Name"] == "sam"
    assert instances[1]["Name"] == "alice"


def describe_instance0(region_name, instance_id):
    ec2_client = boto3.client("ec2", region_name=region_name)
    instances = ec2_client.describe_instances(InstanceIds=[instance_id])
    return instances["Reservations"][0]["Instances"][0]


def test_tags(mock_aws_config):
    mock_aws_config["additional_tags"] = {"Owner": "alice@testlab.io", "Project": "top secret"}
    launch(mock_aws_config, "alice", ami_id)

    instances = instance_tags(config=mock_aws_config)

    assert len(instances) == 1
    assert instances[0]["Tags"] == "Name=alice, Owner=alice@testlab.io, Project=top secret"

    instances = instance_tags(config=mock_aws_config, keys=["Owner", "Project"])

    assert len(instances) == 1
    assert instances[0]["Tag: Owner"] == "alice@testlab.io"
    assert instances[0]["Tag: Project"] == "top secret"


def test_tags_volume(mock_aws_config):
    ec2_client = boto3.client("ec2", region_name=mock_aws_config["region"])

    tags: List[TagTypeDef] = [{"Key": "Name", "Value": "Mr Snuffleupagus"}, {"Key": "Best Friend", "Value": "Big Bird"}]
    ec2_client.create_volume(
        AvailabilityZone="us-east-1a", Size=10, TagSpecifications=[{"ResourceType": "volume", "Tags": tags}]
    )

    volumes = volume_tags(config=mock_aws_config)

    assert len(volumes) == 1
    assert volumes[0]["Tags"] == "Name=Mr Snuffleupagus, Best Friend=Big Bird"

    volumes = volume_tags(config=mock_aws_config, keys=["Name", "Best Friend"])

    assert len(volumes) == 1
    assert volumes[0]["Tag: Name"] == "Mr Snuffleupagus"
    assert volumes[0]["Tag: Best Friend"] == "Big Bird"


def test_tags_filter(mock_aws_config):
    launch(mock_aws_config, "alice", ami_id)
    launch(mock_aws_config, "alex", ami_id)

    instances = instance_tags(config=mock_aws_config, name_match="lic")

    assert len(instances) == 1
    assert instances[0]["Tags"] == "Name=alice"


def test_stop_start(mock_aws_config):
    launch(mock_aws_config, "alice", ami_id)

    stop(mock_aws_config, name="alice")

    start(mock_aws_config, name="alice")


def test_modify(mock_aws_config):
    launch(mock_aws_config, "alice", ami_id)

    instances = modify(name="alice", type="c5.2xlarge", config=mock_aws_config)

    instance = describe_instance0(mock_aws_config["region"], instances[0]["InstanceId"])

    assert instance["InstanceType"] == "c5.2xlarge"
    assert instance["EbsOptimized"] is True

    instances = modify(name="alice", type="t2.medium", config=mock_aws_config)

    instance = describe_instance0(mock_aws_config["region"], instances[0]["InstanceId"])

    assert instance["InstanceType"] == "t2.medium"
    assert instance["EbsOptimized"] is False


def test_terminate(mock_aws_config):
    launch(mock_aws_config, "alice", ami_id)

    terminate(config=mock_aws_config, name="alice")


def test_logs(mock_aws_config):
    launch(mock_aws_config, "alice", ami_id)

    logs(config=mock_aws_config, name="alice")


def test_ebs_encrypted_by_default(mock_aws_config):
    ec2_client = boto3.client("ec2", region_name=mock_aws_config["region"])
    launch(mock_aws_config, "alice", ami=ami_id)
    volumes = ec2_client.describe_volumes()
    assert volumes["Volumes"][0]["Encrypted"] is True
    assert volumes["Volumes"][0]["KmsKeyId"]


def test_ebs_encrypt_with_kms(mock_aws_config):
    mock_aws_config["kms_key_id"] = "arn:aws:kms:ap-southeast-2:123456789012:key/abcdef"
    ec2_client = boto3.client("ec2", region_name=mock_aws_config["region"])
    launch(mock_aws_config, "alice", ami_id)
    volumes = ec2_client.describe_volumes()
    assert volumes["Volumes"][0]["Encrypted"] is True
    assert volumes["Volumes"][0]["KmsKeyId"] == "arn:aws:kms:ap-southeast-2:123456789012:key/abcdef"


def test_create_key_pair(mock_aws_config, mocker: MockFixture):
    mocked_file = mocker.patch("aec.command.ec2.open", mocker.mock_open())
    mocked_chmod = mocker.patch("os.chmod")

    create_key_pair(mock_aws_config, "test-key", "/tmp/test-file")

    mocked_file.assert_called_once_with("/tmp/test-file", "x")

    (private_key,) = mocked_file().write.call_args[0]
    assert private_key.startswith("-----BEGIN RSA PRIVATE KEY-----")
    mocked_chmod.assert_called_once()
