// Checks running EC2 instances for compliance.
package main

import (
	"fmt"
	"os"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/credentials"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/ec2"
	flag "github.com/spf13/pflag"
)

var (
	verbose *bool
	ec2Svc  *ec2.EC2
)

// Parse command-line flags and initialize AWS session and EC2 service.
func init() {
	region := flag.StringP("region", "r", "us-east-1", "Use given AWS region. Default: us-east-1")
	profile := flag.StringP("profile", "p", "default", "Use given AWS profile. Default: default")
	verbose = flag.BoolP("verbose", "v", false, "Be verbose. Default: false")
	flag.Parse()

	session, err := session.NewSession(&aws.Config{
		Region:      aws.String(*region),
		Credentials: credentials.NewSharedCredentials("", *profile),
	})
	if err != nil {
		fmt.Println("Error", err)
		os.Exit(1)
	}

	ec2Svc = ec2.New(session)
}

// Check, whether a Name tag is set with a meaningful value for the given EC2 instance.
func nameTagSet(instance ec2.Instance) bool {
	nameTagSet := false

	for _, tag := range instance.Tags {
		if *tag.Key == "Name" && tag.Value != nil && *tag.Value != "" {
			nameTagSet = true
		}
	}

	return nameTagSet
}

// Check, whether all attached volumes are encrypted for the given EC2 instance.
// If checkRootVolume is set to false, unencrypted root volumes are considered as ok.
func allVolumesEncrypted(instance ec2.Instance, checkRootVolume bool) bool {
	describeVolumesInput := &ec2.DescribeVolumesInput{
		Filters: []*ec2.Filter{
			{
				Name: aws.String("attachment.instance-id"),
				Values: []*string{
					aws.String(*instance.InstanceId),
				},
			},
			{
				Name: aws.String("encrypted"),
				Values: []*string{
					aws.String("false"),
				},
			},
		},
	}
	volumes, err := ec2Svc.DescribeVolumes(describeVolumesInput)
	if err != nil {
		fmt.Println("Error", err)
	}
	if *verbose {
		fmt.Println(volumes)
	}

	if len(volumes.Volumes) > 0 {
		if checkRootVolume {
			return false
		}
		if len(volumes.Volumes) == 1 && *volumes.Volumes[0].VolumeId == *instance.BlockDeviceMappings[0].Ebs.VolumeId {
			return true
		}
		return false
	}

	return true
}

func main() {
	result, err := ec2Svc.DescribeInstances(nil)
	if err != nil {
		fmt.Println("Error", err)
		os.Exit(1)
	}
	if *verbose {
		fmt.Println("Success", result)
		fmt.Println("=== XXX ===")
	}
	for _, reservation := range result.Reservations {
		for _, instance := range reservation.Instances {
			fmt.Println(*instance.InstanceId, nameTagSet(*instance), allVolumesEncrypted(*instance, true), allVolumesEncrypted(*instance, false))
		}
	}

	os.Exit(0)
}
