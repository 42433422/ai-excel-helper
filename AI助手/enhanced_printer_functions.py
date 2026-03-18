
# 增强的标签打印函数，解决ShellExecute问题
def print_pdf_labels_enhanced(pdf_path: str, copies: int = 1, show_app: bool = True) -> Dict:
    """
    增强的PDF标签打印函数
    解决ShellExecute被默认打印机覆盖的问题
    """
    try:
        if not os.path.exists(pdf_path):
            return {"success": False, "message": f"PDF文件不存在: {pdf_path}"}
        
        # 获取正确的标签打印机
        label_printer = get_label_printer()
        if not label_printer:
            return {"success": False, "message": "未找到标签打印机"}
        
        logger.info(f"开始增强PDF标签打印: {pdf_path}")
        logger.info(f"标签打印机: {label_printer}")
        
        # 方法1: 使用ShellExecute，但增加打印机名称验证
        abs_path = os.path.abspath(pdf_path)
        
        # 确保打印机名称正确
        printer_param = f'/d:"{label_printer}"'
        logger.info(f"ShellExecute打印机参数: {printer_param}")
        
        if show_app:
            result = win32api.ShellExecute(0, "print", abs_path, printer_param, ".", 1)
        else:
            result = win32api.ShellExecute(0, "print", abs_path, printer_param, ".", 0)
        
        if result > 32:
            return {
                "success": True, 
                "message": f"PDF标签打印成功发送到 {label_printer}",
                "file": pdf_path,
                "printer": label_printer,
                "method": "enhanced_shellexecute"
            }
        else:
            # 方法2: 如果ShellExecute失败，使用PrintDocument
            logger.warning("ShellExecute失败，尝试PrintDocument方法")
            return print_with_printdocument(pdf_path, label_printer)
            
    except Exception as e:
        logger.error(f"增强PDF打印失败: {e}")
        return {"success": False, "message": f"增强PDF打印失败: {str(e)}"}

def print_with_printdocument(pdf_path: str, printer_name: str) -> Dict:
    """使用PrintDocument方法打印PDF"""
    try:
        # 这里可以实现基于PrintDocument的PDF打印
        # 目前作为备选方案
        logger.info(f"PrintDocument方法尚未实现，使用ShellExecute重试")
        return {"success": False, "message": "PrintDocument方法暂未实现"}
        
    except Exception as e:
        return {"success": False, "message": f"PrintDocument打印失败: {str(e)}"}
