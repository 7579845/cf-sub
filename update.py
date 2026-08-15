import requests
import yaml
import re
import time

# 补充了 username 并更新为全新的 API 路径
USERNAME = "f7579845"
API_KEY  = "lqCB27tmVTf8uC3"
BASE_URL = f"https://api.urlce.com/app/cloudflare?username={USERNAME}&key={API_KEY}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_ip(ip_str):
    """提取纯 IPv4 地址"""
    if not ip_str:
        return None
    match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', str(ip_str))
    return match.group(0) if match else None

def fetch_ips(node_type):
    """请求平台 API 接口"""
    url = f"{BASE_URL}&nodeid={node_type}"
    try:
        print(f"📡 正在请求 API 节点 [nodeid={node_type}]...")
        resp = requests.get(url, headers=HEADERS, timeout=10)
        print(f"   ↳ HTTP 状态码: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            code = data.get("code")
            if code in [0, 200, "200"]:
                info = data.get("info", [])
                raw_ips = []
                if isinstance(info, list):
                    for item in info:
                        if isinstance(item, dict):
                            raw_ips.append(item.get("ip"))
                        elif isinstance(item, str):
                            raw_ips.append(item)
                
                clean_ips = []
                for ip in raw_ips:
                    c_ip = clean_ip(ip)
                    if c_ip and c_ip not in clean_ips:
                        clean_ips.append(c_ip)
                
                print(f"   ↳ 成功提取到 {len(clean_ips)} 个有效 IP")
                return clean_ips
            else:
                print(f"   ⚠️ API 提示: {data.get('msg', '获取失败')}")
        else:
            print(f"   ⚠️ 请求失败，状态码: {resp.status_code}")
    except Exception as e:
        print(f"   ❌ 请求发生异常: {e}")
    return []

def main():
    print("🚀 开始自动同步 Cloudflare 优选 IP...")
    
    # 抓取三网与多线
    ctcc_ips = fetch_ips("ctcc|cucc|cmcc")
    time.sleep(1)
    bgp_ips = fetch_ips("bgp")

    # 兜底默认 IP
    default_ctcc = ['172.64.229.88', '104.19.171.91', '104.18.143.64', '104.16.182.154']
    default_cucc = ['104.17.152.212', '104.29.126.212', '104.17.156.102', '162.159.143.133']
    default_cmcc = ['104.19.47.75', '104.16.156.210']
    default_bgp  = ['172.64.229.54', '104.18.46.20']

    # 智能匹配与分配
    selected_map = {
        '电信': ctcc_ips[0:4] if len(ctcc_ips) >= 4 else ctcc_ips + default_ctcc[len(ctcc_ips):4],
        '联通': ctcc_ips[4:8] if len(ctcc_ips) >= 8 else ctcc_ips[4:] + default_cucc[max(0, 4 - len(ctcc_ips[4:])):4],
        '移动': ctcc_ips[8:10] if len(ctcc_ips) >= 10 else ctcc_ips[8:] + default_cmcc[max(0, 2 - len(ctcc_ips[8:])):2],
        '多线': bgp_ips[0:2] if len(bgp_ips) >= 2 else bgp_ips + default_bgp[len(bgp_ips):2]
    }

    # 读取 template.yaml
    with open('template.yaml', 'r', encoding='utf-8') as f:
        template = yaml.safe_load(f)

    updated_count = 0
    for proxy in template.get('proxies', []):
        p_name = proxy.get('name', '')
        
        if '电信优选01' in p_name and len(selected_map['电信']) > 0: proxy['server'] = selected_map['电信'][0]; updated_count += 1
        elif '电信优选02' in p_name and len(selected_map['电信']) > 1: proxy['server'] = selected_map['电信'][1]; updated_count += 1
        elif '电信优选03' in p_name and len(selected_map['电信']) > 2: proxy['server'] = selected_map['电信'][2]; updated_count += 1
        elif '电信优选04' in p_name and len(selected_map['电信']) > 3: proxy['server'] = selected_map['电信'][3]; updated_count += 1
            
        elif '联通优选01' in p_name and len(selected_map['联通']) > 0: proxy['server'] = selected_map['联通'][0]; updated_count += 1
        elif '联通优选02' in p_name and len(selected_map['联通']) > 1: proxy['server'] = selected_map['联通'][1]; updated_count += 1
        elif '联通优选03' in p_name and len(selected_map['联通']) > 2: proxy['server'] = selected_map['联通'][2]; updated_count += 1
        elif '联通优选04' in p_name and len(selected_map['联通']) > 3: proxy['server'] = selected_map['联通'][3]; updated_count += 1

        elif '移动优选01' in p_name and len(selected_map['移动']) > 0: proxy['server'] = selected_map['移动'][0]; updated_count += 1
        elif '移动优选02' in p_name and len(selected_map['移动']) > 1: proxy['server'] = selected_map['移动'][1]; updated_count += 1

        elif '多线优选01' in p_name and len(selected_map['多线']) > 0: proxy['server'] = selected_map['多线'][0]; updated_count += 1
        elif '多线优选02' in p_name and len(selected_map['多线']) > 1: proxy['server'] = selected_map['多线'][1]; updated_count += 1

    # 写入 sub.yaml
    with open('sub.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(template, f, allow_unicode=True, sort_keys=False)

    print(f"\n✨ 成功！已替换 {updated_count} 个节点 IP，并生成最新的 sub.yaml！")

if __name__ == '__main__':
    main()
