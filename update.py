import requests
import json
import yaml

# 你的专属 API 接口（带上三网 nodeid 参数）
API_URL = "https://api.uouin.com/app/cloudflare?username=f7579845&key=lqCB27tmVTf8uC3&nodeid=ctcc|cmcc|cucc"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

def fetch_uouin_ips():
    """精确解析 uouin 官方文档 API 格式"""
    selected_ips = {'电信': [], '联通': [], '移动': []}
    
    try:
        print(f"📡 正在请求专属 API: {API_URL}")
        resp = requests.get(API_URL, headers=HEADERS, timeout=12)
        
        if resp.status_code == 200:
            res_data = resp.json()
            data_body = res_data.get('data', {})
            
            # ctcc -> 电信, cmcc -> 移动, cucc -> 联通
            isp_mapping = {
                'ctcc': '电信',
                'cmcc': '移动',
                'cucc': '联通'
            }
            
            for isp_key, isp_name in isp_mapping.items():
                isp_obj = data_body.get(isp_key, {})
                if isinstance(isp_obj, dict):
                    info_list = isp_obj.get('info', [])
                    for item in info_list:
                        ip = item.get('ip', '').strip()
                        if ip and ip.count('.') == 3 and len(selected_ips[isp_name]) < 2:
                            selected_ips[isp_name].append(ip)

            print("✅ 成功解析最新优选 IP：")
            print(f"   【电信】: {selected_ips['电信']}")
            print(f"   【联通】: {selected_ips['联通']}")
            print(f"   【移动】: {selected_ips['移动']}")
        else:
            print(f"⚠️ API 请求失败，HTTP 状态码: {resp.status_code}")
    except Exception as e:
        print(f"❌ 抓取 API 出错: {e}")

    # 保底 IP 机制（网络彻底断连时触发）
    if not selected_ips['电信']: selected_ips['电信'] = ['104.18.38.221', '172.64.159.178']
    if not selected_ips['联通']: selected_ips['联通'] = ['104.17.142.43', '162.159.152.185']
    if not selected_ips['移动']: selected_ips['移动'] = ['141.101.114.10', '108.162.192.15']

    return selected_ips

def main():
    print("🚀 启动自动 IP 同步程序...")
    selected_map = fetch_uouin_ips()

    print("📝 正在读取 template.yaml...")
    with open('template.yaml', 'r', encoding='utf-8') as f:
        template = yaml.safe_load(f)

    # 遍历更新所有节点（包括 JP、KR、SG 地区的所有优选节点）
    updated_count = 0
    for proxy in template.get('proxies', []):
        p_name = proxy.get('name', '')
        
        if '电信优选01' in p_name and len(selected_map['电信']) >= 1:
            proxy['server'] = selected_map['电信'][0]
            updated_count += 1
        elif '电信优选02' in p_name and len(selected_map['电信']) >= 2:
            proxy['server'] = selected_map['电信'][1]
            updated_count += 1
        elif '联通优选01' in p_name and len(selected_map['联通']) >= 1:
            proxy['server'] = selected_map['联通'][0]
            updated_count += 1
        elif '联通优选02' in p_name and len(selected_map['联通']) >= 2:
            proxy['server'] = selected_map['联通'][1]
            updated_count += 1
        elif '移动优选01' in p_name and len(selected_map['移动']) >= 1:
            proxy['server'] = selected_map['移动'][0]
            updated_count += 1
        elif '移动优选02' in p_name and len(selected_map['移动']) >= 2:
            proxy['server'] = selected_map['移动'][1]
            updated_count += 1

    print(f"✨ 成功替换了 {updated_count} 个优选节点的 IP 地址！")

    print("💾 正在写入 sub.yaml...")
    with open('sub.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(template, f, allow_unicode=True, sort_keys=False)

    print("🎉 订阅文件 sub.yaml 更新完毕！")

if __name__ == '__main__':
    main()
