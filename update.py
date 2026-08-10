import requests
import json
import time
import socket
import concurrent.futures
import yaml

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Cache-Control": "no-cache"
}

def fetch_ips_from_164746():
    """接口 1：ip.164746.xyz JSON 数据源"""
    ts = int(time.time() * 1000)
    url = f"https://ip.164746.xyz/ip.json?_={ts}"
    ips = {'CT': [], 'CU': [], 'CM': []}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for item in data:
                ip = item.get('ip')
                line = item.get('line', '')
                if ip:
                    if '电信' in line or 'CT' in line: ips['CT'].append(ip)
                    elif '联通' in line or 'CU' in line: ips['CU'].append(ip)
                    elif '移动' in line or 'CM' in line: ips['CM'].append(ip)
            print(f"✅ 从 164746 成功抓取到 IP - 电信:{len(ips['CT'])} 联通:{len(ips['CU'])} 移动:{len(ips['CM'])}")
    except Exception as e:
        print(f"⚠️ 164746 接口抓取失败: {e}")
    return ips

def fetch_ips_from_hostmonit():
    """接口 2：HostMonit 备用数据源"""
    url = "https://stock.hostmonit.com/CloudFlareGslb"
    ips = {'CT': [], 'CU': [], 'CM': []}
    try:
        resp = requests.post(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            # 提取线路 IP
            for key, line_name in [('ct', 'CT'), ('cu', 'CU'), ('cm', 'CM')]:
                if key in data:
                    for item in data[key]:
                        ip = item.get('ip') or item.get('line')
                        if ip and ip.count('.') == 3:
                            ips[line_name].append(ip)
            print("✅ 从 HostMonit 成功抓取备用 IP")
    except Exception as e:
        print(f"⚠️ HostMonit 接口抓取失败: {e}")
    return ips

def get_fallback_ips():
    return {
        'CT': ['104.16.200.6', '104.18.32.73'],
        'CU': ['104.26.11.3', '162.159.152.185'],
        'CM': ['141.101.114.10', '108.162.192.15']
    }

def test_tcp_latency(ip, port=443, timeout=1.5):
    start = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))
        sock.close()
        return ip, (time.time() - start) * 1000
    except:
        return ip, float('inf')

def filter_top_ips(ip_list, count=2):
    unique_ips = list(dict.fromkeys(ip_list))
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(test_tcp_latency, ip) for ip in unique_ips]
        for future in concurrent.futures.as_completed(futures):
            ip, latency = future.result()
            if latency < float('inf'):
                results.append((ip, latency))
    results.sort(key=lambda x: x[1])
    selected = [item[0] for item in results[:count]]
    if len(selected) < count:
        for ip in unique_ips:
            if ip not in selected:
                selected.append(ip)
                if len(selected) == count: break
    return selected[:count]

def main():
    print("🚀 开始获取最新 Cloudflare 优选 IP...")
    ips = fetch_ips_from_164746()
    
    if not (ips['CT'] or ips['CU'] or ips['CM']):
        print("🔄 主接口异常，正在切换备用 JSON 数据源...")
        ips = fetch_ips_from_hostmonit()

    fallback = get_fallback_ips()
    selected_map = {}
    
    for isp_code, isp_name in [('CT', '电信'), ('CU', '联通'), ('CM', '移动')]:
        raw_ips = ips.get(isp_code, []) or fallback[isp_code]
        print(f"🔍 正在测速筛选【{isp_name}】IP (共 {len(raw_ips)} 个候选)...")
        top_2 = filter_top_ips(raw_ips, count=2)
        selected_map[isp_name] = top_2
        print(f"✅ 【{isp_name}】最终优选 IP: {top_2}")

    print("📝 正在注入你的 template.yaml 并生成 sub.yaml...")
    with open('template.yaml', 'r', encoding='utf-8') as f:
        template = yaml.safe_load(f)

    for proxy in template.get('proxies', []):
        p_name = proxy.get('name', '')
        if '电信优选01' in p_name and len(selected_map['电信']) >= 1:
            proxy['server'] = selected_map['电信'][0]
        elif '电信优选02' in p_name and len(selected_map['电信']) >= 2:
            proxy['server'] = selected_map['电信'][1]
        elif '联通优选01' in p_name and len(selected_map['联通']) >= 1:
            proxy['server'] = selected_map['联通'][0]
        elif '联通优选02' in p_name and len(selected_map['联通']) >= 2:
            proxy['server'] = selected_map['联通'][1]
        elif '移动优选01' in p_name and len(selected_map['移动']) >= 1:
            proxy['server'] = selected_map['移动'][0]
        elif '移动优选02' in p_name and len(selected_map['移动']) >= 2:
            proxy['server'] = selected_map['移动'][1]

    with open('sub.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(template, f, allow_unicode=True, sort_keys=False)

    print("🎉 订阅文件 sub.yaml 更新成功！")

if __name__ == '__main__':
    main()
