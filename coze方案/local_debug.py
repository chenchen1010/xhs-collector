import asyncio
import sys
import os

# Ensure the current directory is in python path to import the module
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from xhs_single_note import main

class MockArgs:
    def __init__(self, params):
        self.params = params

async def run_debug():
    params = {
        "bijilianjie": "https://www.xiaohongshu.com/explore/68d0e16100000000130103e1?xsec_token=AB6443D1XGl8lBrsQOKW5flJrbdS_XoE0xDMB7ClRfpf4=",
        "cookie": "ad_worker_plugin_uuid=2c7bbacdd5404f969ae53ad7dd519c31; uuid=0947ba8d-9f63-466c-9668-9ab0a8b46c2b; gucci_worker_plugin_uuid=078b6df21b6a455f94597602fba8d7fc; a1=19925a5470187r8a44m356rcn47r2xy8vcwl4iiv530000598833; webId=1dab40285efc498992435fac4f5e90bf; gid=yjjJ2022J8hKyjjJ2024WS338yYWFY0446q2Eh2KFSI4W1q8FJCvY48882jYYqq824YDjYdi; abRequestId=1dab40285efc498992435fac4f5e90bf; customerClientId=316506318444956; x-user-id-ad.xiaohongshu.com=63f199ae000000001400ea9f; x-user-id-ad-market.xiaohongshu.com=63f199ae000000001400ea9f; access-token-ad-market.xiaohongshu.com=customer.ad_market.AT-68c517553927384459296772jkzr0p0psdudfgq0; omikuji_worker_plugin_uuid=2e5f7cbfc35749aca3cca4075e4a3018; service-market_worker_plugin_uuid=f713604713c64bae8bef1ba3dd755335; x-user-id-school.xiaohongshu.com=65d88e6a0000000005033c59; uuid=9a71ba65-8838-4175-b1a2-bb176bafd4b2; x-user-id-pro.xiaohongshu.com=63f199ae000000001400ea9f; x-user-id-pgy.xiaohongshu.com=65335fdf000000002b000d08; web_session=040069b4471c97fe5d5e9ee0683b4b620d3fcc; id_token=VjEAABu8PJsMQqUBtYgeibPEtT7USOHW9YaSADhLaGl6o698j2QPtHVnIByBEK06f+kWgehGdfTuED5Pbf9VX28bSW/FGhjCVXMPe280lpOtPGxHP46hVPtatjBIBSn1+7PtifE/; x-user-id-creator.xiaohongshu.com=65335fdf000000002b000d08; access-token-ark.beta.xiaohongshu.com=; access-token=; sso-type=customer; subsystem=ark; x-user-id-ark.xiaohongshu.com=65d88e6a0000000005033c59; access-token-ark.xiaohongshu.com=customer.ark.AT-68c517593546593749860358qvzwznboheiww9z3; beaker.session.id=7576da0fef8cfa45ec6bb47f9e7dafefbb7f9084gAJ9cQAoWAsAAABhcmstbGlhcy1pZHEBWBgAAAA2NjBhOWRlZjJmMjNlMTAwMDFmYWE5MTZxAlgOAAAAcmEtdXNlci1pZC1hcmtxA1gYAAAANjYwYTk3ZDllMjAwMDAwMDAwMDAwMDAzcQRYDgAAAF9jcmVhdGlvbl90aW1lcQVHQdpYbJmK8apYEQAAAHJhLWF1dGgtdG9rZW4tYXJrcQZYQQAAAGZhZTZjYTcxYzI4YjRiM2E4YTQ1ZWU4NzFkYjg0YzA5LTdjM2JmNzU4ZGI2MDRjMTM4ZGYyOWU3Njc1N2Q2NjAwcQdYAwAAAF9pZHEIWCAAAABlMGJjYmJhNjVmZGQ0NDVkOWJmNjE2Y2M1MGU1ZGM5ZHEJWA4AAABfYWNjZXNzZWRfdGltZXEKR0HaWGyZivGqdS4=; customer-sso-sid=68c517593993944658493441smi3lkvvhz0irv5b; access-token-creator.xiaohongshu.com=customer.creator.AT-68c517593993944658493442mtacitfe37qd2kxl; galaxy_creator_session_id=DcgesAYgN6KQ0B3Xkj7osDs0YoEiNCmHGGqI; galaxy.creator.beaker.session.id=1768114498630012615216; webBuild=5.6.5; xsecappid=xhs-pc-web; unread={%22ub%22:%22696487f5000000000a03e190%22%2C%22ue%22:%22696208d5000000000a028817%22%2C%22uc%22:25}; loadts=1768204529255; acw_tc=0ad62b1217682060636048476e3527be0370f6369752209a852b1770cc9b7e; websectiga=3633fe24d49c7dd0eb923edc8205740f10fdb18b25d424d2a2322c6196d2a4ad; sec_poison_id=d5ea7032-48f7-409f-bacc-d9103745f109",
        "debug": True
    }
    
    args = MockArgs(params)
    try:
        result = await main(args)
        import json
        print("\n=== Result ===")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"\n=== Error ===\n{e}")

if __name__ == "__main__":
    asyncio.run(run_debug())
