import requests
import yaml
import time
import json

API_URL = "https://api.uouin.com/app/cloudflare"
USERNAME = "f7579845"
KEY = "lqCB27tmVTf8uC3"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_ips_for_nodes(node_str):
    """向 API 请求指定节点的优选 IP"""
    params = {
        'username': USERNAME,
        'key': KEY,
        'nodeid': node_str,
        'url': 'https://api.uouin.com'  # 补全 API 必填的 url 参数
    }
    
    try:
        print(f"📡 发起 API 请求 [nodeid={node_str}]...")
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
        print(f"   HTTP 状态码: {resp.status_code}")
        
        if resp.status_code == 200:
            res_data = resp.json()
            code = str(res_data.get('code', ''))
            msg = res_data.get('msg', '')
            print(f"   API 返回状态: code={code}, msg={msg}")
            
            if code == '200' and 'data' in res_data:
                return res_data['data']
            else:
                print(f"⚠️ API 返回非成功数据: {res_data}")
        else:
            print(f"❌ HTTP 请求失败: {resp.text}")
            
    except Exception as e:
        print(f"❌ 请求过程出现异常: {e}")
        
    return {}

def fetch_all_ips():
    selected_ips = {'电信': [], '联通': [], '移动': [], '多线': []}
    
    # 1. 第一次请求：获取电信、联通、移动 (遵循 nodeid 单次请求最多 3 个的限制)
    data_batch1 = get_ips_for_nodes('ctcc|cucc|cmcc')
    
    # 2. 严格遵守站长类 API 频率限制 (2.0次/秒)，停顿 1 秒防止被接口拦截
    print("⏳ 等待 1 秒，避开站长类 API 频率限制...")
    time.sleep(1.0)
    
    # 3. 第二次请求：获取多线
    data_batch2 = get_ips_for_nodes('bgp')
    
    # 4. 合并两次请求的数据
    combined_data = {}
    if isinstance(data_batch1, dict): 
        combined_data.update(data_batch1)
    if isinstance(data_batch2, dict): 
        combined_data.update(data_batch2)

    isp_map = {
        'ctcc': ('电信', 4),
        'cucc': ('联通', 4),
        'cmcc': ('移动', 2),
        'bgp':  ('多线', 2)
    }

    # 5. 解析提取真实 IP
    for key, (isp_name, max_count) in isp_map.items():
        node_info = combined_data.get(key, {})
        if isinstance(node_info, dict):
            info_list = node_info.get('info', [])
            if isinstance(info_list, list):
                for item in info_list:
                    if isinstance(item, dict):
                        ip = item.get('ip', '').strip()
                        if ip and ip.count('.') == 3 and len(selected_ips[isp_name]) < max_count:
                            selected_ips[isp_name].append(ip)

    print("\n🔍 接口解析到的真实 IP 结果：")
    for isp, ips in selected_ips.items():
        print(f"   【{isp}】({len(ips)}个): {ips}")

    # 6. 兜底备用 IP (仅在 API 请求失败或提取数量不足时补齐)
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
    print("🚀 开始运行自动 IP 同步程序...")
    selected_map = fetch_all_ips()

    print("\n📝 正在读取 template.yaml...")
    with open('template.yaml', 'r', encoding='utf-8') as f:
        template = yaml.safe_load(f)

    updated_count = 0
    for proxy in template.get('proxies', []):
        p_name = proxy.get('name', '')
        
        # 电信节点
        if '电信优选01' in p_name: proxy['server'] = selected_map['电信'][0]; updated_count += 1
        elif '电信优选02' in p_name: proxy['server'] = selected_map['电信'][1]; updated_count += 1
        elif '电信优选03' in p_name: proxy['server'] = selected_map['电信'][2]; updated_count += 1
        elif '电信优选04' in p_name: proxy['server'] = selected_map['电信'][3]; updated_count += 1
            
        # 联通节点
        elif '联通优选01' in p_name: proxy['server'] = selected_map['联通'][0]; updated_count += 1
        elif '联通优选02' in p_name: proxy['server'] = selected_map['联通'][1]; updated_count += 1
        elif '联通优选03' in p_name: proxy['server'] = selected_map['联通'][2]; updated_count += 1
        elif '联通优选04' in p_name: proxy['server'] = selected_map['联通'][3]; updated_count += 1

        # 移动节点
        elif '移动优选01' in p_name: proxy['server'] = selected_map['移动'][0]; updated_count += 1
        elif '移动优选02' in p_name: proxy['server'] = selected_map['移动'][1]; updated_count += 1

        # 多线节点
        elif '多线优选01' in p_name: proxy['server'] = selected_map['多线'][0]; updated_count += 1
        elif '多线优选02' in p_name: proxy['server'] = selected_map['多线'][1]; updated_count += 1

    print(f"✨ 节点替换完成，共更新 {updated_count} 个节点！")

    print("💾 正在写入 sub.yaml...")
    with open('sub.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(template, f, allow_unicode=True, sort_keys=False)

    print("🎉 自动同步程序执行完毕！")

if __name__ == '__main__':
    main()
