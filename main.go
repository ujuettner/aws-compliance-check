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

func main() {
	region := flag.String("region", "us-east-1", "Use given AWS region. Default: us-east-1")
	profile := flag.String("profile", "default", "Use given AWS profile. Default: default")
	flag.Parse()

	session, err := session.NewSession(&aws.Config{
		Region:      aws.String(*region),
		Credentials: credentials.NewSharedCredentials("", *profile),
	})
	if err != nil {
		fmt.Println("Error", err)
		os.Exit(1)
	}

	ec2 := ec2.New(session)
	result, err := ec2.DescribeInstances(nil)
	if err != nil {
		fmt.Println("Error", err)
		os.Exit(1)
	}
	fmt.Println("Success", result)
	fmt.Println("=== XXX ===")
	for _, reservation := range result.Reservations {
		for _, instance := range reservation.Instances {
			fmt.Println(*instance.InstanceId)
		}
	}

	os.Exit(0)
}
