import requests
import json
import time
import socket
import concurrent.futures
import yaml

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*"
}

def fetch_ips_from_github_mirrors():
    """通过 GitHub 原生数据源获取，彻底无视 Cloudflare 5秒盾拦截"""
    ips = {'CT': [], 'CU': [], 'CM': []}
    
    # 多个无防刷/GitHub 原生节点数据源列表
    sources = [
        "https://raw.githubusercontent.com/ymyuuu/IPDB/main/cloudflare/speedtest.json",
        "https://addressesapi.090227.xyz/CloudFlare277",
        "https://raw.githubusercontent.com/cqyp/cloudflare-speedtest/main/ip.txt"
    ]
    
    for url in sources:
        try:
            print(f"📡 正在尝试从数据源获取: {url}")
            resp = requests.get(url, headers=HEADERS, timeout=8)
            if resp.status_code == 200:
                if url.endswith('.json'):
                    data = resp.json()
                    for item in data:
                        ip = item.get('ip') or item.get('ip_address')
                        line = item.get('line', '') or item.get('isp', '')
                        if ip and ip.count('.') == 3:
                            if '电信' in line or 'CT' in line: ips['CT'].append(ip)
                            elif '联通' in line or 'CU' in line: ips['CU'].append(ip)
                            elif '移动' in line or 'CM' in line: ips['CM'].append(ip)
                            else:
                                ips['CT'].append(ip)
                                ips['CU'].append(ip)
                                ips['CM'].append(ip)
                else:
                    # 文本按行解析 IP
                    lines = resp.text.strip().split('\n')
                    for line in lines:
                        ip = line.strip().split()[0] if line.strip() else ''
                        if ip.count('.') == 3:
                            ips['CT'].append(ip)
                            ips['CU'].append(ip)
                            ips['CM'].append(ip)

                if ips['CT'] or ips['CU'] or ips['CM']:
                    print(f"✅ 成功从 {url} 获取到优质 IP！")
                    break
        except Exception as e:
            print(f"⚠️ 源 {url} 请求跳过: {e}")
            
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
    
    # 保底补全
    if len(selected) < count:
        for ip in unique_ips:
            if ip not in selected:
                selected.append(ip)
                if len(selected) == count: break
    return selected[:count]

def main():
    print("🚀 开始抓取最新 Cloudflare 优选 IP...")
    ips = fetch_ips_from_github_mirrors()
    
    # 彻底兜底方案
    if not ips['CT']: ips['CT'] = ['104.18.38.221', '172.64.159.178']
    if not ips['CU']: ips['CU'] = ['104.17.142.43', '162.159.152.185']
    if not ips['CM']: ips['CM'] = ['141.101.114.10', '108.162.192.15']

    selected_map = {}
    for isp_code, isp_name in [('CT', '电信'), ('CU', '联通'), ('CM', '移动')]:
        raw_ips = ips.get(isp_code, [])
        print(f"🔍 正在实测筛选【{isp_name}】优质 IP...")
        top_2 = filter_top_ips(raw_ips, count=2)
        selected_map[isp_name] = top_2
        print(f"✅ 【{isp_name}】测速选出的最佳 IP: {top_2}")

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
