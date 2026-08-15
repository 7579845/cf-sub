import requests
import yaml
import re

# 免费开源的 Cloudflare 优选 IP 节点源（依次尝试抓取）
IP_SOURCES = [
    "https://raw.githubusercontent.com/cmliu/CFipList/main/v4.txt",
    "https://addressesapi.090227.xyz/CloudFlare",
    "https://raw.githubusercontent.com/ip-finder/cloudflare-clean-ip/main/ip.txt"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def fetch_all_ips():
    selected_ips = {'电信': [], '联通': [], '移动': [], '多线': []}
    extracted_ips = []

    # 1. 遍历公开源抓取 IP
    for url in IP_SOURCES:
        try:
            print(f"📡 正在尝试抓取开源 IP 源: {url}")
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                # 使用正则表达式严格提取标准 IPv4，自动忽略所有中文字符、TG宣传标语及节点后缀
                ip_matches = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', resp.text)
                
                # 去重并校验 IP 合法性
                valid_ips = []
                for ip in ip_matches:
                    parts = ip.split('.')
                    if all(0 <= int(p) <= 255 for p in parts) and ip not in valid_ips:
                        valid_ips.append(ip)
                
                if len(valid_ips) >= 12:
                    extracted_ips = valid_ips
                    print(f"✅ 成功提取到 {len(valid_ips)} 个有效优选 IP！")
                    break
        except Exception as e:
            print(f"⚠️ 当前源请求失败: {e}，尝试下一个...")

    # 2. 将提取到的真实 IP 按线路分配
    if len(extracted_ips) >= 12:
        selected_ips['电信'] = extracted_ips[0:4]
        selected_ips['联通'] = extracted_ips[4:8]
        selected_ips['移动'] = extracted_ips[8:10]
        selected_ips['多线'] = extracted_ips[10:12]

    # 3. 兜底备用 IP (仅在所有开源接口抓取不足时触发)
    default_ctcc = ['172.64.229.88', '104.19.171.91', '104.18.143.64', '104.16.182.154']
    default_cucc = ['104.17.152.212', '104.29.126.212', '104.17.156.102', '162.159.143.133']
    default_cmcc = ['104.19.47.75', '104.16.156.210']
    default_bgp  = ['172.64.229.54', '104.18.46.20']

    for i in range(4):
        if len(selected_ips['电信']) <= i: selected_ips['电信'].append(default_ctcc[i])
        if len(selected_ips['联通']) <= i: selected_ips['联通'].append(default_cucc[i])
    for i in range(2):
        if len(selected_ips['移动']) <= i: selected_ips['移动'].append(default_cmcc[i])
        if len(selected_ips['多线']) <= i: selected_ips['多线'].append(default_bgp[i])

    print("\n🔍 最终选定的优选 IP 列表：")
    for k, v in selected_ips.items():
        print(f"   【{k}】: {v}")

    return selected_ips

def main():
    print("🚀 开始运行自动 IP 同步程序...")
    selected_map = fetch_all_ips()

    with open('template.yaml', 'r', encoding='utf-8') as f:
        template = yaml.safe_load(f)

    updated_count = 0
    for proxy in template.get('proxies', []):
        p_name = proxy.get('name', '')
        
        if '电信优选01' in p_name: proxy['server'] = selected_map['电信'][0]; updated_count += 1
        elif '电信优选02' in p_name: proxy['server'] = selected_map['电信'][1]; updated_count += 1
        elif '电信优选03' in p_name: proxy['server'] = selected_map['电信'][2]; updated_count += 1
        elif '电信优选04' in p_name: proxy['server'] = selected_map['电信'][3]; updated_count += 1
            
        elif '联通优选01' in p_name: proxy['server'] = selected_map['联通'][0]; updated_count += 1
        elif '联通优选02' in p_name: proxy['server'] = selected_map['联通'][1]; updated_count += 1
        elif '联通优选03' in p_name: proxy['server'] = selected_map['联通'][2]; updated_count += 1
        elif '联通优选04' in p_name: proxy['server'] = selected_map['联通'][3]; updated_count += 1

        elif '移动优选01' in p_name: proxy['server'] = selected_map['移动'][0]; updated_count += 1
        elif '移动优选02' in p_name: proxy['server'] = selected_map['移动'][1]; updated_count += 1

        elif '多线优选01' in p_name: proxy['server'] = selected_map['多线'][0]; updated_count += 1
        elif '多线优选02' in p_name: proxy['server'] = selected_map['多线'][1]; updated_count += 1

    with open('sub.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(template, f, allow_unicode=True, sort_keys=False)

    print(f"✨ 已成功替换 {updated_count} 个节点 IP 并生成 sub.yaml！")

if __name__ == '__main__':
    main()
