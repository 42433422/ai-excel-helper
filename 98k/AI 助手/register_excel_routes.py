"""
在 app_api.py 中注册 Excel 模板路由
"""

# 读取 app_api.py 文件
with open(r'e:\FHD\AI 助手\app_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 检查是否已经导入
if 'from excel_template_routes import init_templates_routes' not in content:
    # 在文件开头的导入部分添加
    import_section_end = content.find('\n\n# 初始化 Flask 应用')
    if import_section_end == -1:
        import_section_end = content.find('app = Flask')
    
    if import_section_end != -1:
        # 找到最后一个 import 语句的位置
        last_import = content.rfind('\nfrom', 0, import_section_end)
        if last_import != -1:
            # 在最后一个 import 之后添加
            insert_pos = content.find('\n', last_import) + 1
            new_import = 'from excel_template_routes import init_templates_routes\n'
            content = content[:insert_pos] + new_import + content[insert_pos:]

# 检查是否已经注册
if 'init_templates_routes(app)' not in content:
    # 找到其他路由注册的位置
    register_pos = content.find('app.register_blueprint(tools_bp)')
    if register_pos != -1:
        # 在 tools_bp 注册之后添加
        end_of_line = content.find('\n', register_pos)
        new_registration = '\n# 注册 Excel 模板路由\ninit_templates_routes(app)\n'
        content = content[:end_of_line+1] + new_registration + content[end_of_line+1:]

# 写回文件
with open(r'e:\FHD\AI 助手\app_api.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✓ Excel 模板路由已成功注册到 app_api.py')
