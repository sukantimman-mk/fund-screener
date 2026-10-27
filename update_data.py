"""
Finnomena Fund Screener — Data Updater
=======================================
ดึงข้อมูลผลตอบแทน ค่าธรรมเนียม และกองทุนใหม่ล่าสุดจาก Finnomena API
และอัพเดทข้อมูลลงใน index.html พร้อมสำรองไฟล์เดิมอัตโนมัติ
"""

import os
import sys
import json
import re
import urllib.request
import datetime

# Ensure utf-8 output on Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*'
}

def fetch_json(url, timeout=25):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))

def parse_fees(fees_list):
    fee_mgmt = None
    fee_buy = None
    fee_sell = None
    ter = None
    
    for item in (fees_list or []):
        desc = item.get('description', '')
        actual = item.get('actual_value')
        rate = item.get('rate')
        
        def to_float(v):
            if v is None:
                return None
            try:
                s = str(v).replace(',', '').strip()
                if s == '' or s.upper() == 'N/A' or s == '-':
                    return None
                return float(s)
            except Exception:
                return None
        
        act_f = to_float(actual)
        rate_f = to_float(rate)
        
        if 'จัดการ' in desc:
            fee_mgmt = rate_f if rate_f is not None else act_f
        elif 'ขายหน่วยลงทุน' in desc or 'Front-end' in desc:
            fee_buy = act_f if act_f is not None else rate_f
        elif 'รับซื้อคืน' in desc or 'Back-end' in desc:
            fee_sell = act_f if act_f is not None else rate_f
        elif 'รวม' in desc or 'TER' in desc:
            ter = act_f if (act_f is not None and act_f > 0) else rate_f
            
    return fee_mgmt, fee_buy, fee_sell, ter

def infer_type(code, name):
    s = f"{code} {name}".upper()
    if ('THAI' in s and 'ESG' in s) or 'TESG' in s:
        return 'ThaiESG'
    if 'RMF' in s:
        return 'RMF'
    if 'SSF' in s:
        return 'SSF'
    if 'E-CLASS' in s or '(E)' in s or '-E' in s:
        return 'E-Class'
    if 'X-CLASS' in s or '(X)' in s or '-X' in s:
        return 'X-Class'
    if 'PVD' in s:
        return 'PVD'
    if 'LTF' in s:
        return 'LTF'
    if 'ESG' in s:
        return 'ESG'
    if 'AI' in s:
        return 'AI'
    if 'UI' in s:
        return 'UI'
    if '(I)' in s or '-I' in s:
        return 'I'
    return 'ทั่วไป'


TICKER_PATTERNS = [
    (r'\bQQQM\b', 'QQQM', 'Invesco NASDAQ 100 ETF (QQQM)', 'etf'),
    (r'\b(QQQ|USXNDQ|NASDAQ)\b', 'QQQ', 'Invesco NASDAQ 100 ETF (QQQ)', 'etf'),
    (r'\b(S&P500|SP500|US500)\b', 'IVV', 'iShares Core S&P 500 ETF (IVV)', 'etf'),
    (r'\b(SCHD)\b', 'SCHD', 'Schwab U.S. Dividend Equity ETF (SCHD)', 'etf'),
    (r'\b(SCHG)\b', 'SCHG', 'Schwab U.S. Large-Cap Growth ETF (SCHG)', 'etf'),
    (r'\b(JEPQ)\b', 'JEPQ', 'JPMorgan Nasdaq Equity Premium Income ETF (JEPQ)', 'etf'),
    (r'\b(JEPI)\b', 'JEPI', 'JPMorgan Equity Premium Income ETF (JEPI)', 'etf'),
    (r'\b(SEMICON)\b', 'SOXX', 'iShares Semiconductor ETF (SOXX)', 'etf'),
    (r'\b(NK225|NIKKEI)\b', '1329', 'iShares Core Nikkei 225 ETF (1329)', 'etf'),
    (r'\b(TOPIX)\b', '1306', 'NEXT FUNDS TOPIX ETF (1306)', 'etf'),
    (r'\b(GOLD|GLD)\b', 'GLD', 'SPDR Gold Trust (GLD)', 'etf'),
    (r'\b(OIL)\b', 'DBO', 'Invesco DB Oil Fund (DBO)', 'etf'),
    (r'\b(URA|NCLR)\b', 'URA', 'Global X Uranium ETF (URA)', 'etf'),
    (r'\b(ACWI)\b', 'ACWI', 'iShares MSCI ACWI ETF (ACWI)', 'etf'),
    (r'\b(TLWORLDXUS|VXUS)\b', 'VXUS', 'Vanguard Total International Stock ETF (VXUS)', 'etf'),
    (r'\b(INXUS|PICB)\b', 'PICB', 'Principal International Equity ETF (PICB)', 'etf'),
    (r'\b(WXUS|IPKW)\b', 'IPKW', 'Invesco International BuyBack Achievers ETF (IPKW)', 'etf'),
    (r'\b(HIEG)\b', 'HIEG', 'iShares World Equity High Income Active UCITS ETF (HIEG)', 'etf'),
    (r'\b(X-SPACE|TEMA.*SPACE|NASA)\b', 'NASA', 'Tema Space Innovators ETF (NASA)', 'etf'),
    (r'\b(SCBSPACE|SCBUSDSPACE|A-JEDI|JETT)\b', 'JETT', 'VanEck Space Innovators UCITS ETF (JETT)', 'etf'),
    (r'\b(TLSPACE-X|ORBX)\b', 'ORBX', 'Global X Space Tech ETF (ORBX)', 'etf'),
    (r'\b(LHSPACE)\b', 'NB Space Economy', 'Neuberger Berman Next Generation Space Economy Fund', 'active'),
    (r'\b(TDEFENSE|ITA)\b', 'ITA', 'iShares U.S. Aerospace & Defense ETF (ITA)', 'etf'),
    (r'\b(TLDEFENSE|SHLD)\b', 'SHLD', 'Global X Defense Tech ETF (SHLD)', 'etf'),
    (r'\b(DAOL-DEFENSE|DFNS)\b', 'DFNS', 'VanEck Defense UCITS ETF (DFNS)', 'etf'),
]

def run_update(base_dir=None, progress_cb=None):
    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
    index_path = os.path.join(base_dir, 'index.html')
    backup_path = os.path.join(base_dir, 'index.backup.html')
    funds_json_path = os.path.join(base_dir, 'funds.json')
    
    def log(msg, pct=None):
        print(msg)
        if progress_cb:
            progress_cb(pct, msg)

    log("กำลังอ่านข้อมูลเดิมจาก index.html...", 5)
    
    if not os.path.exists(index_path):
        raise FileNotFoundError(f"ไม่พบไฟล์: {index_path}")
        
    # Create backup if not exists
    if not os.path.exists(backup_path):
        with open(index_path, 'r', encoding='utf-8') as src, open(backup_path, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
        log(f"   สร้างไฟล์สำรองที่: {backup_path}")

    existing_funds = {}
    old_categories = []
    old_types = []
    with open(index_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip().startswith('const data ='):
                raw = line.strip()[len('const data ='):].rstrip(';')
                old_data = json.loads(raw)
                for item in old_data.get('funds', []):
                    code = item.get('code')
                    fid = item.get('id')
                    if code: existing_funds[code] = item
                    if fid: existing_funds[fid] = item
                old_categories = old_data.get('categories', [])
                old_types = old_data.get('types', [])
                break

    log(f"   พบกองทุนเดิมในระบบ: {len(old_data.get('funds', []))} กอง", 10)

    # 1. Categories
    log("[1/4] ดึงข้อมูลหมวดหมู่กองทุนจาก Finnomena API...", 15)
    cat_id_to_name = {}
    fund_to_cat = {}
    all_categories = set(old_categories)
    
    try:
        cat_data = fetch_json('https://www.finnomena.com/fn3/api/fund/v2/public/categories?includeFunds=true')
        for main_cat in cat_data.get('data', []):
            for sub in main_cat.get('sub_categories', []):
                cid = sub.get('aimc_category_id')
                cname = sub.get('name_th') or main_cat.get('name_th')
                if cid and cname:
                    cat_id_to_name[cid] = cname
                    all_categories.add(cname)
                for f_sub in sub.get('funds', []):
                    if f_sub.get('fund_id'):
                        fund_to_cat[f_sub['fund_id']] = cname
                    if f_sub.get('short_code'):
                        fund_to_cat[f_sub['short_code']] = cname
        log(f"   หมวดหมู่ทั้งหมด: {len(all_categories)} หมวด", 25)
    except Exception as e:
        log(f"   ⚠️ ไม่สามารถดึงหมวดหมู่ใหม่ได้ ({e}) ใช้หมวดหมู่เดิม", 25)

    # 2. Public List
    log("[2/4] ดึงรายชื่อกองทุนสาธารณะ...", 30)
    fund_meta = {}
    try:
        pub_list = fetch_json('https://www.finnomena.com/fn3/api/fund/public/list')
        for f in pub_list:
            fid = f.get('id')
            code = f.get('short_code')
            meta = {
                'id': fid,
                'code': code,
                'name_th': f.get('name_th'),
                'cat_id': f.get('aimc_category_id')
            }
            if fid: fund_meta[fid] = meta
            if code: fund_meta[code] = meta
        log(f"   พบรายชื่อสาธารณะ: {len(pub_list)} กอง", 40)
    except Exception as e:
        log(f"   ⚠️ ไม่สามารถดึงรายชื่อสาธารณะได้ ({e})", 40)

    # 3. Filter pages
    log("[3/4] ดึงข้อมูลผลตอบแทนและค่าธรรมเนียมล่าสุด...", 45)
    page = 1
    api_funds = []
    while True:
        url = f'https://www.finnomena.com/fn3/api/fund/v2/public/filter?page={page}&size=500'
        res = fetch_json(url)
        batch = res.get('data', {}).get('funds', [])
        if not batch:
            break
        api_funds.extend(batch)
        pagination = res.get('data', {}).get('pagination', {})
        total_p = pagination.get('page_total', 8)
        pct = 45 + int((page / max(total_p, 1)) * 35)
        log(f"   ดึงข้อมูลหน้า {page}/{total_p} ({len(batch)} กอง)...", pct)
        if pagination.get('last_page') or page >= total_p:
            break
        page += 1

    log(f"   ดึงข้อมูลสำเร็จทั้งหมด {len(api_funds)} รายการ", 82)

    # 4. Merge data
    log("[4/4] กำลังประมวลผลผสานข้อมูลและตรวจหากองทุนใหม่...", 85)
    updated_funds = []
    seen_codes = set()
    new_funds_count = 0
    all_types = set(old_types)

    for af in api_funds:
        fid = af.get('fund_id')
        code = af.get('short_code')
        if not code or code in seen_codes:
            continue
        seen_codes.add(code)

        meta = fund_meta.get(code) or fund_meta.get(fid) or {}
        old = existing_funds.get(code) or existing_funds.get(fid)

        fee_mgmt, fee_buy, fee_sell, ter = parse_fees(af.get('fees'))

        # Category
        cat = (old.get('category') if old and old.get('category') else None) or \
              fund_to_cat.get(fid) or fund_to_cat.get(code) or \
              cat_id_to_name.get(meta.get('cat_id')) or 'อื่นๆ'
        all_categories.add(cat)

        # Fund Name
        name = (old.get('name') if old and old.get('name') else None) or \
               meta.get('name_th') or code

        # Fund Type
        ftype = (old.get('type') if old and old.get('type') else None) or infer_type(code, name)
        all_types.add(ftype)

        # Dividend policy
        div_sum = af.get('dividend_sum')
        div_cnt = af.get('dividend_count', 0)
        if old and old.get('dividend'):
            div = old['dividend']
        elif (div_cnt and div_cnt > 0) or (div_sum and float(div_sum) > 0) or '(D)' in code or 'ปันผล' in name:
            div = 'ปันผล'
        else:
            div = 'ไม่ปัน'

        # Preserved fields
        fx = old.get('fx_risk') if old else None
        etf = old.get('etf') if old else None
        aum = old.get('aum') if old else None
        
        is_feeder = old.get('is_feeder', False) if old else False
        feeder_type = old.get('feeder_type') if old else None
        etf_sign = old.get('etf_sign') if old else None
        master_sign = old.get('master_sign') if old else None
        master_fund = old.get('master_fund') if old else None
        
        if not old or not is_feeder:
            # Check ticker patterns
            c_upper = f"{code} {name}".upper()
            for pat, sign, m_full, f_type in TICKER_PATTERNS:
                if re.search(pat, c_upper):
                    is_feeder = True
                    feeder_type = f_type
                    etf_sign = sign if f_type == 'etf' else None
                    master_sign = sign
                    master_fund = m_full
                    break

        # Returns
        r1 = af.get('return_1y')
        r3 = af.get('return_3y')
        r5 = af.get('return_5y')
        r10 = af.get('return_10y')

        if r1 is None and old: r1 = old.get('ret1y')
        if r3 is None and old: r3 = old.get('ret3y')
        if r5 is None and old: r5 = old.get('ret5y')
        if r10 is None and old: r10 = old.get('ret10y')
        if ter is None and old: ter = old.get('ter')
        if fee_mgmt is None and old: fee_mgmt = old.get('fee_mgmt')
        if fee_buy is None and old: fee_buy = old.get('fee_buy')
        if fee_sell is None and old: fee_sell = old.get('fee_sell')

        if not old:
            new_funds_count += 1

        updated_funds.append({
            "id": fid or (old.get('id') if old else code),
            "code": code,
            "name": name,
            "category": cat,
            "type": ftype,
            "dividend": div,
            "fx_risk": fx,
            "etf": etf,
            "aum": aum,
            "is_feeder": is_feeder,
            "feeder_type": feeder_type,
            "etf_sign": etf_sign,
            "master_sign": master_sign,
            "master_fund": master_fund,
            "ret1y": r1,
            "ret3y": r3,
            "ret5y": r5,
            "ret10y": r10,
            "fee_mgmt": fee_mgmt,
            "fee_buy": fee_buy,
            "fee_sell": fee_sell,
            "ter": ter
        })

    # Preserve any old funds not returned in current active batch
    for old_code, old_item in existing_funds.items():
        if old_item['code'] not in seen_codes:
            seen_codes.add(old_item['code'])
            updated_funds.append(old_item)

    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # Sort categories alphabetically, put 'อื่นๆ' at end
    sorted_cats = sorted([c for c in all_categories if c and c != 'อื่นๆ'])
    if 'อื่นๆ' in all_categories:
        sorted_cats.append('อื่นๆ')
        
    sorted_types = sorted(list(all_types))

    final_data = {
        "funds": updated_funds,
        "categories": sorted_cats,
        "types": sorted_types,
        "last_updated": now_str
    }

    log("กำลังบันทึกข้อมูลลงไฟล์...", 92)

    # 1. Save funds.json
    with open(funds_json_path, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False)

    # 2. Update index.html
    json_line = "  const data = " + json.dumps(final_data, ensure_ascii=False) + ";\n"
    
    with open(index_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    replaced = False
    for i, line in enumerate(lines):
        if line.strip().startswith('const data ='):
            lines[i] = json_line
            replaced = True
            break

    if replaced:
        with open(index_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        log("   บันทึกข้อมูลใหม่ลงใน index.html สำเร็จ!", 98)
    else:
        log("   ⚠️ ไม่พบบรรทัด 'const data =' ใน index.html", 98)

    stats = {
        "total_funds": len(updated_funds),
        "new_funds": new_funds_count,
        "categories_count": len(sorted_cats),
        "types_count": len(sorted_types),
        "last_updated": now_str
    }

    log(f"\n========================================================", 100)
    log(f"✅ อัพเดทข้อมูลเรียบร้อยสมบูรณ์!")
    log(f"   - กองทุนทั้งหมด: {stats['total_funds']:,} กอง")
    log(f"   - กองทุนใหม่ที่เพิ่มเข้ามา: {stats['new_funds']:,} กอง")
    log(f"   - เวลาที่อัพเดท: {stats['last_updated']}")
    log(f"========================================================")
    
    return stats

if __name__ == '__main__':
    try:
        run_update()
    except Exception as e:
        print(f"\n❌ เกิดข้อผิดพลาดในการอัพเดท: {e}")
        import traceback
        traceback.print_exc()
