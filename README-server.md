# Server setup

## SSH setup

Set up the `/etc/ssh/sshd_config` to disallow password authentication.
This can prevent cracking. Add your public key to `~/.ssh/authorized_keys`
of the user you want to log in as.

Create an entry in your `~/.ssh/config` file on your personal computer
to SSH into the server using `climatemap`.

```
Host climatemap
    HostName 123.45.67.89
    User climatemap
    Port 1234
```

Then to connect to the server you just run:
```
ssh climatemap
```

## Add a user

Create a dedicated user as running the server with root can create security
risks.

```
adduser climatemap
```

Run the following to make the user a sudoer.

```
usermod -aG sudo climatemap
```

or

```
$ visudo
climatemap  ALL=(ALL)   ALL
```

## Default editor

You may find `nano` is the default editor, for example when editing a crontab.
If you prefer another editor you can update the default:

```
update-alternatives --config editor
```

Also check `~/.selected_editor` to see if it contains a different editor,
as this overrides the alternative.

## Internet

If the system is using netplan (which the hosting server I'm using is),
check the contents of /etc/netplan/ for the proper network configuration.
If you find DNS is not working, trying pinging 1.1.1.1

```
ping 1.1.1.1
```

and if that works add it to the nameservers in the yaml file.

```
nameservers:
    search: [ myclimatemap.org ]
    addresses:
        - "1.1.1.1"
```

## DNS configuration

You will have to either point your registrar's DNS records to the nameserver
of your hosting provider (e.g. ns1.myhosting.com), or add a "custom DNS"
record in the registrar itself pointing to the IP of your server.

```
A 123.45.67.89 myclimatemap.org
```

## Firewall

To make the server more secure, it is recommended to block irrelevant
ports.

Make sure that the firewall allows packets to port 80, 443, and your SSH
port (usually 22). Port 5000 is necessary on loopback for the API server.

```
sudo iptables -nL
sudo ufw status
```

The following is an example iptables configuration. Be very careful when adding any
`iptables` rules (including these) as you may unwittingly lock yourself out of
the server.

```
sudo iptables -P INPUT ACCEPT
sudo iptables -P FORWARD ACCEPT
sudo iptables -P OUTPUT ACCEPT

sudo iptables -F

sudo iptables -A OUTPUT -o lo -p udp -j ACCEPT
sudo iptables -A INPUT -i lo -p udp -j ACCEPT

sudo iptables -A OUTPUT -o lo -p tcp -j ACCEPT
sudo iptables -A INPUT -i lo -p tcp -j ACCEPT

sudo iptables -A INPUT -p tcp --sport 1024:65535 --dport 443 -m state --state NEW,ESTABLISHED -j ACCEPT
sudo iptables -A OUTPUT -p tcp --sport 443 --dport 1024:65535 -m state --state ESTABLISHED -j ACCEPT

sudo iptables -A OUTPUT -p tcp --sport 1024:65535 --dport 443 -m state --state NEW,ESTABLISHED -j ACCEPT
sudo iptables -A INPUT -p tcp --sport 443 --dport 1024:65535 -m state --state ESTABLISHED -j ACCEPT

sudo iptables -A INPUT -p tcp --sport 1024:65535 --dport 80 -m state --state NEW,ESTABLISHED -j ACCEPT
sudo iptables -A OUTPUT -p tcp --sport 80 --dport 1024:65535 -m state --state ESTABLISHED -j ACCEPT

sudo iptables -A OUTPUT -p tcp --sport 1024:65535 --dport 80 -m state --state NEW,ESTABLISHED -j ACCEPT
sudo iptables -A INPUT -p tcp --sport 80 --dport 1024:65535 -m state --state ESTABLISHED -j ACCEPT

sudo iptables -A OUTPUT -p udp --sport 1024:65535 --dport 53 -m state --state NEW,ESTABLISHED -j ACCEPT
sudo iptables -A INPUT -p udp --sport 53 --dport 1024:65535 -m state --state ESTABLISHED -j ACCEPT
#sudo iptables -A OUTPUT -p tcp --sport 1024:65535 --dport 53 -m state --state NEW,ESTABLISHED -j ACCEPT
#sudo iptables -A INPUT -p tcp --sport 53 --dport 1024:65535 -m state --state ESTABLISHED -j ACCEPT

sudo iptables -A INPUT -p tcp --sport 1024:65535 --dport 22 -m state --state NEW,ESTABLISHED -j ACCEPT
sudo iptables -A OUTPUT -p tcp --sport 22 --dport 1024:65535 -m state --state ESTABLISHED -j ACCEPT

#sudo iptables -A OUTPUT -p tcp --sport 1024:65535 --dport 22 -m state --state NEW,ESTABLISHED -j ACCEPT
#sudo iptables -A INPUT -p tcp --sport 22 --dport 1024:65535 -m state --state ESTABLISHED -j ACCEPT

sudo iptables -A INPUT -p icmp --icmp-type echo-request -j ACCEPT
sudo iptables -A OUTPUT -p icmp --icmp-type echo-reply -j ACCEPT

sudo iptables -A OUTPUT -p icmp --icmp-type echo-request -j ACCEPT
sudo iptables -A INPUT -p icmp --icmp-type echo-reply -j ACCEPT

sudo iptables -P INPUT DROP
sudo iptables -P FORWARD DROP
sudo iptables -P OUTPUT DROP
```

To save the rules, you can install `iptables-persistent` and this will
ask if you want to save the current rules.

```
sudo apt-get install iptables-persistent
```

## Set up packages

In addition to what's in [README.md](README.md), the following packages
should be added.

* rsync
* unattended-upgrades

## Automatic security updates

In order to prevent hackers, install and enable `unattended-upgrades`, particularly
for security updates. This is useful for zero-day exploits where a bug gets revealed
and a hacker hacks your server because you didn't update the packages within 0 days.

Enable the following in `/etc/apt/apt.conf.d/10periodic`:

```
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
APT::Periodic::Unattended-Upgrade "1";
```

To be sure of the above, see the full documentation at
[Automatic Updates](https://ubuntu.com/server/docs/package-management#heading--automatic-updates).

### Automatic restarts

Also be sure to automatically restart the server every so often in case
some updates require a restart. It is wise to do this when few people would
be using the server.

```
sudo crontab -e
```

In the crontab, put:

```
0 5 * * sun /sbin/shutdown -r now
```
