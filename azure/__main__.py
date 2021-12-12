import pulumi
from pulumi_azure import network, postgresql, compute
import pulumi_azure_native as azure_native


conf = pulumi.Config()
vnetcidr = conf.get("vnetcidr")
websubnetcidr = conf.get("websubnetcidr")
appsubnetcidr = conf.get("appsubnetcidr")
dbsubnetcidr = conf.get("dbsubnetcidr")
web_host_name = conf.get("web_host_name")
app_host_name = conf.get("app_host_name")
admin_username = conf.get("admin_username")
primary_database = conf.get("primary_database")
primary_database_version = conf.get("primary_database_version")



azure_pulumi_rg = azure_native.resources.ResourceGroup("azure-pulumi-rg",
    resource_group_name="azure-pulumi-rg"
)

azure_terraform_vnet = azure_native.network.VirtualNetwork("azure-pulumi-vnet",
    resource_group_name=azure_pulumi_rg.name,
    virtual_network_name="azure-pulumi-vnet",
    address_space=azure_native.network.AddressSpaceArgs(
        address_prefixes=[vnetcidr],
    )
)


web_subnet = azure_native.network.Subnet("web-subnet",
    virtual_network_name=azure_terraform_vnet.name,
    resource_group_name=azure_pulumi_rg.name,
    subnet_name="web-subnet",
    address_prefix=websubnetcidr)

app_subnet = azure_native.network.Subnet("app-subnet",
    virtual_network_name=azure_terraform_vnet.name,
    resource_group_name=azure_pulumi_rg.name,
    subnet_name="app-subnet",
    address_prefix=appsubnetcidr)

db_subnet = azure_native.network.Subnet("db-subnet",
    virtual_network_name=azure_terraform_vnet.name,
    resource_group_name=azure_pulumi_rg.name,
    subnet_name="db-subnet",
    address_prefix=dbsubnetcidr)


# web_availability_set = azure_native.compute.AvailabilitySet("web-availability-set",
#     availability_set_name="web-availability-set",
#     resource_group_name=azure_pulumi_rg.name,
#     platform_fault_domain_count=1,
#     platform_update_domain_count=1,
#     sku={
#         "name": "Aligned"
#         }
#     )

web_public_ip = azure_native.network.PublicIPAddress("web-public-ip",
    resource_group_name=azure_pulumi_rg.name,
    public_ip_address_name="web-public-ip",
    public_ip_allocation_method="Static")

webnetworksg = azure_native.network.NetworkSecurityGroup("webnetworksg",
    resource_group_name=azure_pulumi_rg.name,
    network_security_group_name="webnetworksg",
    security_rules=[
        azure_native.network.SecurityRuleArgs(
            access="Allow",
            destination_address_prefix="*",
            destination_port_range="22",
            direction="Inbound",
            name="ssh-rule-1",
            priority=101,
            protocol="Tcp",
            source_address_prefix="*",
            source_port_range="*",
        ),
        azure_native.network.SecurityRuleArgs(
            access="Deny",
            destination_address_prefix="*",
            destination_port_range="22",
            direction="Inbound",
            name="ssh-rule-2",
            priority=100,
            protocol="Tcp",
            source_address_prefix="192.168.3.0/24",
            source_port_range="*",
        )
    
    ]
)

web_network_interface = network.NetworkInterface("web-network-interface",
    name = "web-network-interface",
    resource_group_name=azure_pulumi_rg.name,
    opts=pulumi.ResourceOptions(depends_on=[web_subnet]),
    ip_configurations=[{
        "name": "web-webserver",
        "subnet_id": web_subnet.id,
        "privateIpAddressAllocation": "Dynamic",
        "public_ip_address_id": web_public_ip.id,
    }])

web_nsg_subnet = network.SubnetNetworkSecurityGroupAssociation("web-nsg-subnet-association",
    subnet_id=web_subnet.id,
    network_security_group_id=webnetworksg.id,
    opts=pulumi.ResourceOptions(depends_on=[webnetworksg]))


web_nic_sg_assoc = network.NetworkInterfaceSecurityGroupAssociation("web-nic-sg-assoc",
    network_interface_id=web_network_interface.id,
    network_security_group_id=webnetworksg.id)


web_vm = compute.VirtualMachine("web-vm",
    name="web-vm",
    resource_group_name=azure_pulumi_rg.name,
    network_interface_ids=[web_network_interface.id],
    availability_set_id=web_availability_set.id,
    vm_size="Standard_D2s_v3",
    delete_os_disk_on_termination=True,
    storage_image_reference={
        "publisher": "Canonical",
        "offer": "UbuntuServer",
        "sku": "18.04-LTS",
        "version": "latest",
    },
    storage_os_disk={
        "name": "web-disk",
        "caching": "ReadWrite",
        "create_option": "FromImage",
        "managedDiskType": "Standard_LRS",
    },
    os_profile={
        "computer_name": web_host_name,
        "admin_username": admin_username,
    },
    os_profile_linux_config={
        "disable_password_authentication": True,
        "sshKeys": [{
            "path": "/home/diarmaid/.ssh/authorized_keys",
            "keyData": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCwS/sf75LjdVHcSkiTY8Ixvk9fMCrf72xTsmtgkqmFpW3akKYz+UGrPojNaNPqNLbiQ+G3MRwnKRIH5xu1CgRct7knpE0cIEjv4ObcvcX0FvvDYMh+fyXqLy4ko7V4pPFPpzHxB0HwFTDOGGvvYHA6L2NqiSpDkiK3bM+525A/pyR8+Y72xxdRXcamrIUEkHSNJxy2G/xElEczBa8Pz+4Kakj9i4/T9SUUI6CHByjn4SZQsMvGzYzCv0uMZwe5qsjE4gnBVSz89Y6yJr0QHzb6y/NKkshivnniMz5JikfcBtbnEPlkt4jNes7c3VnY3//+4tAEo4Ix3tCZqsmdwPLT diarmaid@development",
        }],
    })

app_availability_set = azure_native.compute.AvailabilitySet("app-availability-set",
    availability_set_name="app-availability-set",
    resource_group_name=azure_pulumi_rg.name,
    platform_fault_domain_count=1,
    platform_update_domain_count=1,
    sku={
        "name": "Aligned"
        }
    )


appnetworksg = azure_native.network.NetworkSecurityGroup("appnetworksg",
    resource_group_name=azure_pulumi_rg.name,
    network_security_group_name="appnetworksg",
    security_rules=[
        azure_native.network.SecurityRuleArgs(
            access="Allow",
            destination_address_prefix="*",
            destination_port_range="22",
            direction="Inbound",
            name="ssh-rule-1",
            priority=100,
            protocol="Tcp",
            source_address_prefix="192.168.1.0/24",
            source_port_range="*",
        ),
        azure_native.network.SecurityRuleArgs(
            access="Allow",
            destination_address_prefix="*",
            destination_port_range="22",
            direction="Outbound",
            name="ssh-rule-2",
            priority=101,
            protocol="Tcp",
            source_address_prefix="192.168.1.0/24",
            source_port_range="*",
        )
    
    ]
)
app_network_interface = network.NetworkInterface("app-network-interface",
    name = "app-network-interface",
    resource_group_name=azure_pulumi_rg.name,
    ip_configurations=[{
        "name": "app-webserver",
        "subnet_id": app_subnet.id,
        "privateIpAddressAllocation": "Dynamic",
    }])


app_nsg_subnet = network.SubnetNetworkSecurityGroupAssociation("app-nsg-subnet-association",
    subnet_id=app_subnet.id,
    network_security_group_id=appnetworksg.id,
    opts=pulumi.ResourceOptions(depends_on=[web_nsg_subnet]))


app_nic_sg_assoc = network.NetworkInterfaceSecurityGroupAssociation("app-nic-sg-assoc",
    network_interface_id=app_network_interface.id,
    network_security_group_id=appnetworksg.id)

app_vm = compute.VirtualMachine("app-vm",
    name="app-vm",
    resource_group_name=azure_pulumi_rg.name,
    network_interface_ids=[app_network_interface.id],
    availability_set_id=app_availability_set.id,
    vm_size="Standard_D2s_v3",
    delete_os_disk_on_termination=True,
    storage_image_reference={
        "publisher": "Canonical",
        "offer": "UbuntuServer",
        "sku": "18.04-LTS",
        "version": "latest",
    },
    storage_os_disk={
        "name": "app-disk",
        "caching": "ReadWrite",
        "create_option": "FromImage",
        "managedDiskType": "Standard_LRS",
    },
    os_profile_linux_config={
        "disable_password_authentication": True,
        "sshKeys": [{
            "path": "/home/diarmaid/.ssh/authorized_keys",
            "keyData": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCwS/sf75LjdVHcSkiTY8Ixvk9fMCrf72xTsmtgkqmFpW3akKYz+UGrPojNaNPqNLbiQ+G3MRwnKRIH5xu1CgRct7knpE0cIEjv4ObcvcX0FvvDYMh+fyXqLy4ko7V4pPFPpzHxB0HwFTDOGGvvYHA6L2NqiSpDkiK3bM+525A/pyR8+Y72xxdRXcamrIUEkHSNJxy2G/xElEczBa8Pz+4Kakj9i4/T9SUUI6CHByjn4SZQsMvGzYzCv0uMZwe5qsjE4gnBVSz89Y6yJr0QHzb6y/NKkshivnniMz5JikfcBtbnEPlkt4jNes7c3VnY3//+4tAEo4Ix3tCZqsmdwPLT diarmaid@development",
        }],
    },
    os_profile={
        "computer_name": app_host_name,
        "admin_username": admin_username,
    }
    )

dbnetworksg = azure_native.network.NetworkSecurityGroup("dbnetworksg",
    resource_group_name=azure_pulumi_rg.name,
    network_security_group_name="dbnetworksg",
    security_rules=[
        azure_native.network.SecurityRuleArgs(
            access="Allow",
            destination_address_prefix="*",
            destination_port_range="3306",
            direction="Inbound",
            name="ssh-rule-1",
            priority=101,
            protocol="Tcp",
            source_address_prefix="192.168.2.0/24",
            source_port_range="*",
        ),
        azure_native.network.SecurityRuleArgs(
            access="Allow",
            destination_address_prefix="*",
            destination_port_range="3306",
            direction="Outbound",
            name="ssh-rule-2",
            priority=101,
            protocol="Tcp",
            source_address_prefix="192.168.2.0/24",
            source_port_range="*",
        ),
        azure_native.network.SecurityRuleArgs(
            access="Deny",
            destination_address_prefix="*",
            destination_port_range="3306",
            direction="Outbound",
            name="ssh-rule-3",
            priority=100,
            protocol="Tcp",
            source_address_prefix="192.168.1.0/24",
            source_port_range="*",
        )
    
    ]
)

db_nsg_subnet = network.SubnetNetworkSecurityGroupAssociation("db-nsg-subnet-association",
    subnet_id=db_subnet.id,
    network_security_group_id=dbnetworksg.id,
    opts=pulumi.ResourceOptions(depends_on=[app_nsg_subnet]))


postgres_db_server = postgresql.Server("pqsqldbserver62a",
    location="North Europe",
    resource_group_name=azure_pulumi_rg.name,
    administrator_login=database_user,
    administrator_login_password=database_password,
    sku_name="GP_Gen5_4",
    version="9.6",
    storage_mb=5120,
    backup_retention_days=7,
    geo_redundant_backup_enabled=False,
    auto_grow_enabled=False,
    public_network_access_enabled=False,
    ssl_enforcement_enabled=False)
