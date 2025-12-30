#!/bin/bash
# Metasploit Framework installation script for Ubuntu 20.04

set -e

echo "Installing Metasploit Framework..."

# Download and run Metasploit installer
curl https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb > /tmp/msfinstall
chmod 755 /tmp/msfinstall
/tmp/msfinstall

# Verify installation
if command -v msfconsole &> /dev/null; then
    echo "Metasploit Framework installed successfully"
    msfconsole --version
else
    echo "Metasploit installation failed"
    exit 1
fi

# Initialize Metasploit database (optional, for faster startup)
# echo "Initializing Metasploit database..."
# msfdb init || true

# Clean up
rm -f /tmp/msfinstall

echo "Metasploit setup complete"
