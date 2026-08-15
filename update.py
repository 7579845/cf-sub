import requests
import yaml
import re

# 核心优选 IP 接口
SOURCES = [
    "https://www.wetest.vip/api/cf2dns/get_cloudflare_ip?key=o1zrmHAF&type=v4",
    "https://vps789.com/public/sum/cfIpApi"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*"
}

def clean_ip(ip_str):
    """提取纯 IPv4 地址"""
    if not ip_str:
        return None
    match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', str(ip_str).strip())
    return match.group(0) if match else None

def fetch_and_rank_ips():
    """双接口自动兼容抓取、去重并按【速度优先，延迟其次】排序"""
    ip_records = []
    seen_ips = set()

    for url in SOURCES:
        try:
            print(f"📡 正在拉取数据源 [{url}]...")
            resp = requests.get(url, headers=HEADERS, timeout=12)
            
            if resp.status_code != 200:
                print(f"   ⚠️ 请求失败，HTTP 状态码: {resp.status_code}")
                continue

            # 1. 尝试解析 JSON 格式
            try:
                raw_json = resp.json()
                info_list = []

                # 自动探测各种 JSON 嵌套结构 (info / data / result / 列表直接返回)
                if isinstance(raw_json, list):
                    info_list = raw_json
                elif isinstance(raw_json, dict):
                    for key in ["info", "data", "result", "ips", "list"]:
                        if isinstance(raw_json.get(key), list):
                            info_list = raw_json.get(key)
                            break

                count_before = len(ip_records)

                for item in info_list:
                    if not isinstance(item, dict):
                        continue
                    
                    # 兼容不同接口的 IP 字段名
                    c_ip = clean_ip(item.get("ip") or item.get("address") or item.get("ip_address"))
                    if c_ip and c_ip not in seen_ips:
                        seen_ips.add(c_ip)
                        
                        # 兼容不同接口的下载速度字段 (MB/s 或 Mbps)
                        try:
                            speed = float(item.get("download_speed") or item.get("speed") or item.get("download") or item.get("kbs") or 0)
                        except Exception:
                            speed = 0.0

                        # 兼容不同接口的延迟字段 (ms)
                        try:
                            lat = float(item.get("latency") or item.get("delay") or item.get("ping") or 999)
                        except Exception:
                            lat = 999.0
                            
                        # 兼容不同接口的线路标识
                        line_tag = str(item.get("line") or item.get("type") or item.get("line_type") or item.get("node") or "").lower().strip()
                        ip_records.append({'ip': c_ip, 'speed': speed, 'latency': lat, 'line': line_tag})

                fetched_this_time = len(ip_records) - count_before
                print(f"   ↳ 成功提取到 {fetched_this_time} 个有效 IP")

                if fetched_this_time == 0:
                    print(f"   ℹ️ [调试日志] 接口返回内容示例: {str(raw_json)[:200]}")
                
                continue

            except Exception as json_err:
                pass  # 非 JSON 则继续尝试文本按行解析

            # 2. 纯文本逐行解析
            lines = resp.text.splitlines()
            count_before = len(ip_records)
            for line in lines:
                c_ip = clean_ip(line)
                if c_ip and c_ip not in seen_ips:
                    seen_ips.add(c_ip)
                    ip_records.append({'ip': c_ip, 'speed': 0.0, 'latency': 999.0, 'line': ''})
            
            fetched_text = len(ip_records) - count_before
            print(f"   ↳ 纯文本解析提取到 {fetched_text} 个有效 IP")

        except Exception as e:
            print(f"   ❌ 抓取发生异常: {e}")

    # **核心排序逻辑：速度降序(-x['speed'])优先，延迟升序(x['latency'])其次**
    ip_records.sort(key=lambda x: (-x['speed'], x['latency']))

    # 线路分配逻辑
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
            if ip not in line_map['多线']: line_map['多线'].append(ip)

    sorted_all_ips = [r['ip'] for r in ip_records]
    print(f"\n📊 汇总结果：电信({len(line_map['电信'])}个) | 联通({len(line_map['联通'])}个) | 移动({len(line_map['移动'])}个) | 多线/cn/AllAvg({len(line_map['多线'])}个)")
    return line_map, sorted_all_ips

def main():
    print("🚀 开始自动同步 Cloudflare 优选节点 IP...")
    
    line_map, sorted_all_ips = fetch_and_rank_ips()

    # 保底 IP 库（防止 API 彻底失效时无 IP 可用）
    fallback_ips = [
        '104.16.182.154', '104.17.152.212', '104.18.143.64', '104.19.171.91',
        '104.29.126.212', '162.159.143.133', '172.64.229.88', '172.64.229.54'
    ]

    # 自动补全各线路不足的数量
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

    # 逐一更新代理节点
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

    # 导出 sub.yaml
    with open('sub.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(template, f, allow_unicode=True, sort_keys=False)

    print(f"✨ 替换完成！已成功更新 {updated_count} 个节点 IP 并生成 sub.yaml。")

if __name__ == '__main__':
    main()
