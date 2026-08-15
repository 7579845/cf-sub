import requests
import json
import yaml

# API 请求地址
API_URL = "https://api.uouin.com/app/cloudflare?username=f7579845&key=lqCB27tmVTf8uC3&nodeid=ctcc|cmcc|cucc"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*"
}

def fetch_uouin_ips():
    selected_ips = {'电信': [], '联通': [], '移动': []}
    
    try:
        print(f"📡 正在请求专属 API: {API_URL}")
        resp = requests.get(API_URL, headers=HEADERS, timeout=15)
        print(f" HTTP 状态码: {resp.status_code}")
        
        if resp.status_code == 200:
            res_data = resp.json()
            print("📄 接口返回原始 JSON:", json.dumps(res_data, ensure_ascii=False)[:300]) # 打印前300字符用于排查
            
            # 如果 response 是字符串格式的 JSON，尝试二次解析
            if isinstance(res_data, str):
                res_data = json.loads(res_data)

            # 兼容不同的 data 嵌套层级
            data_body = res_data.get('data', res_data)
            if isinstance(data_body, str):
                try:
                    data_body = json.loads(data_body)
                except:
                    pass
            
            isp_mapping = {
                'ctcc': '电信',
                'cmcc': '移动',
                'cucc': '联通'
            }
            
            for isp_key, isp_name in isp_mapping.items():
                isp_obj = data_body.get(isp_key, {})
                
                # 如果返回的是列表而非字典结构
                if isinstance(isp_obj, list):
                    info_list = isp_obj
                elif isinstance(isp_obj, dict):
                    info_list = isp_obj.get('info', [])
                else:
                    info_list = []
                    
                for item in info_list:
                    if isinstance(item, dict):
                        ip = item.get('ip', '').strip()
                        if ip and ip.count('.') == 3 and len(selected_ips[isp_name]) < 2:
                            selected_ips[isp_name].append(ip)

            print("✅ 成功解析最新优选 IP：")
            print(f"   【电信】: {selected_ips['电信']}")
            print(f"   【联通】: {selected_ips['联通']}")
            print(f"   【移动】: {selected_ips['移动']}")
        else:
            print(f"⚠️ API 请求返回非 200 状态")
    except Exception as e:
        print(f"❌ 抓取或解析 API 出错: {e}")

    # 保底 IP 机制（仅在 API 解析彻底失败时启用图二最新 IP 作为备用）
    if not selected_ips['电信']:
        print("⚠️ 未获取到电信 IP，使用最新备用 IP")
        selected_ips['电信'] = ['172.64.229.15', '172.66.44.119']
    if not selected_ips['联通']:
        selected_ips['联通'] = ['104.17.142.43', '162.159.152.185']
    if not selected_ips['移动']:
        selected_ips['移动'] = ['141.101.114.10', '108.162.192.15']

    return selected_ips

def main():
    print("🚀 启动自动 IP 同步程序...")
    selected_map = fetch_uouin_ips()

    print("📝 正在读取 template.yaml...")
    with open('template.yaml', 'r', encoding='utf-8') as f:
        template = yaml.safe_load(f)

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
