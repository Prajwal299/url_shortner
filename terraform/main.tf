provider "aws" {
  region = "ap-south-1"
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]  # Canonical
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_subnet" "main" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.1.0/24"
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id
}

resource "aws_route_table" "main" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }
}

resource "aws_route_table_association" "a" {
  subnet_id      = aws_subnet.main.id
  route_table_id = aws_route_table.main.id
}

resource "aws_security_group" "k8s" {
  vpc_id = aws_vpc.main.id
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]  # Open for setup; restrict later
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "master" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t2.medium"  # Changed from t2.micro
  key_name      = "my-aws-key"
  subnet_id     = aws_subnet.main.id
  vpc_security_group_ids = [aws_security_group.k8s.id]
  associate_public_ip_address = true
  tags = { Name = "k8s-master" }
}

resource "aws_instance" "worker" {
  count         = 2
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t2.medium"  # Changed from t2.micro
  key_name      = "my-aws-key"
  subnet_id     = aws_subnet.main.id
  vpc_security_group_ids = [aws_security_group.k8s.id]
  associate_public_ip_address = true
  tags = { Name = "k8s-worker-${count.index + 1}" }
}

resource "aws_ebs_volume" "mysql_data" {
  availability_zone = aws_instance.master.availability_zone
  size              = 10  # GB, free tier
  tags = { Name = "mysql-persistence" }
}

resource "aws_volume_attachment" "mysql_attach" {
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.mysql_data.id
  instance_id = aws_instance.master.id
}

resource "aws_ecr_repository" "api" {
  name = "url-shortener-api"
}

resource "aws_ecr_repository" "frontend" {
  name = "url-shortener-frontend"
}