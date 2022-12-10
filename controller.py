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
    data_table = []

    for response in sw.ReadTableEntries():
        for entity in response.entities:
            cur_table = []

            entry = entity.table_entry

            table_name = p4info_helper.get_tables_name(entry.table_id)
            for m in entry.match:


                ipv4_dst_addr, ipv4_port = p4info_helper.get_match_field_value(m)
                if ipv4_dst_addr == b'\n\x00\x01\x01':
                    cur_table.append("h1")
                if ipv4_dst_addr == b'\n\x00\x02\x02':
                    cur_table.append("s2")
                if ipv4_dst_addr == b'\n\x00\x03\x03':
                    cur_table.append("s3")


                # print(p4info_helper.get_match_field_name(table_name, m.field_id), end=' ')

                # ipv4_dst_addr = ipv4_dst_addr

                    # print("s1", end=' ')
                # ipv4_port = ipv4_port.decode('utf-8')
                # print((ipv4_dst_addr), end=' ')
                # print('%r' % (.decode("utf-8"),), end=' ')
            action = entry.action.action
            # print(action)

            action_name = p4info_helper.get_actions_name(action.action_id)
            # print(action.params)
            # for p in action.params:
            #     print(p)
            #     print(p.value)
                # print(p4info_helper.get_action_param_name(action_name, p.param_id))
                # print()
            # print(p4info_helper.get_action_param_pb(action_name, "port", ))
            cur_table.append(action_name)
            data_table.append(cur_table)
            # print('->', action_name, end=' ')
            # for p in action.params:
            #     print(p4info_helper.get_action_param_name(action_name, p.param_id), end=' ')
            #     print('%r' % p.value, end=' ')
            print()
    print(data_table)

def printCounter(p4info_helper, sw, counter_name, index):
    # print(sw.ReadCounters(p4info_helper.get_counters_id(counter_name), index))
    for response in sw.ReadCounters(p4info_helper.get_counters_id(counter_name), index):
        for entity in response.entities:
            counter = entity.counter_entry
            print("%s %s %d: %d packets (%d bytes)" % (
                sw.name, counter_name, index,
                counter.data.packet_count, counter.data.byte_count
            ))

def writeTunnelRules(p4info_helper, ingress_sw, dst_eth_addr, dst_ip_addr, port, dst_id):

    # Write ingress rule
    table_entry = p4info_helper.buildTableEntry(
        table_name="MyIngress.ipv4_lpm",
        match_fields={
            "hdr.ipv4.dstAddr": (dst_ip_addr, 32)
        },
        action_name="MyIngress.ipv4_forward",
        action_params={
            "dstAddr": dst_eth_addr,
            "port": port,
            "dst_id": dst_id
        }
    )
    ingress_sw.WriteTableEntry(table_entry)

def deleteTableEntry(p4info_helper, ingress_sw, dst_eth_addr, dst_ip_addr, port, dst_id):
    table_entry = p4info_helper.buildTableEntry(
        table_name="MyIngress.ipv4_lpm",
        match_fields={
            "hdr.ipv4.dstAddr": (dst_ip_addr, 32)
        },
        action_name="MyIngress.ipv4_forward",
        action_params={
            "dstAddr": dst_eth_addr,
            "port": port,
            "dst_id": dst_id
        }
    )
    ingress_sw.DeleteTableEntry(table_entry, False)

    # Change to drop func
    table_entry = p4info_helper.buildTableEntry(
        table_name="MyIngress.ipv4_lpm",
        match_fields={
            "hdr.ipv4.dstAddr": (dst_ip_addr, 32)
        },
        action_name="MyIngress.drop"
    )
    ingress_sw.WriteTableEntry(table_entry)


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

    s1.MasterArbitrationUpdate()
    s2.MasterArbitrationUpdate()
    s3.MasterArbitrationUpdate()

    s1.SetForwardingPipelineConfig(p4info=p4info_helper.p4info, bmv2_json_file_path=bmv2_file_path)
    s2.SetForwardingPipelineConfig(p4info=p4info_helper.p4info, bmv2_json_file_path=bmv2_file_path)
    s3.SetForwardingPipelineConfig(p4info=p4info_helper.p4info, bmv2_json_file_path=bmv2_file_path)

    # setup the connection for s1
    writeTunnelRules(p4info_helper, ingress_sw=s1, dst_eth_addr="08:00:00:00:01:11", dst_ip_addr="10.0.1.1", port=1, dst_id=100)
    writeTunnelRules(p4info_helper, ingress_sw=s1, dst_eth_addr="08:00:00:00:02:22", dst_ip_addr="10.0.2.2", port=2, dst_id=200)
    writeTunnelRules(p4info_helper, ingress_sw=s1, dst_eth_addr="08:00:00:00:03:33", dst_ip_addr="10.0.3.3", port=3, dst_id=300)

    # setup the connection for s2
    writeTunnelRules(p4info_helper, ingress_sw=s2, dst_eth_addr="08:00:00:00:01:11", dst_ip_addr="10.0.1.1", port=1, dst_id=400)
    writeTunnelRules(p4info_helper, ingress_sw=s2, dst_eth_addr="08:00:00:00:02:22", dst_ip_addr="10.0.2.2", port=2, dst_id=500)
    writeTunnelRules(p4info_helper, ingress_sw=s2, dst_eth_addr="08:00:00:00:03:33", dst_ip_addr="10.0.3.3", port=3, dst_id=600)
    # writeTunnelRules(p4info_helper, ingress_sw=s2, egress_sw=s1, tunnel_id=200, dst_eth_addr="08:00:00:00:01:11", dst_ip_addr="10.0.1.1/24")

    # setup the connection for s3
    writeTunnelRules(p4info_helper, ingress_sw=s3, dst_eth_addr="08:00:00:00:01:11", dst_ip_addr="10.0.1.1", port=1, dst_id=700)
    writeTunnelRules(p4info_helper, ingress_sw=s3, dst_eth_addr="08:00:00:00:02:22", dst_ip_addr="10.0.2.2", port=2, dst_id=800)
    writeTunnelRules(p4info_helper, ingress_sw=s3, dst_eth_addr="08:00:00:00:03:33", dst_ip_addr="10.0.3.3", port=3, dst_id=900)


    # ShutdownAllSwitchConnections()
    # readTableRules(p4info_helper, s1)
    # printCounter(p4info_helper, s1, "MyIngress.ingressTunnelCounter", 100)
    deleteTableEntry(p4info_helper, ingress_sw=s1, dst_eth_addr="08:00:00:00:02:22", dst_ip_addr="10.0.2.2", port=2, dst_id=200)
    readTableRules(p4info_helper, s1)
    # while True:
    #     sleep(2)
    #     printCounter(p4info_helper, s1, "MyIngress.ingressTunnelCounter", 100)
    #     printCounter(p4info_helper, s1, "MyIngress.ingressTunnelCounter", 200)
    #     printCounter(p4info_helper, s2, "MyIngress.ingressTunnelCounter", 400)
        # sleep(5)

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
