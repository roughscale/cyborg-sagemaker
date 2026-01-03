# VPC for AWS emulation environment (optional)
resource "aws_vpc" "emulation_vpc" {
  count = var.enable_aws_emulation ? 1 : 0

  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-emulation-vpc"
    }
  )
}

# Private subnets for SageMaker jobs
resource "aws_subnet" "private" {
  count = var.enable_aws_emulation ? length(var.availability_zones) : 0

  vpc_id            = aws_vpc.emulation_vpc[0].id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index)
  availability_zone = var.availability_zones[count.index]

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-private-subnet-${count.index + 1}"
      Type = "private"
    }
  )
}

# Security group for SageMaker jobs
resource "aws_security_group" "sagemaker_sg" {
  count = var.enable_aws_emulation ? 1 : 0

  name        = "${var.project_name}-${var.environment}-sagemaker-sg"
  description = "Security group for SageMaker training/processing jobs in AWS emulation mode"
  vpc_id      = aws_vpc.emulation_vpc[0].id

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  # Allow inbound traffic within the security group
  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
    description = "Allow all traffic within security group"
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-sagemaker-sg"
    }
  )
}

# NAT Gateway for private subnets (required for internet access)
resource "aws_eip" "nat" {
  count = var.enable_aws_emulation ? 1 : 0

  domain = "vpc"

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-nat-eip"
    }
  )
}

# Public subnet for NAT Gateway
resource "aws_subnet" "public" {
  count = var.enable_aws_emulation ? 1 : 0

  vpc_id                  = aws_vpc.emulation_vpc[0].id
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, length(var.availability_zones))
  availability_zone       = var.availability_zones[0]
  map_public_ip_on_launch = true

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-public-subnet"
      Type = "public"
    }
  )
}

# Internet Gateway
resource "aws_internet_gateway" "igw" {
  count = var.enable_aws_emulation ? 1 : 0

  vpc_id = aws_vpc.emulation_vpc[0].id

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-igw"
    }
  )
}

# NAT Gateway
resource "aws_nat_gateway" "nat" {
  count = var.enable_aws_emulation ? 1 : 0

  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[0].id

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-nat-gateway"
    }
  )

  depends_on = [aws_internet_gateway.igw]
}

# Route table for public subnet
resource "aws_route_table" "public" {
  count = var.enable_aws_emulation ? 1 : 0

  vpc_id = aws_vpc.emulation_vpc[0].id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw[0].id
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-public-rt"
    }
  )
}

# Route table association for public subnet
resource "aws_route_table_association" "public" {
  count = var.enable_aws_emulation ? 1 : 0

  subnet_id      = aws_subnet.public[0].id
  route_table_id = aws_route_table.public[0].id
}

# Route table for private subnets
resource "aws_route_table" "private" {
  count = var.enable_aws_emulation ? 1 : 0

  vpc_id = aws_vpc.emulation_vpc[0].id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat[0].id
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-private-rt"
    }
  )
}

# Route table associations for private subnets
resource "aws_route_table_association" "private" {
  count = var.enable_aws_emulation ? length(var.availability_zones) : 0

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[0].id
}
