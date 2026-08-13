import requests
import json
import time
import socket
import concurrent.futures
import yaml

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01"
}

def fetch_cf2dns_ips():
    """采用 cf2dns 同款数据源 API (Gacjie / 090227 / HostMonit)"""
    ips = {'CT': [], 'CU': [], 'CM': []}
    
    # cf2dns 核心调用的开源 API 列表
    api_urls = [
        "https://addressesapi.090227.xyz/CloudFlare277",
        "https://api.v2.gacjie.cn/cf/ips",
        "https://stock.hostmonit.com/CloudflareGslb"
    ]
    
    for url in api_urls:
        try:
            print(f"📡 正在调用 cf2dns 优选接口: {url}")
            if "hostmonit" in url:
                resp = requests.post(url, headers=HEADERS, timeout=8)
            else:
                resp = requests.get(url, headers=HEADERS, timeout=8)
                
            if resp.status_code == 200:
                data = resp.json()
                
                # 兼容不同接口的 JSON 返回格式
                if isinstance(data, dict):
                    # HostMonit 或 Gacjie 格式
                    for key in ['ct', 'cu', 'cm', 'CT', 'CU', 'CM', 'telecom', 'unicom', 'mobile']:
                        target_isp = 'CT' if key.lower() in ['ct', 'telecom'] else ('CU' if key.lower() in ['cu', 'unicom'] else 'CM')
                        if key in data and isinstance(data[key], list):
                            for item in data[key]:
                                ip = item.get('ip') or item.get('line')
                                if ip and ip.count('.') == 3:
                                    ips[target_isp].append(ip)
                elif isinstance(data, list):
                    # 090227 / 列表格式
                    for item in data:
                        ip = item.get('ip')
                        line = item.get('line', '') or item.get('isp', '')
                        if ip and ip.count('.') == 3:
                            if '电信' in line or 'CT' in line: ips['CT'].append(ip)
                            elif '联通' in line or 'CU' in line: ips['CU'].append(ip)
                            elif '移动' in line or 'CM' in line: ips['CM'].append(ip)
                            else:
                                ips['CT'].append(ip)
                                ips['CU'].append(ip)
                                ips['CM'].append(ip)

                if ips['CT'] or ips['CU'] or ips['CM']:
                    print(f"✅ 成功从 {url} 获取到优选 IP！")
                    break
        except Exception as e:
            print(f"⚠️ 接口 {url} 请求跳过: {e}")
            
    return ips

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
    
    # 补全保底
    if len(selected) < count:
        for ip in unique_ips:
            if ip not in selected:
                selected.append(ip)
                if len(selected) == count: break
    return selected[:count]

def main():
    print("🚀 启动 cf2dns 同款算法抓取 Cloudflare 优选 IP...")
    ips = fetch_cf2dns_ips()
    
    # 极罕见情况下的兜底 IP
    if not ips['CT']: ips['CT'] = ['104.18.38.221', '172.64.159.178']
    if not ips['CU']: ips['CU'] = ['104.17.142.43', '162.159.152.185']
    if not ips['CM']: ips['CM'] = ['141.101.114.10', '108.162.192.15']

    selected_map = {}
    for isp_code, isp_name in [('CT', '电信'), ('CU', '联通'), ('CM', '移动')]:
        raw_ips = ips.get(isp_code, [])
        print(f"🔍 正在测速筛选【{isp_name}】优质 IP (候选 {len(raw_ips)} 个)...")
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
