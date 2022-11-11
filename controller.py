#!/usr/bin/env python3
import argparse
import os
import sys
from time import sleep

import grpc

# Import P4Runtime lib from parent utils dir
# Probably there's a better way of doing this.
sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 './utils/'))
import p4runtime_lib.bmv2
import p4runtime_lib.helper
from p4runtime_lib.error_utils import printGrpcError
from p4runtime_lib.switch import ShutdownAllSwitchConnections

SWITCH_TO_HOST_PORT = 1
SWITCH_TO_SWITCH_PORT = 2

def readTableRules(p4info_helper, sw):
    """
    Reads the table entries from all tables on the switch.
    :param p4info_helper: the P4Info helper
    :param sw: the switch connection
    """
    print('\n----- Reading tables rules for %s -----' % sw.name)
    for response in sw.ReadTableEntries():
        for entity in response.entities:
            entry = entity.table_entry
            # TODO For extra credit, you can use the p4info_helper to translate
            #      the IDs in the entry to names
            print(entry)
            print('-----')


def writeTunnelRules(p4info_helper, ingress_sw, dst_eth_addr, dst_ip_addr, port):

    # Write drop rule
    table_entry = p4info_helper.buildTableEntry(
        table_name="MyIngress.ipv4_lpm",
        default_action=True,
        action_name="MyIngress.drop",
        action_params= {}
    )
    ingress_sw.WriteTableEntry(table_entry)

    # Write ingress rule
    table_entry = p4info_helper.buildTableEntry(
        table_name="MyIngress.ipv4_lpm",
        match_field={
            "hdr.ipv4.dstAddr": (dst_ip_addr, 32)
        },
        action_name="MyIngress.ipv4_forward",
        action_params={
            "dstAddr": dst_eth_addr,
            "port": port
        }
    )
    ingress_sw.WriteTableEntry(table_entry)
    
    # table_entry = p4info_helper.buildTableEntry(
    #     table_name="MyIngress.ipv4_lpm",
    #     match_fields={
    #         "hdr.ipv4.dstAddr": (dst_ip_addr, 32)
    #     },
    #     action_name="MyIngress.myTunnel_ingress",
    #     action_params={
    #         "dst_id": tunnel_id,
    #     })
    # ingress_sw.WriteTableEntry(table_entry)
    # print("Installed ingress tunnel rule on %s" % ingress_sw.name)

    # table_entry = p4info_helper.buildTableEntry(
    #     table_name="MyIngress.myTunnel_exact",
    #     match_fields={
    #         "hdr.myTunnel.dst_id": tunnel_id
    #     },
    #     action_name="MyIngress.myTunnel_forward",
    #     action_params={
    #         "port": SWITCH_TO_SWITCH_PORT
    #     })
    # ingress_sw.WriteTableEntry(table_entry)
    # print("Installed transit tunnel rule on %s" % ingress_sw.name)

    # table_entry = p4info_helper.buildTableEntry(
    #     table_name="MyIngress.myTunnel_exact",
    #     match_fields={
    #         "hdr.myTunnel.dst_id": tunnel_id
    #     },
    #     action_name="MyIngress.myTunnel_egress",
    #     action_params={
    #         "dstAddr": dst_eth_addr,
    #         "port": SWITCH_TO_HOST_PORT
    #     })
    # egress_sw.WriteTableEntry(table_entry)
    # print("Installed egress tunnel rule on %s" % egress_sw.name)

def main(p4info_file_path, bmv2_file_path):
    # Instantiate a P4Runtime helper from the p4info file
    p4info_helper = p4runtime_lib.helper.P4InfoHelper(p4info_file_path)

    s1 = p4runtime_lib.bmv2.Bmv2SwitchConnection(
        name='s1',
        address='127.0.0.1:50051',
        device_id=0,
        proto_dump_file='logs/s1-p4runtime-requests.txt')
    s2 = p4runtime_lib.bmv2.Bmv2SwitchConnection(
        name='s2',
        address='127.0.0.1:50052',
        device_id=1,
        proto_dump_file='logs/s2-p4runtime-requests.txt')
    s3 = p4runtime_lib.bmv2.Bmv2SwitchConnection(
        name='s3',
        address='127.0.0.1:50053',
        device_id=2,
        proto_dump_file='logs/s3-p4runtime-requests.txt')
    s4 = p4runtime_lib.bmv2.Bmv2SwitchConnection(
        name='s4',
        address='127.0.0.1:50054',
        device_id=3,
        proto_dump_file='logs/s4-p4runtime-requests.txt')

    s1.MasterArbitrationUpdate()
    s2.MasterArbitrationUpdate()
    s3.MasterArbitrationUpdate()
    s4.MasterArbitrationUpdate()

    s1.SetForwardingPipelineConfig(p4info=p4info_helper.p4info, bmv2_json_file_path=bmv2_file_path)
    s2.SetForwardingPipelineConfig(p4info=p4info_helper.p4info, bmv2_json_file_path=bmv2_file_path)
    s3.SetForwardingPipelineConfig(p4info=p4info_helper.p4info, bmv2_json_file_path=bmv2_file_path)
    s4.SetForwardingPipelineConfig(p4info=p4info_helper.p4info, bmv2_json_file_path=bmv2_file_path)

    # setup the connection from s1 to s2
    writeTunnelRules(p4info_helper, ingress_sw=s1, dst_eth_addr="08:00:00:00:02:22", dst_ip_addr="10.0.2.2", port=32)
    # setup the connection from s2 to s1
    writeTunnelRules(p4info_helper, ingress_sw=s2, dst_eth_addr="08:00:00:00:01:11", dst_ip_addr="10.0.1.1", port=32)
    # writeTunnelRules(p4info_helper, ingress_sw=s2, egress_sw=s1, tunnel_id=200, dst_eth_addr="08:00:00:00:01:11", dst_ip_addr="10.0.1.1/24")

    # ShutdownAllSwitchConnections()
    print("close all switches connection, mininet 'h1 ping h2' stucks.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='P4Runtime Controller')
    parser.add_argument('--p4info', help='p4info proto in text format from p4c',
                        type=str, action="store", required=False,
                        default='./build/basic.p4.p4info.txt')
    parser.add_argument('--bmv2-json', help='BMv2 JSON file from p4c',
                        type=str, action="store", required=False,
                        default='./build/basic.json')
    args = parser.parse_args()

    if not os.path.exists(args.p4info):
        parser.print_help()
        print("\np4info file not found: %s\nHave you run 'make'?" % args.p4info)
        parser.exit(1)
    if not os.path.exists(args.bmv2_json):
        parser.print_help()
        print("\nBMv2 JSON file not found: %s\nHave you run 'make'?" % args.bmv2_json)
        parser.exit(1)
    main(args.p4info, args.bmv2_json)
