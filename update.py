import requests
import json
import yaml

# 严格按照 API 文档要求的完整请求 URL
API_URL = "https://api.uouin.com/cloudflare.html?key=cb&type=json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01"
}

def fetch_uouin_ips():
    """根据 uouin 站长 API 文档提取最新优选 IP"""
    selected_ips = {'电信': [], '联通': [], '移动': []}
    
    try:
        print(f"📡 正在请求 uouin 官方 API: {API_URL}")
        resp = requests.get(API_URL, headers=HEADERS, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            # 检查 API 是否返回成功 (code == 200)
            if data.get('code') == 200 or 'info' in data:
                items = data.get('info', [])
                
                for item in items:
                    line = str(item.get('line', ''))
                    ip = str(item.get('ip', '')).strip()
                    
                    # 确保是有效的 IPv4 地址
                    if ip and ip.count('.') == 3:
                        if '电信' in line and len(selected_ips['电信']) < 2:
                            selected_ips['电信'].append(ip)
                        elif '联通' in line and len(selected_ips['联通']) < 2:
                            selected_ips['联通'].append(ip)
                        elif '移动' in line and len(selected_ips['移动']) < 2:
                            selected_ips['移动'].append(ip)

                print("✅ 成功从 uouin API 获取最新优选 IP：")
                print(f"   【电信】: {selected_ips['电信']}")
                print(f"   【联通】: {selected_ips['联通']}")
                print(f"   【移动】: {selected_ips['移动']}")
            else:
                print(f"⚠️ API 返回异常消息: {data.get('msg')}")
        else:
            print(f"⚠️ HTTP 请求失败，状态码: {resp.status_code}")

    except Exception as e:
        print(f"❌ 解析 uouin API 出错: {e}")

    # 防空保底机制（若 API 暂时维护，防止生成的 yaml 为空）
    if not selected_ips['电信']: selected_ips['电信'] = ['104.18.38.221', '172.64.159.178']
    if not selected_ips['联通']: selected_ips['联通'] = ['104.17.142.43', '162.159.152.185']
    if not selected_ips['移动']: selected_ips['移动'] = ['141.101.114.10', '108.162.192.15']

    return selected_ips

def main():
    print("🚀 开始读取 uouin 官方 API 数据源...")
    selected_map = fetch_uouin_ips()

    print("📝 正在注入 template.yaml 并生成 sub.yaml...")
    with open('template.yaml', 'r', encoding='utf-8') as f:
        template = yaml.safe_load(f)

    # 将提取到的 IP 依次写入 YAML 配置节点中
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

    print("🎉 订阅文件 sub.yaml 生成完毕！数据已完全同步 uouin 接口！")

if __name__ == '__main__':
    main()
