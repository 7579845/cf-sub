import requests
import json
import yaml

API_URL = "https://api.uouin.com/app/cloudflare"
USERNAME = "f7579845"
KEY = "lqCB27tmVTf8uC3"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*"
}

def fetch_uouin_ips():
    selected_ips = {'电信': [], '联通': [], '移动': [], '多线': []}
    
    isp_mapping = {
        'ctcc': ('电信', 4),
        'cucc': ('联通', 4),
        'cmcc': ('移动', 2),
        'bgp':  ('多线', 2)
    }

    params = {
        'username': USERNAME,
        'key': KEY
    }

    try:
        print("📡 正在向 API 请求最新 Cloudflare 优选 IP...")
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
        
        if resp.status_code == 200:
            res_data = resp.json()
            if isinstance(res_data, str):
                res_data = json.loads(res_data)

            # 获取数据主体
            data_body = res_data.get('data', res_data)
            if isinstance(data_body, str):
                try:
                    data_body = json.loads(data_body)
                except:
                    pass

            # 解析各线路 IP
            if isinstance(data_body, dict):
                for key, (isp_name, max_count) in isp_mapping.items():
                    isp_data = data_body.get(key, [])
                    
                    # 兼容不同层级的 JSON 结构
                    if isinstance(isp_data, dict):
                        info_list = isp_data.get('info', [])
                    elif isinstance(isp_data, list):
                        info_list = isp_data
                    else:
                        info_list = []

                    for item in info_list:
                        if isinstance(item, dict):
                            ip = item.get('ip', '').strip()
                        elif isinstance(item, str):
                            ip = item.strip()
                        else:
                            ip = ''

                        if ip and ip.count('.') == 3 and len(selected_ips[isp_name]) < max_count:
                            selected_ips[isp_name].append(ip)
        else:
            print(f"⚠️ API 返回状态码异常: {resp.status_code}")

    except Exception as e:
        print(f"❌ 抓取 API 出错: {e}")

    print("\n✅ 最新抓取到的网页真实 IP 如下：")
    print(f"   【电信】: {selected_ips['电信']}")
    print(f"   【联通】: {selected_ips['联通']}")
    print(f"   【移动】: {selected_ips['移动']}")
    print(f"   【多线】: {selected_ips['多线']}\n")

    # 仅当 API 彻底失效时才补充默认 IP
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

        # 多线优选 01 - 02
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
