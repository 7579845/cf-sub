import requests
import json
import yaml

# 基础配置
BASE_URL = "https://api.uouin.com/app/cloudflare?username=f7579845&key=lqCB27tmVTf8uC3"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*"
}

def fetch_uouin_ips():
    selected_ips = {'电信': [], '联通': [], '移动': [], '多线': []}
    
    # 拆分为两次请求，突破 API 限制最多 3 个类型的限制
    urls = [
        f"{BASE_URL}&nodeid=ctcc|cmcc|cucc",
        f"{BASE_URL}&nodeid=bgp"
    ]
    
    isp_mapping = {
        'ctcc': '电信',
        'cmcc': '移动',
        'cucc': '联通',
        'bgp': '多线'
    }

    for url in urls:
        try:
            print(f"📡 正在请求 API: {url}")
            resp = requests.get(url, headers=HEADERS, timeout=15)
            
            if resp.status_code == 200:
                res_data = resp.json()
                if isinstance(res_data, str):
                    res_data = json.loads(res_data)

                data_body = res_data.get('data', res_data)
                if isinstance(data_body, str):
                    try:
                        data_body = json.loads(data_body)
                    except:
                        pass
                
                for isp_key, isp_name in isp_mapping.items():
                    if isp_key in data_body:
                        isp_obj = data_body.get(isp_key, {})
                        
                        if isinstance(isp_obj, list):
                            info_list = isp_obj
                        elif isinstance(isp_obj, dict):
                            info_list = isp_obj.get('info', [])
                        else:
                            info_list = []
                            
                        for item in info_list:
                            if isinstance(item, dict):
                                ip = item.get('ip', '').strip()
                                # 电信/联通/移动存前 4 个，多线(BGP)存前 2 个
                                limit = 2 if isp_name == '多线' else 4
                                if ip and ip.count('.') == 3 and len(selected_ips[isp_name]) < limit:
                                    selected_ips[isp_name].append(ip)

        except Exception as e:
            print(f"❌ 抓取 API 出错: {e}")

    print("✅ 成功解析最新优选 IP：")
    print(f"   【电信】: {selected_ips['电信']}")
    print(f"   【联通】: {selected_ips['联通']}")
    print(f"   【移动】: {selected_ips['移动']}")
    print(f"   【多线(BGP)】: {selected_ips['多线']}")

    # 保底 IP 补全机制
    default_ctcc = ['172.64.229.15', '172.66.44.119', '104.17.52.141', '104.19.77.157']
    default_cucc = ['104.17.142.43', '162.159.152.185', '104.16.160.1', '104.17.160.1']
    default_cmcc = ['141.101.114.10', '108.162.192.15', '141.101.115.10', '108.162.193.15']
    default_bgp  = ['162.159.137.85', '162.159.138.85']

    for i in range(4):
        if len(selected_ips['电信']) <= i: selected_ips['电信'].append(default_ctcc[i])
        if len(selected_ips['联通']) <= i: selected_ips['联通'].append(default_cucc[i])
        if len(selected_ips['移动']) <= i: selected_ips['移动'].append(default_cmcc[i])
    for i in range(2):
        if len(selected_ips['多线']) <= i: selected_ips['多线'].append(default_bgp[i])

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
        
        # 电信 01 - 04
        if '电信优选01' in p_name:
            proxy['server'] = selected_map['电信'][0]
            updated_count += 1
        elif '电信优选02' in p_name:
            proxy['server'] = selected_map['电信'][1]
            updated_count += 1
        elif '电信优选03' in p_name:
            proxy['server'] = selected_map['电信'][2]
            updated_count += 1
        elif '电信优选04' in p_name:
            proxy['server'] = selected_map['电信'][3]
            updated_count += 1
            
        # 联通 01 - 04
        elif '联通优选01' in p_name:
            proxy['server'] = selected_map['联通'][0]
            updated_count += 1
        elif '联通优选02' in p_name:
            proxy['server'] = selected_map['联通'][1]
            updated_count += 1
        elif '联通优选03' in p_name:
            proxy['server'] = selected_map['联通'][2]
            updated_count += 1
        elif '联通优选04' in p_name:
            proxy['server'] = selected_map['联通'][3]
            updated_count += 1

        # 移动 01 - 02
        elif '移动优选01' in p_name:
            proxy['server'] = selected_map['移动'][0]
            updated_count += 1
        elif '移动优选02' in p_name:
            proxy['server'] = selected_map['移动'][1]
            updated_count += 1

        # 多线优选 01 - 02（真实填入 BGP 优选 IP）
        elif '多线优选01' in p_name:
            proxy['server'] = selected_map['多线'][0]
            updated_count += 1
        elif '多线优选02' in p_name:
            proxy['server'] = selected_map['多线'][1]
            updated_count += 1

    print(f"✨ 成功替换了 {updated_count} 个优选节点的 IP 地址！")

    print("💾 正在写入 sub.yaml...")
    with open('sub.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(template, f, allow_unicode=True, sort_keys=False)

    print("🎉 订阅文件 sub.yaml 更新完毕！")

if __name__ == '__main__':
    main()
