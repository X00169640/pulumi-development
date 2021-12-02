import pulumi
import pulumi_aws as aws

#VPC vars
vpc_cidr_block = "10.0.0.0/16"

#subnet vars
public_subnets = {
  "eu-west-1a": "10.0.0.0/24",
  "eu-west-1b": "10.0.1.0/24"
}

private_subnets = {
  "eu-west-1a": "10.0.101.0/24",
  "eu-west-1b": "10.0.102.0/24"
}

database_subnets = {
  "eu-west-1a": "10.0.201.0/24",
  "eu-west-1b": "10.0.202.0/24"
}

#az vars
availability_zones = [
  "eu-west-1a",
  "eu-west-1b"
]

conf = pulumi.Config()
db_username = conf.get("db_username")
db_password = conf.get("db_password")

#Create keypair to connect to webhosts
keypair = aws.ec2.KeyPair("keypair", 
    public_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCwS/sf75LjdVHcSkiTY8Ixvk9fMCrf72xTsmtgkqmFpW3akKYz+UGrPojNaNPqNLbiQ+G3MRwnKRIH5xu1CgRct7knpE0cIEjv4ObcvcX0FvvDYMh+fyXqLy4ko7V4pPFPpzHxB0HwFTDOGGvvYHA6L2NqiSpDkiK3bM+525A/pyR8+Y72xxdRXcamrIUEkHSNJxy2G/xElEczBa8Pz+4Kakj9i4/T9SUUI6CHByjn4SZQsMvGzYzCv0uMZwe5qsjE4gnBVSz89Y6yJr0QHzb6y/NKkshivnniMz5JikfcBtbnEPlkt4jNes7c3VnY3//+4tAEo4Ix3tCZqsmdwPLT diarmaid@developmen"
    )


# Define VPC
main = aws.ec2.Vpc("main",
    cidr_block=vpc_cidr_block,
    tags={
        "Name": "aws-terraform-vpc",
    })
# Internet Gateway
internet_gateway = aws.ec2.InternetGateway("internet-gateway",
    vpc_id=main.id,
    tags={
        "Name": "aws-terraform-internet-gateway",
    })
# Define Public Subnets
public_subnet = {}
for key,value in public_subnets.items():
    public_subnet.update({ key: aws.ec2.Subnet("publicSubnet-" + key,
        vpc_id=main.id,
        availability_zone=key,
        cidr_block=value,
        tags={
            "Name": "aws-pulumi-public-subnet-" + key,
        })})


# Define Private Subnets
private_subnet = {}
for key,value in private_subnets.items():
    private_subnet.update({ key: aws.ec2.Subnet("privateSubnet-" + key,
        vpc_id=main.id,
        availability_zone=key,
        cidr_block=value,
        tags={
            "Name": "aws-pulumi-private-subnet-" + key,
        })})

# Define database Subnets
database_subnet = {}
for key,value in database_subnets.items():
    database_subnet.update({ key: aws.ec2.Subnet("databaseSubnet-" + key,
        vpc_id=main.id,
        availability_zone=key,
        cidr_block=value,
        tags={
            "Name": "aws-pulumi-database-subnet-" + key,
        })})

# Route Table
public_subnet_route_table = aws.ec2.RouteTable("publicSubnetRouteTable",
    vpc_id=main.id,
    routes=[{
        "cidr_block": "0.0.0.0/0",
        "gateway_id": internet_gateway.id,
    }],
    tags={
        "Name": "aws-pulumi-public-subnet-route-table",
    })

# Associate route table with public subnets
public_subnet_route_table_association = []
for key,value in public_subnets.items():
    public_subnet_route_table_association.append(aws.ec2.RouteTableAssociation("publicSubnetRouteTableAssociation-" + key,
        subnet_id=public_subnet[key].id,
        route_table_id=public_subnet_route_table.id))

# Web - ALB Security Group
alb_http = aws.ec2.SecurityGroup("albHttp",
    description="Allowing HTTP requests to the application load balancer",
    vpc_id=main.id,
    ingress=[{
        "from_port": 80,
        "to_port": 80,
        "protocol": "tcp",
        "cidr_blocks": ["0.0.0.0/0"],
    }],
    egress=[{
        "from_port": 0,
        "to_port": 0,
        "protocol": "-1",
        "cidr_blocks": ["0.0.0.0/0"],
    }],
    tags={
        "Name": "webapplb-security-group",
    })

# Web - Application Load Balancer
webapp_lb = aws.lb.LoadBalancer("webapp-lb",
    internal=False,
    load_balancer_type="application",
    security_groups=[alb_http.id],
    subnets=[public_subnet[key].id for key in list(public_subnet.keys())]
    )

# Web - Target Group
web_target_group = aws.lb.TargetGroup("webTargetGroup",
    port=80,
    protocol="HTTP",
    vpc_id=main.id,
    health_check={
        "port": 80,
        "protocol": "HTTP",
    })

# Web - Listener
web_listener = aws.lb.Listener("webListener",
    load_balancer_arn=webapp_lb.arn,
    port=80,
    protocol="HTTP",
    default_actions=[{
        "type": "forward",
        "target_group_arn": web_target_group.arn,
    }])

# Web - EC2 Instance Security Group
web_instance_sg = aws.ec2.SecurityGroup("webInstanceSg",
    description="Allowing requests to the web servers",
    vpc_id=main.id,
    ingress=[{
        "from_port": 80,
        "to_port": 80,
        "protocol": "tcp",
        "security_groups": [alb_http.id],
    }],
    egress=[{
        "from_port": 0,
        "to_port": 0,
        "protocol": "-1",
        "cidr_blocks": ["0.0.0.0/0"],
    }],
    tags={
        "Name": "aws-pulumi-web-server-security-group",
    })

ec2webinstances = []
for key,value in public_subnets.items():
    ec2webinstances.append(aws.ec2.Instance("ec2webinstance-" + key,
        ami="ami-06ce3edf0cff21f07",
        associate_public_ip_address=True,
        key_name=keypair.key_name,
        vpc_security_group_ids=[web_instance_sg.id],
        availability_zone=key,
        subnet_id=public_subnet[key].id,
        instance_type="t1.micro",
        user_data="""#!/bin/bash
                     sudo su
                     yum -y install httpd
                     sudo systemctl start httpd
                  """,
        tags={
            "Name": "aws-pulumi-webserver-" + key,
        }))

# App - ALB Security Group
alb_app_http = aws.ec2.SecurityGroup("albAppHttp",
    description="Allowing HTTP requests to the app tier application load balancer",
    vpc_id=main.id,
    ingress=[{
        "from_port": 80,
        "to_port": 80,
        "protocol": "tcp",
        "security_groups": [web_instance_sg.id],
    }],
    egress=[{
        "from_port": 0,
        "to_port": 0,
        "protocol": "-1",
        "cidr_blocks": ["0.0.0.0/0"],
    }],
    tags={
        "Name": "alb-app-security-group",
    })

# App - Application Load Balancer
app_app_lb = aws.lb.LoadBalancer("appAppLb",
    internal=False,
    load_balancer_type="application",
    security_groups=[alb_app_http.id],
    subnets=[private_subnet[key].id for key in list(private_subnet.keys())]
    )

# App - Target Group
app_target_group = aws.lb.TargetGroup("appTargetGroup",
    port=80,
    protocol="HTTP",
    vpc_id=main.id,
    health_check={
        "port": 80,
        "protocol": "HTTP",
    })


# App - Listener
app_listener = aws.lb.Listener("appListener",
    load_balancer_arn=app_app_lb.arn,
    port=80,
    protocol="HTTP",
    default_actions=[{
        "type": "forward",
        "target_group_arn": app_target_group.arn,
    }])

# App - EC2 Instance Security Group
app_instance_sg = aws.ec2.SecurityGroup("appInstanceSg",
    description="Allowing requests to the app servers",
    vpc_id=main.id,
    ingress=[{
        "from_port": 80,
        "to_port": 80,
        "protocol": "tcp",
        "security_groups": [alb_app_http.id],
    }],
    egress=[{
        "from_port": 0,
        "to_port": 0,
        "protocol": "-1",
        "cidr_blocks": ["0.0.0.0/0"],
    }],
    tags={
        "Name": "app-server-security-group",
    })


ec2appinstances = []
for key,value in private_subnets.items():
    ec2webinstances.append(aws.ec2.Instance("ec2appinstance-" + key,
        ami="ami-06ce3edf0cff21f07",
        associate_public_ip_address=False,
        key_name=keypair.key_name,
        vpc_security_group_ids=[app_instance_sg.id],
        availability_zone=key,
        subnet_id=private_subnet[key].id,
        instance_type="t1.micro",
        tags={
            "Name": "aws-pulumi-appserver-" + key,
        }))

# DB - Security Group
db_security_group = aws.ec2.SecurityGroup("dbSecurityGroup",
    description="RDS postgres server",
    vpc_id=main.id,
    ingress=[{
        "from_port": 5432,
        "to_port": 5432,
        "protocol": "tcp",
        "security_groups": [app_instance_sg.id],
    }],
    egress=[{
        "from_port": 0,
        "to_port": 0,
        "protocol": "-1",
        "cidr_blocks": ["0.0.0.0/0"],
    }])
# DB - Subnet Group
db_subnet = aws.rds.SubnetGroup("dbsubnet",
    subnet_ids=[database_subnet[key].id for key in list(database_subnet.keys())],
    tags={
        "Name": "aws-terraform-subnet-group",
    })

db_postgres = aws.rds.Instance("dbPostgres",
    allocated_storage=10,
    backup_retention_period=0,
    db_subnet_group_name=db_subnet.name,
    engine="postgres",
    engine_version="12.4",
    identifier="dbpostgres",
    instance_class="db.t3.micro",
    multi_az=False,
    name="dbpostgres",
    username=db_username,
    password=db_password,
    port=5432,
    publicly_accessible=False,
    storage_encrypted=True,
    storage_type="gp2",
    vpc_security_group_ids=[db_security_group.id],
    skip_final_snapshot=True)
