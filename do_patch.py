from pathlib import Path

p = Path('e:/FHD/XCAGI/app/routes/tools.py')
lines = p.read_text(encoding='utf-8').splitlines()

# 找到要替换的范围
start = None
end = None
for i, line in enumerate(lines):
    if '规格支持阿拉伯数字与中文数字' in line and start is None:
        start = i
    if start is not None and 'slot_qty_tins = int(qty_num)' in line and i > start:
        end = i
        break

print(f'替换范围: {start+1} - {end+1}')
print('start:', repr(lines[start]))
print('end:', repr(lines[end]))

new_block = [
    '        # 规格支持阿拉伯数字与中文数字，并优先兼容"规格二十八三桶/规格28三桶"这类连续口语',
    '        if "规格" in slot_text:',
    '            after_spec = slot_text.split("规格", 1)[1]',
    r'            number_token_pattern = r"(?:\d+(?:\.\d+)?|[一二两三四五六七八九]?十[一二三四五六七八九]?|[一二两三四五六七八九零〇])"',
    '',
    '            # 优先匹配"规格XX三桶"这种连读',
    '            m_spec_qty = re.search(',
    r'                rf"^\s*[:：]?\s*({number_token_pattern})\s*(\d+|[一二两三四五六七八九十零〇两])\s*桶",',
    '                after_spec,',
    '            )',
    '            if m_spec_qty:',
    '                spec_num = _parse_cn_number(m_spec_qty.group(1))',
    '                qty_num = _parse_cn_number(m_spec_qty.group(2))',
    '                if spec_num is not None:',
    '                    slot_spec = float(spec_num)',
    '                if qty_num is not None:',
    '                    slot_qty_tins = int(qty_num)',
    '            else:',
    '                # 兜底：只提取规格',
    r'                m_spec = re.search(r"^\s*[:：]?\s*(\d+(?:\.\d+)?)", after_spec)',
    '                if m_spec:',
    '                    spec_num = _parse_cn_number(m_spec.group(1))',
    '                    if spec_num is not None:',
    '                        slot_spec = float(spec_num)',
    '                else:',
    r'                    m_spec_cn = re.search(r"^\s*[:：]?\s*([一二两三四五六七八九]?十[一二三四五六七八九]?|[一二两三四五六七八九零〇])", after_spec)',
    '                    if m_spec_cn:',
    '                        spec_num = _parse_cn_number(m_spec_cn.group(1))',
    '                        if spec_num is not None:',
    '                            slot_spec = float(spec_num)',
    '',
    '        # 如果规格连读已经提取了桶数，就不再重复提取',
    '        if slot_qty_tins is None:',
    r'            m_qty = re.search(r"(?:一共|总共|共)?\s*(\d+|[一二两三四五六七八九十零〇两]+)\s*桶", slot_text)',
    '            if m_qty:',
    '                qty_num = _parse_cn_number(m_qty.group(1))',
    '                if qty_num is not None:',
    '                    slot_qty_tins = int(qty_num)',
]

new_lines = lines[:start] + new_block + lines[end+1:]
p.write_text('\n'.join(new_lines), encoding='utf-8')
print('修改完成，新行数:', len(new_lines))

