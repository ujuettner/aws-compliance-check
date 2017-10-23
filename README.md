# aws-compliance-check

Performs some compliance checks on AWS EC2 instances and returns an output digestible by Nagios/Icinga2.

The Python script `aws_compliance_check.py` uses [Boto3](https://github.com/boto/boto3). You have to install it first before running the script.

The Go program uses the [AWS SDK for Go](https://aws.amazon.com/sdk-for-go/). To compile it, set GOPATH appropriately and perform the following steps:

```
cd $GOPATH
go get -u github.com/ujuettner/aws-compliance-check
go install github.com/ujuettner/aws-compliance-check
```

Both rely on a properly set up `~/.aws/credentials` and `~/.aws/config`, respectively.

### TODOs

* Enhance Go variant till feature parity with Python variant.
* Check Security Groups for dangerous rules.
