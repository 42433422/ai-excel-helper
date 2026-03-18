import os
import shutil

def hook_additional_files():
    """打包完成后复制出货记录文件夹到dist目录"""
    try:
        current_dir = os.path.dirname(os.path.abspath(SPEC))
        src_folder = os.path.join(current_dir, '出货记录')
        dist_folder = os.path.join(current_dir, 'dist', '出货记录')
        
        if os.path.exists(src_folder):
            print(f"📁 复制出货记录文件夹到dist...")
            if os.path.exists(dist_folder):
                shutil.rmtree(dist_folder)
            shutil.copytree(src_folder, dist_folder)
            print(f"✅ 已复制到: {dist_folder}")
    except Exception as e:
        print(f"⚠️ 复制出货记录失败: {e}")

hook_additional_files()
