import requests
import yaml
import re
import time

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

def fetch_single_line(node_type):
    """单线路请求（避免触发 VIP 限制）"""
    url = f"{BASE_URL}&nodeid={node_type}"
    try:
        print(f"📡 请求线路 [nodeid={node_type}]...")
        resp = requests.get(url, headers=HEADERS, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") in [0, 200, "200"]:
                info = data.get("info", [])
                raw_ips = [item.get("ip") if isinstance(item, dict) else item for item in info]
                clean_ips = list(dict.fromkeys(filter(None, [clean_ip(ip) for ip in raw_ips])))
                print(f"   ↳ 成功提取 {len(clean_ips)} 个有效 IP")
                return clean_ips
            else:
                print(f"   ⚠️ API 提示: {data.get('msg')}")
        else:
            print(f"   ⚠️ 请求失败，状态码: {resp.status_code}")
    except Exception as e:
        print(f"   ❌ 请求异常: {e}")
    return []

def main():
    print("🚀 开始自动同步 Cloudflare 优选 IP...")
    
    # 拆分为单独线路依次请求（普通免费账户支持的格式）
    ctcc_ips = fetch_single_line("ctcc")
    time.sleep(1)
    cucc_ips = fetch_single_line("cucc")
    time.sleep(1)
    cmcc_ips = fetch_single_line("cmcc")
    time.sleep(1)
    bgp_ips  = fetch_single_line("bgp")

    # 保底 IP（防止接口无数据时节点为空）
    default_ctcc = ['172.64.229.88', '104.19.171.91', '104.18.143.64', '104.16.182.154']
    default_cucc = ['104.17.152.212', '104.29.126.212', '104.17.156.102', '162.159.143.133']
    default_cmcc = ['104.19.47.75', '104.16.156.210']
    default_bgp  = ['172.64.229.54', '104.18.46.20']

    # 智能补全
    selected_map = {
        '电信': ctcc_ips[0:4] if len(ctcc_ips) >= 4 else ctcc_ips + default_ctcc[len(ctcc_ips):4],
        '联通': cucc_ips[0:4] if len(cucc_ips) >= 4 else cucc_ips + default_cucc[len(cucc_ips):4],
        '移动': cmcc_ips[0:2] if len(cmcc_ips) >= 2 else cmcc_ips + default_cmcc[len(cmcc_ips):2],
        '多线': bgp_ips[0:2]  if len(bgp_ips)  >= 2 else bgp_ips  + default_bgp[len(bgp_ips):2]
    }

    # 读取 template.yaml
    with open('template.yaml', 'r', encoding='utf-8') as f:
        template = yaml.safe_load(f)

    updated_count = 0
    for proxy in template.get('proxies', []):
        p_name = proxy.get('name', '')
        
        # 匹配电信节点
        if '电信优选01' in p_name and len(selected_map['电信']) > 0: proxy['server'] = selected_map['电信'][0]; updated_count += 1
        elif '电信优选02' in p_name and len(selected_map['电信']) > 1: proxy['server'] = selected_map['电信'][1]; updated_count += 1
        elif '电信优选03' in p_name and len(selected_map['电信']) > 2: proxy['server'] = selected_map['电信'][2]; updated_count += 1
        elif '电信优选04' in p_name and len(selected_map['电信']) > 3: proxy['server'] = selected_map['电信'][3]; updated_count += 1
            
        # 匹配联通节点
        elif '联通优选01' in p_name and len(selected_map['联通']) > 0: proxy['server'] = selected_map['联通'][0]; updated_count += 1
        elif '联通优选02' in p_name and len(selected_map['联通']) > 1: proxy['server'] = selected_map['联通'][1]; updated_count += 1
        elif '联通优选03' in p_name and len(selected_map['联通']) > 2: proxy['server'] = selected_map['联通'][2]; updated_count += 1
        elif '联通优选04' in p_name and len(selected_map['联通']) > 3: proxy['server'] = selected_map['联通'][3]; updated_count += 1

        # 匹配移动节点
        elif '移动优选01' in p_name and len(selected_map['移动']) > 0: proxy['server'] = selected_map['移动'][0]; updated_count += 1
        elif '移动优选02' in p_name and len(selected_map['移动']) > 1: proxy['server'] = selected_map['移动'][1]; updated_count += 1

        # 匹配多线节点
        elif '多线优选01' in p_name and len(selected_map['多线']) > 0: proxy['server'] = selected_map['多线'][0]; updated_count += 1
        elif '多线优选02' in p_name and len(selected_map['多线']) > 1: proxy['server'] = selected_map['多线'][1]; updated_count += 1

    # 写入 sub.yaml
    with open('sub.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(template, f, allow_unicode=True, sort_keys=False)

    print(f"\n✨ 更新完成！成功写入 {updated_count} 个节点 IP 至 sub.yaml。")

if __name__ == '__main__':
    main()
