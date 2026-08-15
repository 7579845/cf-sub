import requests
import json
import yaml

# 使用专门给 GitHub/脚本开放的优选 API（无防火墙拦截）
API_URL = "https://api.v2.gacjie.cn/cf/ips"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json"
}

def fetch_ips():
    """获取最新三网优选 IP"""
    selected_ips = {'电信': [], '联通': [], '移动': []}
    
    try:
        print(f"📡 正在请求优选 API: {API_URL}")
        resp = requests.get(API_URL, headers=HEADERS, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            # 解析电信、联通、移动 IP
            for item in data.get('ct', []):
                if len(selected_ips['电信']) < 2:
                    selected_ips['电信'].append(item.get('ip'))
            for item in data.get('cu', []):
                if len(selected_ips['联通']) < 2:
                    selected_ips['联通'].append(item.get('ip'))
            for item in data.get('cm', []):
                if len(selected_ips['移动']) < 2:
                    selected_ips['移动'].append(item.get('ip'))

            print("✅ 成功获取最新优选 IP：")
            print(f"   【电信】: {selected_ips['电信']}")
            print(f"   【联通】: {selected_ips['联通']}")
            print(f"   【移动】: {selected_ips['移动']}")
        else:
            print(f"⚠️ API 请求失败，状态码: {resp.status_code}")

    except Exception as e:
        print(f"❌ 解析 API 出错: {e}")

    # 万一接口异常时的保底
    if not selected_ips['电信']: selected_ips['电信'] = ['104.18.38.221', '172.64.159.178']
    if not selected_ips['联通']: selected_ips['联通'] = ['104.17.142.43', '162.159.152.185']
    if not selected_ips['移动']: selected_ips['移动'] = ['141.101.114.10', '108.162.192.15']

    return selected_ips

def main():
    print("🚀 开始读取优选数据源...")
    selected_map = fetch_ips()

    print("📝 正在注入 template.yaml 并生成 sub.yaml...")
    with open('template.yaml', 'r', encoding='utf-8') as f:
        template = yaml.safe_load(f)

    # 替换 IP 地址
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

    print("🎉 订阅文件 sub.yaml 生成完毕！")

if __name__ == '__main__':
    main()
