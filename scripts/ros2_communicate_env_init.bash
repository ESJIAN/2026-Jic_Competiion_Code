#!/bin/bash
# --- RDK X5 端配置 ---

# 这里的 IP 必须填写你的 Windows 物理网卡 IP
WINDOWS_IP="10.70.90.197"

# 1. 生成 FastDDS Client 配置文件
cat <<EOF > ~/fastdds_client.xml
<?xml version="1.0" encoding="UTF-8" ?>
<profiles xmlns="http://www.eprosima.com/XMLSchemas/fastrtps_profiles">
    <participant profile_name="client_profile" is_default_profile="true">
        <rtps>
            <builtin>
                <discovery_config>
                    <discoveryProtocol>CLIENT</discoveryProtocol>
                    <discoveryServersList>
                        <RemoteServer guidPrefix="44.53.00.5f.45.50.52.4f.53.49.4d.41">
                            <metatrafficUnicastLocatorList>
                                <locator>
                                    <udpv4>
                                        <address>$WINDOWS_IP</address>
                                        <port>11811</port>
                                    </udpv4>
                                </locator>
                            </metatrafficUnicastLocatorList>
                        </RemoteServer>
                    </discoveryServersList>
                </discovery_config>
            </builtin>
        </rtps>
    </participant>
</profiles>
EOF

# 2. 设置环境变量
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export FASTRTPS_DEFAULT_PROFILES_FILE=~/fastdds_client.xml
export ROS_DISCOVERY_SERVER="$WINDOWS_IP:11811"
export ROS_DOMAIN_ID=10

echo "✅ RDK Client 配置完成。目标 Server: $WINDOWS_IP:11811"