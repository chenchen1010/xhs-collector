"""
测试无签名方式能否成功请求小红书 API
"""
import requests
import json

# 测试数据
NOTE_URL = "https://www.xiaohongshu.com/explore/68d0e16100000000130103e1?xsec_token=AB6443D1XGl8lBrsQOKW5flJrbdS_XoE0xDMB7ClRfpf4=&xsec_source=pc_user"

COOKIE = "ad_worker_plugin_uuid=2c7bbacdd5404f969ae53ad7dd519c31; uuid=0947ba8d-9f63-466c-9668-9ab0a8b46c2b; gucci_worker_plugin_uuid=078b6df21b6a455f94597602fba8d7fc; a1=19925a5470187r8a44m356rcn47r2xy8vcwl4iiv530000598833; webId=1dab40285efc498992435fac4f5e90bf; gid=yjjJ2022J8hKyjjJ2024WS338yYWFY0446q2Eh2KFSI4W1q8FJCvY48882jYYqq824YDjYdi; abRequestId=1dab40285efc498992435fac4f5e90bf; customerClientId=316506318444956; x-user-id-ad.xiaohongshu.com=63f199ae000000001400ea9f; x-user-id-ad-market.xiaohongshu.com=63f199ae000000001400ea9f; access-token-ad-market.xiaohongshu.com=customer.ad_market.AT-68c517553927384459296772jkzr0p0psdudfgq0; omikuji_worker_plugin_uuid=2e5f7cbfc35749aca3cca4075e4a3018; service-market_worker_plugin_uuid=f713604713c64bae8bef1ba3dd755335; x-user-id-school.xiaohongshu.com=65d88e6a0000000005033c59; uuid=9a71ba65-8838-4175-b1a2-bb176bafd4b2; x-user-id-pro.xiaohongshu.com=63f199ae000000001400ea9f; x-user-id-pgy.xiaohongshu.com=65335fdf000000002b000d08; web_session=040069b4471c97fe5d5e9ee0683b4b620d3fcc; id_token=VjEAABu8PJsMQqUBtYgeibPEtT7USOHW9YaSADhLaGl6o698j2QPtHVnIByBEK06f+kWgehGdfTuED5Pbf9VX28bSW/FGhjCVXMPe280lpOtPGxHP46hVPtatjBIBSn1+7PtifE/; x-user-id-creator.xiaohongshu.com=65335fdf000000002b000d08; access-token-ark.beta.xiaohongshu.com=; access-token=; sso-type=customer; subsystem=ark; x-user-id-ark.xiaohongshu.com=65d88e6a0000000005033c59; access-token-ark.xiaohongshu.com=customer.ark.AT-68c517593546593749860358qvzwznboheiww9z3; beaker.session.id=7576da0fef8cfa45ec6bb47f9e7dafefbb7f9084gAJ9cQAoWAsAAABhcmstbGlhcy1pZHEBWBgAAAA2NjBhOWRlZjJmMjNlMTAwMDFmYWE5MTZxAlgOAAAAcmEtdXNlci1pZC1hcmtxA1gYAAAANjYwYTk3ZDllMjAwMDAwMDAwMDAwMDAzcQRYDgAAAF9jcmVhdGlvbl90aW1lcQVHQdpYbJmK8apYEQAAAHJhLWF1dGgtdG9rZW4tYXJrcQZYQQAAAGZhZTZjYTcxYzI4YjRiM2E4YTQ1ZWU4NzFkYjg0YzA5LTdjM2JmNzU4ZGI2MDRjMTM4ZGYyOWU3Njc1N2Q2NjAwcQdYAwAAAF9pZHEIWCAAAABlMGJjYmJhNjVmZGQ0NDVkOWJmNjE2Y2M1MGU1ZGM5ZHEJWA4AAABfYWNjZXNzZWRfdGltZXEKR0HaWGyZivGqdS4=; customer-sso-sid=68c517593993944658493441smi3lkvvhz0irv5b; access-token-creator.xiaohongshu.com=customer.creator.AT-68c517593993944658493442mtacitfe37qd2kxl; galaxy_creator_session_id=DcgesAYgN6KQ0B3Xkj7osDs0YoEiNCmHGGqI; galaxy.creator.beaker.session.id=1768114498630012615216; webBuild=5.6.5; xsecappid=xhs-pc-web; unread={%22ub%22:%22696487f5000000000a03e190%22%2C%22ue%22:%22696208d5000000000a028817%22%2C%22uc%22:25}; loadts=1768204529255; acw_tc=0ad62b1217682060636048476e3527be0370f6369752209a852b1770cc9b7e; websectiga=3633fe24d49c7dd0eb923edc8205740f10fdb18b25d424d2a2322c6196d2a4ad; sec_poison_id=d5ea7032-48f7-409f-bacc-d9103745f109"

def extract_param(url, key):
    import re
    match = re.search(rf'[?&]{key}=([^&]+)', url)
    return match.group(1) if match else ""

def test_no_sign():
    print("=" * 60)
    print("测试无签名方式请求小红书 API")
    print("=" * 60)

    # 提取参数
    note_id = "68d0e16100000000130103e1"
    xsec_token = extract_param(NOTE_URL, "xsec_token")
    xsec_source = extract_param(NOTE_URL, "xsec_source") or "pc_user"

    print(f"\n笔记ID: {note_id}")
    print(f"xsec_token: {xsec_token[:50]}...")
    print(f"xsec_source: {xsec_source}")

    # 构建请求
    api_url = "https://edith.xiaohongshu.com/api/sns/web/v1/feed"

    payload = {
        "source_note_id": note_id,
        "image_formats": ["jpg", "webp", "avif"],
        "extra": {"need_body_topic": "1"},
        "xsec_source": xsec_source,
        "xsec_token": xsec_token
    }

    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.xiaohongshu.com",
        "Referer": f"https://www.xiaohongshu.com/explore/{note_id}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        "Cookie": COOKIE
    }

    print("\n[请求] 不使用签名，仅用 Cookie 发起请求...")

    try:
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=10
        )

        print(f"\n[响应] 状态码: {response.status_code}")
        print(f"[响应] 内容长度: {len(response.text)}")

        if response.status_code == 200:
            data = response.json()
            print(f"\n[成功] code: {data.get('code')}")

            if data.get('code') == 0:
                items = data.get('data', {}).get('items', [])
                if items:
                    note_card = items[0].get('note_card', {})
                    print(f"[成功] 笔记标题: {note_card.get('title')}")
                    print(f"[成功] 笔记类型: {note_card.get('type')}")
                    print("\n✅ 无签名方式可行!")
                    return True
            else:
                print(f"[失败] API 返回错误: {data.get('msg', 'unknown')}")

        elif response.status_code == 406:
            print("\n❌ 返回 406，需要签名验证")
            return False

        elif response.status_code == 461:
            print("\n❌ 返回 461，参数无效（xsec_token 可能过期）")
            return False

        else:
            print(f"\n❌ 请求失败: {response.status_code}")
            print(f"响应内容: {response.text[:500]}")
            return False

    except Exception as e:
        print(f"\n❌ 请求异常: {e}")
        return False

if __name__ == "__main__":
    success = test_no_sign()
    print("\n" + "=" * 60)
    if success:
        print("✅ 结论: 可以使用无签名方式（仅 Cookie）")
        print("   建议在 Coze 中使用 xhs_simple_no_sign.js")
    else:
        print("❌ 结论: 必须使用签名方式")
        print("   需要在 Coze 中使用完整签名代码")
    print("=" * 60)
