import pandas as pd
import re
import glob

# 获取所有Excel文件
excel_files = glob.glob('e:\\女娲1号\\发货单\\*.xlsx')

print("检查所有文件的购买单位信息提取情况...")
print("=" * 60)

# 只检查前5个文件，避免输出过多
for file_path in excel_files[:5]:
    file_name = file_path.split('\\')[-1]
    print(f"\n检查文件: {file_name}")
    
    try:
        excel_file = pd.ExcelFile(file_path)
        
        # 遍历所有工作表查找客户信息
        found_customer = False
        found_contact = False
        customer_name = ""
        contact = ""
        
        for sheet_name in excel_file.sheet_names:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # 查找包含客户信息的行
                for i in range(min(10, len(df))):
                    for j in range(min(3, len(df.columns))):
                        # 直接处理，不使用try-except
                        cell_value = str(df.iloc[i, j]) if not pd.isna(df.iloc[i, j]) else ""
                        
                        if len(cell_value) > 50:
                            print(f"  工作表: {sheet_name}, 行 {i+1}, 列 {j+1}: {cell_value[:100]}...")
                        else:
                            print(f"  工作表: {sheet_name}, 行 {i+1}, 列 {j+1}: {cell_value}")
                        
                        if '购货单位' in cell_value or '购买单位' in cell_value:
                            print(f"  找到了购买单位信息: {cell_value[:100]}")
                            # 提取客户名称
                            customer_match = re.search(
                                r'[购货购买]单位[（(][^）)]*[）)][：:]\s*(.+?)\s*(?:[\s联系人]|$)',
                                cell_value
                            )
                            if customer_match:
                                customer_name = customer_match.group(1).strip()
                                found_customer = True
                                print(f"  ✓ 提取到客户名称: {customer_name}")
                            
                            # 提取联系人
                            contact_match = re.search(
                                r'联系人[：:]\s*(.+?)\s*(?:[\s日期]|$)',
                                cell_value
                            )
                            if contact_match:
                                contact = contact_match.group(1).strip()
                                found_contact = True
                                print(f"  ✓ 提取到联系人: {contact}")
                        
                        if found_customer and found_contact:
                            break
                    
                    if found_customer and found_contact:
                        break
                
                if found_customer and found_contact:
                    break
                    
            except Exception as e:
                print(f"  处理工作表 {sheet_name} 失败: {str(e)}")
                continue
        
        print(f"  最终提取结果: 客户名称='{customer_name}', 联系人='{contact}'")
        
    except Exception as e:
        print(f"  处理文件 {file_name} 失败: {str(e)}")
        continue

print("\n" + "=" * 60)
print("检查完成！")