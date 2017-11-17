#!/bin/bash -x
exec > >(tee -a /var/tmp/ccm-node-init_$$.log) 2>&1

# . /usr/local/osmosix/etc/.osmosix.sh
# TODO: fix this so that it comes from env variable.
OSMOSIX_CLOUD="vmware"

. /usr/local/osmosix/etc/userenv
. /usr/local/osmosix/service/utils/cfgutil.sh
. /usr/local/osmosix/service/utils/agent_util.sh

check_error()
{
        status=$1
        msg=$2
        exit_status=$3

        if [[ ${status} -ne 0 ]]; then
                agentSendLogMessage "${msg}"
                exit ${exit_status}
        fi

        return 0
}

dlFile () {
    agentSendLogMessage  "Attempting to download $1"
    if [ -n "$dlUser" ]; then
        agentSendLogMessage  "Found user ${dlUser} specified. Using that and specified password for download auth."
        wget --no-check-certificate --user $dlUser --password $dlPass $1
    else
        agentSendLogMessage  "Didn't find username specified. Downloading with no auth."
        wget --no-check-certificate $1
    fi
    if [ "$?" = "0" ]; then
        agentSendLogMessage  "$1 downloaded"
    else
        agentSendLogMessage  "Error downloading $1"
        exit 1
    fi
}

agentSendLogMessage "Username: $(whoami)" # Should execute as cliqruser
agentSendLogMessage "Working Directory: $(pwd)"

agentSendLogMessage  "Installing OS Prerequisits wget vim java-1.8.0-openjdk nmap"
sudo mv /etc/yum.repos.d/cliqr.repo ~
sudo mv /usr/local/osmosix/etc/userenv ~ # Move it back at end of script.



#sudo yum update -y
#sudo yum install -y wget
#sudo yum install -y vim
#sudo yum install -y java-1.8.0-openjdk
#sudo yum install -y nmap


# Download necessary files
cd /tmp
agentSendLogMessage  "Downloading installer files."
dlFile ${baseUrl}/installer/core_installer.bin
dlFile ${baseUrl}/appliance/ccm-installer.jar
dlFile ${baseUrl}/appliance/ccm-response.xml


# Remove list of installed modules residual from worker installer.
sudo rm -f /etc/cliqr_modules.conf

# Install packages not present in cliqr repo.
#sudo yum install -y python-setuptools
#sudo yum install -y jbigkit-libs
# sudo yum install -y mongodb-org

# Run the core installer
sudo chmod +x core_installer.bin
agentSendLogMessage  "Running core installer"
# Set custom repo if desired
if [ -n "$cc_custom_repo" ]; then
    agentSendLogMessage  "Setting custom repo to ${cc_custom_repo}"
    export CUSTOM_REPO=${cc_custom_repo}
fi
export vnc_module=true

# sudo ./core_installer.bin --noexec --keep
#The core installer incorrectly replaces a newer esxmetadata file,
#so instead copy the original one over the one in the installer.
#if [ ${OSMOSIX_CLOUD} == "vmware" ]
#then
#    sudo cp /usr/local/osmosix/bin/esxmetadata /tmp/core/mgmtserver/mds/esxmetadata
#fi
#cd /tmp/core
#sudo -E ./setup.sh centos7 ${OSMOSIX_CLOUD} ccm # -E makes sure to keep CUSTOM_REPO env variable.
sudo -E ./core_installer.bin centos7 ${OSMOSIX_CLOUD} ccm

# agentSendLogMessage  "Running jar installer"
# sudo update-alternatives --install /usr/bin/java java /usr/lib/jvm/java-8-sun/bin/java 1
sudo java -jar ccm-installer.jar ccm-response.xml


# Use "?" as sed delimiter to avoid escaping all the slashes
sed -i -e "s?publicDnsName=<mgmtserver_public_dns_name>?publicDnsName=${CliqrTier_ccm_PUBLIC_IP}?g" \
-e "s?ccm.log.elkHost=?ccm.log.elkHost=${CliqrTier_monitor_PUBLIC_IP}?g" \
/usr/local/tomcat/webapps/ROOT/WEB-INF/server.properties

# Remove these two unsupported properties in the tomcat env config file.
sed -i.bak -e 's$ -XX:PermSize=512m -XX:MaxPermSize=512m$$g' /usr/local/tomcat/bin/setenv.sh

sudo /etc/init.d/tomcat stop
sudo rm -f /usr/local/tomcat/catalina.pid
sudo rm -f /usr/local/tomcat/logs/osmosix.log
sudo /etc/init.d/tomcat start


# agentSendLogMessage  "Waiting for server to start."
COUNT=0
MAX=50
SLEEP_TIME=5
ERR=0

until $(curl https://${CliqrTier_ccm_PUBLIC_IP} -k -m 5 ); do
  sleep ${SLEEP_TIME}
  let "COUNT++"
  echo ${COUNT}
  if [ ${COUNT} -gt 50 ]; then
    ERR=1
    break
  fi
done
if [ ${ERR} -ne 0 ]; then
    : # agentSendLogMessage "Failed to start server after about 5 minutes"
else
    : # agentSendLogMessage "Server Started."
fi

sudo rm -f /tmp/core_installer.bin
sudo rm -f /tmp/ccm-installer.jar
sudo rm -f /tmp/ccm-response.xml
sudo rm -rf /tmp/core

sudo mv ~/userenv /usr/local/osmosix/etc/
sudo mv ~/cliqr.repo /etc/yum.repos.d/