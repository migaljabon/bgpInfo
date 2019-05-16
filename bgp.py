#!/usr/bin/python
from __future__ import print_function
from optparse import OptionParser
from collections import defaultdict
import subprocess
import re
# import datetime
import logging
import pprint


class VerifyUserInput(object):
    """
    Verify User input: ci_name against the /etc/host file.
    return ci_name + domain name:
    wp-nwk-atm-xr.gpi.remote.binc.net
    """
    def __init__(self, ci_name=None):
        self.ci_name = ci_name
        self.verified = None
        self.stdout = None
        self.ci_list = []
        self.ci_count = []

    def verify_etc_hosts(self):
        bgp_logger.info('verify_etc_hosts() method')
        ''' run cat /etc/hosts and get list of devices '''
        # declaring function scope variable
        if self.ci_name is None:
            print("You didn't include ci_name")
            return False
        else:
            try:
                proc = subprocess.Popen(
                        ['cat', '/etc/hosts'], stdout=subprocess.PIPE)
                self.stdout = proc.communicate()[0]
                self.stdout = self.stdout.split('\n')
            except Exception as err:
                bgp_logger.info(err)
                raise SystemExit(
                    "I am not able to find your BGP ROUTER on this BMN\n")
        # Initialize the verified variable if ci_name is not found in
        # /etc/hosts script will exit
        self.stdout = self.filter_findstring_output()
        self.stdout = self.verify_multiple_entries()

        # verified will be None if no FQDN was found
        if self.verified is None:
            print("I cannot find %s as a managed device"
                  " in this BMN" % self.ci_name)
            return False
        else:
            # because self.stdout was turned into a list, it now needs to
            # return the single item stripped out of list
            return self.stdout[0]

    def verify_multiple_entries(self):
        '''
        If multiple devices with similiar name are found,
        prompt user which device is the script going to run on
        '''
        bgp_logger.info('verify_multiple_entries() method')
        for line in self.stdout:
            if self.ci_name in line:
                self.ci_count.append(line)
        # go to print_menu, if user selects wrong
        # choice re-print the menu
        if len(self.ci_count) > 1:
            while True:
                self.print_menu()
                # prompt user to select device run the script on
                try:
                    selection = int(raw_input("Choise# "))
                    selection = selection - 1
                    if selection in self.ci_list:
                        break
                    else:
                        print("\n")
                        print("You enter and INVALID option. "
                              "Please Try again:\n")
                except Exception as err:
                    print("\n")
                    print("INPUT ERROR: %s" % err)
                    print("You enter and INVALID option. "
                          "Please Try again:\n")

            bgp_logger.info(self.ci_count[selection])
            return self.ci_count[selection]
        else:
            return self.ci_count

    def print_menu(self):
        '''
        print menu if multiple devices with similar name
        '''
        print("I found multiple entries with similar name,\n"
              "Choose which ci you want to run this script on,\n"
              "Select a CI by using the number on the left:\n")
        # store the list of indexes
        for index, ci in enumerate(self.ci_count):
            self.ci_list.append(index)
            print(" %d) %s\n" % (index + 1, ci))
        return self.ci_list

    def filter_findstring_output(self):
        '''
        filter out unneeded fields and return only log ci_name
        "wp-hauppauge-sw.gpi.remote.hms.cdw.com"
        '''
        filtered = []
        host_pattern = re.compile(r'\s+(%s)' % self.ci_name, re.IGNORECASE)
        for line in self.stdout:
            if host_pattern.search(line):
                self.verified = True
                if len(line.split()) == 3:
                    bgp_logger.info(line.split()[1])
                    ci_fqdn = line.split()[1]
                    filtered.append(ci_fqdn)
        bgp_logger.info(filtered)
        return filtered


class RunFindstring(object):
    '''
    Run findstring on neighbor IP to verify if it is managed by CDW
    '''
    def __init__(self, neighbor_ip = None):
        self.neighbor_ip = neighbor_ip
        bgp_logger.info('run_findstring() class')

    def find_managed(self):
        '''
        run findstring to verify if neighbor ip address
        is managed by CDW
        '''
        bgp_logger.info('find_managed() method')
        if self.neighbor_ip is None:
            print("Neighbor IP is not valid")
            return False
        else:
            self.neighbor_ip = "ip address " + self.neighbor_ip + " "
            try:
                proc = subprocess.Popen(
                                        ['findstring','-d',
                                        self.neighbor_ip],
                                        stdout=subprocess.PIPE)
                grep = subprocess.Popen(['grep',
                                         'Device:'],
                                        stdin=proc.stdout,
                                        stdout=subprocess.PIPE)
                awk = subprocess.Popen(['awk',
                                        '{print $2}'],
                                        stdin=grep.stdout,
                                        stdout=subprocess.PIPE)
                stdout = awk.communicate()[0]
            except Exception as err:
                bgp_logger.info(err)
                raise SystemExit(
                    "I am not able to run findstring on this BMN\n")
        # Initialize the verified variable if ci_name is not found in
        # /etc/hosts script will exit
        if stdout:
            return stdout
        else:
            return False


class LoggerClass(object):
    """ This class is created to initialize logging functionality
    in this script. It is possible to create a logging filehandle
    that can store logging info in a file. This file is located
    in the same directory where the script is running by default.
    To have the script generate script logging remove the hash in the
    commented out lines below. """
    @staticmethod
    def logging():
        # today = datetime.date.today()
        # mydate = (str(today.year) + "-" + str(today.month) +
        #          "-" + str(today.day))

        # log_filename = "bgpInfoScript_" + mydate + ".log"
        global bgp_logger
        bgp_logger = logging.getLogger(__name__)
        bgp_logger.setLevel(logging.INFO)
        bgp_logger.disabled = False

        # self.file_log = logging.FileHandler(log_filename)
        # self.file_log.setLevel(logging.INFO)

        streamLog = logging.StreamHandler()
        streamLog.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s '
                                      '- %(message)s')

        # self.file_log.setFormatter(formatter)
        streamLog.setFormatter(formatter)

        # self.bgp_logger.addHandler(file_log)
        bgp_logger.addHandler(streamLog)


class RecursiveLookup(object):

    def is_tunnel(self, source_interface):
        if 'Tunnel' in source_interface:
            bgp_logger.info('Found a Tunnel Interface')
            nbma_end_ip = self.show_dmvpn_interface(source_interface,
                                                    neighbor_ip)
            bgp_logger.info('nbma Tunnel %s' % nbma_end_ip)
        else:
            bgp_logger.info('Found no Tunnel Interface')
            nbma_end_ip = None

        if nbma_end_ip:
            bgp_logger.info('Found a Tunnel Interface and '
                            'nbma ip address')
            tunnel_dest_ip, source_interface = self.show_ip_cef(nbma_end_ip)
            bgp_logger.info('nexthop_ip %s , source_interface %s' %
                            (nbma_end_ip, source_interface))
        return (nbma_end_ip, source_interface)


class QueryLogs(object):
    ''' This class will contain all logs related methods '''
    def __init__(self, ci_fqdn):
        self.ci_fqdn = ci_fqdn

    def query_lcat_intf_flap(self, interface_name):
        bgp_logger.info('query_lcat_intf_flap() Method')
        ci_name_short = self.ci_fqdn.split('.')[0]
        bgp_logger.info('CI SHORT NAME: %s' % ci_name_short)
        try:
            lcat_process = subprocess.Popen(
                    ['lcat', 'silo'], stdout=subprocess.PIPE)
            grep1_ci = subprocess.Popen(
                    ['grep', ci_name_short], stdin=lcat_process.stdout,
                    stdout=subprocess.PIPE)
            grep2_interface = subprocess.Popen(
                    ['grep', interface_name], stdin=grep1_ci.stdout,
                    stdout=subprocess.PIPE)
            stdout = grep2_interface.communicate()[0]
            stdout = stdout.split('\n')
            # return false if no %LINEPROTO-5-UPDOWN entry is found 
            # in log line
            for line in stdout:
                if 'UPDOWN' in line:
                    if len(stdout) > 10:
                        return stdout[-10:]
                    else:
                        return stdout
            else:
                return False
        except Exception as err:
            bgp_logger.info(err)
            print("Subprocess failed to retreive BGP\n"
                  " log information for bouncing interfaces\n")
            return False

    def query_lcat_bgp(self, neighbor_ip):
        '''
        Look for BGP flaps
        '''
        bgp_logger.info('query_lcat_bgp() Method')
        ci_name_short = self.ci_fqdn.split('.')[0]
        bgp_logger.info('CI SHORT NAME: %s' % ci_name_short)
        try:
            lcat_process = subprocess.Popen(
                    ['lcat', 'silo'], stdout=subprocess.PIPE)
            grep1_ci = subprocess.Popen(
                    ['grep', ci_name_short], stdin=lcat_process.stdout,
                    stdout=subprocess.PIPE)
            grep2_bgp = subprocess.Popen(
                    ['grep', 'BGP'], stdin=grep1_ci.stdout,
                    stdout=subprocess.PIPE)
            grep3_neighbor = subprocess.Popen(
                    ['grep', neighbor_ip], stdin=grep2_bgp.stdout,
                    stdout=subprocess.PIPE)
            stdout = grep3_neighbor.communicate()[0]
            stdout = stdout.split('\n')
            for line in stdout:
                if "BGP" in line:
                    if len(stdout) > 10:
                        return stdout[-10:]
                    else:
                        return stdout
            else:
                return False
        except Exception as err:
            bgp_logger.info(err)
            print("Subprocess failed to retrieve BGP\n"
                  " log information for Neighbor: %s" % neighbor_ip)
            return False
        

class CiscoCommands(RecursiveLookup):
    ''' This class will run any bgp related commands '''

    def __init__(self, ci_name):
        self.ci_name = ci_name
        self.command = None

    def verify_ip_protocols(self):
        ''' This method will verify BGP is configured '''
        bgp_logger.info('verify_ip_protocols() method')
        self.command = 'show ip protocol | s bgp'
        bgp_as_pattern = re.compile(r'(bgp\s+\d+)')
        output = self.run_cisco_commands()
        for line in output:
            if bgp_as_pattern.search(line):
                print("This device runs BGP: %s" %
                      bgp_as_pattern.search(line).group(1))
                return True

    def clean_clogin_output(self, clogin_output):
        bgp_logger.info('clean_clogin_output() method')
        ''' remove prompt output from clogin output '''
        for index, line in enumerate(clogin_output):
            if self.command in line:
                start = index
            if 'exit' in line:
                end = index
        return clogin_output[start:end]

    def run_cisco_commands(self):
        bgp_logger.info('run_cisco_commands() method')
        ''' Run clogin to retrieve command information
        from device '''
        try:
            clogin_process = subprocess.Popen(['sudo', '-u', 'binc',
                                               '/opt/sbin/clogin',
                                               '-c', self.command,
                                              self.ci_name],
                                              stdout=subprocess.PIPE)
            clogin_output = clogin_process.communicate()[0]
            clogin_output = clogin_output.split('\r\n')
            return self.clean_clogin_output(clogin_output)
        except Exception as err:
            raise SystemExit('clogin process failed for device: %s\n'
                             'ERROR: %s' % (self.ci_name, err))

    def show_bgp_summary(self, ip_address):
        '''
        pull show bgp neighbor information
        '''
        bgp_logger.info('show_bgp_neighbor method()')
        self.command = "show ip bgp summary"
        output = self.run_cisco_commands()
        bgp_logger.info('BGP SUMMARY: \n %s' % output[1:])

        # return a slice of the output, omitting the command entered
        return output[1:]

    def show_ip_cef(self, ip_address):
        bgp_logger.info('show_ip_cef() method')
        self.command = 'show ip cef ' + ip_address
        output = self.run_cisco_commands()
        cef_interface_pattern = re.compile(r'(?:\s+)(\S+)(?:\s+)(\S+)$')
        ip_pattern = re.compile(r'(\d+\.\d+\.\d+.\d+)')
        for line in output[1:]:
            if cef_interface_pattern.search(line):
                nexthop_ip = cef_interface_pattern.search(line).group(1)
                outbound_if = cef_interface_pattern.search(line).group(2)
                if ip_pattern.search(nexthop_ip):
                    return nexthop_ip, outbound_if
                else:
                    return None, outbound_if

    def show_dmvpn_interface(self, source_interface, neighbor_ip):
        ''' retrieve dmvpn information '''
        bgp_logger.info('show_dmvpn_interface() method')
        self.command = ('show dmvpn interface ' + source_interface +
                        ' | i ' + neighbor_ip + " ")

        dmvpn_output_pattern = re.compile(r'(?:^\s+\d+\s)(\S+)(?:\s+\S+\s+)')
        output = self.run_cisco_commands()
        for line in output[1:]:
            if dmvpn_output_pattern.search(line):
                return dmvpn_output_pattern.search(line).group(1)

    def show_vrf_config(self, nbma_interface):
        ''' this method will verify if nbma address
            is reachable through a vrf '''
        bgp_logger.info('show_vrf_config() method')
        self.command = ('sh run int ' + nbma_interface + " | i vrf")
        vrf_name_pattern = re.compile(r'(?:\s+vrf\s+forwarding\s+)(\S+)')
        output = self.run_cisco_commands()
        vrf_name = None
        for line in output:
            if vrf_name_pattern.search(line):
                vrf_name = vrf_name_pattern.search(line).group(1)
                bgp_logger.info('found a VRF: %s' % vrf_name)
                return vrf_name
        if not vrf_name:
            bgp_logger.info('did not find a VRF')
            return None

    def show_intf_desciption(self, nbma_interface):
        ''' This method will extract interface description
            if there's a circuit ID it can be used to open
            a carrier ticket '''
        bgp_logger.info('show_interface_desciption() method')
        self.command = 'show run int ' + nbma_interface + ' | i description'
        output = self.run_cisco_commands()
        description = None
        int_desc_pattern = re.compile(r'(?:description\s+)(.+)')
        for line in output[1:]:
            if int_desc_pattern.search(line):
                description = int_desc_pattern.search(line).group(1)
                return description
        if not description:
            return None

    def ping_through_vrf(self, vrf_name, nbma_end_ip):
        ''' this method will ping nbma end point ip address
            through vrf to test carrier connectivity '''
        bgp_logger.info('ping_through_vrf() method')
        self.command = "ping vrf " + vrf_name + " " + nbma_end_ip
        output = self.run_cisco_commands()
        for line in output[1:]:
            print(line)

    def ping_through_to_end_ip(self, nbma_end_ip):
        ''' this method will ping nbma end point ip address to test
            ip connectivity '''
        bgp_logger.info('ping_through_to_end_ip() method')
        self.command = "ping " + nbma_end_ip
        output = self.run_cisco_commands()
        for line in output:
            print(line)


class Recommendations(object):
    '''
    This class will orchestrate recommendations according
    to a few outputs, bgp neighbor summary and ping results
    '''
    def bgp_neighbor(self, bgp_summary, neighbor_ip):
        bgp_logger.info("bgp_neighbor() method")
        for line in bgp_summary:
            if neighbor_ip in line:
                self._bgp_uptime(line)

    def _bgp_uptime(self, bgp_neighbor_uptime):
        '''
        determine if BGP has flapped in the last 24hrs
        regex: Group(1) = Hrs - Group(2) = Min - Group(3) = Sec
        '''
        uptime_hours = re.compile(r'(\d{2})(?:\:)(\d{2})(?:\:)(\d{2})')
        uptime_days = re.compile(r'(?:\s+)(\d+\w\d+\w)(?:\s+\d+)$')
        match_hours = uptime_hours.search(bgp_neighbor_uptime)
        match_days = uptime_days.search(bgp_neighbor_uptime)

        if match_days:
            bgp_logger.info("BGP neighbor has been stablised"
                            " for over 24hrs\n%s" % bgp_neighbor_uptime)
        if match_hours:
            hours = int(match_hours.group(1))
            minutes = int(match_hours.group(2))
            seconds = int(match_hours.group(3))
            uptime = match_hours.group(0)
            bgp_logger.info("BGP Neighbor Flapped Recently"
                            " in less than 24hrs\n%s" % bgp_neighbor_uptime)


def argument_parser():
    ''' Run argument parser to verify what user wants to do '''
    parser = OptionParser(usage="\nOPTION: %prog -d <ci_name> "
                          "-n <ipAddress>\n\n"
                          "EXAMPLE: bgp -d "
                          "wp-nwk-atm-xr.gpi.remote.binc.net"
                          " -n 8.9.10.11\n\n"
                          "ALSO TO PRINT HELP: %prog "
                          "--help to print this information",
                          version="%prog 1.0")
    parser.add_option("-d", "--device",
                      # optional because action defaults to "store"
                      action="store",
                      dest="ci_name",
                      help="ci_name is a REQUIREMENT to run this script",)
    parser.add_option("-n", "--neighbor",
                      action="store",
                      dest="neighbor_ip",
                      help="BGP Neighbor IP address is a REQUIREMENT",)
    (options, args) = parser.parse_args()
    if options.ci_name and options.neighbor_ip:
        user_input = VerifyUserInput(options.ci_name)
        ci_name_verified = user_input.verify_etc_hosts()
        if not ci_name_verified:
            raise SystemExit('Terminating Script!')
        else:
            return (ci_name_verified, options.neighbor_ip)
    else:
        parser.error("You need to provide ci_name and BGP Neighbor"
                     " IP to run this Script\n\n")


def bgp_orchestrator(ci_fqdn, neighbor_ip):
    bgp_logger.info('bgp_orchestrator() method')

    # Initialize class that will run clogin on cisco Devices
    bgp = CiscoCommands(ci_fqdn)

    # find is neighbor IP is managed by CDW
    findstring = RunFindstring(neighbor_ip)
    cdw_managed = findstring.find_managed()
    bgp_logger.info('Neighbor IP ID: %s' % cdw_managed)

    # Verify if device is configured with BGP
    bgp_as = bgp.verify_ip_protocols()

    #Initialize logging class
    query_logging = QueryLogs(ci_fqdn)

    # initialize vrf_name to None
    vrf_name = None
    if bgp_as:
        # display show ip bgp summary
        bgp_summary = bgp.show_bgp_summary(neighbor_ip)
        verify = Recommendations()
        result_bgp_neighbor = verify.bgp_neighbor(bgp_summary, neighbor_ip)
            
        # display show ip cef <IP> 
        nexthop_ip, source_interface = bgp.show_ip_cef(neighbor_ip)
        bgp_logger.info("nexthop ip: %s , interface %s" %
                        (nexthop_ip, source_interface))

        # Query logs, look for interface flaps or BGP State Change entries
        intf_flaps = query_logging.query_lcat_intf_flap(source_interface)
        if intf_flaps:
            for line in intf_flaps:
                print(line)
        else:
            print("NO INTERFACE FLAPS FOUND")
        # Query logs for BGP and neighbor IP state changes
        bgp_logs = query_logging.query_lcat_bgp(neighbor_ip)
        if bgp_logs:
            for line in bgp_logs:
                print(line)
        else:
            print("NO BGP ENTIES FOUND IN THE LOG")

        # if cef points to a Tunnel then recursive lookup
        # to find nmba tunnel destination IP
        if 'Tunnel' in source_interface:
            tunnel_dest_ip, source_interface = (
                bgp.is_tunnel(source_interface))
        else:
            if not nexthop_ip:
                nexthop_ip = neighbor_ip
            tunnel_dest_ip = False 

        # query the silo logs for interface flap
        if nexthop_ip or tunnel_dest_ip:
            vrf_name = bgp.show_vrf_config(source_interface)

        # if vrf associated with interface, use it to ping
        # gateway, other endpoint or end of tunnel nbma
        if vrf_name is not None:
            if nexthop_ip:
                ping_vrf_results = bgp.ping_through_vrf(
                                    vrf_name, nexthop_ip)
            if tunnel_dest_ip:
                ping_vrf_results = bgp.ping_through_vrf(
                                    vrf_name, tunnel_dest_ip)

        # Retreive Interface Description
        if nexthop_ip:
            description = bgp.show_intf_desciption(source_interface)
        if tunnel_dest_ip:
            description = bgp.show_intf_desciption(source_interface)
        bgp_logger.info('Interface description: %s' % description)

        # If no VRF is associated with interface then
        if vrf_name is None:
            if nexthop_ip:
                ping_results = bgp.ping_through_to_end_ip(
                    nexthop_ip)
            if tunnel_dest_ip:
                ping_results = bgp.ping_through_to_end_ip(
                    tunnel_dest_ip)
    else:
        raise SystemExit("This device %s does not run BGP" % ci_fqdn)


if __name__ == '__main__':
    #  bgpInfo -d wp-nwk-atm-xr.gpi.remote.binc.net
    # Initializing Dictionary to Store BGP information
    try:
        bgp_dict = lambda: defaultdict(bgp_dict)
        bgp_info_dict = bgp_dict()
        __slots__ = bgp_info_dict

        # Initialize logging module
        LoggerClass.logging()

        ci_fqdn, neighbor_ip = argument_parser()

        bgp_orchestrator(ci_fqdn, neighbor_ip)
    except KeyboardInterrupt:
        raise SystemExit("APPLICATION TERMINATED!")
