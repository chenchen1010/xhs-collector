import requests
import json
import sys

# ================= 配置信息 =================
API_URL = "http://localhost:8000/api/v1/collect/note"

# 用户提供的配置
# 引用自 PRD 中的测试数据 (Step 692)
API_KEY = "P2025685459865471"

# PRD 中提供的测试 Cookie
COOKIE = "ad_worker_plugin_uuid=2c7bbacdd5404f969ae53ad7dd519c31; uuid=0947ba8d-9f63-466c-9668-9ab0a8b46c2b; gucci_worker_plugin_uuid=078b6df21b6a455f94597602fba8d7fc; a1=19925a5470187r8a44m356rcn47r2xy8vcwl4iiv530000598833; webId=1dab40285efc498992435fac4f5e90bf; gid=yjjJ2022J8hKyjjJ2024WS338yYWFY0446q2Eh2KFSI4W1q8FJCvY48882jYYqq824YDjYdi; abRequestId=1dab40285efc498992435fac4f5e90bf; customerClientId=316506318444956; x-user-id-ad.xiaohongshu.com=63f199ae000000001400ea9f; x-user-id-ad-market.xiaohongshu.com=63f199ae000000001400ea9f; access-token-ad-market.xiaohongshu.com=customer.ad_market.AT-68c517553927384459296772jkzr0p0psdudfgq0; omikuji_worker_plugin_uuid=2e5f7cbfc35749aca3cca4075e4a3018; service-market_worker_plugin_uuid=f713604713c64bae8bef1ba3dd755335; x-user-id-school.xiaohongshu.com=65d88e6a0000000005033c59; uuid=9a71ba65-8838-4175-b1a2-bb176bafd4b2; x-user-id-pro.xiaohongshu.com=63f199ae000000001400ea9f; x-user-id-pgy.xiaohongshu.com=65335fdf000000002b000d08; web_session=040069b4471c97fe5d5e9ee0683b4b620d3fcc; id_token=VjEAABu8PJsMQqUBtYgeibPEtT7USOHW9YaSADhLaGl6o698j2QPtHVnIByBEK06f+kWgehGdfTuED5Pbf9VX28bSW/FGhjCVXMPe280lpOtPGxHP46hVPtatjBIBSn1+7PtifE/; x-user-id-creator.xiaohongshu.com=65335fdf000000002b000d08; access-token-ark.beta.xiaohongshu.com=; access-token=; sso-type=customer; subsystem=ark; x-user-id-ark.xiaohongshu.com=65d88e6a0000000005033c59; access-token-ark.xiaohongshu.com=customer.ark.AT-68c517593546593749860358qvzwznboheiww9z3; beaker.session.id=7576da0fef8cfa45ec6bb47f9e7dafefbb7f9084gAJ9cQAoWAsAAABhcmstbGlhcy1pZHEBWBgAAAA2NjBhOWRlZjJmMjNlMTAwMDFmYWE5MTZxAlgOAAAAcmEtdXNlci1pZC1hcmtxA1gYAAAANjYwYTk3ZDllMjAwMDAwMDAwMDAwMDAzcQRYDgAAAF9jcmVhdGlvbl90aW1lcQVHQdpYbJmK8apYEQAAAHJhLWF1dGgtdG9rZW4tYXJrcQZYQQAAAGZhZTZjYTcxYzI4YjRiM2E4YTQ1ZWU4NzFkYjg0YzA5LTdjM2JmNzU4ZGI2MDRjMTM4ZGYyOWU3Njc1N2Q2NjAwcQdYAwAAAF9pZHEIWCAAAABlMGJjYmJhNjVmZGQ0NDVkOWJmNjE2Y2M1MGU1ZGM5ZHEJWA4AAABfYWNjZXNzZWRfdGltZXEKR0HaWGyZivGqdS4=; xsecappid=ugc; customer-sso-sid=68c517593993944658493441smi3lkvvhz0irv5b; access-token-creator.xiaohongshu.com=customer.creator.AT-68c517593993944658493442mtacitfe37qd2kxl; galaxy_creator_session_id=DcgesAYgN6KQ0B3Xkj7osDs0YoEiNCmHGGqI; galaxy.creator.beaker.session.id=1768114498630012615216; loadts=1768193857342; acw_tc=0a8f06de17681958331382236ec02086f6655c6d347414f77ab73daeed5817; acw_tc=0a00d58e17681958483181695e9813385749d5d2c2d5dad6427bba65da6398; websectiga=f47eda31ec99545da40c2f731f0630efd2b0959e1dd10d5fedac3dce0bd1e04d; sec_poison_id=765ab115-b773-434b-a0dd-a3be2dc01a3b"

# PRD 中提供的测试表格链接 (Step 699)
TABLE_URL = "https://gcn6bvkburhk.feishu.cn/base/L5yObKSElaxLxUsmgM7cwR2unyd?table=tblwMX5d0foYrjLa&view=vewrPMnOOW"

# PRD 中提供的测试笔记链接 (Step 701)
# 选择第一个链接
NOTE_URL = "https://www.xiaohongshu.com/explore/69510671000000001e011222?xsec_token=ABxT2P8uHqwH-TebtHvshWKszH_o0PEVe7mggVnW2Y2FU=&xsec_source=pc_feed"

# ===========================================

def test_single_note():
    payload = {
        "apiKey": API_KEY,
        "cookie": COOKIE,
        "bijilianjie": NOTE_URL,
        "biaogelianjie": TABLE_URL,
        "writeToFeishu": True 
    }

    print(f"\n🚀 开始测试单篇笔记采集...")
    print(f"URL: {API_URL}")
    print(f"笔记: {NOTE_URL}")
    print(f"目标表格: {TABLE_URL}")
    
    try:
        # 设置超时时间，避免无限等待
        response = requests.post(API_URL, json=payload, timeout=60)
        
        print(f"\n📊 响应状态码: {response.status_code}")
        
        try:
            data = response.json()
            print("\n📝 响应内容:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            if data.get("success"):
                print("\n✅ 测试成功！采集数据已获取。")
                if data.get("records"):
                    fields = data['records'][0]['fields']
                    print(f"\n--- 采集结果预览 ---")
                    print(f"标题: {fields.get('笔记标题', '未知')}")
                    print(f"博主: {fields.get('账号名称', '未知')}")
                    print(f"点赞: {fields.get('点赞数', 0)}")
                    print(f"收藏: {fields.get('收藏数', 0)}")
                    print(f"评论: {fields.get('评论数', 0)}")
                    print(f"------------------")
            else:
                print(f"\n❌ 测试失败: {data.get('message')}")
                if data.get("error"):
                    print(f"❌ 错误详情: {data.get('error')}")
                    
        except json.JSONDecodeError:
            print(f"\n❌ 响应不是有效的 JSON: {response.text}")

    except requests.exceptions.ConnectionError:
        print("\n❌ 连接失败: 无法连接到服务器。")
        print("请确保你已经启动了 FastAPI 服务 (uvicorn app.main:app --reload)")
    except requests.exceptions.Timeout:
        print("\n❌ 请求超时: 服务器响应时间过长。")
    except Exception as e:
        print(f"\n❌ 发生异常: {str(e)}")

if __name__ == "__main__":
    test_single_note()
