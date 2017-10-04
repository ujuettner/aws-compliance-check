// Checks running EC2 instances for compliance.
package main

import (
	"flag"
	"fmt"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/credentials"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/ec2"
	"os"
)

var (
	verbose *bool
	ec2Svc  *ec2.EC2
)

// Parse command-line flags and initialize AWS session and EC2 service.
func init() {
	region := flag.String("region", "us-east-1", "Use given AWS region. Default: us-east-1")
	profile := flag.String("profile", "default", "Use given AWS profile. Default: default")
	verbose = flag.Bool("verbose", false, "Be verbose. Default: false")
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
func name_tag_set(instance ec2.Instance) bool {
	name_tag_set := false

	for _, tag := range instance.Tags {
		if *tag.Key == "Name" && tag.Value != nil && *tag.Value != "" {
			name_tag_set = true
		}
	}

	return name_tag_set
}

// Check, whether all attached volumes are encrypted for the given EC2 instance.
// If checkRootVolume is set to false, unencrypted root volumes are considered as ok.
func all_volumes_encrypted(instance ec2.Instance, checkRootVolume bool) bool {
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
		} else {
			if len(volumes.Volumes) == 1 && *volumes.Volumes[0].VolumeId == *instance.BlockDeviceMappings[0].Ebs.VolumeId {
				return true
			} else {
				return false
			}
		}
	} else {
		return true
	}
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
			fmt.Println(*instance.InstanceId, name_tag_set(*instance), all_volumes_encrypted(*instance, true), all_volumes_encrypted(*instance, false))
		}
	}

	os.Exit(0)
}
