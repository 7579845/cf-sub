import requests
import yaml
import re

# 你的两个核心 API 接口
SOURCES = [
    "https://www.wetest.vip/api/cf2dns/get_cloudflare_ip?key=o1zrmHAF&type=v4",
    "https://vps789.com/public/sum/cfIpApi"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_ip(ip_str):
    """提取纯 IPv4 地址"""
    if not ip_str:
        return None
    match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', str(ip_str).strip())
    return match.group(0) if match else None

def fetch_and_rank_ips():
    """双接口抓取、去重并按【速度优先，延迟其次】排序"""
    ip_records = []
    seen_ips = set()

    for url in SOURCES:
        try:
            print(f"📡 正在拉取数据源 [{url}]...")
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                print(f"   ⚠️ 请求失败，HTTP 状态码: {resp.status_code}")
                continue

            try:
                data = resp.json()
                info_list = data.get("info", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                
                for item in info_list:
                    if not isinstance(item, dict):
                        continue
                    
                    c_ip = clean_ip(item.get("ip"))
                    if c_ip and c_ip not in seen_ips:
                        seen_ips.add(c_ip)
                        
                        # 提取下载速度 (MB/s 或 Mbps)
                        try:
                            speed = float(item.get("download_speed") or item.get("speed") or item.get("download") or 0)
                        except Exception:
                            speed = 0.0

                        # 提取延迟 (ms)
                        try:
                            lat = float(item.get("latency") or item.get("delay") or item.get("ping") or 999)
                        except Exception:
                            lat = 999.0
                            
                        # 提取线路标识
                        line_tag = str(item.get("line", "") or item.get("type", "") or item.get("line_type", "")).lower().strip()
                        ip_records.append({'ip': c_ip, 'speed': speed, 'latency': lat, 'line': line_tag})
                continue
            except Exception:
                pass

            # 纯文本备用解析
            lines = resp.text.splitlines()
            for line in lines:
                c_ip = clean_ip(line)
                if c_ip and c_ip not in seen_ips:
                    seen_ips.add(c_ip)
                    ip_records.append({'ip': c_ip, 'speed': 0.0, 'latency': 999.0, 'line': ''})

        except Exception as e:
            print(f"   ❌ 抓取异常: {e}")

    # 核心排序：速度降序(-x['speed'])优先，延迟升序(x['latency'])其次
    ip_records.sort(key=lambda x: (-x['speed'], x['latency']))

    # 显式线路划分
    line_map = {'电信': [], '联通': [], '移动': [], '多线': []}

    for rec in ip_records:
        ip = rec['ip']
        tag = rec['line']
        
        if 'ct' in tag:
            if ip not in line_map['电信']: line_map['电信'].append(ip)
        elif 'cu' in tag:
            if ip not in line_map['联通']: line_map['联通'].append(ip)
        elif 'cm' in tag:
            if ip not in line_map['移动']: line_map['移动'].append(ip)
        elif 'cn' in tag or 'allavg' in tag or 'all' in tag:
            # 显式将 cn 与 AllAvg 划分至多线
            if ip not in line_map['多线']: line_map['多线'].append(ip)
        else:
            # 其它未标记或通用 IP 统一进入多线
            if ip not in line_map['多线']: line_map['多线'].append(ip)

    sorted_all_ips = [r['ip'] for r in ip_records]
    print(f"   ↳ 抓取完成：电信({len(line_map['电信'])}个) | 联通({len(line_map['联通'])}个) | 移动({len(line_map['移动'])}个) | 多线/cn/AllAvg({len(line_map['多线'])}个)")
    return line_map, sorted_all_ips

def main():
    print("🚀 开始更新 Cloudflare 优选节点 IP...")
    
    line_map, sorted_all_ips = fetch_and_rank_ips()

    # 保底 IP 库
    fallback_ips = [
        '104.16.182.154', '104.17.152.212', '104.18.143.64', '104.19.171.91',
        '104.29.126.212', '162.159.143.133', '172.64.229.88', '172.64.229.54'
    ]

    # 自动补齐数量不足的线路
    pool = sorted_all_ips + fallback_ips
    for key in line_map:
        for p_ip in pool:
            if len(line_map[key]) >= 4:
                break
            if p_ip not in line_map[key]:
                line_map[key].append(p_ip)

    # 读取 template.yaml
    try:
        with open('template.yaml', 'r', encoding='utf-8') as f:
            template = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ 读取 template.yaml 失败: {e}")
        return

    # 替换所有地区（JP、KR、SG）对应的优选节点
    updated_count = 0
    for proxy in template.get('proxies', []):
        p_name = proxy.get('name', '')
        
        if '电信优选01' in p_name: proxy['server'] = line_map['电信'][0]; updated_count += 1
        elif '电信优选02' in p_name: proxy['server'] = line_map['电信'][1]; updated_count += 1
        elif '电信优选03' in p_name: proxy['server'] = line_map['电信'][2]; updated_count += 1
        elif '电信优选04' in p_name: proxy['server'] = line_map['电信'][3]; updated_count += 1
            
        elif '联通优选01' in p_name: proxy['server'] = line_map['联通'][0]; updated_count += 1
        elif '联通优选02' in p_name: proxy['server'] = line_map['联通'][1]; updated_count += 1
        elif '联通优选03' in p_name: proxy['server'] = line_map['联通'][2]; updated_count += 1
        elif '联通优选04' in p_name: proxy['server'] = line_map['联通'][3]; updated_count += 1

        elif '移动优选01' in p_name: proxy['server'] = line_map['移动'][0]; updated_count += 1
        elif '移动优选02' in p_name: proxy['server'] = line_map['移动'][1]; updated_count += 1

        elif '多线优选01' in p_name: proxy['server'] = line_map['多线'][0]; updated_count += 1
        elif '多线优选02' in p_name: proxy['server'] = line_map['多线'][1]; updated_count += 1

    # 写入 sub.yaml
    with open('sub.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(template, f, allow_unicode=True, sort_keys=False)

    print(f"\n✨ 更新成功！已按【速度优先】成功更新了 {updated_count} 个节点（覆盖 JP、KR、SG）。")

if __name__ == '__main__':
    main()
